import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json

# Use the Atlas URI from .env
MONGO_URI = "mongodb+srv://23102180_db_user:9tuXTOlIZyGMHHA2@cluster0.5fmzadc.mongodb.net/SalesAgent?retryWrites=true&w=majority"
DB_NAME = "SalesAgent"

async def check_lead_structure():
    print(f"Connecting to Atlas...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    leads_collection = db["leads"]
    
    lead = await leads_collection.find_one({})
    if lead:
        # Convert ObjectId to string for printing
        if "_id" in lead:
            lead["_id"] = str(lead["_id"])
        print(json.dumps(lead, indent=2))
        
        # Check for zero intent leads
        query = {
            "$or": [
                {"intent_score": 0},
                {"intel.intent_score": 0},
                {"intent_score": "0"},
                {"intel.intent_score": "0"}
            ]
        }
        count = await leads_collection.count_documents(query)
        print(f"\nFound {count} leads with intent_score = 0 in Atlas.")
        
    else:
        collections = await db.list_collection_names()
        print(f"No leads found. Available collections: {collections}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_lead_structure())
