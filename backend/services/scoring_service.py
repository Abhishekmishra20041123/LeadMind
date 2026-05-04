import logging
from datetime import datetime, timezone
from db import leads_collection, agent_activity_collection

logger = logging.getLogger(__name__)

class ScoringService:
    @staticmethod
    async def update_intensity_score(lead_id: str, company_id: str, signal_type: str, weight: int, description: str):
        """
        Updates the lead's intent score and logs the behavioral signal.
        Now triggers Agent 2 (AI) for a full context-aware re-evaluation.
        """
        logger.info(f"[Scoring] Signal: {signal_type} for Lead: {lead_id} (Weight: {weight})")

        # 1. Record the signal in the Lead document (intel.key_signals)
        signal_entry = {
            "signal": description,
            "strength": "High" if weight >= 10 else "Medium",
            "timestamp": datetime.now(timezone.utc),
            "type": signal_type
        }

        await leads_collection.update_one(
            {"lead_id": lead_id, "company_id": company_id},
            {
                "$push": {
                    "intel.key_signals": {
                        "$each": [signal_entry],
                        "$slice": -30, # keep last 30 signals
                        "$position": 0 # newest first
                    }
                }
            }
        )

        # 2. Trigger Agent 2 (AI Re-evaluation) in background
        # We pass the work to Agent 2 to calculate the NEW score based on ALL history
        try:
            from services.agent_runner import rerun_intent_agent_for_lead
            import asyncio
            # We use create_task to avoid blocking the current request (e.g. tracking redirect)
            asyncio.create_task(rerun_intent_agent_for_lead(lead_id, company_id))
            logger.info(f"[Scoring] Agent 2 re-evaluation triggered for {lead_id}")
        except Exception as e:
            logger.error(f"[Scoring] Failed to trigger Agent 2: {e}")

        return True
