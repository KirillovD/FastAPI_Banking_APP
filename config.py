from decimal import Decimal
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    encryption_key: str

    credit_card_min_payment_amount: Decimal
    credit_card_min_payment_percent: Decimal

    # Preferred Portfolio V2 representation:
    # Decimal("0.20") means 20% APR.
    credit_card_default_apr: Decimal

    # Kept temporarily for compatibility with existing local .env files.
    # Credit calculations now derive the daily rate from APR.
    credit_card_default_dpr: Decimal | None = None

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
