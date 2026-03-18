import asyncio
import os
import sys

# Add project root to path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from backend.db import leads_collection

async def check_db():
    lead = await leads_collection.find_one({'lead_id': 'L_JX_DEMO'})
    if not lead:
        print("Lead not found.")
        return
        
    print("=== RAW DB CONTENT ===")
    intel = lead.get('intel', {})
    email = intel.get('email', {})
    preview = email.get('preview', 'NOT_FOUND')
    print("Preview HTML:")
    print(preview)
    
if __name__ == "__main__":
    asyncio.run(check_db())
