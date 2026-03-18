
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def check():
    load_dotenv()
    mongo_url = os.getenv("mongodb")
    client = AsyncIOMotorClient(mongo_url)
    db = client.get_default_database()
    
    batch_id = 'TEST_FIX_2026_03_15_FFE6FB5E'
    lead_id = 'L002'
    lead = await db['leads'].find_one({'batch_id': batch_id, 'lead_id': lead_id})
    
    if lead:
        print(f"Status: {lead.get('status')}")
        print(f"Intel Status: {lead.get('intel', {}).get('status')}")
        print(f"Error: {lead.get('intel', {}).get('error')}")
        print(f"Email Preview is None: {lead.get('email_preview') is None}")
        print(f"Email Preview Length: {len(lead.get('email_preview')) if lead.get('email_preview') else 0}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check())
