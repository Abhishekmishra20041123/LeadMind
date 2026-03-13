import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    mongo_url = os.getenv("mongodb")
    client = AsyncIOMotorClient(mongo_url)
    db = client.get_database("SalesAgent")
    leads_collection = db.get_collection("leads")
    
    # Get the latest lead with a batch_id
    lead = await leads_collection.find_one({"batch_id": {"$exists": True}}, sort=[("_id", -1)])
    
    if not lead:
        print("No leads found.")
        return
        
    print(f"Lead ID: {lead.get('lead_id')}")
    print(f"Name: {lead.get('profile', {}).get('name')}")
    print(f"Batch ID: {lead.get('batch_id')}")
    print(f"Status: {lead.get('status')}")
    
    intel = lead.get("intel", {})
    email = intel.get("email", {})
    
    print("\n--- PREVIEW ---")
    print(email.get("preview")[:500])
    
    print("\n--- SENT_HTML ---")
    sent_html = email.get("sent_html", "")
    print(sent_html[:500])
    if len(sent_html) > 500:
        print("...")
        print(sent_html[-500:])

if __name__ == "__main__":
    asyncio.run(main())
