"""Database health probes for the Formava API.

Deliberately has no fallback behaviour. An unreachable database raises,
so callers surface a 503 rather than reporting healthy while serving an
empty datastore (contrast app/config/database.py:112).
"""

import psycopg
from pydantic import BaseModel


class PostgresHealth(BaseModel):
    """Result of a successful Postgres probe."""

    db: str
    pgvector: str


def check_postgres(dsn: str) -> PostgresHealth:
    """Verify Postgres is reachable and the pgvector extension is installed.

    Raises:
        psycopg.Error: connection failed, or pgvector is not installed.
    """
    with psycopg.connect(dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            row = cur.fetchone()

    if row is None:
        raise psycopg.OperationalError(
            "pgvector extension is not installed in this database"
        )

    return PostgresHealth(db="ok", pgvector=row[0])
