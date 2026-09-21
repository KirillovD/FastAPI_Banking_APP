from decimal import Decimal

import models
from enums import AccountType
from tests.conftest import (
    TestingSessionLocal,
    create_account,
    create_user_and_login,
)
from utils import generate_iban


def _get_balance(client, headers, account_id):
    response = client.get(f"/accounts/{account_id}", headers=headers)
    assert response.status_code == 200
    return Decimal(response.json()["balance"])


def _create_credit_account_for_user(email: str) -> dict:
    with TestingSessionLocal() as db:
        user = db.query(models.User).filter(models.User.email == email).first()
        account = models.Account(
            owner_id=user.id,
            type=AccountType.CREDIT,
            iban=generate_iban(),
            balance=Decimal("0.00"),
            limit=Decimal("500.00"),
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return {"id": account.id, "iban": account.iban}


def test_transfer_money_success(client, auth_headers):
    sender = create_account(client, auth_headers, "checking", 500)

    recipient_headers = create_user_and_login(
        client,
        "bob@example.com",
        "Bob",
    )
    recipient = create_account(
        client,
        recipient_headers,
        "checking",
        1000,
    )

    response = client.post(
        f"/transactions/{sender['id']}",
        json={
            "recipient_iban": recipient["iban"],
            "recipient_name": "  bOb   tEsT  ",
            "amount": 200,
            "description": "Rewe sagt danke",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["sender_account_id"] == sender["id"]
    assert data["sender_iban"] == sender["iban"]
    assert data["recipient_account_id"] == recipient["id"]
    assert data["recipient_iban"] == recipient["iban"]
    assert Decimal(data["amount"]) == Decimal("200")
    assert data["operation_type"] == "transfer"
    assert data["status"] == "successful"
    assert data["category"] == "Groceries"
    assert data["mcc_code"] is None
    assert data["classification_source"] == "description_rule"

    assert _get_balance(client, auth_headers, sender["id"]) == Decimal("300")
    assert _get_balance(client, recipient_headers, recipient["id"]) == Decimal("1200")


def test_transfer_rejects_sender_metadata_from_client(client, auth_headers):
    sender = create_account(client, auth_headers, "checking", 500)

    recipient_headers = create_user_and_login(
        client,
        "bob@example.com",
        "Bob",
    )
    recipient = create_account(client, recipient_headers, "checking", 1000)

    response = client.post(
        f"/transactions/{sender['id']}",
        json={
            "recipient_iban": recipient["iban"],
            "recipient_name": "Bob Test",
            "amount": 100,
            "description": "test",
            "sender_account_id": 999,
            "sender_iban": recipient["iban"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_transfer_amount_must_be_positive(client, auth_headers):
    sender = create_account(client, auth_headers, "checking", 500)

    recipient_headers = create_user_and_login(
        client,
        "bob@example.com",
        "Bob",
    )
    recipient = create_account(client, recipient_headers, "checking", 1000)

    response = client.post(
        f"/transactions/{sender['id']}",
        json={
            "recipient_iban": recipient["iban"],
            "recipient_name": "Bob Test",
            "amount": -200,
            "description": "invalid transfer",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert _get_balance(client, auth_headers, sender["id"]) == Decimal("500")
    assert _get_balance(client, recipient_headers, recipient["id"]) == Decimal("1000")


def test_transfer_rejects_self_transfer(client, auth_headers):
    sender = create_account(client, auth_headers, "checking", 500)

    response = client.post(
        f"/transactions/{sender['id']}",
        json={
            "recipient_iban": sender["iban"],
            "recipient_name": "John Test",
            "amount": 100,
            "description": "self transfer",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert _get_balance(client, auth_headers, sender["id"]) == Decimal("500")


def test_transfer_rejects_unowned_source_account(client, auth_headers):
    recipient_headers = create_user_and_login(
        client,
        "bob@example.com",
        "Bob",
    )
    recipient = create_account(client, recipient_headers, "checking", 1000)

    response = client.post(
        f"/transactions/{recipient['id']}",
        json={
            "recipient_iban": recipient["iban"],
            "recipient_name": "Bob Test",
            "amount": 100,
            "description": "not my account",
        },
        headers=auth_headers,
    )

    assert response.status_code == 403


def test_transfer_rejects_credit_source_account(client, auth_headers):
    credit_account = _create_credit_account_for_user("john@example.com")

    recipient_headers = create_user_and_login(
        client,
        "bob@example.com",
        "Bob",
    )
    recipient = create_account(client, recipient_headers, "checking", 1000)

    response = client.post(
        f"/transactions/{credit_account['id']}",
        json={
            "recipient_iban": recipient["iban"],
            "recipient_name": "Bob Test",
            "amount": 100,
            "description": "credit cash advance",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_deposit_cash_creates_history_record(client, auth_headers):
    account = create_account(client, auth_headers, "checking", 500)

    response = client.post(
        f"/transactions/{account['id']}/deposit",
        json={"amount": 100},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert _get_balance(client, auth_headers, account["id"]) == Decimal("600")

    history = client.get("/transactions/", headers=auth_headers)

    assert history.status_code == 200
    data = history.json()
    assert len(data) == 1
    assert data[0]["operation_type"] == "deposit"
    assert data[0]["recipient_account_id"] == account["id"]
    assert Decimal(data[0]["amount"]) == Decimal("100")


def test_withdraw_cash_creates_history_record(client, auth_headers):
    account = create_account(client, auth_headers, "savings", 500)

    response = client.post(
        f"/transactions/{account['id']}/withdraw",
        json={"amount": 100},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert _get_balance(client, auth_headers, account["id"]) == Decimal("400")

    history = client.get("/transactions/", headers=auth_headers)

    assert history.status_code == 200
    data = history.json()
    assert len(data) == 1
    assert data[0]["operation_type"] == "withdrawal"
    assert data[0]["sender_account_id"] == account["id"]
    assert Decimal(data[0]["amount"]) == Decimal("100")


def test_cash_operations_reject_credit_account(client, auth_headers):
    credit_account = _create_credit_account_for_user("john@example.com")

    deposit = client.post(
        f"/transactions/{credit_account['id']}/deposit",
        json={"amount": 100},
        headers=auth_headers,
    )
    withdraw = client.post(
        f"/transactions/{credit_account['id']}/withdraw",
        json={"amount": 100},
        headers=auth_headers,
    )

    assert deposit.status_code == 400
    assert withdraw.status_code == 400


def test_withdraw_rejects_insufficient_funds(client, auth_headers):
    account = create_account(client, auth_headers, "checking", 50)

    response = client.post(
        f"/transactions/{account['id']}/withdraw",
        json={"amount": 100},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert _get_balance(client, auth_headers, account["id"]) == Decimal("50")


def test_cash_history_is_newest_first(client, auth_headers):
    account = create_account(client, auth_headers, "checking", 500)

    deposit = client.post(
        f"/transactions/{account['id']}/deposit",
        json={"amount": 100},
        headers=auth_headers,
    )
    withdrawal = client.post(
        f"/transactions/{account['id']}/withdraw",
        json={"amount": 50},
        headers=auth_headers,
    )

    assert deposit.status_code == 200
    assert withdrawal.status_code == 200

    history = client.get("/transactions/", headers=auth_headers)
    assert history.status_code == 200

    data = history.json()
    assert [item["operation_type"] for item in data] == [
        "withdrawal",
        "deposit",
    ]
