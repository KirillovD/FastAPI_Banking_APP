#this file has schemas to receive information from the users in the app
from typing import Literal

from pydantic import BaseModel, Field, EmailStr

class UserCreate(BaseModel):
    first_name :str = Field(min_length=3, max_length=20, pattern="^[a-zA-Z]+$")
    last_name : str = Field(min_length=3, max_length=20, pattern="^[a-zA-Z]+$")
    email : EmailStr
    password : str = Field(min_length=3, max_length=20, pattern="^[a-zA-Z0-9_-]+$")

class AccCreate(BaseModel):
    acc_type : Literal["checking","savings"]
    acc_balance : float=Field(default=0)