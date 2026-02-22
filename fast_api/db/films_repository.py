from postgres import BaseRepository

import uuid
from sqlalchemy import delete
from models.film import FilmDB  # Ваша модель фильма


class FilmsRepository(BaseRepository):
    async def delete_single(self, film_id: uuid.UUID) -> bool:
        """Удаление фильма из Postgres."""
        query = delete(FilmDB).where(FilmDB.id == film_id)
        result = await self.session.execute(query)
        await self.session.commit()

        # rowcount покажет, была ли удалена запись
        return result.rowcount > 0
