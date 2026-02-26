#!/bin/bash

echo "running migrations..."
alembic upgrade head

python3 -m src.db.create_super_user
echo "Superuser is created"

echo "run auth-service..."
exec "$@"
