import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("mongodb", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "SalesAgent")

async def check_voice_logs():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_database(DB_NAME)
    activity = db.get_collection("agent_activity")
    
    print("Checking for VOICE_AGENT_LIVE activities...")
    cursor = activity.find({"agent": "VOICE_AGENT_LIVE"}).sort("timestamp", -1).limit(20)
    
    found = False
    async for log in cursor:
        found = True
        print(f"[{log.get('timestamp')}] {log.get('action')} | Status: {log.get('status')}")
        
    if not found:
        print("No VOICE_AGENT_LIVE logs found. The webhook might not be reaching the backend.")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(check_voice_logs())
