import sys
import os
import pandas as pd
import json

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from agents.data_discovery_agent import DataDiscoveryAgent
from agents.lead_research_agent import LeadResearchAgent
from agents.email_strategy_agent import EmailStrategyAgent

class MockLLM:
    def generate_content(self, prompt):
        p = str(prompt).lower()
        
        if "datadiscovery agent" in p:
            # Discovery Logic
            return type('obj', (object,), {'text': json.dumps({
                "business_context": {
                    "company_name": "EduStream",
                    "industry": "E-Learning / Services",
                    "description": "Premium online courses for software engineering."
                },
                "schema_mapping": {
                    "lead_id": "student_id",
                    "behavioral_fields": {
                        "visits": "course_views",
                        "depth": "modules_completed",
                        "content_links": "interested_courses",
                        "time_on_site": "study_minutes"
                    }
                },
                "is_sufficient": True,
                "reasoning": "Detected course-based terminology and student IDs."
            })})
            
        if "specialized sales advisor" in p:
            # Dynamic Email Logic
            return type('obj', (object,), {'text': json.dumps({
                "subject": "Level up your Software Engineering skills",
                "email_preview": "<h3>Advanced System Design</h3><iframe src='https://edustream.io/system-design' width='100%' height='300px'></iframe><p>I noticed you were exploring our System Design modules...</p>",
                "personalization_factors": ["High module completion rate detected"]
            })})
            
        return type('obj', (object,), {'text': '{"status": "ok"}'})

def run_universal_demo():
    print("🌍 STARTING UNIVERSAL WHITE-LABEL DEMO 🌍")
    llm = MockLLM()
    
    # 1. DISCOVERY PHASE
    # Simulate a company (EduStream) uploading a non-standard CSV
    edu_csv = os.path.join(root_dir, "data", "EduStream_Leads.csv")
    edu_data = pd.DataFrame([{
        "student_id": "ST_001",
        "student_name": "Charlie",
        "course_views": 15,
        "study_minutes": 120,
        "modules_completed": 8,
        "interested_courses": "https://edustream.io/system-design,https://edustream.io/python-expert"
    }])
    edu_data.to_csv(edu_csv, index=False)
    
    discovery_agent = DataDiscoveryAgent(llm)
    mapping_res = discovery_agent.analyze_data_sources([edu_csv])
    
    print(f"\n✅ Discovery Complete!")
    print(f"Detected Industry: {mapping_res['business_context']['industry']}")
    print(f"Lead ID Mapped To: {mapping_res['schema_mapping']['lead_id']}")
    
    # 2. DYNAMIC RESEARCH
    research_agent = LeadResearchAgent(llm)
    research_agent.load_data(edu_csv)
    # The agent now uses the discovered mapping!
    
    # 3. DYNAMIC EMAIL (Industry-Agnostic)
    biz_info = {
        "company_name": mapping_res['business_context']['company_name'],
        "business_type": mapping_res['business_context']['industry'],
        "description": mapping_res['business_context']['description'],
        "operator_name": "Thomas Shelby" # Fallback for persona
    }
    email_agent = EmailStrategyAgent(llm, biz_info)
    
    # In universal mode, we might not have historical logs, so we skip load_data
    # or load the current file as logs
    email_agent.email_history = edu_data 
    
    lead_row = edu_data.iloc[0].to_dict()
    
    email_res = email_agent.craft_email(
        lead_row, 
        {"intent": {"signals": ["Completed 8 modules in one sitting"]}},
        mapping=mapping_res['schema_mapping']
    )
    
    print(f"\n✅ Created Dynamic Email for {biz_info['business_type']}!")
    print(f"Subject: {email_res['subject']}")
    print(f"Body: {email_res['email_preview'][:150]}...")

if __name__ == "__main__":
    run_universal_demo()
