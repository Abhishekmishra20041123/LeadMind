import asyncio
from db import email_templates_collection

async def main():
    cursor = email_templates_collection.find({}, {"name": 1})
    docs = await cursor.to_list(length=100)
    print("--- AVAILABLE TEMPLATES ---")
    for d in docs:
        print(f"ID: {d['_id']} | Name: {d.get('name')}")

if __name__ == "__main__":
    asyncio.run(main())
