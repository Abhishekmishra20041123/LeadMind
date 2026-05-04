from pymongo import MongoClient
from bson import ObjectId
import os

# Using the URL from .env
MONGO_URL = "mongodb+srv://23102180_db_user:9tuXTOlIZyGMHHA2@cluster0.5fmzadc.mongodb.net/SalesAgent?retryWrites=true&w=majority"
DB_NAME = "SalesAgent"

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

def migrate_collection(name):
    coll = db[name]
    count = 0
    # Find documents where company_id is a string
    cursor = coll.find({"company_id": {"$type": "string"}})
    for doc in cursor:
        try:
            # Standardizing to ObjectId for CRM collections
            coll.update_one(
                {"_id": doc["_id"]},
                {"$set": {"company_id": ObjectId(doc["company_id"])}}
            )
            count += 1
        except Exception as e:
            pass # Skip if not a valid ObjectId string
    print(f"Migrated {count} documents in '{name}' to ObjectId company_id")

if __name__ == "__main__":
    collections = [
        "leads", "batches", "agent_activity", "email_logs", 
        "email_opens", "email_events", "followup_queue", "tasks", "outreach_queue"
    ]
    for c in collections:
        migrate_collection(c)
