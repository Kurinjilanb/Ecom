#!/bin/sh
set -e

# Wait for PostgreSQL to be ready
if [ -n "$DATABASE_HOST" ]; then
    echo "Waiting for PostgreSQL at $DATABASE_HOST:${DATABASE_PORT:-5432}..."
    while ! nc -z "$DATABASE_HOST" "${DATABASE_PORT:-5432}"; do
        sleep 0.2
    done
    echo "PostgreSQL is ready."
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

exec "$@"