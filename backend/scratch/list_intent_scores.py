import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = "mongodb+srv://23102180_db_user:9tuXTOlIZyGMHHA2@cluster0.5fmzadc.mongodb.net/SalesAgent?retryWrites=true&w=majority"
DB_NAME = "SalesAgent"

async def list_intent_scores():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    leads_collection = db["leads"]
    
    # Get all distinct intent scores
    pipeline = [
        {"$group": {"_id": "$intel.intent_score", "count": {"$sum": 1}}}
    ]
    
    results = await leads_collection.aggregate(pipeline).to_list(None)
    print("Intent Score Distribution (intel.intent_score):")
    for r in results:
        print(f"Score: {r['_id']}, Count: {r['count']}")
        
    # Also check root intent_score
    pipeline_root = [
        {"$group": {"_id": "$intent_score", "count": {"$sum": 1}}}
    ]
    results_root = await leads_collection.aggregate(pipeline_root).to_list(None)
    print("\nRoot Intent Score Distribution (intent_score):")
    for r in results_root:
        print(f"Score: {r['_id']}, Count: {r['count']}")

    client.close()

if __name__ == "__main__":
    asyncio.run(list_intent_scores())
