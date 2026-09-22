from datetime import datetime, timedelta

from sqlalchemy import inspect

import models
from schemas.accounts import AccResponse
from tests.conftest import create_user_and_login


def test_credit_account_metrics_has_primary_key():
    mapper = inspect(models.CreditAccountMetrics)
    assert [column.name for column in mapper.primary_key] == ["account_id"]


def test_create_account(client, auth_headers):
    response = client.post(
        "/accounts/",
        json={"type": "savings", "balance": 1000},
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    AccResponse(**data)

    assert data["type"] == "savings"
    assert data["balance"] == "1000.00" or data["balance"] == 1000
    assert data["iban"].startswith("DE")
    assert "created_at" in data
    assert "overdraft_limit" not in data


def test_create_checking_account(client, auth_headers):
    response = client.post(
        "/accounts/",
        json={"type": "checking", "balance": 500},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["type"] == "checking"


def test_generic_account_endpoint_rejects_credit_account(client, auth_headers):
    response = client.post(
        "/accounts/",
        json={"type": "credit", "balance": 0},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_get_all_accounts(client, auth_headers):
    savings = client.post(
        "/accounts/",
        json={"type": "savings", "balance": 1000},
        headers=auth_headers,
    )
    checking = client.post(
        "/accounts/",
        json={"type": "checking", "balance": 50000},
        headers=auth_headers,
    )

    assert savings.status_code == 200
    assert checking.status_code == 200

    response = client.get("/accounts/", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    AccResponse(**data[0])
    AccResponse(**data[1])


def test_get_accounts_empty(client, auth_headers):
    response = client.get("/accounts/", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_create_account_without_token(client):
    response = client.post(
        "/accounts/",
        json={"type": "savings", "balance": 1000},
    )

    assert response.status_code == 401


def test_get_acc_by_id(client, auth_headers):
    created = client.post(
        "/accounts/",
        json={"type": "savings", "balance": 1000},
        headers=auth_headers,
    )

    assert created.status_code == 200
    account_id = created.json()["id"]

    response = client.get(
        f"/accounts/{account_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    AccResponse(**response.json())


def test_get_acc_by_id_idor(client, auth_headers):
    created = client.post(
        "/accounts/",
        json={"type": "savings", "balance": 1000},
        headers=auth_headers,
    )

    assert created.status_code == 200
    account_id = created.json()["id"]

    other_user_headers = create_user_and_login(
        client,
        "mary@example.com",
        "Mary",
    )

    response = client.get(
        f"/accounts/{account_id}",
        headers=other_user_headers,
    )

    assert response.status_code == 403


def test_list_accounts_only_returns_current_users_accounts(client, auth_headers):
    own_account = client.post(
        "/accounts/",
        json={"type": "checking", "balance": 250},
        headers=auth_headers,
    )
    assert own_account.status_code == 200

    other_headers = create_user_and_login(
        client,
        "other@example.com",
        "Other",
    )
    other_account = client.post(
        "/accounts/",
        json={"type": "savings", "balance": 900},
        headers=other_headers,
    )
    assert other_account.status_code == 200

    response = client.get("/accounts/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == own_account.json()["id"]



def test_huge_resource_id_is_rejected_before_sqlite_binding(
    client,
    auth_headers,
):
    response = client.get(
        "/accounts/9223372036854775808",
        headers=auth_headers,
    )

    assert response.status_code == 422



def test_account_created_at_is_serialized_as_utc(
    client,
    auth_headers,
):
    account = create_account(
        client,
        auth_headers,
        "checking",
        0,
    )

    created_at = datetime.fromisoformat(
        account["created_at"].replace(
            "Z",
            "+00:00",
        )
    )

    assert created_at.tzinfo is not None
    assert created_at.utcoffset() == timedelta(0)
