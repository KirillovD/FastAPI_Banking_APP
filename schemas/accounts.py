from decimal import Decimal
from pydantic import BaseModel, Field
from enums import AccountType


class AccCreate(BaseModel):
    type : AccountType
    balance : Decimal = Field(default=0.0)


class AccResponse(BaseModel):
    id : int
    owner_id : int
    iban : str
    type : str
    balance : Decimal
    overdraft_limit : int = Field(default=0)

    class Config:
        from_attributes = True
