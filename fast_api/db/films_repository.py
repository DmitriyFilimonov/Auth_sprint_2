import uuid

from sqlalchemy import func, update

from db.postgres import BaseRepository
from db.sqlalchemy_models import FilmWork


class FilmsRepository(BaseRepository):
    async def soft_delete(self, film_id: str | uuid.UUID) -> bool:
        uid = film_id if isinstance(film_id, uuid.UUID) else uuid.UUID(str(film_id))
        stmt = (
            update(FilmWork)
            .where(FilmWork.id == uid, FilmWork.is_deleted.is_(False))
            .values(is_deleted=True, modified=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount > 0
