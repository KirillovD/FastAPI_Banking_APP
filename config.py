from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    secret_key : str

    algorithm : str = "HS256"

    encryption_key : str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()