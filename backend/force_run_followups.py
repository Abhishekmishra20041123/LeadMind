import asyncio
from db import followup_queue_collection
from datetime import datetime, timedelta

async def main():
    now = datetime.utcnow()
    # Set scheduled_at to 1 minute ago for all pending jobs to force them to run
    result = await followup_queue_collection.update_many(
        {"status": "pending"},
        {"$set": {"scheduled_at": now - timedelta(minutes=1)}}
    )
    print(f"Force-scheduled {result.modified_count} pending jobs to run immediately.")
    print("The background scheduler should pick them up within a minute.")

if __name__ == "__main__":
    asyncio.run(main())
