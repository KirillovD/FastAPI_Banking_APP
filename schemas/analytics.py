from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from enums import TransactionCategory


class CategorySpend(BaseModel):
    category: TransactionCategory
    amount: Decimal
    percentage: Decimal
    transaction_count: int


class TopSpendingLabel(BaseModel):
    label: str
    amount: Decimal
    transaction_count: int


class SpendingSummaryResponse(BaseModel):
    window_days: int
    generated_at: datetime
    total_spend: Decimal
    transaction_count: int
    categories: list[CategorySpend]
    top_merchants: list[TopSpendingLabel]


class CustomerInsightSignal(BaseModel):
    code: str
    label: str
    share_percent: Decimal
    explanation: str


class SuggestedOffer(BaseModel):
    code: str
    title: str
    reason: str


class CustomerInsightsResponse(BaseModel):
    window_days: int
    profile_tags: list[str]
    signals: list[CustomerInsightSignal]
    risk_category_share_percent: Decimal
    stability_category_share_percent: Decimal
    suggested_offers: list[SuggestedOffer]
    spending_summary: SpendingSummaryResponse
    disclaimer: str
