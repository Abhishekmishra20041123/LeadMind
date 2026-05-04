import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = "mongodb+srv://23102180_db_user:9tuXTOlIZyGMHHA2@cluster0.5fmzadc.mongodb.net/SalesAgent?retryWrites=true&w=majority"
DB_NAME = "SalesAgent"

async def check_engagement_scores():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    leads_collection = db["leads"]
    
    # Check raw_data.Engagement_Score (exact name from CSV)
    pipeline = [
        {"$group": {"_id": "$raw_data.Engagement_Score", "count": {"$sum": 1}}}
    ]
    
    results = await leads_collection.aggregate(pipeline).to_list(None)
    print("Engagement Score Distribution (raw_data.Engagement_Score):")
    for r in results:
        print(f"Score: {r['_id']}, Count: {r['count']}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_engagement_scores())
