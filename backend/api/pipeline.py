"""
Pipeline API — Deal Pipeline Kanban Board (Phase 1)

Endpoints:
  GET  /api/pipeline/board     — Leads grouped by stage for kanban UI
  POST /api/pipeline/move      — Move a lead to a new stage (drag-drop)
  GET  /api/pipeline/stages    — Get configured stages for company
  POST /api/pipeline/stages    — Create or reset company stage config
  GET  /api/pipeline/forecast  — Revenue forecast (value × stage probability)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from bson import ObjectId

from dependencies import get_current_user
from db import leads_collection, pipeline_stages_collection, agent_activity_collection

router = APIRouter()

# ── Default Stages ─────────────────────────────────────────────────────────────

DEFAULT_STAGES = [
    {"name": "New Lead",      "order": 0, "color": "#3B82F6", "probability": 0.10},
    {"name": "Contacted",     "order": 1, "color": "#F59E0B", "probability": 0.25},
    {"name": "Qualified",     "order": 2, "color": "#10B981", "probability": 0.50},
    {"name": "Proposal Sent", "order": 3, "color": "#8B5CF6", "probability": 0.75},
    {"name": "Negotiation",   "order": 4, "color": "#EC4899", "probability": 0.90},
    {"name": "Won",           "order": 5, "color": "#22C55E", "probability": 1.00},
    {"name": "Lost",          "order": 6, "color": "#EF4444", "probability": 0.00},
]

# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_company_stages(company_id: ObjectId) -> list:
    """Return stages for a company, seeding defaults if none exist yet."""
    doc = await pipeline_stages_collection.find_one({"company_id": company_id})
    if doc:
        return doc["stages"]
    # Auto-seed defaults on first access
    await pipeline_stages_collection.insert_one({
        "company_id": company_id,
        "stages": DEFAULT_STAGES,
        "created_at": datetime.utcnow(),
    })
    return DEFAULT_STAGES


def _serialize_lead_card(lead: dict) -> dict:
    """Extract only the fields needed to render a Kanban card."""
    profile  = lead.get("profile", {})
    intel    = lead.get("intel", {})
    crm      = lead.get("crm", {})
    contact  = lead.get("contact", {})

    # Days in current stage
    moved_at = lead.get("pipeline_stage_moved_at")
    days_in_stage = 0
    if moved_at:
        try:
            delta = datetime.utcnow() - moved_at
            days_in_stage = delta.days
        except Exception:
            days_in_stage = 0

    return {
        "lead_id":        lead.get("lead_id", str(lead["_id"])),
        "name":           profile.get("name", "Unknown"),
        "company":        profile.get("company", ""),
        "title":          profile.get("title", ""),
        "email":          contact.get("email", ""),
        "intent_score":   round(intel.get("intent_score", 0)),
        "deal_value":     crm.get("deal_value", 0),
        "pipeline_stage": lead.get("pipeline_stage", "New Lead"),
        "days_in_stage":  days_in_stage,
        "email_sent":     intel.get("email", {}).get("sent", False),
        "status":         lead.get("status", ""),
        "source":         lead.get("source", "csv"),
    }


# ── GET /api/pipeline/stages ───────────────────────────────────────────────────

@router.get("/stages")
async def get_stages(user=Depends(get_current_user)):
    """Get the Kanban stage configuration for this company."""
    stages = await _get_company_stages(user["company_id"])
    return {"stages": stages}


# ── POST /api/pipeline/stages ──────────────────────────────────────────────────

class StagesPayload(BaseModel):
    stages: list  # list of {name, order, color, probability}

@router.post("/stages")
async def update_stages(payload: StagesPayload, user=Depends(get_current_user)):
    """Create or replace the Kanban stage configuration."""
    company_id = user["company_id"]
    await pipeline_stages_collection.update_one(
        {"company_id": company_id},
        {"$set": {"stages": payload.stages, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"ok": True, "stages": payload.stages}


# ── GET /api/pipeline/board ────────────────────────────────────────────────────

@router.get("/board")
async def get_board(user=Depends(get_current_user)):
    """
    Return leads grouped by pipeline stage, in stage order.
    Used to render the Kanban columns.
    """
    company_id = user["company_id"]
    stages = await _get_company_stages(company_id)

    # Fetch all leads for this company
    cursor = leads_collection.find({"company_id": company_id})
    leads = await cursor.to_list(length=2000)

    # Build a map: stage_name → [cards]
    stage_names = [s["name"] for s in stages]
    board: dict[str, list] = {name: [] for name in stage_names}

    for lead in leads:
        stage = lead.get("pipeline_stage", "New Lead")
        if stage not in board:
            stage = "New Lead"     # fallback for any unrecognised stage
        board[stage].append(_serialize_lead_card(lead))

    # Assemble ordered columns
    columns = []
    for s in stages:
        columns.append({
            "stage":       s["name"],
            "order":       s["order"],
            "color":       s["color"],
            "probability": s["probability"],
            "leads":       board[s["name"]],
            "count":       len(board[s["name"]]),
            "value":       sum(l.get("deal_value", 0) or 0 for l in board[s["name"]]),
        })

    return {"columns": columns}


# ── POST /api/pipeline/move ────────────────────────────────────────────────────

class MovePayload(BaseModel):
    lead_id:   str
    new_stage: str
    note:      Optional[str] = None

@router.post("/move")
async def move_lead(payload: MovePayload, user=Depends(get_current_user)):
    """
    Move a lead to a new Kanban stage.
    Called when the user drags a card to a different column.
    """
    company_id = user["company_id"]

    # Validate stage exists for this company
    stages = await _get_company_stages(company_id)
    valid_names = [s["name"] for s in stages]
    if payload.new_stage not in valid_names:
        raise HTTPException(status_code=400, detail=f"Invalid stage: '{payload.new_stage}'")

    # Update lead
    result = await leads_collection.update_one(
        {"lead_id": payload.lead_id, "company_id": company_id},
        {"$set": {
            "pipeline_stage":          payload.new_stage,
            "pipeline_stage_moved_at": datetime.utcnow(),
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Audit trail in agent_activity
    await agent_activity_collection.insert_one({
        "company_id": company_id,
        "lead_id":    payload.lead_id,
        "agent":      "HUMAN",
        "action":     f"Moved lead to stage: {payload.new_stage}" + (f" — {payload.note}" if payload.note else ""),
        "status":     "SUCCESS",
        "timestamp":  datetime.utcnow(),
    })

    return {"ok": True, "lead_id": payload.lead_id, "stage": payload.new_stage}


# ── GET /api/pipeline/forecast ─────────────────────────────────────────────────

@router.get("/forecast")
async def get_forecast(user=Depends(get_current_user)):
    """
    Revenue forecast: for each stage, sum deal_value × stage probability.
    Also returns total weighted forecast and total raw pipeline value.
    """
    company_id = user["company_id"]
    stages = await _get_company_stages(company_id)
    prob_map = {s["name"]: s["probability"] for s in stages}

    cursor = leads_collection.aggregate([
        {"$match": {"company_id": company_id}},
        {"$group": {
            "_id":   {"$ifNull": ["$pipeline_stage", "New Lead"]},
            "count": {"$sum": 1},
            "value": {"$sum": {"$toDouble": {"$ifNull": ["$crm.deal_value", 0]}}}
        }}
    ])
    rows = await cursor.to_list(100)

    forecast_rows = []
    total_raw = 0
    total_weighted = 0

    for row in rows:
        stage   = row["_id"] or "New Lead"
        value   = row["value"]
        count   = row["count"]
        prob    = prob_map.get(stage, 0.1)
        weighted = round(value * prob, 2)

        total_raw      += value
        total_weighted += weighted

        forecast_rows.append({
            "stage":           stage,
            "count":           count,
            "raw_value":       value,
            "probability":     prob,
            "weighted_value":  weighted,
        })

    # Sort by stage order
    stage_order = {s["name"]: s["order"] for s in stages}
    forecast_rows.sort(key=lambda r: stage_order.get(r["stage"], 99))

    return {
        "forecast":       forecast_rows,
        "total_raw":      round(total_raw, 2),
        "total_weighted": round(total_weighted, 2),
    }
