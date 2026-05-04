"""
Phase 3 — SDK Ingest API (v2 — Enriched Behavioral Tracking)
Public endpoints authenticated via API key (not user JWT).
Receives tracking events from the LeadMind tracker.js SDK (v2).

Enriched fields stored per event:
  - session_id, device_type, browser, os, screen_resolution, connection_type
  - page_type, is_product/category/pricing/cart/checkout/confirmation_page
  - product_category, utm_* params, landing_page, active_time_window
  - exit_page_type, scroll milestones, click counts

Visitor Sessions (visitor_sessions collection) — one aggregated doc per visitor:
  - total_page_views, total_clicks, total_time_sec, max_scroll_depth
  - pages_viewed_list, is_product_visitor, cart_added, checkout_started, purchase_made
  - engagement_score (0–100), sessions_count, identified_email
  - new_vs_returning, last_seen, first_seen
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import json, secrets as sec

from db import (
    api_keys_collection,
    tracking_events_collection,
    visitor_sessions_collection,
    leads_collection,
)
from services.scoring_service import ScoringService

router = APIRouter()


# ── API Key Auth ──────────────────────────────────────────────────────────────

async def _resolve_api_key(key: str) -> dict:
    """Validate API key and return its document. Updates last_used_at."""
    doc = await api_keys_collection.find_one({"key": key, "is_active": True})
    if not doc:
        raise HTTPException(401, "Invalid or inactive API key")
    await api_keys_collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"last_used_at": datetime.now(timezone.utc)}, "$inc": {"event_count": 1}},
    )
    return doc


# ── Models ────────────────────────────────────────────────────────────────────

class TrackingEvent(BaseModel):
    # Core
    api_key:    str
    visitor_id: str
    event_type: str                  # page_view | scroll | click | time_spent | cart_view | checkout_started | etc.
    url:        str

    # Optional standard fields
    session_id:   Optional[str]  = None
    title:        Optional[str]  = None
    referrer:     Optional[str]  = None
    landing_page: Optional[str]  = None

    # Device
    device_type:       Optional[str] = None
    browser:           Optional[str] = None
    os:                Optional[str] = None
    screen_resolution: Optional[str] = None
    connection_type:   Optional[str] = None

    # Page classification
    page_type:            Optional[str]  = None
    is_product_page:      Optional[bool] = None
    is_category_page:     Optional[bool] = None
    is_pricing_page:      Optional[bool] = None
    is_cart_page:         Optional[bool] = None
    is_checkout_page:     Optional[bool] = None
    is_confirmation_page: Optional[bool] = None
    product_category:     Optional[str]  = None
    exit_page_type:       Optional[str]  = None

    # UTM
    utm_source:   Optional[str] = None
    utm_medium:   Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term:     Optional[str] = None
    utm_content:  Optional[str] = None

    # Timing
    active_time_window: Optional[str] = None

    # Arbitrary metadata (scroll_depth, duration_s, click info, etc.)
    metadata: Optional[dict] = {}


class IdentifyEvent(BaseModel):
    api_key:    str
    visitor_id: str
    session_id: Optional[str] = None
    email:      str
    name:       Optional[str]    = None
    username:   Optional[str]    = None
    first_name: Optional[str]    = None
    last_name:  Optional[str]    = None
    company:    Optional[str]    = None
    phone:      Optional[str]    = None
    city:       Optional[str]    = None
    state:      Optional[str]    = None
    country:    Optional[str]    = None


# ── Engagement Scoring ────────────────────────────────────────────────────────

def _calc_engagement_score(session: dict) -> int:
    """
    Compute 0–100 engagement score from session aggregate.
    Weights:
      page_views      × 5  (max 30)
      time_sec        × 0.01 (max 20)
      max_scroll      × 0.3  (max 30)
      clicks          × 2  (max 10)
      cart_added      +5
      checkout_started+10
      purchase_made   +15 (capped at 100)
      sessions_count  × 3  (max 10)
    """
    score  = min(session.get("total_page_views", 0) * 5,  30)
    score += min(session.get("total_time_sec",    0) * 0.01, 20)
    score += min(session.get("max_scroll_depth",  0) * 0.3, 30)
    score += min(session.get("total_clicks",      0) * 2,  10)
    score += 5  if session.get("cart_added")        else 0
    score += 10 if session.get("checkout_started")  else 0
    score += 15 if session.get("purchase_made")     else 0
    score += min(session.get("sessions_count",    1) * 3,  10)
    return min(int(score), 100)


# ── Visitor Session Upsert ────────────────────────────────────────────────────

async def _upsert_visitor_session(company_id: str, payload: TrackingEvent, now: datetime):
    """
    Maintain one aggregated 'visitor_sessions' document per (company_id, visitor_id).
    Called after every event. Uses $setOnInsert for first-seen and $set/$inc for updates.
    """
    ev = payload.event_type
    meta = payload.metadata or {}

    # Increments
    inc = {"total_page_views": 1 if ev == "page_view" else 0,
           "total_clicks":     1 if ev == "click" else 0}

    # Duration (time_spent event)
    if ev == "time_spent":
        inc["total_time_sec"] = meta.get("duration_s", 0)

    # Set fields
    sets = {
        "last_seen":    now,
        "last_url":     payload.url,
        "last_page_type": payload.page_type,
        "company_id":   company_id,
        "visitor_id":   payload.visitor_id,
        "last_session_id": payload.session_id,
    }
    
    # Session count logic: if this is a new session ID for this visitor, increment
    # We'll handle this via a conditional update later.
    
    if payload.device_type:    sets["device_type"]  = payload.device_type
    if payload.browser:        sets["browser"]       = payload.browser
    if payload.os:             sets["os"]            = payload.os
    if payload.utm_source:     sets["utm_source"]    = payload.utm_source
    if payload.utm_medium:     sets["utm_medium"]    = payload.utm_medium
    if payload.utm_campaign:   sets["utm_campaign"]  = payload.utm_campaign


    # Behavioral flags
    if ev == "cart_view"       or meta.get("cart_added"):
        sets["cart_added"] = True
    if ev == "checkout_started" or meta.get("checkout_started"):
        sets["checkout_started"] = True
    if ev == "purchase_complete" or meta.get("purchase_made"):
        sets["purchase_made"] = True
        sets["new_vs_returning"] = "Customer"
    if payload.is_product_page:
        sets["is_product_visitor"] = True

    # Build update
    update = {
        "$setOnInsert": {
            "first_seen":       now,
            "new_vs_returning": "New",
            "sessions_count":   1, # Start with 1
            "cart_added":       False,
            "checkout_started": False,
            "purchase_made":    False,
            "is_product_visitor": False,
            "is_lead":          False,
            "pages_viewed_list":[],
            "engagement_score": 0,
        },
        "$set": sets,
    }
    
    # Initialize optional operators
    clean_inc = {k: v for k, v in inc.items() if v}
    if clean_inc:
        update["$inc"] = clean_inc
        
    if ev == "scroll" and meta.get("scroll_depth"):
        update["$max"] = {"max_scroll_depth": meta["scroll_depth"]}

    # Add URL to pages_viewed_list (capped at 50)
    if ev == "page_view":
        update["$addToSet"] = {"pages_viewed_list": payload.url}

    # Clean up $setOnInsert to prevent ConflictingUpdateOperators
    for op in ["$set", "$inc", "$max", "$addToSet"]:
        if op in update:
            for key in update[op].keys():
                if key in update["$setOnInsert"]:
                    del update["$setOnInsert"][key]


    # 1. First, check if session_id changed to increment sessions_count
    existing = await visitor_sessions_collection.find_one({"company_id": company_id, "visitor_id": payload.visitor_id})
    if existing and existing.get("last_session_id") != payload.session_id:
        if "$inc" not in update: update["$inc"] = {}
        update["$inc"]["sessions_count"] = 1

    # 2. Upsert
    result = await visitor_sessions_collection.find_one_and_update(
        {"company_id": company_id, "visitor_id": payload.visitor_id},
        update,
        upsert=True,
        return_document=True,
    )

    if result:
        # Recalculate and update engagement_score
        score = _calc_engagement_score(result)
        await visitor_sessions_collection.update_one(
            {"company_id": company_id, "visitor_id": payload.visitor_id},
            {"$set": {"engagement_score": score, "new_vs_returning": result.get("new_vs_returning", "New")}},
        )

def _build_key_signals(session: dict) -> list:
    """Convert session data into structured key_signals for intel field."""
    signals = []
    if session.get("checkout_started"):
        signals.append({"signal": "Started checkout — very high purchase intent", "weight": "critical"})
    if session.get("cart_added"):
        signals.append({"signal": "Added item to cart", "weight": "high"})
    if session.get("purchase_made"):
        signals.append({"signal": "Completed a purchase", "weight": "critical"})
    pv = session.get("total_page_views", 0)
    if pv >= 5:
        signals.append({"signal": f"High page engagement: {pv} pages viewed", "weight": "medium"})
    t = session.get("total_time_sec", 0)
    if t >= 120:
        mins = t // 60
        signals.append({"signal": f"Extended browsing session: {mins}m on site", "weight": "medium"})
    sc = session.get("max_scroll_depth", 0)
    if sc >= 70:
        signals.append({"signal": f"Deep content engagement: {sc}% scroll depth", "weight": "medium"})
    if session.get("utm_source"):
        signals.append({"signal": f"Arrived via {session['utm_source']}", "weight": "low"})
    return signals


# ── Threshold Check ───────────────────────────────────────────────────────────

THRESHOLDS = {
    "min_page_views":    3,
    "min_time_sec":      120,
    "cart_added":        True,
    "checkout_started":  True,
    "min_visits":        5,
    "min_scroll":        80,
    "is_identified":     True,
}

async def _check_threshold(company_id: str, visitor_id: str, identified_email: str = None) -> bool:
    """Return True if this visitor crosses the auto-promote threshold."""
    sess = await visitor_sessions_collection.find_one(
        {"company_id": company_id, "visitor_id": visitor_id}
    )
    if not sess:
        return False

    if sess.get("cart_added"):        return True
    if sess.get("checkout_started"):   return True
    if identified_email:               return True
    if sess.get("total_page_views", 0) >= THRESHOLDS["min_page_views"] \
       and sess.get("total_time_sec", 0) >= THRESHOLDS["min_time_sec"]:
        return True
    if sess.get("sessions_count", 0) >= THRESHOLDS["min_visits"]:
        return True
    if sess.get("max_scroll_depth", 0) >= THRESHOLDS["min_scroll"] \
       and sess.get("is_product_visitor"):
        return True
    return False


async def _maybe_auto_promote(visitor_id: str, company_id: str, session: dict):
    """
    Auto-promote visitor to lead and trigger AI pipeline.
    - New visitor: create lead, ALWAYS trigger pipeline (with or without email)
    - Returning visitor: update behavior, recalculate intent_score, append to history
    """
    from datetime import datetime, timezone
    import secrets
    from bson import ObjectId

    company_id_str = str(company_id)
    company_id_oid = ObjectId(company_id_str)

    id_email        = session.get("identified_email")
    id_name         = session.get("identified_name")
    engagement_score = session.get("engagement_score", 0)

    # Promotion criteria: identified OR high engagement OR cart/checkout activity
    if not id_email and engagement_score < 50 and not session.get("cart_added"):
        return

    # ── Deduplication: try email first, then visitor_id ──────────────────────
    existing = None
    if id_email:
        existing = await leads_collection.find_one({
            "company_id": company_id_oid,
            "profile.email": id_email
        })

    if not existing:
        existing = await leads_collection.find_one({
            "company_id": company_id_oid,
            "visitor_id": visitor_id
        })

    if existing:
        # ── Returning visitor: merge behavioral data + update intent score ───
        now = datetime.now(timezone.utc)

        # Recalculate intent_score from engagement_score (0–100 → map to 0–99)
        new_intent_score = min(int(engagement_score * 0.99), 99)
        if session.get("checkout_started"):
            new_intent_score = max(new_intent_score, 85)
        elif session.get("cart_added"):
            new_intent_score = max(new_intent_score, 70)

        # Build a behavior snapshot for history
        behavior_snapshot = {
            "recorded_at":      now.isoformat(),
            "page_views":       session.get("total_page_views", 0),
            "time_sec":         session.get("total_time_sec", 0),
            "max_scroll":       session.get("max_scroll_depth", 0),
            "engagement_score": engagement_score,
            "cart_added":       session.get("cart_added", False),
            "checkout_started": session.get("checkout_started", False),
            "pages_visited":    session.get("pages_viewed_list", []),
            "last_url":         session.get("last_url", ""),
        }

        update_fields = {
            "sdk_activity.page_views":        session.get("total_page_views", 0),
            "sdk_activity.total_time_sec":    session.get("total_time_sec", 0),
            "sdk_activity.max_scroll":        session.get("max_scroll_depth", 0),
            "sdk_activity.engagement_score":  engagement_score,
            "sdk_activity.cart_added":        session.get("cart_added", False),
            "sdk_activity.checkout_started":  session.get("checkout_started", False),
            "sdk_activity.purchase_made":     session.get("purchase_made", False),
            "sdk_activity.last_seen":         session.get("last_seen"),
            "sdk_activity.urls":              session.get("pages_viewed_list", []),
            # Update intent score on every revisit
            "intel.intent_score":             new_intent_score,
            "updated_at":                     now,
        }
        # Improve name if we now have a better one
        if id_name and not existing.get("profile", {}).get("name"):
            update_fields["profile.name"] = id_name
        elif not id_name and id_email and "Visitor" in existing.get("profile", {}).get("name", ""):
            prefix = id_email.split("@")[0]
            update_fields["profile.name"] = prefix.replace(".", " ").replace("_", " ").title()

        await leads_collection.update_one(
            {"_id": existing["_id"]},
            {
                "$set": update_fields,
                "$push": {
                    "sdk_activity.behavior_history": {
                        "$each":     [behavior_snapshot],
                        "$slice":    -20,   # keep last 20 snapshots
                        "$position": 0,     # prepend (newest first)
                    }
                }
            }
        )

        # ── Intensity Scoring for Revisit ──
        # Only score if it's a genuine "revisit" (e.g. more than 30 mins since last seen)
        last_seen = existing.get("sdk_activity", {}).get("last_seen")
        if last_seen:
            # Handle both datetime objects and strings
            if isinstance(last_seen, str):
                try:
                    from datetime import datetime
                    last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                except:
                    last_seen = now # fallback
            
            # If last activity was > 30 mins ago, it's a revisit
            diff = (now - last_seen).total_seconds()
            if diff > 1800: # 30 minutes
                await ScoringService.update_intensity_score(
                    lead_id=existing["lead_id"],
                    company_id=company_id_str,
                    signal_type="sdk_revisit",
                    weight=10,
                    description="Lead revisited the website"
                )
        return

    # ── New lead creation ─────────────────────────────────────────────────────
    now     = datetime.now(timezone.utc)
    lead_id = f"L_SDK_{secrets.token_hex(4).upper()}"

    display_name = id_name
    if not display_name and id_email:
        display_name = id_email.split("@")[0].replace(".", " ").replace("_", " ").title()
    if not display_name:
        display_name = f"Visitor {visitor_id[:8]}"

    # Initial intent score from engagement
    initial_intent = min(int(engagement_score * 0.99), 99)
    if session.get("checkout_started"):
        initial_intent = max(initial_intent, 85)
    elif session.get("cart_added"):
        initial_intent = max(initial_intent, 70)

    lead_doc = {
        "lead_id":    lead_id,
        "company_id": company_id_oid,
        "batch_id":   "sdk_auto",
        "source":     "sdk",
        "visitor_id": visitor_id,
        "visitor_ids": [visitor_id],
        "status":     "new" if id_email else "hot_visitor",
        "profile": {
            "name":    display_name,
            "email":   id_email or "",
            "company": session.get("identified_company") or "Website Visitor",
            "title":   "Customer",
            "phone":   session.get("identified_phone", ""),
            "city":    session.get("identified_city", ""),
            "country": session.get("identified_country", ""),
        },
        "pipeline_stage": "New Lead",
        "intel": {
            "intent_score": initial_intent,
            "key_signals": _build_key_signals(session),
        },
        "crm":    {"notes": "Auto-promoted via LeadMind SDK threshold.", "next_followup": None},
        "sdk_activity": {
            "page_views":         session.get("total_page_views", 0),
            "total_time_sec":     session.get("total_time_sec", 0),
            "engagement_score":   engagement_score,
            "cart_added":         session.get("cart_added", False),
            "checkout_started":   session.get("checkout_started", False),
            "purchase_made":      session.get("purchase_made", False),
            "urls":               session.get("pages_viewed_list", []),
            "utm_source":         session.get("utm_source"),
            "utm_campaign":       session.get("utm_campaign"),
            "last_seen":          session.get("last_seen"),
            "behavior_history":   [],
        },
        "created_at": now,
    }
    await leads_collection.insert_one(lead_doc)

    # Mark session as promoted
    await visitor_sessions_collection.update_one(
        {"company_id": company_id_str, "visitor_id": visitor_id},
        {"$set": {"is_lead": True, "lead_id": lead_id}}
    )

    # ── AI Pipeline is strictly manual for SDK visitors (per user request) ──────
    # The user will manually click "Convert to Lead" in the dashboard to trigger the agent runner.


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/event")
async def ingest_event(request: Request):
    """
    Receive a tracking event from the JS SDK v2.
    No user JWT — authenticated via api_key field.
    Handles text/plain Content-Type emitted by navigator.sendBeacon.
    """
    try:
        body = await request.body()
        data = json.loads(body)
        payload = TrackingEvent(**data)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid payload format")

    key_doc    = await _resolve_api_key(payload.api_key)
    company_id = str(key_doc["company_id"])
    now        = datetime.now(timezone.utc)

    # Build enriched event document
    event = {
        # Core
        "company_id":   company_id,
        "api_key":      payload.api_key,
        "visitor_id":   payload.visitor_id,
        "session_id":   payload.session_id,
        "event_type":   payload.event_type,
        "url":          payload.url,
        "title":        payload.title,
        "referrer":     payload.referrer,
        "landing_page": payload.landing_page,
        "timestamp":    now,
        # Device
        "device_type":       payload.device_type,
        "browser":           payload.browser,
        "os":                payload.os,
        "screen_resolution": payload.screen_resolution,
        "connection_type":   payload.connection_type,
        # Page classification
        "page_type":            payload.page_type,
        "is_product_page":      payload.is_product_page,
        "is_category_page":     payload.is_category_page,
        "is_pricing_page":      payload.is_pricing_page,
        "is_cart_page":         payload.is_cart_page,
        "is_checkout_page":     payload.is_checkout_page,
        "is_confirmation_page": payload.is_confirmation_page,
        "product_category":     payload.product_category,
        "exit_page_type":       payload.exit_page_type,
        # UTM
        "utm_source":   payload.utm_source,
        "utm_medium":   payload.utm_medium,
        "utm_campaign": payload.utm_campaign,
        "utm_term":     payload.utm_term,
        "utm_content":  payload.utm_content,
        # Timing
        "active_time_window": payload.active_time_window,
        # Network
        "ip":         request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
        # Arbitrary metadata
        "metadata":   payload.metadata or {},
    }
    await tracking_events_collection.insert_one(event)

    # Update visitor session aggregate
    await _upsert_visitor_session(company_id, payload, now)

    # Check if threshold crossed → auto-promote
    sess = await visitor_sessions_collection.find_one({"company_id": company_id, "visitor_id": payload.visitor_id})
    if sess:
        await _maybe_auto_promote(payload.visitor_id, company_id, sess)

    return {"ok": True}


@router.post("/identify")
async def ingest_identify(request: Request):
    """
    Identify a visitor with their contact info (from form submit or login).
    - Backfills all past events with identified_email
    - Updates visitor_session with email
    - Upserts a lead record
    - Triggers threshold check (identified visitor = instant promote)
    """
    import secrets
    from bson import ObjectId

    try:
        body = await request.body()
        data = json.loads(body)
        payload = IdentifyEvent(**data)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid payload format")

    key_doc        = await _resolve_api_key(payload.api_key)
    company_id_str = str(key_doc["company_id"])
    company_id_oid = ObjectId(company_id_str)
    now            = datetime.now(timezone.utc)

    # Backfill all past events for this visitor
    await tracking_events_collection.update_many(
        {"visitor_id": payload.visitor_id, "company_id": company_id_str},
        {"$set": {"identified_email": payload.email}},
    )

    # Derive name from possible fields
    real_name_found = False
    derived_name = payload.name
    if not derived_name:
        if payload.first_name and payload.last_name:
            derived_name = f"{payload.first_name} {payload.last_name}"
        elif payload.first_name:
            derived_name = payload.first_name
        elif payload.last_name:
            derived_name = payload.last_name
        elif payload.username:
            derived_name = payload.username

    if derived_name:
        real_name_found = True
    else:
        # Fallback to email prefix if completely blank
        derived_name = payload.email.split("@")[0].replace(".", " ").replace("_", " ").title() if payload.email else payload.email

    # Update visitor session
    session_update = {
        "identified_email": payload.email,
        "new_vs_returning": "Identified",
    }
    if derived_name:    session_update["identified_name"]    = derived_name
    if payload.company: session_update["identified_company"] = payload.company
    if payload.phone:   session_update["identified_phone"]   = payload.phone
    if payload.city:    session_update["identified_city"]    = payload.city
    if payload.state:   session_update["identified_state"]   = payload.state
    if payload.country: session_update["identified_country"] = payload.country

    await visitor_sessions_collection.update_one(
        {"company_id": company_id_str, "visitor_id": payload.visitor_id},
        {"$set": session_update},
        upsert=True,
    )

    if existing_by_email:
        # Merge visitor_id into existing lead (multi-device)
        update_doc = {
            "$addToSet": {"visitor_ids": payload.visitor_id},
            "$set": {
                "visitor_id": payload.visitor_id,
                "source": "sdk",
                "updated_at": now,
            },
        }
        # Update name if we found a real name and the existing name looks like an email/placeholder
        existing_name = existing_by_email.get("profile", {}).get("name", "")
        if real_name_found and (not existing_name or "@" in existing_name or existing_name.lower().startswith("visitor ")):
            update_doc["$set"]["profile.name"] = derived_name

        await leads_collection.update_one(
            {"_id": existing_by_email["_id"]},
            update_doc
        )
        return {"ok": True, "identified": True, "merged": True}

    # If a lead already exists for this visitor_id (anonymous lead case)
    existing_by_vid = await leads_collection.find_one(
        {"company_id": company_id_oid, "visitor_id": payload.visitor_id}
    )
    if existing_by_vid:
        existing_name = existing_by_vid.get("profile", {}).get("name", "")
        best_name = derived_name if real_name_found else (existing_name if existing_name else derived_name)

        # Upgrade anonymous lead with identity
        await leads_collection.update_one(
            {"_id": existing_by_vid["_id"]},
            {"$set": {
                "profile.email":   payload.email,
                "profile.name":    best_name,
                "profile.company": payload.company or "Website Visitor",
                "status":          "new",
                "updated_at":      now,
            }},
        )
        # Trigger pipeline since now we have an email
        import asyncio
        from services.agent_runner import run_pipeline_for_lead
        asyncio.create_task(
            run_pipeline_for_lead(
                existing_by_vid["lead_id"], existing_by_vid.get("batch_id", "sdk_auto"), company_id_str
            )
        )
        return {"ok": True, "identified": True, "upgraded": True}

    # No existing lead — create one and trigger pipeline
    lead_id = f"L_SDK_{secrets.token_hex(4).upper()}"
    sess = await visitor_sessions_collection.find_one(
        {"company_id": company_id_str, "visitor_id": payload.visitor_id}
    )
    if not derived_name:
        derived_name = f"Visitor {payload.visitor_id[:8]}"

    await leads_collection.insert_one({
        "lead_id":    lead_id,
        "company_id": company_id_oid,
        "batch_id":   "sdk_identify",
        "source":     "sdk",
        "visitor_id": payload.visitor_id,
        "visitor_ids": [payload.visitor_id],
        "status":     "new",
        "profile": {
            "name":    derived_name,
            "email":   payload.email,
            "company": payload.company or "Website Visitor",
            "title":   "Customer",
            "phone":   payload.phone or "",
            "city":    payload.city or "",
            "state":   payload.state or "",
            "country": payload.country or "",
        },
        "pipeline_stage": "New Lead",
        "intel":  {},
        "crm":    {"notes": "Identified via LeadMind SDK form capture.", "next_followup": None},
        "sdk_activity": {
            "page_views":       sess.get("total_page_views", 0) if sess else 0,
            "total_time_sec":   sess.get("total_time_sec", 0) if sess else 0,
            "engagement_score": sess.get("engagement_score", 0) if sess else 0,
            "cart_added":       sess.get("cart_added", False) if sess else False,
            "checkout_started": sess.get("checkout_started", False) if sess else False,
            "purchase_made":    sess.get("purchase_made", False) if sess else False,
            "urls":             sess.get("pages_viewed_list", []) if sess else [],
            "utm_source":       sess.get("utm_source") if sess else None,
            "utm_campaign":     sess.get("utm_campaign") if sess else None,
        } if sess else {},
        "created_at": now,
    })

    await visitor_sessions_collection.update_one(
        {"company_id": company_id_str, "visitor_id": payload.visitor_id},
        {"$set": {"is_lead": True, "lead_id": lead_id}}
    )

    import asyncio
    from services.agent_runner import run_pipeline_for_lead
    asyncio.create_task(run_pipeline_for_lead(lead_id, "sdk_identify", company_id_str))

    return {"ok": True, "identified": True, "lead_created": True}
