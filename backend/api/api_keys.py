"""
Phase 3 — API Key Management
Authenticated routes for generating / listing / revoking SDK API keys.
"""
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from db import api_keys_collection, tracking_events_collection, visitor_sessions_collection, leads_collection
from dependencies import get_current_user

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


# ── Models ────────────────────────────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    name: str   # e.g. "Production Website"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_api_key(req: CreateKeyRequest, user=Depends(get_current_user)):
    """Generate a new API key for the authenticated company."""
    company_id = str(user["company_id"])
    key = f"lm_live_{secrets.token_urlsafe(24)}"
    doc = {
        "company_id": company_id,
        "key":        key,
        "name":       req.name.strip(),
        "created_at": datetime.now(timezone.utc),
        "last_used_at": None,
        "is_active":  True,
        "event_count": 0,
    }
    result = await api_keys_collection.insert_one(doc)
    return {"key_id": str(result.inserted_id), "key": key, "name": doc["name"]}


@router.get("/list")
async def list_api_keys(user=Depends(get_current_user)):
    """List all API keys for the authenticated company (key value masked)."""
    company_id = str(user["company_id"])
    cursor = api_keys_collection.find({"company_id": company_id}).sort("created_at", -1)
    keys = []
    async for doc in cursor:
        doc = _serialize(doc)
        # Mask key: show first 12 + last 4 chars
        k = doc["key"]
        doc["key_preview"] = f"{k[:12]}...{k[-4:]}"
        keys.append(doc)
    return {"keys": keys}


@router.get("/stats")
async def get_tracking_stats(user=Depends(get_current_user)):
    """KPI stats for the tracking dashboard header."""
    company_id_str = str(user["company_id"])
    company_id_oid = user["company_id"]
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    cutoff_7d  = datetime.now(timezone.utc) - timedelta(days=7)

    total_visitors   = await visitor_sessions_collection.count_documents({"company_id": company_id_str})
    active_24h       = await visitor_sessions_collection.count_documents({"company_id": company_id_str, "last_seen": {"$gte": cutoff_24h}})
    total_leads_sdk  = await leads_collection.count_documents({"company_id": company_id_oid, "source": "sdk"})
    identified       = await visitor_sessions_collection.count_documents({"company_id": company_id_str, "identified_email": {"$exists": True, "$ne": None, "$ne": ""}})
    events_7d        = await tracking_events_collection.count_documents({"company_id": company_id_str, "timestamp": {"$gte": cutoff_7d}})
    cart_visitors    = await visitor_sessions_collection.count_documents({"company_id": company_id_str, "cart_added": True})
    checkout_visitors= await visitor_sessions_collection.count_documents({"company_id": company_id_str, "checkout_started": True})

    # Avg engagement score
    pipeline = [
        {"$match": {"company_id": company_id_str}},
        {"$group": {"_id": None, "avg_score": {"$avg": "$engagement_score"}}}
    ]
    avg_score = 0
    async for doc in visitor_sessions_collection.aggregate(pipeline):
        avg_score = round(doc.get("avg_score", 0), 1)

    return {
        "total_visitors":    total_visitors,
        "active_24h":        active_24h,
        "total_leads_sdk":   total_leads_sdk,
        "identified":        identified,
        "events_7d":         events_7d,
        "cart_visitors":     cart_visitors,
        "checkout_visitors": checkout_visitors,
        "avg_engagement":    avg_score,
    }


@router.get("/events")
async def list_recent_events(
    limit: int = Query(50, le=200),
    event_type: str = Query(None),
    user=Depends(get_current_user)
):
    """Fetch recent live tracking events (enriched) for the authenticated company."""
    company_id = str(user["company_id"])
    query = {"company_id": company_id}
    if event_type:
        query["event_type"] = event_type

    cursor = tracking_events_collection.find(query).sort("timestamp", -1).limit(limit)
    events = []
    async for doc in cursor:
        events.append({
            "id":           str(doc["_id"]),
            "visitor_id":   doc["visitor_id"],
            "session_id":   doc.get("session_id"),
            "event_type":   doc["event_type"],
            "url":          doc["url"],
            "title":        doc.get("title"),
            "page_type":    doc.get("page_type"),
            "device_type":  doc.get("device_type"),
            "utm_source":   doc.get("utm_source"),
            "utm_campaign": doc.get("utm_campaign"),
            "timestamp":    doc["timestamp"].isoformat(),
            "metadata":     doc.get("metadata", {}),
            "identified_email": doc.get("identified_email"),
        })
    return {"events": events}


