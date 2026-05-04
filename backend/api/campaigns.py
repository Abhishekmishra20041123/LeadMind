"""
Campaigns API — Drip Campaign Engine (Phase 2)

Endpoints:
  POST   /api/campaigns/create                → Create drip campaign
  GET    /api/campaigns/list                  → List all campaigns
  GET    /api/campaigns/{campaign_id}         → Campaign details + stats
  POST   /api/campaigns/{campaign_id}/enroll  → Enroll leads
  PATCH  /api/campaigns/{campaign_id}/pause   → Pause/resume
  DELETE /api/campaigns/{campaign_id}         → Delete campaign
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId

from dependencies import get_current_user
from db import (
    campaigns_collection,
    campaign_enrollments_collection,
    leads_collection,
)

router = APIRouter()


# ── Pydantic Models ────────────────────────────────────────────────────────────

class CampaignStep(BaseModel):
    step_id:    str
    day_offset: int               # days after enrollment (0 = immediately)
    channel:    str = "email"
    subject:    str
    content:    str
    conditions: dict = {"proceed_if": "always"}  # always | opened_previous | clicked_previous


class CreateCampaignPayload(BaseModel):
    name:  str
    steps: List[CampaignStep]


class EnrollPayload(BaseModel):
    lead_ids: List[str]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _oid(v) -> ObjectId:
    """Convert str → ObjectId safely."""
    if isinstance(v, ObjectId):
        return v
    return ObjectId(str(v))


def _serialize_campaign(doc: dict) -> dict:
    """Convert MongoDB doc → JSON-safe dict."""
    return {
        "campaign_id":      str(doc["_id"]),
        "name":             doc.get("name", ""),
        "status":           doc.get("status", "active"),
        "steps":            doc.get("steps", []),
        "enrolled_count":   doc.get("enrolled_count", 0),
        "completed_count":  doc.get("completed_count", 0),
        "created_at":       doc.get("created_at", "").isoformat() if isinstance(doc.get("created_at"), datetime) else "",
    }


def _serialize_enrollment(doc: dict) -> dict:
    return {
        "enrollment_id": str(doc["_id"]),
        "campaign_id":   str(doc.get("campaign_id", "")),
        "lead_id":       doc.get("lead_id", ""),
        "current_step":  doc.get("current_step", ""),
        "status":        doc.get("status", "active"),
        "enrolled_at":   doc.get("enrolled_at", "").isoformat() if isinstance(doc.get("enrolled_at"), datetime) else "",
        "next_step_at":  doc.get("next_step_at", "").isoformat() if isinstance(doc.get("next_step_at"), datetime) else "",
    }


# ── POST /api/campaigns/create ─────────────────────────────────────────────────

@router.post("/create")
async def create_campaign(payload: CreateCampaignPayload, user=Depends(get_current_user)):
    """Create a new drip campaign with ordered steps."""
    company_id = user["company_id"]

    if not payload.steps:
        raise HTTPException(status_code=400, detail="Campaign must have at least one step")

    # Validate step_ids are unique
    step_ids = [s.step_id for s in payload.steps]
    if len(step_ids) != len(set(step_ids)):
        raise HTTPException(status_code=400, detail="step_id values must be unique")

    steps_data = [s.model_dump() for s in payload.steps]

    result = await campaigns_collection.insert_one({
        "company_id":      company_id,
        "name":            payload.name,
        "status":          "active",
        "steps":           steps_data,
        "enrolled_count":  0,
        "completed_count": 0,
        "created_at":      datetime.utcnow(),
        "updated_at":      datetime.utcnow(),
    })

    return {"ok": True, "campaign_id": str(result.inserted_id)}


# ── GET /api/campaigns/list ────────────────────────────────────────────────────

@router.get("/list")
async def list_campaigns(user=Depends(get_current_user)):
    """List all campaigns for this company with enrollment stats."""
    company_id = user["company_id"]
    cursor = campaigns_collection.find({"company_id": company_id}).sort("created_at", -1)
    docs = await cursor.to_list(length=200)
    return {"campaigns": [_serialize_campaign(d) for d in docs]}


# ── GET /api/campaigns/{campaign_id} ──────────────────────────────────────────

@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, user=Depends(get_current_user)):
    """Get campaign details including step-by-step enrollment stats."""
    company_id = user["company_id"]

    doc = await campaigns_collection.find_one({
        "_id": _oid(campaign_id), "company_id": company_id
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Gather per-step counts from enrollments
    steps = doc.get("steps", [])
    step_stats = {}
    for step in steps:
        sid = step["step_id"]
        count = await campaign_enrollments_collection.count_documents({
            "campaign_id": _oid(campaign_id),
            "current_step": sid,
            "company_id": company_id,
        })
        step_stats[sid] = count

    # Enrollment breakdown
    total     = await campaign_enrollments_collection.count_documents({"campaign_id": _oid(campaign_id), "company_id": company_id})
    active    = await campaign_enrollments_collection.count_documents({"campaign_id": _oid(campaign_id), "company_id": company_id, "status": "active"})
    completed = await campaign_enrollments_collection.count_documents({"campaign_id": _oid(campaign_id), "company_id": company_id, "status": "completed"})
    dropped   = await campaign_enrollments_collection.count_documents({"campaign_id": _oid(campaign_id), "company_id": company_id, "status": "dropped"})

    serialized = _serialize_campaign(doc)
    serialized["step_stats"]     = step_stats
    serialized["total_enrolled"] = total
    serialized["active"]         = active
    serialized["completed"]      = completed
    serialized["dropped"]        = dropped

    return serialized


# ── POST /api/campaigns/{campaign_id}/enroll ──────────────────────────────────

@router.post("/{campaign_id}/enroll")
async def enroll_leads(campaign_id: str, payload: EnrollPayload, user=Depends(get_current_user)):
    """Enroll one or more leads into a campaign."""
    company_id = user["company_id"]

    doc = await campaigns_collection.find_one({
        "_id": _oid(campaign_id), "company_id": company_id
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if doc.get("status") == "paused":
        raise HTTPException(status_code=400, detail="Cannot enroll into a paused campaign")

    steps = doc.get("steps", [])
    if not steps:
        raise HTTPException(status_code=400, detail="Campaign has no steps")

    first_step    = min(steps, key=lambda s: s.get("day_offset", 0))
    first_step_id = first_step["step_id"]
    first_offset  = first_step.get("day_offset", 0)

    enrolled = 0
    skipped  = 0

    for lead_id in payload.lead_ids:
        # Skip if already enrolled and still active
        existing = await campaign_enrollments_collection.find_one({
            "campaign_id": _oid(campaign_id),
            "lead_id": lead_id,
            "status": "active",
        })
        if existing:
            skipped += 1
            continue

        # Verify lead belongs to this company
        lead = await leads_collection.find_one({"lead_id": lead_id, "company_id": company_id})
        if not lead:
            skipped += 1
            continue

        now = datetime.utcnow()
        await campaign_enrollments_collection.insert_one({
            "campaign_id":  _oid(campaign_id),
            "lead_id":      lead_id,
            "company_id":   company_id,
            "current_step": first_step_id,
            "status":       "active",
            "enrolled_at":  now,
            "next_step_at": now + timedelta(days=first_offset),
            "step_history": [],
        })
        enrolled += 1

    # Update campaign enrollment count
    if enrolled > 0:
        await campaigns_collection.update_one(
            {"_id": _oid(campaign_id)},
            {"$inc": {"enrolled_count": enrolled}}
        )

    return {"ok": True, "enrolled": enrolled, "skipped": skipped}


# ── PATCH /api/campaigns/{campaign_id}/pause ──────────────────────────────────

@router.patch("/{campaign_id}/pause")
async def pause_resume_campaign(campaign_id: str, user=Depends(get_current_user)):
    """Toggle a campaign between active and paused."""
    company_id = user["company_id"]

    doc = await campaigns_collection.find_one({
        "_id": _oid(campaign_id), "company_id": company_id
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Campaign not found")

    new_status = "paused" if doc.get("status") == "active" else "active"
    await campaigns_collection.update_one(
        {"_id": _oid(campaign_id)},
        {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
    )
    return {"ok": True, "status": new_status}


# ── DELETE /api/campaigns/{campaign_id} ───────────────────────────────────────

@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str, user=Depends(get_current_user)):
    """Delete a campaign and all its enrollments."""
    company_id = user["company_id"]

    doc = await campaigns_collection.find_one({
        "_id": _oid(campaign_id), "company_id": company_id
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Campaign not found")

    await campaign_enrollments_collection.delete_many({"campaign_id": _oid(campaign_id)})
    await campaigns_collection.delete_one({"_id": _oid(campaign_id)})

    return {"ok": True, "deleted_campaign_id": campaign_id}
