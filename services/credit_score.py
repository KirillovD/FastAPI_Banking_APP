from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

import exceptions
import models
from enums import (
    AccountType,
    OperationType,
    TransactionCategory,
)
from schemas.credit_score import (
    CreditScoreFactor,
    CreditScoreResponse,
)


BASELINE_SCORE = 500
MIN_SCORE = 300
MAX_SCORE = 850
BEHAVIOR_WINDOW_DAYS = 90

RISK_CATEGORIES = {
    TransactionCategory.GAMBLING,
    TransactionCategory.MICROLOANS,
}
STABILITY_CATEGORIES = {
    TransactionCategory.INVESTMENTS,
    TransactionCategory.INSURANCES,
}


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _payment_history_factor(
    on_time: int,
    missed: int,
) -> CreditScoreFactor:
    total = on_time + missed

    if total == 0:
        return CreditScoreFactor(
            name="payment_history",
            impact=0,
            value="No evaluated statements yet",
            explanation=(
                "Payment history has not been established yet."
            ),
        )

    confidence = min(total, 6) / 6
    positive = round(
        (on_time / total) * 120 * confidence
    )
    missed_penalty = min(missed * 50, 120)
    impact = _clamp(
        positive - missed_penalty,
        -120,
        120,
    )

    return CreditScoreFactor(
        name="payment_history",
        impact=impact,
        value=f"{on_time} on-time / {missed} missed",
        explanation=(
            "On-time statement history builds score gradually, "
            "while missed minimum obligations carry a stronger "
            "immediate penalty."
        ),
    )


def _delinquency_factor(
    current_dpd: int,
    max_dpd: int,
) -> CreditScoreFactor:
    current_penalty = min(current_dpd * 5, 100)
    history_penalty = min(max_dpd, 50)
    impact = -min(
        current_penalty + history_penalty,
        150,
    )

    if current_dpd > 0:
        explanation = (
            "A statement is currently past due; the penalty grows "
            "as current days past due increase."
        )
    elif max_dpd > 0:
        explanation = (
            "There is no current delinquency, but historical days "
            "past due still reduce the synthetic score."
        )
    else:
        explanation = "There is no current or historical delinquency."

    return CreditScoreFactor(
        name="delinquency",
        impact=impact,
        value=(
            f"current DPD {current_dpd}, "
            f"max DPD {max_dpd}"
        ),
        explanation=explanation,
    )


def _utilization_factor(
    debt: Decimal,
    credit_limit: Decimal,
) -> CreditScoreFactor:
    if credit_limit <= Decimal("0"):
        return CreditScoreFactor(
            name="credit_utilization",
            impact=0,
            value="No available credit limit",
            explanation=(
                "Utilization cannot be calculated without a credit limit."
            ),
        )

    utilization = debt / credit_limit

    if utilization <= Decimal("0"):
        impact = 0
    elif utilization <= Decimal("0.30"):
        impact = 40
    elif utilization <= Decimal("0.50"):
        impact = 20
    elif utilization <= Decimal("0.75"):
        impact = -20
    elif utilization <= Decimal("1.00"):
        impact = -60
    else:
        impact = -80

    percent = (utilization * Decimal("100")).quantize(
        Decimal("0.1")
    )

    return CreditScoreFactor(
        name="credit_utilization",
        impact=impact,
        value=f"{percent}% utilization",
        explanation=(
            "Utilization compares total outstanding credit debt "
            "with the user's total credit limit."
        ),
    )


def _credit_age_factor(
    oldest_created_at: datetime | None,
    as_of: datetime,
) -> CreditScoreFactor:
    if oldest_created_at is None:
        return CreditScoreFactor(
            name="credit_history_age",
            impact=0,
            value="No credit account",
            explanation="No credit-account history exists yet.",
        )

    created_at = oldest_created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    age_days = max(
        (as_of - created_at).days,
        0,
    )

    if age_days < 30:
        impact = 0
    elif age_days < 180:
        impact = 5
    elif age_days < 365:
        impact = 10
    elif age_days < 730:
        impact = 20
    elif age_days < 1095:
        impact = 30
    else:
        impact = 40

    return CreditScoreFactor(
        name="credit_history_age",
        impact=impact,
        value=f"{age_days} days",
        explanation=(
            "Longer established credit history adds a modest "
            "confidence bonus in this synthetic model."
        ),
    )


def _rapid_depletion_factor(
    event_count: int,
) -> CreditScoreFactor:
    impact = -min(event_count * 10, 60)

    return CreditScoreFactor(
        name="rapid_limit_depletion",
        impact=impact,
        value=f"{event_count} events",
        explanation=(
            "Repeatedly crossing from below 50% utilization to at "
            "least 80% utilization is treated as a risk signal."
        ),
    )


