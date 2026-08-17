#!/usr/bin/env bash
set -e
: "${DATABASE_URL:?Set DATABASE_URL to a PostgreSQL database before starting}"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
alembic upgrade head
python bootstrap.py
python app.py
