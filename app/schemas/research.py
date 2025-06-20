from pydantic import BaseModel

class Research(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    tags: str