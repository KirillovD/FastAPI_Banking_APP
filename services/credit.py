from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import logging

from sqlalchemy.orm import Session

import models
from config import settings
from crud import accounts as crud_accounts
from crud import credit as crud_credit
from crud import transaction as crud_transaction
from enums import AccountType, CreditStatementStatus
from schemas import credit as credit_schemas
from services import credit_score


MONEY_QUANTUM = Decimal("0.01")
logger = logging.getLogger(__name__)


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANTUM)


def _normalized_apr() -> Decimal:
    apr = Decimal(settings.credit_card_default_apr)

    # Backward-compatible with an older "20 means 20%" local setting.
    # Portfolio V2 documents 0.20 as the preferred representation.
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


def calculate_min_credit_account_payment(account: models.Account) -> Decimal:
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

    as_of_date = as_of_date or datetime.now(timezone.utc).date()

    existing = crud_credit.get_statement_for_period(
        account.id,
        as_of_date,
        db,
    )
    if existing:
        return existing

    latest = crud_credit.get_latest_statement(account.id, db)

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
    return statement


def create_monthly_statements(
    db: Session,
    as_of_date: date | None = None,
):
    as_of_date = as_of_date or datetime.now(timezone.utc).date()
    credit_accounts = crud_accounts.get_all_accounts(
        AccountType.CREDIT,
        db,
    )

    created_count = 0

    for account in credit_accounts:
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

                if statement is not None and before is None:
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
    metrics = account.credit_account_metrics

    metrics_payload = {
        "on_time_payments_count": (
            metrics.on_time_payments_count if metrics else 0
        ),
        "total_missed_payments_count": (
            metrics.total_missed_payments_count if metrics else 0
        ),
        "current_days_past_due": (
            metrics.current_days_past_due if metrics else 0
        ),
        "max_days_past_due": (
            metrics.max_days_past_due if metrics else 0
        ),
        "rapid_limit_depletion_count": (
            metrics.rapid_limit_depletion_count if metrics else 0
        ),
    }

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
        "metrics": metrics_payload,
        "current_statement": latest_statement,
    }


def _post_pending_interest(
    account: models.Account,
    statement: models.CreditStatement | None = None,
) -> Decimal:
    amount = _money(account.acquired_interest)

    if amount <= Decimal("0.00"):
        account.acquired_interest = Decimal("0.00")
        return Decimal("0.00")

    crud_transaction.withdraw_funds(account, amount)
    account.acquired_interest = Decimal("0.00")

    if statement is not None:
        statement.interest_charged = _money(
            statement.interest_charged + amount
        )

    return amount


def add_acquired_interest_to_balance(
    account: models.Account,
):
    if account.grace_period_active:
        import exceptions

        raise exceptions.GraceNoInterest()

    _post_pending_interest(account)
    return account


def repay_credit_account(
    account: models.Account,
    payment: credit_schemas.CreditRepaymentInput,
    db: Session,
):
    payment_amount = _money(payment.amount)
    now = datetime.now(timezone.utc)

    latest_statement = crud_credit.get_latest_statement(
        account.id,
        db,
    )

    # Once grace has already been lost, pending interest is owed.
    # Post it before principal repayment so it cannot disappear.
    if not account.grace_period_active:
        _post_pending_interest(
            account,
            latest_statement,
        )

    repayment_statement = crud_credit.get_repayment_statement(
        account.id,
        db,
    )

    crud_transaction.deposit_funds(
        account,
        payment_amount,
    )

    if repayment_statement is not None:
        remaining_statement = _money(
            max(
                repayment_statement.statement_balance
                - repayment_statement.amount_paid,
                Decimal("0.00"),
            )
        )
        applied_to_statement = min(
            payment_amount,
            remaining_statement,
        )

        repayment_statement.amount_paid = _money(
            repayment_statement.amount_paid
            + applied_to_statement
        )

        if (
            repayment_statement.minimum_paid_at is None
            and repayment_statement.amount_paid
            >= repayment_statement.minimum_payment
        ):
            repayment_statement.minimum_paid_at = now

        if (
            repayment_statement.paid_in_full_at is None
            and repayment_statement.amount_paid
            >= repayment_statement.statement_balance
        ):
            repayment_statement.paid_in_full_at = now

        if (
            repayment_statement.amount_paid
            >= repayment_statement.statement_balance
        ):
            repayment_statement.status = (
                CreditStatementStatus.PAID_IN_FULL
            )
        elif (
            repayment_statement.amount_paid
            >= repayment_statement.minimum_payment
        ):
            repayment_statement.status = (
                CreditStatementStatus.MINIMUM_PAID
            )

        if (
            repayment_statement.amount_paid
            >= repayment_statement.minimum_payment
            and account.credit_account_metrics is not None
        ):
            account.credit_account_metrics.current_days_past_due = 0

    # Original grace behavior: if grace was still active and the
    # statement obligation is fully paid, pending conditional interest
    # is waived. New purchases can begin accruing again the next day.
    if account.grace_period_active:
        statement_paid_in_full_on_time = (
            repayment_statement is not None
            and repayment_statement.amount_paid
            >= repayment_statement.statement_balance
            and now.date() <= repayment_statement.due_date
        )

        if statement_paid_in_full_on_time or (
            repayment_statement is None
            and account.balance >= Decimal("0.00")
        ):
            account.acquired_interest = Decimal("0.00")

    # If grace had already been lost, it only comes back once all
    # posted debt is settled and there is no active delinquency.
    if not account.grace_period_active:
        current_past_due = (
            crud_credit.get_current_past_due_statement(
                account.id,
                db,
            )
        )

        if (
            account.balance >= Decimal("0.00")
            and account.acquired_interest <= Decimal("0.00")
            and current_past_due is None
        ):
            account.grace_period_active = True

    db.flush()
    credit_score.recalculate_user_credit_score(
        account.owner_id,
        db,
        commit=False,
    )

    db.commit()
    db.refresh(account)

    if repayment_statement is not None:
        db.refresh(repayment_statement)

    return credit_schemas.CreditRepaymentResponse(
        account_id=account.id,
        payment_amount=payment_amount,
        balance=_money(account.balance),
        grace_period_active=account.grace_period_active,
        statement_id=(
            repayment_statement.id
            if repayment_statement is not None
            else None
        ),
        statement_amount_paid=(
            _money(repayment_statement.amount_paid)
            if repayment_statement is not None
            else None
        ),
        statement_status=(
            repayment_statement.status
            if repayment_statement is not None
            else None
        ),
    )


