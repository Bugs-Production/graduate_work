from logging import config as logging_config

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.logger import LOGGING


class RabbitMQSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="RABBITMQ_"
    )
    host: str = Field("localhost", alias="RABBITMQ_HOST")
    port: int = Field("5672", alias="RABBITMQ_PORT")
    user: str = Field("user", alias="RABBITMQ_USER")
    password: str = Field("password", alias="RABBITMQ_PASSWORD")
    exchange_name: str = Field("billing_events", alias="RABBITMQ_EXCHANGE_NAME")

    @property
    def url(self):
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}"


class TestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="TEST_")
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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    project_name: str = Field("billing_api", alias="PROJECT_NAME")
    postgres_url: str = Field("postgresql+asyncpg://postgres:postgres@db:5432/foo", alias="POSTGRES_URL")
    engine_echo: bool = Field(default=False, alias="ENGINE_ECHO")
    jwt_secret_key: str = Field("my_secret_key", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    stripe_publishable_key: str = Field("stripe_publishable_key", alias="STRIPE_PUBLISHABLE_KEY")
    stripe_api_key: str = Field("stripe_secret_key", alias="STRIPE_API_KEY")

    secret_token: str = Field("super_secret_token", alias="SECRET_TOKEN")
    auth_service_url: str = Field("http://localhost/api/v1/auth", alias="AUTH_SERVICE_URL")
    notification_service_url: str = Field("http://localhost/api/v1/notitications", alias="NOTIFICATION_SERVICE_URL")

    rabbitmq: RabbitMQSettings = RabbitMQSettings()  # type:ignore[call-arg]
    tests: TestSettings = TestSettings()

    celery_scheduler_interval_sec: int = Field(60, alias="CELERY_SСHEDULER_INTERVAL_SEC")


logging_config.dictConfig(LOGGING)
settings = Settings()  # type: ignore[call-arg]
