from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from schwifty import IBAN
from schwifty.exceptions import SchwiftyException

from money import PositiveMoney

from enums import (
    OperationType,
    PaymentType,
    TransactionCategory,
    TransactionClassificationSource,
    TransactionStatus,
)


class TransferDataInput(BaseModel):
    recipient_iban: str
    recipient_name: str = Field(min_length=1, max_length=101)
    amount: PositiveMoney
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
    classification_source: TransactionClassificationSource = (
        TransactionClassificationSource.SYSTEM
    )


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
    classification_source: TransactionClassificationSource

    model_config = ConfigDict(from_attributes=True)


class CashOperation(BaseModel):
    amount: PositiveMoney


class CashOperationsResponse(BaseModel):
    id: int
    balance: Decimal

    model_config = ConfigDict(from_attributes=True)


class PaymentTerminalData(BaseModel):
    merchant_name: str = Field(min_length=1, max_length=120)
    card_number: str = Field(min_length=12, max_length=19)
    payment_type: PaymentType
    mcc_code: str = Field(pattern=r"^\d{4}$")

    model_config = ConfigDict(extra="forbid")


class CardPaymentCreate(BaseModel):
    amount: PositiveMoney
    terminal_data: PaymentTerminalData
    pin_block: str | None = Field(default=None, pattern=r"^\d{4}$")
    cvv: str | None = Field(default=None, pattern=r"^\d{3,4}$")

    model_config = ConfigDict(extra="forbid")


class CardPaymentResponse(BaseModel):
    transaction_id: int
    status: TransactionStatus
    amount: Decimal
    message: str
