import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("mongodb")

client = AsyncIOMotorClient(MONGO_URL)
database = client.get_database("SalesAgent")
companies_collection = database.get_collection("companies")
