from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import logging
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

import exceptions
import models
from config import settings
from crud import accounts as crud_accounts
from crud import credit as crud_credit
from crud import transaction as crud_transaction
from enums import AccountType, CreditStatementStatus
from money import MONEY_QUANTUM
from schemas import credit as credit_schemas
from services import credit_score


logger = logging.getLogger(__name__)


def _business_timezone() -> ZoneInfo:
    return ZoneInfo(settings.bank_business_timezone)


def _business_date(value: datetime | None = None) -> date:
    tz = _business_timezone()

    if value is None:
        return datetime.now(tz).date()

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(tz).date()


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANTUM)


def _ensure_metrics(account: models.Account) -> models.CreditAccountMetrics:
    metrics = account.credit_account_metrics

    if metrics is None:
        metrics = models.CreditAccountMetrics(
            on_time_payments_count=0,
            total_missed_payments_count=0,
            current_days_past_due=0,
            max_days_past_due=0,
            rapid_limit_depletion_count=0,
        )
        account.credit_account_metrics = metrics

    return metrics


def _normalized_apr() -> Decimal:
    apr = Decimal(settings.credit_card_default_apr)

    if apr > Decimal("1"):
        apr = apr / Decimal("100")

    return apr


def get_daily_interest_rate() -> Decimal:
    return _normalized_apr() / Decimal("365")


def calculate_minimum_payment_for_debt(debt: Decimal) -> Decimal:
    debt = _money(abs(Decimal(debt)))

    if debt <= Decimal("0.00"):
        return Decimal("0.00")

    percent_amount = _money(
        debt * settings.credit_card_min_payment_percent
    )
    configured_minimum = _money(
        settings.credit_card_min_payment_amount
    )

    required = max(percent_amount, configured_minimum)
    return min(debt, required)


def calculate_min_credit_account_payment(
    account: models.Account,
) -> Decimal:
    if account.balance >= Decimal("0.00"):
        return Decimal("0.00")

    return calculate_minimum_payment_for_debt(
        abs(account.balance)
    )


def _next_due_date(period_end: date) -> date:
    if period_end.month == 12:
        return date(period_end.year + 1, 1, 15)

    return date(period_end.year, period_end.month + 1, 15)


def create_statement_for_account(
    account: models.Account,
    db: Session,
    as_of_date: date | None = None,
):
    if account.type != AccountType.CREDIT:
        return None

    if account.balance >= Decimal("0.00"):
        return None

    as_of_date = as_of_date or _business_date()

    existing = crud_credit.get_statement_for_period(
        account.id,
        as_of_date,
        db,
    )
    if existing:
        return existing

    latest = crud_credit.get_latest_statement(
        account.id,
        db,
    )

    if latest:
        period_start = latest.period_end + timedelta(days=1)
    else:
        first_day_of_month = as_of_date.replace(day=1)
        period_start = max(
            account.created_at.date(),
            first_day_of_month,
        )

    if period_start > as_of_date:
        return None

    statement_balance = _money(abs(account.balance))

    statement = models.CreditStatement(
        account_id=account.id,
        period_start=period_start,
        period_end=as_of_date,
        due_date=_next_due_date(as_of_date),
        statement_balance=statement_balance,
        minimum_payment=calculate_minimum_payment_for_debt(
            statement_balance
        ),
        amount_paid=Decimal("0.00"),
        status=CreditStatementStatus.OPEN,
        interest_charged=Decimal("0.00"),
    )

    db.add(statement)
    # Autoflush is disabled. Flushing here makes direct helper replay
    # safe and lets the database unique constraint enforce the period.
    db.flush()

    return statement


def create_monthly_statements(
    db: Session,
    as_of_date: date | None = None,
):
    as_of_date = as_of_date or _business_date()
    credit_accounts = crud_accounts.get_all_accounts(
        AccountType.CREDIT,
        db,
    )

    created_count = 0

    for account in credit_accounts:
        created = False

        try:
            with db.begin_nested():
                before = crud_credit.get_statement_for_period(
                    account.id,
                    as_of_date,
                    db,
                )
                statement = create_statement_for_account(
                    account,
                    db,
                    as_of_date,
                )
                created = (
                    statement is not None
                    and before is None
                )

            if created:
                created_count += 1

        except Exception as exc:
            logger.exception(
                "Failed to create credit statement for account %s: %s",
                account.id,
                exc,
            )

    db.commit()
    logger.info(
        "Credit statement creation finished: %s statements created",
        created_count,
    )
    return created_count


