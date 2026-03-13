import asyncio
from db import email_logs_collection, leads_collection

async def main():
    # Find the very last email sent
    latest_log = await email_logs_collection.find_one({}, sort=[("sent_at", -1)])
    if not latest_log:
        print("No email logs found.")
        return

    lead_id = latest_log.get("lead_id")
    token = latest_log.get("tracking_token")
    sent_at = latest_log.get("sent_at")
    
    print(f"Latest Email Log:")
    print(f"  Lead ID: {lead_id}")
    print(f"  Token: {token}")
    print(f"  Sent At: {sent_at}")
    
    content = latest_log.get("content_snapshot", "")
    print(f"  Content Length: {len(content)} bytes")
    
    # Check for tracking pixel
    import re
    # Look for /api/track/open
    pixel_match = re.search(r'src="([^"]*?/api/track/open\?token=[^"]*)"', content)
    if pixel_match:
        print(f"  ✅ Tracking Pixel Found: {pixel_match.group(1)}")
    else:
        print("  ❌ Tracking Pixel NOT found in content_snapshot!")
        # Check first 500 characters and last 500 characters
        print("--- CONTENT START ---")
        print(content[:500])
        print("--- CONTENT END ---")
        print(content[-500:])

    # Check lead document as well
    lead_doc = await leads_collection.find_one({"lead_id": lead_id})
    if lead_doc:
        lead_html = lead_doc.get("intel", {}).get("email", {}).get("sent_html", "")
        lead_pixel_match = re.search(r'src="([^"]*?/api/track/open\?token=[^"]*)"', lead_html)
        if lead_pixel_match:
            print(f"  ✅ Tracking Pixel Found in Lead Doc: {lead_pixel_match.group(1)}")
        else:
            print("  ❌ Tracking Pixel NOT found in Lead Doc sent_html!")

asyncio.run(main())
