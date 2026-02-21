import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.entity import User, History, UserRole, Role
from src.core.security import get_password_hash, verify_password


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by ID"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_login(self, login: str) -> User | None:
        """Get user by login"""
        result = await self.session.execute(
            select(User).where(User.login == login).options(selectinload(User.roles))
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email"""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        login: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: UserRole = UserRole.USER
    ) -> User:
        """Create new user"""
        hashed_password = get_password_hash(password)
        user = User(
            login=login,
            email=email,
            password=hashed_password,
            first_name=first_name,
            last_name=last_name,
        )
        self.session.add(user)
        await self.session.flush()

        new_role = Role(
            user_id=user.id,
            role=role
        )

        self.session.add(new_role)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Update user password"""
        hashed_password = get_password_hash(new_password)
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(password=hashed_password)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def update_user_login(self, user_id: int, new_login: str) -> bool:
        """Update user login"""
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(login=new_login)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def verify_user_password(self, user_id: int, password: str) -> bool:
        """Verify user password"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        return verify_password(password, user.password)


class LoginHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_login_record(
        self,
        user_id: uuid.UUID,
        user_agent: str | None = None,
        login_info: str | None = None
    ) -> History:
        """Create login history record"""
        record = History(
            user_id=user_id,
            user_agent=user_agent,
            login_info=login_info
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_user_login_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> list[History]:
        """Get user login history"""
        result = await self.session.execute(
            select(History)
            .where(History.user_id == user_id)
            .order_by(History.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(History.users))
        )
        return result.scalars().all()
