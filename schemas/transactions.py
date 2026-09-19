from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from schwifty import IBAN
from schwifty.exceptions import SchwiftyException

from enums import (
    OperationType,
    PaymentType,
    TransactionCategory,
    TransactionStatus,
)


class TransferDataInput(BaseModel):
    recipient_iban: str
    recipient_name: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0)
    description: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")

    @field_validator("recipient_iban")
    @classmethod
    def validate_iban(cls, value: str):
        clean_value = value.replace(" ", "").upper()

        try:
            IBAN(clean_value)
        except SchwiftyException:
            raise ValueError("Recipient account IBAN is incorrect")

        return clean_value


class TransactionCreateRecord(BaseModel):
    sender_account_id: int | None = None
    recipient_account_id: int | None = None
    sender_iban: str | None = None
    recipient_iban: str | None = None
    amount: Decimal
    created_at: datetime
    status: TransactionStatus
    operation_type: OperationType
    description: str | None = None
    category: TransactionCategory = TransactionCategory.OTHER
    mcc_code: str | None = None


class TransactionResponse(BaseModel):
    id: int
    sender_account_id: int | None
    recipient_account_id: int | None
    sender_iban: str | None
    recipient_iban: str | None
    amount: Decimal
    created_at: datetime
    status: TransactionStatus
    operation_type: OperationType
    description: str | None
    category: TransactionCategory
    mcc_code: str | None

    model_config = ConfigDict(from_attributes=True)


class CashOperation(BaseModel):
    amount: Decimal = Field(gt=0, description="Amount must be greater than zero")


class CashOperationsResponse(BaseModel):
    id: int
    balance: Decimal

    model_config = ConfigDict(from_attributes=True)


class PaymentTerminalData(BaseModel):
    transaction_id: str
    merchant_name: str
    card_number: str
    payment_type: PaymentType


class CardPaymentCreate(BaseModel):
    description: str
    amount: Decimal
    terminal_data: PaymentTerminalData
    created_at: datetime

    pin_block: str | None = None
    cvv: str | None = None


class CardPaymentResponse(BaseModel):
    transaction_id: int
    status: TransactionStatus
    amount: Decimal
    message: str
