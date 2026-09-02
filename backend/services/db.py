import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    engine = None
else:
    # Clean pgbouncer parameter from DSN since psycopg2 does not support it
    if "pgbouncer=" in DATABASE_URL:
        from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
        u = urlparse(DATABASE_URL)
        q = parse_qsl(u.query)
        q_clean = [(k, v) for k, v in q if k != "pgbouncer"]
        query_clean = urlencode(q_clean)
        u_clean = u._replace(query=query_clean)
        DATABASE_URL = urlunparse(u_clean)

    # Use NullPool since we are connecting via pgBouncer transaction pooling mode
    # to prevent pgbouncer connections accumulation.
    engine = create_engine(DATABASE_URL, poolclass=NullPool)


def get_engine():
    """Return the SQLAlchemy engine."""
    if engine is None:
        raise ValueError("DATABASE_URL is not defined in the environment variables.")
    return engine


@contextmanager
def get_db_conn():
    """Context manager to yield a database connection and ensure cleanup."""
    eng = get_engine()
    conn = eng.connect()
    try:
        yield conn
    finally:
        conn.close()
