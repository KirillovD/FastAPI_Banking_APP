from decimal import Decimal

import pytest
from pydantic import ValidationError

from config import Settings


def _settings(**overrides):
    values = {
        "secret_key": "test-secret",
        "encryption_key": "test-encryption-value",
        "credit_card_min_payment_amount": Decimal("30.00"),
        "credit_card_min_payment_percent": Decimal("0.03"),
        "credit_card_default_apr": Decimal("0.20"),
    }
    values.update(overrides)
    return Settings(
        **values,
        _env_file=None,
    )


def test_standard_postgresql_url_uses_psycopg_driver():
    settings = _settings(
        database_url=(
            "postgresql://demo:password@example.test:5432/banking"
        )
    )

    assert settings.database_url.startswith(
        "postgresql+psycopg://"
    )


def test_demo_seed_requires_explicit_password():
    with pytest.raises(ValidationError):
        _settings(
            seed_demo_data=True,
            demo_user_password=None,
        )


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
