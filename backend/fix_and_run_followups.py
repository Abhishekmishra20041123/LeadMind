import asyncio
from db import followup_queue_collection, email_templates_collection
from datetime import datetime, timedelta
from bson import ObjectId

async def main():
    now = datetime.utcnow()
    
    # 1. Find the latest template
    latest_tpl = await email_templates_collection.find_one({}, sort=[("created_at", -1)])
    if not latest_tpl:
        print("No templates found to apply.")
        return
        
    tpl_id = latest_tpl["_id"]
    tpl_name = latest_tpl.get("name")
    print(f"Using latest template: {tpl_name} ({tpl_id})")

    # 2. Update jobs that are 'failed' or 'pending' and overdue
    # Reset status and set template_id
    query = {
        "status": {"$in": ["failed", "pending"]},
        "scheduled_at": {"$lte": now}
    }
    
    result = await followup_queue_collection.update_many(
        query,
        {
            "$set": {
                "status": "pending",
                "template_id": str(tpl_id),
                "scheduled_at": now - timedelta(minutes=1), # Force run immediately
                "error": None
            }
        }
    )
    
    print(f"Updated {result.modified_count} follow-up jobs. They will now run with template '{tpl_name}' immediately.")

if __name__ == "__main__":
    asyncio.run(main())
