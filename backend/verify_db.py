import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://abhishekdb:abhishekdb@cluster0.b7f6x.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
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
