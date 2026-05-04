import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json

MONGO_URI = os.getenv("mongodb", "mongodb://localhost:27017")
DB_NAME = "SalesAgent"

async def check_lead_structure():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    leads_collection = db["leads"]
    
    lead = await leads_collection.find_one({})
    if lead:
        # Convert ObjectId to string for printing
        if "_id" in lead:
            lead["_id"] = str(lead["_id"])
        print(json.dumps(lead, indent=2))
    else:
        # List collections
        collections = await db.list_collection_names()
        print(f"No leads found. Available collections: {collections}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_lead_structure())
