from typing import Dict, Any, List
from langgraph.graph import StateGraph
import json

def prepare_data(state):
    """Clean and prepare individual lead and email data"""
    print("\n=== prepare_data Step ===")
    
    lead = state.get("lead", {})
    emails = state.get("email_data", [])
    
    if not lead:
        return {**state, "status": "error", "error": "No lead data provided"}
        
    clean_lead = {
        "lead_id": str(lead.get("lead_id", "")),
        "name": str(lead.get("name", "")),
        "company": str(lead.get("company", "")),
        "title": str(lead.get("title", "")),
        "industry": str(lead.get("industry", "Unknown")),
        "visits": int(lead.get("visits", 0) if pd.notna(lead.get("visits")) else 0) if 'pd' in globals() else int(lead.get("visits", 0)),
        "time_on_site": float(lead.get("time_on_site", 0.0)),
        "pages_per_visit": float(lead.get("pages_per_visit", 0.0)),
        "converted": bool(lead.get("converted", False))
    }
    
    lead_id = clean_lead["lead_id"]
    clean_emails = []
    
    # Filter emails specifically for this lead
    for email in emails:
        if email.get("lead_id") == lead_id:
            clean_emails.append({
                "email_id": str(email.get("email_id", "")),
                "opened": bool(email.get("opened", False)),
                "replied": bool(email.get("replied", False)) or bool(email.get("reply_status", "") == "replied"),
                "engagement_score": float(email.get("engagement_score", 0.0))
            })
            
    return {
        **state,
        "lead": clean_lead,
        "email_history": clean_emails,
        "status": "data_prepared"
    }

def analyze_patterns(state):
    """Pass-through enrichment for single lead"""
    return {
        **state,
        "status": "patterns_analyzed"
    }

def generate_insights(state, llm=None, prompt_templates=None):
    """Generate precise intent scoring using LLM for a single lead"""
    print("\n=== generating Intent Insights ===")
    
    if not llm or not prompt_templates:
        return {**state, "status": "error", "error": "Missing LLM or prompts"}
    
    try:
        lead_json = json.dumps(state.get("lead", {}), indent=2)
        email_json = json.dumps(state.get("email_history", []), indent=2)
        
        # Use manual string replacement to avoid JSON curly braces breaking .format()
        prompt = prompt_templates["generate_insights"]
        prompt = prompt.replace("{lead_data}", lead_json)
        prompt = prompt.replace("{email_data}", email_json)
        
        response = llm.generate_content(prompt)
        response_text = response.text.strip()
        
        if response_text.startswith("```"):
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end != 0:
                response_text = response_text[start:end]
                
        result = json.loads(response_text)
        
        return {
            **state,
            "status": "completed",
            "intent_score": result.get("intent_score", 0.0),
            "key_signals": result.get("key_signals", []),
            "intent_recommendation": result.get("recommendation", {})
        }
        
    except Exception as e:
        print(f"Error generating intent insights: {str(e)}")
        return {
            **state,
            "status": "error",
            "error": str(e),
            "intent_score": 0.0,
            "key_signals": [{"signal": "Analysis Failed", "strength": "Low"}],
            "intent_recommendation": {"next_best_action": "Manual review", "urgency": "Low"}
        }

def create_intent_qualifier_graph(llm, prompt_templates):
    """Create the LangGraph workflow for individual intent qualification"""
    
    def generate_insights_with_llm(state):
        return generate_insights(state, llm, prompt_templates)
    
    workflow = StateGraph(state_schema=Dict[str, Any])
    
    workflow.add_node("prepare_data", prepare_data)
    workflow.add_node("analyze_patterns", analyze_patterns)
    workflow.add_node("generate_insights", generate_insights_with_llm)
    
    workflow.add_edge("prepare_data", "analyze_patterns")
    workflow.add_edge("analyze_patterns", "generate_insights")
    
    workflow.set_entry_point("prepare_data")
    workflow.set_finish_point("generate_insights")
    
    return workflow.compile()