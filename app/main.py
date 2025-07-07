from fastapi import FastAPI
from app.api.auth_routes import router as auth_routes
from app.api.research_routes import router as research_routes
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.auth.middleware import AuthMiddleware
from app.db.mongo import connect_to_mongo, close_mongo_connection, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)
app.include_router(auth_routes)
app.include_router(research_routes)