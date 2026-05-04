import sys
import os
import json
from datetime import datetime, timezone
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import requests

# Add project root to sys.path so we can import 'prompts' and 'langgraph_nodes'
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_path not in sys.path:
    sys.path.append(root_path)

from dependencies import get_current_user
from bson import ObjectId
from db import leads_collection, email_logs_collection, agent_activity_collection, channel_settings_collection, companies_collection
from prompts.channel_outreach_prompts import channel_outreach_prompts
from prompts.email_strategy_prompts import email_strategy_prompts
from langgraph_nodes.email_strategy_node import create_email_strategy_graph
from services.twilio_service import TwilioService

class OllamaResponse:
    def __init__(self, text):
        self.text = text

OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "minimax-m2.5:cloud")

# ── FIX #4: Share a single session across all instances for HTTP keep-alive ──
# This reuses TCP connections to Ollama, eliminating handshake overhead per call.
_ollama_session = requests.Session()
_ollama_session.headers.update({"Content-Type": "application/json"})

import time as _time

class OllamaWrapper:
    def __init__(self, model_name=OLLAMA_MODEL):
        self.model_name = model_name

    def generate_content(self, prompt):
        url = f"{OLLAMA_URL}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }

        
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            res = None
            try:
                res = _ollama_session.post(url, json=payload, timeout=180) # Increased timeout to 180s
                res.raise_for_status()
                data = res.json()
                return OllamaResponse(data.get("response", ""))
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                error_msg = str(e)
                if res is not None and hasattr(res, 'text'):
                    error_msg += f" Response: {res.text}"
                
                print(f"Ollama attempt {attempt + 1} failed: {error_msg}")
                
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay}s...")
                    _time.sleep(retry_delay)
                    retry_delay *= 2 # Exponential backoff
                else:
                    print(f"Ollama generation failed after {max_retries} attempts.")
                    return OllamaResponse("{}")
        
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
DEFAULT_FALLBACK_PHONE = "+917777039470"


class AgentRunRequest(BaseModel):
    lead_id: Optional[str] = None
    lead_index: Optional[int] = None
    params: Optional[Dict[str, Any]] = None


