from datetime import datetime,timezone
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field
class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic validation."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class User(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    email: str
    password: str
    name: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}

class UserRequestModel(BaseModel):
    email: str
    password: str
    created_at: str
    updated_at: str
    name: str
    
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str