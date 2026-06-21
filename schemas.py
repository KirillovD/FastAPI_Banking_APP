#this file has schemas to receive information from the users in the app
from typing import Literal

from pydantic import BaseModel, Field, EmailStr

class UserCreate(BaseModel):
    first_name :str = Field(min_length=3, max_length=20, pattern="^[a-zA-Z]+$")
    last_name : str = Field(min_length=3, max_length=20, pattern="^[a-zA-Z]+$")
    email : EmailStr
    password : str = Field(min_length=8, max_length=20, pattern="^[a-zA-Z0-9_-]+$")

class AccCreate(BaseModel):
    acc_type : Literal["Savings", "Checking", "HYSA"]
    acc_balance : float = Field(default=0.0)


class UserResponse(BaseModel):
    user_id : int
    first_name : str
    last_name : str
    email : str
    credit_score : int

    class Config:
        from_attributes = True


class AccResponse(BaseModel):
    acc_id : int
    owner_id : int
    acc_type : str
    acc_balance : int

    class Config:
        from_attributes = True

