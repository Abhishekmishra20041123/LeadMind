"""
A/B Testing API — Statistical Email Variant Testing (Phase 2)

Endpoints:
  POST /api/ab/create                   → Create A/B test with variants
  GET  /api/ab/list                     → List all A/B tests
  GET  /api/ab/{test_id}                → Results per variant
  POST /api/ab/{test_id}/declare-winner → Send winning variant to remainder
"""

import math
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

from dependencies import get_current_user
from db import ab_tests_collection, leads_collection, email_logs_collection

router = APIRouter()


# ── Pydantic Models ────────────────────────────────────────────────────────────

class ABVariant(BaseModel):
    id:      str           # "A", "B", etc.
    subject: str
    content: str


class CreateABTestPayload(BaseModel):
    name:         str
    lead_ids:     List[str]
    variants:     List[ABVariant]      # exactly 2 supported
    split_ratio:  Optional[List[int]] = None   # e.g. [50, 50]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _oid(v) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    return ObjectId(str(v))


def _serialize_test(doc: dict) -> dict:
    return {
        "test_id":      str(doc["_id"]),
        "name":         doc.get("name", ""),
        "status":       doc.get("status", "running"),
        "variants":     doc.get("variants", []),
        "winner":       doc.get("winner"),
        "split_ratio":  doc.get("split_ratio", [50, 50]),
        "sample_size":  doc.get("sample_size", 0),
        "created_at":   doc.get("created_at", "").isoformat() if isinstance(doc.get("created_at"), datetime) else "",
        "significance": doc.get("significance"),
        "lead_ids":     doc.get("lead_ids", []),
    }


def _z_score(opens_a: int, sent_a: int, opens_b: int, sent_b: int) -> float:
    """
    Two-proportion z-test.
    Returns the z-score comparing variant A open rate vs B open rate.
    """
    if sent_a == 0 or sent_b == 0:
        return 0.0
    p_a = opens_a / sent_a
    p_b = opens_b / sent_b
    p_pool = (opens_a + opens_b) / (sent_a + sent_b)
    if p_pool == 0 or p_pool == 1:
        return 0.0
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / sent_a + 1 / sent_b))
    if se == 0:
        return 0.0
    return abs(p_a - p_b) / se


def _is_significant(z: float, confidence: float = 0.95) -> bool:
    """
    95% confidence → z > 1.96
    99% confidence → z > 2.576
    """
    threshold = 1.96 if confidence == 0.95 else 2.576
    return z >= threshold


# ── POST /api/ab/create ───────────────────────────────────────────────────────

