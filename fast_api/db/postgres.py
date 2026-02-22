from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from core.config import settings

# Создаём базовый класс для будущих моделей
Base = declarative_base()

dsn = f"{settings.postgres_async_driver}://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"

engine = create_async_engine(dsn, echo=True, future=True)
async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore


# Dependency
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


class BaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
