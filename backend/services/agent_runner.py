import asyncio
from datetime import datetime, timezone
import json
import os
import sys

from db import leads_collection, agent_activity_collection, batches_collection

from langgraph_nodes.lead_research_node import create_lead_research_graph
from langgraph_nodes.intent_qualifier_node import create_intent_qualifier_graph
from langgraph_nodes.email_strategy_node import create_email_strategy_graph
from langgraph_nodes.followup_timing_node import create_followup_timing_graph
from langgraph_nodes.crm_logger_node import create_crm_logger_graph

from prompts.lead_research_prompts import lead_research_prompts
from prompts.intent_qualifier_prompts import intent_qualifier_prompts
from prompts.email_strategy_prompts import email_strategy_prompts
from prompts.followup_timing_prompts import followup_timing_prompts
from api.agents import (
    OllamaWrapper, 
    _build_channel_prompt, 
    _channel_draft_async, 
    _extract_channel_media
)
from services.sdk_page_crawler import crawl_sdk_product_pages
from db import channel_settings_collection


async def update_batch_progress(batch_id: str, updates: dict):
    """Helper to merge updates into the batch document in MongoDB"""
    await batches_collection.update_one(
        {"batch_id": batch_id},
        {"$set": updates}
    )

async def push_batch_log(batch_id: str, log_message: str):
    """Helper to push a timestamped log to the batch document"""
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {log_message}"
    await batches_collection.update_one(
        {"batch_id": batch_id},
        {"$push": {"logs": formatted_msg}}
    )

