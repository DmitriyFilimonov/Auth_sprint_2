"""Заголовки при ручном HTTP-проксировании (этот сервис → auth).

Почему отдельный модуль
    Здесь собрана «нестандартная» часть прокси: не все заголовки можно
    пересылать на следующий hop как есть. Без контекста через неделю неочевидно,
    зачем что-то выкидывают — см. описание ниже и ссылку на RFC HTTP.

Hop-by-hop (между двумя соседними узлами)
    Часть полей HTTP относится только к *текущему* участку цепочки
    «клиент ↔ прокси ↔ upstream», а не ко всему пути целиком. Их нельзя
    слепо копировать: следующее соединение само выставит свои
    ``Connection``, ``Transfer-Encoding`` и т.д.

    Список имён (в нижнем регистре для сравнения) — обычный набор hop-by-hop
    полей. Актуально: RFC 9110 (HTTP Semantics, в т.ч. ``Connection`` и
    hop-by-hop) и RFC 9112 (HTTP/1.1 Messaging). RFC 7230 по этой теме устарел
    (obsoleted), но термины те же.

Дополнительно для исходящего запроса
    Поле ``Host`` от входящего клиента не пересылаем: для upstream оно должно
    соответствовать хосту из URL; ``aiohttp`` подставляет его из URL запроса.

Ответ upstream → клиенту
    Hop-by-hop из ответа тоже не отдаём клиенту: они описывали hop
    «auth → этот сервис», а не «этот сервис → клиент».
"""

from __future__ import annotations

import aiohttp
from aiohttp import web

# Имена заголовков в нижнем регистре (сравниваем с request.headers так же).
HOP_BY_HOP_HEADER_NAMES = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)

# Исходящий запрос к upstream: hop-by-hop + см. модульный docstring про Host.
_OUTBOUND_REQUEST_SKIP = HOP_BY_HOP_HEADER_NAMES | frozenset({"host"})


def filter_request_headers(request: web.Request) -> dict[str, str]:
    """Заголовки для ``ClientSession.request``: без hop-by-hop и без клиентского Host."""
    out: dict[str, str] = {}
    for k, v in request.headers.items():
        if k.lower() not in _OUTBOUND_REQUEST_SKIP:
            out[k] = v
    return out


def filter_response_headers(headers: aiohttp.typedefs.LooseHeaders) -> dict[str, str]:
    """Заголовки ответа клиенту: без hop-by-hop с участка upstream → этот сервис."""
    out: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() not in HOP_BY_HOP_HEADER_NAMES:
            out[k] = v
    return out
