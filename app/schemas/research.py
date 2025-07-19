from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field
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
class Research(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    title: str
    description: str

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True 
        json_encoders = {ObjectId: str}

class ResearchCreate(BaseModel):
    title: str
    description: str
    pdf_url: str

class GenerateArticle(BaseModel):
    query: str
    research_id: str