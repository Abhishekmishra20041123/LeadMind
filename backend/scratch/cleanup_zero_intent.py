import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

# MongoDB URI
MONGO_URI = os.getenv("mongodb", "mongodb://localhost:27017")
DB_NAME = "SalesAgent"

async def remove_zero_intent_leads():
    print(f"Connecting to {MONGO_URI}, DB: {DB_NAME}...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    leads_collection = db["leads"]
    
    # Try multiple common paths and types for zero intent score
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
    print(f"Found {count} leads with intent_score = 0.")
    
    if count > 0:
        result = await leads_collection.delete_many(query)
        print(f"Successfully deleted {result.deleted_count} leads.")
    else:
        print("No leads found to delete.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(remove_zero_intent_leads())
