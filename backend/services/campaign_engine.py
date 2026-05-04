"""
Campaign Engine — Background Drip Campaign Processor (Phase 2)

Polls campaign_enrollments for steps that are due (next_step_at <= now).
Checks conditional branching, dispatches emails via email_sender, advances enrollment.

Run pattern: mirrors scheduler.py — started in FastAPI lifespan as asyncio.create_task.
"""

import asyncio
from datetime import datetime, timedelta
from bson import ObjectId
import uuid
from db import (
    campaign_enrollments_collection,
    campaigns_collection,
    leads_collection,
    email_logs_collection,
    agent_activity_collection,
    email_opens_collection
)
from services.email_sender import EmailService


POLL_INTERVAL_SECONDS = 60   # check every 60 seconds (same cadence as scheduler)
BATCH_SIZE = 50              # process at most 50 enrollments per tick


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _check_condition(condition: dict, enrollment: dict, company_id) -> bool:
    """
    Evaluate whether a step's proceed_if condition is met.

    Supported conditions:
      always            → always proceed
      opened_previous   → lead opened the previous campaign step email
      clicked_previous  → lead clicked a link in the previous campaign step email
    """
    proceed_if = condition.get("proceed_if", "always")

    if proceed_if == "always":
        return True

    # Look up recent email_logs for this lead from this campaign to check open/click
    lead_id     = enrollment.get("lead_id")
    campaign_id = str(enrollment.get("campaign_id"))

    recent_log = await email_logs_collection.find_one(
        {
            "company_id":  company_id,
            "lead_id":     lead_id,
            "campaign_id": campaign_id,
        },
        sort=[("sent_at", -1)],
    )

    if not recent_log:
        return False  # No email record — skip to avoid false positives

    if proceed_if == "opened_previous":
        return bool(recent_log.get("open_count", 0) > 0)

    if proceed_if == "clicked_previous":
        return bool(recent_log.get("click_count", 0) > 0)

    return True  # fallback: proceed


async def _get_next_step(steps: list, current_step_id: str):
    """
    Return the step dict that comes after current_step_id (by day_offset order).
    Returns None if current is the last step.
    """
    sorted_steps = sorted(steps, key=lambda s: s.get("day_offset", 0))
    for i, step in enumerate(sorted_steps):
        if step["step_id"] == current_step_id:
            if i + 1 < len(sorted_steps):
                return sorted_steps[i + 1]
            return None
    return None


async def _get_step_by_id(steps: list, step_id: str) -> dict | None:
    """Find a step dict by its step_id."""
    for step in steps:
        if step["step_id"] == step_id:
            return step
    return None


# ── Core Processing ────────────────────────────────────────────────────────────

