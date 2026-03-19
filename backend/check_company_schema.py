import asyncio
from db import companies_collection

async def run():
    doc = await companies_collection.find_one({'email': 'admin@qoder.ai'})
    if doc:
        # Print keys to see if company_id is present
        print(f"Total keys: {len(doc.keys())}")
        print(f"Keys: {doc.keys()}")
        print(f"Full Doc: {doc}")
    else:
        print("Not found")

if __name__ == '__main__':
    asyncio.run(run())
