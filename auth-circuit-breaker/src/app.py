import asyncio
import logging

import aiohttp
from aiohttp import web

from src.circuit import CircuitBreaker
from src.config import Settings
from src.proxy_headers import filter_request_headers, filter_response_headers

logger = logging.getLogger(__name__)


def is_service_error_status(status: int) -> bool:
    return status >= 500


def build_service_request_url(settings: Settings, request: web.Request) -> str:
    base = settings.auth_service_base_url.rstrip("/")
    path = request.path if request.path.startswith("/") else f"/{request.path}"
    url = f"{base}{path}"
    if request.query_string:
        url = f"{url}?{request.query_string}"
    return url


async def health(_: web.Request) -> web.StreamResponse:
    return web.Response(text="ok")


async def proxy_handler(request: web.Request) -> web.StreamResponse:
    if request.path == "/health":
        return await health(request)

    settings: Settings = request.app["settings"]
    cb: CircuitBreaker = request.app["circuit"]

    request_refuse_reason = await cb.try_get_permission_to_request()
    if request_refuse_reason is not None:
        return web.json_response({"detail": request_refuse_reason.message}, status=503)

    url = build_service_request_url(settings, request)
    timeout = aiohttp.ClientTimeout(total=settings.request_timeout_seconds)
    session: aiohttp.ClientSession = request.app["http_session"]

    try:
        body = await request.read()
        req_headers = filter_request_headers(request)

        async with session.request(
            request.method,
            url,
            headers=req_headers,
            data=body if body else None,
            timeout=timeout,
            allow_redirects=False,
        ) as resp:
            data = await resp.read()
            resp_headers = filter_response_headers(resp.headers)

            if is_service_error_status(resp.status):
                await cb.on_service_failure()
            else:
                await cb.on_service_success()

            return web.Response(
                status=resp.status,
                body=data,
                headers=resp_headers,
            )
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.warning("Auth service request failed: %s", e)
        await cb.on_service_failure()
        return web.json_response(
            {
                "detail": "Auth service unreachable through the circuit breaker.",
            },
            status=503,
        )


def create_app(settings: Settings) -> web.Application:
    app = web.Application(client_max_size=1024**2 * 50)
    app["settings"] = settings
    app["circuit"] = CircuitBreaker(settings)

    async def on_startup(app_: web.Application) -> None:
        # ClientSession needs a running event loop (aiohttp 3.x).
        app_["http_session"] = aiohttp.ClientSession()

    async def on_cleanup(app_: web.Application) -> None:
        await app_["http_session"].close()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    app.router.add_route("*", "/{tail:.*}", proxy_handler)
    return app
