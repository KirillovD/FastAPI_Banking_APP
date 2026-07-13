from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CreateCard(BaseModel):
    pin_code : int
    type : str = "mastercard"

class CardResponse(BaseModel):
    id : int
    number : str
    expiry_date : datetime
    linked_acc_id : int

    model_config = ConfigDict(from_attributes=True)


class CardSecretResponse(BaseModel):
    cvv : str


class AllCardsDashboard(BaseModel):
    cards : list[CardResponse]
