"""
Phase 3 — Auto Pipeline Service (v2)
Background loop that watches visitor_sessions for visitors who cross
an engagement threshold.

Uses the visitor_sessions collection (maintained by ingest.py) to avoid
expensive re-aggregation on every poll. The ingest endpoint already handles
threshold checks on every event — this loop is a safety net for visitors
who accumulated events before the auto-promote logic existed, or whose
sessions_count threshold is only detectable in aggregate.

Poll interval: 3 minutes (ingest.py handles real-time promotions)
"""
import asyncio
from datetime import datetime, timezone, timedelta
from db import visitor_sessions_collection, leads_collection, batches_collection

# Same thresholds as ingest.py — keep in sync
THRESHOLDS = {
    "min_page_views":   3,
    "min_time_sec":     120,
    "cart_added":       True,
    "checkout_started": True,
    "min_sessions":     5,
    "min_scroll":       80,
}

POLL_INTERVAL = 180   # 3 minutes


async def check_and_promote_visitors():
    """
    Scan visitor_sessions for sessions that:
      1. Have NOT been promoted to a lead yet (is_lead == False)
      2. Cross at least one engagement threshold
    For each match, create a lead and optionally fire the pipeline.
    Also handles returning visitors: updates sdk_activity on existing leads.
    """
    now = datetime.now(timezone.utc)

    # ── 1. Update existing leads with latest session stats ─────────────────
    async for sess in visitor_sessions_collection.find({"is_lead": True}):
        company_id = sess["company_id"]
        visitor_id = sess["visitor_id"]
        lead = await leads_collection.find_one(
            {"company_id": company_id, "visitor_id": visitor_id}
        )
        if not lead:
            continue
        await leads_collection.update_one(
            {"_id": lead["_id"]},
            {"$set": {
                "sdk_activity.page_views":       sess.get("total_page_views", 0),
                "sdk_activity.total_time_sec":   sess.get("total_time_sec", 0),
                "sdk_activity.max_scroll":        sess.get("max_scroll_depth", 0),
                "sdk_activity.engagement_score":  sess.get("engagement_score", 0),
                "sdk_activity.cart_added":        sess.get("cart_added", False),
                "sdk_activity.checkout_started":  sess.get("checkout_started", False),
                "sdk_activity.purchase_made":     sess.get("purchase_made", False),
                "sdk_activity.sessions_count":    sess.get("sessions_count", 0),
                "sdk_activity.last_seen":         sess.get("last_seen"),
                "updated_at":                     now,
            }},
        )

    # ── 2. Find unpromotable sessions that NOW cross threshold ─────────────
    # Build a MongoDB $or query covering all threshold conditions
    threshold_filter = {
        "is_lead": {"$ne": True},
        "$or": [
            {"cart_added":       True},
            {"checkout_started": True},
            {"purchase_made":    True},
            {
                "total_page_views": {"$gte": THRESHOLDS["min_page_views"]},
                "total_time_sec":   {"$gte": THRESHOLDS["min_time_sec"]},
            },
            {"sessions_count":    {"$gte": THRESHOLDS["min_sessions"]}},
            {
                "max_scroll_depth":  {"$gte": THRESHOLDS["min_scroll"]},
                "is_product_visitor": True,
            },
            {"identified_email": {"$exists": True, "$nin": [None, ""]}},
        ]
    }

    import secrets

    async for sess in visitor_sessions_collection.find(threshold_filter):
        company_id = sess["company_id"]
        visitor_id = sess["visitor_id"]

        # Double-check not already a lead
        existing = await leads_collection.find_one(
            {"company_id": company_id, "visitor_id": visitor_id}
        )
        if existing:
            # Mark session as promoted in case it slipped through
            await visitor_sessions_collection.update_one(
                {"_id": sess["_id"]},
                {"$set": {"is_lead": True, "lead_id": existing.get("lead_id")}},
            )
            continue

        identified_email = sess.get("identified_email", "")
        lead_id = f"L_AUTO_{secrets.token_hex(3).upper()}"

        # Build lead document from session data
        lead_doc = {
            "lead_id":    lead_id,
            "company_id": company_id,
            "batch_id":   "sdk_auto",
            "source":     "sdk",
            "visitor_id": visitor_id,
            "visitor_ids": [visitor_id],
            "status":     "new" if identified_email else "hot_visitor",
            "profile": {
                "name":    sess.get("identified_name", f"Visitor {visitor_id[:8]}"),
                "email":   identified_email,
                "company": sess.get("identified_company", ""),
                "title":   "",
                "phone":   sess.get("identified_phone", ""),
                "city":    sess.get("identified_city", ""),
                "state":   sess.get("identified_state", ""),
            },
            "pipeline_stage": "New Lead",
            "intel":  {},
            "crm":    {
                "notes":         "Auto-promoted by LeadMind engagement threshold scanner.",
                "next_followup": None,
            },
            "sdk_activity": {
                "page_views":       sess.get("total_page_views", 0),
                "total_time_sec":   sess.get("total_time_sec", 0),
                "max_scroll":       sess.get("max_scroll_depth", 0),
                "engagement_score": sess.get("engagement_score", 0),
                "cart_added":       sess.get("cart_added", False),
                "checkout_started": sess.get("checkout_started", False),
                "purchase_made":    sess.get("purchase_made", False),
                "sessions_count":   sess.get("sessions_count", 0),
                "last_seen":        sess.get("last_seen"),
                "urls":             sess.get("pages_viewed_list", []),
                "device_type":      sess.get("device_type"),
                "utm_source":       sess.get("utm_source"),
                "utm_medium":       sess.get("utm_medium"),
                "utm_campaign":     sess.get("utm_campaign"),
            },
            "created_at": now,
        }
        await leads_collection.insert_one(lead_doc)

        # Mark session as promoted
        await visitor_sessions_collection.update_one(
            {"_id": sess["_id"]},
            {"$set": {"is_lead": True, "lead_id": lead_id}},
        )

        print(f"[AutoPipeline] Promoted visitor {visitor_id[:12]} → Lead {lead_id}")

        # Only fire pipeline if we have an email (can't research anonymous)
        if identified_email:
            import asyncio as _aio
            from services.agent_runner import run_pipeline_for_lead
            _aio.create_task(run_pipeline_for_lead(lead_id, "sdk_auto", company_id))


async def auto_pipeline_loop():
    """Long-running background task — runs in FastAPI lifespan."""
    print("[AutoPipeline] v2 Started — polling every 3 minutes")
    while True:
        try:
            await check_and_promote_visitors()
        except Exception as e:
            print(f"[AutoPipeline] Error: {e}")
        await asyncio.sleep(POLL_INTERVAL)
