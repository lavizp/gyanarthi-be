from fastapi import FastAPI
from app.api.routes import router as api_router
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.routes import router as api_router
from app.auth.middleware import AuthMiddleware
from app.db.mongo import connect_to_mongo, close_mongo_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan)
app.add_middleware(AuthMiddleware)
app.include_router(api_router)