def _paid_on_or_before_due(
    paid_at: datetime | None,
    due_date: date,
) -> bool:
    return (
        paid_at is not None
        and paid_at.date() <= due_date
    )


def evaluate_due_statement(
    statement: models.CreditStatement,
    db: Session,
    evaluated_at: datetime | None = None,
):
    if statement.evaluated_at is not None:
        return statement

    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    account = statement.linked_account
    metrics = account.credit_account_metrics

    if metrics is None:
        metrics = models.CreditAccountMetrics()
        account.credit_account_metrics = metrics

    full_paid_on_time = _paid_on_or_before_due(
        statement.paid_in_full_at,
        statement.due_date,
    )
    minimum_paid_on_time = _paid_on_or_before_due(
        statement.minimum_paid_at,
        statement.due_date,
    )

    if full_paid_on_time:
        statement.status = CreditStatementStatus.PAID_IN_FULL
        metrics.on_time_payments_count += 1
        metrics.current_days_past_due = 0

        if account.grace_period_active:
            account.acquired_interest = Decimal("0.00")
        else:
            _post_pending_interest(account, statement)

            if (
                account.balance >= Decimal("0.00")
                and account.acquired_interest <= Decimal("0.00")
            ):
                account.grace_period_active = True

    elif minimum_paid_on_time:
        statement.status = CreditStatementStatus.MINIMUM_PAID
        metrics.on_time_payments_count += 1
        metrics.current_days_past_due = 0

        account.grace_period_active = False
        _post_pending_interest(account, statement)

    else:
        metrics.total_missed_payments_count += 1
        metrics.current_days_past_due = 0

        account.grace_period_active = False
        _post_pending_interest(account, statement)

        # The obligation was missed by the due date, but a scheduler
        # that runs after a late payment should still reflect the
        # statement's current cured/settled state.
        if statement.amount_paid >= statement.statement_balance:
            statement.status = CreditStatementStatus.PAID_IN_FULL

            if account.balance >= Decimal("0.00"):
                account.grace_period_active = True
        elif statement.amount_paid >= statement.minimum_payment:
            statement.status = CreditStatementStatus.MINIMUM_PAID
        else:
            statement.status = CreditStatementStatus.PAST_DUE

    statement.evaluated_at = evaluated_at
    return statement


def evaluate_due_statements(
    db: Session,
    as_of_date: date | None = None,
):
    as_of_date = as_of_date or datetime.now(timezone.utc).date()
    due_statements = crud_credit.get_due_unevaluated_statements(
        as_of_date,
        db,
    )

    evaluated_count = 0

    for statement in due_statements:
        try:
            with db.begin_nested():
                evaluate_due_statement(statement, db)
                db.flush()
                credit_score.recalculate_user_credit_score(
                    statement.linked_account.owner_id,
                    db,
                    commit=False,
                )
                evaluated_count += 1
        except Exception as exc:
            logger.exception(
                "Failed to evaluate credit statement %s: %s",
                statement.id,
                exc,
            )

    db.commit()
    logger.info(
        "Credit due-date evaluation finished: %s statements evaluated",
        evaluated_count,
    )
    return evaluated_count


def calculate_credit_account_acquired_interest(
    account: models.Account,
):
    if account.balance >= Decimal("0.00"):
        return account

    daily_interest = _money(
        abs(account.balance) * get_daily_interest_rate()
    )

    account.acquired_interest = _money(
        account.acquired_interest + daily_interest
    )

    return account


def update_days_past_due_counter(
    account: models.Account,
    db: Session,
):
    metrics = account.credit_account_metrics

    if metrics is None:
        metrics = models.CreditAccountMetrics()
        account.credit_account_metrics = metrics

    past_due_statement = (
        crud_credit.get_current_past_due_statement(
            account.id,
            db,
        )
    )

    if past_due_statement is None:
        metrics.current_days_past_due = 0
        return metrics

    metrics.current_days_past_due += 1

    if (
        metrics.current_days_past_due
        > metrics.max_days_past_due
    ):
        metrics.max_days_past_due = (
            metrics.current_days_past_due
        )

    return metrics


def calculate_acquired_interest_all_credit_accounts(
    db: Session,
):
    credit_accounts = crud_accounts.get_all_accounts(
        AccountType.CREDIT,
        db,
    )

    success_count = 0

    for account in credit_accounts:
        try:
            with db.begin_nested():
                update_days_past_due_counter(account, db)
                calculate_credit_account_acquired_interest(
                    account
                )
                db.flush()
                credit_score.recalculate_user_credit_score(
                    account.owner_id,
                    db,
                    commit=False,
                )
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
