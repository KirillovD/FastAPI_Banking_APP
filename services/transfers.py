import datetime
from datetime import datetime, timezone
from sqlalchemy.orm import Session

import exceptions
import models
from crud import accounts, transaction
from enums import TransactionStatus, OperationType
from services import payments
from services.categorizer import categorizer
from schemas import transactions


def transfer_money(transfer_data  : transactions.TransferDataInput,
                   valid_source_acc: models.Account,
                   db : Session):

    recipient_account = accounts.get_acc_by_iban(transfer_data.recipient_iban, db)

    if not recipient_account:
        raise exceptions.AccountNotFound(detail="Recipient account not found")

    if transfer_data.recipient_name != f"{recipient_account.owner.first_name} {recipient_account.owner.last_name}":
        raise exceptions.UserNotFound(detail="Recipient name is wrong or doesn't exist")

    if payments.is_account_balance_sufficient(valid_source_acc, transfer_data.amount) is False:
        raise exceptions.InsufficientFunds()


    categorizer_response = categorizer.categorize(transfer_data.description)

    transaction.withdraw_funds(valid_source_acc, transfer_data.amount)
    transaction.deposit_funds(recipient_account,transfer_data.amount)

    transaction_record_data = transactions.TransactionCreateRecord(
        **transfer_data.model_dump(exclude={"recipient_name"}),
        recipient_account_id=recipient_account.id,
        status= TransactionStatus.SUCCESSFUL,
        created_at= datetime.now(timezone.utc),
        operation_type= OperationType.TRANSFER,
        category=categorizer_response["category"])

    new_record= transaction.create_transaction_record(transaction_record_data,db)

    db.commit()
    db.refresh(new_record)

    return  new_record




