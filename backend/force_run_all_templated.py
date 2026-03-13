import asyncio
from db import followup_queue_collection, email_templates_collection
from datetime import datetime, timedelta

async def main():
    now = datetime.utcnow()
    
    latest_tpl = await email_templates_collection.find_one({}, sort=[("created_at", -1)])
    if not latest_tpl:
        print("No templates found.")
        return
        
    tpl_id = str(latest_tpl["_id"])
    print(f"Force-applying template: {latest_tpl.get('name')} to all pending jobs.")

    # Reset ALL pending and failed jobs to run NOW with the latest template
    result = await followup_queue_collection.update_many(
        {"status": {"$in": ["pending", "failed"]}},
        {
            "$set": {
                "status": "pending",
                "template_id": tpl_id,
                "scheduled_at": now - timedelta(minutes=1),
                "error": None
            }
        }
    )
    
    print(f"Success: {result.modified_count} jobs updated and forced to run.")

if __name__ == "__main__":
    asyncio.run(main())
