from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v, info=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class AIFeedback(BaseModel):
    grammar_score: Optional[float] = None
    clarity_score: Optional[float] = None
    factual_correctness: Optional[float] = None
    suggestions: Optional[str] = None

class WrittenArticle(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId = Field(...)
    research_id: str = None
    title: str = Field(...)
    content: str = Field(...)
    ai_feedback: Optional[AIFeedback] = None

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True

class WrittenArticleCreate(BaseModel):
    user_id: str
    title: str
    content: str

    class Config:
        schema_extra = {
            "example": {
                "user_id": "64a2bf3b9f1b3f0123456789",
                "title": "Sample Written Article Title",
                "content": "This is the content of the written article."
            }
        }
