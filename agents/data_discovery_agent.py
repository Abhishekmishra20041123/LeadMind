import json
import pandas as pd
from typing import Dict, List, Any

class DataDiscoveryAgent:
    def __init__(self, llm):
        self.llm = llm
        
    def analyze_data_sources(self, files: List[str]) -> Dict[str, Any]:
        """
        Analyzes multiple CSV files to discover schema roles and business context.
        """
        all_headers = {}
        data_samples = {}
        
        for file in files:
            df = pd.read_csv(file, nrows=5)
            all_headers[file] = df.columns.tolist()
            data_samples[file] = df.to_dict(orient='records')
            
        prompt = f"""
You are the DataDiscovery Agent. Your job is to analyze the provided CSV headers and samples from a company's data and map them to our internal semantic requirements.

DATA SOURCES:
{json.dumps({"headers": all_headers, "samples": data_samples}, indent=2)}

INTERNAL SEMANTIC ROLES:
- IDENTITY: Columns that identify a user (email, name, user_id, lead_id).
- BEHAVIOR: Columns tracking activity (visits, pages_viewed, time_on_site, session_duration).
- CONTENT: Columns showing what they looked at (url, product_name, page_link, breadcrumbs).
- SALES: Columns about historical deals (close_value, stage, deal_date).

YOUR TASKS:
1. IDENTIFY BUSINESS TYPE: Determine if this is E-commerce (Product), Service (Teaching/Consulting), SaaS, or Wearables.
2. MAP COLUMNS: Find which columns in the provided files represent the core metrics needed for research and outreach.
3. SUFFICIENCY CHECK: Determine if there is enough data to build a behavioral profile and draft a personalized outreach.

OUTPUT FORMAT:
Return strictly valid JSON:
{{
    "business_context": {{
        "company_name": "Unknown",
        "industry": "e.g. E-commerce",
        "description": "Brief description based on data"
    }},
    "files_roles": {{
        "primary_leads_file": "filename.csv (The main table with users/sessions)",
        "email_history_file": "filename.csv (Optional table with past emails)"
    }},
    "schema_mapping": {{
        "lead_id": "column_name",
        "identity_fields": ["col1", "col2"],
        "behavioral_fields": {{
            "visits": "column_name",
            "depth": "column_name (pages/time)",
            "content_links": "column_name",
            "time_on_site": "column_name"
        }},
        "sales_fields": {{
            "value": "column_name",
            "stage": "column_name"
        }}
    }},
    "is_sufficient": true,
    "missing_critical_data": [],
    "reasoning": "Why you mapped it this way"
}}
"""
        print("\n=== Discovering Schema & Context ===")
        response = self.llm.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean markdown if present
        if response_text.startswith("```"):
            start = response_text.find("\n") + 1
            end = response_text.rfind("```")
            if end > start:
                response_text = response_text[start:end].strip()
                if response_text.startswith("json\n"):
                    response_text = response_text[5:].strip()
                    
        return json.loads(response_text)
