import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = "mongodb+srv://23102180_db_user:9tuXTOlIZyGMHHA2@cluster0.5fmzadc.mongodb.net/SalesAgent?retryWrites=true&w=majority"
DB_NAME = "SalesAgent"

async def debug_atlas_zero_intent():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    leads_collection = db["leads"]
    
    # Let's find leads where ANY common intent/score field is 0
    # and also look at what fields exist in the document
    
    all_leads = await leads_collection.find({}).to_list(100)
    print(f"Total leads scanned: {len(all_leads)}")
    
    found_zero = 0
    for lead in all_leads:
        # Check root
        if lead.get("intent_score") == 0:
            found_zero += 1
            continue
            
        # Check intel
        intel = lead.get("intel", {})
        if isinstance(intel, dict):
            if intel.get("intent_score") == 0 or intel.get("engagement_score") == 0:
                found_zero += 1
                continue
        
        # Check engagement
        engagement = lead.get("engagement", {})
        if isinstance(engagement, dict):
             if engagement.get("score") == 0:
                 found_zero += 1
                 continue
                 
    print(f"Found {found_zero} leads that might match 'zero intent' criteria.")
    
    # If we still find 0, let's print the keys of the first lead's intel again but safely
    if len(all_leads) > 0:
        first = all_leads[0]
        print(f"Keys in lead: {list(first.keys())}")
        if "intel" in first:
            print(f"Keys in intel: {list(first['intel'].keys())}")
            # Print intent_score if it exists
            print(f"Intent Score in intel: {first['intel'].get('intent_score')}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(debug_atlas_zero_intent())
