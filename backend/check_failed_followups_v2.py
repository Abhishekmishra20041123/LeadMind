import asyncio
from db import followup_queue_collection, leads_collection
from bson import ObjectId

async def main():
    cursor = followup_queue_collection.find({"status": "failed"}).sort("created_at", -1).limit(5)
    failed_jobs = await cursor.to_list(length=5)
    
    if not failed_jobs:
        print("No failed jobs")
        return

    for job in failed_jobs:
        print(f"--- FAILED JOB {job['_id']} ---")
        lead = await leads_collection.find_one({"lead_id": job.get("lead_id")})
        to_email = lead.get("contact", {}).get("email") if lead else "N/A"
        print(f"Lead: {job.get('lead_id')} | To: {to_email}")
        print(f"Subject: {job.get('subject')}")
        print(f"Error: {job.get('error')}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(main())
