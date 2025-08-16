import datetime
from typing import List, Literal, Optional
from bson import ObjectId
from pydantic import BaseModel, Field, PyObject

def now_utc() -> datetime.datetime:
    return datetime.datetime.utcnow()
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
RoleLiteral = Literal["system", "user", "assistant", "tool"]

class MessageModel(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    session_id: PyObjectId
    role: RoleLiteral
    content: str
    created_at: datetime.datetime = Field(default_factory=now_utc)

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True

class CreateMessageRequest(BaseModel):
    session_id: PyObjectId
    content: str

class ChatSessionModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    title: str = "New Chat"
    created_at: datetime.datetime = Field(default_factory=now_utc)
    updated_at: datetime.datetime = Field(default_factory=now_utc)
    messages_count: int = 0
    user_id: PyObjectId 
    class Config:
        allow_population_by_field_name = True
        populate_by_name = True 
        json_encoders = {ObjectId: str}

class CreateChatRequest(BaseModel):
    title: Optional[str] = None

class CreateChatResponse(BaseModel):
    session_id: str
    title: str

class StreamChatRequest(BaseModel):
    session_id: str = Field(..., description="Existing chat session id")
    prompt: str = Field(..., description="User prompt")
    model: str = Field(default="llama-3.1-70b-versatile")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    system_prompt: Optional[str] = Field(default=None)
