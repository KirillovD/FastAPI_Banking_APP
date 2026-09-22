from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from money import MAX_MONEY


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_URL = (
    f"sqlite:///{BASE_DIR / 'bankapp.db'}"
)


class Settings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    encryption_key: str

    database_url: str = DEFAULT_DATABASE_URL
    auto_create_schema: bool = True
    seed_demo_data: bool = False
    demo_user_password: str | None = None

    credit_card_min_payment_amount: Decimal = Field(
        ge=Decimal("0.00"),
        le=MAX_MONEY,
    )
    credit_card_min_payment_percent: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    # Preferred representation: Decimal("0.20") means 20% APR.
    # Whole-percent legacy values such as 20 are still accepted.
    credit_card_default_apr: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    # Legacy compatibility only; credit calculations derive DPR from APR.
    credit_card_default_dpr: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    bank_business_timezone: str = "Europe/Berlin"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str):
        value = value.strip()

        if not value:
            raise ValueError("database_url cannot be empty")

        sqlite_prefix = "sqlite:///"
        if (
            value.startswith(sqlite_prefix)
            and value != "sqlite:///:memory:"
        ):
            sqlite_path = value[len(sqlite_prefix):]

            if not sqlite_path.startswith("/"):
                resolved = (
                    BASE_DIR / sqlite_path
                ).resolve()
                return f"sqlite:///{resolved}"

        return value

    @field_validator("bank_business_timezone")
    @classmethod
    def validate_timezone(cls, value: str):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                "bank_business_timezone must be a valid IANA timezone"
            ) from exc
        return value

    @model_validator(mode="after")
    def validate_demo_seed(self):
        if (
            self.seed_demo_data
            and not self.demo_user_password
        ):
            raise ValueError(
                "demo_user_password is required when seed_demo_data is enabled"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
