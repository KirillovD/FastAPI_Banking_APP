import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault(
    "ENCRYPTION_KEY",
    "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
)
os.environ.setdefault(
    "CREDIT_CARD_MIN_PAYMENT_AMOUNT",
    "30",
)
os.environ.setdefault(
    "CREDIT_CARD_MIN_PAYMENT_PERCENT",
    "0.03",
)
os.environ.setdefault(
    "CREDIT_CARD_DEFAULT_APR",
    "0.20",
)
os.environ.setdefault(
    "BANK_BUSINESS_TIMEZONE",
    "Europe/Berlin",
)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUTO_CREATE_SCHEMA"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import Base


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def auth_headers(client):
    return create_user_and_login(
        client,
        "john@example.com",
        "John",
    )


def create_user_and_login(
    client,
    email,
    first_name,
):
    create = client.post(
        "/users/",
        json={
            "first_name": first_name,
            "last_name": "Test",
            "email": email,
            "password": "securepassword123",
        },
    )

    assert create.status_code == 201

    login = client.post(
        "/auth/",
        data={
            "username": email,
            "password": "securepassword123",
        },
    )

    assert login.status_code == 200

    token = login.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
    }


def create_account(
    client,
    headers,
    acc_type,
    balance,
):
    response = client.post(
        "/accounts/",
        json={
            "type": acc_type,
            "balance": balance,
        },
        headers=headers,
    )

    assert response.status_code == 200
    return response.json()


def create_credit_card(
    client,
    headers,
):
    response = client.post(
        "/cards/credit",
        json={
            "pin_code": "1234",
            "type": "mastercard",
        },
        headers=headers,
    )

    assert response.status_code == 200
    return response.json()


def create_debit_card(
    client,
    headers,
    acc_id,
):
    response = client.post(
        f"/cards/debit/{acc_id}",
        json={
            "pin_code": "1234",
            "type": "mastercard",
        },
        headers=headers,
    )

    assert response.status_code == 200
    return response.json()