async def process_campaign_enrollments():
    """
    Main tick: find all active enrollments whose next_step_at <= now,
    apply conditions, send email, advance to the next step.
    """
    now = datetime.utcnow()

    cursor = campaign_enrollments_collection.find(
        {"status": "active", "next_step_at": {"$lte": now}},
        limit=BATCH_SIZE,
    )
    due_enrollments = await cursor.to_list(length=BATCH_SIZE)

    if not due_enrollments:
        return

    print(f"[CampaignEngine] Processing {len(due_enrollments)} due enrollment(s)...")

    for enrollment in due_enrollments:
        enrollment_id = enrollment["_id"]
        campaign_id   = enrollment["campaign_id"]
        lead_id       = enrollment["lead_id"]
        company_id    = enrollment["company_id"]
        current_step  = enrollment["current_step"]

        try:
            # ── 1. Lock: mark as processing to prevent double-send ─────────────
            updated = await campaign_enrollments_collection.find_one_and_update(
                {"_id": enrollment_id, "status": "active"},
                {"$set": {"status": "processing"}},
            )
            if not updated:
                continue  # another worker grabbed it

            # ── 2. Fetch campaign definition ───────────────────────────────────
            campaign = await campaigns_collection.find_one({"_id": campaign_id})
            if not campaign or campaign.get("status") == "paused":
                # Campaign deleted or paused — drop enrollment
                await campaign_enrollments_collection.update_one(
                    {"_id": enrollment_id},
                    {"$set": {"status": "dropped", "dropped_reason": "campaign_paused_or_deleted"}}
                )
                continue

            steps = campaign.get("steps", [])
            step  = await _get_step_by_id(steps, current_step)
            if not step:
                # Step gone — drop
                await campaign_enrollments_collection.update_one(
                    {"_id": enrollment_id},
                    {"$set": {"status": "dropped", "dropped_reason": "step_not_found"}}
                )
                continue

            # ── 3. Check conditional branching ─────────────────────────────────
            condition = step.get("conditions", {"proceed_if": "always"})
            should_proceed = await _check_condition(condition, enrollment, company_id)

            if not should_proceed:
                # Condition not met: drop this lead from the campaign
                await campaign_enrollments_collection.update_one(
                    {"_id": enrollment_id},
                    {"$set": {"status": "dropped", "dropped_reason": "condition_not_met"}}
                )
                print(f"[CampaignEngine] Lead {lead_id} dropped at step {current_step} — condition not met")
                continue

            # ── 4. Fetch lead details ──────────────────────────────────────────
            lead = await leads_collection.find_one(
                {"lead_id": lead_id, "company_id": company_id}
            )
            if not lead:
                await campaign_enrollments_collection.update_one(
                    {"_id": enrollment_id},
                    {"$set": {"status": "dropped", "dropped_reason": "lead_not_found"}}
                )
                continue

            to_email = lead.get("contact", {}).get("email", "")

            # Simple template variable substitution
            profile = lead.get("profile", {})
            subject = step.get("subject", "").replace("{{name}}", profile.get("name", "there"))
            content = step.get("content", "").replace("{{name}}", profile.get("name", "there"))
            content = content.replace("{{company}}", profile.get("company", ""))
            content = content.replace("{{title}}", profile.get("title", ""))

            # ── 5. Send email with tracking ────────────────────────────────────
            tracking_token = str(uuid.uuid4())
            await email_opens_collection.insert_one({
                "token":      tracking_token,
                "lead_id":    lead_id,
                "company_id": ObjectId(str(company_id)),
                "subject":    subject,
                "sent_at":    datetime.utcnow(),
                "open_count": 0,
                "click_count":0,
                "is_campaign":True
            })

            await EmailService.send_email(
                company_id=str(company_id),
                to_address=to_email,
                subject=subject,
                html_content=f"<div style='font-family:sans-serif;line-height:1.6'>{content}</div>",
                tracking_token=tracking_token
            )

            # ── 6. Log the send ────────────────────────────────────────────────
            await email_logs_collection.insert_one({
                "company_id":   company_id,
                "lead_id":      lead_id,
                "campaign_id":  str(campaign_id),
                "step_id":      current_step,
                "subject":      subject,
                "content_snapshot": content,
                "sent_at":      datetime.utcnow(),
                "status":       "delivered",
                "open_count":   0,
                "click_count":  0,
                "is_campaign":  True,
            })

            # ── 7. Advance to next step ─────────────────────────────────────────
            next_step = await _get_next_step(steps, current_step)

            if next_step:
                next_step_id = next_step["step_id"]
                day_offset   = next_step.get("day_offset", 1)
                next_run     = datetime.utcnow() + timedelta(days=day_offset)

                await campaign_enrollments_collection.update_one(
                    {"_id": enrollment_id},
                    {"$set": {
                        "status":       "active",
                        "current_step": next_step_id,
                        "next_step_at": next_run,
                    }, "$push": {
                        "step_history": {
                            "step_id":   current_step,
                            "sent_at":   datetime.utcnow(),
                            "email_to":  to_email,
                        }
                    }}
                )
            else:
                # Last step done — mark complete
                await campaign_enrollments_collection.update_one(
                    {"_id": enrollment_id},
                    {"$set": {
                        "status":       "completed",
                        "completed_at": datetime.utcnow(),
                    }, "$push": {
                        "step_history": {
                            "step_id":   current_step,
                            "sent_at":   datetime.utcnow(),
                            "email_to":  to_email,
                        }
                    }}
                )
                await campaigns_collection.update_one(
                    {"_id": campaign_id},
                    {"$inc": {"completed_count": 1}}
                )

            # ── 8. Audit trail ─────────────────────────────────────────────────
            await agent_activity_collection.insert_one({
                "company_id":  company_id,
                "lead_id":     lead_id,
                "agent":       "CAMPAIGN_ENGINE",
                "action":      f"Sent campaign step '{current_step}' from campaign '{campaign.get('name', '')}' to {to_email}",
                "status":      "SUCCESS",
                "timestamp":   datetime.utcnow(),
            })

            print(f"[CampaignEngine] ✅ Step '{current_step}' → lead '{lead_id}' sent")

        except Exception as exc:
            print(f"[CampaignEngine] ❌ Enrollment {enrollment_id} error: {exc}")
            # Restore to active so it retries next tick
            await campaign_enrollments_collection.update_one(
                {"_id": enrollment_id},
                {"$set": {"status": "active", "last_error": str(exc)}}
            )


# ── Background Loop ────────────────────────────────────────────────────────────

async def campaign_engine_loop():
    """
    Long-running background coroutine. Mirrors scheduler_loop() pattern.
    Started in FastAPI lifespan alongside scheduler.
    """
    print("[CampaignEngine] Background Campaign Engine Started.")
    while True:
        try:
            await process_campaign_enrollments()
        except Exception as exc:
            print(f"[CampaignEngine] Loop error: {exc}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