@router.get("/visitors")
async def list_active_visitors(
    hours:  int = Query(720, le=8760),
    limit:  int = Query(50, le=200),
    user=Depends(get_current_user)
):
    """
    Returns enriched visitor list from visitor_sessions collection.
    Sorted by last_seen desc. Includes all behavioral signals.
    """
    company_id_str = str(user["company_id"])
    company_id_oid = user["company_id"]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    cursor = (
        visitor_sessions_collection
        .find({"company_id": company_id_str, "last_seen": {"$gte": cutoff}})
        .sort("last_seen", -1)
        .limit(limit)
    )

    visitors = []
    async for sess in cursor:
        v = {
            "visitor_id":        sess["visitor_id"],
            "first_seen":        sess["first_seen"].isoformat() if sess.get("first_seen") else None,
            "last_seen":         sess["last_seen"].isoformat()  if sess.get("last_seen")  else None,
            "page_views":        sess.get("total_page_views",  0),
            "clicks":            sess.get("total_clicks",      0),
            "total_time_sec":    sess.get("total_time_sec",    0),
            "max_scroll":        sess.get("max_scroll_depth",  0),
            "sessions_count":    sess.get("sessions_count",    1),
            "engagement_score":  sess.get("engagement_score",  0),
            "cart_added":        sess.get("cart_added",        False),
            "checkout_started":  sess.get("checkout_started",  False),
            "purchase_made":     sess.get("purchase_made",     False),
            "is_product_visitor":sess.get("is_product_visitor",False),
            "device_type":       sess.get("device_type"),
            "browser":           sess.get("browser"),
            "os":                sess.get("os"),
            "utm_source":        sess.get("utm_source"),
            "utm_medium":        sess.get("utm_medium"),
            "utm_campaign":      sess.get("utm_campaign"),
            "last_page_type":    sess.get("last_page_type"),
            "last_url":          sess.get("last_url"),
            "pages_viewed_list": sess.get("pages_viewed_list", []),
            "new_vs_returning":  sess.get("new_vs_returning",  "New"),
            # SDK-captured identity (may be partial)
            "identified_email":  sess.get("identified_email"),
            "identified_name":   sess.get("identified_name"),
            "identified_phone":  sess.get("identified_phone"),
            "identified_company":sess.get("identified_company"),
            "identified_city":   sess.get("identified_city"),
            "identified_country":sess.get("identified_country"),
            "is_lead":           sess.get("is_lead",  False),
            "lead_id":           sess.get("lead_id"),
        }

        # ── Enrich with full lead profile if converted ─────────────────────
        if v["is_lead"] and v["lead_id"]:
            lead = await leads_collection.find_one(
                {"company_id": company_id_oid, "lead_id": v["lead_id"]},
                {"profile": 1, "intel": 1, "sdk_activity": 1, "status": 1,
                 "pipeline_stage": 1, "source": 1, "created_at": 1}
            )
            if lead:
                p = lead.get("profile", {})
                intel = lead.get("intel", {})
                sdk   = lead.get("sdk_activity", {})
                # Merge profile — lead record wins over session
                v["identified_name"]    = p.get("name")    or v["identified_name"]
                v["identified_email"]   = p.get("email")   or v["identified_email"]
                v["identified_phone"]   = p.get("phone")   or v["identified_phone"]
                v["identified_company"] = p.get("company") or v["identified_company"]
                v["identified_title"]   = p.get("title")
                v["identified_city"]    = p.get("city")    or v["identified_city"]
                v["identified_country"] = p.get("country") or v["identified_country"]
                # Intel / pipeline
                v["intent_score"]       = intel.get("intent_score")
                v["key_signals"]        = intel.get("key_signals", [])
                v["pipeline_stage"]     = lead.get("pipeline_stage")
                v["lead_status"]        = lead.get("status")
                v["lead_source"]        = lead.get("source")
                v["lead_created_at"]    = lead["created_at"].isoformat() if lead.get("created_at") else None
                # Prefer sdk_activity urls if session list is empty
                if not v["pages_viewed_list"] and sdk.get("urls"):
                    v["pages_viewed_list"] = sdk["urls"]
            else:
                # SELF-HEALING: Lead was deleted but visitor session still has is_lead=True
                v["is_lead"] = False
                v["lead_id"] = None
                await visitor_sessions_collection.update_one(
                    {"_id": sess["_id"]},
                    {"$set": {"is_lead": False}, "$unset": {"lead_id": ""}}
                )

        visitors.append(v)
    return {"visitors": visitors}

