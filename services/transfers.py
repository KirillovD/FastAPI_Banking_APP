from datetime import datetime, timezone

from sqlalchemy.orm import Session

import exceptions
import models
from crud import accounts, transaction
from enums import (
    AccountType,
    OperationType,
    TransactionClassificationSource,
    TransactionStatus,
)
from schemas import transactions
from services import credit_score, payments
from services.categorizer import categorizer


TRANSFER_ACCOUNT_TYPES = {
    AccountType.CHECKING,
    AccountType.SAVINGS,
}


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def _ensure_transfer_account(account: models.Account):
    if account.type not in TRANSFER_ACCOUNT_TYPES:
        raise exceptions.AccountOperationNotAllowed(
            detail=(
                "Bank transfers are only available for "
                "checking and savings accounts"
            )
        )


def transfer_money(
    transfer_data: transactions.TransferDataInput,
    valid_source_acc: models.Account,
    db: Session,
):
    _ensure_transfer_account(valid_source_acc)

    recipient_account = accounts.get_acc_by_iban(
        transfer_data.recipient_iban,
        db,
    )

    if not recipient_account:
        raise exceptions.AccountNotFound(
            detail="Recipient account not found"
        )

    _ensure_transfer_account(recipient_account)

    if recipient_account.id == valid_source_acc.id:
        raise exceptions.SelfTransferNotAllowed()

    expected_name = (
        f"{recipient_account.owner.first_name} "
        f"{recipient_account.owner.last_name}"
    )
    if (
        _normalize_name(transfer_data.recipient_name)
        != _normalize_name(expected_name)
    ):
        raise exceptions.UserNotFound(
            detail="Recipient name is wrong or doesn't exist"
        )

    if not payments.is_account_balance_sufficient(
        valid_source_acc,
        transfer_data.amount,
    ):
        raise exceptions.InsufficientFunds()

    categorizer_response = categorizer.categorize(
        transfer_data.description,
        rule_source=(
            TransactionClassificationSource.DESCRIPTION_RULE
        ),
    )

    transaction.withdraw_funds(
        valid_source_acc,
        transfer_data.amount,
    )
    transaction.deposit_funds(
        recipient_account,
        transfer_data.amount,
    )

    transaction_record_data = transactions.TransactionCreateRecord(
        sender_account_id=valid_source_acc.id,
        recipient_account_id=recipient_account.id,
        sender_iban=valid_source_acc.iban,
        recipient_iban=recipient_account.iban,
        amount=transfer_data.amount,
        status=TransactionStatus.SUCCESSFUL,
        created_at=datetime.now(timezone.utc),
        operation_type=OperationType.TRANSFER,
        description=transfer_data.description,
        category=categorizer_response["category"],
        # A SEPA transfer has no merchant MCC in this simulator.
        mcc_code=None,
        classification_source=(
            categorizer_response["classification_source"]
        ),
    )

    new_record = transaction.create_transaction_record(
        transaction_record_data,
        db,
    )

    db.flush()
    credit_score.recalculate_user_credit_score(
        valid_source_acc.owner_id,
        db,
        commit=False,
    )

    db.commit()
    db.refresh(new_record)

    return new_record
