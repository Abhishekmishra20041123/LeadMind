import asyncio
from db import leads_collection, companies_collection
from bson import ObjectId
import os

async def main():
    lead = await leads_collection.find_one({"lead_id": "L051"})
    if not lead:
        print("Lead L051 not found")
        return
        
    company_id = lead.get("company_id")
    company = await companies_collection.find_one({"_id": company_id})
    if not company:
        print(f"Company {company_id} not found")
        return
        
    settings = company.get("settings", {})
    smtp_user = settings.get("smtp_user")
    smtp_pass = "********" if settings.get("smtp_pass") else None
    
    print(f"SMTP User: {smtp_user}")
    print(f"SMTP Pass: {smtp_pass}")
    print(f"From Name: {settings.get('from_name')}")
    print(f"From Email: {settings.get('from_email')}")
    
    # Check resolv
    from services.email_sender import _resolve_smtp
    host, port = _resolve_smtp(smtp_user or "")
    print(f"Derived Host: {host}")
    print(f"Derived Port: {port}")
    
    # Check env overrides
    print(f"ENV SMTP_HOST: {os.getenv('SMTP_HOST')}")
    print(f"ENV SMTP_PORT: {os.getenv('SMTP_PORT')}")

if __name__ == "__main__":
    asyncio.run(main())
