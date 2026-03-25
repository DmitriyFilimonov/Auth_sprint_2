-- Мягкое удаление фильмов: ETL увидит изменение по modified и переиндексирует документ.
ALTER TABLE content.film_work
    ADD COLUMN IF NOT EXISTS is_deleted boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN content.film_work.is_deleted IS 'true — фильм скрыт из API; строка и связи в PG сохраняются';
