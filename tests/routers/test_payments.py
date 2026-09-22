from datetime import datetime, timedelta, timezone
from decimal import Decimal

import models
from enums import OperationType
from tests.conftest import (
    TestingSessionLocal,
    create_account,
    create_credit_card,
    create_debit_card,
    create_user_and_login,
)


def _get_balance(client, headers, account_id):
    response = client.get(
        f"/accounts/{account_id}",
        headers=headers,
    )
    assert response.status_code == 200
    return Decimal(response.json()["balance"])


def _get_cvv(client, headers, card_id):
    response = client.get(
        f"/cards/{card_id}/cvv",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["cvv"]


def test_online_debit_payment_success(client, auth_headers):
    account = create_account(
        client,
        auth_headers,
        "checking",
        1000,
    )
    card = create_debit_card(
        client,
        auth_headers,
        account["id"],
    )
    cvv = _get_cvv(client, auth_headers, card["id"])

    response = client.post(
        "/payments/",
        json={
            "amount": 125,
            "terminal_data": {
                "merchant_name": "REWE Berlin",
                "card_number": card["number"],
                "payment_type": "online",
                "mcc_code": "5411",
            },
            "cvv": cvv,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "successful"
    assert Decimal(data["amount"]) == Decimal("125.00")
    assert data["message"] == "Payment approved"

    assert _get_balance(
        client,
        auth_headers,
        account["id"],
    ) == Decimal("875.00")

    history = client.get("/transactions/", headers=auth_headers)
    assert history.status_code == 200

    transactions = history.json()
    assert len(transactions) == 1
    assert transactions[0]["id"] == data["transaction_id"]
    assert transactions[0]["operation_type"] == "payment"
    assert transactions[0]["description"] == "REWE Berlin"
    assert transactions[0]["category"] == "Groceries"
    assert transactions[0]["mcc_code"] == "5411"
    assert transactions[0]["classification_source"] == "mcc"


def test_pos_credit_payment_uses_credit_limit(client, auth_headers):
    card = create_credit_card(client, auth_headers)

    response = client.post(
        "/payments/",
        json={
            "amount": 200,
            "terminal_data": {
                "merchant_name": "Local Store",
                "card_number": card["number"],
                "payment_type": "pos",
                "mcc_code": "5399",
            },
            "pin_block": "1234",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert _get_balance(
        client,
        auth_headers,
        card["linked_acc_id"],
    ) == Decimal("-200.00")

    with TestingSessionLocal() as db:
        transaction = db.get(
            models.Transaction,
            response.json()["transaction_id"],
        )
        assert transaction is not None
        assert transaction.operation_type == OperationType.PAYMENT
        assert transaction.sender_account_id == card["linked_acc_id"]


def test_payment_rejects_other_users_card(client, auth_headers):
    other_headers = create_user_and_login(
        client,
        "mary@example.com",
        "Mary",
    )
    other_account = create_account(
        client,
        other_headers,
        "checking",
        500,
    )
    other_card = create_debit_card(
        client,
        other_headers,
        other_account["id"],
    )
    other_cvv = _get_cvv(
        client,
        other_headers,
        other_card["id"],
    )

    response = client.post(
        "/payments/",
        json={
            "amount": 50,
            "terminal_data": {
                "merchant_name": "REWE Berlin",
                "card_number": other_card["number"],
                "payment_type": "online",
                "mcc_code": "5411",
            },
            "cvv": other_cvv,
        },
        headers=auth_headers,
    )

    assert response.status_code == 403
    assert _get_balance(
        client,
        other_headers,
        other_account["id"],
    ) == Decimal("500.00")


def test_online_payment_rejects_wrong_cvv_without_mutation(
    client,
    auth_headers,
):
    account = create_account(
        client,
        auth_headers,
        "checking",
        500,
    )
    card = create_debit_card(
        client,
        auth_headers,
        account["id"],
    )

    actual_cvv = _get_cvv(
        client,
        auth_headers,
        card["id"],
    )
    wrong_cvv = (
        "000"
        if actual_cvv != "000"
        else "001"
    )

    response = client.post(
        "/payments/",
        json={
            "amount": 50,
            "terminal_data": {
                "merchant_name": "REWE Berlin",
                "card_number": card["number"],
                "payment_type": "online",
                "mcc_code": "5411",
            },
            "cvv": wrong_cvv,
        },
        headers=auth_headers,
    )

    assert response.status_code == 403
    assert _get_balance(
        client,
        auth_headers,
        account["id"],
    ) == Decimal("500.00")

    with TestingSessionLocal() as db:
        assert db.query(models.Transaction).count() == 0


def test_online_payment_requires_cvv(client, auth_headers):
    account = create_account(
        client,
        auth_headers,
        "checking",
        500,
    )
    card = create_debit_card(
        client,
        auth_headers,
        account["id"],
    )

    response = client.post(
        "/payments/",
        json={
            "amount": 50,
            "terminal_data": {
                "merchant_name": "REWE Berlin",
                "card_number": card["number"],
                "payment_type": "online",
                "mcc_code": "5411",
            },
        },
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_pos_payment_rejects_wrong_pin_without_mutation(
    client,
    auth_headers,
):
    account = create_account(
        client,
        auth_headers,
        "checking",
        500,
    )
    card = create_debit_card(
        client,
        auth_headers,
        account["id"],
    )

    response = client.post(
        "/payments/",
        json={
            "amount": 50,
            "terminal_data": {
                "merchant_name": "Local Store",
                "card_number": card["number"],
                "payment_type": "pos",
                "mcc_code": "5399",
            },
            "pin_block": "4321",
        },
        headers=auth_headers,
    )

    assert response.status_code == 403
    assert _get_balance(
        client,
        auth_headers,
        account["id"],
    ) == Decimal("500.00")

    with TestingSessionLocal() as db:
        assert db.query(models.Transaction).count() == 0


def test_payment_rejects_expired_card(client, auth_headers):
    account = create_account(
        client,
        auth_headers,
        "checking",
        500,
    )
    card = create_debit_card(
        client,
        auth_headers,
        account["id"],
    )

    with TestingSessionLocal() as db:
        db_card = db.get(models.Card, card["id"])
        db_card.expiry_date = (
            datetime.now(timezone.utc) - timedelta(days=1)
        )
        db.commit()

    response = client.post(
        "/payments/",
        json={
            "amount": 50,
            "terminal_data": {
                "merchant_name": "Local Store",
                "card_number": card["number"],
                "payment_type": "pos",
                "mcc_code": "5399",
            },
            "pin_block": "1234",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert _get_balance(
        client,
        auth_headers,
        account["id"],
    ) == Decimal("500.00")


def test_payment_amount_must_be_positive(client, auth_headers):
    account = create_account(
        client,
        auth_headers,
        "checking",
        500,
    )
    card = create_debit_card(
        client,
        auth_headers,
        account["id"],
    )

    response = client.post(
        "/payments/",
        json={
            "amount": -50,
            "terminal_data": {
                "merchant_name": "Local Store",
                "card_number": card["number"],
                "payment_type": "pos",
                "mcc_code": "5399",
            },
            "pin_block": "1234",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert _get_balance(
        client,
        auth_headers,
        account["id"],
    ) == Decimal("500.00")


def test_payment_rejects_insufficient_funds_without_transaction(
    client,
    auth_headers,
):
    account = create_account(
        client,
        auth_headers,
        "checking",
        50,
    )
    card = create_debit_card(
        client,
        auth_headers,
        account["id"],
    )

    response = client.post(
        "/payments/",
        json={
            "amount": 100,
            "terminal_data": {
                "merchant_name": "Local Store",
                "card_number": card["number"],
                "payment_type": "pos",
                "mcc_code": "5399",
            },
            "pin_block": "1234",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert _get_balance(
        client,
        auth_headers,
        account["id"],
    ) == Decimal("50.00")

    with TestingSessionLocal() as db:
        assert db.query(models.Transaction).count() == 0


def test_payment_requires_authentication(client):
    response = client.post(
        "/payments/",
        json={
            "amount": 10,
            "terminal_data": {
                "merchant_name": "Local Store",
                "card_number": "5555555555554444",
                "payment_type": "pos",
                "mcc_code": "5399",
            },
            "pin_block": "1234",
        },
    )

    assert response.status_code == 401
