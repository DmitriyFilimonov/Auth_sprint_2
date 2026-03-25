from dataclasses import dataclass

from models.film import Film


@dataclass
class FilmListResult:
    items: list[Film] | None
    total: int
