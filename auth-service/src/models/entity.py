import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID

from src.db.postgres import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    login: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(50))
    last_name: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    roles: Mapped[list["Role"]] = relationship(back_populates="users", passive_deletes=True, cascade="all, delete-orphan")
    history: Mapped[list["History"]] = relationship(back_populates="users", passive_deletes=True, cascade="all, delete-orphan")
    oauth_identities: Mapped[list["OAuthIdentity"]] = relationship(
        back_populates="user",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f'<User {self.login}>'


class UserRole(str, enum.Enum):
    USER = "user"  # Обычный пользователь
    SUBSCRIBER = "subscriber"  # Подписчик (платный)
    ADMIN = "admin"  # Администратор
    SUPERUSER = "superuser"  # Суперпользователь (полный доступ)


class OAuthIdentity(Base):
    """Привязка внешнего аккаунта к пользователю"""

    __tablename__ = "oauth_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_oauth_identities_provider_subject",
        ),
        UniqueConstraint(
            "user_id",
            "provider",
            name="uq_oauth_identities_user_provider",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="oauth_identities")

    def __repr__(self) -> str:
        return f"<OAuthIdentity {self.provider}:{self.provider_user_id}>"


class Role(Base):
    __tablename__ = 'roles'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False, default=UserRole.USER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    users: Mapped["User"] = relationship(back_populates="roles")

    def __init__(self, user_id: uuid.UUID, role: UserRole) -> None:
        self.user_id = user_id
        self.role = role

    def __repr__(self) -> str:
        return f"<Role {self.role}>"


class History(Base):
    __tablename__ = 'history'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    login_info: Mapped[str | None] = mapped_column(String(255))

    users: Mapped["User"] = relationship(back_populates="history")

    def __init__(self, user_id: uuid.UUID, user_agent: str, login_info: str) -> None:
        self.user_id = user_id
        self.user_agent = user_agent
        self.login_info = login_info
