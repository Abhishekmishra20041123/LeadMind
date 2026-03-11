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

async def create_indexes():
    import pymongo
    print("Creating MongoDB indexes...")
    
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
    
    print("MongoDB indexes created.")
