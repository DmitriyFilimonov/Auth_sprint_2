from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ADMIN_ROOT = Path(__file__).resolve().parent.parent


class AdminEnvSettings(BaseSettings):
    postgres_db: str = Field(validation_alias="POSTGRES_DB")
    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: str = Field(validation_alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(validation_alias="POSTGRES_HOST")
    postgres_port: str = Field(validation_alias="POSTGRES_PORT")

    auth_service: str = Field(validation_alias="AUTH_SERVICE")
    auth_port: str = Field(validation_alias="AUTH_PORT")
    auth_login_endpoint: str = Field(validation_alias="AUTH_LOGIN_EDNPOINT")

    algorithm: str = Field(validation_alias="ALGORITHM")

    fastapi_service: str = Field(default="fastapi", validation_alias="FASTAPI_SERVICE")
    fastapi_port: str = Field(default="8000", validation_alias="FASTAPI_PORT")

    model_config = SettingsConfigDict(
        env_file=_ADMIN_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @computed_field
    def auth_api_url(self) -> str:
        return f"http://{self.auth_service}:{self.auth_port}"

    @computed_field
    def auth_api_login_url(self) -> str:
        return f"{self.auth_api_url}/{self.auth_login_endpoint}"

    @computed_field
    def fastapi_url(self) -> str:
        return f"http://{self.fastapi_service}:{self.fastapi_port}"


env = AdminEnvSettings()
