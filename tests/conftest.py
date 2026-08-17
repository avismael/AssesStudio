import os
import re
import sys
from urllib.parse import urlparse

import psycopg
from alembic import command
from alembic.config import Config
import pytest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()
if not TEST_DATABASE_URL:
    raise pytest.UsageError("TEST_DATABASE_URL is required; tests never use an application database")


def require_test_database_name(database_name, source):
    if not re.search(r"(^test_|_test$|_test_)", str(database_name or "").lower()):
        raise pytest.UsageError(f"{source} database name must use an explicit test_/_test naming boundary")


database_name = urlparse(TEST_DATABASE_URL).path.lstrip("/")
require_test_database_name(database_name, "TEST_DATABASE_URL")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("TEACHER_ADMIN_EMAIL", "test-admin@example.invalid")
os.environ.setdefault("TEACHER_ADMIN_PASSWORD", "TestAdmin12345")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key")

with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as connection:
    require_test_database_name(connection.info.dbname, "Effective PostgreSQL")
    connection.execute("DROP SCHEMA public CASCADE")
    connection.execute("CREATE SCHEMA public")

alembic_config = Config(os.path.join(ROOT, "alembic.ini"))
command.upgrade(alembic_config, "head")

import app  # noqa: E402

app.bootstrap_runtime_data()


def pytest_sessionfinish(session, exitstatus):
    app.close_pool()
