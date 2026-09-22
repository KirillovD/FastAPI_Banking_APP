from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from enums import AccountType
from money import Money


class AccCreate(BaseModel):
    type: Literal[AccountType.CHECKING, AccountType.SAVINGS]
    balance: Money = Decimal("0.00")


class CreditAccCreate(BaseModel):
    type: Literal[AccountType.CREDIT] = AccountType.CREDIT
    balance: Money = Decimal("0.00")


class AccResponse(BaseModel):
    id: int
    owner_id: int
    iban: str
    type: AccountType
    balance: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
