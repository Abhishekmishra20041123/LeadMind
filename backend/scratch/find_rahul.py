import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("mongodb", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "SalesAgent")

async def find_visitor():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_database(DB_NAME)
    sessions = db.get_collection("visitor_sessions")
    
    # Try to find by name or something similar
    # The image shows "RAHUL AJAY MISHRA"
    # Sessions might have a lead_id or identified_email
    
    visitor = await sessions.find_one({"$or": [
        {"identified_email": {"$regex": "rahul", "$options": "i"}},
        {"visitor_id": {"$regex": "rahul", "$options": "i"}},
        {"metadata.name": {"$regex": "rahul", "$options": "i"}}
    ]})
    
    if not visitor:
        # Check leads collection too
        leads = db.get_collection("leads")
        lead = await leads.find_one({"profile.name": {"$regex": "Rahul Ajay Mishra", "$options": "i"}})
        if lead:
            print(f"Found in leads: {lead.get('lead_id')}")
            # Try to find session by lead_id or email
            email = lead.get('profile', {}).get('email')
            if email:
                visitor = await sessions.find_one({"identified_email": email})
            if not visitor:
                # Some systems link by visitor_id in leads
                vid = lead.get('visitor_id')
                if vid:
                    visitor = await sessions.find_one({"visitor_id": vid})
        
    if visitor:
        print("Found Visitor Session:")
        print(visitor)
    else:
        print("Visitor not found.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(find_visitor())
