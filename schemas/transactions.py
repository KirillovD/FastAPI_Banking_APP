from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, ConfigDict
from schwifty import IBAN
from schwifty.exceptions import SchwiftyException
from enums import TransactionCategory, TransactionStatus, OperationType, PaymentType


class TransactionBase(BaseModel):
    sender_account_id : int | None
    sender_iban : str | None
    recipient_iban : str | None
    recipient_name : str
    amount : Decimal
    description : str | None = None

class TransferDataInput(TransactionBase):

    @field_validator("recipient_iban")
    @classmethod
    def validate_iban(cls, value : str):
        clean_value = value.replace(" ", "").upper()

        try:
            IBAN(clean_value)
        except SchwiftyException:
            raise ValueError("Recipient account IBAN is incorrect")

        return clean_value


class TransactionResponse(TransactionBase):
    id : int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionCreateRecord(TransactionBase):
    recipient_account_id : int | None
    status: TransactionStatus
    created_at: datetime
    operation_type: OperationType
    category : TransactionCategory
    transaction_metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class CashOperation(BaseModel):
    amount: Decimal = Field(gt=0, description="Amount must be greater than zero")


class CashOperationsResponse(BaseModel):
    id : int
    balance : Decimal

    model_config = ConfigDict(from_attributes=True)



class PaymentTerminalData(BaseModel):
    transaction_id: str
    merchant_name: str
    card_number: str
    payment_type: PaymentType


class CardPaymentCreate(BaseModel):
    description: str
    amount: Decimal
    terminal_data : PaymentTerminalData
    created_at: datetime

    pin_block: str | None = None
    cvv: str | None = None


class CardPaymentResponse(BaseModel):
    transaction_id: int
    status: TransactionStatus
    amount: Decimal
    message: str
