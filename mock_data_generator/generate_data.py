import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from faker import Faker

from database import SessionLocal
from enums import (
    OperationType,
    TransactionClassificationSource,
    TransactionStatus,
)
from mock_data_generator.patterns import TRANSACTION_PATTERNS
from models import Transaction
from services.categorizer import categorizer


def build_transaction_record(
    *,
    user_account_id: int,
    user_iban: str,
    root_category: str,
    merchant: str,
    mcc_code: str | None,
    amount: Decimal,
    created_at: datetime,
    counterparty_iban: str | None = None,
) -> Transaction:
    is_income = root_category == "Income"

    if is_income:
        classification = categorizer.categorize(
            merchant,
            rule_source=(
                TransactionClassificationSource.DESCRIPTION_RULE
            ),
        )

        return Transaction(
            sender_account_id=None,
            recipient_account_id=user_account_id,
            sender_iban=counterparty_iban,
            recipient_iban=user_iban,
            amount=amount,
            created_at=created_at,
            status=TransactionStatus.SUCCESSFUL,
            operation_type=OperationType.TRANSFER,
            description=merchant,
            category=classification["category"],
            mcc_code=None,
            classification_source=(
                classification["classification_source"]
            ),
        )

    classification = categorizer.categorize(
        merchant,
        mcc_code=mcc_code,
        rule_source=(
            TransactionClassificationSource.MERCHANT_RULE
        ),
    )

    return Transaction(
        sender_account_id=user_account_id,
        recipient_account_id=None,
        sender_iban=user_iban,
        recipient_iban=None,
        amount=amount,
        created_at=created_at,
        status=TransactionStatus.SUCCESSFUL,
        operation_type=OperationType.PAYMENT,
        description=merchant,
        category=classification["category"],
        mcc_code=classification["mcc_code"],
        classification_source=(
            classification["classification_source"]
        ),
    )


def generate_transactions(
    user_account_id: int,
    user_iban: str,
    num_records: int = 10_000,
    *,
    seed: int = 42,
    as_of: datetime | None = None,
):
    db = SessionLocal()
    rng = random.Random(seed)
    fake = Faker("de_DE")
    fake.seed_instance(seed)

    as_of = as_of or datetime.now(timezone.utc)

    choices = []
    weights = []

    for root_category, subcategories in (
        TRANSACTION_PATTERNS.items()
    ):
        for sub_name, data in subcategories.items():
            choices.append(
                {
                    "root_category": root_category,
                    "subcategory": sub_name,
                    "mcc": data["mcc"],
                    "merchants": data["merchants"],
                    "amount_range": data["amount"],
                }
            )
            weights.append(data["weight"])

    transactions_to_insert = []

    try:
        for index in range(num_records):
            chosen = rng.choices(
                choices,
                weights=weights,
                k=1,
            )[0]

            raw_merchant = rng.choice(
                chosen["merchants"]
            )
            merchant = raw_merchant.format(
                city=fake.city(),
                month=fake.month_name(),
            )

            low, high = chosen["amount_range"]
            amount = Decimal(
                f"{rng.uniform(low, high):.2f}"
            )

            created_at = (
                as_of
                - timedelta(
                    days=rng.randint(0, 365)
                )
            )

            record = build_transaction_record(
                user_account_id=user_account_id,
                user_iban=user_iban,
                root_category=chosen["root_category"],
                merchant=merchant,
                mcc_code=chosen["mcc"],
                amount=amount,
                created_at=created_at,
                counterparty_iban=(
                    fake.iban()
                    if chosen["root_category"] == "Income"
                    else None
                ),
            )
            transactions_to_insert.append(record)

            if len(transactions_to_insert) >= 1_000:
                db.add_all(transactions_to_insert)
                db.commit()
                transactions_to_insert = []

        if transactions_to_insert:
            db.add_all(transactions_to_insert)
            db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    return num_records


if __name__ == "__main__":
    generate_transactions(
        user_account_id=1,
        user_iban="DE71100000003258113999",
    )
