from passlib.context import CryptContext
import asyncio

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Верификация пароля. Для пользователей только с OAuth хэш отсутствует — вход по паролю невозможен."""
    if hashed_password is None:
        return False
    return await asyncio.to_thread(pwd_context.verify,plain_password, hashed_password)


async def get_password_hash(password: str) -> str:
    """Получение хэш пароля."""
    return await asyncio.to_thread(pwd_context.hash,password)
