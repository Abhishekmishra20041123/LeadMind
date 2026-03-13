import asyncio
from db import followup_queue_collection
from datetime import datetime

async def main():
    now = datetime.utcnow()
    print(f"Current UTC: {now}")
    
    # Overdue jobs
    cursor = followup_queue_collection.find({
        "status": "pending",
        "scheduled_at": {"$lte": now}
    }).sort("scheduled_at", 1).limit(10)
    
    overdue_jobs = await cursor.to_list(length=10)
    
    print(f"--- OVERDUE JOBS ({len(overdue_jobs)}) ---")
    for job in overdue_jobs:
        print(f"ID: {str(job['_id'])[-6:]} | Lead: {job.get('lead_id')} | Scheduled: {job['scheduled_at']}")

if __name__ == "__main__":
    asyncio.run(main())
