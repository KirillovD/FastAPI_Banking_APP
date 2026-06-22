#this file has everything when it comes to transactions
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from crud import transaction,accounts
import exceptions,schemas,utils
from database import get_db

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
    dependencies = [Depends(utils.verify_existing_token)]
)

@router.post("/")
def transfer_money(transfer_data  : schemas.TransferMoney,
                   user_id : int = Depends(utils.verify_existing_token),
                   db : Session = Depends(get_db)):

    source_account = accounts.find_source_acc(user_id, transfer_data.source_account_id, db)
    recipient_account = accounts.find_recipient_acc(transfer_data.recipient_acc_id, db)

    if not source_account:
        raise exceptions.AccountNotFoundException(detail=
                                                  "Source account not found or access denied")
    if not recipient_account:
        raise exceptions.AccountNotFoundException(detail="Recipient account not found")

    if transaction.is_balance_sufficient(source_account,transfer_data.transfer_amount) is False:
        raise exceptions.AccountInsufficientFundsException()

    transaction.transfer_money(source_account,
                                      recipient_account,
                                      transfer_data.transfer_amount,
                                      db)

    return {"Message": "Transfer successful!", "Amount": transfer_data.transfer_amount}





