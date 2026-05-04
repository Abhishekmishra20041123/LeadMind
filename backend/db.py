import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("mongodb", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "SalesAgent")

client = AsyncIOMotorClient(MONGO_URL)
database = client.get_database(DB_NAME)

companies_collection = database.get_collection("companies")
batches_collection = database.get_collection("batches")
leads_collection = database.get_collection("leads")
pipeline_collection = database.get_collection("pipeline")
email_logs_collection = database.get_collection("email_logs")
agent_activity_collection = database.get_collection("agent_activity")
followup_queue_collection = database.get_collection("followup_queue")
email_opens_collection = database.get_collection("email_opens")     # summary: open_count, first/last timestamps
email_events_collection = database.get_collection("email_events")   # individual open/click events (IP, UA, etc.)
email_templates_collection = database.get_collection("email_templates")  # saved email layout templates
pipeline_stages_collection = database.get_collection("pipeline_stages")   # kanban board stage config per company

# ── Phase 2: Drip Campaigns & A/B Testing ──────────────────────────────────────
campaigns_collection            = database.get_collection("campaigns")             # drip campaign definitions + steps
campaign_enrollments_collection = database.get_collection("campaign_enrollments")  # per-lead progress through a campaign
ab_tests_collection             = database.get_collection("ab_tests")              # A/B test variants + per-variant metrics
segments_collection             = database.get_collection("segments")              # lead segmentation rules

# ── Phase 6: Tasks, AI Chatbot & Multi-Channel Outreach ─────────────────────────
tasks_collection            = database.get_collection("tasks")              # task management per lead/user
chat_sessions_collection    = database.get_collection("chat_sessions")      # chatbot visitor sessions
chat_messages_collection    = database.get_collection("chat_messages")      # individual chatbot messages
channel_settings_collection = database.get_collection("channel_settings")   # Twilio / channel config per company
outreach_queue_collection   = database.get_collection("outreach_queue")      # AI-drafted outreach pending approval

# ── Phase 3: Live Behavioral Tracking SDK ───────────────────────────────────────
api_keys_collection             = database.get_collection("api_keys")              # company SDK API keys
tracking_events_collection      = database.get_collection("tracking_events")       # raw visitor events (enriched v2)
visitor_sessions_collection     = database.get_collection("visitor_sessions")      # one doc per visitor — live aggregate stats

