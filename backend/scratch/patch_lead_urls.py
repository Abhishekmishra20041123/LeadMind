import asyncio, sys
sys.path.insert(0, 'backend')
from db import leads_collection

async def main():
    result = await leads_collection.update_one(
        {"lead_id": "L_4C9E5BA9"},
        {"$set": {
            "sdk_activity.product_page_urls": [
                "https://homy-stay-eight.vercel.app/listings/68b3951f67e080a9ad5b66f6",
                "https://homy-stay-eight.vercel.app/bookings/listings/68b3951f67e080a9ad5b66f6/book"
            ]
        }}
    )
    print("Patched:", result.modified_count, "doc")

asyncio.run(main())
