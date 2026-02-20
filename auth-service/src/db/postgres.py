from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.core.config import settings

# Создаём базовый класс для будущих моделей
Base = declarative_base()
# Создаём движок
# Настройки подключения к БД передаём из переменных окружения, которые заранее загружены в файл настроек
dsn = f'{settings.async_driver}://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}'

migrations_dsn = f'{settings.sync_driver}://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_migrations_host}:{settings.postgres_port}/{settings.postgres_db}'

engine = create_async_engine(dsn, echo=True, future=True)
async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False) # type: ignore


# Dependency
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def create_database() -> None:
    """Создание таблиц."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def purge_database() -> None:
    """Удаление таблиц."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
