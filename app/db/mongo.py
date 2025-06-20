from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client: AsyncIOMotorClient = None
db = None

async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    print("Connected to MongoDB", db.name)

async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("Closed MongoDB connection")
        
def get_db():
    from app.db.mongo import db
    if db is None:
        raise RuntimeError("❌ DB not initialized")
    return db