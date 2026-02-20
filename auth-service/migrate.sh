#!/bin/bash

echo "running migrations..."
alembic upgrade head

echo "run auth-service..."
exec "$@"