def get_credit_dashboard(
    account: models.Account,
    db: Session,
):
    latest_statement = crud_credit.get_latest_statement(
        account.id,
        db,
    )
    metrics = _ensure_metrics(account)

    balance = _money(account.balance)
    outstanding_debt = _money(
        max(-balance, Decimal("0.00"))
    )
    available_credit = _money(
        max(
            account.limit + balance,
            Decimal("0.00"),
        )
    )

    return {
        "account_id": account.id,
        "balance": balance,
        "outstanding_debt": outstanding_debt,
        "credit_limit": _money(account.limit),
        "available_credit": available_credit,
        "grace_period_active": account.grace_period_active,
        "acquired_interest": _money(account.acquired_interest),
        "metrics": {
            "on_time_payments_count": (
                metrics.on_time_payments_count or 0
            ),
            "total_missed_payments_count": (
                metrics.total_missed_payments_count or 0
            ),
            "current_days_past_due": (
                metrics.current_days_past_due or 0
            ),
            "max_days_past_due": (
                metrics.max_days_past_due or 0
            ),
            "rapid_limit_depletion_count": (
                metrics.rapid_limit_depletion_count or 0
            ),
        },
        "current_statement": latest_statement,
    }


def _post_pending_interest(
    account: models.Account,
    db: Session | None = None,
    statement: models.CreditStatement | None = None,
) -> Decimal:
    amount = _money(account.acquired_interest)

    if amount <= Decimal("0.00"):
        account.acquired_interest = Decimal("0.00")
        return Decimal("0.00")

    crud_transaction.withdraw_funds(
        account,
        amount,
        db,
    )
    account.acquired_interest = Decimal("0.00")

    if statement is not None:
        statement.interest_charged = _money(
            (statement.interest_charged or Decimal("0.00"))
            + amount
        )

    return amount


def add_acquired_interest_to_balance(
    account: models.Account,
    db: Session | None = None,
):
    if account.grace_period_active:
        raise exceptions.GraceNoInterest()

    _post_pending_interest(account, db)
    return account


def _paid_on_or_before_due(
    paid_at: datetime | None,
    due_date: date,
) -> bool:
    return (
        paid_at is not None
        and _business_date(paid_at) <= due_date
    )


def _current_statement_status(
    statement: models.CreditStatement,
) -> CreditStatementStatus:
    amount_paid = Decimal(
        statement.amount_paid or Decimal("0.00")
    )

    if amount_paid >= statement.statement_balance:
        return CreditStatementStatus.PAID_IN_FULL

    if amount_paid >= statement.minimum_payment:
        return CreditStatementStatus.MINIMUM_PAID

    if statement.evaluated_at is not None:
        return CreditStatementStatus.PAST_DUE

    return CreditStatementStatus.OPEN


def _recalculate_delinquency_metrics(
    account: models.Account,
    db: Session,
    as_of_date: date,
) -> models.CreditAccountMetrics:
    metrics = _ensure_metrics(account)
    statements = crud_credit.get_statements(
        account.id,
        db,
    )

    current_dpd = 0
    historical_max = metrics.max_days_past_due or 0

    for statement in statements:
        amount_paid = Decimal(
            statement.amount_paid or Decimal("0.00")
        )

        if (
            statement.minimum_paid_at is not None
            and amount_paid >= statement.minimum_payment
        ):
            late_days = max(
                (
                    _business_date(statement.minimum_paid_at)
                    - statement.due_date
                ).days,
                0,
            )
            historical_max = max(
                historical_max,
                late_days,
            )
            continue

        if (
            statement.due_date < as_of_date
            and amount_paid < statement.minimum_payment
        ):
            days_late = (
                as_of_date - statement.due_date
            ).days
            current_dpd = max(
                current_dpd,
                days_late,
            )
            historical_max = max(
                historical_max,
                days_late,
            )

    metrics.current_days_past_due = current_dpd
    metrics.max_days_past_due = historical_max

    return metrics


def _restore_grace_if_fully_settled(
    account: models.Account,
    db: Session,
    as_of_date: date,
):
    if (
        account.balance >= Decimal("0.00")
        and account.acquired_interest <= Decimal("0.00")
        and not crud_credit.has_active_deficiency(
            account.id,
            as_of_date,
            db,
        )
    ):
        account.grace_period_active = True


