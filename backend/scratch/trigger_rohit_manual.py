import asyncio
import os
import sys
from bson import ObjectId

# Add the project root and backend to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
backend_dir = os.path.join(root_dir, "backend")
if root_dir not in sys.path:
    sys.path.append(root_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Now we can import
from services.agent_runner import run_pipeline_for_lead

async def main():
    lead_id = "L_SDK_B242414D"
    company_id = "69bcc3b357aa22e20696713b"
    batch_id = "sdk_identify"
    
    print(f"Manually triggering pipeline for lead {lead_id}...")
    await run_pipeline_for_lead(lead_id, batch_id, company_id)
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
