from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
from crud import accounts
from enums import (
    OperationType,
    TransactionCategory,
    TransactionStatus,
)
from schemas.analytics import (
    CategorySpend,
    CustomerInsightSignal,
    CustomerInsightsResponse,
    SpendingSummaryResponse,
    SuggestedOffer,
    TopSpendingLabel,
)


PERCENT_QUANTUM = Decimal("0.1")
MONEY_QUANTUM = Decimal("0.01")
TOP_MERCHANT_LIMIT = 5

MOBILITY_CATEGORIES = {
    TransactionCategory.PUBLIC_TRANSIT,
    TransactionCategory.TAXI_CARSHARING,
    TransactionCategory.FUEL,
}
DINING_CATEGORIES = {
    TransactionCategory.RESTAURANTS,
    TransactionCategory.DELIVERY_FAST_FOOD,
}
SHOPPING_CATEGORIES = {
    TransactionCategory.ELECTRONICS,
    TransactionCategory.CLOTHING,
    TransactionCategory.E_COMMERCE,
}
STABILITY_CATEGORIES = {
    TransactionCategory.INVESTMENTS,
    TransactionCategory.INSURANCES,
}
RISK_CATEGORIES = {
    TransactionCategory.GAMBLING,
    TransactionCategory.MICROLOANS,
}


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANTUM)


