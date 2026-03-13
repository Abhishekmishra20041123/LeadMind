import asyncio
from db import leads_collection

async def main():
    lead = await leads_collection.find_one({"lead_id": "L006"})
    if lead:
        print(f"Lead L006 Email: {lead.get('contact', {}).get('email')}")
    else:
        print("Lead L006 not found")

if __name__ == "__main__":
    asyncio.run(main())
