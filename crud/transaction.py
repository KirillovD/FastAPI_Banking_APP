from decimal import Decimal

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

import exceptions
import models
from crud import accounts
from money import MAX_MONEY, MIN_MONEY, normalize_money
from schemas import transactions


def _refresh_balance(account: models.Account, db: Session):
    db.expire(account, ["balance"])
    db.refresh(account, attribute_names=["balance"])
    return account


def _current_balance_and_limit(
    account_id: int,
    db: Session,
) -> tuple[Decimal, Decimal] | None:
    row = db.execute(
        select(
            models.Account.balance,
            models.Account.limit,
        ).where(models.Account.id == account_id)
    ).one_or_none()

    if row is None:
        return None

    return Decimal(row.balance), Decimal(row.limit)


def withdraw_funds(
    account: models.Account,
    amount: Decimal,
    db: Session,
    *,
    enforce_available_funds: bool = False,
):
    amount = normalize_money(amount, positive=True)

    conditions = [
        models.Account.id == account.id,
        models.Account.balance
        >= MIN_MONEY + amount,
        models.Account.balance
        <= MAX_MONEY + amount,
    ]

    if enforce_available_funds:
        conditions.append(
            models.Account.balance + models.Account.limit
            >= amount
        )

    result = db.execute(
        update(models.Account)
        .where(*conditions)
        .values(
            balance=models.Account.balance - amount
        )
        .execution_options(synchronize_session=False)
    )

    if result.rowcount != 1:
        current = _current_balance_and_limit(
            account.id,
            db,
        )

        if current is None:
            raise exceptions.AccountNotFound()

        balance, limit = current

        if (
            enforce_available_funds
            and balance.is_finite()
            and limit.is_finite()
            and balance + limit < amount
        ):
            raise exceptions.InsufficientFunds()

        raise exceptions.MoneyLimitExceeded()

    return _refresh_balance(account, db)


def deposit_funds(
    account: models.Account,
    amount: Decimal,
    db: Session,
):
    amount = normalize_money(amount, positive=True)

    result = db.execute(
        update(models.Account)
        .where(
            models.Account.id == account.id,
            models.Account.balance
            <= MAX_MONEY - amount,
            models.Account.balance
            >= MIN_MONEY - amount,
        )
        .values(
            balance=models.Account.balance + amount
        )
        .execution_options(synchronize_session=False)
    )

    if result.rowcount != 1:
        current = _current_balance_and_limit(
            account.id,
            db,
        )

        if current is None:
            raise exceptions.AccountNotFound()

        raise exceptions.MoneyLimitExceeded()

    return _refresh_balance(account, db)


def get_transactions_history(user_id: int, db: Session):
    user_accounts = accounts.get_all_user_accounts(user_id, db)
    account_ids = [account.id for account in user_accounts]

    if not account_ids:
        return []

    return (
        db.query(models.Transaction)
        .filter(
            or_(
                models.Transaction.sender_account_id.in_(
                    account_ids
                ),
                models.Transaction.recipient_account_id.in_(
                    account_ids
                ),
            )
        )
        .order_by(
            models.Transaction.created_at.desc(),
            models.Transaction.id.desc(),
        )
        .all()
    )


def create_transaction_record(
    transaction_data: transactions.TransactionCreateRecord,
    db: Session,
):
    new_transaction_record = models.Transaction(
        **transaction_data.model_dump()
    )
    db.add(new_transaction_record)
    return new_transaction_record
