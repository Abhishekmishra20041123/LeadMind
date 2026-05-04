import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Use the Atlas URI from .env
MONGO_URI = "mongodb+srv://23102180_db_user:9tuXTOlIZyGMHHA2@cluster0.5fmzadc.mongodb.net/SalesAgent?retryWrites=true&w=majority"
DB_NAME = "SalesAgent"

async def cleanup_atlas_leads():
    print(f"Connecting to Atlas...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    leads_collection = db["leads"]
    
    # Define query based on intent_score being 0
    query = {
        "$or": [
            {"intent_score": 0},
            {"intel.intent_score": 0},
            {"intent_score": "0"},
            {"intel.intent_score": "0"},
            {"intent_score": 0.0},
            {"intel.intent_score": 0.0}
        ]
    }
    
    # Count first
    count = await leads_collection.count_documents(query)
    print(f"Found {count} leads with intent_score = 0 in Atlas.")
    
    if count > 0:
        result = await leads_collection.delete_many(query)
        print(f"Successfully deleted {result.deleted_count} leads from Atlas.")
    else:
        print("No leads found to delete.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(cleanup_atlas_leads())
