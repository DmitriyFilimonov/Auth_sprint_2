from src.services.oauth_base import OAuthProvider
from src.services.yandex_oauth import YandexOAuthProvider, YANDEX_PROVIDER

_PROVIDERS: dict[str, OAuthProvider] = {
    YANDEX_PROVIDER: YandexOAuthProvider(),
}


def register_oauth_provider(provider: OAuthProvider) -> None:
    """Регистрирует новый OAuth-провайдер.

    Чтобы добавить провайдера (VK, Google ...):
    1. Создайте класс, наследующий OAuthProvider.
    2. Вызовите register_oauth_provider(YourProvider()) при старте.
    """
    _PROVIDERS[provider.name] = provider


def get_oauth_provider(name: str) -> OAuthProvider:
    """Находит провайдер по имени из URL (/oauth/{name}/...)."""
    provider = _PROVIDERS.get(name)
    if provider is None:
        raise KeyError(f"Unknown OAuth provider: {name}")
    return provider


def list_oauth_provider_names() -> list[str]:
    return list(_PROVIDERS.keys())
