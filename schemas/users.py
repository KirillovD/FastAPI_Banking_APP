from pydantic import BaseModel, Field, EmailStr


class UserCreate(BaseModel):
    first_name :str = Field(min_length=3, max_length=20, pattern="^[a-zA-Z]+$")
    last_name : str = Field(min_length=3, max_length=20, pattern="^[a-zA-Z]+$")
    email : EmailStr
    password : str = Field(min_length=8, max_length=20, pattern="^[a-zA-Z0-9_-]+$")


class UserResponse(BaseModel):
    id : int
    first_name : str
    last_name : str
    email : str
    credit_score : int

    class Config:
        from_attributes = True
