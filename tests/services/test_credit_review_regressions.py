import os
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault(
    "ENCRYPTION_KEY",
    "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
)
os.environ.setdefault("CREDIT_CARD_MIN_PAYMENT_AMOUNT", "30")
os.environ.setdefault("CREDIT_CARD_MIN_PAYMENT_PERCENT", "0.03")
os.environ.setdefault("CREDIT_CARD_DEFAULT_APR", "0.20")

import models
from enums import AccountType, CreditStatementStatus
from schemas.credit import CreditRepaymentInput
from services import credit, credit_score


@pytest.fixture()
def db_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'credit-review.db'}",
        connect_args={"check_same_thread": False},
    )
    models.Base.metadata.create_all(bind=engine)

    factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    yield factory

    engine.dispose()


def _create_credit_account(
    db,
    *,
    email: str = "user@example.com",
    balance: str = "0.00",
    acquired_interest: str = "0.00",
    grace: bool = True,
):
    user = models.User(
        email=email,
        first_name="Test",
        last_name="User",
        password="hashed",
    )
    account = models.Account(
        owner=user,
        type=AccountType.CREDIT,
        iban=f"DE{abs(hash(email)) % 10**20:020d}",
        balance=Decimal(balance),
        limit=Decimal("500.00"),
        acquired_interest=Decimal(acquired_interest),
        grace_period_active=grace,
    )
    account.credit_account_metrics = models.CreditAccountMetrics(
        on_time_payments_count=0,
        total_missed_payments_count=0,
        current_days_past_due=0,
        max_days_past_due=0,
        rapid_limit_depletion_count=0,
    )
    db.add(user)
    db.add(account)
    db.commit()
    db.refresh(account)
    return user, account


def _statement(
    account_id: int,
    *,
    period_end: date,
    due_date: date,
    balance: str = "300.00",
    minimum: str = "30.00",
    amount_paid: str = "0.00",
    status=CreditStatementStatus.OPEN,
    minimum_paid_at=None,
    paid_in_full_at=None,
    evaluated_at=None,
):
    return models.CreditStatement(
        account_id=account_id,
        period_start=period_end.replace(day=1),
        period_end=period_end,
        due_date=due_date,
        statement_balance=Decimal(balance),
        minimum_payment=Decimal(minimum),
        amount_paid=Decimal(amount_paid),
        status=status,
        minimum_paid_at=minimum_paid_at,
        paid_in_full_at=paid_in_full_at,
        evaluated_at=evaluated_at,
        interest_charged=Decimal("0.00"),
    )


def test_on_time_minimum_then_late_full_settlement_keeps_current_state_correct(
    db_factory,
):
    with db_factory() as db:
        _, account = _create_credit_account(
            db,
            balance="-270.00",
            acquired_interest="20.00",
            grace=True,
        )
        statement = _statement(
            account.id,
            period_end=date(2026, 8, 31),
            due_date=date(2026, 9, 15),
            amount_paid="30.00",
            status=CreditStatementStatus.MINIMUM_PAID,
            minimum_paid_at=datetime(
                2026, 9, 10, 12, tzinfo=timezone.utc
            ),
        )
        db.add(statement)
        db.commit()

        result = credit.repay_credit_account(
            account,
            CreditRepaymentInput(amount="290.00"),
            db,
            now=datetime(
                2026, 9, 16, 12, tzinfo=timezone.utc
            ),
        )

        db.refresh(statement)
        metrics = account.credit_account_metrics

        assert account.balance == Decimal("0.00")
        assert account.acquired_interest == Decimal("0.00")
        assert account.grace_period_active is True
        assert statement.status == CreditStatementStatus.PAID_IN_FULL
        assert statement.interest_charged == Decimal("20.00")
        assert metrics.on_time_payments_count == 1
        assert metrics.total_missed_payments_count == 0
        assert result.statement_status == CreditStatementStatus.PAID_IN_FULL


def test_second_late_payment_cannot_erase_earned_interest(
    db_factory,
):
    with db_factory() as db:
        _, account = _create_credit_account(
            db,
            balance="-300.00",
            acquired_interest="20.00",
            grace=True,
        )
        statement = _statement(
            account.id,
            period_end=date(2026, 8, 31),
            due_date=date(2026, 9, 15),
        )
        db.add(statement)
        db.commit()

        late_time = datetime(
            2026, 9, 16, 12, tzinfo=timezone.utc
        )

        credit.repay_credit_account(
            account,
            CreditRepaymentInput(amount="300.00"),
            db,
            now=late_time,
        )

        assert account.balance == Decimal("-20.00")
        assert account.acquired_interest == Decimal("0.00")
        assert account.grace_period_active is False

        credit.repay_credit_account(
            account,
            CreditRepaymentInput(amount="0.01"),
            db,
            now=late_time,
        )

        db.refresh(statement)
        assert account.balance == Decimal("-19.99")
        assert account.acquired_interest == Decimal("0.00")
        assert account.grace_period_active is False
        assert statement.interest_charged == Decimal("20.00")
        assert account.credit_account_metrics.total_missed_payments_count == 1


