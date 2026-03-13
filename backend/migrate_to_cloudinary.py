import asyncio
import os
import re
import cloudinary.uploader
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

MONGO_URL = os.getenv("mongodb", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "SalesAgent")

client = AsyncIOMotorClient(MONGO_URL)
database = client.get_database(DB_NAME)

templates_collection = database.get_collection("email_templates")
leads_collection = database.get_collection("leads")
email_logs_collection = database.get_collection("email_logs")

def is_base64(src):
    return src and isinstance(src, str) and src.startswith("data:image")

async def migrate_templates():
    print("Migrating email templates...")
    cursor = templates_collection.find({})
    async for tpl in cursor:
        blocks = tpl.get("blocks", [])
        changed = False
        for block in blocks:
            src = block.get("src")
            if is_base64(src):
                print(f"Uploading base64 image in template {tpl.get('name')}...")
                try:
                    res = cloudinary.uploader.upload(src, folder="email_templates_migration")
                    block["src"] = res.get("secure_url")
                    changed = True
                    print(f"  Success: {block['src']}")
                except Exception as e:
                    print(f"  Failed: {e}")
        
        if changed:
            await templates_collection.update_one({"_id": tpl["_id"]}, {"$set": {"blocks": blocks}})
            print(f"Template {tpl.get('name')} updated.")

async def migrate_leads():
    print("Migrating lead drafts...")
    # Base64 can be in intel.email.preview (if saved in old format)
    # Actually, the preview is usually plain text or limited HTML.
    # But let's check.
    cursor = leads_collection.find({"intel.email.preview": {"$regex": "data:image"}})
    async for lead in cursor:
        preview = lead.get("intel", {}).get("email", {}).get("preview", "")
        print(f"Fixing lead {lead.get('lead_id')} draft...")
        
        def replacer(match):
            base64_data = match.group(1)
            try:
                res = cloudinary.uploader.upload(base64_data, folder="leads_migration")
                return f'src="{res.get("secure_url")}"'
            except:
                return match.group(0)

        new_preview = re.sub(r'src="(data:image/[^"]+)"', replacer, preview)
        if new_preview != preview:
            await leads_collection.update_one(
                {"_id": lead["_id"]}, 
                {"$set": {"intel.email.preview": new_preview}}
            )
            print(f"Lead {lead.get('lead_id')} updated.")

async def migrate_logs():
    print("Migrating email logs snapshots...")
    cursor = email_logs_collection.find({"content_snapshot": {"$regex": "data:image"}})
    async for log in cursor:
        snapshot = log.get("content_snapshot", "")
        print(f"Fixing log for lead {log.get('lead_id')}...")
        
        def replacer(match):
            base64_data = match.group(1)
            try:
                res = cloudinary.uploader.upload(base64_data, folder="logs_migration")
                return f'src="{res.get("secure_url")}"'
            except:
                return match.group(0)

        new_snapshot = re.sub(r'src="(data:image/[^"]+)"', replacer, snapshot)
        if new_snapshot != snapshot:
            await email_logs_collection.update_one(
                {"_id": log["_id"]}, 
                {"$set": {"content_snapshot": new_snapshot}}
            )
            print(f"Log for lead {log.get('lead_id')} updated.")

async def main():
    await migrate_templates()
    await migrate_leads()
    await migrate_logs()
    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(main())
