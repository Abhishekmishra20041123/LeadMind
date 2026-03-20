import os
import re
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body, Depends
import pymongo
from bson import ObjectId

from db import (
    leads_collection, agent_activity_collection, email_logs_collection,
    followup_queue_collection, companies_collection,
    email_opens_collection, email_events_collection,
)
from dependencies import get_current_user
from services.email_sender import EmailService
from services.templating import render_template

router = APIRouter()

@router.get("")
async def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    region: Optional[str] = None,
    lead_source: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: str = Query("asc", regex="^(asc|desc)$"),
    batch_id: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    user=Depends(get_current_user)
):
    query = {"company_id": user["company_id"]}
    if batch_id:
        query["batch_id"] = batch_id
        
    if search:
        search_regex = {"$regex": re.escape(search), "$options": "i"}
        search_or = [
            {"profile.name": search_regex},
            {"profile.company": search_regex},
            {"profile.title": search_regex}
        ]
        
        try:
            int_val = int(search)
            search_or.append({"intel.intent_score": int_val})
        except ValueError:
            pass
            
        query["$or"] = search_or
        
    if region:
        query["profile.region"] = region
    if lead_source:
        query["profile.lead_source"] = lead_source
        
    if min_score is not None or max_score is not None:
        score_query = {}
        if min_score is not None:
            score_query["$gte"] = min_score
        if max_score is not None:
            score_query["$lte"] = max_score
        query["intel.intent_score"] = score_query

    sort_criteria = []
    if sort_by:
        sort_field = sort_by
        if sort_by in ["name", "company", "title", "region", "lead_source"]:
            sort_field = f"profile.{sort_by}"
        elif sort_by == "intent_score":
            sort_field = "intel.intent_score"
            
        direction = pymongo.ASCENDING if sort_dir == "asc" else pymongo.DESCENDING
        sort_criteria.append((sort_field, direction))
    else:
        sort_criteria.append(("_id", pymongo.ASCENDING))

    skip = (page - 1) * page_size
    
    total = await leads_collection.count_documents(query)
    cursor = leads_collection.find(query).sort(sort_criteria).skip(skip).limit(page_size)
    leads = await cursor.to_list(length=page_size)
    
    leads_list = []
    for lead_doc in leads:
        profile = lead_doc.get("profile", {})
        activity = lead_doc.get("activity", {})
        flat_lead = {
            "lead_id": lead_doc.get("lead_id"),
            "name": profile.get("name", "Unknown"),
            "company": profile.get("company", "Unknown"),
            "title": profile.get("title", "Unknown"),
            "region": profile.get("region", "Unknown"),
            "lead_source": profile.get("lead_source", "Unknown"),
            "visits": activity.get("visits", 0),
            "time_on_site": activity.get("time_on_site", 0.0),
            "pages_per_visit": activity.get("pages_per_visit", 0.0),
            "converted": activity.get("converted", False),
            "intent_score": lead_doc.get("intel", {}).get("intent_score", 0),
            "status": lead_doc.get("status", "Unknown"),
            "record_id": lead_doc.get("lead_id"),
            "email_sent": lead_doc.get("crm", {}).get("email_sent", False),
            "last_sent_at": lead_doc.get("crm", {}).get("last_sent_at", None),
            "email": lead_doc.get("contact", {}).get("email", ""),
        }
        leads_list.append(flat_lead)
        
    return {
        "data": leads_list,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/stats")
async def lead_stats(batch_id: Optional[str] = None, user=Depends(get_current_user)):
    query = {"company_id": user["company_id"]}
    if batch_id:
        query["batch_id"] = batch_id
        
    pipeline = [
        {"$match": query},
        {"$facet": {
            "total": [{"$count": "count"}],
            "active": [{"$match": {"status": {"$in": ["Analysis", "Processing_"]}}}, {"$count": "count"}],
            "ready": [{"$match": {"status": "Ready"}}, {"$count": "count"}],
            "converted": [{"$match": {"activity.converted": True}}, {"$count": "count"}]
        }}
    ]
    
    result = await leads_collection.aggregate(pipeline).to_list(length=1)
    stats = result[0]
    
    total_leads = stats["total"][0]["count"] if stats["total"] else 0
    active_pursuits = stats["active"][0]["count"] if stats["active"] else 0
    ready_leads = stats["ready"][0]["count"] if stats["ready"] else 0
    converted_leads = stats["converted"][0]["count"] if stats["converted"] else 0
    
    conversion_rate = round((converted_leads / total_leads) * 100, 1) if total_leads > 0 else 0
        
    return {
        "total": total_leads,
        "active_pursuits": active_pursuits,
        "conversion_rate": conversion_rate,
        "ready": ready_leads
    }

@router.get("/filters")
async def lead_filters(batch_id: Optional[str] = None, user=Depends(get_current_user)):
    query = {"company_id": user["company_id"]}
    if batch_id:
        query["batch_id"] = batch_id
        
    regions = await leads_collection.distinct("profile.region", query)
    sources = await leads_collection.distinct("profile.lead_source", query)
    
    return {
        "regions": sorted([r for r in regions if r]),
        "lead_sources": sorted([s for s in sources if s])
    }

@router.get("/{record_id}")
async def get_lead_details(record_id: str, batch_id: Optional[str] = None, user=Depends(get_current_user)):
    """Retrieve full intelligence report data for a specific lead."""
    query = {"company_id": user["company_id"], "lead_id": record_id}
    if batch_id:
        query["batch_id"] = batch_id
        
    lead_doc = await leads_collection.find_one(query)
    if not lead_doc:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    profile = lead_doc.get("profile", {})
    name = profile.get("name", "Unknown")
    company = profile.get("company", "Unknown")
    
    intel = lead_doc.get("intel", {})
    email_data = intel.get("email", {})
    email_preview = email_data.get("preview", "")

    # Clean redundant elements like AI footers/buttons
    from services.templating import clean_ai_content
    email_preview_str = clean_ai_content(str(email_preview).replace('\\n', '\n'))
    draft_blocks = []
    
    # THE FIX: If the email is already HTML, do NOT split it by newlines.
    # Splitting HTML by \n and wrapping each line in <p> completely destroys
    # <div> and <img> product card structure, making images disappear.
    # The frontend handles type='html' by rendering it as a raw div (preserving all tags).
    if email_preview_str.strip().startswith('<'):
        draft_blocks = [{"type": "html", "content": email_preview_str}]
    else:
        # Fallback for plain text emails: split by newlines into blocks
        for line in email_preview_str.split('\n'):
            if line.strip() == "":
                draft_blocks.append({"type": "br"})
            else:
                draft_blocks.append({"type": "text", "content": line})

            
    quality_indicators = intel.get("quality_indicators", [])
    research_signals = [
        f"{q.get('metric', '')}: {q.get('value', '')}" if isinstance(q, dict) else str(q)
        for q in quality_indicators
    ]
    if not research_signals:
         research_signals = ["High Engagement", "Target Account Hit"] # fallback UI
         
    key_signals = intel.get("key_signals", [])
    signals_list = [s.get("signal", str(s)) if isinstance(s, dict) else str(s) for s in key_signals]
    intent_reasoning = " • ".join(signals_list) if signals_list else "Pending analysis"
    
    timing_data = intel.get("timing", {})
    timing_rec = f"{timing_data.get('recommended_date', '')} {timing_data.get('send_time', '')}".strip()
    
    crm_logs = []
    cursor = agent_activity_collection.find({"lead_id": record_id, "company_id": user["company_id"]}).sort("timestamp", 1)
    activities = await cursor.to_list(length=100)
    
    for act in activities:
        crm_logs.append({
            "time": act.get("timestamp").strftime("%H:%M:%S") if act.get("timestamp") else "",
            "agent": act.get("agent", "SYSTEM"),
            "action": act.get("action", ""),
            "status": act.get("status", "SUCCESS")
        })

    # Fallback log if empty
    if not crm_logs:
        crm_logs.append({
             "time": datetime.utcnow().strftime("%H:%M:%S"),
             "agent": "SYSTEM",
             "action": "Legacy record loaded from database.",
             "status": "INFO"
        })

    return {
        "lead_id": record_id,
        "email": lead_doc.get("contact", {}).get("email", ""),
        "profile": {
            "name": name,
            "title": profile.get("title", "Unknown"),
            "company": company,
            "linkedin": profile.get('linkedin') or f"linkedin.com/in/{name.lower().replace(' ', '')}",
            "website": profile.get('website') or f"{company.lower().replace(' ', '')}.com",
            "bio": profile.get('bio') or f"{profile.get('title')} at {company}"
        },
        "agents": {
            "research": {
                "summary": "Processed via LangGraph Pipeline.",
                "signals": research_signals
            },
            "intent": {
                "score": intel.get("intent_score", 0),
                "reasoning": intent_reasoning,
                "recommendation": intel.get("intent_recommendation", {})
            },
            "message": {
                "draft": draft_blocks,
                "subject": email_data.get("subject", ""),
                "personalization_factors": email_data.get("personalization_factors", [])
            },
            "timing": {
                "recommended": timing_rec,
                "recommendedReason": timing_data.get("reasoning", ""),
                "optimal_time_window": timing_data.get("optimal_time_window", ""),
                "approach": intel.get("approach", {}),
                "engagement_prediction": intel.get("engagement_prediction", {}),
                "timeline": lead_doc.get("crm", {}).get("timeline", {})
            },
            "crm": {
                "logs": crm_logs
            }
        },
        "status": lead_doc.get("status", "Ready"),
        "batch_id": lead_doc.get("batch_id"),
        "email_sent": lead_doc.get("crm", {}).get("email_sent", False),
        "last_sent_at": lead_doc.get("crm", {}).get("last_sent_at", None),
    }

@router.post("/{lead_id}/preview-template")
async def preview_template(lead_id: str, payload: dict = Body(...), user=Depends(get_current_user)):
    """
    Preview the email with the given template applied.
    """
    template_id = payload.get("template_id")
    raw_content = payload.get("content", "")
    
    if not template_id:
        return {"html": raw_content}
        
    from db import email_templates_collection, companies_collection, leads_collection
    from bson import ObjectId
    
    lead_doc = await leads_collection.find_one({"lead_id": lead_id, "company_id": user["company_id"]})
    if not lead_doc:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    try:
        tpl_doc = await email_templates_collection.find_one({"_id": ObjectId(template_id), "company_id": user["company_id"]})
    except:
        tpl_doc = None
        
    if not tpl_doc:
        raise HTTPException(status_code=404, detail="Template not found")
        
    company_doc = await companies_collection.find_one({"_id": user["company_id"]}) or {}
    
    # Format AI content (only add breaks for plain text; preserve HTML formatting)
    if raw_content.strip().startswith("<"):
        formatted_ai_content = raw_content
    else:
        formatted_ai_content = raw_content.replace("\n", "<br/>")
        formatted_ai_content = formatted_ai_content.replace("<p>", "<p style='margin:0 0 16px 0;'>")
    
    # Temporarily replace {{personalized_message}} placeholder in the lead dict
    lead_with_ai = dict(lead_doc)
    if lead_with_ai.get("intel") is None:
        lead_with_ai["intel"] = {}
    if lead_with_ai["intel"].get("email") is None:
        lead_with_ai["intel"]["email"] = {}
    lead_with_ai["intel"]["email"]["preview"] = formatted_ai_content
    
    from api.templates import render_blocks_to_html
    
    tpl_html = render_blocks_to_html(tpl_doc.get("blocks", []), tpl_doc.get("global_styles", {}))
    final_html = render_template(tpl_html, lead_with_ai, company_doc)
    
    return {"html": final_html}


@router.patch("/{record_id}/status")
async def update_lead_status(record_id: str, payload: dict = Body(...), user=Depends(get_current_user)):
    new_status = payload.get("status")
    intent_score = payload.get("intent_score")
    
    if not new_status and intent_score is None:
        raise HTTPException(status_code=400, detail="Missing status or intent_score in body")
        
    query = {"lead_id": record_id, "company_id": user["company_id"]}
    update_data = {}
    
    if new_status:
        update_data["status"] = new_status
    if intent_score is not None:
        update_data["intel.intent_score"] = intent_score
        
    update_data["updated_at"] = datetime.utcnow()
    
    result = await leads_collection.update_one(query, {"$set": update_data})
    
    if result.matched_count == 0:
         raise HTTPException(status_code=404, detail="Lead not found")
         
    return {"status": "success"}


# Logic moved to services/templating.py


@router.post("/{record_id}/approve-email")
async def approve_email(record_id: str, payload: dict = Body(...), user=Depends(get_current_user)):
    """Send approved email and log to CRM. Returns 409 if already sent."""
    subject = payload.get("subject")
    content = payload.get("content")
    to_email = "mishraabhishek1703@gmail.com"
    force = payload.get("force", False)  # allow forced re-send if explicitly requested
    
    if not subject or not content:
        raise HTTPException(status_code=400, detail="Missing subject or content")
        
    query = {"lead_id": record_id, "company_id": user["company_id"]}
    lead_doc = await leads_collection.find_one(query)
    if not lead_doc:
         raise HTTPException(status_code=404, detail="Lead not found")

    # ── Duplicate guard ────────────────────────────────────────────────────────
    if not force and lead_doc.get("crm", {}).get("email_sent", False):
        last_sent = lead_doc.get("crm", {}).get("last_sent_at")
        last_sent_str = last_sent.isoformat() if last_sent else None
        raise HTTPException(
            status_code=409,
            detail={"already_sent": True, "sent_at": last_sent_str}
        )
         
    # ── Optional: wrap AI content in a saved email template ───────────────────
    template_id = payload.get("template_id")
    final_html_content = content  # default: raw AI/edited content

    if template_id:
        from db import email_templates_collection, companies_collection
        from bson import ObjectId
        try:
            tpl_doc = await email_templates_collection.find_one({
                "_id": ObjectId(template_id),
                "company_id": user["company_id"]
            })
        except Exception:
            tpl_doc = None

        if tpl_doc:
            company_doc = await companies_collection.find_one({"_id": user["company_id"]}) or {}
            
            # Format AI content (only add breaks for plain text; preserve HTML formatting)
            if content.strip().startswith("<"):
                formatted_ai_content = content
            else:
                formatted_ai_content = content.replace("\n", "<br/>")
                formatted_ai_content = formatted_ai_content.replace("<p>", "<p style='margin:0 0 16px 0;'>")

            # Temporarily replace {{personalized_message}} placeholder in the lead dict
            lead_with_ai = dict(lead_doc)
            if lead_with_ai.get("intel") is None:
                lead_with_ai["intel"] = {}
            if lead_with_ai["intel"].get("email") is None:
                lead_with_ai["intel"]["email"] = {}
            lead_with_ai["intel"]["email"]["preview"] = formatted_ai_content

            from api.templates import render_blocks_to_html
            tpl_html = render_blocks_to_html(
                tpl_doc.get("blocks", []),
                tpl_doc.get("global_styles", {})
            )
            # render_template will replace {{personalized_message}} with formatted_ai_content
            final_html_content = render_template(tpl_html, lead_with_ai, company_doc)

    # Generate a secure UUID token for this specific email send
    tracking_token = str(uuid.uuid4())

    try:
        print(f"Attempting to send email to {to_email}")
        final_tracked_html = await EmailService.send_email(
            company_id=user["company_id"],
            to_address=to_email,
            subject=subject,
            html_content=final_html_content,
            tracking_token=tracking_token,
        )
        print(f"Email sent successfully. Final size: {len(final_tracked_html)} bytes")
        if len(final_tracked_html) > 102000:
            print("WARNING: Email size exceeds 102KB (Gmail limit). Clipping is likely.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Email sending failed with error: {e}")
        raise HTTPException(status_code=500, detail=f"Email delivery failed: {str(e)}")
        
    # 2. Update CRM state
    now = datetime.utcnow()
    
    await leads_collection.update_one(query, {
        "$set": {
            "status": "Email Dispatched",
            "crm.email_sent": True,
            "crm.last_sent_at": now,
            "intel.email.sent_html": final_tracked_html,   # store FULLY TEMPLATED & TRACKED HTML
            "updated_at": now
        }
    })
    
    # 4. Log to activity
    await agent_activity_collection.insert_one({
        "company_id": user["company_id"],
        "batch_id": lead_doc.get("batch_id"),
        "lead_id": record_id,
        "agent": "HUMAN",
        "action": f"Approved and dispatched email via UI (Size: {len(final_tracked_html)} bytes)",
        "status": "SUCCESS",
        "timestamp": now
    })
    
    # 5. Log to email_logs
    await email_logs_collection.insert_one({
        "company_id": user["company_id"],
        "batch_id": lead_doc.get("batch_id"),
        "lead_id": record_id,
        "subject": subject,
        "content_snapshot": final_tracked_html, # store FULLY TEMPLATED & TRACKED HTML
        "sent_at": now,
        "status": "delivered",
        "tracking_token": tracking_token,
    })

    # 4b. Seed email_opens summary document (open_count starts at 0)
    await email_opens_collection.insert_one({
        "token":          tracking_token,
        "lead_id":        record_id,
        "company_id":     user["company_id"],
        "open_count":     0,
        "click_count":    0,
        "first_opened_at":  None,
        "last_opened_at":   None,
        "first_clicked_at": None,
        "last_clicked_at":  None,
        "created_at":     now,
    })
    
    # 5. AUTO-SCHEDULE FOLLOW-UP using AI timing data
    try:
        from datetime import timedelta
        timing_data = lead_doc.get("intel", {}).get("timing", {})
        recommended_date = timing_data.get("recommended_date", "")
        send_time = timing_data.get("send_time", "10:00")

        if recommended_date:
            try:
                scheduled_at = datetime.strptime(
                    f"{recommended_date} {send_time}", "%Y-%m-%d %H:%M"
                )
            except ValueError:
                scheduled_at = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=3)
        else:
            scheduled_at = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=3)

        # ✅ Safety check: if the scheduled date is already in the past,
        # reschedule to 3 days from now at 10:00 AM UTC
        if scheduled_at <= datetime.utcnow():
            scheduled_at = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=3)
            print(f"[Auto-Schedule] AI-recommended date was in the past. Rescheduled to {scheduled_at}")

        # Build a quick follow-up reminder email
        lead_name = lead_doc.get("profile", {}).get("name", "there")
        lead_company = lead_doc.get("profile", {}).get("company", "your company")
        followup_subject = f"Quick follow-up: {subject}"
        followup_content = f"""<p>Hi {lead_name},</p>
<p>Just following up on my previous email regarding a potential opportunity for {lead_company}.</p>
<p>I wanted to make sure it didn't get lost in your inbox. Would love to connect and explore if there's a fit.</p>
<p>Feel free to reply here or grab a time that works for you.</p>
<p>Best regards</p>"""

        await followup_queue_collection.insert_one({
            "company_id": user["company_id"],
            "lead_id": record_id,
            "batch_id": lead_doc.get("batch_id"),
            "subject": followup_subject,
            "content": followup_content,
            "template_id": template_id,
            "status": "pending",
            "scheduled_at": scheduled_at,
            "created_at": now,
            "auto_scheduled": True
        })
        
        # Update CRM timeline
        await leads_collection.update_one(query, {
            "$set": {
                "crm.email_sent": True,
                "crm.timeline.first_contact": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "crm.timeline.next_followup": scheduled_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        })
        
        await agent_activity_collection.insert_one({
            "company_id": user["company_id"],
            "batch_id": lead_doc.get("batch_id"),
            "lead_id": record_id,
            "agent": "SCHEDULER",
            "action": f"Auto-scheduled follow-up for {scheduled_at.strftime('%Y-%m-%d %H:%M')} UTC",
            "status": "QUEUED",
            "timestamp": now
        })
        print(f"[Auto-Schedule] Follow-up queued for lead {record_id} at {scheduled_at}")
        
    except Exception as e:
        print(f"[Auto-Schedule] Warning: Could not auto-schedule follow-up for {record_id}: {e}")
        # Non-fatal — the initial email was already sent successfully
    
    return {"status": "success", "message": "Email sent and logged successfully"}


@router.post("/bulk-approve")
async def bulk_approve_leads(payload: dict = Body(...), user=Depends(get_current_user)):
    """
    Send emails to a list of leads sequentially.
    Skips leads where email has already been sent.
    Returns per-lead result for live frontend progress display.
    Body: { "lead_ids": ["id1", "id2", ...], "template_id": "optional_id" }
    """
    lead_ids: List[str] = payload.get("lead_ids", [])
    if not lead_ids:
        raise HTTPException(status_code=400, detail="lead_ids list is required")

    template_id = payload.get("template_id")
    
    # Pre-fetch template and company doc if template_id is provided
    tpl_doc = None
    company_doc = {}
    if template_id:
        from db import email_templates_collection, companies_collection
        from bson import ObjectId
        try:
            tpl_doc = await email_templates_collection.find_one({
                "_id": ObjectId(template_id),
                "company_id": user["company_id"]
            })
            if tpl_doc:
                company_doc = await companies_collection.find_one({"_id": user["company_id"]}) or {}
        except Exception as e:
            print(f"[BulkApprove] Failed to load template {template_id}: {e}")


    results = []

    for lead_id in lead_ids:
        query = {"lead_id": lead_id, "company_id": user["company_id"]}
        lead_doc = await leads_collection.find_one(query)

        if not lead_doc:
            results.append({
                "lead_id": lead_id,
                "name": "Unknown",
                "company": "Unknown",
                "result": "failed",
                "reason": "Lead not found"
            })
            continue

        profile  = lead_doc.get("profile", {})
        name     = profile.get("name", "Unknown")
        company  = profile.get("company", "Unknown")
        to_email = lead_doc.get("contact", {}).get("email", "")

        # Skip if already sent
        if lead_doc.get("crm", {}).get("email_sent", False):
            last_sent = lead_doc.get("crm", {}).get("last_sent_at")
            results.append({
                "lead_id": lead_id,
                "name": name,
                "company": company,
                "result": "skipped",
                "reason": "Already sent",
                "sent_at": last_sent.isoformat() if last_sent else None
            })
            continue

        # Build email from stored intel
        intel       = lead_doc.get("intel", {})
        email_data  = intel.get("email", {})
        subject     = email_data.get("subject", f"Following up — {company}")
        raw_content = email_data.get("preview", "")

        if not raw_content:
            results.append({
                "lead_id": lead_id,
                "name": name,
                "company": company,
                "result": "failed",
                "reason": "No email draft available — run agent first"
            })
            continue

        # Prepare content exactly like approve_email logic
        final_html_content = raw_content

        if tpl_doc:
            try:
                # Format AI content (only add breaks for plain text; preserve HTML formatting)
                if raw_content.strip().startswith("<"):
                    formatted_ai_content = raw_content
                else:
                    formatted_ai_content = raw_content.replace("\n", "<br/>")
                    formatted_ai_content = formatted_ai_content.replace("<p>", "<p style='margin:0 0 16px 0;'>")

                # Temporarily replace {{personalized_message}} placeholder in the lead dict
                lead_with_ai = dict(lead_doc)
                if lead_with_ai.get("intel") is None:
                    lead_with_ai["intel"] = {}
                if lead_with_ai["intel"].get("email") is None:
                    lead_with_ai["intel"]["email"] = {}
                lead_with_ai["intel"]["email"]["preview"] = formatted_ai_content

                from services.templating import render_blocks_to_html
                tpl_html = render_blocks_to_html(
                    tpl_doc.get("blocks", []),
                    tpl_doc.get("global_styles", {})
                )
                final_html_content = render_template(tpl_html, lead_with_ai, company_doc)
            except Exception as e:
                print(f"[BulkApprove] Failed to apply template for {lead_id}: {e}")
                # Fallback to plain formatting if template fails
                final_html_content = raw_content
        else:
            # Fallback for no template: basic wrapping to ensure it looks reasonable
            if not raw_content.strip().startswith("<"):
                paragraphs = raw_content.split("\n\n")
                html_parts = [f"<p style='margin:0 0 16px 0;'>{p.replace('\\n', '<br/>')}</p>" for p in paragraphs if p.strip()]
                final_html_content = f"<div style='font-family:Arial,sans-serif;font-size:15px;color:#1a1a1a;max-width:600px'>{''.join(html_parts)}</div>"

        # Generate a secure UUID token for this specific email send
        tracking_token = str(uuid.uuid4())

        try:
            # Override to_email to default for now as requested
            to_email = "mishraabhishek1703@gmail.com"
            print(f"  [BulkApprove] No lead email for {name}, overriding with default: {to_email}")

            # 3. Send via SMTP
            final_tracked_html = await EmailService.send_email(
                company_id=user["company_id"],
                to_address=to_email,
                subject=subject,
                html_content=final_html_content,
                tracking_token=tracking_token,
            )

            now = datetime.utcnow()

            await leads_collection.update_one(query, {
                "$set": {
                    "status": "Email Dispatched",
                    "crm.email_sent": True,
                    "crm.last_sent_at": now,
                    "crm.timeline.first_contact": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "intel.email.sent_html": final_tracked_html, # save design
                    "updated_at": now
                }
            })

            await agent_activity_collection.insert_one({
                "company_id": user["company_id"],
                "batch_id": lead_doc.get("batch_id"),
                "lead_id": lead_id,
                "agent": "HUMAN",
                "action": f"Bulk approved and dispatched (Size: {len(final_tracked_html)} bytes)",
                "status": "SUCCESS",
                "timestamp": now
            })

            # Save to logs collection
            await email_logs_collection.insert_one({
                "company_id": user["company_id"],
                "batch_id": lead_doc.get("batch_id"),
                "lead_id": lead_id,
                "subject": subject,
                "content_snapshot": final_tracked_html, # store FULLY tracked design
                "sent_at": now,
                "status": "delivered",
                "tracking_token": tracking_token,
            })

            # Seed email_opens summary document
            await email_opens_collection.insert_one({
                "token":          tracking_token,
                "lead_id":        lead_id,
                "company_id":     user["company_id"],
                "open_count":     0,
                "click_count":    0,
                "first_opened_at":  None,
                "last_opened_at":   None,
                "first_clicked_at": None,
                "last_clicked_at":  None,
                "created_at":     now,
            })

            # ── Auto-schedule follow-up (same as individual approve-email) ──────
            try:
                from datetime import timedelta
                timing_data = lead_doc.get("intel", {}).get("timing", {})
                recommended_date = timing_data.get("recommended_date", "")
                send_time        = timing_data.get("send_time", "10:00")

                if recommended_date:
                    try:
                        scheduled_at = datetime.strptime(f"{recommended_date} {send_time}", "%Y-%m-%d %H:%M")
                    except ValueError:
                        scheduled_at = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=3)
                else:
                    scheduled_at = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=3)

                # Safety: if AI date is in the past, push to 3 days from now
                if scheduled_at <= datetime.utcnow():
                    scheduled_at = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=3)

                followup_subject = f"Quick follow-up: {subject}"
                followup_content = f"""<p>Hi {name},</p>
<p>Just following up on my previous email regarding a potential opportunity for {company}.</p>
<p>I wanted to make sure it didn't get lost in your inbox. Would love to connect and explore if there's a fit.</p>
<p>Feel free to reply here or grab a time that works for you.</p>
<p>Best regards</p>"""

                await followup_queue_collection.insert_one({
                    "company_id": user["company_id"],
                    "lead_id": lead_id,
                    "batch_id": lead_doc.get("batch_id"),
                    "subject": followup_subject,
                    "content": followup_content,
                    "template_id": template_id,
                    "status": "pending",
                    "scheduled_at": scheduled_at,
                    "created_at": now,
                    "auto_scheduled": True
                })

                await leads_collection.update_one(query, {
                    "$set": {
                        "crm.timeline.first_contact": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "crm.timeline.next_followup": scheduled_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                    }
                })

                await agent_activity_collection.insert_one({
                    "company_id": user["company_id"],
                    "batch_id": lead_doc.get("batch_id"),
                    "lead_id": lead_id,
                    "agent": "SCHEDULER",
                    "action": f"Auto-scheduled follow-up for {scheduled_at.strftime('%Y-%m-%d %H:%M')} UTC",
                    "status": "QUEUED",
                    "timestamp": now
                })
                print(f"[BulkApprove] Follow-up queued for lead {lead_id} at {scheduled_at}")

            except Exception as sched_err:
                print(f"[BulkApprove] Warning: could not auto-schedule follow-up for {lead_id}: {sched_err}")
                # Non-fatal — email already sent

            results.append({
                "lead_id": lead_id,
                "name": name,
                "company": company,
                "result": "sent",
                "sent_at": now.isoformat()
            })

        except Exception as e:
            results.append({
                "lead_id": lead_id,
                "name": name,
                "company": company,
                "result": "failed",
                "reason": str(e)
            })

    sent    = [r for r in results if r["result"] == "sent"]
    skipped = [r for r in results if r["result"] == "skipped"]
    failed  = [r for r in results if r["result"] == "failed"]

    return {
        "total":   len(results),
        "sent":    len(sent),
        "skipped": len(skipped),
        "failed":  len(failed),
        "results": results
    }

