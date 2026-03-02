import os
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body, Depends
import pymongo
from bson import ObjectId

from db import leads_collection, agent_activity_collection
from dependencies import get_current_user

router = APIRouter()

@router.get("")
async def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    region: Optional[str] = None,
    lead_source: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: str = Query("asc", regex="^(asc|desc)$"),
    batch_id: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    user=Depends(get_current_user)
):
    query = {"company_id": user["company_id"]}
    if batch_id:
        query["batch_id"] = batch_id
        
    if search:
        search_regex = {"$regex": re.escape(search), "$options": "i"}
        search_or = [
            {"profile.name": search_regex},
            {"profile.company": search_regex},
            {"profile.title": search_regex}
        ]
        
        try:
            int_val = int(search)
            search_or.append({"intel.intent_score": int_val})
        except ValueError:
            pass
            
        query["$or"] = search_or
        
    if region:
        query["profile.region"] = region
    if lead_source:
        query["profile.lead_source"] = lead_source
        
    if min_score is not None or max_score is not None:
        score_query = {}
        if min_score is not None:
            score_query["$gte"] = min_score
        if max_score is not None:
            score_query["$lte"] = max_score
        query["intel.intent_score"] = score_query

    sort_criteria = []
    if sort_by:
        sort_field = sort_by
        if sort_by in ["name", "company", "title", "region", "lead_source"]:
            sort_field = f"profile.{sort_by}"
        elif sort_by == "intent_score":
            sort_field = "intel.intent_score"
            
        direction = pymongo.ASCENDING if sort_dir == "asc" else pymongo.DESCENDING
        sort_criteria.append((sort_field, direction))
    else:
        sort_criteria.append(("_id", pymongo.ASCENDING))

    skip = (page - 1) * page_size
    
    total = await leads_collection.count_documents(query)
    cursor = leads_collection.find(query).sort(sort_criteria).skip(skip).limit(page_size)
    leads = await cursor.to_list(length=page_size)
    
    leads_list = []
    for lead_doc in leads:
        profile = lead_doc.get("profile", {})
        activity = lead_doc.get("activity", {})
        flat_lead = {
            "lead_id": lead_doc.get("lead_id"),
            "name": profile.get("name", "Unknown"),
            "company": profile.get("company", "Unknown"),
            "title": profile.get("title", "Unknown"),
            "region": profile.get("region", "Unknown"),
            "lead_source": profile.get("lead_source", "Unknown"),
            "visits": activity.get("visits", 0),
            "time_on_site": activity.get("time_on_site", 0.0),
            "pages_per_visit": activity.get("pages_per_visit", 0.0),
            "converted": activity.get("converted", False),
            "intent_score": lead_doc.get("intel", {}).get("intent_score", 0),
            "status": lead_doc.get("status", "Unknown"),
            "record_id": lead_doc.get("lead_id")
        }
        leads_list.append(flat_lead)
        
    return {
        "data": leads_list,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/stats")
async def lead_stats(batch_id: Optional[str] = None, user=Depends(get_current_user)):
    query = {"company_id": user["company_id"]}
    if batch_id:
        query["batch_id"] = batch_id
        
    pipeline = [
        {"$match": query},
        {"$facet": {
            "total": [{"$count": "count"}],
            "active": [{"$match": {"status": {"$in": ["Analysis", "Processing_"]}}}, {"$count": "count"}],
            "ready": [{"$match": {"status": "Ready"}}, {"$count": "count"}],
            "converted": [{"$match": {"activity.converted": True}}, {"$count": "count"}]
        }}
    ]
    
    result = await leads_collection.aggregate(pipeline).to_list(length=1)
    stats = result[0]
    
    total_leads = stats["total"][0]["count"] if stats["total"] else 0
    active_pursuits = stats["active"][0]["count"] if stats["active"] else 0
    ready_leads = stats["ready"][0]["count"] if stats["ready"] else 0
    converted_leads = stats["converted"][0]["count"] if stats["converted"] else 0
    
    conversion_rate = round((converted_leads / total_leads) * 100, 1) if total_leads > 0 else 0
        
    return {
        "total": total_leads,
        "active_pursuits": active_pursuits,
        "conversion_rate": conversion_rate,
        "ready": ready_leads
    }

@router.get("/filters")
async def lead_filters(batch_id: Optional[str] = None, user=Depends(get_current_user)):
    query = {"company_id": user["company_id"]}
    if batch_id:
        query["batch_id"] = batch_id
        
    regions = await leads_collection.distinct("profile.region", query)
    sources = await leads_collection.distinct("profile.lead_source", query)
    
    return {
        "regions": sorted([r for r in regions if r]),
        "lead_sources": sorted([s for s in sources if s])
    }

@router.get("/{record_id}")
async def get_lead_details(record_id: str, batch_id: Optional[str] = None, user=Depends(get_current_user)):
    """Retrieve full intelligence report data for a specific lead."""
    query = {"company_id": user["company_id"], "lead_id": record_id}
    if batch_id:
        query["batch_id"] = batch_id
        
    lead_doc = await leads_collection.find_one(query)
    if not lead_doc:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    profile = lead_doc.get("profile", {})
    name = profile.get("name", "Unknown")
    company = profile.get("company", "Unknown")
    
    intel = lead_doc.get("intel", {})
    email_data = intel.get("email", {})
    email_preview = email_data.get("preview", "")
    
    paragraphs = str(email_preview).replace('\\n', '\n').split('\n')
    draft_blocks = []
    for line in paragraphs:
        if line.strip() == "":
            draft_blocks.append({"type": "br"})
        else:
            draft_blocks.append({"type": "text", "content": line})
            
    quality_indicators = intel.get("quality_indicators", [])
    research_signals = [
        f"{q.get('metric', '')}: {q.get('value', '')}" if isinstance(q, dict) else str(q)
        for q in quality_indicators
    ]
    if not research_signals:
         research_signals = ["High Engagement", "Target Account Hit"] # fallback UI
         
    key_signals = intel.get("key_signals", [])
    signals_list = [s.get("signal", str(s)) if isinstance(s, dict) else str(s) for s in key_signals]
    intent_reasoning = " • ".join(signals_list) if signals_list else "Pending analysis"
    
    timing_data = intel.get("timing", {})
    timing_rec = f"{timing_data.get('recommended_date', '')} {timing_data.get('send_time', '')}".strip()
    
    crm_logs = []
    cursor = agent_activity_collection.find({"lead_id": record_id, "company_id": user["company_id"]}).sort("timestamp", 1)
    activities = await cursor.to_list(length=100)
    
    for act in activities:
        crm_logs.append({
            "time": act.get("timestamp").strftime("%H:%M:%S") if act.get("timestamp") else "",
            "agent": act.get("agent", "SYSTEM"),
            "action": act.get("action", ""),
            "status": act.get("status", "SUCCESS")
        })

    # Fallback log if empty
    if not crm_logs:
        crm_logs.append({
             "time": datetime.utcnow().strftime("%H:%M:%S"),
             "agent": "SYSTEM",
             "action": "Legacy record loaded from database.",
             "status": "INFO"
        })

    return {
        "lead_id": record_id,
        "profile": {
            "name": name,
            "title": profile.get("title", "Unknown"),
            "company": company,
            "linkedin": profile.get('linkedin') or f"linkedin.com/in/{name.lower().replace(' ', '')}",
            "website": profile.get('website') or f"{company.lower().replace(' ', '')}.com",
            "bio": profile.get('bio') or f"{profile.get('title')} at {company}"
        },
        "agents": {
            "research": {
                "summary": "Processed via LangGraph Pipeline.",
                "signals": research_signals
            },
            "intent": {
                "score": intel.get("intent_score", 0),
                "reasoning": intent_reasoning,
                "recommendation": intel.get("intent_recommendation", {})
            },
            "message": {
                "draft": draft_blocks,
                "subject": email_data.get("subject", ""),
                "personalization_factors": email_data.get("personalization_factors", [])
            },
            "timing": {
                "recommended": timing_rec,
                "recommendedReason": timing_data.get("reasoning", ""),
                "optimal_time_window": timing_data.get("optimal_time_window", ""),
                "approach": intel.get("approach", {}),
                "engagement_prediction": intel.get("engagement_prediction", {}),
                "timeline": lead_doc.get("crm", {}).get("timeline", {})
            },
            "crm": {
                "logs": crm_logs
            }
        },
        "status": lead_doc.get("status", "Ready"),
        "batch_id": lead_doc.get("batch_id")
    }

@router.patch("/{record_id}/status")
async def update_lead_status(record_id: str, payload: dict = Body(...), user=Depends(get_current_user)):
    new_status = payload.get("status")
    intent_score = payload.get("intent_score")
    
    if not new_status and intent_score is None:
        raise HTTPException(status_code=400, detail="Missing status or intent_score in body")
        
    query = {"lead_id": record_id, "company_id": user["company_id"]}
    update_data = {}
    
    if new_status:
        update_data["status"] = new_status
    if intent_score is not None:
        update_data["intel.intent_score"] = intent_score
        
    update_data["updated_at"] = datetime.utcnow()
    
    result = await leads_collection.update_one(query, {"$set": update_data})
    
    if result.matched_count == 0:
         raise HTTPException(status_code=404, detail="Lead not found")
         
    return {"status": "success"}

@router.post("/{record_id}/approve-email")
async def approve_email(record_id: str, payload: dict = Body(...), user=Depends(get_current_user)):
    """Send approved email and log to CRM"""
    subject = payload.get("subject")
    content = payload.get("content")
    to_email = payload.get("to_email", "mock@lead.com")
    
    if not subject or not content:
        raise HTTPException(status_code=400, detail="Missing subject or content")
        
    query = {"lead_id": record_id, "company_id": user["company_id"]}
    lead_doc = await leads_collection.find_one(query)
    if not lead_doc:
         raise HTTPException(status_code=404, detail="Lead not found")
         
    # 1. Send Email
    from services.email_sender import EmailService
    try:
        await EmailService.send_email(
            company_id=user["company_id"],
            to_address=to_email,
            subject=subject,
            html_content=content
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email delivery failed: {str(e)}")
        
    # 2. Update CRM state
    from db import email_logs_collection
    now = datetime.utcnow()
    
    await leads_collection.update_one(query, {
        "$set": {
            "crm.email_sent": True,
            "updated_at": now
        }
    })
    
    # 3. Log to activity
    await agent_activity_collection.insert_one({
        "company_id": user["company_id"],
        "batch_id": lead_doc.get("batch_id"),
        "lead_id": record_id,
        "agent": "HUMAN",
        "action": "Approved and dispatched email via UI",
        "status": "SUCCESS",
        "timestamp": now
    })
    
    # 4. Log to email_logs
    await email_logs_collection.insert_one({
        "company_id": user["company_id"],
        "batch_id": lead_doc.get("batch_id"),
        "lead_id": record_id,
        "subject": subject,
        "content_snapshot": content,
        "sent_at": now,
        "status": "delivered"
    })
    
    return {"status": "success", "message": "Email sent and logged successfully"}

@router.post("/{record_id}/schedule-followup")
async def schedule_followup(record_id: str, payload: dict = Body(...), user=Depends(get_current_user)):
    """Schedule a future email follow-up"""
    subject = payload.get("subject")
    content = payload.get("content")
    scheduled_at_str = payload.get("scheduled_at") # ISO 8601 string expected
    
    if not subject or not content or not scheduled_at_str:
        raise HTTPException(status_code=400, detail="Missing subject, content, or scheduled_at")
        
    try:
        if scheduled_at_str.endswith("Z"):
            scheduled_at_str = scheduled_at_str[:-1] + "+00:00"
        scheduled_at = datetime.fromisoformat(scheduled_at_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
        
    query = {"lead_id": record_id, "company_id": user["company_id"]}
    lead_doc = await leads_collection.find_one(query)
    if not lead_doc:
         raise HTTPException(status_code=404, detail="Lead not found")
         
    from db import followup_queue_collection
    now = datetime.utcnow()
    
    await followup_queue_collection.insert_one({
        "company_id": user["company_id"],
        "lead_id": record_id,
        "batch_id": lead_doc.get("batch_id"),
        "subject": subject,
        "content": content,
        "status": "pending",
        "scheduled_at": scheduled_at,
        "created_at": now
    })
    
    await agent_activity_collection.insert_one({
        "company_id": user["company_id"],
        "batch_id": lead_doc.get("batch_id"),
        "lead_id": record_id,
        "agent": "HUMAN",
        "action": f"Scheduled follow-up email for {scheduled_at.strftime('%Y-%m-%d %H:%M')}",
        "status": "SUCCESS",
        "timestamp": now
    })
    
    return {"status": "success", "message": "Follow-up scheduled successfully"}
