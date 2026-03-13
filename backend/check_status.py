import asyncio
from db import followup_queue_collection
from datetime import datetime

async def main():
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    counts = await followup_queue_collection.aggregate(pipeline).to_list(10)
    print("--- JOB STATUS COUNTS ---")
    for c in counts:
        print(f"{c['_id']}: {c['count']}")
    
    # Check if any are overdue
    now = datetime.utcnow()
    overdue = await followup_queue_collection.count_documents({"status": "pending", "scheduled_at": {"$lte": now}})
    print(f"Overdue Pending: {overdue}")

if __name__ == "__main__":
    asyncio.run(main())
