from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    credit_score: int

    model_config = ConfigDict(from_attributes=True)
