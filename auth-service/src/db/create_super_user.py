import asyncio

# import os


from src.db.postgres import async_session
from src.core.security import get_password_hash
from src.models.entity import Role, User, UserRole
from src.core.config import settings


async def create_super_user():
    async with async_session() as session:
        hashed_password = await get_password_hash(settings.superuser_password)

        user = User(
            login="admin",
            password=hashed_password,
        )

        session.add(user)

        await session.flush()

        session.add(Role(user_id=user.id, role=UserRole.SUPERUSER))

        await session.commit()


if __name__ == "__main__":
    asyncio.run(create_super_user())
