from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from enums import CreditStatementStatus


class CreditStatementResponse(BaseModel):
    id: int
    account_id: int
    period_start: date
    period_end: date
    due_date: date
    statement_balance: Decimal
    minimum_payment: Decimal
    amount_paid: Decimal
    status: CreditStatementStatus
    minimum_paid_at: datetime | None
    paid_in_full_at: datetime | None
    evaluated_at: datetime | None
    interest_charged: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreditMetricsResponse(BaseModel):
    on_time_payments_count: int
    total_missed_payments_count: int
    current_days_past_due: int
    max_days_past_due: int
    rapid_limit_depletion_count: int

    model_config = ConfigDict(from_attributes=True)


class CreditAccountDashboardResponse(BaseModel):
    account_id: int
    balance: Decimal
    outstanding_debt: Decimal
    credit_limit: Decimal
    available_credit: Decimal
    grace_period_active: bool
    acquired_interest: Decimal
    metrics: CreditMetricsResponse
    current_statement: CreditStatementResponse | None


class CreditRepaymentInput(BaseModel):
    amount: Decimal = Field(gt=0)


class CreditRepaymentResponse(BaseModel):
    account_id: int
    payment_amount: Decimal
    balance: Decimal
    grace_period_active: bool
    statement_id: int | None
    statement_amount_paid: Decimal | None
    statement_status: CreditStatementStatus | None
