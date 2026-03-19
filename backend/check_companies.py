import asyncio
from db import companies_collection

async def check():
    cursor = companies_collection.find({})
    async for doc in cursor:
        print(f"Company: {doc.get('company_name', 'N/A')}, Email: {doc.get('email', 'N/A')}")

if __name__ == '__main__':
    asyncio.run(check())
