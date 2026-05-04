import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = "mongodb+srv://23102180_db_user:9tuXTOlIZyGMHHA2@cluster0.5fmzadc.mongodb.net/SalesAgent?retryWrites=true&w=majority"
DB_NAME = "SalesAgent"

async def check_atlas_keys():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    leads_collection = db["leads"]
    
    lead = await leads_collection.find_one({})
    if lead:
        print(f"Lead keys: {list(lead.keys())}")
        if "intel" in lead:
            print(f"Intel keys: {list(lead['intel'].keys())}")
            print(f"Intel data: {lead['intel']}")
    else:
        print("No leads found.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_atlas_keys())
