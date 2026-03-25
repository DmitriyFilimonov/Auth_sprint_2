"""ORM-модели Postgres (схема content)."""

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy.dialects.postgresql import UUID

from db.postgres import Base


class FilmWork(Base):
    __tablename__ = "film_work"
    __table_args__ = {"schema": "content"}

    id = Column(UUID(as_uuid=True), primary_key=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    modified = Column(DateTime(timezone=False), nullable=True)
