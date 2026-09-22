from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from database import get_db
from dependecies import auth
from dependecies.accounts import get_valid_acc
from dependecies.users import get_current_user
from crud import transaction
from schemas import transactions
from schemas.common import ResourceId
from schemas.transactions import CashOperationsResponse
from services import cash_operations, transfers


router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
    dependencies=[Depends(auth.verify_existing_token)],
)


@router.post(
    "/{acc_id}",
    response_model=transactions.TransactionResponse,
)
def transfer_money(
    acc_id: ResourceId,
    transfer_data: transactions.TransferDataInput,
    valid_source_acc: models.Account = Depends(get_valid_acc),
    db: Session = Depends(get_db),
):
    return transfers.transfer_money(
        transfer_data,
        valid_source_acc,
        db,
    )


@router.get(
    "/",
    response_model=list[transactions.TransactionResponse],
)
def get_transactions_history(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transaction.get_transactions_history(user.id, db)


@router.post(
    "/{acc_id}/deposit",
    response_model=CashOperationsResponse,
)
def deposit_cash(
    acc_id: ResourceId,
    amount_data: transactions.CashOperation,
    valid_acc: models.Account = Depends(get_valid_acc),
    db: Session = Depends(get_db),
):
    return cash_operations.deposit_cash(amount_data, valid_acc, db)


@router.post(
    "/{acc_id}/withdraw",
    response_model=CashOperationsResponse,
)
def withdraw_cash(
    acc_id: ResourceId,
    amount_data: transactions.CashOperation,
    valid_acc: models.Account = Depends(get_valid_acc),
    db: Session = Depends(get_db),
):
    return cash_operations.withdraw_cash(amount_data, valid_acc, db)
