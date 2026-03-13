import asyncio
from db import email_logs_collection

async def main():
    async for log in email_logs_collection.find().sort("sent_at", -1).limit(1):
        print(f"To: {log.get('lead_id')}")
        print(f"Subject: {log.get('subject')}")
        print("--- CONTENT SNAPSHOT ---")
        print(log.get('content_snapshot', ''))

asyncio.run(main())
