from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / ".env"


def get_env_file() -> Path | None:
    return ENV_FILE if ENV_FILE.is_file() else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=get_env_file())
    postgres_db: str
    postgres_user: str
    postgres_password: str
    db_host: str
    db_port: int

    @property
    def test_postgres_url(self):
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.db_host}:{self.db_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
