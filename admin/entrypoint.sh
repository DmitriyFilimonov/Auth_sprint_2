#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate

echo "Starting application..."
exec "$@"
