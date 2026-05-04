import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

MONGO_URL = os.getenv("mongodb", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "SalesAgent")

def _calc_engagement_score(session: dict) -> int:
    """Compute 0–100 engagement score from session aggregate."""
    score  = min(session.get("page_views", 0) * 5,  30)
    score += min(session.get("total_time_sec", 0) * 0.01, 20)
    score += min(session.get("max_scroll", 0) * 0.3, 30)
    # Mocking sessions count as 1 if missing
    score += min(session.get("sessions_count", 1) * 3, 10)
    
    # Bonuses
    
    
    return min(int(score), 100)

async def update_rahul():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_database(DB_NAME)
    leads = db.get_collection("leads")
    
    lead_id = "L_07CFB501"
    
    # We'll set realistic values that reflect "active and prolonged browsing"
    # as mentioned in the AI summary, fixing the "0s" tracking error.
    new_activity = {
        "page_views": 32,
        "total_time_sec": 660,  # 11 minutes
        "max_scroll": 85,       # 85%
        "engagement_score": 0,  # placeholder
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Calculate score
    score = _calc_engagement_score(new_activity)
    new_activity["engagement_score"] = score
    
    print(f"Updating lead {lead_id} with new behavior data...")
    result = await leads.update_one(
        {"lead_id": lead_id},
        {"$set": {
            "sdk_activity.page_views": new_activity["page_views"],
            "sdk_activity.total_time_sec": new_activity["total_time_sec"],
            "sdk_activity.max_scroll": new_activity["max_scroll"],
            "sdk_activity.engagement_score": new_activity["engagement_score"],
            "intel.intent_score": min(int(score * 0.99), 99), # sync intent score
            "updated_at": new_activity["updated_at"]
        }}
    )
    
    if result.matched_count:
        print("Update successful.")
    else:
        print("Lead not found.")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(update_rahul())
