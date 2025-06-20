from fastapi import APIRouter, Depends, Response, HTTPException
from datetime import datetime
from app.auth.hashing import hash_password, verify_password
from app.auth.jwt import create_access_token, create_refresh_token
from app.schemas.user import User, UserCreate, UserLogin
import uuid
from app.db.mongo import get_db

router = APIRouter(prefix="/auth")

@router.post("/register")
async def register(payload: UserCreate, res: Response,db = Depends(get_db)):
    data = payload.model_dump()
    existing = await db["users"].find_one({"email": data["email"]})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    now = datetime.utcnow().isoformat()
    user_id = str(uuid.uuid4())
    refresh = create_refresh_token({"id": user_id, "email": data["email"]})

    user_data = {
        "id": user_id,
        "email": data["email"],
        "name": data.get("name", ""),
        "password": hash_password(data["password"]),
        "created_at": now,
        "updated_at": now,
        "refresh_token": refresh
    }

    await db["users"].insert_one(user_data)

    access = create_access_token({"id": user_id, "email": data["email"]})
    res.set_cookie("access_token", access, httponly=True)
    res.set_cookie("refresh_token", refresh, httponly=True)

    return {"message": "User created", "user": {"id": user_id, "email": data["email"]}}

@router.post("/login")
async def login(payload: UserLogin, res: Response, db = Depends(get_db)):
    data = payload.model_dump()
    user = await db["users"].find_one({"email": data["email"]})
    if not user or not verify_password(data["password"], user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    refresh = create_refresh_token({"id": user["id"], "email": user["email"]})
    await db["users"].update_one({"id": user["id"]}, {"$set": {"refresh_token": refresh}})
    access = create_access_token({"id": user["id"], "email": user["email"]})
    res.set_cookie("access_token", access, httponly=True)
    res.set_cookie("refresh_token", refresh, httponly=True)
    return {"message": "Logged in"}
