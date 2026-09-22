from datetime import datetime, timezone

from sqlalchemy.orm import Session

import exceptions
import models
from crud import transaction
from enums import AccountType, OperationType, TransactionCategory, TransactionStatus
from schemas import transactions


CASH_ACCOUNT_TYPES = {
    AccountType.CHECKING,
    AccountType.SAVINGS,
}


def _ensure_cash_account(account: models.Account):
    if account.type not in CASH_ACCOUNT_TYPES:
        raise exceptions.AccountOperationNotAllowed(
            detail=(
                "Cash operations are only available for "
                "checking and savings accounts"
            )
        )


def deposit_cash(
    amount_data: transactions.CashOperation,
    valid_acc: models.Account,
    db: Session,
):
    _ensure_cash_account(valid_acc)

    try:
        account_after_deposit = transaction.deposit_funds(
            valid_acc,
            amount_data.amount,
            db,
        )

        transaction_data = transactions.TransactionCreateRecord(
            recipient_account_id=valid_acc.id,
            recipient_iban=valid_acc.iban,
            amount=amount_data.amount,
            created_at=datetime.now(timezone.utc),
            status=TransactionStatus.SUCCESSFUL,
            operation_type=OperationType.DEPOSIT,
            description="Cash deposit",
            category=TransactionCategory.OTHER,
        )
        transaction.create_transaction_record(
            transaction_data,
            db,
        )

        db.commit()
        db.refresh(account_after_deposit)

        return account_after_deposit

    except Exception:
        db.rollback()
        raise


def withdraw_cash(
    amount_data: transactions.CashOperation,
    valid_acc: models.Account,
    db: Session,
):
    _ensure_cash_account(valid_acc)

    try:
        account_after_withdraw = transaction.withdraw_funds(
            valid_acc,
            amount_data.amount,
            db,
            enforce_available_funds=True,
        )

        transaction_data = transactions.TransactionCreateRecord(
            sender_account_id=valid_acc.id,
            sender_iban=valid_acc.iban,
            amount=amount_data.amount,
            created_at=datetime.now(timezone.utc),
            status=TransactionStatus.SUCCESSFUL,
            operation_type=OperationType.WITHDRAWAL,
            description="Cash withdrawal",
            category=TransactionCategory.OTHER,
        )
        transaction.create_transaction_record(
            transaction_data,
            db,
        )

        db.commit()
        db.refresh(account_after_withdraw)

        return account_after_withdraw

    except Exception:
        db.rollback()
        raise