def evaluate_due_statement(
    statement: models.CreditStatement,
    db: Session,
    evaluated_at: datetime | None = None,
    *,
    recalculate_metrics: bool = True,
):
    if statement.evaluated_at is not None:
        return statement

    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    as_of_date = _business_date(evaluated_at)
    account = statement.linked_account
    metrics = _ensure_metrics(account)

    full_paid_on_time = _paid_on_or_before_due(
        statement.paid_in_full_at,
        statement.due_date,
    )
    minimum_paid_on_time = _paid_on_or_before_due(
        statement.minimum_paid_at,
        statement.due_date,
    )

    if full_paid_on_time:
        metrics.on_time_payments_count = (
            (metrics.on_time_payments_count or 0) + 1
        )

        if account.grace_period_active:
            account.acquired_interest = Decimal("0.00")
        else:
            _post_pending_interest(
                account,
                db,
                statement,
            )

    elif minimum_paid_on_time:
        metrics.on_time_payments_count = (
            (metrics.on_time_payments_count or 0) + 1
        )
        account.grace_period_active = False
        _post_pending_interest(
            account,
            db,
            statement,
        )

    else:
        metrics.total_missed_payments_count = (
            (metrics.total_missed_payments_count or 0) + 1
        )
        account.grace_period_active = False
        _post_pending_interest(
            account,
            db,
            statement,
        )

    statement.evaluated_at = evaluated_at
    statement.status = _current_statement_status(
        statement
    )

    db.flush()

    if recalculate_metrics:
        _recalculate_delinquency_metrics(
            account,
            db,
            as_of_date,
        )

    _restore_grace_if_fully_settled(
        account,
        db,
        as_of_date,
    )

    return statement


def _reconcile_overdue_statements_for_account(
    account: models.Account,
    db: Session,
    as_of_date: date,
    evaluated_at: datetime,
):
    statements = (
        crud_credit.get_due_unevaluated_statements_for_account(
            account.id,
            as_of_date,
            db,
        )
    )

    for statement in statements:
        evaluate_due_statement(
            statement,
            db,
            evaluated_at=evaluated_at,
            recalculate_metrics=False,
        )

    if statements:
        db.flush()

    _recalculate_delinquency_metrics(
        account,
        db,
        as_of_date,
    )


def _apply_payment_to_open_statements(
    statements: list[models.CreditStatement],
    payment_amount: Decimal,
    paid_at: datetime,
) -> bool:
    paid_full_on_time = False

    for statement in statements:
        amount_paid = Decimal(
            statement.amount_paid or Decimal("0.00")
        )
        remaining = max(
            statement.statement_balance - amount_paid,
            Decimal("0.00"),
        )

        if remaining <= Decimal("0.00"):
            continue

        applied = min(
            payment_amount,
            remaining,
        )
        new_amount_paid = _money(
            amount_paid + applied
        )
        statement.amount_paid = new_amount_paid

        if (
            statement.minimum_paid_at is None
            and new_amount_paid >= statement.minimum_payment
        ):
            statement.minimum_paid_at = paid_at

        if (
            statement.paid_in_full_at is None
            and new_amount_paid >= statement.statement_balance
        ):
            statement.paid_in_full_at = paid_at

            if _business_date(paid_at) <= statement.due_date:
                paid_full_on_time = True

        statement.status = _current_statement_status(
            statement
        )

    return paid_full_on_time


def repay_credit_account(
    account: models.Account,
    payment: credit_schemas.CreditRepaymentInput,
    db: Session,
    *,
    now: datetime | None = None,
):
    payment_amount = _money(payment.amount)
    now = now or datetime.now(timezone.utc)
    as_of_date = _business_date(now)

    try:
        # A late payment must not receive a grace waiver merely because
        # the due-date scheduler has not run yet.
        _reconcile_overdue_statements_for_account(
            account,
            db,
            as_of_date,
            now,
        )

        statements = crud_credit.get_unsettled_statements(
            account.id,
            db,
        )

        crud_transaction.deposit_funds(
            account,
            payment_amount,
            db,
        )

        paid_full_on_time = _apply_payment_to_open_statements(
            statements,
            payment_amount,
            now,
        )

        db.flush()

        _recalculate_delinquency_metrics(
            account,
            db,
            as_of_date,
        )

        if account.grace_period_active:
            if paid_full_on_time:
                account.acquired_interest = Decimal("0.00")
            elif not statements and account.balance >= Decimal("0.00"):
                account.acquired_interest = Decimal("0.00")

        _restore_grace_if_fully_settled(
            account,
            db,
            as_of_date,
        )

        db.flush()
        credit_score.recalculate_user_credit_score(
            account.owner_id,
            db,
            commit=False,
        )

        db.commit()
        db.refresh(account)

        latest_statement = crud_credit.get_latest_statement(
            account.id,
            db,
        )

        return credit_schemas.CreditRepaymentResponse(
            account_id=account.id,
            payment_amount=payment_amount,
            balance=_money(account.balance),
            grace_period_active=account.grace_period_active,
            statement_id=(
                latest_statement.id
                if latest_statement is not None
                else None
            ),
            statement_amount_paid=(
                _money(latest_statement.amount_paid)
                if latest_statement is not None
                else None
            ),
            statement_status=(
                latest_statement.status
                if latest_statement is not None
                else None
            ),
        )

    except Exception:
        db.rollback()
        raise


