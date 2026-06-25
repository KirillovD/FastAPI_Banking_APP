#this file has everything when it comes to transactions
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import dependencies
from crud import transaction,accounts
import exceptions,schemas
from database import get_db

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
    dependencies = [Depends(dependencies.verify_existing_token)]
)

@router.post("/")
def transfer_money(transfer_data  : schemas.TransferMoney,
                   user_id : int = Depends(dependencies.verify_existing_token),
                   db : Session = Depends(get_db)):

    source_account = accounts.get_acc_by_id_with_token(user_id, transfer_data.source_account_id, db)
    recipient_account = accounts.get_acc_by_id(transfer_data.recipient_acc_id, db)

    if not source_account:
        raise exceptions.AccountNotFoundException(detail=
                                                  "Source account not found or access denied")
    if not recipient_account:
        raise exceptions.AccountNotFoundException(detail="Recipient account not found")

    if transfer_data.recipient_name != f"{recipient_account.owner.first_name} {recipient_account.owner.last_name}":
        raise exceptions.UserNotFoundException(detail="Recipient name is wrong or doesn't exist")

    if transaction.is_balance_sufficient(source_account,transfer_data.transfer_amount) is False:
        raise exceptions.AccountInsufficientFundsException()

    transaction.transfer_money(source_account,
                                      recipient_account,
                                      transfer_data.transfer_amount,
                                      db)

    return {"Message": "Transfer successful!", "Amount": transfer_data.transfer_amount}


@router.get("/", response_model = list[schemas.TransactionResponse])
def get_transactions_history(user_id : int = Depends(dependencies.verify_existing_token),
                             db : Session = Depends(get_db)):

    return transaction.get_transactions_history(user_id,db)

@router.post("/deposit")
def deposit_cash(acc_id_and_amount : schemas.CashOperation ,
                 user_id : int = Depends(dependencies.verify_existing_token),
                 db : Session = Depends(get_db)):

    account = accounts.get_acc_by_id_with_token(user_id,acc_id_and_amount.acc_id,db)

    if not account:
        raise exceptions.AccountNotFoundException()

    deposit  = transaction.deposit_cash(acc_id_and_amount.acc_id,
                                        acc_id_and_amount.amount,
                                        db )

    return {"Message": "Deposit successful!", "Account Balance:": deposit.acc_balance }


@router.post("/withdraw")
def withdraw_cash(acc_id_and_amount : schemas.CashOperation ,
                  user_id : int = Depends(dependencies.verify_existing_token),
                  db : Session = Depends(get_db)):

    account = accounts.get_acc_by_id_with_token(user_id,acc_id_and_amount.acc_id,db)

    if not account:
        raise exceptions.AccountNotFoundException()

    if not transaction.is_balance_sufficient(account,acc_id_and_amount.amount):
        raise exceptions.AccountInsufficientFundsException()

    withdraw  = transaction.withdraw_cash(acc_id_and_amount.acc_id,
                                        acc_id_and_amount.amount,
                                        db )

    return {"Message": "Withdraw successful!", "Account Balance:": withdraw.acc_balance }
