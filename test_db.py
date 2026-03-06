import asyncio
import os
import sys

root_dir = os.path.dirname(__file__)
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(root_dir, 'backend', '.env'))

from backend.db import leads_collection

async def check_mongo():
    lead = await leads_collection.find_one({}, sort=[("updated_at", -1)])
    if not lead:
        print("No leads found.")
        return
        
    print(f"\n--- LATEST DATABASE ROW: {lead.get('lead_id')} ---")
    timing = lead.get("intel", {}).get("timing", {})
    approach = lead.get("intel", {}).get("approach", {})
    print(f"Timing Date: {timing.get('recommended_date')}")
    print(f"Send Time: {timing.get('send_time')}")
    print(f"Reasoning: {timing.get('reasoning')}")
    print(f"Approach: {approach}")

if __name__ == "__main__":
    asyncio.run(check_mongo())
