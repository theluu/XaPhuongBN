from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str = "dev-only-secret-change-me-dev-only-secret-change-me"
    JWT_TTL_MINUTES: int = 30
    REQUIRE_2FA: bool = False
    LOCKOUT_THRESHOLD: int = 5
    LOCKOUT_MINUTES: int = 15
    STORAGE_DIR: str = "/data/storage"
    SEED_PASSWORD: str = ""
    APP_ENV: str = "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
