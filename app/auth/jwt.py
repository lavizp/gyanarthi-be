
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.config import settings

SECRET = settings.JWT_SECRET
ALGORITHM = settings.JWT_ALGORITHM

def create_access_token(data: dict, expires_minutes: int = 15):
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(days=7)
    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
