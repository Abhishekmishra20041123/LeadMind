import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("mongodb", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "SalesAgent")

async def find_rahul():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_database(DB_NAME)
    leads = db.get_collection("leads")
    
    # Search for Rahul Ajay Mishra
    cursor = leads.find({"profile.name": {"$regex": "Rahul", "$options": "i"}})
    results = await cursor.to_list(length=10)
    
    for r in results:
        try:
            print(f"Found Lead: {r.get('profile', {}).get('name')}")
            print(f"Lead ID: {r.get('lead_id')}")
            # Use repr for sdk_activity and intel to avoid unicode print issues
            print(f"SDK Activity: {repr(r.get('sdk_activity'))}")
            print(f"Intel: {repr(r.get('intel'))}")
            print("-" * 20)
        except Exception as e:
            print(f"Error printing record: {e}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(find_rahul())
