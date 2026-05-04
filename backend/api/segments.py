from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId

from db import segments_collection, leads_collection
from dependencies import get_current_user
import json
import os
from api.agents import OllamaWrapper

router = APIRouter()

# ── Models ────────────────────────────────────────────────────────────────────

class Rule(BaseModel):
    field: str
    operator: str # eq, neq, gt, gte, lt, lte, contains
    value: Any

class SegmentCreateRequest(BaseModel):
    name: str
    rules: List[Rule]
    logic: str = "AND"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize(doc: dict) -> dict:
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    if "company_id" in doc:
        doc["company_id"] = str(doc["company_id"])
    return doc

def build_mongo_query(company_id: ObjectId, rules: List[Rule], logic: str) -> dict:
    query = {"company_id": company_id}
    if not rules:
        return query

    conditions = []
    for r in rules:
        if r.operator == "eq":
            conditions.append({r.field: r.value})
        elif r.operator == "neq":
            conditions.append({r.field: {"$ne": r.value}})
        elif r.operator == "gt":
            conditions.append({r.field: {"$gt": r.value}})
        elif r.operator == "gte":
            conditions.append({r.field: {"$gte": r.value}})
        elif r.operator == "lt":
            conditions.append({r.field: {"$lt": r.value}})
        elif r.operator == "lte":
            conditions.append({r.field: {"$lte": r.value}})
        elif r.operator == "contains":
            conditions.append({r.field: {"$regex": str(r.value), "$options": "i"}})

    if not conditions:
        return query

    if logic.upper() == "OR":
        query["$or"] = conditions
    else:
        query["$and"] = conditions
        
    return query

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/create")
async def create_segment(req: SegmentCreateRequest, user=Depends(get_current_user)):
    """Create a new smart segment."""
    company_id = user["company_id"]
    
    # Calculate initial member count
    query = build_mongo_query(company_id, req.rules, req.logic)
    member_count = await leads_collection.count_documents(query)

    doc = {
        "company_id": company_id,
        "name": req.name,
        "rules": [r.model_dump() for r in req.rules],
        "logic": req.logic,
        "auto_refresh": True,
        "member_count": member_count,
        "created_at": datetime.now(timezone.utc)
    }
    
    res = await segments_collection.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    doc["company_id"] = str(company_id)
    return doc


@router.get("/list")
async def list_segments(user=Depends(get_current_user)):
    """Lists all segments. Recalculates their counts on the fly."""
    company_id = user["company_id"]
    cursor = segments_collection.find({"company_id": company_id}).sort("created_at", -1)
    segments = []
    async for s in cursor:
        # Auto refresh count
        if s.get("auto_refresh", True):
            query = build_mongo_query(company_id, [Rule(**r) for r in s.get("rules", [])], s.get("logic", "AND"))
            count = await leads_collection.count_documents(query)
            if count != s.get("member_count"):
                await segments_collection.update_one({"_id": s["_id"]}, {"$set": {"member_count": count}})
                s["member_count"] = count
        segments.append(_serialize(s))
    
    return {"segments": segments}


@router.get("/{segment_id}")
async def get_segment(segment_id: str, limit: int = 50, skip: int = 0, user=Depends(get_current_user)):
    """Get segment details along with its paginated members."""
    company_id = user["company_id"]
    try:
        sid = ObjectId(segment_id)
    except:
        raise HTTPException(400, "Invalid ID")

    segment = await segments_collection.find_one({"_id": sid, "company_id": company_id})
    if not segment:
        raise HTTPException(404, "Segment not found")

    query = build_mongo_query(company_id, [Rule(**r) for r in segment.get("rules", [])], segment.get("logic", "AND"))
    
    leads_cursor = leads_collection.find(query).skip(skip).limit(limit)
    leads = [ _serialize(doc) async for doc in leads_cursor ]

    segment = _serialize(segment)
    return {
        "segment": segment,
        "members": leads
    }

@router.delete("/{segment_id}")
async def delete_segment(segment_id: str, user=Depends(get_current_user)):
    """Delete a segment."""
    company_id = user["company_id"]
    try:
        sid = ObjectId(segment_id)
    except:
        raise HTTPException(400, "Invalid ID")
        
    await segments_collection.delete_one({"_id": sid, "company_id": company_id})
    return {"ok": True}

@router.post("/ai-suggest")
async def ai_suggest_segments(user=Depends(get_current_user)):
    """Analyze a sample of leads and suggest new segments."""
    company_id = user["company_id"]
    
    # Grab up to 20 random leads for context
    sample = []
    async for lead in leads_collection.aggregate([
        {"$match": {"company_id": company_id}},
        {"$sample": {"size": 20}}
    ]):
        sample.append({
            "industry": lead.get("intel", {}).get("industry", ""),
            "intent_score": lead.get("intel", {}).get("intent_score", 0),
            "pipeline_stage": lead.get("pipeline_stage", ""),
            "title": lead.get("profile", {}).get("title", ""),
            "status": lead.get("status", "")
        })
        
    # Initialize Minimax model
    llm = OllamaWrapper()
    
    prompt = f"""You are an AI sales operations expert. 
Based on this sample of 20 leads from our CRM, suggest 3 highly effective segments we could create.
Only suggest segments using these valid schema fields:
- intel.intent_score (number 0-100)
- pipeline_stage (string e.g. 'New Lead', 'Qualified', 'Lost', 'Won')
- profile.title (string)
- status (string e.g. 'Lead', 'Contacted')

Sample JSON:
{json.dumps(sample)}

Return ONLY a JSON array of segment objects. Exclude markdown formatting.
Schema per object:
{{
   "name": "Segment Title",
   "logic": "AND",
   "rules": [
      {{"field": "field_name", "operator": "eq|neq|gt|gte|lt|lte|contains", "value": val}}
   ]
}}"""

    try:
        res = llm.generate_content(prompt)
        text = res.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.endswith("```"): text = text[:-3]
        suggestions = json.loads(text)
        return {"suggestions": suggestions}
    except Exception as e:
        print("AI Suggest Error:", e)
        # Fallback
        return {"suggestions": [
            {"name": "High Intent Prospects", "logic": "AND", "rules": [{"field": "intel.intent_score", "operator": "gte", "value": 75}]},
        ]}
