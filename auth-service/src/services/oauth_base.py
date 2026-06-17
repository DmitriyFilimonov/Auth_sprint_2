from abc import ABC, abstractmethod


class OAuthProvider(ABC):
    """Базовый интерфейс OAuth-провайдера."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное имя провайдера (используется в URL: /oauth/{name}/...)."""

    @abstractmethod
    def build_authorization_url(self, state: str) -> str:
        """Возвращает URL, на который нужно редиректить пользователя для авторизации."""

    @abstractmethod
    async def exchange_code_for_tokens(self, code: str) -> dict:
        """Обмен авторизационного кода на токены провайдера."""

    @abstractmethod
    async def fetch_user_profile(self, access_token: str) -> dict:
        """Получение профиля пользователя через access_token."""

    @abstractmethod
    def map_profile_to_identity(self, profile: dict) -> dict:
        """Маппинг сырого профиля провайдера на внутренние поля.

        Returns dict with keys:
            provider_user_id: str
            login: str
            email: str | None
            first_name: str | None
            last_name: str | None
        """
