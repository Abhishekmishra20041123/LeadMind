
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client["strategic_grid"]

leads_collection = db["leads"]
agent_activity_collection = db["agent_activity"]
email_logs_collection = db["email_logs"]
followup_queue_collection = db["followup_queue"]

async def test_delete():
    # 1. Create a dummy lead
    lead_id = "TEST_DELETE_001"
    company_id = ObjectId()
    
    lead = {
        "lead_id": lead_id,
        "company_id": company_id,
        "name": "Test Delete",
        "email": "test@example.com"
    }
    await leads_collection.insert_one(lead)
    
    # 2. Add associated data
    await agent_activity_collection.insert_one({"lead_id": lead_id, "company_id": company_id, "action": "test"})
    await email_logs_collection.insert_one({"lead_id": lead_id, "company_id": company_id, "subject": "test"})
    await followup_queue_collection.insert_one({"lead_id": lead_id, "company_id": company_id, "status": "pending"})
    
    print(f"Created lead and associated data for {lead_id}")
    
    # 3. Simulate delete_lead logic
    async def delete_logic(rid, cid):
        lead_result = await leads_collection.delete_one({"lead_id": rid, "company_id": cid})
        if lead_result.deleted_count == 0:
             return False
        await agent_activity_collection.delete_many({"lead_id": rid, "company_id": cid})
        await email_logs_collection.delete_many({"lead_id": rid, "company_id": cid})
        await followup_queue_collection.delete_many({"lead_id": rid, "company_id": cid})
        return True

    success = await delete_logic(lead_id, company_id)
    print(f"Delete logic success: {success}")
    
    # 4. Verify
    l = await leads_collection.find_one({"lead_id": lead_id})
    a = await agent_activity_collection.find_one({"lead_id": lead_id})
    e = await email_logs_collection.find_one({"lead_id": lead_id})
    f = await followup_queue_collection.find_one({"lead_id": lead_id})
    
    print(f"Lead remaining: {l is not None}")
    print(f"Activity remaining: {a is not None}")
    print(f"Email logs remaining: {e is not None}")
    print(f"Followup remaining: {f is not None}")
    
    if not any([l, a, e, f]):
        print("VERIFICATION SUCCESS: All data cleared.")
    else:
        print("VERIFICATION FAILED: Some data remains.")

if __name__ == "__main__":
    asyncio.run(test_delete())
