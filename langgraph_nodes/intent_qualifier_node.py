from typing import Dict, Any, List
from langgraph.graph import StateGraph
import json

# ── Pipeline Value Config ──────────────────────────────────────────────────────
TITLE_BASE_VALUES = {
    "c-suite": 15_000,   # CEO, CTO, CFO, COO, CMO, CRO, CISO, CPO
    "vp":      10_000,   # VP, Vice President
    "director": 7_000,   # Director, Head of
    "manager":  4_000,   # Manager, Lead, Senior, Principal
    "default":  2_000,   # All others / unknown
}

INTENT_MULTIPLIERS = {
    (80, 101): 1.5,
    (60,  80): 1.2,
    (40,  60): 1.0,
    ( 0,  40): 0.5,
}

STAGE_MULTIPLIERS = {
    "converted":   1.0,
    "negotiation": 0.8,
    "proposal":    0.6,
    "qualified":   0.4,
    "prospect":    0.2,
}


def _title_base_value(title: str) -> int:
    t = title.lower()
    if any(k in t for k in ["ceo", "cto", "cfo", "coo", "cmo", "cro", "ciso", "cpo", "chief"]):
        return TITLE_BASE_VALUES["c-suite"]
    if any(k in t for k in ["vp", "vice president"]):
        return TITLE_BASE_VALUES["vp"]
    if any(k in t for k in ["director", "head of", "head,"]):
        return TITLE_BASE_VALUES["director"]
    if any(k in t for k in ["manager", "lead", "senior", "principal"]):
        return TITLE_BASE_VALUES["manager"]
    return TITLE_BASE_VALUES["default"]


def _intent_multiplier(score: float) -> float:
    for (low, high), mult in INTENT_MULTIPLIERS.items():
        if low <= score < high:
            return mult
    return 0.5


def _stage_multiplier(stage: str) -> float:
    return STAGE_MULTIPLIERS.get((stage or "prospect").lower().strip(), 0.2)


# ── Node functions ─────────────────────────────────────────────────────────────

def prepare_data(state):
    """Clean and prepare individual lead and email data"""
    print("\n=== prepare_data Step ===")

    lead = state.get("lead", {})
    emails = state.get("email_data", [])

    if not lead:
        return {**state, "status": "error", "error": "No lead data provided"}

    clean_lead = lead.copy()
    clean_lead.update({
        "lead_id": str(lead.get("lead_id", "")),
        "name": str(lead.get("name", "")),
        "company": str(lead.get("company", "")),
        "title": str(lead.get("title", "")),
        "industry": str(lead.get("industry", "Unknown")),
        "visits": int(lead.get("visits", 0) if pd.notna(lead.get("visits")) else 0) if 'pd' in globals() else int(lead.get("visits", 0)),
        "time_on_site": float(lead.get("time_on_site", 0.0)),
        "pages_per_visit": float(lead.get("pages_per_visit", 0.0)),
        "converted": bool(lead.get("converted", False)),
        "crm_stage": str(lead.get("crm_stage", "") or lead.get("stage", "") or "prospect"),
        "page_link": lead.get("page_link", [])
    })

    lead_id = clean_lead["lead_id"]
    clean_emails = []

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
    return {**state, "status": "patterns_analyzed"}


def generate_insights(state, llm=None, prompt_templates=None):
    """Generate precise intent scoring using LLM for a single lead"""
    print("\n=== generating Intent Insights ===")

    if not llm or not prompt_templates:
        return {**state, "status": "error", "error": "Missing LLM or prompts"}

    try:
        lead_json = json.dumps(state.get("lead", {}), indent=2)
        email_json = json.dumps(state.get("email_history", []), indent=2)

        prompt = prompt_templates["generate_insights"]
        prompt = prompt.replace("{lead_data}", lead_json)
        prompt = prompt.replace("{email_data}", email_json)

        response = llm.generate_content(prompt)
        response_text = response.text.strip()

        try:
            result = json.loads(response_text)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Warning: Failed to parse Intent Insights JSON. Response was: {response_text[:100]}...")
            return {
                **state,
                "status": "completed", # allow pipeline to continue with fallbacks
                "intent_score": 0.0,
                "key_signals": [{"signal": "AI parsing error", "strength": "Low"}],
                "intent_recommendation": {"urgency": "Low"}
            }

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


def calculate_deal_value(state):
    """
    Deterministically estimate crm.deal_value from title + intent_score + crm stage.
    Runs as the final node after generate_insights so intent_score is in state.
    Result is written to MongoDB via batch.py's $set block.
    """
    lead  = state.get("lead", {})
    title = str(lead.get("title", "") or "")
    score = float(state.get("intent_score", 0.0))
    stage = str(lead.get("crm_stage", "") or "prospect")

    base   = _title_base_value(title)
    i_mult = _intent_multiplier(score)
    s_mult = _stage_multiplier(stage)

    deal_value = round(base * i_mult * s_mult, 2)
    crm_stage  = stage.lower().strip() if stage else "prospect"

    print(f"  [DealValue] title={title!r} score={score} stage={stage} → ${deal_value:,.2f}")

    return {
        **state,
        "deal_value": deal_value,
        "crm_stage":  crm_stage,
        "status": "completed",
    }


# ── Graph ──────────────────────────────────────────────────────────────────────

def create_intent_qualifier_graph(llm, prompt_templates):
    """Create the LangGraph workflow for individual intent qualification"""

    def generate_insights_with_llm(state):
        return generate_insights(state, llm, prompt_templates)

    workflow = StateGraph(state_schema=Dict[str, Any])

    workflow.add_node("prepare_data",         prepare_data)
    workflow.add_node("analyze_patterns",     analyze_patterns)
    workflow.add_node("generate_insights",    generate_insights_with_llm)
    workflow.add_node("calculate_deal_value", calculate_deal_value)

    workflow.add_edge("prepare_data",      "analyze_patterns")
    workflow.add_edge("analyze_patterns",  "generate_insights")
    workflow.add_edge("generate_insights", "calculate_deal_value")

    workflow.set_entry_point("prepare_data")
    workflow.set_finish_point("calculate_deal_value")

    return workflow.compile()