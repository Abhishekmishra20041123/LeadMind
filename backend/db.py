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
    
    print("MongoDB indexes created.")