async def create_indexes():
    import pymongo
    print("Creating MongoDB indexes...")
    try:
        # companies
        await companies_collection.create_index("email", unique=True)
        
        # batches
        await batches_collection.create_index([("batch_id", pymongo.ASCENDING)], unique=True)
        await batches_collection.create_index("company_id")
        
        # leads
        await leads_collection.create_index(
            [("lead_id", pymongo.ASCENDING), ("batch_id", pymongo.ASCENDING)], 
            unique=True
        )
        await leads_collection.create_index("company_id")
        await leads_collection.create_index([("intel.intent_score", pymongo.DESCENDING)])
        await leads_collection.create_index([
            ("profile.name", pymongo.TEXT),
            ("profile.company", pymongo.TEXT),
            ("profile.title", pymongo.TEXT)
        ])
        await leads_collection.create_index("status")
        await leads_collection.create_index("crm.next_followup")
        await leads_collection.create_index("pipeline_stage")   # Phase 1: Kanban board queries
        
        # pipeline
        await pipeline_collection.create_index("company_id")
        await pipeline_collection.create_index("deal_stage")
        
        # email_logs
        await email_logs_collection.create_index("company_id")
        await email_logs_collection.create_index("lead_id")
        
        # agent_activity
        await agent_activity_collection.create_index([("company_id", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)])
        await agent_activity_collection.create_index("batch_id")
        await agent_activity_collection.create_index("lead_id")
        
        # followup_queue
        await followup_queue_collection.create_index([("status", pymongo.ASCENDING), ("scheduled_at", pymongo.ASCENDING)])
        await followup_queue_collection.create_index("company_id")
        await followup_queue_collection.create_index("lead_id")
        
        # email_opens (summary layer — one doc per sent email)
        await email_opens_collection.create_index("token", unique=True)
        await email_opens_collection.create_index([("lead_id", pymongo.ASCENDING), ("company_id", pymongo.ASCENDING)])
        
        # email_events (per-event layer — one doc per open/click event)
        await email_events_collection.create_index("token")
        await email_events_collection.create_index([("lead_id", pymongo.ASCENDING), ("company_id", pymongo.ASCENDING)])
        await email_events_collection.create_index("event_type")
        await email_events_collection.create_index("timestamp")
        
        # pipeline_stages (one doc per company — their kanban stage config)
        await pipeline_stages_collection.create_index("company_id", unique=True)

        # ── Phase 2: Campaigns ────────────────────────────────────────────────────
        await campaigns_collection.create_index("company_id")
        await campaigns_collection.create_index("status")

        # campaign_enrollments — critical compound index for the campaign engine poll
        await campaign_enrollments_collection.create_index([
            ("campaign_id", pymongo.ASCENDING),
            ("status",      pymongo.ASCENDING),
            ("next_step_at",pymongo.ASCENDING),
        ])
        await campaign_enrollments_collection.create_index("company_id")
        await campaign_enrollments_collection.create_index("lead_id")

        # ab_tests
        await ab_tests_collection.create_index("company_id")
        await ab_tests_collection.create_index("status")

        # ── Phase 3: Live Tracking SDK ────────────────────────────────────────────
        await api_keys_collection.create_index("key", unique=True)
        await api_keys_collection.create_index("company_id")
        await api_keys_collection.create_index("is_active")

        await tracking_events_collection.create_index([
            ("company_id",  pymongo.ASCENDING),
            ("timestamp",   pymongo.DESCENDING),
        ])
        await tracking_events_collection.create_index("visitor_id")
        await tracking_events_collection.create_index("api_key")
        await tracking_events_collection.create_index("event_type")
        await tracking_events_collection.create_index("page_type")
        await tracking_events_collection.create_index("utm_source")
        await tracking_events_collection.create_index(
            "timestamp", expireAfterSeconds=7_776_000
        )

        await visitor_sessions_collection.create_index(
            [("company_id", pymongo.ASCENDING), ("visitor_id", pymongo.ASCENDING)],
            unique=True
        )
        await visitor_sessions_collection.create_index("company_id")
        await visitor_sessions_collection.create_index([("last_seen", pymongo.DESCENDING)])
        await visitor_sessions_collection.create_index([("engagement_score", pymongo.DESCENDING)])
        await visitor_sessions_collection.create_index("is_lead")
        await visitor_sessions_collection.create_index("identified_email")

        # ── Phase 6: Tasks, Chat & Multi-Channel ──────────────────────────────────
        await tasks_collection.create_index([("company_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)])
        await tasks_collection.create_index([("company_id", pymongo.ASCENDING), ("due_date", pymongo.ASCENDING)])
        await tasks_collection.create_index("assigned_to")
        await tasks_collection.create_index("lead_id")

        await chat_sessions_collection.create_index("session_id", unique=True)
        await chat_sessions_collection.create_index("company_id")
        await chat_sessions_collection.create_index([("company_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])

        await chat_messages_collection.create_index([("session_id", pymongo.ASCENDING), ("timestamp", pymongo.ASCENDING)])

        await channel_settings_collection.create_index("company_id", unique=True)

        await outreach_queue_collection.create_index([("company_id", pymongo.ASCENDING), ("channel", pymongo.ASCENDING), ("status", pymongo.ASCENDING)])
        await outreach_queue_collection.create_index([("company_id", pymongo.ASCENDING), ("intent_score", pymongo.DESCENDING)])
        await outreach_queue_collection.create_index("lead_id")

        print("MongoDB indexes created.")
    except Exception as e:
        print(f"CRITICAL WARNING: MongoDB index creation failed: {e}")
        print("The server will continue to start, but performance or unique constraints may be affected.")

