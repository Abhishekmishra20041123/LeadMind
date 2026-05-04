import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    mongo_url = os.getenv("mongodb", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["SalesAgent"]
    user = await db.companies.find_one({"email": "e2e@test.com"})
    print("USER IN DB:")
    if user:
        print(f"Email: {user.get('email')}")
        print(f"Password Hash: {user.get('password_hash')}")
        print(f"Company ID: {user.get('_id')}")
    else:
        print("Not Found")

if __name__ == "__main__":
    asyncio.run(main())
