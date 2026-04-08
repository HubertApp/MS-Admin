from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.DATABASE_URL)
db = client.admin_db
apis_collection = db.registered_apis