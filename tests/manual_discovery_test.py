import sys
import os
import json
import pandas as pd

# Add project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from agents.data_discovery_agent import DataDiscoveryAgent

class MockLLM:
    def generate_content(self, prompt):
        # Simulate a successful mapping of the boAt CSV
        # This is what we EXPECT the LLM to return if it follows our new instructions
        response = {
            "business_context": {
                "company_name": "boAt",
                "industry": "Electronics / E-commerce",
                "description": "Premium audio and wearable brand"
            },
            "files_roles": {
                "primary_leads_file": "boAt User Behavioral Data - Sheet1.csv",
                "email_history_file": None
            },
            "schema_mapping": {
                "lead_id": "User ID",
                "identity_fields": ["Name", "Email", "Phone Number"],
                "behavioral_fields": {
                    "visits": "No. of Visits",
                    "depth": "Pages Visited",
                    "content_links": "Product Page Link", # Should NOT include Product Name
                    "time_on_site": "Total Time Spent (hrs)"
                },
                "sales_fields": {
                    "value": "MRP (INR)",
                    "stage": "Purchase Made"
                }
            },
            "is_sufficient": True,
            "missing_critical_data": [],
            "reasoning": "Standard mapping for boAt dataset. content_links mapped ONLY to the URL column per instructions."
        }
        class Obj: pass
        res = Obj()
        res.text = json.dumps(response)
        return res

def test_discovery():
    print("Testing DataDiscoveryAgent with boAt CSV...")
    
    csv_path = os.path.join(root_dir, "data", "boAt User Behavioral Data - Sheet1.csv")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found")
        return

    # 1. Test Fallback logic (Manual Mapping)
    print("\n--- Testing Fallback Logic (Internal Guessing) ---")
    agent_fallback = DataDiscoveryAgent(None)
    fallback_res = agent_fallback._make_safe_default([csv_path])
    print(json.dumps(fallback_res, indent=2))
    
    # Verify content_links in fallback
    link_col = fallback_res["schema_mapping"]["behavioral_fields"]["content_links"]
    print(f"\n[Fallback] content_links mapped to: '{link_col}'")
    assert link_col == "Product Page Link", f"Fallback failed to map Product Page Link, got {link_col}"

    # 2. Test LLM Prompting Logic
    print("\n--- Testing LLM Prompt Generation ---")
    mock_llm = MockLLM()
    agent_llm = DataDiscoveryAgent(mock_llm)
    
    # We can't easily see the prompt without modifying the class to return it, 
    # but we can see the result if the LLM "responds" correctly.
    llm_res = agent_llm.analyze_data_sources([csv_path])
    print(json.dumps(llm_res, indent=2))
    
    link_col_llm = llm_res["schema_mapping"]["behavioral_fields"]["content_links"]
    print(f"\n[LLM Mode] content_links mapped to: '{link_col_llm}'")
    
    if isinstance(link_col_llm, list):
        print("FAIL: content_links is a list. It should be a single string for better stability.")
    elif "Product Name" in link_col_llm:
        print("FAIL: content_links included 'Product Name'. Scraper will fail.")
    else:
        print("SUCCESS: content_links correctly mapped to a single URL column.")

if __name__ == "__main__":
    test_discovery()
