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


def _salary(
    account: models.Account,
    amount: str,
    created_at: datetime,
    label: str,
) -> models.Transaction:
    classified = categorizer.categorize(
        label,
        rule_source=(
            TransactionClassificationSource.DESCRIPTION_RULE
        ),
    )

    return models.Transaction(
        recipient_account=account,
        sender_iban=_iban("9000000001"),
        recipient_iban=account.iban,
        amount=Decimal(amount),
        created_at=created_at,
        status=TransactionStatus.SUCCESSFUL,
        operation_type=OperationType.TRANSFER,
        description=label,
        category=classified["category"],
        mcc_code=None,
        classification_source=classified[
            "classification_source"
        ],
    )


def _external_transfer(
    account: models.Account,
    amount: str,
    created_at: datetime,
    description: str,
) -> models.Transaction:
    classified = categorizer.categorize(
        description,
        rule_source=(
            TransactionClassificationSource.DESCRIPTION_RULE
        ),
    )

    return models.Transaction(
        sender_account=account,
        sender_iban=account.iban,
        recipient_iban=_iban("9000000002"),
        amount=Decimal(amount),
        created_at=created_at,
        status=TransactionStatus.SUCCESSFUL,
        operation_type=OperationType.TRANSFER,
        description=description,
        category=classified["category"],
        mcc_code=None,
        classification_source=classified[
            "classification_source"
        ],
    )


def seed_demo_data(
    db: Session,
    *,
    password: str,
    now: datetime | None = None,
) -> bool:
    existing = (
        db.query(models.User)
        .filter(models.User.email == DEMO_EMAIL)
        .first()
    )
    if existing is not None:
        return False

    now = now or datetime.now(timezone.utc)
    today = now.date()

    user = models.User(
        email=DEMO_EMAIL,
        first_name="Demo",
        last_name="User",
        password=utils.hash_password(password),
    )

    checking = models.Account(
        owner=user,
        type=AccountType.CHECKING,
        iban=_iban("0000000101"),
        balance=Decimal("3275.40"),
        limit=Decimal("0.00"),
        created_at=now - timedelta(days=820),
    )
    savings = models.Account(
        owner=user,
        type=AccountType.SAVINGS,
        iban=_iban("0000000102"),
        balance=Decimal("8650.00"),
        limit=Decimal("0.00"),
        created_at=now - timedelta(days=790),
    )
    credit = models.Account(
        owner=user,
        type=AccountType.CREDIT,
        iban=_iban("0000000103"),
        balance=Decimal("-145.00"),
        limit=Decimal("500.00"),
        grace_period_active=False,
        acquired_interest=Decimal("1.37"),
        last_interest_accrual_date=today,
        created_at=now - timedelta(days=720),
    )
    credit.credit_account_metrics = models.CreditAccountMetrics(
        on_time_payments_count=5,
        total_missed_payments_count=1,
        current_days_past_due=0,
        max_days_past_due=4,
        rapid_limit_depletion_count=1,
    )

    card_info = utils.generate_card_info(
        "mastercard",
        DEMO_PIN,
    )
    credit_card = models.Card(
        linked_account=credit,
        owner=user,
        number=card_info["card_number"],
        expiry_date=card_info["expiry_date"],
        CVV_encrypted=card_info[
            "encrypted_security_code"
        ],
        pin_code_hashed=card_info[
            "hashed_pin_code"
        ],
        created_at=now - timedelta(days=720),
    )

    previous_month_end = (
        today.replace(day=1)
        - timedelta(days=1)
    )
    two_months_end = (
        previous_month_end.replace(day=1)
        - timedelta(days=1)
    )
    older_due = (
        two_months_end + relativedelta(months=1)
    ).replace(day=15)
    latest_due = (
        previous_month_end + relativedelta(months=1)
    ).replace(day=15)

    older_statement = models.CreditStatement(
        linked_account=credit,
        period_start=two_months_end.replace(day=1),
        period_end=_month_end(two_months_end),
        due_date=older_due,
        statement_balance=Decimal("310.00"),
        minimum_payment=Decimal("30.00"),
        amount_paid=Decimal("310.00"),
        status=CreditStatementStatus.PAID_IN_FULL,
        minimum_paid_at=datetime.combine(
            older_due - timedelta(days=2),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ),
        paid_in_full_at=datetime.combine(
            older_due - timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ),
        evaluated_at=datetime.combine(
            older_due + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ),
        interest_charged=Decimal("0.00"),
        created_at=now - timedelta(days=60),
    )

    latest_statement = models.CreditStatement(
        linked_account=credit,
        period_start=previous_month_end.replace(day=1),
        period_end=_month_end(previous_month_end),
        due_date=latest_due,
        statement_balance=Decimal("250.00"),
        minimum_payment=Decimal("30.00"),
        amount_paid=Decimal("30.00"),
        status=CreditStatementStatus.MINIMUM_PAID,
        minimum_paid_at=datetime.combine(
            latest_due - timedelta(days=3),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ),
        evaluated_at=datetime.combine(
            latest_due + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ),
        interest_charged=Decimal("8.40"),
        created_at=now - timedelta(days=30),
    )

    db.add(user)
    db.add_all(
        [
            checking,
            savings,
            credit,
            credit_card,
            older_statement,
            latest_statement,
        ]
    )
    db.flush()
