from typing import Dict, Any
from langgraph.graph import StateGraph
import json

def prepare_data(state):
    """Prepare and clean individual lead data"""
    print("\n=== prepare_data Step ===")
    
    lead = state.get("lead", {})
    if not lead:
        return {**state, "status": "error", "error": "No lead data provided"}
    
    clean_lead = {
        "lead_id": str(lead.get("lead_id", "")),
        "name": str(lead.get("name", "")),
        "visits": int(lead.get("visits", 0) if pd.notna(lead.get("visits")) else 0) if 'pd' in globals() else int(lead.get("visits", 0)),
        "time_on_site": float(lead.get("time_on_site", 0.0)),
        "pages_per_visit": float(lead.get("pages_per_visit", 0.0)),
        "converted": bool(lead.get("converted", False)),
        "lead_source": str(lead.get("lead_source", "")),
        "region": str(lead.get("region", "")),
        "company": str(lead.get("company", "")),
        "title": str(lead.get("title", "")),
        "industry": str(lead.get("industry", "Unknown")),
        "company_size": str(lead.get("company_size", "Unknown")),
        "engagement_score": float(lead.get("engagement_score", 0.0))
    }
    
    return {
        **state,
        "lead": clean_lead,
        "status": "data_prepared"
    }

def analyze_patterns(state):
    """Pass-through enrichment for single lead"""
    print("\n=== analyze_patterns Step ===")
    
    lead = state.get("lead", {})
    if not lead:
        return {**state, "status": "error", "error": "No lead data provided for enrichment"}
        
    return {
        **state,
        "status": "patterns_analyzed"
    }

def generate_insights(state, llm=None, prompt_templates=None):
    """Generate insights from a single lead using LLM."""
    print("\n=== Generating Lead Research Insights ===")
    
    if not llm or not prompt_templates:
        return {
            **state,
            "status": "error",
            "error": "Missing LLM or prompts",
            "quality_indicators": [],
            "recommendation": {}
        }
    
    try:
        lead_data_json = json.dumps(state.get("lead", {}), indent=2)
        
        # Use manual string replacement to avoid JSON curly braces breaking .format()
        prompt = prompt_templates["generate_insights"]
        prompt = prompt.replace("{lead_data}", lead_data_json)
        
        response = llm.generate_content(prompt)
        response_text = response.text.strip()
        
        # Strip markdown syntax if LLM returns it
        if response_text.startswith("```"):
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end != 0:
                response_text = response_text[start:end]
            
        result = json.loads(response_text)
        
        return {
            **state,
            "status": "completed",
            "quality_indicators": result.get("quality_indicators", []),
            "recommendation": result.get("recommendation", {})
        }
        
    except Exception as e:
        print(f"Error in generate_insights: {str(e)}")
        return {
            **state,
            "status": "error",
            "error": f"Error generating insights: {str(e)}",
            "quality_indicators": [
                {
                    "metric": "Analysis Error",
                    "value": "Low",
                    "reasoning": str(e)
                }
            ],
            "recommendation": {
                "segment": "Unknown",
                "strategy": "Requires manual review due to analysis error",
                "expected_impact": 0.0
            }
        }

def create_lead_research_graph(llm, prompt_templates):
    """Create the LangGraph workflow for individual lead research"""
    
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