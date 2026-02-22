from db.postgres import BaseRepository

import uuid
from sqlalchemy import delete
from models.film import FilmDB


class FilmsRepository(BaseRepository):
    async def delete_single(self, film_id: uuid.UUID) -> bool:
        """Удаление фильма из Postgres."""
        query = delete(FilmDB).where(FilmDB.id == film_id)
        result = await self.session.execute(query)
        await self.session.commit()

        return result.rowcount > 0
