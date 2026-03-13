import asyncio
from db import followup_queue_collection, email_logs_collection
from datetime import datetime

async def main():
    cursor = followup_queue_collection.find().sort("scheduled_at", -1).limit(10)
    jobs = await cursor.to_list(length=10)
    
    print(f"--- RECENT FOLLOW-UP JOBS (Current Time: {datetime.utcnow()}) ---")
    for job in jobs:
        print(f"ID: {job['_id']} | Status: {job['status']} | Scheduled: {job['scheduled_at']}")
        if job.get('error'):
            print(f"  Error: {job['error'][:100]}")
    
    print("\n--- RECENT EMAIL LOGS ---")
    cursor = email_logs_collection.find({"is_followup": True}).sort("sent_at", -1).limit(5)
    logs = await cursor.to_list(length=5)
    for log in logs:
        print(f"Lead: {log.get('lead_id')} | Sent: {log.get('sent_at')} | Subject: {log.get('subject')}")

if __name__ == "__main__":
    asyncio.run(main())
