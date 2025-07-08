
from typing import List, Optional
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



class UploadedArticle(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId = Field(...)
    research_id: str = None
    original_text: str = None
    chunks: List[str]= None
    embedding_ids: List[float]

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True

class UploadedArticleCreate(BaseModel):
    user_id: str
    research_id: str
    original_text: str
    chunks: List[str]  # <- change from str to List[str]
    embedding_ids: List[float]
    # title: str
    # content: str
