#this file has schemas to receive information from the users in the app
from datetime import datetime
from schwifty import IBAN
from typing import Literal
from pydantic import BaseModel, Field, EmailStr, field_validator
from schwifty.exceptions import SchwiftyException


class UserCreate(BaseModel):
    first_name :str = Field(min_length=3, max_length=20, pattern="^[a-zA-Z]+$")
    last_name : str = Field(min_length=3, max_length=20, pattern="^[a-zA-Z]+$")
    email : EmailStr
    password : str = Field(min_length=8, max_length=20, pattern="^[a-zA-Z0-9_-]+$")

class AccCreate(BaseModel):
    acc_type : Literal["Savings", "Checking"]
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
    iban : str
    acc_type : str
    acc_balance : int
    overdraft_limit : int = Field(default=0)

    class Config:
        from_attributes = True

class TransferMoney(BaseModel):
    recipient_iban : str
    recipient_name : str
    source_account_id : int
    transfer_amount : float= Field(gt=0)

    @field_validator("recipient_iban")
    @classmethod
    def validate_iban(cls, value : str):
        clean_value = value.replace(" ", "").upper()

        try:
            IBAN(clean_value)
        except SchwiftyException:
            raise ValueError("Recipient account IBAN is incorrect")

        return clean_value



class TransactionResponse(BaseModel):
    transaction_id : int
    sender_account_id : int | None
    sender_iban : str | None
    recipient_iban : str | None
    transfer_amount : float
    created_at : datetime
    status : str
    operation_type : str
    description : str | None = None
    category : str | None

    class Config:
        from_attributes = True

class CashOperation(BaseModel):
    acc_id : int
    amount : float= Field(gt=0)
    