def test_full_payoff_updates_overlapping_statement_snapshots(
    db_factory,
):
    with db_factory() as db:
        _, account = _create_credit_account(
            db,
            balance="-300.00",
            acquired_interest="5.00",
            grace=True,
        )
        older = _statement(
            account.id,
            period_end=date(2026, 8, 31),
            due_date=date(2026, 10, 15),
        )
        newer = _statement(
            account.id,
            period_end=date(2026, 9, 30),
            due_date=date(2026, 11, 15),
        )
        db.add_all([older, newer])
        db.commit()

        credit.repay_credit_account(
            account,
            CreditRepaymentInput(amount="300.00"),
            db,
            now=datetime(
                2026, 10, 10, 12, tzinfo=timezone.utc
            ),
        )

        db.refresh(older)
        db.refresh(newer)

        assert account.balance == Decimal("0.00")
        assert older.amount_paid == Decimal("300.00")
        assert newer.amount_paid == Decimal("300.00")
        assert older.status == CreditStatementStatus.PAID_IN_FULL
        assert newer.status == CreditStatementStatus.PAID_IN_FULL

        credit.evaluate_due_statements(
            db,
            as_of_date=date(2026, 11, 16),
        )

        db.refresh(older)
        db.refresh(newer)
        metrics = account.credit_account_metrics

        assert older.status == CreditStatementStatus.PAID_IN_FULL
        assert newer.status == CreditStatementStatus.PAID_IN_FULL
        assert metrics.total_missed_payments_count == 0
        assert metrics.on_time_payments_count == 2


def test_curing_last_past_due_obligation_restores_grace(
    db_factory,
):
    with db_factory() as db:
        _, account = _create_credit_account(
            db,
            balance="-100.00",
            grace=False,
        )
        statement = _statement(
            account.id,
            period_end=date(2026, 8, 31),
            due_date=date(2026, 9, 15),
            status=CreditStatementStatus.PAST_DUE,
            evaluated_at=datetime(
                2026, 9, 16, 1, tzinfo=timezone.utc
            ),
        )
        db.add(statement)
        db.commit()

        credit.repay_credit_account(
            account,
            CreditRepaymentInput(amount="100.00"),
            db,
            now=datetime(
                2026, 9, 22, 12, tzinfo=timezone.utc
            ),
        )

        db.refresh(statement)

        assert account.balance == Decimal("0.00")
        assert account.grace_period_active is True
        assert statement.status == CreditStatementStatus.PAID_IN_FULL
        assert account.credit_account_metrics.current_days_past_due == 0
        assert account.credit_account_metrics.max_days_past_due >= 7


def test_newer_statement_evaluation_does_not_reset_older_dpd(
    db_factory,
):
    with db_factory() as db:
        _, account = _create_credit_account(
            db,
            balance="-200.00",
            grace=False,
        )
        old = _statement(
            account.id,
            period_end=date(2026, 7, 31),
            due_date=date(2026, 9, 1),
            balance="100.00",
            status=CreditStatementStatus.PAST_DUE,
            evaluated_at=datetime(
                2026, 9, 2, 1, tzinfo=timezone.utc
            ),
        )
        new = _statement(
            account.id,
            period_end=date(2026, 8, 31),
            due_date=date(2026, 9, 15),
            balance="200.00",
        )
        db.add_all([old, new])
        db.commit()

        credit.evaluate_due_statements(
            db,
            as_of_date=date(2026, 9, 22),
        )

        metrics = account.credit_account_metrics
        assert metrics.current_days_past_due == 21
        assert metrics.max_days_past_due >= 21


def test_late_minimum_cure_records_historical_dpd_without_daily_runs(
    db_factory,
):
    with db_factory() as db:
        _, account = _create_credit_account(
            db,
            balance="-100.00",
            grace=True,
        )
        statement = _statement(
            account.id,
            period_end=date(2026, 8, 31),
            due_date=date(2026, 9, 15),
            balance="100.00",
            minimum="30.00",
        )
        db.add(statement)
        db.commit()

        credit.repay_credit_account(
            account,
            CreditRepaymentInput(amount="30.00"),
            db,
            now=datetime(
                2026, 9, 21, 12, tzinfo=timezone.utc
            ),
        )

        metrics = account.credit_account_metrics
        assert metrics.total_missed_payments_count == 1
        assert metrics.current_days_past_due == 0
        assert metrics.max_days_past_due == 6


