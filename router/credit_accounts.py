from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from database import get_db
from dependecies import auth
from dependecies.accounts import get_valid_credit_acc
from crud import credit as crud_credit
from schemas import credit
from schemas.common import ResourceId
from services import credit as credit_services


router = APIRouter(
    prefix="/credit-accounts",
    tags=["Credit Accounts"],
    dependencies=[Depends(auth.verify_existing_token)],
)


@router.get(
    "/{acc_id}",
    response_model=credit.CreditAccountDashboardResponse,
)
def get_credit_account_dashboard(
    acc_id: ResourceId,
    account: models.Account = Depends(get_valid_credit_acc),
    db: Session = Depends(get_db),
):
    return credit_services.get_credit_dashboard(account, db)


@router.post(
    "/{acc_id}/payments",
    response_model=credit.CreditRepaymentResponse,
)
def repay_credit_account(
    acc_id: ResourceId,
    payment: credit.CreditRepaymentInput,
    account: models.Account = Depends(get_valid_credit_acc),
    db: Session = Depends(get_db),
):
    return credit_services.repay_credit_account(
        account,
        payment,
        db,
    )


@router.get(
    "/{acc_id}/statements",
    response_model=list[credit.CreditStatementResponse],
)
def get_credit_statements(
    acc_id: ResourceId,
    account: models.Account = Depends(get_valid_credit_acc),
    db: Session = Depends(get_db),
):
    return crud_credit.get_statements(account.id, db)