class PromoteRequest(BaseModel):
    visitor_ids: list[str]

@router.post("/visitors/promote")
async def promote_visitors_to_leads(req: PromoteRequest, user=Depends(get_current_user)):
    """Manually push selected visitors into the Pipeline as full Leads and trigger AI Agents."""
    from db import leads_collection, batches_collection, tracking_events_collection
    import secrets
    from services.agent_runner import run_pipeline_for_lead
    import asyncio
    
    company_id_str = str(user["company_id"])
    company_id_oid = user["company_id"]
    promoted_count = 0
    now = datetime.now(timezone.utc)

    # We attach these manual promotions to a pseudo-batch for UI grouping
    batch_doc = {
        "batch_id": f"MANUAL_{secrets.token_hex(4).upper()}",
        "company_id": company_id_oid,
        "name": "Live Tracking Conversion",
        "total_leads": len(req.visitor_ids),
        "status": "processing",
        "created_at": now,
        "leads_processed": 0
    }
    await batches_collection.insert_one(batch_doc)
    
    for vid in req.visitor_ids:
        # Check if they exist
        existing = await leads_collection.find_one({"company_id": company_id_oid, "visitor_id": vid})
        if existing:
            # If already a lead, we can optionally re-run them or just skip
            lead_id = existing["lead_id"]
        else:
            # Fetch session to get identity (name/email)
            sess = await visitor_sessions_collection.find_one({"company_id": company_id_str, "visitor_id": vid})
            
            # Fetch stats for sdk_activity
            stats = {}
            async for s in tracking_events_collection.aggregate([
                {"$match": {"company_id": company_id_str, "visitor_id": vid}},
                {"$group": {"_id": None, "urls": {"$addToSet": "$url"}, "last_seen": {"$max": "$timestamp"}, "views": {"$sum": 1}}}
            ]):
                stats = s
                
            lead_id = f"L_{secrets.token_hex(4).upper()}"
            
            # Identity defaults
            id_name = sess.get("identified_name") if sess else None
            id_email = sess.get("identified_email") if sess else None
            
            final_name = id_name
            if not final_name and id_email:
                final_name = id_email
            if not final_name:
                final_name = f"Live Visitor {vid[:6]}"
            
            await leads_collection.insert_one({
                "lead_id": lead_id,
                "company_id": company_id_oid,
                "batch_id": batch_doc["batch_id"],
                "source": "sdk",
                "visitor_id": vid,
                "status": "new" if id_email else "hot_visitor",
                "profile": {
                    "name":    final_name,
                    "email":   id_email or "",
                    "company": sess.get("identified_company") or "Live Website Visitor",
                    "title":   "Customer"
                },
                "pipeline_stage": "New Lead",
                "intel": {},
                "crm": {"notes": "Manually promoted from Live Tracking Feed.", "next_followup": None},
                "sdk_activity": {
                    "urls": stats.get("urls", []),
                    "last_seen": stats.get("last_seen", now),
                    "page_views": stats.get("views", 1),
                    "engagement_score": sess.get("engagement_score") if sess else 0,
                    "device_type": sess.get("device_type") if sess else None,
                },
                "created_at": now
            })
        
        # Fire off the AI Agent Pipeline completely async
        asyncio.create_task(run_pipeline_for_lead(lead_id, batch_doc["batch_id"], company_id_str))
        
        # Update visitor session to mark as lead
        await visitor_sessions_collection.update_one(
            {"company_id": company_id_str, "visitor_id": vid},
            {"$set": {"is_lead": True, "lead_id": lead_id}}
        )

        promoted_count += 1


    return {"ok": True, "promoted": promoted_count, "batch_id": batch_doc["batch_id"]}

@router.delete("/{key_id}")
async def revoke_api_key(key_id: str, user=Depends(get_current_user)):
    """Revoke (soft-delete) an API key."""
    from bson import ObjectId
    company_id = str(user["company_id"])
    result = await api_keys_collection.update_one(
        {"_id": ObjectId(key_id), "company_id": company_id},
        {"$set": {"is_active": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Key not found")
    return {"revoked": True}

@router.delete("/visitors/{visitor_id}")
async def delete_visitor_session(visitor_id: str, user=Depends(get_current_user)):
    """Delete a visitor session and their tracking events."""
    company_id = str(user["company_id"])
    await visitor_sessions_collection.delete_one({"company_id": company_id, "visitor_id": visitor_id})
    await tracking_events_collection.delete_many({"company_id": company_id, "visitor_id": visitor_id})
    return {"deleted": True}