def _behavioral_factor(
    user_account_ids: list[int],
    db: Session,
    as_of: datetime,
) -> CreditScoreFactor:
    if not user_account_ids:
        return CreditScoreFactor(
            name="financial_behavior",
            impact=0,
            value="No recent outgoing spending",
            explanation=(
                "No categorized outgoing spending is available."
            ),
        )

    cutoff = as_of - timedelta(
        days=BEHAVIOR_WINDOW_DAYS
    )

    transactions = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.sender_account_id.in_(
                user_account_ids
            ),
            models.Transaction.created_at >= cutoff,
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
                    user_account_ids
                ),
            ),
        )
        .all()
    )

    total_spend = sum(
        (
            Decimal(transaction.amount)
            for transaction in transactions
        ),
        Decimal("0.00"),
    )

    if total_spend <= Decimal("0"):
        return CreditScoreFactor(
            name="financial_behavior",
            impact=0,
            value="No recent outgoing spending",
            explanation=(
                "No categorized outgoing spending is available."
            ),
        )

    risk_spend = sum(
        (
            Decimal(transaction.amount)
            for transaction in transactions
            if transaction.category in RISK_CATEGORIES
        ),
        Decimal("0.00"),
    )
    stability_spend = sum(
        (
            Decimal(transaction.amount)
            for transaction in transactions
            if transaction.category in STABILITY_CATEGORIES
        ),
        Decimal("0.00"),
    )

    risk_ratio = risk_spend / total_spend
    stability_ratio = stability_spend / total_spend

    if risk_ratio >= Decimal("0.20"):
        risk_impact = -25
    elif risk_ratio >= Decimal("0.10"):
        risk_impact = -18
    elif risk_ratio >= Decimal("0.05"):
        risk_impact = -10
    elif risk_ratio > Decimal("0"):
        risk_impact = -4
    else:
        risk_impact = 0

    if stability_ratio >= Decimal("0.20"):
        stability_impact = 15
    elif stability_ratio >= Decimal("0.10"):
        stability_impact = 10
    elif stability_ratio >= Decimal("0.05"):
        stability_impact = 5
    else:
        stability_impact = 0

    impact = _clamp(
        risk_impact + stability_impact,
        -25,
        15,
    )

    risk_percent = (
        risk_ratio * Decimal("100")
    ).quantize(Decimal("0.1"))
    stability_percent = (
        stability_ratio * Decimal("100")
    ).quantize(Decimal("0.1"))

    return CreditScoreFactor(
        name="financial_behavior",
        impact=impact,
        value=(
            f"{risk_percent}% risk-category / "
            f"{stability_percent}% stability-category spend "
            f"over {BEHAVIOR_WINDOW_DAYS} days"
        ),
        explanation=(
            "Categorized spending is intentionally a small bounded "
            "factor; repayment and delinquency remain dominant."
        ),
    )


def calculate_user_credit_score(
    user_id: int,
    db: Session,
    as_of: datetime | None = None,
) -> CreditScoreResponse:
    as_of = as_of or datetime.now(timezone.utc)

    user = db.get(models.User, user_id)
    if user is None:
        raise exceptions.UserNotFound()

    credit_accounts = (
        db.query(models.Account)
        .filter(
            models.Account.owner_id == user_id,
            models.Account.type == AccountType.CREDIT,
        )
        .all()
    )
    all_accounts = (
        db.query(models.Account)
        .filter(models.Account.owner_id == user_id)
        .all()
    )

    on_time = 0
    missed = 0
    current_dpd = 0
    max_dpd = 0
    rapid_depletion = 0
    total_debt = Decimal("0.00")
    total_limit = Decimal("0.00")
    oldest_created_at = None

    for account in credit_accounts:
        total_debt += max(
            -Decimal(account.balance),
            Decimal("0.00"),
        )
        total_limit += max(
            Decimal(account.limit),
            Decimal("0.00"),
        )

        if (
            oldest_created_at is None
            or account.created_at < oldest_created_at
        ):
            oldest_created_at = account.created_at

        metrics = account.credit_account_metrics
        if metrics is None:
            continue

        on_time += metrics.on_time_payments_count
        missed += metrics.total_missed_payments_count
        current_dpd = max(
            current_dpd,
            metrics.current_days_past_due,
        )
        max_dpd = max(
            max_dpd,
            metrics.max_days_past_due,
        )
        rapid_depletion += (
            metrics.rapid_limit_depletion_count
        )

    factors = [
        _payment_history_factor(on_time, missed),
        _delinquency_factor(
            current_dpd,
            max_dpd,
        ),
        _utilization_factor(
            total_debt,
            total_limit,
        ),
        _credit_age_factor(
            oldest_created_at,
            as_of,
        ),
        _rapid_depletion_factor(
            rapid_depletion,
        ),
        _behavioral_factor(
            [account.id for account in all_accounts],
            db,
            as_of,
        ),
    ]

    raw_score = BASELINE_SCORE + sum(
        factor.impact for factor in factors
    )
    score = _clamp(
        raw_score,
        MIN_SCORE,
        MAX_SCORE,
    )

    return CreditScoreResponse(
        score=score,
        raw_score=raw_score,
        baseline=BASELINE_SCORE,
        range_min=MIN_SCORE,
        range_max=MAX_SCORE,
        label="synthetic_demo_score",
        disclaimer=(
            "Custom portfolio simulation only; not FICO, SCHUFA "
            "or a real lending/underwriting decision model."
        ),
        factors=factors,
    )


def recalculate_user_credit_score(
    user_id: int,
    db: Session,
    *,
    commit: bool = False,
) -> CreditScoreResponse:
    result = calculate_user_credit_score(
        user_id,
        db,
    )

    user = db.get(models.User, user_id)
    user.credit_score = result.score

    if commit:
        db.commit()
        db.refresh(user)

    return result
