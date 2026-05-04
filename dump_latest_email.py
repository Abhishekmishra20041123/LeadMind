
import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def check():
    load_dotenv()
    mongo_url = os.getenv("mongodb")
    client = AsyncIOMotorClient(mongo_url)
    db = client.get_default_database()
    
    # Find the absolute latest lead in the whole DB
    lead = await db['leads'].find_one(sort=[('_id', -1)])
    
    if lead:
        print(f"Lead ID: {lead.get('lead_id')}")
        print(f"Batch ID: {lead.get('batch_id')}")
        print(f"Links: {lead.get('page_link')}")
        print(f"Preview Length: {len(lead.get('email_preview', ''))}")
        print("\n=== EMAIL PREVIEW ===")
        print(lead.get('email_preview'))
        print("\n=== END PREVIEW ===")
        
        # Check if img tag exists in raw data just in case
        print(f"\n'<img' in preview: {'<img' in lead.get('email_preview', '')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check())
