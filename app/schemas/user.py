from pydantic import BaseModel, EmailStr

class User(BaseModel):
    id: str
    email: str
    password: str
    created_at: str
    updated_at: str
    refresh_token: str
    name: str

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