#this file has everything when it comes to transactions
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import utils
from dependecies import auth
from crud import transaction,accounts, cards
import exceptions,schemas
from database import get_db
from dependecies.accounts import get_valid_acc
from dependecies.users import get_current_user
from schemas import CashOperationsResponse
from services import payments
from services.categorizer import categorizer


router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
    dependencies = [Depends(auth.verify_existing_token)]
)

@router.post("/{acc_id}",response_model = schemas.TransactionResponse)
def transfer_money(acc_id : int,
                   transfer_data  : schemas.TransferMoney,
                   valid_source_acc: models.Account = Depends(get_valid_acc),
                   db : Session = Depends(get_db)):

    recipient_account = accounts.get_acc_by_iban(transfer_data.recipient_iban, db)

    if not recipient_account:
        raise exceptions.AccountNotFound(detail="Recipient account not found")

    if transfer_data.recipient_name != f"{recipient_account.owner.first_name} {recipient_account.owner.last_name}":
        raise exceptions.UserNotFound(detail="Recipient name is wrong or doesn't exist")

    if payments.is_balance_sufficient(valid_source_acc, transfer_data.transfer_amount) is False:
        raise exceptions.InsufficientFunds()


    categorizer_response = categorizer.categorize(transfer_data.description)


    transaction_data = transaction.transfer_money(source_account = valid_source_acc,
                               recipient_account = recipient_account,
                               transfer_amount = transfer_data.transfer_amount,
                               description = transfer_data.description,
                               category = categorizer_response["category"],
                               db = db)

    return  transaction_data


@router.get("/", response_model = list[schemas.TransactionResponse])
def get_transactions_history(user : models.User = Depends(get_current_user),
                             db : Session = Depends(get_db)):

    return transaction.get_transactions_history(user.id,db)


@router.post("/{acc_id}/deposit", response_model= CashOperationsResponse)
def deposit_cash(acc_id : int,
                 amount_data : schemas.CashOperation,
                 valid_acc : models.Account = Depends(get_valid_acc),
                 db : Session = Depends(get_db)):

    account_after_deposit  = transaction.deposit_cash(valid_acc.id,
                                        amount_data.amount,
                                        db )

    return account_after_deposit


@router.post("/{acc_id}/withdraw", response_model= CashOperationsResponse)
def withdraw_cash(acc_id : int,
                  amount_data : schemas.CashOperation,
                  valid_acc: models.Account = Depends(get_valid_acc),
                  db : Session = Depends(get_db)) :

    if not payments.is_balance_sufficient(valid_acc, amount_data.amount):
        raise exceptions.InsufficientFunds()

    account_after_withdraw  = transaction.withdraw_cash(valid_acc.id,
                                          amount_data.amount,
                                          db)

    return account_after_withdraw


@router.post("/process_paymnent", response_model=schemas.CardPaymentResponse)
def process_payment(payment_info: schemas.CardPaymentCreate,
                    db: Session = Depends(get_db)):

    result = payments.process_payment(payment_info,db)

    return 