from decimal import Decimal

import pytest

import models
import services.cards as card_services
from enums import AccountType
from schemas.cards import CardResponse, CardSecretResponse
from tests.conftest import (
    TestingSessionLocal,
    create_account,
    create_credit_card,
    create_user_and_login,
)


def test_create_credit_card_creates_credit_invariants(client, auth_headers):
    response = client.post(
        "/cards/credit",
        json={"pin_code": "1234", "type": "mastercard"},
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    CardResponse(**data)

    assert "pin_code" not in data
    assert "pin_code_hashed" not in data
    assert "CVV_encrypted" not in data

    with TestingSessionLocal() as db:
        account = db.get(models.Account, data["linked_acc_id"])

        assert account is not None
        assert account.type == AccountType.CREDIT
        assert account.limit == Decimal("500.00")
        assert account.credit_account_metrics is not None
        assert account.credit_account_metrics.account_id == account.id


def test_credit_card_issuance_rolls_back_if_card_creation_fails(
    client,
    auth_headers,
    monkeypatch,
):
    def fail_card_creation(*args, **kwargs):
        raise RuntimeError("synthetic card creation failure")

    monkeypatch.setattr(
        card_services.crud_cards,
        "create_card",
        fail_card_creation,
    )

    with pytest.raises(RuntimeError):
        client.post(
            "/cards/credit",
            json={"pin_code": "1234", "type": "mastercard"},
            headers=auth_headers,
        )

    with TestingSessionLocal() as db:
        user = (
            db.query(models.User)
            .filter(models.User.email == "john@example.com")
            .first()
        )

        credit_accounts = (
            db.query(models.Account)
            .filter(
                models.Account.owner_id == user.id,
                models.Account.type == AccountType.CREDIT,
            )
            .all()
        )

        assert credit_accounts == []
        assert db.query(models.CreditAccountMetrics).count() == 0
        assert db.query(models.Card).count() == 0


def test_create_debit_card_for_checking_account(client, auth_headers):
    account = create_account(
        client,
        auth_headers,
        "checking",
        1000,
    )

    response = client.post(
        f"/cards/debit/{account['id']}",
        json={"pin_code": "1234", "type": "maestro"},
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    validated_card = CardResponse(**data)

    assert validated_card.linked_acc_id == account["id"]
    assert "pin_code_hashed" not in data
    assert "CVV_encrypted" not in data


def test_create_debit_card_for_savings_account(client, auth_headers):
    account = create_account(
        client,
        auth_headers,
        "savings",
        1000,
    )

    response = client.post(
        f"/cards/debit/{account['id']}",
        json={"pin_code": "1234", "type": "mastercard"},
        headers=auth_headers,
    )

    assert response.status_code == 200


def test_create_debit_card_rejects_credit_account(client, auth_headers):
    credit_card = create_credit_card(client, auth_headers)

    response = client.post(
        f"/cards/debit/{credit_card['linked_acc_id']}",
        json={"pin_code": "1234", "type": "mastercard"},
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_create_debit_card_idor(client, auth_headers):
    account = create_account(
        client,
        auth_headers,
        "checking",
        1000,
    )

    other_headers = create_user_and_login(
        client,
        "mary@example.com",
        "Mary",
    )

    response = client.post(
        f"/cards/debit/{account['id']}",
        json={"pin_code": "1234", "type": "mastercard"},
        headers=other_headers,
    )

    assert response.status_code == 403


def test_card_creation_requires_four_digit_pin(client, auth_headers):
    too_short = client.post(
        "/cards/credit",
        json={"pin_code": "123", "type": "mastercard"},
        headers=auth_headers,
    )
    non_digit = client.post(
        "/cards/credit",
        json={"pin_code": "12a4", "type": "mastercard"},
        headers=auth_headers,
    )

    assert too_short.status_code == 422
    assert non_digit.status_code == 422


def test_card_creation_rejects_unsupported_type(client, auth_headers):
    response = client.post(
        "/cards/credit",
        json={"pin_code": "1234", "type": "visa"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_get_card(client, auth_headers):
    credit_card = create_credit_card(client, auth_headers)

    response = client.get(
        f"/cards/{credit_card['id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    CardResponse(**data)

    assert "pin_code_hashed" not in data
    assert "CVV_encrypted" not in data


def test_get_card_idor(client, auth_headers):
    credit_card = create_credit_card(client, auth_headers)

    other_headers = create_user_and_login(
        client,
        "mary@example.com",
        "Mary",
    )

    response = client.get(
        f"/cards/{credit_card['id']}",
        headers=other_headers,
    )

    assert response.status_code == 403


def test_get_card_cvv(client, auth_headers):
    credit_card = create_credit_card(client, auth_headers)

    response = client.get(
        f"/cards/{credit_card['id']}/cvv",
        headers=auth_headers,
    )

    assert response.status_code == 200
    CardSecretResponse(**response.json())


def test_get_card_cvv_idor(client, auth_headers):
    credit_card = create_credit_card(client, auth_headers)

    other_headers = create_user_and_login(
        client,
        "mary@example.com",
        "Mary",
    )

    response = client.get(
        f"/cards/{credit_card['id']}/cvv",
        headers=other_headers,
    )

    assert response.status_code == 403


def test_get_all_cards_only_returns_current_users_cards(client, auth_headers):
    own_card = create_credit_card(client, auth_headers)

    other_headers = create_user_and_login(
        client,
        "mary@example.com",
        "Mary",
    )
    create_credit_card(client, other_headers)

    response = client.get("/cards/", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == own_card["id"]
