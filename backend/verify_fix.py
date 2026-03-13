import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URL = os.getenv("mongodb")
DB_NAME = os.getenv("DB_NAME", "SalesAgent")

async def check():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_database(DB_NAME)
    
    tpl = await db.get_collection("email_templates").find_one({"name": "test2"})
    if tpl:
        blocks_str = str(tpl.get("blocks", []))
        print(f"Template 'test2' blocks size: {len(blocks_str)}")
        if "res.cloudinary.com" in blocks_str:
            print("  Cloudinary URL found in template blocks.")
        if "data:image" in blocks_str:
            print("  WARNING: Base64 still found in template blocks.")
            
    lead = await db.get_collection("leads").find_one({"lead_id": "L003"})
    if lead:
        preview = lead.get("intel", {}).get("email", {}).get("preview", "")
        print(f"Lead L003 preview size: {len(preview)}")
        if "res.cloudinary.com" in preview:
            print("  Cloudinary URL found in lead preview.")
        if "data:image" in preview:
             print("  WARNING: Base64 still found in lead preview.")

if __name__ == "__main__":
    asyncio.run(check())
