
import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def dump_lead():
    load_dotenv()
    mongo_url = os.getenv("mongodb")
    client = AsyncIOMotorClient(mongo_url)
    db = client.get_default_database()
    
    batch_id = 'BATCH_2026_03_15_1063C09B'
    lead = await db['leads'].find_one({'batch_id': batch_id})
    
    if lead:
        lead['_id'] = str(lead['_id'])
        lead['company_id'] = str(lead['company_id'])
        print(json.dumps(lead, indent=2))

    client.close()

if __name__ == "__main__":
    asyncio.run(dump_lead())
