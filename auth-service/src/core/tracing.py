"""
Трассировка (OpenTelemetry → Jaeger по OTLP) и x-request-id.

Зачем OpenTelemetry, а не «ручная отправка в Jaeger»:
  Jaeger принимает готовые спаны в формате OTLP (protobuf по HTTP). Библиотека
  opentelemetry-* собирает эти сообщения за вас. Писать то же «вручную» —
  это по сути повторить OTLP SDK.

Что здесь происходит (простая цепочка):
  1) setup_tracing() — если задан OTEL_EXPORTER_OTLP_ENDPOINT, включаем экспорт
     спанов на Jaeger (коллектор слушает OTLP HTTP, обычно порт 4318).
  2) FastAPIInstrumentor.instrument_app(app) — автоматически создаёт span на
     каждый HTTP-запрос (имя маршрута, статус и т.д.).
  3) RequestIdMiddleware — читает или генерирует x-request-id, кладёт в
     атрибут спана http.request_id и возвращает заголовок в ответе.

Если endpoint не задан (локально без Jaeger), приложение работает как раньше,
только без экспорта спанов.
"""

from __future__ import annotations

import os
import uuid

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


def _normalize_otlp_traces_endpoint() -> str | None:
    raw = (os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip()
    if not raw:
        return None
    base = raw.rstrip("/")
    if base.endswith("/v1/traces"):
        return base
    return f"{base}/v1/traces"


def setup_tracing() -> bool:
    """
    Возвращает True, если включён экспорт в Jaeger (можно вызвать instrument_app).
    """
    endpoint = _normalize_otlp_traces_endpoint()
    if not endpoint:
        return False

    service_name = os.getenv("OTEL_SERVICE_NAME", "auth-service")
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return True


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Добавьте к приложению до вызова FastAPIInstrumentor.instrument_app.
    После инструментирования middleware выполняется уже внутри span’а
    сервера — можно дописать атрибут http.request_id.
    """

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id") or request.headers.get(
            "X-Request-ID"
        )
        rid = incoming or str(uuid.uuid4())

        span = trace.get_current_span()
        if span is not None and span.is_recording():
            span.set_attribute("http.request_id", rid)

        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


def flush_traces() -> None:
    """Вызвать при остановке процесса, чтобы не потерять последние спаны."""
    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush()
