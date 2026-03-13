import asyncio
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock dependencies before importing router
class MockCollection:
    async def find_one(self, *args, **kwargs): return None
    async def update_one(self, *args, **kwargs): return None
    async def insert_one(self, *args, **kwargs): return None

# Mocking modules that might cause import errors or side effects
import types
mock_db = types.ModuleType("db")
mock_db.leads_collection = MockCollection()
mock_db.email_logs_collection = MockCollection()
mock_db.agent_activity_collection = MockCollection()
mock_db.email_opens_collection = MockCollection()
mock_db.email_events_collection = MockCollection()
mock_db.email_templates_collection = MockCollection()
mock_db.companies_collection = MockCollection()
mock_db.followup_queue_collection = MockCollection()
sys.modules["db"] = mock_db

mock_deps = types.ModuleType("dependencies")
mock_deps.get_current_user = lambda: {"company_id": "mock_company"}
sys.modules["dependencies"] = mock_deps

mock_sender = types.ModuleType("services.email_sender")
class MockEmailService:
    @staticmethod
    async def send_email(company_id, to_address, subject, html_content, tracking_token):
        print(f"\n--- SENT HTML ---\n{html_content[:500]}\n...")
        return html_content
mock_sender.EmailService = MockEmailService
sys.modules["services.email_sender"] = mock_sender

# Mock api.templates
mock_tpl = types.ModuleType("api.templates")
mock_tpl.render_blocks_to_html = lambda blocks, gs: "<html><body>{{personalized_message}}</body></html>"
sys.modules["api.templates"] = mock_tpl

from api.leads import bulk_approve_leads, render_template

async def test_bulk_logic():
    print("Testing bulk sending logic unification...")
    
    # Mock lead doc
    lead_doc = {
        "lead_id": "test_lead",
        "profile": {"name": "Jordan Page", "company": "Abbott-Henson"},
        "contact": {"email": "jordan@example.com"},
        "intel": {
            "email": {
                "subject": "Quick question about Abbott-Henson's growth",
                "preview": "<p>Hi Jordan,</p><p>We noticed Abbott-Henson's presence on our site...</p>"
            }
        },
        "crm": {"email_sent": False}
    }
    
    # Mock user
    user = {"company_id": "test_company"}
    
    # Mock leads_collection
    async def mock_find_one(query):
        return lead_doc
    mock_db.leads_collection.find_one = mock_find_one
    
    # Mock companies_collection
    async def mock_find_company(query):
        return {"company_name": "My Company", "email": "me@example.com"}
    mock_db.companies_collection.find_one = mock_find_company

    # 1. Test WITH template
    print("\n--- CASE 1: With Template ---")
    payload = {
        "lead_ids": ["test_lead"],
        "template_id": "65f1a2b3c4d5e6f7a8b9c0d1"
    }
    
    # Mock template doc
    async def mock_find_tpl(query):
        return {"_id": "65f1a2b3c4d5e6f7a8b9c0d1", "name": "Modern Blue", "blocks": [{"type": "ai_body"}]}
    mock_db.email_templates_collection.find_one = mock_find_tpl
    
    # Mock render_blocks_to_html to return a full skeleton
    mock_tpl.render_blocks_to_html = lambda blocks, gs: "<html><head></head><body>{rows}</body></html>".replace("{rows}", "<div>{{personalized_message}}</div>")

    sent_emails = []
    async def mock_send_email(company_id, to_address, subject, html_content, tracking_token):
        sent_emails.append(html_content)
        return html_content
    mock_sender.EmailService.send_email = mock_send_email

    await bulk_approve_leads(payload, user)
    
    final_html = sent_emails[0]
    print(f"Final HTML Length: {len(final_html)}")
    
    # Check for double wrapping
    html_count = final_html.lower().count("<html>")
    body_count = final_html.lower().count("<body>")
    
    print(f"<html> count: {html_count}")
    print(f"<body> count: {body_count}")
    
    assert html_count == 1, "Should only have one <html> tag"
    assert body_count == 1, "Should only have one <body> tag"
    print("SUCCESS: Single-wrapped HTML verified.")

if __name__ == "__main__":
    asyncio.run(test_bulk_logic())