# In-memory agent status tracking
_agent_status = {
    "lead_research":      {"status": "idle", "last_run": None, "result": None},
    "intent_qualifier":   {"status": "idle", "last_run": None, "result": None},
    "email_strategy":     {"status": "idle", "last_run": None, "result": None},
    "followup_timing":    {"status": "idle", "last_run": None, "result": None},
    "crm_logger":         {"status": "idle", "last_run": None, "result": None},
    "sms_agent":          {"status": "idle", "last_run": None, "result": None},
    "whatsapp_agent":     {"status": "idle", "last_run": None, "result": None},
    "voice_agent":        {"status": "idle", "last_run": None, "result": None},
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
        {
            "id": "sms_agent",
            "name": "SMS Outreach Agent",
            "description": "AI personalizes & sends SMS based on behavioral data",
            "icon": "sms",
            "stage": 6,
            "status": _agent_status["sms_agent"]["status"],
            "last_run": _agent_status["sms_agent"]["last_run"],
        },
        {
            "id": "whatsapp_agent",
            "name": "WhatsApp Agent",
            "description": "AI drafts & sends WhatsApp messages per lead",
            "icon": "chat",
            "stage": 7,
            "status": _agent_status["whatsapp_agent"]["status"],
            "last_run": _agent_status["whatsapp_agent"]["last_run"],
        },
        {
            "id": "voice_agent",
            "name": "AI Voice Call Agent",
            "description": "Generates personalized call script & initiates Twilio voice call",
            "icon": "record_voice_over",
            "stage": 8,
            "status": _agent_status["voice_agent"]["status"],
            "last_run": _agent_status["voice_agent"]["last_run"],
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
    _agent_status[agent_id]["last_run"] = datetime.now(timezone.utc).isoformat()
    _agent_status[agent_id]["result"] = result

    return {
        "agent_id": agent_id,
        "status": "completed",
        "timestamp": _agent_status[agent_id]["last_run"],
        "result": result,
    }

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
                "page_link": lead.get("page_link", []), # CRITICAL: Pass the existing links!
                "all_images": lead.get("profile", {}).get("all_images", []),
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
        update_data["intel.email.subject"] = new_state.get("subject", "")
        update_data["intel.email.preview"] = new_state.get("email_preview", "")
        update_data["intel.email.personalization_factors"] = new_state.get("personalization_factors", [])
        update_data["intel.scraped_media"] = new_state.get("scraped_media", [])
        update_data["intel.timing"] = new_state.get("timing", {})
        update_data["intel.approach"] = new_state.get("approach", {})
        update_data["intel.engagement_prediction"] = new_state.get("engagement_prediction", {})
        
        now = datetime.now(timezone.utc)
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
            "scraped_media": update_data.get("intel.scraped_media"),
            "timing": update_data.get("intel.timing"),
            "approach": update_data.get("intel.approach"),
            "engagement_prediction": update_data.get("intel.engagement_prediction")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
#  CHANNEL AGENTS — Stage 6/7/8 pipeline extensions
#  Uses same OllamaWrapper as all other pipeline agents (minimax-m2.5:cloud)
#  Prompts are fully personalized using behavioral + profile data
# ══════════════════════════════════════════════════════════════════════════════

import asyncio as _asyncio


def _ollama_draft(prompt: str) -> str:
    """Use the existing OllamaWrapper (same model as all pipeline agents)."""
    llm = OllamaWrapper("minimax-m2.5:cloud")
    resp = llm.generate_content(prompt)
    text = (resp.text or "").strip()
    
    # ── Comprehensive metadata-stripping pipeline ─────────────────────────────
    import re

    # 1. Remove markdown headers (e.g., # WhatsApp Message, ## Block 1)
    text = re.sub(r'^#+\s*.*$', '', text, flags=re.MULTILINE)

    # 2. Remove block/section labels (e.g., **Block 1: Greeting**, *CTA:*, **Sign-off**)
    text = re.sub(r'(?i)^\**\s*Block\s*\d+[\s:–\-]*.*?\**\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^\**\s*(Greeting|Value\s*Prop|Hook|CTA|Soft\s*CTA|Sign[\s\-]?off|Introduction|Body|Closing)[\s:–]+.*?\**\s*$', '', text, flags=re.MULTILINE)

    # 3. Remove echoed prompt labels on their own line (e.g., "Final Message:", "WhatsApp Message:")
    text = re.sub(r'(?i)^(📱\s*)?(Final\s*)?(WhatsApp\s*Message|SMS(\s*Message)?|Voice\s*Script|Message|Script|Draft|Output|Response|Personalized\s*Message)\s*:?\s*$', '', text, flags=re.MULTILINE)

    # 4. Remove "Here is / Here's / Below is / I've written" lead-in lines
    text = re.sub(r"(?i)^(here\s+(is|are|'?s)|below\s+is|i'?ve?\s+(written|crafted|drafted|created|prepared)|i\s+have\s+(written|crafted|drafted|created|prepared))\b[^\n]*\n?", '', text, flags=re.MULTILINE)

    # 5. Remove bold **Message:** / **WhatsApp Message:** inline headers
    text = re.sub(r'(?i)\*\*(WhatsApp\s*Message|SMS\s*Message|Voice\s*Script|Message|Draft|Script)\*\*\s*:?\s*', '', text)

    # 6. Remove horizontal dividers (---, ***, ___)
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # 7. Truncate at "Notes:", "Tip:", "Suggestion:", "Important:", "P.S.:"
    text = re.split(r'(?i)(\*\*|💡|📝|⚠️)?\s*(Notes?|Tips?|Suggestions?|Important|Reminder|P\.?S\.?)\s*:', text)[0]

    # 8. Remove trailing meta-questions and commentary
    text = re.sub(r'(?i)(\*?\s*)?(Would you like me to|Should I|Do you want me to|Feel free to|Let me know if you|I hope this (helps|works)|Is there anything).*$', '', text, flags=re.DOTALL)

    # 9. Remove common standalone label prefixes at very start of text
    text = re.sub(r'(?i)^(📱\s*)?WhatsApp\s*Message\s*:?\s*', '', text.lstrip())
    text = re.sub(r'(?i)^(💬\s*)?SMS(\s*Message)?\s*:?\s*', '', text.lstrip())
    text = re.sub(r'(?i)^(Final\s+)?(Message|Script|Draft|Output)\s*:?\s*', '', text.lstrip())
    text = re.sub(r'(?i)^Personalized\s*Message\s*:?\s*', '', text.lstrip())

    # 10. Fix double greeting: "Hey Grace, **Hi Grace!**" → strip outer "Hey Grace,"
    text = re.sub(r'^Hey\s+[A-Z][a-z]+,?\s*(?=\**(?:Hi|Hello|Hey))', '', text, flags=re.IGNORECASE)

    # 11. Replace unfilled placeholders
    text = text.replace('[Your Name]', 'The Team')
    text = re.sub(r'\[Phone\s*Number\]|\[Email(\s*Address)?\]|\[Link\]|\[Company\s*Name\]', '', text, flags=re.IGNORECASE)

    # 12. Collapse 3+ consecutive blank lines into a single blank line
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Final trim
    return text.strip(' \n\r\t-')


async def _channel_draft_async(prompt: str) -> str:
    """Run Ollama in a thread so the async endpoint doesn't block."""
    return await _asyncio.to_thread(_ollama_draft, prompt)


def _build_channel_prompt(channel: str, lead: dict, sender_company: str = "our company", custom_prompt: str = None, has_image: bool = False) -> str:
    """
    Build a rich, behaviorally-grounded prompt.
    Pulls from: profile, intel, sdk_activity, raw_data, and activity sub-docs.
    """
    profile  = lead.get("profile", {})
    intel    = lead.get("intel",   {})
    activity = lead.get("activity", {})
    sdk      = lead.get("sdk_activity", {})
    raw      = lead.get("raw_data", {})

    # ── Identity ──────────────────────────────────────────────────────────────
    name     = profile.get("name",    raw.get("name",    "there"))
    company  = profile.get("company", raw.get("company", "your company"))
    title    = profile.get("title",   raw.get("title",   ""))
    region   = profile.get("region",  raw.get("region",  raw.get("city", "")))
    industry = raw.get("industry", "")
    source   = lead.get("source", "")

    # ── Intent / AI intel ─────────────────────────────────────────────────────
    intent_score = intel.get("intent_score", 0)
    key_signals  = intel.get("key_signals", [])
    ai_summary   = intel.get("summary", "")
    timing_rec   = intel.get("timing", {}).get("recommended", "")
    crm_stage    = lead.get("crm", {}).get("stage", "")

    # ── CSV behavioral fields ─────────────────────────────────────────────────
    visits         = activity.get("visits",         raw.get("visits",         sdk.get("page_views", 0)))
    pages_per_visit= activity.get("pages_per_visit",raw.get("pages_per_visit",sdk.get("pages_per_visit", 0)))
    time_on_site   = activity.get("time_on_site",   raw.get("time_on_site",   sdk.get("total_time_sec", 0)))
    lead_score     = activity.get("lead_score",     raw.get("lead_score",     0))

    # ── SDK real-time behavioral signals ─────────────────────────────────────
    engagement_score   = sdk.get("engagement_score", 0)
    sessions_count     = sdk.get("sessions_count", 0)
    max_scroll         = sdk.get("max_scroll", 0)
    cart_added         = sdk.get("cart_added", False)
    checkout_started   = sdk.get("checkout_started", False)
    purchase_made      = sdk.get("purchase_made", False)
    device_type        = sdk.get("device_type", "")
    utm_source         = sdk.get("utm_source", "")
    utm_campaign       = sdk.get("utm_campaign", "")
    visited_urls       = sdk.get("urls", sdk.get("page_link", []))
    last_seen          = sdk.get("last_seen", "")

    # ── Compose behavioral context block ─────────────────────────────────────
    sig_lines = []
    if key_signals:
        parsed_signals = [s.get('signal', str(s)) if isinstance(s, dict) else str(s) for s in key_signals[:4]]
        sig_lines.append("AI signals: " + "; ".join(parsed_signals))
    if visits:
        sig_lines.append(f"Website visits: {visits} (avg {pages_per_visit} pages/visit)")
    if time_on_site:
        try:
            val = float(time_on_site)
            mins = int(val) // 60
            secs = int(val) % 60
            sig_lines.append(f"Time on site: {mins}m {secs}s")
        except:
            pass
    if sessions_count:
        sig_lines.append(f"Sessions: {sessions_count}")
    if max_scroll:
        sig_lines.append(f"Max scroll depth: {max_scroll}%")
    if engagement_score:
        sig_lines.append(f"Real-time engagement score: {engagement_score}/100")
    if cart_added:
        sig_lines.append("🛒 Added item to cart (high-intent)")
    if checkout_started:
        sig_lines.append("💳 Started checkout (very high-intent)")
    if purchase_made:
        sig_lines.append("✅ Made a purchase")
    if visited_urls:
        url_list = ", ".join(str(u).replace("https://","").replace("http://","") for u in visited_urls[:5])
        sig_lines.append(f"Pages visited: {url_list}")
    if utm_source:
        sig_lines.append(f"Traffic source: {utm_source}" + (f" / {utm_campaign}" if utm_campaign else ""))
    if device_type:
        sig_lines.append(f"Device: {device_type}")
    if lead_score:
        sig_lines.append(f"CRM lead score: {lead_score}")
    if crm_stage:
        sig_lines.append(f"Pipeline stage: {crm_stage}")

    behavioral_block = "\n".join(f"  - {s}" for s in sig_lines) if sig_lines else "  - No behavioral data available"

    ctx = f"""
SENDER INFORMATION:
  Your Company Name: {sender_company} (Use this as your identity)

LEAD PROFILE:
  Name: {name}
  Title: {title}
  Company: {company}
  Region: {region}
  Industry: {industry}
  Source: {source}

INTENT:
  AI Intent Score: {intent_score}/100
  Timing Recommendation: {timing_rec}
  AI Summary: {ai_summary}

BEHAVIORAL SIGNALS:
{behavioral_block}
"""

    if custom_prompt:
        text = custom_prompt
        text = text.replace("{{customer_name}}", name).replace("{{customer_company}}", company)
        if "{{page_link}}" in text:
            page_link = str(visited_urls[0]) if visited_urls else "https://yourcompany.com"
            text = text.replace("{{page_link}}", page_link)
            
        if "{{ai_msg}}" in text:
            return f"""You are a sales expert writing an outreach message.
Here is the exact template you MUST use. You must fill in the {{{{ai_msg}}}} placeholder with a personalized sentence based on the context provided.
DO NOT change the rest of the template text.
TEMPLATE:
{text}

{ctx}
Generate the final message with the placeholder replaced:"""
        else:
            return f"{text}\n\n{ctx}\nMessage:"

    if channel in channel_outreach_prompts:
        template = channel_outreach_prompts[channel]
        
        # ── Media Context Logic ──────────────────────────────────────────────
        if has_image:
            media_context = "A relevant product image from the page they visited is attached to this message. Reference it naturally (e.g. 'I noticed you were looking at this product...')."
        else:
            media_context = "No product image was found for the specific page they visited (it might have been a calculator or service page without clear product visuals). Draft a warm, text-only message without referring to an attached image."

        # Use helper to get consistent media info
        all_links, all_images = _extract_channel_media(lead)
        page_link = all_links[0] if all_links else "https://yourcompany.com"
        
        return template.format(
            operator_company=sender_company,
            operator_business_type=industry or "Luxury Retail",
            name=name,
            specific_interest=ai_summary or "our latest collections",
            behavioral_signals=behavioral_block,
            media_context=media_context,
            page_link=page_link
        )

    return f"Write a {channel} message for {name} about {sender_company}."


import re

def _extract_channel_media(lead: dict):
    """
    Extract media (images + page links) for WhatsApp/SMS outreach.
    Returns (page_links_list, image_urls_list).
    """
    intel = lead.get("intel", {})
    all_links = []
    all_images = []

    # ── Priority 1: scraped_media list from the Email Strategy node ──────────
    scraped = intel.get("scraped_media", [])
    if scraped and isinstance(scraped, list):
        for item in scraped:
            u = item.get("url")
            img = item.get("image")
            if u and u not in all_links:
                all_links.append(u)
            if img and img not in all_images:
                all_images.append(img)
        
        if all_links or all_images:
            return all_links, all_images

    # ── Priority 2: Parse images out of the generated email HTML preview ──────
    email_preview = intel.get("email", {}).get("preview", "")
    if email_preview:
        # Extract ALL valid <img src="..."> from email HTML
        for m in re.finditer(r'<img[^>]+src="([^"]+)"', email_preview):
            url = m.group(1)
            # Skip tracking pixels
            if url and "1x1" not in url and "pixel" not in url.lower():
                if url not in all_images:
                    all_images.append(url)

        # Extract ALL valid <a href="..."> links
        for m in re.finditer(r'<a[^>]+href="([^"]+)"', email_preview):
            url = m.group(1)
            if url and url.startswith("http") and url not in all_links:
                all_links.append(url)

    # ── Page link fallback from SDK visited URLs ──────────────────────────────
    if not all_links:
        sdk = lead.get("sdk_activity", {})
        visited_urls = sdk.get("urls", sdk.get("page_link", []))
        raw_data = lead.get("raw_data", {})
        if not visited_urls:
            visited_urls = raw_data.get("page_link", [])
        if not visited_urls:
            visited_urls = lead.get("page_link", [])
        
        if isinstance(visited_urls, str):
            visited_urls = [u.strip() for u in visited_urls.replace("|", ",").split(",") if u.strip()]
        
        for u in visited_urls:
            if str(u).startswith("http") and u not in all_links:
                all_links.append(str(u))

    return all_links, all_images



@router.get("/channel-draft/{lead_id}/{channel}")
async def get_channel_draft(lead_id: str, channel: str, user=Depends(get_current_user)):
    """Stage 6/7/8 — returns or generates AI draft for this lead's channel outreach."""
    if channel not in ("sms", "whatsapp", "voice"):
        raise HTTPException(400, "channel must be sms | whatsapp | voice")

    company_id = str(user["company_id"])
    from bson import ObjectId
    try: comp_oid = ObjectId(company_id)
    except: comp_oid = company_id

    lead = await leads_collection.find_one({
        "lead_id": lead_id, 
        "$or": [{"company_id": company_id}, {"company_id": comp_oid}]
    })
    if not lead:
        raise HTTPException(404, "Lead not found")

    existing = lead.get("intel", {}).get("channels", {}).get(channel, {})

    scraped_media = lead.get("intel", {}).get("scraped_media", [])
    all_links, all_images = _extract_channel_media(lead)
    page_link = all_links[0] if all_links else ""
    img_url = all_images[0] if all_images else ""

    if existing.get("draft"):
        return {"lead_id": lead_id, "channel": channel, "draft": existing["draft"],
                "sent": existing.get("sent", False), "sent_at": existing.get("sent_at"),
                "image_url": img_url, "page_link": page_link, "all_images": all_images, "all_links": all_links, "scraped_media": scraped_media}

    cfg = await channel_settings_collection.find_one({"company_id": company_id}) or {}
    comp_doc = await companies_collection.find_one({"$or": [{"_id": company_id}, {"_id": comp_oid}]})
    sender_comp = comp_doc.get("company_name", "our company") if comp_doc else "our company"

    custom_prompt = cfg.get(f"{channel}_prompt")
    has_image = bool(all_images)
    prompt = _build_channel_prompt(channel, lead, sender_company=sender_comp, custom_prompt=custom_prompt, has_image=has_image)
    try:
        draft = await _channel_draft_async(prompt)
        if not draft:
            raise ValueError("Empty response from Ollama")
    except Exception as e:
        print(f"[ChannelAgent] Ollama draft failed for {channel}/{lead_id}: {e}")
        draft = f"Hi {lead.get('profile',{}).get('name','there')}, wanted to reach out about how we might help {lead.get('profile',{}).get('company','your company')}. Would love a quick chat!"

    if channel == "sms":
        draft = draft[:160]

    await leads_collection.update_one(
        {"lead_id": lead_id, "$or": [{"company_id": company_id}, {"company_id": comp_oid}]},
        {"$set": {
            f"intel.channels.{channel}.draft": draft, 
            f"intel.channels.{channel}.sent": False,
            f"intel.channels.{channel}.image_url": img_url,
            f"intel.channels.{channel}.page_link": page_link,
            f"intel.channels.{channel}.all_images": all_images,
            f"intel.channels.{channel}.all_links": all_links
        }}
    )

    _agent_status[f"{channel}_agent"]["status"] = "completed"
    _agent_status[f"{channel}_agent"]["last_run"] = datetime.now(timezone.utc).isoformat()

    return {"lead_id": lead_id, "channel": channel, "draft": draft, "sent": False, "sent_at": None, "image_url": img_url, "page_link": page_link, "scraped_media": scraped_media}


@router.post("/channel-approve/{lead_id}/{channel}")
async def approve_channel_send(lead_id: str, channel: str,
                                body: dict = None, user=Depends(get_current_user)):
    """Stage 6/7/8 Approve — send via Twilio and log to CRM audit trail."""
    company_id = str(user["company_id"])
    
    lead = await leads_collection.find_one({"lead_id": lead_id})
    if not lead:
        raise HTTPException(404, "Lead not found")

    draft = (body or {}).get("draft") or lead.get("intel", {}).get("channels", {}).get(channel, {}).get("draft", "")
    if not draft:
        raise HTTPException(422, "No draft found. Click generate first.")

    try:
        res = await TwilioService.send_channel_message(
            company_id=company_id,
            lead_id=lead_id,
            channel=channel,
            draft_override=draft
        )
        # Update local status for the agent monitor
        now = datetime.now(timezone.utc)
        if f"{channel}_agent" in _agent_status:
            _agent_status[f"{channel}_agent"]["status"] = "completed"
            _agent_status[f"{channel}_agent"]["last_run"] = now.isoformat()
            
        return res
    except Exception as e:
        print(f"[AgentApprove] Error: {e}")
        raise HTTPException(500, f"Channel delivery failed: {str(e)}")


@router.post("/channel-regenerate/{lead_id}/{channel}")
async def regenerate_channel_draft(lead_id: str, channel: str, user=Depends(get_current_user)):
    """Re-run the channel AI agent to get a fresh personalized draft."""
    if channel not in ("sms", "whatsapp", "voice"):
        raise HTTPException(400, "channel must be sms | whatsapp | voice")
    company_id = str(user["company_id"])
    from bson import ObjectId
    try: comp_oid = ObjectId(company_id)
    except: comp_oid = company_id

    lead = await leads_collection.find_one({
        "lead_id": lead_id, 
        "$or": [{"company_id": company_id}, {"company_id": comp_oid}]
    })
    if not lead:
        raise HTTPException(404, "Lead not found")
    cfg = await channel_settings_collection.find_one({"company_id": company_id}) or {}
    comp_doc = await companies_collection.find_one({"$or": [{"_id": company_id}, {"_id": comp_oid}]})
    sender_comp = comp_doc.get("company_name", "our company") if comp_doc else "our company"

    custom_prompt = cfg.get(f"{channel}_prompt")
    prompt = _build_channel_prompt(channel, lead, sender_company=sender_comp, custom_prompt=custom_prompt)
    try:
        draft = await _channel_draft_async(prompt)
        if not draft:
            raise ValueError("Empty response from Ollama")
    except Exception as e:
        raise HTTPException(500, f"Ollama generation failed: {e}")
    if channel == "sms":
        draft = draft[:160]
        
    page_link, img_url = _extract_channel_media(lead)
    
    await leads_collection.update_one(
        {"lead_id": lead_id, "$or": [{"company_id": company_id}, {"company_id": comp_oid}]},
        {"$set": {
            f"intel.channels.{channel}.draft": draft, 
            f"intel.channels.{channel}.sent": False,
            f"intel.channels.{channel}.image_url": img_url,
            f"intel.channels.{channel}.page_link": page_link
        }}
    )
    scraped_media = lead.get("intel", {}).get("scraped_media", [])
    return {"lead_id": lead_id, "channel": channel, "draft": draft, "sent": False, "sent_at": None, "image_url": img_url, "page_link": page_link, "scraped_media": scraped_media}
