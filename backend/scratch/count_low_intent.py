import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = "mongodb+srv://23102180_db_user:9tuXTOlIZyGMHHA2@cluster0.5fmzadc.mongodb.net/SalesAgent?retryWrites=true&w=majority"
DB_NAME = "SalesAgent"

async def count_low_intent():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    leads_collection = db["leads"]
    
    # Check for intent_score < 1
    query = {
        "intel.intent_score": {"$lt": 1}
    }
    
    count = await leads_collection.count_documents(query)
    print(f"Found {count} leads with intel.intent_score < 1.")
    
    # Also check if it's stored at the root
    query_root = {
        "intent_score": {"$lt": 1}
    }
    count_root = await leads_collection.count_documents(query_root)
    print(f"Found {count_root} leads with root intent_score < 1.")

    client.close()

if __name__ == "__main__":
    asyncio.run(count_low_intent())
