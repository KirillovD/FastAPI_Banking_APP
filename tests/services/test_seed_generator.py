from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from enums import (
    OperationType,
    TransactionCategory,
    TransactionClassificationSource,
    TransactionStatus,
)
from mock_data_generator.generate_data import (
    build_transaction_record,
)
from schemas.transactions import TransactionResponse


def test_card_seed_record_uses_current_payment_contract():
    record = build_transaction_record(
        user_account_id=1,
        user_iban="DE71100000003258113999",
        root_category="Food & Dining",
        merchant="REWE FIL. München",
        mcc_code="5411",
        amount=Decimal("42.50"),
        created_at=datetime(
            2026,
            9,
            22,
            12,
            tzinfo=timezone.utc,
        ),
    )

    assert record.amount == Decimal("42.50")
    assert record.status == TransactionStatus.SUCCESSFUL
    assert record.operation_type == OperationType.PAYMENT
    assert record.category == TransactionCategory.GROCERIES
    assert record.mcc_code == "5411"
    assert (
        record.classification_source
        == TransactionClassificationSource.MCC
    )


def test_income_seed_record_uses_transfer_without_fake_mcc():
    record = build_transaction_record(
        user_account_id=1,
        user_iban="DE71100000003258113999",
        root_category="Income",
        merchant="Gehalt September",
        mcc_code=None,
        amount=Decimal("3200.00"),
        created_at=datetime(
            2026,
            9,
            22,
            12,
            tzinfo=timezone.utc,
        ),
        counterparty_iban="DE02120300000000202051",
    )

    assert record.operation_type == OperationType.TRANSFER
    assert record.category == TransactionCategory.SALARY
    assert record.mcc_code is None
    assert record.sender_account_id is None
    assert record.recipient_account_id == 1


def test_seed_record_serializes_with_current_transaction_response():
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    with factory() as db:
        record = build_transaction_record(
            user_account_id=1,
            user_iban="DE71100000003258113999",
            root_category="Shopping",
            merchant="Amazon.de",
            mcc_code="5399",
            amount=Decimal("19.99"),
            created_at=datetime(
                2026,
                9,
                22,
                12,
                tzinfo=timezone.utc,
            ),
        )
        db.add(record)
        db.flush()

        response = TransactionResponse.model_validate(
            record
        )

        assert response.id == record.id
        assert response.amount == Decimal("19.99")
        assert (
            response.category
            == TransactionCategory.E_COMMERCE
        )

    engine.dispose()
