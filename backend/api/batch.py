import os
import io
import sys

# Force UTF-8 output so Unicode characters in agent logs (e.g. →) don't crash on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import json
import pandas as pd
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form, Depends
import asyncio
from bson import ObjectId

# Import dependencies and DB collections
from dependencies import get_current_user
from db import batches_collection, leads_collection, pipeline_collection, email_logs_collection, agent_activity_collection, companies_collection

# Import Ollama wrapper
from api.agents import OllamaWrapper

# Import our LangGraph node compilers
import sys
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from langgraph_nodes.lead_research_node import create_lead_research_graph
from langgraph_nodes.intent_qualifier_node import create_intent_qualifier_graph
from langgraph_nodes.email_strategy_node import create_email_strategy_graph
from langgraph_nodes.followup_timing_node import create_followup_timing_graph
from langgraph_nodes.crm_logger_node import create_crm_logger_graph

from prompts.lead_research_prompts import lead_research_prompts
from prompts.intent_qualifier_prompts import intent_qualifier_prompts
from prompts.email_strategy_prompts import email_strategy_prompts
from prompts.followup_timing_prompts import followup_timing_prompts

router = APIRouter()

DATA_DIR = os.path.join(root_dir, "data")
BATCHES_DIR = os.path.join(DATA_DIR, "batches")
os.makedirs(BATCHES_DIR, exist_ok=True)

async def update_batch_progress(batch_id: str, updates: dict):
    """Helper to merge updates into the batch document in MongoDB"""
    await batches_collection.update_one(
        {"batch_id": batch_id},
        {"$set": updates}
    )

async def push_batch_log(batch_id: str, log_message: str):
    """Helper to push a timestamped log to the batch document"""
    timestamp = datetime.utcnow().strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {log_message}"
    await batches_collection.update_one(
        {"batch_id": batch_id},
        {"$push": {"logs": formatted_msg}}
    )

@router.get("/list")
async def list_batches(user=Depends(get_current_user)):
    """List all batches for the current company"""
    cursor = batches_collection.find({"company_id": user["company_id"]}).sort("created_at", -1)
    batches = await cursor.to_list(length=100)
    for b in batches:
        b["_id"] = str(b["_id"])
        b["company_id"] = str(b["company_id"])
    return {"batches": batches}

@router.get("/{batch_id}/progress")
async def get_batch_progress(batch_id: str, user=Depends(get_current_user)):
    batch = await batches_collection.find_one({"batch_id": batch_id, "company_id": user["company_id"]})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch progress not found")
    batch["_id"] = str(batch["_id"])
    batch["company_id"] = str(batch["company_id"])
    return batch



