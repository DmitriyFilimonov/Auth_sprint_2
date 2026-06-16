from passlib.context import CryptContext
import asyncio

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_password_hash(password: str) -> str:
    """Получение хэш пароля."""
    return await asyncio.to_thread(pwd_context.hash,password)
