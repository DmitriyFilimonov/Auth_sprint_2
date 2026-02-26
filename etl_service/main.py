#!/usr/bin/env python
import time

import psycopg

from core.backoff import backoff
from core.docker_stopper import DockerStop
from core.logger import logger
from core.settings import settings
from core.state_storage import JsonFileStorage, StateManager

from db.elastic import ElasticClientFactory, ElasticConnector
from db.postgres import PostgresConnectionFactory, PostgresConnector

from services.extractor import PostgresExtractor
from services.loader import ElasticLoader
from services.transformer import DataTransformer


@backoff(psycopg.OperationalError)  # backoff for Elastic inside ElasticLoader
def load_from_postgres_to_elastic():
    """Main function for load from PostgresSQL to Elasticsearch."""
    state_manager = StateManager(JsonFileStorage())
    pg_factory = PostgresConnectionFactory(settings.postgres_settings.get_dsn())
    es_factory = ElasticClientFactory(settings.elastic_settings.get_host())
    postgres = PostgresConnector(pg_factory)
    elastic = ElasticConnector(es_factory)
    with postgres.connect() as pg_connection, elastic.connect() as es_client:
        extractor = PostgresExtractor(
            state_manager,
            settings.postgres_settings.dbschema,
            settings.postgres_settings.main_table
        )
        transformer = DataTransformer()
        loader = ElasticLoader(settings.elastic_settings.indices)
        loader.check_indices_exists(es_client)

        for batch in extractor.extract_data(
                pg_connection, settings.postgres_settings.tables):
            transformed_data = transformer.transform_data(batch)
            loader.load_data(es_client, transformed_data)


if __name__ == '__main__':
    logger.info('Start ETL application')
    loop_stopper = DockerStop()
    sleep_time = settings.main_loop_time
    while True:
        logger.info('Start loading iteration')
        load_from_postgres_to_elastic()
        if loop_stopper.stop_now:
            logger.info('Catch stop command from Docker')
            break
        logger.info(f'Successful iteration. Go sleep for {sleep_time} sec.')
        time.sleep(sleep_time)
    logger.info('Stop ETL application')