def _percent(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= Decimal("0"):
        return Decimal("0.0")

    return (
        numerator
        / denominator
        * Decimal("100")
    ).quantize(PERCENT_QUANTUM)


def _outgoing_transactions(
    user_id: int,
    days: int,
    db: Session,
    now: datetime,
) -> list[models.Transaction]:
    user_accounts = accounts.get_all_user_accounts(
        user_id,
        db,
    )
    account_ids = [account.id for account in user_accounts]

    if not account_ids:
        return []

    cutoff = now - timedelta(days=days)

    return (
        db.query(models.Transaction)
        .filter(
            models.Transaction.sender_account_id.in_(
                account_ids
            ),
            models.Transaction.created_at >= cutoff,
            models.Transaction.status
            == TransactionStatus.SUCCESSFUL,
            models.Transaction.operation_type.in_(
                [
                    OperationType.PAYMENT,
                    OperationType.TRANSFER,
                ]
            ),
            or_(
                models.Transaction.operation_type
                != OperationType.TRANSFER,
                models.Transaction.recipient_account_id.is_(None),
                ~models.Transaction.recipient_account_id.in_(
                    account_ids
                ),
            ),
        )
        .order_by(
            models.Transaction.created_at.desc(),
            models.Transaction.id.desc(),
        )
        .all()
    )


def _spending_label(
    transaction: models.Transaction,
) -> str:
    if transaction.description:
        return transaction.description.strip()

    if (
        transaction.operation_type == OperationType.TRANSFER
        and transaction.recipient_iban
    ):
        return transaction.recipient_iban

    if transaction.operation_type == OperationType.PAYMENT:
        return "Card payment"

    return "Bank transfer"


def get_spending_summary(
    user_id: int,
    days: int,
    db: Session,
    *,
    now: datetime | None = None,
) -> SpendingSummaryResponse:
    now = now or datetime.now(timezone.utc)
    transactions = _outgoing_transactions(
        user_id,
        days,
        db,
        now,
    )

    category_amounts: dict[
        TransactionCategory,
        Decimal,
    ] = defaultdict(lambda: Decimal("0.00"))
    category_counts: dict[
        TransactionCategory,
        int,
    ] = defaultdict(int)
    label_amounts: dict[str, Decimal] = defaultdict(
        lambda: Decimal("0.00")
    )
    label_counts: dict[str, int] = defaultdict(int)

    total_spend = Decimal("0.00")

    for transaction in transactions:
        amount = _money(transaction.amount)
        total_spend += amount

        category_amounts[transaction.category] += amount
        category_counts[transaction.category] += 1

        label = _spending_label(transaction)
        label_amounts[label] += amount
        label_counts[label] += 1

    total_spend = _money(total_spend)

    categories = [
        CategorySpend(
            category=category,
            amount=_money(amount),
            percentage=_percent(
                amount,
                total_spend,
            ),
            transaction_count=category_counts[category],
        )
        for category, amount in sorted(
            category_amounts.items(),
            key=lambda item: (
                -item[1],
                item[0].value,
            ),
        )
    ]

    top_merchants = [
        TopSpendingLabel(
            label=label,
            amount=_money(amount),
            transaction_count=label_counts[label],
        )
        for label, amount in sorted(
            label_amounts.items(),
            key=lambda item: (
                -item[1],
                item[0].casefold(),
            ),
        )[:TOP_MERCHANT_LIMIT]
    ]

    return SpendingSummaryResponse(
        window_days=days,
        generated_at=now,
        total_spend=total_spend,
        transaction_count=len(transactions),
        categories=categories,
        top_merchants=top_merchants,
    )


def _category_share(
    summary: SpendingSummaryResponse,
    categories: set[TransactionCategory],
) -> Decimal:
    amount = sum(
        (
            row.amount
            for row in summary.categories
            if row.category in categories
        ),
        Decimal("0.00"),
    )
    return _percent(
        amount,
        summary.total_spend,
    )


def _signal(
    code: str,
    label: str,
    share: Decimal,
    explanation: str,
) -> CustomerInsightSignal:
    return CustomerInsightSignal(
        code=code,
        label=label,
        share_percent=share,
        explanation=explanation,
    )


def get_customer_insights(
    user_id: int,
    days: int,
    db: Session,
    *,
    now: datetime | None = None,
) -> CustomerInsightsResponse:
    summary = get_spending_summary(
        user_id,
        days,
        db,
        now=now,
    )

    shares = {
        "groceries": _category_share(
            summary,
            {TransactionCategory.GROCERIES},
        ),
        "mobility": _category_share(
            summary,
            MOBILITY_CATEGORIES,
        ),
        "dining": _category_share(
            summary,
            DINING_CATEGORIES,
        ),
        "shopping": _category_share(
            summary,
            SHOPPING_CATEGORIES,
        ),
        "subscriptions": _category_share(
            summary,
            {TransactionCategory.SUBSCRIPTIONS},
        ),
        "stability": _category_share(
            summary,
            STABILITY_CATEGORIES,
        ),
        "risk": _category_share(
            summary,
            RISK_CATEGORIES,
        ),
    }

    signals: list[CustomerInsightSignal] = []
    tags: list[str] = []
    offers: list[SuggestedOffer] = []

    if shares["groceries"] >= Decimal("20.0"):
        tags.append("grocery_focused")
        signals.append(
            _signal(
                "grocery_focused",
                "Grocery-focused spending",
                shares["groceries"],
                "A large share of recent categorized spending is groceries.",
            )
        )
        offers.append(
            SuggestedOffer(
                code="grocery_cashback",
                title="Grocery cashback card",
                reason=(
                    "Recent grocery spending is high enough that "
                    "cashback on supermarket purchases could be relevant."
                ),
            )
        )

    if shares["mobility"] >= Decimal("15.0"):
        tags.append("mobility_spender")
        signals.append(
            _signal(
                "mobility_spender",
                "Mobility-focused spending",
                shares["mobility"],
                "Public transport, taxi/carsharing and fuel form a meaningful share of spend.",
            )
        )
        offers.append(
            SuggestedOffer(
                code="mobility_rewards",
                title="Mobility rewards card",
                reason=(
                    "Recent transport-related spending suggests "
                    "mobility rewards could be relevant."
                ),
            )
        )

    if shares["dining"] >= Decimal("15.0"):
        tags.append("dining_focused")
        signals.append(
            _signal(
                "dining_focused",
                "Dining-focused spending",
                shares["dining"],
                "Restaurants and delivery form a meaningful share of recent spend.",
            )
        )

    if shares["shopping"] >= Decimal("20.0"):
        tags.append("shopping_focused")
        signals.append(
            _signal(
                "shopping_focused",
                "Shopping-focused spending",
                shares["shopping"],
                "Shopping and e-commerce form a large share of recent spend.",
            )
        )

    if (
        shares["dining"] >= Decimal("15.0")
        or shares["shopping"] >= Decimal("20.0")
    ):
        offers.append(
            SuggestedOffer(
                code="lifestyle_rewards",
                title="Lifestyle rewards card",
                reason=(
                    "Dining or shopping patterns suggest a general "
                    "lifestyle rewards product could be relevant."
                ),
            )
        )

    if shares["subscriptions"] >= Decimal("5.0"):
        tags.append("subscription_user")
        signals.append(
            _signal(
                "subscription_user",
                "Recurring digital-services spender",
                shares["subscriptions"],
                "Subscriptions are a visible part of recent categorized spending.",
            )
        )

    if shares["stability"] >= Decimal("10.0"):
        tags.append("financial_products_engaged")
        signals.append(
            _signal(
                "financial_products_engaged",
                "Financial-products engagement",
                shares["stability"],
                "Insurance and investment categories form a meaningful share of recent spend.",
            )
        )
        offers.append(
            SuggestedOffer(
                code="financial_services_bundle",
                title="Insurance / wealth bundle",
                reason=(
                    "Recent insurance or investment activity suggests "
                    "related financial-service offers may be relevant."
                ),
            )
        )

    if shares["risk"] >= Decimal("5.0"):
        tags.append("elevated_risk_category_spend")
        signals.append(
            _signal(
                "elevated_risk_category_spend",
                "Elevated risk-category spending",
                shares["risk"],
                "Gambling or microloan categories exceed the demo risk-signal threshold.",
            )
        )

    if (
        summary.total_spend > Decimal("0.00")
        and not offers
        and shares["risk"] < Decimal("5.0")
    ):
        offers.append(
            SuggestedOffer(
                code="general_cashback",
                title="General cashback card",
                reason=(
                    "No single spending category dominates enough for "
                    "a more specialized demo recommendation."
                ),
            )
        )

    return CustomerInsightsResponse(
        window_days=days,
        profile_tags=tags,
        signals=signals,
        risk_category_share_percent=shares["risk"],
        stability_category_share_percent=shares["stability"],
        suggested_offers=offers,
        spending_summary=summary,
        disclaimer=(
            "Synthetic portfolio insights only; not a lending decision, "
            "underwriting outcome, or real advertising profile."
        ),
    )
