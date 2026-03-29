import logging
import os

from aiohttp import web

from src.app import create_app
from src.config import settings


def _configure_logging() -> None:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )


_configure_logging()

app = create_app(settings)

if __name__ == "__main__":
    web.run_app(app, host=settings.listen_host, port=settings.listen_port)
