"""
Dashboard API — Aggregated stats and activity feed.
"""

from fastapi import APIRouter, Depends
from datetime import datetime
import random
from dependencies import get_current_user
from db import leads_collection, email_logs_collection, agent_activity_collection

router = APIRouter()

@router.get("/stats")
async def dashboard_stats(user = Depends(get_current_user)):
    """Get KPI card data for the dashboard."""
    company_id = user["company_id"]
    # 1. Total Leads
    total_leads = await leads_collection.count_documents({"company_id": company_id})
    
    # 2. High Intent Leads
    high_intent = await leads_collection.count_documents({"company_id": company_id, "intel.intent_score": {"$gte": 80}})
    
    # 3. Conversion Rate
    converted_leads = await leads_collection.count_documents({"company_id": company_id, "status": "converted"})
    conversion_rate = round((converted_leads / total_leads * 100), 1) if total_leads > 0 else 0
    
    # 3. Pipeline Value
    pipeline_cursor = leads_collection.aggregate([
        {"$match": {"company_id": company_id}},
        {"$group": {"_id": None, "total_value": {"$sum": {"$toDouble": {"$ifNull": ["$crm.deal_value", 0]}}}}}
    ])
    pipeline_res = await pipeline_cursor.to_list(1)
    pipeline_value = pipeline_res[0]["total_value"] if pipeline_res else 0
    
    # 5. Average Score
    score_cursor = leads_collection.aggregate([
        {"$match": {"company_id": company_id}},
        {"$group": {"_id": None, "avg_score": {"$avg": {"$toDouble": {"$ifNull": ["$intel.intent_score", 0]}}}}}
    ])
    score_res = await score_cursor.to_list(1)
    avg_score = round(score_res[0]["avg_score"]) if score_res else 0
    
    # 6. Emails Sent
    emails_sent = await email_logs_collection.count_documents({"company_id": company_id})
    
    # 7. Response Rate (mocked for now since IMAP parsing isn't wired)
    response_rate = random.randint(12, 45) if emails_sent > 0 else 0
    
    return {
        "total_leads": total_leads,
        "high_intent": high_intent,
        "avg_score": avg_score,
        "conversion_rate": conversion_rate,
        "pipeline_value": pipeline_value,
        "active_agents": 5,
        "emails_sent": emails_sent,
        "response_rate": response_rate,
    }

@router.get("/activity")
async def dashboard_activity(user = Depends(get_current_user)):
    """Get recent agent activity feed."""
    company_id = user["company_id"]
    
    cursor = agent_activity_collection.find({"company_id": company_id}).sort("timestamp", -1).limit(20)
    docs = await cursor.to_list(length=20)
    
    activities = []
    
    def map_icon(agent_type):
        agent_type = agent_type.upper()
        if "RESEARCH" in agent_type: return {"icon": "search", "color": "#52c41a"}
        if "INTENT" in agent_type: return {"icon": "target", "color": "#fa8c16"}
        if "EMAIL" in agent_type: return {"icon": "mail", "color": "#2f54eb"}
        if "LOGGER" in agent_type: return {"icon": "database", "color": "#722ed1"}
        if "SCHEDULER" in agent_type: return {"icon": "clock", "color": "#eb2f96"}
        if "HUMAN" in agent_type: return {"icon": "person", "color": "#13c2c2"}
        return {"icon": "smart_toy", "color": "#1890ff"}
    
    for doc in docs:
        meta = map_icon(doc.get("agent", "SYSTEM"))
        activities.append({
            "id": str(doc["_id"]),
            "agent": doc.get("agent", "SYSTEM"),
            "icon": meta["icon"],
            "color": meta["color"],
            "action": doc.get("action", "Performed action"),
            "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else datetime.utcnow().isoformat(),
        })

    return {"activities": activities}

@router.get("/pipeline")
async def dashboard_pipeline(user = Depends(get_current_user)):
    """Get sales pipeline breakdown."""
    company_id = user["company_id"]
    
    cursor = leads_collection.aggregate([
        {"$match": {"company_id": company_id, "crm.stage": {"$ne": None}}},
        {"$group": {
            "_id": "$crm.stage",
            "count": {"$sum": 1},
            "value": {"$sum": {"$toDouble": {"$ifNull": ["$crm.deal_value", 0]}}}
        }}
    ])
    
    docs = await cursor.to_list(100)
    
    stages = []
    for doc in docs:
        if doc["_id"]:
            stages.append({
                "deal_stage": doc["_id"],
                "count": doc["count"],
                "value": doc["value"],
            })
            
    return {
        "stages": stages
    }

@router.get("/priority-targets")
async def priority_targets(user = Depends(get_current_user)):
    """Get top priority leads for the dashboard."""
    company_id = user["company_id"]
    
    cursor = leads_collection.find({"company_id": company_id}).sort("intel.intent_score", -1).limit(6)
    docs = await cursor.to_list(6)
    
    targets = []
    signals = [
        "Viewed pricing page 4x in last 24h",
        "Downloaded Q3 whitepaper",
        "LinkedIn connection accepted",
        "Attended product webinar",
        "Opened 3 emails this week",
        "Visited case studies section",
    ]
    
    for i, lead in enumerate(docs):
        targets.append({
            "id": lead.get("lead_id", str(lead["_id"])),
            "index": i,
            "name": lead.get("profile", {}).get("name", f"Lead {i}"),
            "title": lead.get("profile", {}).get("title", "Unknown"),
            "company": lead.get("profile", {}).get("company", "Unknown"),
            "region": lead.get("profile", {}).get("region", ""),
            "score": round(lead.get("intel", {}).get("intent_score", 0)),
            "signal": signals[i % len(signals)],
        })

    return {"targets": targets}
