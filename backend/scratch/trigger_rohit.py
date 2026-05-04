import asyncio
import os
import sys
from bson import ObjectId

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from db import leads_collection
from services.agent_runner import run_pipeline_for_lead

async def main():
    email = "rohit.test.identity@gmail.com"
    lead = await leads_collection.find_one({"profile.email": email})
    if not lead:
        print(f"Lead {email} not found")
        return
    
    lead_id = lead["lead_id"]
    company_id = str(lead["company_id"])
    print(f"Triggering pipeline for lead {lead_id} (Company: {company_id})...")
    
    await run_pipeline_for_lead(lead_id, "sdk_identify_manual_trigger", company_id)
    print("Pipeline execution complete.")

if __name__ == "__main__":
    asyncio.run(main())
