import os
import io
import sys
import re

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
from typing import List, Optional
import asyncio
from bson import ObjectId

# Import dependencies and DB collections
from dependencies import get_current_user
from db import batches_collection, leads_collection, pipeline_collection, email_logs_collection, agent_activity_collection, companies_collection

# Import Ollama wrapper + channel-draft helpers (used in pipeline auto-generation)
from api.agents import OllamaWrapper, _build_channel_prompt, _channel_draft_async, _extract_channel_media

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



async def process_batch_background(company_id_str: str, batch_id: str, start_index: int = None, end_index: int = None, saved_file_paths: Optional[list] = None):
    """ 
    Background worker that:
      1. Runs the Data Discovery Agent (so the upload endpoint returns instantly)
      2. Uses LangGraph to process each lead concurrently, writing results to MongoDB.
    """
    try:
        await asyncio.sleep(0.5) # Brief yield so the HTTP response is sent first
        company_id = ObjectId(company_id_str)

        # ── FIX #2: Run Data Discovery here (background), not in the upload handler ──
        if saved_file_paths:
            from agents.data_discovery_agent import DataDiscoveryAgent
            await push_batch_log(batch_id, "Running Data Discovery Agent...")
            llm_discovery = OllamaWrapper()
            agent = DataDiscoveryAgent(llm_discovery)
            # Run synchronous LLM call in a thread so we don't block the event loop
            discovery_result = await asyncio.to_thread(agent.analyze_data_sources, saved_file_paths)
            await batches_collection.update_one(
                {"batch_id": batch_id},
                {"$set": {"discovery_result": discovery_result}}
            )
            await push_batch_log(batch_id, "Data Discovery complete. Starting lead pipeline...")
        
        # Fetch batch to get discovery results
        batch_doc = await batches_collection.find_one({"batch_id": batch_id})
        discovery = batch_doc.get("discovery_result", {})
        
        # === VALIDATION FIX: Check if the data is actually usable before proceeding ===
        is_sufficient = discovery.get("is_sufficient", True)
        if not is_sufficient:
            error_reason = discovery.get("reasoning", "The uploaded CSV does not contain enough actionable fields (e.g. missing identities or behavioral metrics) to run the AI pipeline.")
            print(f"[Validation Failed] {error_reason}")
            await update_batch_progress(batch_id, {
                "status": "failed",
                "error": f"Insufficient Data: {error_reason}"
            })
            return
            
        schema_mapping = discovery.get("schema_mapping", {})
        files_roles = discovery.get("files_roles", {})
        
        primary_file = files_roles.get("primary_leads_file") or "Leads_Data.csv"
        email_file = files_roles.get("email_history_file") or "Email_Logs.csv"
        
        batch_dir = os.path.join(BATCHES_DIR, batch_id)
        
        leads_file = os.path.join(batch_dir, os.path.basename(primary_file))
        emails_file = os.path.join(batch_dir, os.path.basename(email_file)) if email_file else None
        
        if not os.path.exists(leads_file):
            # Fallback to first csv
            csvs = [f for f in os.listdir(batch_dir) if f.endswith('.csv')]
            if csvs:
                leads_file = os.path.join(batch_dir, csvs[0])
            else:
                await update_batch_progress(batch_id, { "status": "failed", "error": "Leads file missing" })
                return
            
        df = pd.read_csv(leads_file)
        emails_df = pd.read_csv(emails_file) if emails_file and os.path.exists(emails_file) else pd.DataFrame()
        
        original_total = len(df)
        start_idx = start_index if start_index is not None and start_index >= 0 else 0
        end_idx = end_index if end_index is not None and end_index > start_idx else original_total
        end_idx = min(end_idx, original_total)
        
        df_to_process = df.iloc[start_idx:end_idx].copy()
        total = len(df_to_process)
        
        # Load the Ollama LLM
        llm = OllamaWrapper()
        
        # Compile pipelines (once per batch, shared across all leads)
        agents = {
            'research': create_lead_research_graph(llm, lead_research_prompts),
            'intent': create_intent_qualifier_graph(llm, intent_qualifier_prompts),
            'email': create_email_strategy_graph(llm, email_strategy_prompts),
            'timing': create_followup_timing_graph(llm, followup_timing_prompts),
            'logger': create_crm_logger_graph()
        }

        # ── FIX #3: Fetch company doc ONCE before the loop ──
        company_doc = await companies_collection.find_one({"_id": company_id})
        operator_info = {}
        if company_doc:
            operator_info = {
                "operator_name": company_doc.get("contact_person_name", company_doc.get("company_name", "Unknown Operator")),
                "operator_company": company_doc.get("company_name", "Unknown Company"),
                "operator_website": company_doc.get("domain", "") or company_doc.get("website", ""),
                "operator_email": company_doc.get("email", "")
            }
        
        start_msg = f"Processing subset of {total} leads (rows {start_idx} to {end_idx-1})" if total < original_total else f"Processing all {total} leads"
        print(f"[Batch] {start_msg} | Batch ID: {batch_id}", flush=True)
        await push_batch_log(batch_id, f"Starting pipeline: {start_msg}")
        await update_batch_progress(batch_id, {
            "percent": 0,
            "processed_count": 0,
            "total_count": total,
            "agents": { k: "pending" for k in ["research", "intent", "message", "timing", "logger"] },
            "message": start_msg
        })
        
        processed = 0
        semaphore = asyncio.Semaphore(3)  # Limit concurrent LangGraph executions (reduced from 5 to avoid Ollama overload)


        def safe_num(val, default=0, as_float=False):
            """Safely convert a value to int/float. Handles pipe-separated strings like '8 | 5 | 4'."""
            if val is None or (hasattr(val, '__class__') and val.__class__.__name__ == 'float' and str(val) == 'nan'):
                return float(default) if as_float else int(default)
            s = str(val).split('|')[0].split(',')[0].strip()
            try:
                return float(s) if as_float else int(float(s))
            except (ValueError, TypeError):
                return float(default) if as_float else int(default)

        def get_mapped_val(row, mapping_key, default=None, is_list=False):
            """Helper to extract values from row based on schema mapping keys"""
            cols = []
            if isinstance(mapping_key, str):
                cols = [c.strip() for c in mapping_key.split(",") if c.strip()]
            elif isinstance(mapping_key, list):
                cols = mapping_key
            
            # Find the actual column in the row (case-insensitive)
            row_cols_lower = {c.lower(): c for c in row.index}
            
            found_vals = []
            for col in cols:
                actual_col = row_cols_lower.get(col.lower())
                if actual_col and pd.notna(row[actual_col]):
                    val = row[actual_col]
                    if is_list:
                        # Use robust regex to find all URLs regardless of delimiter
                        val_str = str(val)
                        urls = re.findall(r'https?://[^\s,|;<>\"\'\[\]\(\)\{\}]+', val_str)
                        for url in urls:
                            # Clean up trailing punctuation that might be caught by regex
                            clean_url = re.sub(r'[,;\"\'\)\]\s\.]+$', '', url)
                            if clean_url and clean_url not in found_vals:
                                found_vals.append(clean_url)

                    else:
                        return val
            
            return found_vals if is_list else default

        async def process_single_lead(index, row, _operator_info=operator_info):
            nonlocal processed
            
            # Use dynamic mapping to get core fields
            lead_id_col = schema_mapping.get("lead_id", "lead_id")
            lead_id = str(get_mapped_val(row, lead_id_col, f"L{index}"))
            
            # Identity - support common aliases
            # Try split first/last name columns
            first_name = get_mapped_val(row, ["First_Name", "First Name", "firstname", "first_name", "first"], "")
            last_name = get_mapped_val(row, ["Last_Name", "Last Name", "lastname", "last_name", "last"], "")
            
            full_name = f"{first_name} {last_name}".strip()
            if not full_name:
                # Try common single full-name columns directly (handles CSVs with a plain "name" column)
                full_name = get_mapped_val(row, ["name", "Name", "Full Name", "full_name", "FullName", "user_name", "User", "Customer Name"], "")
            if not full_name:
                # Last resort: use identity_fields from schema_mapping, but skip values that look like IDs
                identity_cols = schema_mapping.get("identity_fields", [])
                if isinstance(identity_cols, list):
                    for col in identity_cols:
                        val = get_mapped_val(row, [col], "")
                        val_str = str(val).strip()
                        # Skip empty values, values that look like IDs (e.g. "L_JX_001"), or "lead_id" columns
                        if val_str and not val_str.startswith("L_") and col.lower() not in ("lead_id", "id", "email"):
                            full_name = val_str
                            break
            if not full_name:
                full_name = "Lead"
            
            email = get_mapped_val(row, ["Email", "email", "Email_Address", "Email Address"], "contact@unknown.com")
            
            # Behavior - needed for company inference
            behavior = schema_mapping.get("behavioral_fields", {})
            content_links_mapping = behavior.get("content_links", "page_link")
            aggregated_links = get_mapped_val(row, content_links_mapping, is_list=True)

            # --- SMART MAPPING: Handle Company/Organization ---
            # 1. Try explicit columns and mapping
            company_mapped = get_mapped_val(row, ["Company", "Organization", "Account", "Employer", "Brand", "Business", "entity"], None)
            
            # 2. B2C Fallback: Infer from product links (e.g. tiffany.com -> Tiffany)
            if not company_mapped or str(company_mapped).lower() == "unknown":
                from urllib.parse import urlparse
                for link in aggregated_links:
                    if str(link).startswith("http") and "." in str(link):
                        domain = urlparse(str(link)).netloc
                        if domain:
                            domain_part = domain.replace("www.", "").split(".")[0]
                            if len(domain_part) > 2: # filter out tiny domains
                                company_mapped = domain_part.capitalize()
                                break
            
            # 3. Batch Level Fallback: Use the identified business name from discovery
            if not company_mapped or str(company_mapped).lower() == "unknown":
                company_mapped = discovery.get("business_context", {}).get("company_name", "Organization")

            # --- SMART MAPPING: Handle Title/Role ---
            title = get_mapped_val(row, ["Title", "Job", "Position", "Role", "job_title", "Occupation"], None)
            if not title or str(title).lower() == "unknown":
                # Industry-aware title generation
                industry_hint = str(discovery.get("business_context", {}).get("industry", "generic")).lower()
                if any(x in industry_hint for x in ["ecommerce", "e-commerce", "retail", "shop"]):
                    title = "Customer"
                elif any(x in industry_hint for x in ["book", "publish", "read"]):
                    title = "Reader"
                elif any(x in industry_hint for x in ["boat", "marine", "sail"]):
                    title = "Enthusiast" # User requested enthusiast for boats
                elif any(x in industry_hint for x in ["jewelry", "luxury", "diamond", "tiffany"]):
                    title = "Luxury Enthusiast"
                else:
                    title = "Professional" # Default for B2B

            region = get_mapped_val(row, ["Region", "City", "State", "Country", "Location"], "Global")
            lead_source = get_mapped_val(row, ["Lead_Source", "Source", "UTM_Source", "Medium"], "Direct")
            industry = get_mapped_val(row, ["Industry", "Sector", "Niche"], discovery.get("business_context", {}).get("industry", "Business"))
            
            # Behavior
            behavior = schema_mapping.get("behavioral_fields", {})
            visits = safe_num(get_mapped_val(row, behavior.get("visits", "visits"), 0))
            time_spent = safe_num(get_mapped_val(row, behavior.get("time_on_site", "time_on_site"), 0.0), as_float=True)
            pages = safe_num(get_mapped_val(row, behavior.get("depth", "pages_per_visit"), 0.0), as_float=True)
            
            # Sales/Stage
            sales = schema_mapping.get("sales_fields", {})
            purchased_val = get_mapped_val(row, sales.get("stage", "Lead_Status"), "")
            converted = str(purchased_val).lower() in ["yes", "customer", "won", "purchased", "active"]
            deal_value = safe_num(get_mapped_val(row, sales.get("value", "Purchase_Value"), 0.0), as_float=True)

            # Aggregate product links from multiple columns
            content_links_mapping = behavior.get("content_links", "page_link")
            # Be inclusive: check mapped column AND common fallbacks (especially history columns)
            search_cols = ["Product_Pages_Viewed", "Product Pages Viewed", "product_link", "url", "page_link", "landing_page", "Pages_Visited"]
            if isinstance(content_links_mapping, str) and content_links_mapping not in search_cols:
                search_cols.insert(0, content_links_mapping)
            
            aggregated_links = get_mapped_val(row, search_cols, is_list=True)
            
            cleaned_links = []
            for link in aggregated_links:
                l = str(link).strip()
                if ("://" in l or ("." in l and "/" in l)) and len(l) > 8:
                    l = re.sub(r'[,;\"\'\s\.]+$', '', l)
                    if l and l not in cleaned_links:
                        cleaned_links.append(l)


            # Aggregate product images from multiple columns
            common_image_cols = ["Product Image", "image_url", "image", "product_image", "media_url", "picture", "thumbnail"]
            aggregated_images = get_mapped_val(row, common_image_cols, is_list=True)
            cleaned_images = []
            for img in aggregated_images:
                i = str(img).strip()
                if ("://" in i) and len(i) > 8:
                    i = re.sub(r'[,;\"\'\s]+$', '', i)
                    if i not in cleaned_images:
                        cleaned_images.append(i)

            
            lead_dict = row.to_dict()
            lead_dict["lead_id"] = lead_id
            lead_dict["name"] = full_name
            lead_dict["email"] = email
            lead_dict["title"] = title
            lead_dict["company"] = company_mapped
            lead_dict["industry"] = industry
            lead_dict["page_link"] = cleaned_links # Standardize for LangGraph
            lead_dict["image_url"] = cleaned_images
            lead_dict["visits"] = visits
            lead_dict["time_on_site"] = time_spent
            lead_dict["pages_per_visit"] = pages
            lead_dict["converted"] = converted
            
            # ── PRE-INGESTION: Save leads as 'Processing' immediately so UI isn't empty ──
            # Also pre-populate scraped_media if images are found in CSV
            csv_scraped_media = []
            for idx, link in enumerate(cleaned_links):
                img = cleaned_images[idx] if idx < len(cleaned_images) else None
                csv_scraped_media.append({
                    "url": link,
                    "image": img,
                    "name": link.split("/")[-1].replace(".html", "").replace("-", " ").title() or "Product"
                })

            await leads_collection.update_one(
                {"lead_id": lead_id, "batch_id": batch_id},
                {
                    "$set": {
                        "company_id": company_id,
                        "profile": {
                            "name": full_name,
                            "email": email,
                            "title": title,
                            "company": company_mapped,
                            "industry": industry,
                            "region": region,
                            "lead_source": lead_source,
                            "image_url": cleaned_images[0] if cleaned_images else None,
                            "all_images": cleaned_images
                        },

                        "intel": {
                            "scraped_media": csv_scraped_media,
                            "status": "extracting"
                        },
                        "page_link": cleaned_links,
                        "raw_data": lead_dict,
                        "status": "Processing",
                        "updated_at": datetime.utcnow()

                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )


            async with semaphore:
                if not emails_df.empty and 'lead_id' in emails_df.columns:
                    email_history = emails_df[emails_df['lead_id'] == lead_id].to_dict('records')
                else:
                    email_history = []
                    
                state = {
                    "lead": lead_dict, 
                    "email_history": email_history, 
                    "operator_info": _operator_info,   # ── FIX #3: pre-fetched once
                    "schema_mapping": schema_mapping
                }
                
                # Use mapping to find company name for logs
                company_col = schema_mapping.get("identity_fields", ["company"])[0] if schema_mapping.get("identity_fields") else 'company'
                company_name = lead_dict.get(company_col, lead_dict.get('company', 'Unknown'))
                print(f"\\n[Processing] Lead {lead_id} ({company_name}) through LangGraph pipeline...")
                await push_batch_log(batch_id, f"Initializing pipeline for {company_name} (Lead ID: {lead_id})")
                
                try:
                    # ── Real-time per-agent status: update MongoDB as each node starts/finishes ──
                    # Each lead runs concurrently, so we only update the batch-level agent status
                    # when the FIRST lead starts/completes each stage (non-blocking best-effort).

                    print(f"[Batch] Running lead {lead_id} ({company_name}) — Agent 1/5: Research", flush=True)
                    await push_batch_log(batch_id, f"[{company_name}] Running Agent: [1/5] Lead Web Research...")
                    await batches_collection.update_one({"batch_id": batch_id}, {"$set": {"agents.research": "running"}}, upsert=False)
                    state = await asyncio.to_thread(agents['research'].invoke, state)
                    await batches_collection.update_one({"batch_id": batch_id}, {"$set": {"agents.research": "completed"}}, upsert=False)

                    print(f"[Batch] Lead {lead_id} — Agent 2/5: Intent", flush=True)
                    await push_batch_log(batch_id, f"[{company_name}] Running Agent: [2/5] Intent Qualification...")
                    await batches_collection.update_one({"batch_id": batch_id}, {"$set": {"agents.intent": "running"}}, upsert=False)
                    state = await asyncio.to_thread(agents['intent'].invoke, state)
                    await batches_collection.update_one({"batch_id": batch_id}, {"$set": {"agents.intent": "completed"}}, upsert=False)

                    print(f"[Batch] Lead {lead_id} — Agent 3/5: Email Strategy", flush=True)
                    await push_batch_log(batch_id, f"[{company_name}] Running Agent: [3/5] Email Strategy Formulation...")
                    await batches_collection.update_one({"batch_id": batch_id}, {"$set": {"agents.message": "running"}}, upsert=False)
                    state = await asyncio.to_thread(agents['email'].invoke, state)
                    await batches_collection.update_one({"batch_id": batch_id}, {"$set": {"agents.message": "completed"}}, upsert=False)

                    print(f"[Batch] Lead {lead_id} — Agent 4/5: Follow-up Timing", flush=True)
                    await push_batch_log(batch_id, f"[{company_name}] Running Agent: [4/5] Follow-up Timing Optimization...")
                    await batches_collection.update_one({"batch_id": batch_id}, {"$set": {"agents.timing": "running"}}, upsert=False)
                    state = await asyncio.to_thread(agents['timing'].invoke, state)
                    await batches_collection.update_one({"batch_id": batch_id}, {"$set": {"agents.timing": "completed"}}, upsert=False)

                    print(f"[Batch] Lead {lead_id} — Agent 5/5: CRM Logger", flush=True)
                    await push_batch_log(batch_id, f"[{company_name}] Running Agent: [5/5] CRM Serialization...")
                    await batches_collection.update_one({"batch_id": batch_id}, {"$set": {"agents.logger": "running"}}, upsert=False)
                    state = await asyncio.to_thread(agents['logger'].invoke, state)
                    await batches_collection.update_one({"batch_id": batch_id}, {"$set": {"agents.logger": "completed"}}, upsert=False)
                    
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
                                    "industry": lead_dict.get("industry"),
                                    "image_url": lead_dict.get("image_url", [None])[0] if lead_dict.get("image_url") else None,
                                    "all_images": lead_dict.get("image_url", [])
                                },
                                "page_link": lead_dict.get("page_link", []),
                                "contact": {
                                    "email": lead_dict.get("email", ""),
                                    "linkedin": lead_dict.get("linkedin", "")
                                },
                                "activity": {
                                    "visits": visits,
                                    "time_on_site": time_spent,
                                    "pages_per_visit": pages,
                                    "converted": converted
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
                                    "scraped_media": state.get("scraped_media", []),
                                    "timing": state.get("timing", {}),
                                    "approach": state.get("approach", {}),
                                    "engagement_prediction": state.get("engagement_prediction", {})
                                },
                                "crm": {
                                    "email_sent": False,
                                    "timeline": state.get("timeline", {}),
                                    "deal_value": deal_value,
                                    "stage": state.get("crm_stage", purchased_val if purchased_val else "prospect"),
                                },
                                "raw_data": lead_dict,
                                "schema_mapping": schema_mapping,
                                "status": "Completed",
                                "updated_at": datetime.utcnow()
                            },
                            "$setOnInsert": {"created_at": datetime.utcnow()}
                        },
                        upsert=True
                    )
                    
                    # ── AUTO MULTI-CHANNEL DRAFT GENERATION ─────────────────────────────────────
                    # After the 5-node pipeline, automatically generate SMS/WhatsApp/Voice drafts
                    # so users don't need to trigger them manually. Each channel is attempted
                    # independently — failure on one does NOT affect the others or the lead.
                    await push_batch_log(batch_id, f"[{company_name}] Auto-generating multi-channel drafts (SMS / WhatsApp / Voice)...")

                    # Fetch the fully-saved lead doc so _build_channel_prompt has all intel/profile fields
                    saved_lead_doc = await leads_collection.find_one({"lead_id": lead_id, "batch_id": batch_id})

                    if saved_lead_doc:
                        from db import channel_settings_collection
                        cfg = await channel_settings_collection.find_one({"company_id": company_id}) or {}
                        all_links, all_images = _extract_channel_media(saved_lead_doc)
                        page_link = all_links[0] if all_links else ""
                        img_url = all_images[0] if all_images else ""

                        for ch in ("sms", "whatsapp", "voice"):
                            try:
                                custom_prompt = cfg.get(f"{ch}_prompt")
                                has_image = bool(all_images)
                                ch_prompt = _build_channel_prompt(ch, saved_lead_doc, sender_company=company_name, custom_prompt=custom_prompt, has_image=has_image)
                                ch_draft = await _channel_draft_async(ch_prompt)

                                if ch == "sms" and ch_draft:
                                    ch_draft = ch_draft[:160]  # SMS hard limit
                                if ch_draft:
                                    await leads_collection.update_one(
                                        {"lead_id": lead_id, "batch_id": batch_id},
                                        {"$set": {
                                            f"intel.channels.{ch}.draft":    ch_draft,
                                            f"intel.channels.{ch}.sent":     False,
                                            f"intel.channels.{ch}.image_url": img_url,
                                            f"intel.channels.{ch}.page_link": page_link,
                                            f"intel.channels.{ch}.all_images": all_images,
                                            f"intel.channels.{ch}.all_links": all_links,

                                        }}
                                    )
                                    await push_batch_log(batch_id, f"[{company_name}] ✓ {ch.upper()} draft ready")
                                else:
                                    await push_batch_log(batch_id, f"[{company_name}] ⚠ {ch.upper()} draft was empty — skipped")
                            except Exception as ch_err:
                                safe_ch_err = str(ch_err).encode('utf-8', errors='replace').decode('utf-8')
                                await push_batch_log(batch_id, f"[{company_name}] ⚠ {ch.upper()} draft failed: {safe_ch_err}")

                    # Log activity
                    await agent_activity_collection.insert_one({
                        "company_id": company_id,
                        "batch_id": batch_id,
                        "lead_id": lead_id,
                        "agent": "PIPELINE",
                        "action": "Completed 5-node AI analysis + multi-channel draft generation",
                        "status": "SUCCESS",
                        "timestamp": datetime.utcnow()
                    })
                    print(f"[Batch] ✓ Lead {lead_id} ({company_name}) fully complete.", flush=True)
                    await push_batch_log(batch_id, f"SUCCESS: Completed full pipeline (5-node + 3 channels) for {company_name}")

                except Exception as e:
                    # Sanitize the error message — strip any unencodable Unicode chars
                    safe_err = str(e).encode('utf-8', errors='replace').decode('utf-8')
                    print(f"[Batch] ✗ Lead {lead_id} FAILED: {safe_err}", flush=True)
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

        # Build all coroutines and run them concurrently (semaphore limits to 5 at a time)
        tasks = [process_single_lead(index, row) for index, row in df_to_process.iterrows()]
        print(f"[Batch] Launching {len(tasks)} lead tasks concurrently (semaphore=5)...", flush=True)
        if not tasks:
            print(f"[Batch] WARNING: No leads to process! Check CSV row range (start={start_idx}, end={end_idx}) and file: {leads_file}", flush=True)
            await push_batch_log(batch_id, f"WARNING: 0 leads found to process. CSV has {original_total} rows. Check start/end index settings.")
        await asyncio.gather(*tasks)
            
        # Finish
        await update_batch_progress(batch_id, {
            "status": "completed",
            "percent": 100,
            "processed_count": total,
            "total_count": total,
            "agents": { k: "completed" for k in ["research", "intent", "message", "timing", "logger"] }
        })
        print(f"[Batch] ✓ Batch {batch_id} complete. {total} leads processed.", flush=True)
                
    except Exception as e:
        print(f"Error during Background Batch processing: {e}")
        await push_batch_log(batch_id, f"FATAL ERROR during batch processing: {str(e)}")
        await update_batch_progress(batch_id, { "status": "failed", "percent": 0 })

