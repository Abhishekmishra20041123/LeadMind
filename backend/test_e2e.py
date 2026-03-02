import asyncio
import httpx
import json
import os

BASE_URL = "http://localhost:8000/api"

async def run_e2e():
    print("--- E2E TEST: Registration to Email Generation ---")
    async with httpx.AsyncClient() as client:
        # 1. Signup
        print("\n1. Signing up...")
        signup_payload = {
            "company_name": "E2E Test Corp",
            "company_website_url": "https://e2e.test.com",
            "country": "United States",
            "contact_person_name": "E2E Tester",
            "email": "e2e@test.com",
            "phone_number": "123-456-7890",
            "password": "password123"
        }
        res = await client.post(f"{BASE_URL}/auth/signup", json=signup_payload)
        
        # If already exists, we login instead.
        if res.status_code == 400 and "already exists" in res.text:
            print("User already exists. Logging in...")
            res = await client.post(f"{BASE_URL}/auth/signin", json={"email": "e2e@test.com", "password": "password123"})
            
        assert res.status_code == 200, f"Auth failed: {res.text}"
        token = res.json()["access_token"]
        print("✅ Authenticated successfully")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Upload CSVs
        print("\n2. Uploading 5 Data Sources...")
        
        files_config = {
            "agent_mapping": ("Agent_Mapping.csv", "text/csv"),
            "crm_pipeline": ("CRM_Pipeline.csv", "text/csv"),
            "email_logs": ("Email_Logs.csv", "text/csv"),
            "leads_data": ("Leads_Data.csv", "text/csv"),
            "sales_pipeline": ("Sales_Pipeline.csv", "text/csv")
        }
        
        files = {}
        file_handles = []
        for key, (filename, content_type) in files_config.items():
            path = f"../data/{filename}"
            if not os.path.exists(path):
                print(f"❌ '{path}' does not exist.")
                return
            
            f = open(path, "rb")
            file_handles.append(f)
            files[key] = (filename, f, content_type)

        res = await client.post(
            f"{BASE_URL}/batch/upload", 
            files=files,
            data={"start_index": 0, "end_index": 10},
            headers=headers
        )
        
        # Cleanup file handles
        for f in file_handles:
            f.close()
        
        assert res.status_code == 200, f"Upload failed: {res.text}"
        batch_data = res.json()
        print(f"✅ Upload succeeded. Batch ID: {batch_data['batch_id']}")
        batch_id = batch_data["batch_id"]
        
        # 3. Process first 10 leads (simulate the execute button on UI)
        print("\n3. Waiting for Background Engine to Parse...")
        
        # Poll for completion
        for _ in range(30):
            res = await client.get(f"{BASE_URL}/batch/{batch_id}/progress", headers=headers)
            progress = res.json()
            print(f"Progress: {progress['processed_leads']}/{progress['total_leads']} ({progress['status']})")
            if progress['status'] == 'Completed':
                break
            await asyncio.sleep(2)
            
        # 4. Fetch leads from ledger
        print("\n4. Fetching Leads Ledger...")
        res = await client.get(f"{BASE_URL}/leads", headers=headers)
        assert res.status_code == 200, f"Failed to fetch leads: {res.text}"
        leads = res.json()["leads"]
        print(f"✅ Retrieved {len(leads)} leads from DB")
        
        if not leads:
            print("❌ No leads found after processing!")
            return
            
        target_lead = leads[0]["lead_id"]
        
        # 5. Fetch Intel Details
        print(f"\n5. Fetching Intel for Lead {target_lead}...")
        res = await client.get(f"{BASE_URL}/leads/{target_lead}", headers=headers)
        assert res.status_code == 200, f"Failed to fetch lead: {res.text}"
        lead_data = res.json()
        print(f"✅ Intel Retrieved: Name={lead_data['profile']['name']}, Score={lead_data['intel'].get('intent_score', 'N/A')}")
        
        # 6. Approve & Send Email
        print(f"\n6. Approving Email for Lead {target_lead}...")
        res = await client.post(f"{BASE_URL}/leads/{target_lead}/approve-email", headers=headers)
        if res.status_code == 200:
            print(f"✅ Email queued for dispatch: {res.json()}")
        else:
            print(f"⚠️ Email approval returned: {res.text}")

        # 7. Check Dashboard Pipeline
        print("\n7. Fetching Dashboard stats...")
        res = await client.get(f"{BASE_URL}/dashboard/stats", headers=headers)
        if res.status_code == 200:
            print(f"✅ Dashboard Data: {res.json()}")
            
        print("\n🚀 E2E WORKFLOW COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_e2e())
