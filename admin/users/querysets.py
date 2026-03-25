"""Список «строк» истории для админки: из типов OpenAPI-клиента в модель только для отображения."""

from __future__ import annotations

from datetime import datetime

from django.db import models
from django.utils.dateparse import parse_datetime

from clients.auth_api.auth_api_client.models.history_response_item import (
    HistoryResponseItem,
)
from clients.films_api.movie_theater_client.models.film_short_response import (
    FilmShortResponse,
)
from clients.films_api.movie_theater_client.types import Unset


def _created_at_to_datetime(value: str) -> datetime:
    s = value.replace("Z", "+00:00")
    dt = parse_datetime(s)
    if dt is not None:
        return dt
    return datetime.fromisoformat(s)


class LoginHistoryQuerySet(list):
    def __init__(
        self,
        data: list[HistoryResponseItem],
        *,
        model: type[models.Model],
    ):
        rows = [
            model(
                id=item.id,
                user_id=item.user_id,
                user_agent=item.user_agent,
                created_at=_created_at_to_datetime(item.created_at),
            )
            for item in data
        ]
        super().__init__(rows)
        self.model = model
        self.query = type(
            "Query", (), {"select_related": False, "order_by": (), "distinct": False}
        )

    @property
    def _meta(self):
        """Для admin.utils.model_format_dict (Django 6+ и фейковые queryset’ы)."""
        return self.model._meta

    @property
    def verbose_name(self):
        return self.model._meta.verbose_name

    @property
    def verbose_name_plural(self):
        return self.model._meta.verbose_name_plural

    def count(self):
        return len(self)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def only(self, *args, **kwargs):
        return self

    def defer(self, *args, **kwargs):
        return self

    def select_related(self, *args, **kwargs):
        return self

    def prefetch_related(self, *args, **kwargs):
        return self

    def _clone(self):
        return self


def _film_imdb_rating(item: FilmShortResponse) -> float | None:
    if isinstance(item.imdb_rating, Unset):
        return None
    return item.imdb_rating


def _film_genres_display(item: FilmShortResponse) -> str:
    if isinstance(item.genres, Unset) or item.genres is None:
        return ""
    return ", ".join(g.name for g in item.genres)


class FilmListingQuerySet(list):
    """Страница каталога из OpenAPI-клиента: total — всего по фильтру, строки — только текущая страница."""

    def __init__(
        self,
        data: list,
        *,
        total: int,
        model: type[models.Model],
        _prefetched_rows: list | None = None,
    ):
        if _prefetched_rows is not None:
            super().__init__(list(_prefetched_rows))
            self._total = total
            self.model = model
            self.query = type(
                "Query", (), {"select_related": False, "order_by": (), "distinct": False}
            )
            return

        rows = []
        for item in data:
            if not isinstance(item, FilmShortResponse):
                continue
            rows.append(
                model(
                    uuid=item.uuid,
                    title=item.title,
                    imdb_rating=_film_imdb_rating(item),
                    genres_display=_film_genres_display(item),
                )
            )
        super().__init__(rows)
        self._total = total
        self.model = model
        self.query = type(
            "Query", (), {"select_related": False, "order_by": (), "distinct": False}
        )

    @property
    def _meta(self):
        """Для admin.utils.model_format_dict (Django 6+ и фейковые queryset’ы)."""
        return self.model._meta

    @property
    def verbose_name(self):
        return self.model._meta.verbose_name

    @property
    def verbose_name_plural(self):
        return self.model._meta.verbose_name_plural

    def count(self):
        return self._total

    def filter(self, *args, **kwargs):
        """Массовые действия админки делают .filter(pk__in=выбранные_id) — без этого удалялась вся страница."""
        if args:
            return self
        if len(kwargs) != 1:
            return self

        pks = None
        if "pk__in" in kwargs:
            pks = kwargs["pk__in"]
        elif "uuid__in" in kwargs:
            pks = kwargs["uuid__in"]
        elif "pk" in kwargs:
            pks = [kwargs["pk"]]
        elif "uuid" in kwargs:
            pks = [kwargs["uuid"]]

        if pks is None:
            return self

        if not pks:
            return FilmListingQuerySet(
                [], total=0, model=self.model, _prefetched_rows=[]
            )

        pks_set = {str(p) for p in pks}
        filtered = [obj for obj in self if str(obj.pk) in pks_set]
        return FilmListingQuerySet(
            [],
            total=len(filtered),
            model=self.model,
            _prefetched_rows=filtered,
        )

    def order_by(self, *args, **kwargs):
        return self

    def only(self, *args, **kwargs):
        return self

    def defer(self, *args, **kwargs):
        return self

    def select_related(self, *args, **kwargs):
        return self

    def prefetch_related(self, *args, **kwargs):
        return self

    def _clone(self):
        return FilmListingQuerySet(
            [],
            total=self._total,
            model=self.model,
            _prefetched_rows=list(self),
        )
