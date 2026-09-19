from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from database import get_db
from dependecies import auth
from dependecies.users import get_current_user
from schemas import transactions
from services import payments


router = APIRouter(
    prefix="/payments",
    tags=["Payment Simulator"],
    dependencies=[Depends(auth.verify_existing_token)],
)


@router.post("/", response_model=transactions.CardPaymentResponse)
def process_payment(
    payment_info: transactions.CardPaymentCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return payments.process_payment(
        payment_info,
        user,
        db,
    )