@router.post("/{record_id}/schedule-followup")
async def schedule_followup(record_id: str, payload: dict = Body(...), user=Depends(get_current_user)):
    """Schedule a future email follow-up"""
    subject = payload.get("subject")
    content = payload.get("content")
    scheduled_at_str = payload.get("scheduled_at") # ISO 8601 string expected
    
    if not subject or not content or not scheduled_at_str:
        raise HTTPException(status_code=400, detail="Missing subject, content, or scheduled_at")
        
    try:
        if scheduled_at_str.endswith("Z"):
            scheduled_at_str = scheduled_at_str[:-1] + "+00:00"
        scheduled_at = datetime.fromisoformat(scheduled_at_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
        
    query = {"lead_id": record_id, "company_id": user["company_id"]}
    lead_doc = await leads_collection.find_one(query)
    if not lead_doc:
         raise HTTPException(status_code=404, detail="Lead not found")
         
    from db import followup_queue_collection
    now = datetime.utcnow()
    
    await followup_queue_collection.insert_one({
        "company_id": user["company_id"],
        "lead_id": record_id,
        "batch_id": lead_doc.get("batch_id"),
        "subject": subject,
        "content": content,
        "status": "pending",
        "scheduled_at": scheduled_at,
        "created_at": now
    })
    
    await agent_activity_collection.insert_one({
        "company_id": user["company_id"],
        "batch_id": lead_doc.get("batch_id"),
        "lead_id": record_id,
        "agent": "HUMAN",
        "action": f"Scheduled follow-up email for {scheduled_at.strftime('%Y-%m-%d %H:%M')}",
        "status": "SUCCESS",
        "timestamp": now
    })
    
    return {"status": "success", "message": "Follow-up scheduled successfully"}


@router.get("/{record_id}/email-engagement")
async def get_email_engagement(record_id: str, user=Depends(get_current_user)):
    """
    Fetch email open and click stats for a specific lead.
    Looks up the latest email_logs doc to get the tracking_token,
    then reads from email_opens and email_events.
    """
    from bson import ObjectId
    # 1. Check if an email was sent and get the tracking token
    # company_id might be a string (from UI send) or ObjectId (from batch)
    company_id_str = user["company_id"]
    company_id_obj = ObjectId(company_id_str)
    
    log_query = {
        "lead_id": record_id, 
        "company_id": {"$in": [company_id_str, company_id_obj]}, 
        "status": "delivered"
    }
    latest_log = await email_logs_collection.find_one(log_query, sort=[("sent_at", pymongo.DESCENDING)])
    
    if not latest_log:
        return {
            "email_sent": False,
            "open_count": 0,
            "click_count": 0,
        }
        
    tracking_token = latest_log.get("tracking_token")
    if not tracking_token:
        # Legacy email sent before tracking was implemented
        return {
            "email_sent": True,
            "last_sent_at": latest_log.get("sent_at"),
            "open_count": 0,
            "click_count": 0,
            "is_legacy": True
        }
        
    # 2. Get summary stats from email_opens
    summary = await email_opens_collection.find_one({"token": tracking_token})
    
    # 3. Get recent individual events from email_events for the timeline
    cursor = email_events_collection.find({"token": tracking_token}).sort("timestamp", pymongo.DESCENDING).limit(5)
    events = await cursor.to_list(length=5)
    
    recent_events = []
    for evt in events:
        recent_events.append({
            "type": evt.get("event_type"),
            "timestamp": evt.get("timestamp"),
            "user_agent": evt.get("user_agent"),
            "ip_address": evt.get("ip_address")
        })
        
    def _iso_utc(dt):
        return dt.isoformat() + "Z" if dt else None
        
    result = {
        "email_sent": True,
        "last_sent_at": _iso_utc(latest_log.get("sent_at")),
        "open_count": summary.get("open_count", 0) if summary else 0,
        "click_count": summary.get("click_count", 0) if summary else 0,
        "first_opened_at": _iso_utc(summary.get("first_opened_at")) if summary else None,
        "last_opened_at": _iso_utc(summary.get("last_opened_at")) if summary else None,
        "first_clicked_at": _iso_utc(summary.get("first_clicked_at")) if summary else None,
        "last_clicked_at": _iso_utc(summary.get("last_clicked_at")) if summary else None,
        "recent_events": recent_events
    }
    return result


@router.delete("/{record_id}")
async def delete_lead(record_id: str, user=Depends(get_current_user)):
    """Delete a lead and its associated data."""
    company_id = user["company_id"]
    
    # 1. Delete lead document
    lead_result = await leads_collection.delete_one({"lead_id": record_id, "company_id": company_id})
    if lead_result.deleted_count == 0:
        # Try checking with record_id as string just in case
        lead_result = await leads_collection.delete_one({"lead_id": record_id, "company_id": company_id})
        if lead_result.deleted_count == 0:
             raise HTTPException(status_code=404, detail="Lead not found")
        
    # 2. Cleanup associated data
    await agent_activity_collection.delete_many({"lead_id": record_id, "company_id": company_id})
    await email_logs_collection.delete_many({"lead_id": record_id, "company_id": company_id})
    await followup_queue_collection.delete_many({"lead_id": record_id, "company_id": company_id})
    
    return {"status": "success", "message": f"Lead {record_id} deleted successfully"}

