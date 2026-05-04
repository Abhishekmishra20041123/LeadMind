import asyncio
from db import leads_collection

async def run():
    doc = await leads_collection.find_one({'lead_id': 'L005'})
    if doc:
        print(doc.get('intel', {}).get('email', {}).get('preview'))
    else:
        print("Not found")

if __name__ == '__main__':
    asyncio.run(run())
