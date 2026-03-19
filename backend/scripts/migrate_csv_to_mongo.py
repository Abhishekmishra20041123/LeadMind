import os
import sys
import json
import asyncio
import pandas as pd
from datetime import datetime

# Add parent to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.db import (
    companies_collection,
    leads_collection,
    email_logs_collection,
    pipeline_collection
)
from bson import ObjectId

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "outputs")

async def migrate_data():
    print("🚀 Starting Legacy Data Migration to MongoDB...")
    
    # 1. Setup default company
    company_email = "admin@strategicgrid.ai"
    company = await companies_collection.find_one({"email": company_email})
    if not company:
        print("Creating default admin company...")
        res = await companies_collection.insert_one({
            "email": company_email,
            "company_name": "LeadMind",
            "password_hash": "mock", # Normally set via signup
            "created_at": datetime.utcnow()
        })
        company_id = res.inserted_id
    else:
        company_id = company["_id"]
        
    print(f"Company ID: {company_id}")
    
    # 2. Migrate Leads & Intel
    leads_csv = os.path.join(DATA_DIR, "Leads_Data.csv")
    intel_json = os.path.join(OUTPUTS_DIR, "intel_db.json")
    
    intel_data = {}
    if os.path.exists(intel_json):
        with open(intel_json, "r") as f:
            try:
                intel_data = json.load(f)
            except:
                pass
                
    if os.path.exists(leads_csv):
        print("Migrating leads from CSV...")
        df = pd.read_csv(leads_csv)
        lead_docs = []
        for _, row in df.iterrows():
            lead_id = str(row.get("lead_id", ""))
            if not lead_id: continue
            
            # Mix with intel
            intel = intel_data.get(lead_id, {})
            
            doc = {
                "company_id": str(company_id),
                "batch_id": "LEGACY_MIGRATION",
                "lead_id": lead_id,
                "profile": {
                    "name": str(row.get("name", "")),
                    "company": str(row.get("company", "")),
                    "title": str(row.get("title", "")),
                    "region": str(row.get("region", "")),
                    "industry": str(row.get("industry", ""))
                },
                "contact": {
                    "email": str(row.get("email", "")),
                    "linkedin": str(row.get("linkedin", ""))
                },
                "activity": {
                    "visits": int(row.get("visits", 0)) if pd.notna(row.get("visits")) else 0,
                    "pages_per_visit": float(row.get("pages_per_visit", 0)) if pd.notna(row.get("pages_per_visit")) else 0,
                    "time_on_site": int(row.get("time_on_site", 0)) if pd.notna(row.get("time_on_site")) else 0
                },
                "intel": {
                    "intent_score": int(row.get("intent_score", 0)) if pd.notna(row.get("intent_score")) else 0,
                    **intel
                },
                "crm": {
                    "converted": bool(row.get("converted", False))
                },
                "status": "Ready" if intel else "Pending",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            lead_docs.append(doc)
            
        if lead_docs:
            await leads_collection.delete_many({"batch_id": "LEGACY_MIGRATION"})
            await leads_collection.insert_many(lead_docs)
            print(f"✅ Migrated {len(lead_docs)} leads.")
            
    # 3. Migrate Sales Pipeline
    sales_csv = os.path.join(DATA_DIR, "Sales_Pipeline.csv")
    if os.path.exists(sales_csv):
        print("Migrating sales pipeline...")
        df = pd.read_csv(sales_csv)
        for _, row in df.iterrows():
            lead_id = str(row.get("lead_id", ""))
            if not lead_id: continue
            
            update = {
                "crm.stage": str(row.get("deal_stage", "")),
                "crm.deal_value": float(row.get("close_value", 0)) if pd.notna(row.get("close_value")) else 0,
                "crm.close_date": str(row.get("expected_close", ""))
            }
            
            await leads_collection.update_one(
                {"lead_id": lead_id, "company_id": str(company_id)},
                {"$set": update}
            )
        print("✅ Sales Pipeline merged into Leads collection.")

    print("🎉 Migration Complete!")

if __name__ == "__main__":
    asyncio.run(migrate_data())
