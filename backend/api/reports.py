import csv
from io import StringIO
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from datetime import datetime, timezone, timedelta
from typing import Optional

from db import (
    leads_collection, 
    email_events_collection, 
    pipeline_stages_collection, 
    agent_activity_collection,
    campaigns_collection
)
from dependencies import get_current_user

router = APIRouter()

@router.get("/email-performance")
async def email_performance(days: int = 30, user=Depends(get_current_user)):
    """Return email performance (opens/clicks) grouped by day."""
    company_id = user["company_id"]
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    pipeline = [
        {"$match": {
            "company_id": company_id, 
            "timestamp": {"$gte": start_date}
        }},
        {"$group": {
            "_id": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "event_type": "$event_type"
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.date": 1}}
    ]
    
    events = []
    async for e in email_events_collection.aggregate(pipeline):
        events.append({
            "date": e["_id"]["date"],
            "event_type": e["_id"]["event_type"],
            "count": e["count"]
        })
    
    # Process into daily buckets
    data = {}
    for ev in events:
        d = ev["date"]
        if d not in data:
            data[d] = {"date": d, "opens": 0, "clicks": 0, "sends": 0}
        type_str = ev["event_type"].lower()
        if type_str == "open": data[d]["opens"] += ev["count"]
        elif type_str == "click": data[d]["clicks"] += ev["count"]
        elif type_str == "sent": data[d]["sends"] += ev["count"]

    return {"data": list(data.values())}


@router.get("/conversion-funnel")
async def conversion_funnel(user=Depends(get_current_user)):
    """Counts leads in each pipeline stage following the correct sequential order."""
    company_id = user["company_id"]
    
    stages_doc = await pipeline_stages_collection.find_one({"company_id": company_id})
    stages = stages_doc["stages"] if stages_doc else []
    if not stages:
        # Fallback to defaults
        stages = [
            {"name": "New Lead", "order": 0},
            {"name": "Contacted", "order": 1},
            {"name": "Qualified", "order": 2},
            {"name": "Proposal Sent", "order": 3},
            {"name": "Negotiation", "order": 4},
            {"name": "Won", "order": 5},
            {"name": "Lost", "order": 6}
        ]
        
    stages = sorted(stages, key=lambda x: x["order"])
    
    pipeline = [
        {"$match": {"company_id": company_id}},
        {"$group": {"_id": "$pipeline_stage", "count": {"$sum": 1}}}
    ]
    
    counts = {}
    async for c in leads_collection.aggregate(pipeline):
        # handle missing pipeline_stage by grouping as "New Lead"
        counts[c["_id"] or "New Lead"] = c["count"]
        
    funnel = []
    for st in stages:
        funnel.append({
            "id": st["name"],
            "label": st["name"],
            "value": counts.get(st["name"], 0),
            "color": st.get("color", "#3B82F6")
        })
        
    return {"funnel": funnel}


@router.get("/agent-performance")
async def agent_performance(user=Depends(get_current_user)):
    """Returns AI success stats based on agent_activity."""
    company_id = user["company_id"]
    
    pipeline = [
        {"$match": {"company_id": company_id}},
        {"$group": {
            "_id": "$agent_name",
            "calls": {"$sum": 1},
            "successes": {"$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}}
        }}
    ]
    
    data = []
    async for a in agent_activity_collection.aggregate(pipeline):
        calls = a["calls"]
        successes = a["successes"]
        rate = round(successes/calls*100) if calls > 0 else 0
        data.append({
            "agent": a["_id"],
            "calls": calls,
            "success_rate": rate
        })
        
    return {"data": data}


@router.get("/revenue-forecast")
async def revenue_forecast(user=Depends(get_current_user)):
    """Calculates deal value * probability matching the pipeline dashboard."""
    company_id = user["company_id"]
    stages_doc = await pipeline_stages_collection.find_one({"company_id": company_id})
    stages = stages_doc.get("stages", []) if stages_doc else []
    
    prob_map = {s["name"]: s.get("probability", 0.0) for s in stages}
    if not prob_map:
        prob_map = {
            "New Lead": 0.1, "Contacted": 0.25, "Qualified": 0.5,
            "Proposal Sent": 0.75, "Negotiation": 0.9, "Won": 1.0, "Lost": 0.0
        }

    pipeline = [
        {"$match": {"company_id": company_id, "pipeline_stage": {"$ne": "Lost"}}},
        {"$group": {
            "_id": "$pipeline_stage",
            "total_deal_value": {"$sum": "$intel.deal_value"}
        }}
    ]
    
    forecast = 0
    actual = 0
    async for s in leads_collection.aggregate(pipeline):
        st = s["_id"] or "New Lead"
        prob = prob_map.get(st, 0.0)
        value = s["total_deal_value"] or 0
        forecast += value * prob
        actual += value
        
    return {
        "pipeline_total": actual,
        "weighted_forecast": forecast
    }

@router.get("/campaign-comparison")
async def campaign_comparison(user=Depends(get_current_user)):
    """Compare performance across all active drip campaigns."""
    company_id = user["company_id"]
    
    data = []
    async for c in campaigns_collection.find({"company_id": company_id}):
        data.append({
            "name": c.get("name"),
            "enrolled": c.get("enrolled_count", 0),
            "completed": c.get("completed_count", 0),
            "status": c.get("status", "active")
        })
        
    return {"data": data}

@router.get("/export")
async def export_leads(user=Depends(get_current_user)):
    """Export all leads to CSV."""
    company_id = user["company_id"]
    
    f = StringIO()
    writer = csv.writer(f)
    writer.writerow([
        "Lead ID", "Source", "Name", "Email", "Company", "Title",
        "Pipeline Stage", "Deal Value", "Intent Score", "Last Contacted", "Created At"
    ])
    
    async for lead in leads_collection.find({"company_id": company_id}):
        prof = lead.get("profile", {})
        intel = lead.get("intel", {})
        writer.writerow([
            lead.get("lead_id"),
            lead.get("source"),
            prof.get("name", ""),
            prof.get("email", ""),
            prof.get("company", ""),
            prof.get("title", ""),
            lead.get("pipeline_stage", "New Lead"),
            intel.get("deal_value", 0),
            intel.get("intent_score", 0),
            lead.get("last_contacted_at", ""),
            lead.get("_id").generation_time.isoformat() if "_id" in lead else ""
        ])
        
    response = Response(content=f.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=leadmind_export.csv"
    return response
