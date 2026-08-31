#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${SECRET_KEY:?SECRET_KEY is required}"
: "${TEACHER_ADMIN_EMAIL:?TEACHER_ADMIN_EMAIL is required}"
: "${TEACHER_ADMIN_PASSWORD:?TEACHER_ADMIN_PASSWORD is required}"

migration_attempt=1
until alembic upgrade head; do
  if [ "$migration_attempt" -ge 10 ]; then
    echo "Database migration failed after $migration_attempt attempts." >&2
    exit 1
  fi
  echo "Database is not ready for migrations; retrying in 2 seconds ($migration_attempt/10)." >&2
  migration_attempt=$((migration_attempt + 1))
  sleep 2
done
python bootstrap.py

exec gunicorn \
  --bind "0.0.0.0:${APP_PORT:-5000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  ${GUNICORN_RELOAD:+--reload} \
  --access-logfile - \
  --error-logfile - \
  --log-level "${GUNICORN_LOG_LEVEL:-info}" \
  "app:app"