@router.post("/upload")
async def upload_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    start_index: int = Form(None),
    end_index: int = Form(None),
    user=Depends(get_current_user)
):
    try:
        date_str = datetime.utcnow().strftime("%Y_%m_%d")
        import uuid
        import shutil
        short_id = str(uuid.uuid4())[:8].upper()
        batch_id = f"BATCH_{date_str}_{short_id}"
        
        batch_dir = os.path.join(BATCHES_DIR, batch_id)
        os.makedirs(batch_dir, exist_ok=True)
        
        company_id = user["company_id"]
        company_id_str = str(user["company_id"])

        saved_file_paths = []
        for file in files:
            file_path = os.path.join(batch_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_file_paths.append(file_path)

        # ── FIX #2: Save the batch doc immediately (no blocking LLM call here) ──
        # Discovery will run as the FIRST step inside the background task.
        await batches_collection.insert_one({
            "batch_id": batch_id,
            "company_id": company_id,
            "created_at": datetime.utcnow(),
            "status": "processing",
            "percent": 0,
            "error": None,
            "logs": [f"[{datetime.utcnow().strftime('%H:%M:%S')}] Files uploaded. Queuing discovery & pipeline..."],
            "agents": { k: "pending" for k in ["research", "intent", "message", "timing", "logger"] },
            "discovery_result": {}
        })

        # Pass saved_file_paths into background so discovery runs there
        background_tasks.add_task(
            process_batch_background,
            company_id_str, batch_id, start_index, end_index, saved_file_paths
        )
        
        return {
            "batch_id": batch_id,
            "status": "processing",
            "message": "Files received. Discovery & processing started in background."
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Batch upload rejected: {str(e)}")