async def run_pipeline_for_lead(lead_id: str, batch_id: str, company_id: str):
    """
    Executes the 5-node AI pipeline for a single Lead (used by SDK Live Tracking Conversion).
    """
    print(f"[AgentRunner] Starting SDK Live Conversion Pipeline for Lead {lead_id}...")
    await push_batch_log(batch_id, f"Initializing pipeline for Lead ID: {lead_id}")
    
    # Initialize agent status
    await update_batch_progress(batch_id, {
        "agents": { k: "pending" for k in ["research", "intent", "message", "timing", "logger"] },
        "status": "processing",
        "percent": 5
    })
    
    # 1. Fetch Lead
    from bson import ObjectId
    try:
        c_id_obj = ObjectId(company_id) if isinstance(company_id, str) else company_id
    except:
        c_id_obj = company_id
        
    lead_doc = await leads_collection.find_one({"lead_id": lead_id, "company_id": c_id_obj})
    if not lead_doc:
        print(f"[AgentRunner] Lead {lead_id} not found.")
        await push_batch_log(batch_id, f"ERROR: Lead {lead_id} not found in database.")
        return

    # 2. Extract Lead Data — enriched with all sdk_activity v2 fields
    sdk  = lead_doc.get("sdk_activity", {})
    prof = lead_doc.get("profile", {})
    urls = sdk.get("urls", sdk.get("page_link", []))
    lead_dict = {
        "lead_id":          lead_id,
        "name":             prof.get("name", "Unknown Visitor"),
        "email":            prof.get("email", ""),
        "company":          prof.get("company", "Unknown"),
        "title":            prof.get("title", ""),
        "phone":            prof.get("phone", ""),
        "city":             prof.get("city", ""),
        "state":            prof.get("state", ""),
        # Behavioral signals
        "visits":           sdk.get("page_views", sdk.get("total_page_views", 1)),
        "page_link":        urls,
        "time_on_site":     sdk.get("total_time_sec", 0),
        "engage_date":      sdk.get("last_seen", "").isoformat() if hasattr(sdk.get("last_seen", ""), "isoformat") else str(sdk.get("last_seen", "")),
        "sessions_count":   sdk.get("sessions_count", 1),
        "max_scroll":       sdk.get("max_scroll", 0),
        "engagement_score": sdk.get("engagement_score", 0),
        "cart_added":       sdk.get("cart_added", False),
        "checkout_started": sdk.get("checkout_started", False),
        "purchase_made":    sdk.get("purchase_made", False),
        "device_type":      sdk.get("device_type", "Unknown"),
        "utm_source":       sdk.get("utm_source", ""),
        "utm_medium":       sdk.get("utm_medium", ""),
        "utm_campaign":     sdk.get("utm_campaign", ""),
        "source":           lead_doc.get("source", "sdk"),
        "sdk_activity":     {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in sdk.items()},
    }
    
    # 4. Compile Agents
    llm = OllamaWrapper()
    
    # ── NEW: SDK Smart Crawler Integration ──
    scraped_products = []
    if urls and lead_doc.get("source") == "sdk":
        try:
            await push_batch_log(batch_id, f"Running Smart Crawler on {len(urls)} URLs...")
            # Run the crawler in a thread to avoid blocking
            scraped_products = await asyncio.to_thread(crawl_sdk_product_pages, urls, llm)
            await push_batch_log(batch_id, f"Crawler found {len(scraped_products)} products.")
            
            # Save results to lead doc immediately so UI can show them
            await leads_collection.update_one(
                {"lead_id": lead_id, "company_id": c_id_obj},
                {"$set": {"intel.scraped_media": scraped_products}}
            )
        except Exception as crawl_err:
            print(f"[AgentRunner] Crawler failed: {crawl_err}")
            await push_batch_log(batch_id, f"Crawler warning: {str(crawl_err)}")

    agents = {
        'research': create_lead_research_graph(llm, lead_research_prompts),
        'intent': create_intent_qualifier_graph(llm, intent_qualifier_prompts),
        'email': create_email_strategy_graph(llm, email_strategy_prompts),
        'timing': create_followup_timing_graph(llm, followup_timing_prompts),
        'logger': create_crm_logger_graph()
    }
    
    # Optional operator info
    from db import companies_collection
    from bson import ObjectId
    c_doc = await companies_collection.find_one({"_id": ObjectId(company_id)})
    operator_info = {}
    if c_doc:
        operator_info = {
            "operator_name": c_doc.get("contact_person_name", c_doc.get("company_name", "Unknown")),
            "operator_company": c_doc.get("company_name", "Unknown"),
            "operator_website": c_doc.get("domain", "") or c_doc.get("website", ""),
            "operator_email": c_doc.get("email", "")
        }

    state = {
        "lead": {**lead_dict, "scraped_products": scraped_products},
        "email_history": [],
        "operator_info": operator_info,
        "schema_mapping": {},
        "scraped_products": scraped_products
    }

    print(f"[AgentRunner] Pipeline Initialized for SDK Lead {lead_id}. Running node sequence...")
    await push_batch_log(batch_id, f"Pipeline Initialized for {lead_dict['name']}. Running node sequence...")

    try:
        # Run node sequence with logs
        await push_batch_log(batch_id, "Running Agent: [1/5] Lead Web Research...")
        await update_batch_progress(batch_id, {"agents.research": "running", "percent": 20})
        state = await asyncio.to_thread(agents['research'].invoke, state)
        await update_batch_progress(batch_id, {"agents.research": "completed"})

        await push_batch_log(batch_id, "Running Agent: [2/5] Intent Qualification...")
        await update_batch_progress(batch_id, {"agents.intent": "running", "percent": 40})
        state = await asyncio.to_thread(agents['intent'].invoke, state)
        await update_batch_progress(batch_id, {"agents.intent": "completed"})

        await push_batch_log(batch_id, "Running Agent: [3/5] Email Strategy Formulation...")
        await update_batch_progress(batch_id, {"agents.message": "running", "percent": 60})
        state = await asyncio.to_thread(agents['email'].invoke, state)
        await update_batch_progress(batch_id, {"agents.message": "completed"})

        await push_batch_log(batch_id, "Running Agent: [4/5] Follow-up Timing Optimization...")
        await update_batch_progress(batch_id, {"agents.timing": "running", "percent": 80})
        state = await asyncio.to_thread(agents['timing'].invoke, state)
        await update_batch_progress(batch_id, {"agents.timing": "completed"})

        await push_batch_log(batch_id, "Running Agent: [5/5] CRM Serialization...")
        await update_batch_progress(batch_id, {"agents.logger": "running", "percent": 90})
        state = await asyncio.to_thread(agents['logger'].invoke, state)
        await update_batch_progress(batch_id, {"agents.logger": "completed"})

        
        # 4. Save mapped output state to lead
        await leads_collection.update_one(
            {"lead_id": lead_id, "batch_id": batch_id},
            {
                "$set": {
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
                        "deal_value": 0,
                        "stage": state.get("crm_stage", "prospect"),
                        "notes": lead_doc.get("crm", {}).get("notes", "")
                    },
                    "status": "Completed", # Marks them as fully ready for Email Sender
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        # ── AUTO MULTI-CHANNEL DRAFT GENERATION ─────────────────────────────────────
        # Ported from batch.py: Automatically generate SMS/WhatsApp/Voice drafts
        print(f"[AgentRunner] Auto-generating multi-channel drafts for {lead_id}...")
        await push_batch_log(batch_id, "Auto-generating multi-channel drafts (SMS / WhatsApp / Voice)...")
        
        # Fetch fully saved doc to ensure all fields are ready
        saved_lead_doc = await leads_collection.find_one({"lead_id": lead_id, "batch_id": batch_id})
        if saved_lead_doc:
            cfg = await channel_settings_collection.find_one({"company_id": company_id}) or {}
            page_link, img_urls = _extract_channel_media(saved_lead_doc)
            
            # Use the first valid image for channel drafts
            primary_img = None
            if img_urls and isinstance(img_urls, list) and len(img_urls) > 0:
                primary_img = img_urls[0]
            elif isinstance(img_urls, str) and img_urls.strip():
                primary_img = img_urls

            for ch in ("sms", "whatsapp", "voice"):
                try:
                    await push_batch_log(batch_id, f"Generating {ch.upper()} draft...")
                    custom_prompt = cfg.get(f"{ch}_prompt")
                    sender_name = operator_info.get("operator_company", "Our Team")
                    has_img = bool(primary_img)
                    ch_prompt = _build_channel_prompt(ch, saved_lead_doc, sender_name, custom_prompt, has_image=has_img)
                    ch_draft = await _channel_draft_async(ch_prompt)
                    
                    if ch == "sms" and ch_draft:
                        ch_draft = ch_draft[:160] # SMS hard limit
                    
                    if ch_draft:
                        await leads_collection.update_one(
                            {"lead_id": lead_id, "batch_id": batch_id},
                            {"$set": {
                                f"intel.channels.{ch}.draft": ch_draft,
                                f"intel.channels.{ch}.sent": False,
                                f"intel.channels.{ch}.image_url": primary_img,
                                f"intel.channels.{ch}.page_link": page_link,
                            }}
                        )
                        print(f"[AgentRunner] [SUCCESS] {ch.upper()} draft ready for {lead_id}")
                        await push_batch_log(batch_id, f"[SUCCESS] {ch.upper()} draft ready")
                    else:
                        await push_batch_log(batch_id, f"[WARN] {ch.upper()} draft skipped (empty)")
                except Exception as ch_err:
                    print(f"[AgentRunner] [WARN] {ch.upper()} draft failed for {lead_id}: {ch_err}")
                    await push_batch_log(batch_id, f"[WARN] {ch.upper()} draft failed: {str(ch_err)}")
        
        # 5. Log Activity
        await agent_activity_collection.insert_one({
            "company_id": company_id,
            "batch_id": batch_id,
            "lead_id": lead_id,
            "agent": "PIPELINE",
            "action": "Completed SDK Auto-Conversion Pipeline (Live Tracker)",
            "status": "SUCCESS",
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Increment pseudo batch progress
        await batches_collection.update_one(
            {"batch_id": batch_id},
            {"$inc": {"leads_processed": 1}, "$set": {"percent": 100, "status": "completed"}}
        )
        await push_batch_log(batch_id, "SUCCESS: Full pipeline completed.")
        
        print(f"[AgentRunner] SUCCESS: SDK Lead {lead_id} completed.")


    except Exception as e:
        safe_err = str(e).encode('utf-8', errors='replace').decode('utf-8')
        print(f"[AgentRunner] Error processing lead {lead_id}: {safe_err}")
        await leads_collection.update_one(
            {"lead_id": lead_id, "batch_id": batch_id},
            {"$set": {"status": "Error", "intel.error": safe_err}}
        )
async def rerun_intent_agent_for_lead(lead_id: str, company_id: str):
    """
    Independent entry point to re-run ONLY the Intent Qualifier Agent (Agent 2).
    Triggered by real-time behavioral signals (email open/click, SDK revisit).
    """
    print(f"[AgentRunner] Re-evaluating Intent for Lead {lead_id} (Agent 2 Triggered)...")
    
    # 1. Fetch Lead
    from bson import ObjectId
    try:
        c_id_obj = ObjectId(company_id) if isinstance(company_id, str) else company_id
    except:
        c_id_obj = company_id
        
    lead_doc = await leads_collection.find_one({"lead_id": lead_id, "company_id": c_id_obj})
    if not lead_doc:
        print(f"[AgentRunner] Lead {lead_id} not found for re-evaluation.")
        return

    # 2. Fetch Email History from email_logs_collection for this lead
    # We map 'delivered' and counts to what the node expects
    email_logs = await email_logs_collection.find({"lead_id": lead_id, "company_id": c_id_obj}).to_list(length=100)
    email_data = []
    for log in email_logs:
        email_data.append({
            "email_id": str(log.get("_id")),
            "opened": bool(log.get("open_count", 0) > 0),
            "replied": False, # TODO: Add reply detection if available
            "engagement_score": float(log.get("open_count", 0) * 5 + log.get("click_count", 0) * 15)
        })

    # 3. Extract Lead Data
    sdk  = lead_doc.get("sdk_activity", {})
    prof = lead_doc.get("profile", {})
    lead_dict = {
        "lead_id":          lead_id,
        "name":             prof.get("name", "Unknown Visitor"),
        "company":          prof.get("company", "Unknown"),
        "title":            prof.get("title", ""),
        "visits":           sdk.get("page_views", 1),
        "time_on_site":     sdk.get("total_time_sec", 0),
        "crm_stage":        lead_doc.get("crm", {}).get("stage", "prospect"),
        "engagement_score": sdk.get("engagement_score", 0),
    }
    
    # 4. Run Intent Agent
    llm = OllamaWrapper()
    agent = create_intent_qualifier_graph(llm, intent_qualifier_prompts)
    
    state = {
        "lead": lead_dict,
        "email_data": email_data, # Node expects 'email_data' for prepare_data
        "status": "pending"
    }

    try:
        final_state = await asyncio.to_thread(agent.invoke, state)
        new_score = final_state.get("intent_score", 0.0)
        new_signals = final_state.get("key_signals", [])
        
        # 5. Update Lead with AI-generated score
        await leads_collection.update_one(
            {"_id": lead_doc["_id"]},
            {
                "$set": {
                    "intel.intent_score": new_score,
                    "updated_at": datetime.now(timezone.utc)
                },
                "$push": {
                    "intel.key_signals": {
                        "$each": new_signals,
                        "$slice": -30
                    }
                }
            }
        )
        
        # 6. Log Activity
        await agent_activity_collection.insert_one({
            "company_id": company_id,
            "lead_id": lead_id,
            "agent": "AGENT_02_INTENT",
            "action": f"AI Re-evaluation: New score {new_score}",
            "status": "SUCCESS",
            "timestamp": datetime.now(timezone.utc)
        })
        print(f"[AgentRunner] ✓ Intent re-evaluated for {lead_id}: {new_score}")
        
    except Exception as e:
        print(f"[AgentRunner] Error re-evaluating intent for {lead_id}: {e}")