def test_payment_in_last_minute_of_due_date_remains_on_time(
    db_factory,
):
    with db_factory() as db:
        _, account = _create_credit_account(
            db,
            balance="-100.00",
            acquired_interest="10.00",
            grace=True,
        )
        statement = _statement(
            account.id,
            period_end=date(2026, 8, 31),
            due_date=date(2026, 9, 15),
            balance="100.00",
        )
        db.add(statement)
        db.commit()

        # 21:59:30 UTC == 23:59:30 Europe/Berlin (CEST).
        credit.repay_credit_account(
            account,
            CreditRepaymentInput(amount="100.00"),
            db,
            now=datetime(
                2026, 9, 15, 21, 59, 30,
                tzinfo=timezone.utc,
            ),
        )

        credit.evaluate_due_statements(
            db,
            as_of_date=date(2026, 9, 16),
        )

        db.refresh(statement)
        metrics = account.credit_account_metrics

        assert statement.status == CreditStatementStatus.PAID_IN_FULL
        assert metrics.on_time_payments_count == 1
        assert metrics.total_missed_payments_count == 0
        assert account.acquired_interest == Decimal("0.00")
        assert account.grace_period_active is True


def test_daily_credit_processing_is_idempotent_for_same_business_date(
    db_factory,
):
    with db_factory() as db:
        _, account = _create_credit_account(
            db,
            balance="-100.00",
        )

        credit.calculate_acquired_interest_all_credit_accounts(
            db,
            as_of_date=date(2026, 9, 20),
        )
        first_interest = account.acquired_interest

        credit.calculate_acquired_interest_all_credit_accounts(
            db,
            as_of_date=date(2026, 9, 20),
        )

        assert account.acquired_interest == first_interest
        assert account.last_interest_accrual_date == date(2026, 9, 20)


def test_daily_processing_reconciles_missed_due_date_job(
    db_factory,
):
    with db_factory() as db:
        _, account = _create_credit_account(
            db,
            balance="-100.00",
            grace=True,
        )
        statement = _statement(
            account.id,
            period_end=date(2026, 8, 31),
            due_date=date(2026, 9, 15),
            balance="100.00",
        )
        db.add(statement)
        db.commit()

        credit.calculate_acquired_interest_all_credit_accounts(
            db,
            as_of_date=date(2026, 9, 20),
        )

        db.refresh(statement)
        metrics = account.credit_account_metrics

        assert statement.evaluated_at is not None
        assert statement.status == CreditStatementStatus.PAST_DUE
        assert metrics.total_missed_payments_count == 1
        assert metrics.current_days_past_due == 5
        assert account.grace_period_active is False


def test_statement_helper_is_replay_safe_before_commit(
    db_factory,
):
    with db_factory() as db:
        _, account = _create_credit_account(
            db,
            balance="-100.00",
        )

        first = credit.create_statement_for_account(
            account,
            db,
            date(2026, 9, 30),
        )
        second = credit.create_statement_for_account(
            account,
            db,
            date(2026, 9, 30),
        )

        assert first.id == second.id
        assert (
            db.query(models.CreditStatement)
            .filter_by(account_id=account.id)
            .count()
            == 1
        )


def test_statement_batch_does_not_count_rolled_back_statement(
    db_factory,
):
    with db_factory() as db:
        _, first_account = _create_credit_account(
            db,
            email="one@example.com",
            balance="-100.00",
        )
        _, second_account = _create_credit_account(
            db,
            email="two@example.com",
            balance="-100.00",
        )

        failed_account_id = first_account.id

        def fail_first_statement(session, flush_context, instances):
            if any(
                isinstance(item, models.CreditStatement)
                and item.account_id == failed_account_id
                for item in session.new
            ):
                raise RuntimeError("injected statement flush failure")

        event.listen(db, "before_flush", fail_first_statement)

        created = credit.create_monthly_statements(
            db,
            date(2026, 9, 30),
        )

        event.remove(db, "before_flush", fail_first_statement)

        assert created == 1
        rows = db.query(models.CreditStatement).all()
        assert len(rows) == 1
        assert rows[0].account_id == second_account.id


def test_score_handles_loaded_naive_and_new_aware_credit_timestamps(
    db_factory,
):
    with db_factory() as db:
        user, first_account = _create_credit_account(
            db,
            balance="-400.00",
        )
        user_id = user.id
        db.commit()

    with db_factory() as db:
        user = db.get(models.User, user_id)
        old_account = (
            db.query(models.Account)
            .filter_by(owner_id=user_id)
            .one()
        )
        assert old_account.created_at.tzinfo is None

        new_account = models.Account(
            owner_id=user_id,
            type=AccountType.CREDIT,
            iban="DE9999999999999999999999",
            balance=Decimal("0.00"),
            limit=Decimal("500.00"),
        )
        new_account.credit_account_metrics = models.CreditAccountMetrics(
            on_time_payments_count=0,
            total_missed_payments_count=0,
            current_days_past_due=0,
            max_days_past_due=0,
            rapid_limit_depletion_count=0,
        )
        db.add(new_account)
        db.flush()

        result = credit_score.recalculate_user_credit_score(
            user_id,
            db,
            commit=False,
        )

        assert 300 <= result.score <= 850
