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


DEV_SECRET = "dev-only-secret-change-me-dev-only-secret-change-me"


def check_production(s: Settings) -> None:
    """Không cho chạy môi trường thật với cấu hình không an toàn."""
    if s.APP_ENV != "production":
        return
    if s.JWT_SECRET == DEV_SECRET or len(s.JWT_SECRET) < 32 or "change-me" in s.JWT_SECRET:
        raise RuntimeError("JWT_SECRET chưa được đặt giá trị bí mật riêng (≥ 32 ký tự) cho môi trường thật")
    if not s.REQUIRE_2FA:
        raise RuntimeError("Môi trường thật phải bật REQUIRE_2FA=true")
