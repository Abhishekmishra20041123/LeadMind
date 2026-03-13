import asyncio
import motor.motor_asyncio
import urllib.parse
import os

async def run():
    client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.SalesAgent
    
    # Just find any lead with sent_html
    leads = await db.leads.find({"intel.email.sent_html": {"$exists": True}}).to_list(10)
    if not leads:
        print("No leads with sent_html found")
        return
        
    for lead in leads:
        html = lead.get('intel', {}).get('email', {}).get('sent_html', '')
        if html:
            print(f"Lead {lead.get('lead_id')}:")
            print('  len:', len(html))
            print('  has base64:', 'data:image' in html)
            
            if 'data:image' in html:
                idx = html.find('data:image')
                print("  Found base64 at index:", idx)
                print("  Surrounding context:")
                print("  " + html[max(0, idx-50):min(len(html), idx+100)])

asyncio.run(run())
