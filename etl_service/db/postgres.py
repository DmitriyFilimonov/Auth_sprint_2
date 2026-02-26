from contextlib import contextmanager
import logging
from typing import Any, Generator

import psycopg
from psycopg import connect, Connection, ClientCursor
from psycopg import OperationalError as PGOperationalError
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from core.backoff import backoff


# вынесем создание коннекта отдельно
class PostgresConnectionFactory:
    """Create PostgresSQL connection with backoff."""
    def __init__(self, dsn: dict):
        self.dsn = make_conninfo(**dsn)

    @backoff(PGOperationalError)
    def create(self) -> Connection:
        return connect(self.dsn, row_factory=dict_row,
                       cursor_factory=ClientCursor)


class PostgresConnector:
    """PostgresSQL context manager connector."""

    def __init__(self, postgres_factory: PostgresConnectionFactory):
        self.postgres_factory = postgres_factory
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def connect(self) -> Generator[Connection, Any, None]:
        """PostgresSQL context manager."""
        conn = None
        try:
            conn = self.postgres_factory.create()
            self.logger.info('Successful connection to PostgresSQL')
            yield conn
        except psycopg.OperationalError:
            self.logger.exception('Get connection error from PostgresSQL')
            raise
        finally:
            if conn:
                conn.close()
                self.logger.info('Close connection with PostgresSQL')
