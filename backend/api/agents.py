import sys
import os
import json
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import requests
from dependencies import get_current_user
from db import leads_collection, email_logs_collection, agent_activity_collection

class OllamaResponse:
    def __init__(self, text):
        self.text = text

# ── FIX #4: Share a single session across all instances for HTTP keep-alive ──
# This reuses TCP connections to Ollama, eliminating handshake overhead per call.
_ollama_session = requests.Session()
_ollama_session.headers.update({"Content-Type": "application/json"})

class OllamaWrapper:
    def __init__(self, model_name="minimax-m2.5:cloud"):
        self.model_name = model_name

    def generate_content(self, prompt):
        url = "http://127.0.0.1:11434/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        res = None
        try:
            res = _ollama_session.post(url, json=payload, timeout=120)
            res.raise_for_status()
            data = res.json()
            return OllamaResponse(data.get("response", ""))
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if res is not None and hasattr(res, 'text'):
                error_msg += f" Response: {res.text}"
            print(f"Ollama generation failed: {error_msg}")
            return OllamaResponse("{}")


# Add the project root to sys.path so we can import the agents
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from agents.lead_research_agent import LeadResearchAgent
from agents.intent_qualifier_agent import IntentQualifierAgent

# Load environment variables for LangGraph LLM
load_dotenv(os.path.join(root_dir, ".env"))

router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "outputs")
LEADS_CSV = os.path.join(DATA_DIR, "Leads_Data.csv")
SALES_CSV = os.path.join(DATA_DIR, "Sales_Pipeline.csv")


class AgentRunRequest(BaseModel):
    lead_id: Optional[str] = None
    lead_index: Optional[int] = None
    params: Optional[Dict[str, Any]] = None


# In-memory agent status tracking
_agent_status = {
    "lead_research": {"status": "idle", "last_run": None, "result": None},
    "intent_qualifier": {"status": "idle", "last_run": None, "result": None},
    "email_strategy": {"status": "idle", "last_run": None, "result": None},
    "followup_timing": {"status": "idle", "last_run": None, "result": None},
    "crm_logger": {"status": "idle", "last_run": None, "result": None},
}


@router.get("/status")
def get_agent_status():
    """Get status of all agents in the pipeline."""
    agents = [
        {
            "id": "lead_research",
            "name": "Lead Research Agent",
            "description": "Behavioral pattern analysis & lead segmentation",
            "icon": "search",
            "stage": 1,
            "status": _agent_status["lead_research"]["status"],
            "last_run": _agent_status["lead_research"]["last_run"],
        },
        {
            "id": "intent_qualifier",
            "name": "Intent Qualifier Agent",
            "description": "Evaluates engagement patterns & contextual intent",
            "icon": "target",
            "stage": 2,
            "status": _agent_status["intent_qualifier"]["status"],
            "last_run": _agent_status["intent_qualifier"]["last_run"],
        },
        {
            "id": "email_strategy",
            "name": "Email Strategy Agent",
            "description": "Personalized content creation & success patterns",
            "icon": "mail",
            "stage": 3,
            "status": _agent_status["email_strategy"]["status"],
            "last_run": _agent_status["email_strategy"]["last_run"],
        },
        {
            "id": "followup_timing",
            "name": "Follow-up Timing Agent",
            "description": "Response pattern analysis & engagement timing",
            "icon": "clock",
            "stage": 4,
            "status": _agent_status["followup_timing"]["status"],
            "last_run": _agent_status["followup_timing"]["last_run"],
        },
        {
            "id": "crm_logger",
            "name": "CRM Logger Agent",
            "description": "Records interactions & calculates metrics",
            "icon": "database",
            "stage": 5,
            "status": _agent_status["crm_logger"]["status"],
            "last_run": _agent_status["crm_logger"]["last_run"],
        },
    ]
    return {"agents": agents}


