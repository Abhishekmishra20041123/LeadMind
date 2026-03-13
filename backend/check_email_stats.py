import asyncio
from db import email_logs_collection

async def main():
    async for log in email_logs_collection.find().sort("sent_at", -1).limit(1):
        print(f"To: {log.get('lead_id')}")
        print(f"Subject: {log.get('subject')}")
        content = log.get('content_snapshot', '')
        print(f"Content Length: {len(content)}")
        if "data:image" in content:
            print("FOUND BASE64 IMAGE IN CONTENT")
        if "res.cloudinary.com" in content:
            print("FOUND CLOUDINARY URL IN CONTENT")
        print("--- CONTENT START ---")
        print(content[:500])
        print("--- CONTENT END ---")
        print(content[-500:])

asyncio.run(main())
