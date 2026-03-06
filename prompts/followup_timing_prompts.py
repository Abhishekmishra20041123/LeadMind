"""Prompts for the Follow-up Timing Agent."""

followup_timing_prompts = {
    "generate_strategy": """You are an AI assistant helping optimize follow-up timing for sales leads.

Given this data:
{context}

Generate a follow-up strategy. Return as JSON:
{
    "timing": {
        "recommended_date": "FUTURE_DATE_AFTER_{current_date}",
        "send_time": "10:00",
        "optimal_time_window": "Tuesday 2-4 PM",
        "reasoning": "Based on patterns"
    },
    "approach": {
        "type": "soft_nudge",
        "urgency": 25,
        "reasoning": "Low urgency",
        "content_suggestions": [
            "Quick check-in",
            "Share update"
        ]
    },
    "engagement_prediction": {
        "response_probability": 0.35,
        "expected_delay": 24
    }
}

Rules:
1. recommended_date MUST be a future date strictly after {current_date}
2. urgency must match type:
   - soft_nudge: 0-30
   - value_add: 31-70 
   - social_proof: 71-100
3. Return only valid JSON"""
}

