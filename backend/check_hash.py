import asyncio
from db import companies_collection
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def check():
    email = "admin@qoder.ai"
    company = await companies_collection.find_one({"email": email})
    if company:
        print(f"User: {email}")
        print(f"Hash: {company.get('password_hash')}")
        # Test against 'password123'
        is_valid = pwd_context.verify("password123", company["password_hash"])
        print(f"Is 'password123' valid? {is_valid}")
    else:
        print(f"User {email} not found")

if __name__ == '__main__':
    asyncio.run(check())
