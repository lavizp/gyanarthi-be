from fastapi import APIRouter, Depends, Response, HTTPException
from datetime import datetime
from app.auth.hashing import hash_password, verify_password
from app.auth.jwt import create_access_token, create_refresh_token
from app.schemas.refresh_token import RefreshToken
from app.schemas.user import User, UserCreate, UserLogin
from app.db.mongo import get_db
from bson import ObjectId

router = APIRouter(prefix="/auth")

@router.post("/register")
async def register(payload: UserCreate, res: Response,db = Depends(get_db)):
    data = payload.model_dump()
    existing = await db["users"].find_one({"email": data["email"]})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    now = datetime.utcnow().isoformat()
    # user_id = str(uuid.uuid4())

    user_data = User(
        email=data["email"],
        name= data.get("name"),
        password= hash_password(data["password"]),
    )
    print(user_data)
    # print(user_data.model_dump())

    await db["users"].insert_one(user_data.model_dump(by_alias=True))

    refresh = create_refresh_token({"id": str(user_data.id), "email": data["email"]})
    access = create_access_token({"id": str(user_data.id), "email": data["email"]})

    refresh_token = RefreshToken(
        user_id=ObjectId(str(user_data.id)),
        refresh_token=refresh
    )
    await db["refresh_tokens"].insert_one(refresh_token.model_dump(by_alias=True))
    res.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        samesite="none",
        secure=True,
        path="/",
    )
    res.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        samesite="none",
        secure=True,
        path="/",
    )

    return {"message": "User created", "user": {"id": user_data.id, "email": data["email"]}}

@router.post("/login")
async def login(payload: UserLogin, res: Response, db = Depends(get_db)):
    data = payload.model_dump()
    user = await db["users"].find_one({"email": "admin@amdin.com"})
    print(user)
    if not user or not verify_password(data["password"], user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    print("ya pugyo")
    user_id = str(user["_id"]) 
    refresh = create_refresh_token({"id": user_id, "email": user["email"]})
    access = create_access_token({"id": user_id, "email": user["email"]})

    # Update or insert the refresh token
    await db["refresh_tokens"].update_one(
        {"user_id": user["_id"]},
        {"$set": {"refresh_token": refresh}},
        upsert=True
    )
    res.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        samesite="none",
        secure=True,
        path="/",
    )
    res.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        samesite="none",
        secure=True,
        path="/",
    )
    return {"message": "Logged in"}
