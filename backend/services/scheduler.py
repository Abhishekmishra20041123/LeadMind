import asyncio
from datetime import datetime
from db import followup_queue_collection, leads_collection, email_logs_collection, agent_activity_collection
from services.email_sender import EmailService

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
        subject = job.get("subject", "Follow up")
        content = job.get("content", "")
        
        try:
            # Mark processing
            await followup_queue_collection.update_one(
                {"_id": job_id},
                {"$set": {"status": "processing"}}
            )
            
            # Fetch lead to get target email
            lead = await leads_collection.find_one({"lead_id": lead_id, "company_id": company_id})
            to_email = lead.get("contact", {}).get("email", "mock@lead.com") if lead else "mock@lead.com"
            
            # Dispatch
            await EmailService.send_email(
                company_id=str(company_id),
                to_address=to_email,
                subject=subject,
                html_content=content
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
                "content_snapshot": content,
                "sent_at": datetime.utcnow(),
                "status": "delivered",
                "is_followup": True
            })
            
            await agent_activity_collection.insert_one({
                "company_id": company_id,
                "batch_id": lead.get("batch_id") if lead else None,
                "lead_id": lead_id,
                "agent": "SCHEDULER",
                "action": f"Executed scheduled follow-up: {subject}",
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
