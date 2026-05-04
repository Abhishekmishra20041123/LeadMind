"""
Phase 6 — Task Management API
Endpoints: create, list (my-tasks), update, overdue, AI-suggest
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid, os, traceback

from db import tasks_collection, leads_collection
from dependencies import get_current_user
from bson import ObjectId

router = APIRouter()

# ── Pydantic ──────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    lead_id: Optional[str] = None
    title: str
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None          # ISO string e.g. "2024-06-15T10:00:00"
    priority: str = "medium"                # high | medium | low
    source: str = "manual"                  # manual | ai

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None           # pending | done | cancelled
    priority: Optional[str] = None
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


def _serialize(doc: dict) -> dict:
    """Safely convert MongoDB doc to JSON-ready dict by converting ObjectIds and datetimes."""
    if not doc: return {}
    
    # 1. Handle the main ID
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    elif "id" not in doc and "task_id" in doc:
        doc["id"] = doc["task_id"]

    # 2. Iterate and convert types that JSON doesn't like
    for k, v in doc.items():
        # Convert all ObjectIds (like company_id) to strings
        if isinstance(v, ObjectId):
            doc[k] = str(v)
        # Convert any remaining datetimes to ISO strings
        elif isinstance(v, datetime):
            doc[k] = v.isoformat()
            
    return doc


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/create")
async def create_task(payload: TaskCreate, user=Depends(get_current_user)):
    company_id_oid = user["company_id"]

    due = None
    if payload.due_date:
        try:
            due = datetime.fromisoformat(payload.due_date)
        except ValueError:
            raise HTTPException(400, "Invalid due_date ISO format")

    task = {
        "task_id":    f"T_{uuid.uuid4().hex[:8].upper()}",
        "company_id": company_id_oid,
        "lead_id":    payload.lead_id,
        "title":      payload.title,
        "assigned_to": payload.assigned_to or user.get("email", ""),
        "due_date":   due,
        "priority":   payload.priority,
        "status":     "pending",
        "source":     payload.source,
        "notes":      "",
        "created_at": datetime.now(timezone.utc),
    }
    result = await tasks_collection.insert_one(task)
    task["id"] = str(result.inserted_id)
    task.pop("_id", None)
    if isinstance(task.get("due_date"), datetime):
        task["due_date"] = task["due_date"].isoformat()
    task["created_at"] = task["created_at"].isoformat()
    return task


@router.get("/my-tasks")
async def my_tasks(user=Depends(get_current_user)):
    try:
        email = user.get('email')
        company_id_oid = user["company_id"]
        print(f"DEBUG: my_tasks fetching for {email} (CID: {company_id_oid})")
        
        cursor = tasks_collection.find(
            {"company_id": company_id_oid}
        ).sort([("due_date", 1), ("priority", 1)])
        tasks = []
        async for t in cursor:
            tasks.append(_serialize(t))
        print(f"DEBUG: my_tasks returning {len(tasks)} tasks")
        return {"tasks": tasks}
    except Exception as e:
        print(f"ERROR in my_tasks: {traceback.format_exc()}")
        raise


@router.patch("/{task_id}")
async def update_task(task_id: str, payload: TaskUpdate, user=Depends(get_current_user)):
    company_id_oid = user["company_id"]
    updates: dict = {k: v for k, v in payload.dict(exclude_none=True).items()}
    if "due_date" in updates and updates["due_date"]:
        try:
            updates["due_date"] = datetime.fromisoformat(updates["due_date"])
        except ValueError:
            raise HTTPException(400, "Invalid due_date ISO format")

    result = await tasks_collection.update_one(
        {"task_id": task_id, "company_id": company_id_oid},
        {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Task not found")
    return {"success": True}


@router.get("/overdue")
async def overdue_tasks(user=Depends(get_current_user)):
    company_id_oid = user["company_id"]
    now = datetime.now(timezone.utc)
    cursor = tasks_collection.find({
        "company_id": company_id_oid,
        "status": "pending",
        "due_date": {"$lt": now}
    }).sort([("due_date", 1)])
    tasks = []
    async for t in cursor:
        tasks.append(_serialize(t))
    return {"tasks": tasks, "count": len(tasks)}


@router.post("/ai-suggest")
async def ai_suggest_tasks(user=Depends(get_current_user)):
    """Use Minimax 2.7 (Ollama) to analyse hot leads and suggest follow-up tasks."""
    from api.agents import OllamaWrapper
    import json as _json

    company_id_oid = user["company_id"]
    
    # Initialize Minimax model
    llm = OllamaWrapper()

    # Grab up to 10 hot leads
    leads = []
    async for lead in leads_collection.find(
        {"company_id": company_id_oid, "intel.intent_score": {"$gte": 60}},
        {"profile": 1, "intel": 1, "lead_id": 1, "crm": 1}
    ).limit(10):
        lead.pop("_id", None)
        leads.append(lead)

    if not leads:
        return {"tasks": []}

    prompt = f"""
    You are a sales coach. Given these high-intent leads, suggest exactly 5 specific follow-up tasks.
    Return ONLY a JSON array (no markdown) where each object has:
      lead_id, title (action-oriented, ≤12 words), priority (high/medium/low), due_days_from_now (int)

    Leads:
    {_json.dumps(leads, default=str)}
    """
    
    resp = llm.generate_content(prompt)
    raw = resp.text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    
    try:
        suggestions = _json.loads(raw)
        return {"tasks": suggestions[:5]}
    except Exception:
        return {"tasks": [], "raw": raw}