@router.post("/create")
async def create_ab_test(payload: CreateABTestPayload, user=Depends(get_current_user)):
    """Create a new A/B test and assign leads to variants."""
    company_id = user["company_id"]

    if len(payload.variants) < 2:
        raise HTTPException(status_code=400, detail="At least 2 variants are required")
    if not payload.lead_ids:
        raise HTTPException(status_code=400, detail="At least 1 lead_id is required")

    n_variants = len(payload.variants)
    split      = payload.split_ratio or [100 // n_variants] * n_variants

    # Assign leads round-robin across variants
    variants_data = []
    for i, v in enumerate(payload.variants):
        variants_data.append({
            "id":      v.id,
            "subject": v.subject,
            "content": v.content,
            "sent":    0,
            "opens":   0,
            "clicks":  0,
            "lead_ids": [],    # leads assigned to this variant
        })

    for idx, lead_id in enumerate(payload.lead_ids):
        bucket = idx % n_variants
        variants_data[bucket]["lead_ids"].append(lead_id)
        variants_data[bucket]["sent"] += 1

    result = await ab_tests_collection.insert_one({
        "company_id":  company_id,
        "name":        payload.name,
        "status":      "running",
        "variants":    variants_data,
        "winner":      None,
        "split_ratio": split,
        "sample_size": len(payload.lead_ids),
        "lead_ids":    payload.lead_ids,
        "created_at":  datetime.utcnow(),
    })

    return {"ok": True, "test_id": str(result.inserted_id)}


# ── GET /api/ab/list ──────────────────────────────────────────────────────────

@router.get("/list")
async def list_ab_tests(user=Depends(get_current_user)):
    """List all A/B tests for this company."""
    company_id = user["company_id"]
    cursor = ab_tests_collection.find({"company_id": company_id}).sort("created_at", -1)
    docs = await cursor.to_list(length=100)
    return {"tests": [_serialize_test(d) for d in docs]}


# ── GET /api/ab/{test_id} ─────────────────────────────────────────────────────

@router.get("/{test_id}")
async def get_ab_test(test_id: str, user=Depends(get_current_user)):
    """
    Return full A/B test results including live open/click stats
    and computed statistical significance.
    """
    company_id = user["company_id"]

    doc = await ab_tests_collection.find_one({
        "_id": _oid(test_id), "company_id": company_id
    })
    if not doc:
        raise HTTPException(status_code=404, detail="A/B test not found")

    variants = doc.get("variants", [])

    # Hydrate open/click counts from email_logs if available
    for v in variants:
        lead_ids_in_variant = v.get("lead_ids", [])
        if lead_ids_in_variant:
            pipeline = [
                {"$match": {
                    "company_id": company_id,
                    "lead_id": {"$in": lead_ids_in_variant},
                    "ab_test_id": str(doc["_id"]),
                    "ab_variant": v["id"],
                }},
                {"$group": {
                    "_id": None,
                    "opens":  {"$sum": {"$cond": [{"$gt": ["$open_count", 0]}, 1, 0]}},
                    "clicks": {"$sum": {"$cond": [{"$gt": ["$click_count", 0]}, 1, 0]}},
                }}
            ]
            rows = await email_logs_collection.aggregate(pipeline).to_list(1)
            if rows:
                v["opens"]  = rows[0].get("opens", v.get("opens", 0))
                v["clicks"] = rows[0].get("clicks", v.get("clicks", 0))

    # Compute statistical significance (for 2-variant tests)
    significance = None
    if len(variants) == 2:
        z = _z_score(
            variants[0].get("opens", 0), variants[0].get("sent", 1),
            variants[1].get("opens", 0), variants[1].get("sent", 1),
        )
        significance = {
            "z_score":       round(z, 3),
            "is_significant": _is_significant(z),
            "confidence":    "95%",
        }

    result = _serialize_test(doc)
    result["variants"]    = variants
    result["significance"] = significance
    return result


# ── POST /api/ab/{test_id}/declare-winner ─────────────────────────────────────

class DeclareWinnerPayload(BaseModel):
    winner_variant_id: str


@router.post("/{test_id}/declare-winner")
async def declare_winner(test_id: str, payload: DeclareWinnerPayload, user=Depends(get_current_user)):
    """
    Manually declare a winner variant.
    Marks the test as completed with the given winner variant ID.
    """
    company_id = user["company_id"]

    doc = await ab_tests_collection.find_one({
        "_id": _oid(test_id), "company_id": company_id
    })
    if not doc:
        raise HTTPException(status_code=404, detail="A/B test not found")
    if doc.get("status") == "completed":
        raise HTTPException(status_code=400, detail="Test already completed")

    variant_ids = [v["id"] for v in doc.get("variants", [])]
    if payload.winner_variant_id not in variant_ids:
        raise HTTPException(status_code=400, detail=f"Invalid variant id: {payload.winner_variant_id}")

    await ab_tests_collection.update_one(
        {"_id": _oid(test_id)},
        {"$set": {
            "status":       "completed",
            "winner":       payload.winner_variant_id,
            "completed_at": datetime.utcnow(),
        }}
    )

    return {
        "ok":     True,
        "winner": payload.winner_variant_id,
        "status": "completed",
    }
