
import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def check_schema_mapping():
    load_dotenv()
    mongo_url = os.getenv("mongodb")
    client = AsyncIOMotorClient(mongo_url)
    db = client.get_default_database()
    
    batch_id = 'BATCH_2026_03_15_1063C09B'
    batch = await db['batches'].find_one({'batch_id': batch_id})
    
    if batch:
        print(f"Batch: {batch_id}")
        discovery = batch.get('discovery_result')
        print(f"Full Discovery Result: {json.dumps(discovery, indent=2)}")
        
        # Check a raw lead too
        lead = await db['leads'].find_one({'batch_id': batch_id})
        if lead:
            print(f"\nLead {lead.get('lead_id')} raw_data keys: {list(lead.get('raw_data', {}).keys())}")
            print(f"Lead page_link field: {lead.get('page_link')}")
            print(f"Lead intel status: {lead.get('intel', {}).get('status')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_schema_mapping())
