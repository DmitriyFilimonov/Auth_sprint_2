from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Generator, Any
from uuid import UUID

import psycopg
from psycopg import Connection
from psycopg.rows import Row
from psycopg.sql import SQL, Identifier

from core.state_storage import StateManager


@dataclass
class PostgresQueries:
    """Dataclass with SQL-templates for PostgresExtractor."""
    modified_ids = '''
        SELECT id, modified
        FROM {schema}.{table}
        WHERE modified > %s
        ORDER BY modified
        LIMIT %s;
        '''

    related_ids = '''
        SELECT fw.id, fw.modified
        FROM {schema}.{main_table} fw
        LEFT JOIN {schema}.{related_table} rt
        ON rt.{main_table_id} = fw.id
        WHERE rt.{related_table_id} = ANY(%s)
        GROUP BY fw.id
        ORDER BY fw.modified;
        '''

    film_work = '''
        SELECT
            fw.id,
            fw.title,
            fw.description,
            fw.rating,
            fw.type,
            fw.created,
            fw.modified,
            fw.is_deleted,
            COALESCE (
                json_agg(
                    DISTINCT jsonb_build_object(
                       'role', pfw.role,
                       'id', p.id,
                       'full_name', p.full_name
                    )
                ) FILTER (WHERE p.id is not null),
                '[]'
            ) as persons,
            COALESCE (
                json_agg(
                    DISTINCT jsonb_build_object(
                       'id', g.id,
                       'name', g.name
                    )
                ) FILTER (WHERE g.id is not null),
                '[]'
            ) as genres
        FROM {schema}.film_work fw
        LEFT JOIN {schema}.person_film_work pfw ON pfw.film_work_id = fw.id
        LEFT JOIN {schema}.person p ON p.id = pfw.person_id
        LEFT JOIN {schema}.genre_film_work gfw ON gfw.film_work_id = fw.id
        LEFT JOIN {schema}.genre g ON g.id = gfw.genre_id
        WHERE fw.id = ANY(%s)
        GROUP BY fw.id
        ORDER BY fw.modified;
        '''

    person = '''
        SELECT
            p.id,
            p.full_name
        FROM {schema}.person p
        WHERE p.id = ANY(%s)
        ORDER BY p.modified;
        '''

    genre = '''
        SELECT
            g.id,
            g.name,
            g.description
        FROM {schema}.genre g
        WHERE g.id = ANY(%s)
        ORDER BY g.modified;
        '''

    def get_query(self, attribute_name: str):
        """Get class attribute by name."""
        return getattr(self, attribute_name)


class PostgresExtractor:
    """Extractor from PostgresSQL."""
    def __init__(self, state: StateManager, schema: str, main_table: str):
        self.schema = schema
        self.main_table = main_table
        self.state = state
        self.base_batch_size = 100
        self.queries = PostgresQueries()
        self.logger = logging.getLogger(__name__)

    def extract_data(self, connection: Connection,
                     tables: list[dict]) -> Generator[dict, Any, None]:
        """Extract data from PostgresSQL using batch."""
        self.logger.info('Extract data from Postgres')
        for table in tables:
            batch_size = table.get('batch_size')
            table_name = table.get('name')
            state_key = f'last_sync_dt-{table_name}'
            self.logger.info(f'Check "{table_name}"')

            while True:
                last_sync_dt = self.state.get_state(state_key)
                last_sync_dt = self._parse_dt(last_sync_dt)
                self.logger.info(f'Search from {last_sync_dt}')

                batch = self._get_modified_ids(
                    connection, table_name, last_sync_dt,
                    batch_size, self.queries.modified_ids)
                if len(batch) == 0:
                    break
                modified_ids = self._get_only_ids(batch)
                self.logger.info(f'Find {len(modified_ids)} ids')
                yield {'model': table_name,
                       'data': self._fetch_data(
                           connection, modified_ids,
                           self.queries.get_query(table_name))}

                if table_name != self.main_table:
                    for internal_batch in self._get_related_ids(
                            connection, modified_ids, table_name,
                            self.queries.related_ids):
                        related_ids = self._get_only_ids(internal_batch)
                        self.logger.info(f'Find {len(related_ids)} related ids')
                        yield {'model': self.main_table,
                               'data': self._fetch_data(
                                   connection, related_ids,
                                   self.queries.get_query(self.main_table))}

                last_modified_dt = batch[-1].get('modified')
                self.state.set_state(state_key, last_modified_dt.isoformat())

    @staticmethod
    def _parse_dt(_dt: str | None) -> datetime:
        """Parse string in datetime format."""
        if _dt is None:
            return datetime.min
        return datetime.fromisoformat(_dt)

    @staticmethod
    def _get_only_ids(batch: list[Row]) -> list[UUID]:
        """Get only ids from batch."""
        return [row.get('id') for row in batch]

    def _get_modified_ids(
            self, connection: Connection, table: str, last_load: datetime,
            batch_size: int, query: str,) -> list[Row]:
        """Get modified ids from last load time by batch size."""
        with connection.cursor() as cursor:
            cursor.execute(SQL(query).format(
                schema=Identifier(self.schema),
                table=Identifier(table)),
                (last_load, batch_size))
            return cursor.fetchall()

    def _get_related_ids(
            self, connection: Connection, ids: list[UUID], table: str,
            query: str) -> Generator[list[Row], None, None]:
        """Get related ids using batch."""
        with connection.cursor() as cursor:
            cursor.execute(SQL(query).format(
                schema=Identifier(self.schema),
                main_table=Identifier(self.main_table),
                main_table_id=Identifier(f'{self.main_table}_id'),
                related_table=Identifier(f'{table}_{self.main_table}'),
                related_table_id=Identifier(f'{table}_id')
                ),(ids,))
            while results := cursor.fetchmany(size=self.base_batch_size):
                yield results

    def _fetch_data(self, connection: Connection, ids: list[UUID],
                    query: str) -> list[Row]:
        """Fetch full data from PostgresSQL."""
        with connection.cursor() as cursor:
            cursor.execute(SQL(query).format(
                schema=Identifier(self.schema)),
                (ids,))
            return cursor.fetchall()