async def process_batch_background(company_id_str: str, batch_id: str, start_index: int = None, end_index: int = None):
    """
    Background worker that uses LangGraph to process each lead concurrently,
    writing results securely to MongoDB.
    """
    try:
        await asyncio.sleep(1) # Give the UI a second to process the success response
        company_id = ObjectId(company_id_str)
        
        batch_dir = os.path.join(BATCHES_DIR, batch_id)
        leads_file = os.path.join(batch_dir, "Leads_Data.csv")
        emails_file = os.path.join(batch_dir, "Email_Logs.csv")
        
        if not os.path.exists(leads_file):
            await update_batch_progress(batch_id, { "status": "failed", "error": "Leads file missing" })
            return
            
        df = pd.read_csv(leads_file)
        emails_df = pd.read_csv(emails_file) if os.path.exists(emails_file) else pd.DataFrame()
        
        original_total = len(df)
        start_idx = start_index if start_index is not None and start_index >= 0 else 0
        end_idx = end_index if end_index is not None and end_index > start_idx else original_total
        end_idx = min(end_idx, original_total)
        
        df_to_process = df.iloc[start_idx:end_idx].copy()
        total = len(df_to_process)
        
        # Load the Ollama LLM
        llm = OllamaWrapper('minimax-m2.5:cloud')
        
        # Compile pipelines
        agents = {
            'research': create_lead_research_graph(llm, lead_research_prompts),
            'intent': create_intent_qualifier_graph(llm, intent_qualifier_prompts),
            'email': create_email_strategy_graph(llm, email_strategy_prompts),
            'timing': create_followup_timing_graph(llm, followup_timing_prompts),
            'logger': create_crm_logger_graph()
        }
        
        await update_batch_progress(batch_id, {
            "percent": 0,
            "processed_count": 0,
            "total_count": total,
            "agents": { k: "running" for k in ["research", "intent", "message", "timing", "logger"] },
            "message": f"Processing subset of {total} leads (rows {start_idx} to {end_idx-1})" if total < original_total else f"Processing all {total} leads"
        })
        
        processed = 0
        semaphore = asyncio.Semaphore(5)  # Limit concurrent LangGraph executions (sync LLM calls)

        async def process_single_lead(index, row):
            nonlocal processed
            lead_dict = row.dropna().to_dict()
            lead_id = str(lead_dict.get("lead_id", ""))
            
            async with semaphore:
                if not emails_df.empty and 'lead_id' in emails_df.columns:
                    email_history = emails_df[emails_df['lead_id'] == lead_id].to_dict('records')
                else:
                    email_history = []
                    
                # Fetch company details for operator info
                company = await companies_collection.find_one({"_id": company_id})
                operator_info = {}
                if company:
                    operator_info = {
                        "operator_name": company.get("contact_person_name", company.get("company_name", "Unknown Operator")),
                        "operator_company": company.get("company_name", "Unknown Company"),
                        "operator_website": company.get("domain", "") or company.get("website", ""),
                        "operator_email": company.get("email", "")
                    }
                    
                state = {"lead": lead_dict, "email_history": email_history, "operator_info": operator_info}
                company_name = lead_dict.get('company', 'Unknown')
                print(f"\\n[Processing] Lead {lead_id} ({company_name}) through LangGraph pipeline...")
                await push_batch_log(batch_id, f"Initializing pipeline for {company_name} (Lead ID: {lead_id})")
                
                try:
                    # Run CPU/Network heavy LangGraph nodes individually in threads to allow real-time UI logging
                    await push_batch_log(batch_id, f"[{company_name}] Running Agent: [1/5] Lead Web Research...")
                    state = await asyncio.to_thread(agents['research'].invoke, state)
                    
                    await push_batch_log(batch_id, f"[{company_name}] Running Agent: [2/5] Intent Qualification Data Extraction...")
                    state = await asyncio.to_thread(agents['intent'].invoke, state)
                    
                    await push_batch_log(batch_id, f"[{company_name}] Running Agent: [3/5] Personalized Email Strategy Formulation...")
                    state = await asyncio.to_thread(agents['email'].invoke, state)

                    await push_batch_log(batch_id, f"[{company_name}] Running Agent: [4/5] Follow-up Timing Optimization...")
                    state = await asyncio.to_thread(agents['timing'].invoke, state)

                    await push_batch_log(batch_id, f"[{company_name}] Running Agent: [5/5] Formatting and CRM Serialization...")
                    state = await asyncio.to_thread(agents['logger'].invoke, state)
                    
                    # Dump mapped state to MongoDB `leads` collection
                    await leads_collection.update_one(
                        {"lead_id": lead_id, "batch_id": batch_id},
                        {
                            "$set": {
                                "company_id": company_id,
                                "profile": {
                                    "name": lead_dict.get("name"),
                                    "title": lead_dict.get("title"),
                                    "company": lead_dict.get("company"),
                                    "region": lead_dict.get("region"),
                                    "lead_source": lead_dict.get("lead_source"),
                                    "industry": lead_dict.get("industry")
                                },
                                "contact": {
                                    "email": lead_dict.get("email", ""),
                                    "linkedin": lead_dict.get("linkedin", "")
                                },
                                "activity": {
                                    "visits": lead_dict.get("visits", 0),
                                    "time_on_site": lead_dict.get("time_on_site", 0.0),
                                    "pages_per_visit": lead_dict.get("pages_per_visit", 0.0),
                                    "converted": lead_dict.get("converted", False)
                                },
                                "intel": {
                                    "status": "completed",
                                    "intent_score": state.get("intent_score", 0.0),
                                    "key_signals": state.get("key_signals", []),
                                    "email": {
                                        "subject": state.get("subject", ""),
                                        "preview": state.get("email_preview", ""),
                                        "personalization_factors": state.get("personalization_factors", [])
                                    },
                                    "timing": state.get("timing", {}),
                                    "approach": state.get("approach", {}),
                                    "engagement_prediction": state.get("engagement_prediction", {})
                                },
                                "crm": {
                                    "email_sent": False,
                                    "timeline": state.get("timeline", {}),
                                    "deal_value": state.get("deal_value", 0.0),
                                    "stage": state.get("crm_stage", "prospect"),
                                },
                                "status": "Ready",
                                "updated_at": datetime.utcnow()
                            },
                            "$setOnInsert": {"created_at": datetime.utcnow()}
                        },
                        upsert=True
                    )
                    
                    # Log activity
                    await agent_activity_collection.insert_one({
                        "company_id": company_id,
                        "batch_id": batch_id,
                        "lead_id": lead_id,
                        "agent": "PIPELINE",
                        "action": "Completed 5-node AI analysis",
                        "status": "SUCCESS",
                        "timestamp": datetime.utcnow()
                    })
                    await push_batch_log(batch_id, f"SUCCESS: Completed 5-node AI analysis for {company_name}")

                except Exception as e:
                    # Sanitize the error message — strip any unencodable Unicode chars
                    safe_err = str(e).encode('utf-8', errors='replace').decode('utf-8')
                    print(f"Error processing lead {lead_id}: {safe_err}")
                    await push_batch_log(batch_id, f"ERROR: Failed processing {company_name} - {safe_err}")
                    await leads_collection.update_one(
                        {"lead_id": lead_id, "batch_id": batch_id},
                        {"$set": {"status": "Error", "intel.error": str(e), "company_id": company_id}},
                        upsert=True
                    )
                    
                # Update progress
                processed += 1
                percent = int((processed / total) * 100)
                await update_batch_progress(batch_id, {
                    "percent": percent,
                    "processed_count": processed,
                    "total_count": total
                })

        # Process all leads concurrently
        tasks = [process_single_lead(index, row) for index, row in df_to_process.iterrows()]
        await asyncio.gather(*tasks)
            
        # Finish
        await update_batch_progress(batch_id, {
            "status": "completed",
            "percent": 100,
            "processed_count": total,
            "total_count": total,
            "agents": { k: "completed" for k in ["research", "intent", "message", "timing", "logger"] }
        })
        print(f"Batch {batch_id} fully processed through LangGraph and synced to MongoDB.")
                
    except Exception as e:
        print(f"Error during Background Batch processing: {e}")
        await push_batch_log(batch_id, f"FATAL ERROR during batch processing: {str(e)}")
        await update_batch_progress(batch_id, { "status": "failed", "percent": 0 })

