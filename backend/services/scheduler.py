import asyncio
from datetime import datetime
from bson import ObjectId
from db import (
    followup_queue_collection, leads_collection, email_logs_collection, 
    agent_activity_collection, email_templates_collection, companies_collection
)
from services.email_sender import EmailService
from services.templating import render_blocks_to_html, render_template

async def process_followups():
    """Poll the queue for pending follow-ups that are due."""
    now = datetime.utcnow()
    
    cursor = followup_queue_collection.find({
        "status": "pending",
        "scheduled_at": {"$lte": now}
    })
    
    pending_jobs = await cursor.to_list(length=50) # Batch size of 50
    
    for job in pending_jobs:
        job_id = job["_id"]
        lead_id = job["lead_id"]
        company_id = job["company_id"]
        template_id = job.get("template_id")
        subject = job.get("subject", "Follow up")
        content = job.get("content", "")
        
        try:
            # Mark processing
            await followup_queue_collection.update_one(
                {"_id": job_id},
                {"$set": {"status": "processing"}}
            )
            
            # Fetch lead details
            lead = await leads_collection.find_one({"lead_id": lead_id, "company_id": company_id})
            if not lead:
                 raise ValueError(f"Lead {lead_id} not found in database.")

            to_email = lead.get("contact", {}).get("email") if lead else None
            
            # Override to_email to default for now as requested
            to_email = "mishraabhishek1703@gmail.com"
            print(f"[Scheduler] Lead {lead_id} being sent to default receiver: {to_email}")

            final_html = content
            
            # ── Apply Template ──────────────────────────────────────────────────
            if template_id:
                try:
                    tpl_doc = await email_templates_collection.find_one({
                        "_id": ObjectId(template_id),
                        "company_id": ObjectId(str(company_id))
                    })
                    if tpl_doc:
                        company_doc = await companies_collection.find_one({"_id": ObjectId(str(company_id))}) or {}
                        
                        # Prepare lead dict for template replacements
                        # We need 'intel.email.preview' to store the body for {{personalized_message}}
                        lead_copy = dict(lead)
                        if "intel" not in lead_copy: lead_copy["intel"] = {}
                        if "email" not in lead_copy["intel"]: lead_copy["intel"]["email"] = {}
                        
                        # Format body content (preserve breaks)
                        clean_content = content
                        
                        # Optional: If template has a greeting block, we might want to strip 
                        # the hardcoded "Hi {name}" from the start of content to avoid repeats.
                        has_greeting_block = any(b.get("type") == "greeting" for b in tpl_doc.get("blocks", []))
                        if has_greeting_block:
                            import re
                            # Remove "Hi ..., <br/>" or similar greeting patterns from the start
                            clean_content = re.sub(r'^<p>Hi[^,]+,</p>', '', content, flags=re.IGNORECASE).strip()
                            # If it starts with a <br/> or extra space after stripping, clean it
                            clean_content = re.sub(r'^(<br\s*/?>|\s)+', '', clean_content).strip()

                        lead_copy["intel"]["email"]["preview"] = clean_content

                        tpl_html = render_blocks_to_html(tpl_doc.get("blocks", []), tpl_doc.get("global_styles", {}))
                        final_html = render_template(tpl_html, lead_copy, company_doc)
                        print(f"[Scheduler] Applied template {template_id} to follow-up for {lead_id}")
                except Exception as tpl_err:
                    print(f"[Scheduler] Warning: Failed to apply template {template_id}: {tpl_err}")
                    # Fallback to raw content if template application fails

            # Dispatch
            await EmailService.send_email(
                company_id=str(company_id),
                to_address=to_email,
                subject=subject,
                html_content=final_html
            )
            
            # Mark complete
            await followup_queue_collection.update_one(
                {"_id": job_id},
                {"$set": {"status": "completed", "executed_at": datetime.utcnow()}}
            )
            
            # Audit trail
            await email_logs_collection.insert_one({
                "company_id": company_id,
                "batch_id": lead.get("batch_id") if lead else None,
                "lead_id": lead_id,
                "subject": subject,
                "content_snapshot": final_html, # Store fully rendered themed HTML
                "sent_at": datetime.utcnow(),
                "status": "delivered",
                "is_followup": True
            })
            
            await agent_activity_collection.insert_one({
                "company_id": company_id,
                "batch_id": lead.get("batch_id") if lead else None,
                "lead_id": lead_id,
                "agent": "SCHEDULER",
                "action": f"Executed scheduled follow-up: {subject} (Themed)",
                "status": "SUCCESS",
                "timestamp": datetime.utcnow()
            })
            print(f"[Scheduler] Sent follow-up for lead {lead_id}")
            
        except Exception as e:
            print(f"[Scheduler] Follow-up job {job_id} failed: {e}")
            await followup_queue_collection.update_one(
                {"_id": job_id},
                {"$set": {"status": "failed", "error": str(e)}}
            )

async def scheduler_loop():
    print("Background Follow-up Scheduler Started.")
    while True:
        try:
            await process_followups()
        except Exception as e:
            print(f"Scheduler loop error: {e}")
        await asyncio.sleep(60) # Poll every 60 seconds
