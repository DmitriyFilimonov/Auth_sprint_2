from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    listen_host: str = Field(default="0.0.0.0", validation_alias="LISTEN_HOST")
    listen_port: int = Field(default=8000, validation_alias="LISTEN_PORT")

    auth_service_base_url: str = Field(
        ...,
        validation_alias="UPSTREAM_AUTH_BASE_URL",
    )

    failure_threshold: int = Field(
        default=5,
        ge=1,
        validation_alias="FAILURE_THRESHOLD",
    )
    recovery_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        validation_alias="RECOVERY_TIMEOUT_SECONDS",
    )
    half_open_probes: int = Field(
        default=1,
        ge=1,
        validation_alias="HALF_OPEN_PROBES",
    )

    request_timeout_seconds: float = Field(
        default=60.0, ge=1.0, validation_alias="REQUEST_TIMEOUT_SECONDS"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
