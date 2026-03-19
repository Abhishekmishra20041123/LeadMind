import asyncio
from db import companies_collection
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def reset():
    email = "admin@qoder.ai"
    new_pwd = "password123"
    hashed = pwd_context.hash(new_pwd)
    
    result = await companies_collection.update_one(
        {"email": email},
        {"$set": {"password_hash": hashed}}
    )
    
    if result.modified_count > 0:
        print(f"Password for {email} reset to '{new_pwd}' successfully.")
    else:
        print(f"Failed to reset password for {email} (User not found or no change).")

if __name__ == '__main__':
    asyncio.run(reset())
