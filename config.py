from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    secret_key : str

    algorithm : str = "HS256"

    encryption_key : str

    model_config = SettingsConfigDict(
            env_file=BASE_DIR / ".env",
            env_file_encoding='utf-8',
            extra='ignore'
        )

settings = Settings()