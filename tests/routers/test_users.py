import jwt
from datetime import datetime, timedelta, timezone

import models
from tests.conftest import TestingSessionLocal, create_user_and_login
from schemas.users import UserResponse
from utils import secret_key, ALGORITHM


def test_create_user(client):
    response = client.post(
        "/users/",
        json={
            "first_name": "John",
            "last_name": "Test",
            "email": "john@example.com",
            "password": "securepassword123",
        },
    )

    assert response.status_code == 201

    data = response.json()
    UserResponse(**data)
    assert "password" not in data


def test_create_user_with_realistic_name_and_symbol_password(client):
    response = client.post(
        "/users/",
        json={
            "first_name": "José",
            "last_name": "Smith-Jones",
            "email": "jose@example.com",
            "password": "strong!password#123",
        },
    )

    assert response.status_code == 201


def test_duplicate_email_is_rejected(client):
    payload = {
        "first_name": "John",
        "last_name": "Test",
        "email": "john@example.com",
        "password": "securepassword123",
    }

    first = client.post("/users/", json=payload)
    second = client.post("/users/", json=payload)

    assert first.status_code == 201
    assert second.status_code == 400


def test_login_user(client):
    create = client.post(
        "/users/",
        json={
            "first_name": "John",
            "last_name": "Test",
            "email": "john@example.com",
            "password": "securepassword123",
        },
    )
    assert create.status_code == 201

    login = client.post(
        "/auth/",
        data={
            "username": "john@example.com",
            "password": "securepassword123",
        },
    )

    assert login.status_code == 200

    data = login.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert "password" not in data


def test_invalid_credentials_use_same_response(client):
    client.post(
        "/users/",
        json={
            "first_name": "John",
            "last_name": "Test",
            "email": "john@example.com",
            "password": "securepassword123",
        },
    )

    wrong_password = client.post(
        "/auth/",
        data={
            "username": "john@example.com",
            "password": "wrong-password",
        },
    )
    unknown_email = client.post(
        "/auth/",
        data={
            "username": "missing@example.com",
            "password": "wrong-password",
        },
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == "Invalid email or password"
    assert unknown_email.json()["detail"] == "Invalid email or password"


def test_find_user(client, auth_headers):
    response = client.get("/users/", headers=auth_headers)

    assert response.status_code == 200
    UserResponse(**response.json())


def test_find_user_requires_authentication(client):
    response = client.get("/users/")

    assert response.status_code == 401


def test_token_without_identity_is_rejected(client):
    token = jwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        secret_key,
        algorithm=ALGORITHM,
    )

    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_normal_user_cannot_access_admin(client, auth_headers):
    response = client.get("/admin/", headers=auth_headers)

    assert response.status_code == 403


def test_admin_user_can_access_admin(client):
    headers = create_user_and_login(client, "admin@example.com", "Admin")

    with TestingSessionLocal() as db:
        admin_user = (
            db.query(models.User)
            .filter(models.User.email == "admin@example.com")
            .first()
        )
        admin_user.is_admin = True
        db.commit()

    response = client.get("/admin/", headers=headers)

    assert response.status_code == 200
