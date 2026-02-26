from sqlalchemy.ext.asyncio import create_async_engine

from tests.functional.settings import test_settings


dsn = f"postgresql+asyncpg://postgres:secret@{test_settings.auth_db_setting.get_host()}/auth"

users_engine = create_async_engine(dsn, echo=test_settings.debug, future=True)
