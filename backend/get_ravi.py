import asyncio
from db import leads_collection

async def run():
    doc = await leads_collection.find_one({'lead_id': 'L_JX_002'})
    if doc:
        print(f"ID: {doc.get('lead_id')}")
        print(f"Preview: {doc.get('intel', {}).get('email', {}).get('preview')}")
    else:
        # Search by name
        doc = await leads_collection.find_one({'profile.name': 'Ravi Singh'})
        if doc:
             print(f"Found Ravi as {doc.get('lead_id')}")
             print(f"Preview: {doc.get('intel', {}).get('email', {}).get('preview')}")
        else:
             print("Not found")

if __name__ == '__main__':
    asyncio.run(run())
