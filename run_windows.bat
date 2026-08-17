@echo off
if "%DATABASE_URL%"=="" (
  echo Set DATABASE_URL to a PostgreSQL database before starting.
  exit /b 1
)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
alembic upgrade head
python bootstrap.py
python app.py
