import asyncio
import sys
import os

sys.path.append(os.path.abspath('backend'))
from db import leads_collection

async def update():
    urls = "https://www.tiffany.com/engagement/engagement-rings/platinum-diamond-engagement-rings-1711.html,https://www.tiffany.com/jewelry/necklaces-pendants/tiffany-t-18k-yellow-gold-diamond-necklaces-pendants-1364184611.html,https://www.tiffany.com/jewelry/earrings/tiffany-t-18k-yellow-gold-diamond-earrings-1361328805.html"
    res = await leads_collection.update_many(
        {"lead_id": "L_JX_DEMO"},
        {"$set": {"page_link": urls, "raw_data.page_link": urls}}
    )
    print("Modified:", res.modified_count)

asyncio.run(update())
