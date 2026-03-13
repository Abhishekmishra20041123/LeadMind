import asyncio
from db import followup_queue_collection, leads_collection
from bson import ObjectId

async def main():
    # Find few failed follow-ups
    cursor = followup_queue_collection.find({"status": "failed"}).sort("created_at", -1).limit(5)
    failed_jobs = await cursor.to_list(length=5)
    
    if not failed_jobs:
        print("No failed follow-up jobs found in the queue.")
        return

    for job in failed_jobs:
        print(f"--- FAILED JOB {job['_id']} ---")
        print(f"Lead ID: {job.get('lead_id')}")
        print(f"Subject: {job.get('subject')}")
        print(f"Error: {job.get('error')}")
        
        # Get lead email
        lead = await leads_collection.find_one({"lead_id": job.get("lead_id")})
        to_email = lead.get("contact", {}).get("email") if lead else "Unknown"
        print(f"To: {to_email}")
        
        # print("Content:")
        # print(job.get('content'))
        print("\n")

if __name__ == "__main__":
    asyncio.run(main())
