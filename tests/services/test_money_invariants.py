from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import exceptions
import models
from crud import transaction
from enums import AccountType
from money import MAX_MONEY
from schemas.accounts import AccCreate
from schemas.credit import CreditRepaymentInput
from schemas.transactions import CashOperation


@pytest.fixture()
def db_factory(tmp_path):
    database_path = tmp_path / "money-invariants.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    models.Base.metadata.create_all(bind=engine)

    factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    yield factory

    engine.dispose()


def _create_account(
    db_factory,
    *,
    balance: Decimal,
    limit: Decimal = Decimal("0.00"),
):
    with db_factory() as db:
        account = models.Account(
            owner_id=1,
            type=AccountType.CHECKING,
            iban=f"DE{abs(hash((str(balance), str(limit)))) % 10**20:020d}",
            balance=balance,
            limit=limit,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account.id


@pytest.mark.parametrize(
    "schema,value",
    [
        (CashOperation, "0.004"),
        (CashOperation, "0.005"),
        (CashOperation, "0.009"),
        (CreditRepaymentInput, "0.004"),
    ],
)
def test_sub_cent_external_money_is_rejected(schema, value):
    with pytest.raises(ValidationError):
        schema(amount=value)


def test_one_cent_is_accepted():
    assert CashOperation(amount="0.01").amount == Decimal("0.01")


def test_opening_balance_rejects_finite_out_of_range_value():
    with pytest.raises(ValidationError):
        AccCreate(
            type=AccountType.CHECKING,
            balance="1e309",
        )


def test_resulting_balance_cannot_exceed_numeric_contract(
    db_factory,
):
    account_id = _create_account(
        db_factory,
        balance=MAX_MONEY,
    )

    with db_factory() as db:
        account = db.get(models.Account, account_id)

        with pytest.raises(exceptions.MoneyLimitExceeded):
            transaction.deposit_funds(
                account,
                Decimal("0.01"),
                db,
            )

        db.rollback()

    with db_factory() as db:
        account = db.get(models.Account, account_id)
        assert account.balance == MAX_MONEY


def test_stale_second_debit_cannot_overwrite_first_debit(
    db_factory,
):
    account_id = _create_account(
        db_factory,
        balance=Decimal("100.00"),
    )

    first = db_factory()
    second = db_factory()
    try:
        first_account = first.get(models.Account, account_id)
        second_account = second.get(models.Account, account_id)

        assert first_account.balance == Decimal("100.00")
        assert second_account.balance == Decimal("100.00")

        transaction.withdraw_funds(
            first_account,
            Decimal("80.00"),
            first,
            enforce_available_funds=True,
        )
        first.commit()

        with pytest.raises(exceptions.InsufficientFunds):
            transaction.withdraw_funds(
                second_account,
                Decimal("80.00"),
                second,
                enforce_available_funds=True,
            )
        second.rollback()
    finally:
        first.close()
        second.close()

    with db_factory() as db:
        account = db.get(models.Account, account_id)
        assert account.balance == Decimal("20.00")


def test_stale_deposits_accumulate_instead_of_losing_update(
    db_factory,
):
    account_id = _create_account(
        db_factory,
        balance=Decimal("0.00"),
    )

    first = db_factory()
    second = db_factory()
    try:
        first_account = first.get(models.Account, account_id)
        second_account = second.get(models.Account, account_id)

        transaction.deposit_funds(
            first_account,
            Decimal("80.00"),
            first,
        )
        first.commit()

        transaction.deposit_funds(
            second_account,
            Decimal("80.00"),
            second,
        )
        second.commit()
    finally:
        first.close()
        second.close()

    with db_factory() as db:
        account = db.get(models.Account, account_id)
        assert account.balance == Decimal("160.00")


def test_existing_non_finite_balance_cannot_be_spent(
    db_factory,
):
    account_id = _create_account(
        db_factory,
        balance=Decimal("Infinity"),
    )

    with db_factory() as db:
        account = db.get(models.Account, account_id)

        with pytest.raises(exceptions.MoneyLimitExceeded):
            transaction.withdraw_funds(
                account,
                Decimal("1.00"),
                db,
                enforce_available_funds=True,
            )

        db.rollback()
