import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import sys
import os

# Set up paths to import backend modules
sys.path.insert(0, os.path.abspath('backend'))
from api.leads import preview_template
from db import leads_collection, email_templates_collection, companies_collection
from api.templates import render_blocks_to_html

async def run_test():
    # Pick the lead
    lead_id = 'L003'
    company_id = "C001" # Tony Stark's company
    
    lead_doc = await leads_collection.find_one({"lead_id": lead_id, "company_id": company_id})
    if not lead_doc:
        print("Lead not found")
        return
        
    tpl_doc = await email_templates_collection.find_one({"company_id": company_id})
    if not tpl_doc:
        print("Template not found")
        return
        
    company_doc = await companies_collection.find_one({"company_id": company_id}) or {}
    
    raw_content = "Hello World\nLine 2"
    formatted_ai_content = raw_content.replace("\n", "<br/>")
    
    lead_with_ai = dict(lead_doc)
    if lead_with_ai.get("intel") is None:
        lead_with_ai["intel"] = {}
    if lead_with_ai["intel"].get("email") is None:
        lead_with_ai["intel"]["email"] = {}
    lead_with_ai["intel"]["email"]["preview"] = formatted_ai_content
    
    try:
        tpl_html = render_blocks_to_html(tpl_doc.get("blocks", []), tpl_doc.get("global_styles", {}))
        
        # Need to import render_template
        from api.leads import render_template
        final_html = render_template(tpl_html, lead_with_ai, company_doc)
        print("SUCCESS! Output length:", len(final_html))
    except Exception as e:
        print("EXCEPTION CAUGHT:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
