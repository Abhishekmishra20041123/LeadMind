import asyncio
from db import followup_queue_collection
from datetime import datetime, timedelta

async def main():
    now = datetime.utcnow()
    
    # Check all pending/processing/completed jobs
    cursor = followup_queue_collection.find().sort("scheduled_at", -1).limit(20)
    jobs = await cursor.to_list(length=20)
    
    print(f"--- F-UP JOBS QUEUE | UTC: {now} ---")
    if not jobs:
        print("Empty queue.")
    else:
        for job in jobs:
            print(f"ID: {str(job['_id'])[-6:]} | Status: {job['status']} | Lead: {job.get('lead_id')} | Sch: {job['scheduled_at']}")
            if job.get('error'): print(f"  Err: {job['error']}")

if __name__ == "__main__":
    asyncio.run(main())
