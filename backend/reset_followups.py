import asyncio
from db import followup_queue_collection
from datetime import datetime

async def main():
    # 1. Reset 'failed' jobs to 'pending'
    failed_result = await followup_queue_collection.update_many(
        {"status": "failed"},
        {"$set": {"status": "pending", "error": None}}
    )
    print(f"Reset {failed_result.modified_count} failed follow-up jobs to 'pending'.")

    # 2. Check if there are any 'pending' jobs that are overdue
    now = datetime.utcnow()
    overdue_count = await followup_queue_collection.count_documents({
        "status": "pending",
        "scheduled_at": {"$lte": now}
    })
    print(f"There are currently {overdue_count} overdue pending jobs in the queue.")
    
    if overdue_count > 0:
        print("The background scheduler should pick these up in the next 60 seconds.")
        print("To run them immediately without waiting for the loop, you can restart the backend or wait.")

if __name__ == "__main__":
    asyncio.run(main())
