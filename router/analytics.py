from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import models
from database import get_db
from dependecies import auth
from dependecies.users import get_current_user
from schemas.analytics import (
    CustomerInsightsResponse,
    SpendingSummaryResponse,
)
from services import analytics


AnalyticsWindow = Annotated[
    int,
    Query(ge=1, le=365),
]


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics & Insights"],
    dependencies=[Depends(auth.verify_existing_token)],
)


@router.get(
    "/spending-summary",
    response_model=SpendingSummaryResponse,
)
def get_spending_summary(
    days: AnalyticsWindow = 30,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return analytics.get_spending_summary(
        user.id,
        days,
        db,
    )


@router.get(
    "/customer-insights",
    response_model=CustomerInsightsResponse,
)
def get_customer_insights(
    days: AnalyticsWindow = 90,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return analytics.get_customer_insights(
        user.id,
        days,
        db,
    )
