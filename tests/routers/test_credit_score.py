from datetime import date
from decimal import Decimal

import models
from enums import CreditStatementStatus
from services import credit as credit_services
from tests.conftest import (
    TestingSessionLocal,
    create_credit_card,
)


def _score(client, headers):
    response = client.get(
        "/credit-score/",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def _purchase(
    client,
    headers,
    card,
    amount,
    *,
    mcc_code="5399",
    merchant_name="Amazon.de",
):
    response = client.post(
        "/payments/",
        json={
            "amount": amount,
            "terminal_data": {
                "merchant_name": merchant_name,
                "card_number": card["number"],
                "payment_type": "pos",
                "mcc_code": mcc_code,
            },
            "pin_block": "1234",
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_score_endpoint_starts_from_existing_500_baseline(
    client,
    auth_headers,
):
    data = _score(client, auth_headers)

    assert data["score"] == 500
    assert data["baseline"] == 500
    assert data["range_min"] == 300
    assert data["range_max"] == 850
    assert data["label"] == "synthetic_demo_score"
    assert len(data["factors"]) == 6


def test_moderate_credit_use_improves_utilization_factor(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)

    _purchase(
        client,
        auth_headers,
        card,
        100,
    )

    data = _score(client, auth_headers)
    factors = {
        factor["name"]: factor
        for factor in data["factors"]
    }

    assert factors["credit_utilization"]["impact"] == 40
    assert data["score"] == 540

    with TestingSessionLocal() as db:
        user = (
            db.query(models.User)
            .filter(models.User.email == "john@example.com")
            .one()
        )
        assert user.credit_score == 540


def test_rapid_limit_depletion_event_is_recorded(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)

    _purchase(
        client,
        auth_headers,
        card,
        400,
    )

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        assert (
            account.credit_account_metrics
            .rapid_limit_depletion_count
            == 1
        )

    data = _score(client, auth_headers)
    factors = {
        factor["name"]: factor
        for factor in data["factors"]
    }

    assert factors["credit_utilization"]["impact"] == -60
    assert factors["rapid_limit_depletion"]["impact"] == -10


def test_repayment_can_improve_score_by_lowering_utilization(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)
    _purchase(
        client,
        auth_headers,
        card,
        400,
    )
    before = _score(client, auth_headers)["score"]

    repayment = client.post(
        f"/credit-accounts/{card['linked_acc_id']}/payments",
        json={"amount": 300},
        headers=auth_headers,
    )
    assert repayment.status_code == 200

    after = _score(client, auth_headers)["score"]

    assert after > before


def test_gambling_pattern_is_small_bounded_behavioral_factor(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)

    _purchase(
        client,
        auth_headers,
        card,
        50,
        mcc_code="7995",
        merchant_name="Tipico",
    )

    data = _score(client, auth_headers)
    factors = {
        factor["name"]: factor
        for factor in data["factors"]
    }

    assert factors["financial_behavior"]["impact"] == -25
    assert factors["payment_history"]["impact"] == 0
    assert factors["delinquency"]["impact"] == 0


def test_payment_history_dominates_behavioral_factor(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        account.credit_account_metrics.on_time_payments_count = 6
        account.credit_account_metrics.total_missed_payments_count = 0
        db.commit()

    _purchase(
        client,
        auth_headers,
        card,
        25,
        mcc_code="7995",
        merchant_name="Tipico",
    )

    data = _score(client, auth_headers)
    factors = {
        factor["name"]: factor
        for factor in data["factors"]
    }

    assert factors["payment_history"]["impact"] == 120
    assert factors["financial_behavior"]["impact"] == -25
    assert data["score"] > 500



def test_missed_statement_due_date_recalculates_stored_score(
    client,
    auth_headers,
):
    card = create_credit_card(client, auth_headers)
    before = _score(client, auth_headers)["score"]

    with TestingSessionLocal() as db:
        account = db.get(
            models.Account,
            card["linked_acc_id"],
        )
        account.balance = Decimal("-100.00")

        statement = models.CreditStatement(
            account_id=account.id,
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            due_date=date(2026, 9, 15),
            statement_balance=Decimal("100.00"),
            minimum_payment=Decimal("30.00"),
            amount_paid=Decimal("0.00"),
            status=CreditStatementStatus.OPEN,
            interest_charged=Decimal("0.00"),
        )
        db.add(statement)
        db.commit()

        credit_services.evaluate_due_statements(
            db,
            date(2026, 9, 15),
        )

        user = (
            db.query(models.User)
            .filter(models.User.email == "john@example.com")
            .one()
        )
        after = user.credit_score

    assert after < before


def test_dpd_progression_can_reduce_score_further(
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

        statement = models.CreditStatement(
            account_id=account.id,
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            due_date=date(2026, 9, 15),
            statement_balance=Decimal("100.00"),
            minimum_payment=Decimal("30.00"),
            amount_paid=Decimal("0.00"),
            status=CreditStatementStatus.OPEN,
            interest_charged=Decimal("0.00"),
        )
        db.add(statement)
        db.commit()

        credit_services.evaluate_due_statements(
            db,
            date(2026, 9, 15),
        )

        user = (
            db.query(models.User)
            .filter(models.User.email == "john@example.com")
            .one()
        )
        after_due_date = user.credit_score

        credit_services.calculate_acquired_interest_all_credit_accounts(
            db
        )

        db.refresh(user)
        after_one_dpd_day = user.credit_score

    assert after_one_dpd_day < after_due_date