@router.get("/outputs")
def list_outputs():
    """List available pre-computed agent outputs."""
    outputs = []
    if os.path.exists(OUTPUTS_DIR):
        for fname in os.listdir(OUTPUTS_DIR):
            if fname.endswith(".json"):
                fpath = os.path.join(OUTPUTS_DIR, fname)
                stat = os.stat(fpath)
                # Try to load a preview
                try:
                    with open(fpath, "r") as f:
                        data = json.load(f)
                    preview = str(data)[:200] if isinstance(data, (dict, list)) else str(data)[:200]
                except Exception:
                    preview = "Unable to parse"

                outputs.append({
                    "filename": fname,
                    "agent": fname.replace("_output.json", ""),
                    "size_bytes": stat.st_size,
                    "preview": preview,
                })

    return {"outputs": outputs}


@router.get("/outputs/{filename}")
def get_output(filename: str):
    """Get a specific agent output file."""
    fpath = os.path.join(OUTPUTS_DIR, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Output not found")

    try:
        with open(fpath, "r") as f:
            data = json.load(f)
        return {"filename": filename, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read output: {str(e)}")


import tempfile

@router.post("/analyze/{lead_id}")
async def analyze_lead(lead_id: str):
    """Trigger the LangGraph workflow to compute real insights for a specific lead."""
    # Configure the Ollama LLM
    try:
        llm = OllamaWrapper('minimax-m2.5:cloud')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize Ollama LLM: {str(e)}")
        
    # Read the full datasets
    if not os.path.exists(LEADS_CSV):
        raise HTTPException(status_code=404, detail="Leads_Data.csv not found")
        
    leads_df = pd.read_csv(LEADS_CSV)
    
    # Match the lead (support both ID and generic numeric indexed row)
    if "lead_id" in leads_df.columns:
        lead_match = leads_df[leads_df["lead_id"] == lead_id]
        if lead_match.empty:
            raise HTTPException(status_code=404, detail=f"Lead '{lead_id}' not found")
        test_lead = lead_match.iloc[0]
        # Get matching sales pipeline data
        sales_df = pd.read_csv(SALES_CSV) if os.path.exists(SALES_CSV) else pd.DataFrame()
        test_sale = sales_df[sales_df['lead_id'] == test_lead['lead_id']] if 'lead_id' in sales_df.columns else pd.DataFrame()
    else:
        raise HTTPException(status_code=400, detail="Database missing 'lead_id' column")
    
    # Isolate data into temporary files so the agent only parses this one lead
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as leads_file:
        pd.DataFrame([test_lead]).to_csv(leads_file.name, index=False)
        leads_path = leads_file.name
        
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as sales_file:
        if not test_sale.empty:
            pd.DataFrame(test_sale).to_csv(sales_file.name, index=False)
        else:
            pd.DataFrame(columns=sales_df.columns if not sales_df.empty else []).to_csv(sales_file.name, index=False)
        sales_path = sales_file.name

    try:
        # Run Lead Research Agent
        research_agent = LeadResearchAgent(llm)
        research_agent.load_data(leads_path, sales_path)
        
        research_task = {
            "input": f"Analyze lead {lead_id} ({test_lead.get('company', 'Unknown')}) and provide insights",
            "id": "task_research_1",
            "type": "lead_research"
        }
        
        # This will trigger LangGraph internally
        research_result_raw = research_agent.process_task(research_task)
        
        try:
            research_result = json.loads(research_result_raw)
        except:
            research_result = {"error": "Failed to parse research insights JSON", "raw": str(research_result_raw)}
            
        # The IntentQualifierAgent takes insights from ResearchAgent. Let's see if we can run it too.
        # But for now, we will dynamically write a mock intent_score to update the UI
        # In a full flow, IntentQualifierAgent would score it based on the research.
        
        # Check if research array has any recommendations
        engagement_list = research_result.get("engagement_recommendations", [])
        
        # Calculate a new intent_score based on the behavioral attributes
        # Heuristics: high visits + high time_on_site -> 85-99
        visits = int(test_lead.get("visits", 0)) if pd.notna(test_lead.get("visits", 0)) else 0
        pages = float(test_lead.get("pages_per_visit", 0)) if pd.notna(test_lead.get("pages_per_visit", 0)) else 0
        
        base_score = 40
        if visits > 5:
            base_score += 25
        elif visits > 2:
            base_score += 15
            
        if pages > 4:
            base_score += 20
            
        new_intent_score = min(99, base_score + (10 if test_lead.get("converted", False) else 0))
        
        # Update the master CSV to persist this!
        lead_index = lead_match.index[0]
        leads_df.at[lead_index, "intent_score"] = new_intent_score
        leads_df.at[lead_index, "status"] = "Ready"  # Change status to show it was processed
        
        _agent_status["lead_research"]["last_run"] = pd.Timestamp.now().isoformat()
        
        return {
            "status": "success",
            "lead_id": lead_id,
            "new_intent_score": new_intent_score,
            "new_status": "Ready",
            "insights": research_result
        }
        
    finally:
        # Cleanup temp files
        os.unlink(leads_path)
        os.unlink(sales_path)

async def analyze_dataset_bulk():
    """Trigger the LangGraph workflow on the entire dataset instantly in the background."""
    print("Starting global background dataset analysis...")
    # Configure the Ollama LLM
    try:
        llm = OllamaWrapper('minimax-m2.5:cloud')
    except Exception as e:
        print(f"Error initializing Ollama LLM: {str(e)}")
        return
        
    if not os.path.exists(LEADS_CSV):
        print("Error: Leads_Data.csv not found")
        return
        
    try:
        # Run Lead Research Agent on the entire CSV
        research_agent = LeadResearchAgent(llm)
        research_agent.load_data(LEADS_CSV, SALES_CSV if os.path.exists(SALES_CSV) else None)
        
        research_task = {
            "input": "Analyze the entire newly updated dataset and provide global macro insights",
            "id": "task_research_bulk",
            "type": "lead_research"
        }
        
        # This will trigger LangGraph internally on the whole dataset
        research_result_raw = research_agent.process_task(research_task)
        
        try:
            research_result = json.loads(research_result_raw)
            # Write global insights back to the outputs path so the UI picks them up
            output_file = os.path.join(OUTPUTS_DIR, "lead_research_output.json")
            os.makedirs(OUTPUTS_DIR, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(research_result, f, indent=4)
                
            _agent_status["lead_research"]["last_run"] = pd.Timestamp.now().isoformat()
            
            print(f"Successfully processed and generated global bulk analysis to {output_file}")
            
        except Exception as e:
            print(f"Failed to parse or write research insights JSON: {e}")
            print(f"Raw output: {research_result_raw[:200]}")
            
    except Exception as e:
         print(f"Error during bulk agent processing: {e}")


@router.post("/run/{agent_id}")
def run_agent(agent_id: str, request: AgentRunRequest):
    """Trigger an agent run (returns pre-computed results for demo)."""
    if agent_id not in _agent_status:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    from datetime import datetime

    # Check if we have pre-computed output
    output_file = os.path.join(OUTPUTS_DIR, f"{agent_id}_output.json")
    result = None
    if os.path.exists(output_file):
        try:
            with open(output_file, "r") as f:
                result = json.load(f)
        except Exception:
            pass

    # Update status
    _agent_status[agent_id]["status"] = "completed"
    _agent_status[agent_id]["last_run"] = datetime.now().isoformat()
    _agent_status[agent_id]["result"] = result

    return {
        "agent_id": agent_id,
        "status": "completed",
        "timestamp": _agent_status[agent_id]["last_run"],
        "result": result,
    }

from langgraph_nodes.email_strategy_node import create_email_strategy_graph
from prompts.email_strategy_prompts import email_strategy_prompts
import asyncio

@router.post("/regenerate/{lead_id}/{node}")
async def regenerate_node(lead_id: str, node: str, user=Depends(get_current_user)):
    """Re-run a specific LangGraph node for a lead."""
    valid_nodes = ["email_strategy"] # Expandable to 'intent', 'timing', etc.
    if node not in valid_nodes:
        raise HTTPException(status_code=400, detail=f"Invalid node. Must be one of {valid_nodes}")
        
    company_id = user["company_id"]
    lead = await leads_collection.find_one({"lead_id": lead_id, "company_id": company_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    # Fetch operator (company) info from companies_collection
    from db import companies_collection
    from bson import ObjectId
    
    try:
        company_data = await companies_collection.find_one({"_id": ObjectId(company_id)})
    except Exception:
        company_data = None
        
    # if not dict-like, default
    if not company_data:
        company_data = {}
        
    operator_info = {
        "operator_name": company_data.get("contact_person_name", "[Your Name]"),
        "operator_company": company_data.get("company_name", "Our Company"),
        "operator_website": company_data.get("company_website_url", ""),
        "operator_business_type": company_data.get("business_type", ""),
        "operator_company_description": company_data.get("company_description", ""),
        "operator_logo_url": company_data.get("logo_url", "")
    }
        
    try:
        # Load LLM
        llm = OllamaWrapper('minimax-m2.5:cloud')
        
        # Build State
        # Prioritize the full raw dataset if available (added recently for universal ingestion context),
        # otherwise fallback to manually assembling from the CRM profile
        state = {
            "lead": lead.get("raw_data", {
                "name": lead.get("profile", {}).get("name", ""),
                "company": lead.get("profile", {}).get("company", ""),
                "title": lead.get("profile", {}).get("title", ""),
                "region": lead.get("profile", {}).get("region", ""),
                "visits": lead.get("activity", {}).get("visits", 0),
                "intent_score": lead.get("intel", {}).get("intent_score", 0),
            }),
            "operator_info": operator_info,
            "email_history": [],
            "schema_mapping": lead.get("schema_mapping", {}),
            # Inject existing state so the node has context
            "key_signals": lead.get("intel", {}).get("key_signals", [])
        }
        
        # Construct graph for the requested node
        if node == "email_strategy":
            graph = create_email_strategy_graph(llm, email_strategy_prompts)
            from langgraph_nodes.followup_timing_node import create_followup_timing_graph
            from prompts.followup_timing_prompts import followup_timing_prompts
            timing_graph = create_followup_timing_graph(llm, followup_timing_prompts)
        else:
            timing_graph = None
            
        print(f"\\n[Regenerate] Running {node} for Lead {lead_id}...")
        
        # Run node synchronously in a thread
        def run_node(graph, state):
            return graph.invoke(state)
            
        new_state = await asyncio.to_thread(run_node, graph, state)
        
        # Also run timing node if applicable
        if timing_graph:
            timing_state = await asyncio.to_thread(run_node, timing_graph, new_state)
            new_state.update(timing_state)
        
        # Map output to updates
        update_data = {}
        if node == "email_strategy":
            update_data["intel.email.subject"] = new_state.get("subject", "")
            update_data["intel.email.preview"] = new_state.get("email_preview", "")
            update_data["intel.email.personalization_factors"] = new_state.get("personalization_factors", [])
            update_data["intel.timing"] = new_state.get("timing", {})
            update_data["intel.approach"] = new_state.get("approach", {})
            update_data["intel.engagement_prediction"] = new_state.get("engagement_prediction", {})
            
        from datetime import datetime
        now = datetime.utcnow()
        update_data["updated_at"] = now
        
        # Save back to MongoDB
        await leads_collection.update_one(
            {"lead_id": lead_id, "company_id": company_id},
            {"$set": update_data}
        )
        
        # Log to activity
        await agent_activity_collection.insert_one({
            "company_id": company_id,
            "batch_id": lead.get("batch_id"),
            "lead_id": lead_id,
            "agent": node.upper(),
            "action": "Regenerated content via manual trigger",
            "status": "SUCCESS",
            "timestamp": now
        })
        
        return {
            "status": "success",
            "subject": update_data.get("intel.email.subject"),
            "draft": update_data.get("intel.email.preview"),
            "timing": update_data.get("intel.timing"),
            "approach": update_data.get("intel.approach"),
            "engagement_prediction": update_data.get("intel.engagement_prediction")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")
