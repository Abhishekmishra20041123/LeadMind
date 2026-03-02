import asyncio
from db import companies_collection
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def test_user_login():
    email = "e2e@test.com"
    pwd = "password123"
    company = await companies_collection.find_one({"email": email})
    
    if not company:
        print(f"Company {email} not found")
        return
        
    print(f"Company Found: {company['company_name']}")
    print(f"Password Hash: {company.get('password_hash')}")
    
    if 'password_hash' not in company:
        print("ERROR: User has no password hash!")
        print("Dropping invalid user...")
        await companies_collection.delete_one({"email": email})
        print("Dropped.")
        return
        
    is_valid = pwd_context.verify(pwd, company["password_hash"])
    print(f"Password Verify Result: {is_valid}")
    
    # If it fails, maybe drop the user so we can re-register?
    if not is_valid:
        print("Dropping user with invalid password...")
        await companies_collection.delete_one({"email": email})
        print("Dropped.")

if __name__ == "__main__":
    asyncio.run(test_user_login())
