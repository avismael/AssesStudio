import os
import atexit
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")


def _bounded_int(name, default, minimum, maximum):
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


POOL_MIN_SIZE = _bounded_int("DB_POOL_MIN_SIZE", 1, 0, 20)
POOL_MAX_SIZE = _bounded_int("DB_POOL_MAX_SIZE", 10, 1, 100)
if POOL_MIN_SIZE > POOL_MAX_SIZE:
    POOL_MIN_SIZE = POOL_MAX_SIZE

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=POOL_MIN_SIZE,
    max_size=POOL_MAX_SIZE,
    timeout=_bounded_int("DB_POOL_TIMEOUT", 10, 1, 120),
    kwargs={"row_factory": dict_row},
    open=False,
)


def open_pool():
    if pool.closed:
        pool.open(wait=True)


@contextmanager
def connection():
    open_pool()
    with pool.connection() as conn:
        yield conn


def close_pool():
    if not pool.closed:
        pool.close()


atexit.register(close_pool)
