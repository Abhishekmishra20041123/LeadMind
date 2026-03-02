"""Email Strategy Nodes

LangGraph workflow for email crafting.
"""

import json
from typing import Dict, Any
from langgraph.graph import StateGraph, END

def create_email_strategy_graph(llm, prompt_templates):
    """Create email strategy workflow"""
    workflow = StateGraph(Dict[str, Any])
    
    workflow.add_node("prepare_data", prepare_data)
    workflow.add_node("generate_email", lambda x: generate_email(x, llm, prompt_templates))
    
    workflow.add_edge("prepare_data", "generate_email")
    workflow.add_edge("generate_email", END)
    
    workflow.set_entry_point("prepare_data")
    return workflow.compile()

def prepare_data(state):
    """Clean and validate data for single lead"""
    print("\n=== prepare_data Step (Email Strategy) ===")
    
    lead = state.get("lead", {})
    if not lead:
        return {**state, "status": "error", "error": "No lead data provided"}
    
    intent_score = state.get("intent_score", 0.0)
    
    return {
        **state,
        "status": "data_prepared"
    }

def generate_email(state, llm=None, prompt_templates=None):
    """Generate email using LLM for single lead"""
    print("\n=== generate_email Step ===")
    
    if not llm or not prompt_templates:
        return {**state, "status": "error", "error": "Missing LLM or prompts"}
    
    lead_json = json.dumps(state.get("lead", {}), indent=2)
    intent_signals = json.dumps(state.get("key_signals", []), indent=2)
    company_info = json.dumps(state.get("company_info", {"product": "Sales Multi-Agent AI", "value_prop": "Automated pipeline orchestration"}), indent=2)
    operator_info = json.dumps(state.get("operator_info", {}), indent=2)
    
    
    try:
        prompt = prompt_templates["craft_email"].format(
            lead=lead_json,
            intent_signals=intent_signals,
            company_info=company_info,
            operator_info=operator_info
        )
        
        response = llm.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse JSON payload specifically
        if response_text.startswith('```'):
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end != 0:
                response_text = response_text[start:end]
                
        email = json.loads(response_text)
        
        return {
            **state,
            "subject": email.get("subject", ""),
            "personalization_factors": email.get("personalization_factors", []),
            "email_preview": email.get("email_preview", ""),
            "status": "completed"
        }
        
    except Exception as e:
        print(f"Error parsing response: {str(e)}")
        return {
            **state, 
            "status": "error", 
            "error": str(e),
            "subject": "Error drafting email",
            "personalization_factors": ["Error"],
            "email_preview": "Failed to generate email."
        }
