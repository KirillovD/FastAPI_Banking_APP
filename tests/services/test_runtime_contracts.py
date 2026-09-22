import os
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import models
import services.users as user_services
import tests.conftest as packaged_conftest
from config import Settings
from enums import AccountType
from schemas.users import UserCreate


def test_user_service_imports_with_schema_annotation_intact():
    assert user_services.create_user.__annotations__["user"] is UserCreate


def test_pytest_uses_single_packaged_conftest_module():
    assert sys.modules["tests.conftest"] is packaged_conftest
    if "conftest" in sys.modules:
        assert sys.modules["conftest"] is packaged_conftest


@pytest.mark.parametrize(
    "overrides",
    [
        {"credit_card_min_payment_amount": Decimal("-1")},
        {"credit_card_min_payment_percent": Decimal("1.01")},
        {"credit_card_default_apr": Decimal("-0.01")},
        {"credit_card_default_apr": Decimal("101")},
        {"bank_business_timezone": "Not/A_Timezone"},
    ],
)
def test_invalid_financial_settings_fail_fast(overrides):
    values = {
        "secret_key": "test",
        "encryption_key": (
            "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
        ),
        "credit_card_min_payment_amount": Decimal("30"),
        "credit_card_min_payment_percent": Decimal("0.03"),
        "credit_card_default_apr": Decimal("0.20"),
        "auto_create_schema": False,
    }
    values.update(overrides)

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **values,
        )


def test_sqlite_datetime_round_trip_restores_utc(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'utc.db'}"
    )
    models.Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    original = datetime(
        2026,
        9,
        22,
        12,
        30,
        tzinfo=timezone.utc,
    )

    with factory() as db:
        user = models.User(
            email="utc@example.com",
            first_name="Utc",
            last_name="User",
            password="hashed",
        )
        db.add(user)
        db.flush()

        account = models.Account(
            owner_id=user.id,
            type=AccountType.CHECKING,
            iban="DE1111111111111111111111",
            balance=Decimal("0.00"),
            created_at=original,
        )
        db.add(account)
        db.commit()
        account_id = account.id

    with factory() as db:
        loaded = db.get(models.Account, account_id)

        assert loaded.created_at.tzinfo is not None
        assert loaded.created_at.utcoffset() == Decimal("0")
        assert loaded.created_at == original

    engine.dispose()


def test_duplicate_registration_race_maps_to_domain_error(
    monkeypatch,
):
    user = UserCreate(
        first_name="Race",
        last_name="User",
        email="race@example.com",
        password="securepassword123",
    )
    existing = object()
    lookups = iter([None, existing])

    monkeypatch.setattr(
        user_services.user_crud,
        "get_user_by_email",
        lambda *args, **kwargs: next(lookups),
    )
    monkeypatch.setattr(
        user_services.user_crud,
        "create_user",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        user_services.utils,
        "hash_password",
        lambda password: "hashed",
    )

    class FakeDb:
        rolled_back = False

        def commit(self):
            raise IntegrityError(
                "insert",
                {},
                Exception("unique"),
            )

        def rollback(self):
            self.rolled_back = True

        def refresh(self, obj):
            raise AssertionError("refresh must not run")

    db = FakeDb()

    with pytest.raises(Exception) as exc_info:
        user_services.create_user(
            user,
            db,
        )

    assert exc_info.value.__class__.__name__ == "UserAlreadyExists"
    assert db.rolled_back is True


def test_importing_database_does_not_create_cwd_bankapp(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]

    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["SECRET_KEY"] = "test-secret"
    env["ENCRYPTION_KEY"] = (
        "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    )
    env["CREDIT_CARD_MIN_PAYMENT_AMOUNT"] = "30"
    env["CREDIT_CARD_MIN_PAYMENT_PERCENT"] = "0.03"
    env["CREDIT_CARD_DEFAULT_APR"] = "0.20"
    env["PYTHONPATH"] = str(repo_root)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import database; print(database.settings.database_url)",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "bankapp.db").exists()
