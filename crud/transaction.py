from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
from crud import accounts
from schemas import transactions


def withdraw_funds(account: models.Account, amount: Decimal):
    account.balance -= amount
    return account


def deposit_funds(account: models.Account, amount: Decimal):
    account.balance += amount
    return account


def get_transactions_history(user_id: int, db: Session):
    user_accounts = accounts.get_all_user_accounts(user_id, db)
    account_ids = [account.id for account in user_accounts]

    if not account_ids:
        return []

    return (
        db.query(models.Transaction)
        .filter(
            or_(
                models.Transaction.sender_account_id.in_(account_ids),
                models.Transaction.recipient_account_id.in_(account_ids),
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
