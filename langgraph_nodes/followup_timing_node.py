"""Follow-up Timing Nodes

LangGraph workflow for follow-up timing optimization.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any
from langgraph.graph import StateGraph, END

def create_followup_timing_graph(llm, prompt_templates):
    """Create follow-up timing workflow"""
    workflow = StateGraph(Dict[str, Any])
    
    workflow.add_node("prepare_data", prepare_data)
    workflow.add_node("generate_strategy", lambda x: generate_strategy(x, llm, prompt_templates))
    
    workflow.add_edge("prepare_data", "generate_strategy")
    workflow.add_edge("generate_strategy", END)
    
    workflow.set_entry_point("prepare_data")
    return workflow.compile()

def prepare_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and prepare email data for analysis."""
    print("\n=== prepare_data Step (Followup Timing) ===")
    
    lead = state.get("lead", {})
    email_history = state.get("email_history", [])
    
    if not lead:
        return {**state, "status": "error", "error": "No lead data provided"}
        
    return {
        **state,
        "status": "data_prepared"
    }

def generate_strategy(state: Dict[str, Any], llm=None, prompt_templates=None) -> Dict[str, Any]:
    """Generate follow-up strategy using LLM."""
    print("\n=== generate_strategy Step ===")
    
    if not llm or not prompt_templates:
        return {**state, "status": "error", "error": "Missing LLM or prompts"}
        
    lead = state.get("lead", {})
    email_history = state.get("email_history", [])
    
    # Calculate some basic context for the LLM
    total_emails = len(email_history)
    replies = sum(1 for e in email_history if e.get("replied"))
    response_rate = (replies / total_emails) if total_emails > 0 else 0
    
    context = {
        "lead_id": lead.get("lead_id"),
        "industry": lead.get("industry"),
        "current_visit_time": state.get("current_visit_time"),
        "total_past_emails": total_emails,
        "historical_replies": replies,
        "response_rate": response_rate,
        "recent_email_engagement": email_history[-3:] if email_history else []
    }
    
    try:
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        # Use manual string replacement instead of .format() to avoid
        # Python misinterpreting JSON curly braces as format placeholders
        context_json = json.dumps(context, indent=2)
        prompt = prompt_templates["generate_strategy"]
        prompt = prompt.replace("{current_date}", current_date)
        prompt = prompt.replace("{context}", context_json)
        
        response = llm.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse JSON
        if response_text.startswith('```'):
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end != 0:
                response_text = response_text[start:end]
                
        strategy = json.loads(response_text)
        
        fallback_date = (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d")
        timing_dict = strategy.get("timing", {})
        if "2025" in str(timing_dict.get("recommended_date", "")):
            timing_dict["recommended_date"] = fallback_date
        
        return {
            **state,
            "timing": timing_dict,
            "approach": strategy.get("approach", {}),
            "engagement_prediction": strategy.get("engagement_prediction", {}),
            "status": "completed"
        }
        
    except Exception as e:
        print(f"Error parsing response: {str(e)}")
        fallback_date = (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d")
        return {
            **state,
            "status": "error",
            "error": str(e),
            "timing": {
                "recommended_date": fallback_date,
                "send_time": "10:00",
                "optimal_time_window": "Error fallback",
                "reasoning": str(e)
            },
            "approach": {
                "type": "soft_nudge",
                "urgency": 50,
                "reasoning": "Fallback",
                "content_suggestions": ["Manual outreach recommended"]
            },
            "engagement_prediction": {
                "response_probability": 0.1,
                "expected_delay": 48
            }
        }