def evaluate_due_statements(
    db: Session,
    as_of_date: date | None = None,
    *,
    commit: bool = True,
):
    as_of_date = as_of_date or _business_date()
    due_statements = crud_credit.get_due_unevaluated_statements(
        as_of_date,
        db,
    )

    evaluated_count = 0
    touched_accounts: set[int] = set()

    for statement in due_statements:
        evaluated = False

        try:
            with db.begin_nested():
                evaluate_due_statement(
                    statement,
                    db,
                    recalculate_metrics=False,
                )
                db.flush()
                evaluated = True

            if evaluated:
                evaluated_count += 1
                touched_accounts.add(statement.account_id)

        except Exception as exc:
            logger.exception(
                "Failed to evaluate credit statement %s: %s",
                statement.id,
                exc,
            )

    for account_id in touched_accounts:
        account = db.get(models.Account, account_id)
        if account is None:
            continue

        _recalculate_delinquency_metrics(
            account,
            db,
            as_of_date,
        )
        _restore_grace_if_fully_settled(
            account,
            db,
            as_of_date,
        )
        db.flush()

        credit_score.recalculate_user_credit_score(
            account.owner_id,
            db,
            commit=False,
        )

    if commit:
        db.commit()

    logger.info(
        "Credit due-date evaluation finished: %s statements evaluated",
        evaluated_count,
    )
    return evaluated_count


def calculate_credit_account_acquired_interest(
    account: models.Account,
    as_of_date: date | None = None,
):
    as_of_date = as_of_date or _business_date()
    last_processed = account.last_interest_accrual_date

    if (
        last_processed is not None
        and last_processed >= as_of_date
    ):
        return account

    if (
        last_processed is not None
        and last_processed < as_of_date - timedelta(days=1)
    ):
        logger.warning(
            "Credit account %s missed daily interest dates between %s and %s; "
            "historical changing balances are unavailable, so missed days "
            "are not fabricated.",
            account.id,
            last_processed,
            as_of_date,
        )

    if account.balance < Decimal("0.00"):
        daily_interest = _money(
            abs(account.balance) * get_daily_interest_rate()
        )
        account.acquired_interest = _money(
            account.acquired_interest + daily_interest
        )

    account.last_interest_accrual_date = as_of_date
    return account


def update_days_past_due_counter(
    account: models.Account,
    db: Session,
    as_of_date: date | None = None,
):
    return _recalculate_delinquency_metrics(
        account,
        db,
        as_of_date or _business_date(),
    )


def calculate_acquired_interest_all_credit_accounts(
    db: Session,
    as_of_date: date | None = None,
):
    as_of_date = as_of_date or _business_date()

    # Reconcile overdue statement facts first. This makes restart/catch-up
    # behavior independent of whether the dedicated due-date job ran.
    evaluate_due_statements(
        db,
        as_of_date,
        commit=False,
    )

    credit_accounts = crud_accounts.get_all_accounts(
        AccountType.CREDIT,
        db,
    )

    success_count = 0

    for account in credit_accounts:
        processed = False

        try:
            with db.begin_nested():
                update_days_past_due_counter(
                    account,
                    db,
                    as_of_date,
                )
                calculate_credit_account_acquired_interest(
                    account,
                    as_of_date,
                )
                db.flush()
                credit_score.recalculate_user_credit_score(
                    account.owner_id,
                    db,
                    commit=False,
                )
                processed = True

            if processed:
                success_count += 1

        except Exception as exc:
            logger.exception(
                "Failed daily credit processing for account %s: %s",
                account.id,
                exc,
            )

    db.commit()
    logger.info(
        "Daily credit processing finished: %s accounts processed",
        success_count,
    )
    return success_count
