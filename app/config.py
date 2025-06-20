from dotenv import load_dotenv
import os

load_dotenv()  # loads .env into os.environ

class Settings:
    # APP_NAME = os.getenv("APP_NAME")
    # APP_ENV = os.getenv("APP_ENV")
    APP_PORT = int(os.getenv("APP_PORT", 8000))
    
    MONGO_URI = os.getenv("MONGO_URI")
    JWT_SECRET = os.getenv("JWT_SECRET")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME",'gyanarthi')
    # ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")

settings = Settings()