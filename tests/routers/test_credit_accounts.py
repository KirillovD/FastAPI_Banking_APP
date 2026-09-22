from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import models
import services.credit as credit_services
from enums import AccountType, CreditStatementStatus
from tests.conftest import (
    TestingSessionLocal,
    create_account,
    create_credit_card,
    create_user_and_login,
)


def _statement(
    account_id: int,
    *,
    balance: str = "300.00",
    minimum: str = "30.00",
    amount_paid: str = "0.00",
    status=CreditStatementStatus.OPEN,
    due_date=date(2026, 10, 15),
    minimum_paid_at=None,
    paid_in_full_at=None,
):
    return models.CreditStatement(
        account_id=account_id,
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
        due_date=due_date,
        statement_balance=Decimal(balance),
        minimum_payment=Decimal(minimum),
        amount_paid=Decimal(amount_paid),
        status=status,
        minimum_paid_at=minimum_paid_at,
        paid_in_full_at=paid_in_full_at,
        interest_charged=Decimal("0.00"),
    )


def _load_account(account_id: int):
    db = TestingSessionLocal()
    account = db.get(models.Account, account_id)
    return db, account


def test_credit_dashboard_is_owner_only(client, auth_headers):
    card = create_credit_card(client, auth_headers)

    response = client.get(
        f"/credit-accounts/{card['linked_acc_id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == card["linked_acc_id"]
    assert Decimal(str(data["credit_limit"])) == Decimal("500.00")
    assert data["metrics"]["on_time_payments_count"] == 0

    other_headers = create_user_and_login(
        client,
        "mary@example.com",
        "Mary",
    )
    denied = client.get(
        f"/credit-accounts/{card['linked_acc_id']}",
        headers=other_headers,
    )

    assert denied.status_code == 403


def test_credit_endpoint_rejects_non_credit_account(
    client,
    auth_headers,
):
    account = create_account(
        client,
        auth_headers,
        "checking",
        100,
    )

    response = client.get(
        f"/credit-accounts/{account['id']}",
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_month_end_statement_captures_debt_and_due_date(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        account.balance = Decimal("-300.00")
        db.commit()

        created = credit_services.create_monthly_statements(
            db,
            date(2026, 9, 30),
        )

        assert created == 1

        statement = (
            db.query(models.CreditStatement)
            .filter(
                models.CreditStatement.account_id
                == account.id
            )
            .one()
        )

        assert statement.statement_balance == Decimal("300.00")
        assert statement.minimum_payment <= Decimal("300.00")
        assert statement.due_date == date(2026, 10, 15)

    response = client.get(
        f"/credit-accounts/{card['linked_acc_id']}/statements",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_no_statement_is_created_without_credit_debt(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)

    with TestingSessionLocal() as db:
        created = credit_services.create_monthly_statements(
            db,
            date(2026, 9, 30),
        )

        assert created == 0
        assert db.query(models.CreditStatement).count() == 0


def test_small_positive_repayment_is_allowed(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        account.balance = Decimal("-300.00")
        statement = _statement(account.id)
        db.add(statement)
        db.commit()

    response = client.post(
        f"/credit-accounts/{card['linked_acc_id']}/payments",
        json={"amount": 5},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["payment_amount"])) == Decimal("5.00")
    assert Decimal(str(data["balance"])) == Decimal("-295.00")
    assert Decimal(str(data["statement_amount_paid"])) == Decimal("5.00")
    assert data["statement_status"] == "open"


def test_full_statement_payment_preserves_grace_and_waives_interest(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        account.balance = Decimal("-400.00")
        account.acquired_interest = Decimal("20.00")
        account.grace_period_active = True

        statement = _statement(account.id)
        db.add(statement)
        db.commit()

    response = client.post(
        f"/credit-accounts/{card['linked_acc_id']}/payments",
        json={"amount": 300},
        headers=auth_headers,
    )

    assert response.status_code == 200

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        statement = (
            db.query(models.CreditStatement)
            .filter_by(account_id=account.id)
            .one()
        )

        assert account.balance == Decimal("-100.00")
        assert account.grace_period_active is True
        assert account.acquired_interest == Decimal("0.00")
        assert statement.amount_paid == Decimal("300.00")
        assert statement.status == CreditStatementStatus.PAID_IN_FULL


def test_repayment_after_grace_loss_posts_pending_interest_first(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        account.balance = Decimal("-100.00")
        account.acquired_interest = Decimal("10.00")
        account.grace_period_active = False
        db.commit()

    response = client.post(
        f"/credit-accounts/{card['linked_acc_id']}/payments",
        json={"amount": 110},
        headers=auth_headers,
    )

    assert response.status_code == 200

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        assert account.balance == Decimal("0.00")
        assert account.acquired_interest == Decimal("0.00")
        assert account.grace_period_active is True


def test_minimum_paid_on_time_loses_grace_without_delinquency(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)

    due = date(2026, 10, 15)
    paid_at = datetime(2026, 10, 10, tzinfo=timezone.utc)

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        account.balance = Decimal("-270.00")
        account.acquired_interest = Decimal("10.00")
        statement = _statement(
            account.id,
            amount_paid="30.00",
            status=CreditStatementStatus.MINIMUM_PAID,
            due_date=due,
            minimum_paid_at=paid_at,
        )
        db.add(statement)
        db.commit()

        credit_services.evaluate_due_statements(
            db,
            due + timedelta(days=1),
        )

        db.refresh(account)
        db.refresh(statement)
        metrics = account.credit_account_metrics

        assert statement.status == CreditStatementStatus.MINIMUM_PAID
        assert statement.interest_charged == Decimal("10.00")
        assert account.balance == Decimal("-280.00")
        assert account.grace_period_active is False
        assert metrics.on_time_payments_count == 1
        assert metrics.total_missed_payments_count == 0
        assert metrics.current_days_past_due == 0


def test_missed_minimum_creates_true_delinquency_and_dpd(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)
    due = date(2026, 10, 15)

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        account.balance = Decimal("-300.00")
        account.acquired_interest = Decimal("10.00")
        statement = _statement(
            account.id,
            due_date=due,
        )
        db.add(statement)
        db.commit()

        credit_services.evaluate_due_statements(
            db,
            due + timedelta(days=1),
        )
        credit_services.calculate_acquired_interest_all_credit_accounts(
            db
        )

        db.refresh(account)
        db.refresh(statement)
        metrics = account.credit_account_metrics

        assert statement.status == CreditStatementStatus.PAST_DUE
        assert statement.interest_charged == Decimal("10.00")
        assert metrics.total_missed_payments_count == 1
        assert metrics.on_time_payments_count == 0
        assert metrics.current_days_past_due == 1
        assert metrics.max_days_past_due == 1


def test_full_payment_on_time_waives_pending_interest_at_due_date(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)
    due = date(2026, 10, 15)
    paid_at = datetime(2026, 10, 10, tzinfo=timezone.utc)

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        account.balance = Decimal("-100.00")
        account.acquired_interest = Decimal("20.00")
        account.grace_period_active = True

        statement = _statement(
            account.id,
            amount_paid="300.00",
            status=CreditStatementStatus.PAID_IN_FULL,
            due_date=due,
            minimum_paid_at=paid_at,
            paid_in_full_at=paid_at,
        )
        db.add(statement)
        db.commit()

        credit_services.evaluate_due_statements(
            db,
            due + timedelta(days=1),
        )

        db.refresh(account)
        metrics = account.credit_account_metrics

        assert account.acquired_interest == Decimal("0.00")
        assert account.grace_period_active is True
        assert metrics.on_time_payments_count == 1
        assert metrics.total_missed_payments_count == 0



def test_late_full_payment_does_not_waive_pending_interest(
    client,
    auth_headers,
    monkeypatch,
):
    card = create_credit_card(client, auth_headers)

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        account.balance = Decimal("-300.00")
        account.acquired_interest = Decimal("20.00")

        late_statement = _statement(
            account.id,
            due_date=date(2026, 1, 15),
        )
        db.add(late_statement)
        db.commit()

    response = client.post(
        f"/credit-accounts/{card['linked_acc_id']}/payments",
        json={"amount": 300},
        headers=auth_headers,
    )

    assert response.status_code == 200

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        assert account.acquired_interest == Decimal("20.00")



def test_minimum_paid_statement_never_accumulates_dpd(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)
    due = date(2026, 10, 15)
    paid_at = datetime(2026, 10, 10, tzinfo=timezone.utc)

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        account.balance = Decimal("-270.00")

        statement = _statement(
            account.id,
            amount_paid="30.00",
            status=CreditStatementStatus.MINIMUM_PAID,
            due_date=due,
            minimum_paid_at=paid_at,
        )
        db.add(statement)
        db.commit()

        credit_services.evaluate_due_statements(
            db,
            due + timedelta(days=1),
        )
        credit_services.calculate_acquired_interest_all_credit_accounts(db)
        credit_services.calculate_acquired_interest_all_credit_accounts(db)

        db.refresh(account)
        metrics = account.credit_account_metrics

        assert metrics.current_days_past_due == 0
        assert metrics.max_days_past_due == 0
        assert metrics.total_missed_payments_count == 0