@router.post("/upload")
async def upload_batch(
    background_tasks: BackgroundTasks,
    agent_mapping: UploadFile = File(...),
    crm_pipeline: UploadFile = File(...),
    email_logs: UploadFile = File(...),
    leads_data: UploadFile = File(...),
    sales_pipeline: UploadFile = File(...),
    start_index: int = Form(None),
    end_index: int = Form(None),
    user=Depends(get_current_user)
):
    try:
        import uuid
        date_str = datetime.utcnow().strftime("%Y_%m_%d")
        short_id = str(uuid.uuid4())[:8].upper()
        batch_id = f"BATCH_{date_str}_{short_id}"
        
        batch_dir = os.path.join(BATCHES_DIR, batch_id)
        os.makedirs(batch_dir, exist_ok=True)
        
        company_id = user["company_id"]
        
        # Helper to read into RAM, dump to batch structure, and return records
        async def save_and_read_file(upload_file: UploadFile, filename: str):
            contents = await upload_file.read()
            df = pd.read_csv(io.BytesIO(contents))
            df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
            df.to_csv(os.path.join(batch_dir, filename), index=False)
            return df.to_dict('records')
            
        await save_and_read_file(agent_mapping, "Agent_Mapping.csv")
        crm_records = await save_and_read_file(crm_pipeline, "CRM_Pipeline.csv")
        email_records = await save_and_read_file(email_logs, "Email_Logs.csv")
        await save_and_read_file(leads_data, "Leads_Data.csv")
        sales_records = await save_and_read_file(sales_pipeline, "Sales_Pipeline.csv")
        
        # Save batch tracking doc
        await batches_collection.insert_one({
            "batch_id": batch_id,
            "company_id": company_id,
            "created_at": datetime.utcnow(),
            "status": "processing",
            "percent": 0,
            "error": None,
            "logs": [],
            "agents": { k: "pending" for k in ["research", "intent", "message", "timing", "logger"] }
        })

        # Bulk insert historical emails if present
        if email_records:
            for rec in email_records:
                rec["company_id"] = company_id
                rec["batch_id"] = batch_id
            await email_logs_collection.insert_many(email_records)
            
        # Bulk insert sales pipeline if present
        if sales_records:
            for rec in sales_records:
                rec["company_id"] = company_id
                rec["batch_id"] = batch_id
            await pipeline_collection.insert_many(sales_records)
        
        background_tasks.add_task(process_batch_background, str(company_id), batch_id, start_index, end_index)
        
        return {
            "batch_id": batch_id,
            "status": "processing",
            "files_received": 5
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Batch upload rejected: {str(e)}")
