import asyncio, sys, json
sys.path.insert(0, 'backend')
from db import leads_collection

async def main():
    doc = await leads_collection.find_one({'lead_id': 'L_4C9E5BA9'})
    if doc:
        intel = doc.get('intel', {})
        print(f"Subject: {intel.get('email', {}).get('subject')}")
        print(f"Media count: {len(intel.get('scraped_media', []))}")
        for m in intel.get('scraped_media', []):
            name = str(m.get('name', 'N/A')).encode('ascii', 'ignore').decode('ascii')
            price = str(m.get('price', 'N/A')).encode('ascii', 'ignore').decode('ascii')
            print(f" - {name}: {price}")
    else:
        print("Lead not found")

if __name__ == '__main__':
    asyncio.run(main())
