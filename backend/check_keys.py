import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.SalesAgent

async def main():
    keys = await db.api_keys.find({}).to_list(length=10)
    print("API Keys in DB:")
    for key in keys:
        print(f"- Key: {key.get('key')}, Active: {key.get('is_active')}, Company: {key.get('company_id')}")

if __name__ == "__main__":
    asyncio.run(main())
