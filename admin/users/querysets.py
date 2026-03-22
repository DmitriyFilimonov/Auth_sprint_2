"""Список «строк» истории для админки: из типов OpenAPI-клиента в модель только для отображения."""

from __future__ import annotations

from datetime import datetime

from django.db import models
from django.utils.dateparse import parse_datetime

from clients.auth_api.auth_api_client.models.history_response_item import (
    HistoryResponseItem,
)


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
