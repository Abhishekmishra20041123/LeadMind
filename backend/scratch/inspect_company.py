import asyncio
from db import companies_collection

async def main():
    companies = await companies_collection.find().to_list(10)
    for c in companies:
        print(c)

if __name__ == "__main__":
    asyncio.run(main())
