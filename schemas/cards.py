from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateCard(BaseModel):
    pin_code: str = Field(pattern=r"^\d{4}$")
    type: Literal["mastercard", "maestro"] = "mastercard"


class CardResponse(BaseModel):
    id: int
    number: str
    expiry_date: datetime
    linked_acc_id: int

    model_config = ConfigDict(from_attributes=True)


class CardSecretResponse(BaseModel):
    cvv: str


class PayDownBalanceInput(BaseModel):
    card_id: int
    amount: Decimal
