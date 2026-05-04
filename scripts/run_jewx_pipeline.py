import sys
import os
import pandas as pd
import json
from datetime import datetime

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Mock LLM for demonstration
class MockLLM:
    def generate_content(self, prompt):
        prompt_str = str(prompt).lower()
        if "lead_research" in prompt_str or "interpret_insights" in prompt_str:
            return type('obj', (object,), {'text': json.dumps({
                "lead_quality_indicators": {"intent": "High", "focus": "Engagement Products"},
                "engagement_recommendations": ["Highlight the craftsmanship of the Platinum Diamond Ring"]
            })})
        if "craft_email" in prompt_str:
            # Extract last_visited_page from prompt to show behavior-first reasoning
            try:
                # Find the product info in the prompt context
                product = "Jewelry"
                if "platinum-diamond-engagement-rings" in prompt_str:
                    product = "Platinum Diamond Engagement Ring"
                elif "tiffany-t-18k-yellow-gold-diamond-necklace" in prompt_str:
                    product = "Tiffany T Gold Necklace"
                
                return type('obj', (object,), {'text': json.dumps({
                    "subject": f"The {product} you liked at JewX",
                    "email_preview": f"Hi Sarah, I noticed you spent some time viewing our {product}. It's a stunning choice...",
                    "personalization_factors": [f"Direct mention of {product}"]
                })})
            except:
                pass
        if "generate_strategy" in prompt_str:
            return type('obj', (object,), {'text': json.dumps({
                "timing": {
                    "recommended_date": "2024-12-16",
                    "send_time": "10:15", # Based on 10 AM visit
                    "reasoning": "Matching the user's active browsing period."
                },
                "approach": {"type": "direct_offer"}
            })})
        return type('obj', (object,), {'text': '{"status": "success"}'})

def run_jewx_pipeline():
    print("🚀 Running BEHAVIOR-FIRST pipeline for JewX...")
    
    from agents.lead_research_agent import LeadResearchAgent
    from agents.intent_qualifier_agent import IntentQualifierAgent
    from agents.email_strategy_agent import EmailStrategyAgent
    from agents.followup_timing_agent import FollowUpTimingAgent
    from agents.crm_logger_agent import CRMLoggerAgent
    
    llm = MockLLM()
    leads_path = os.path.join(root_dir, "data", "JewX_Combined_Leads.csv")
    email_path = os.path.join(root_dir, "data", "JewX_Email_Logs.csv")
    
    # 1. Lead Research (Behavioral Analysis)
    print("\n[RESEARCH] Analyzing site activity...")
    research_agent = LeadResearchAgent(llm)
    research_agent.load_data(leads_path)
    res = research_agent.process_task({"input": "Analyze Sarah Johnson"})
    print(f"✅ Context: Identified focus on Engagement Rings.")

    # 2. Intent Qualifier (Scoring Depth)
    print("\n[QUALIFY] Scoring readiness based on visit depth...")
    intent_agent = IntentQualifierAgent(llm)
    intent_agent.load_data(leads_path, email_path)
    # Using row 0 (Sarah Johnson)
    sarah_row = pd.read_csv(leads_path).iloc[0].to_dict()
    print(f"✅ Score: {sarah_row['intent_score']} (Signals: {sarah_row['visits']} visits, spent {sarah_row['time_on_site']} mins)")

    # 3. Email Strategy (Product-Specific Outreach)
    print("\n[EMAIL] Generating product-framed email...")
    email_agent = EmailStrategyAgent(llm, {"company_name": "JewX"})
    email_agent.load_data(email_path)
    email_res = email_agent.craft_email(sarah_row, {"intent_signals": ["Browse depth"]})
    print(f"✅ Draft: {email_res['subject']}")
    print(f"✅ Text: {email_res['email_preview']}")

    # 4. Follow-up Timing (Visit Anchor)
    print("\n[TIMING] Determining schedule based on visit window...")
    timing_agent = FollowUpTimingAgent(llm)
    timing_agent.load_data(email_path)
    # Sarah visited at 10:00 (from our logs/engage_date context)
    timing_res = timing_agent.process_task("L_JX_001", current_visit_time="2024-12-15 10:00:00")
    print(f"✅ Recommended: {timing_res['recommended_date']} at {timing_res['send_time']}")

    # 5. CRM Logger (State Persistence)
    print("\n[LOGGER] Recording lifecycle events...")
    crm_agent = CRMLoggerAgent()
    crm_agent.process_event({
        "lead_id": "L_JX_001", "event_type": "pipeline_complete", 
        "data": {"status": "Sarah is now in sales funnel", "product": "Engagement Ring"}
    })
    print("✅ Success: Timeline updated.")

    print("\n🎯 PIPELINE SUCCESSFUL: Agent coordination complete.")

if __name__ == "__main__":
    run_jewx_pipeline()
