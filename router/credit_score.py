from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from database import get_db
from dependecies import auth
from dependecies.users import get_current_user
from schemas.credit_score import CreditScoreResponse
from services import credit_score


router = APIRouter(
    prefix="/credit-score",
    tags=["Synthetic Credit Score"],
    dependencies=[Depends(auth.verify_existing_token)],
)


@router.get("/", response_model=CreditScoreResponse)
def get_credit_score(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return credit_score.recalculate_user_credit_score(
        user.id,
        db,
        commit=True,
    )
