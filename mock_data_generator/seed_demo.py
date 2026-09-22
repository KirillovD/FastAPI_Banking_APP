"""Deterministic synthetic data setup for the public portfolio demo."""

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from schwifty import IBAN
from sqlalchemy.orm import Session

import models
import utils
from enums import (
    AccountType,
    CreditStatementStatus,
    OperationType,
    TransactionClassificationSource,
    TransactionStatus,
)
from services.categorizer import categorizer


DEMO_EMAIL = "demo@example.com"
DEMO_PIN = "1234"


def _iban(account_number: str) -> str:
    return str(
        IBAN.generate(
            "DE",
            "10000000",
            account_number,
        )
    )


def _month_end(value: date) -> date:
    return value.replace(
        day=monthrange(value.year, value.month)[1]
    )


def _card_payment(
    account: models.Account,
    merchant: str,
    mcc: str,
    amount: str,
    created_at: datetime,
) -> models.Transaction:
    classified = categorizer.categorize(
        merchant,
        mcc_code=mcc,
        rule_source=(
            TransactionClassificationSource.MERCHANT_RULE
        ),
    )

    return models.Transaction(
        sender_account=account,
        sender_iban=account.iban,
        amount=Decimal(amount),
        created_at=created_at,
        status=TransactionStatus.SUCCESSFUL,
        operation_type=OperationType.PAYMENT,
        description=merchant,
        category=classified["category"],
        mcc_code=classified["mcc_code"],
        classification_source=classified[
            "classification_source"
        ],
    )
