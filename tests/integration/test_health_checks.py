import os

import psycopg
import pytest

from app.health.checks import PostgresHealth, check_postgres

DSN = os.environ.get(
    "FORMAVA_TEST_DSN",
    "postgresql://formava:formava_dev@localhost:5432/formava",
)


def test_check_postgres_reports_ok_and_pgvector_version():
    result = check_postgres(DSN)

    assert isinstance(result, PostgresHealth)
    assert result.db == "ok"
    # pgvector reports a semver-ish string such as "0.6.0" or "0.8.0"
    assert result.pgvector
    assert result.pgvector[0].isdigit()


def test_check_postgres_raises_when_database_unreachable():
    bad_dsn = "postgresql://formava:formava_dev@localhost:59999/formava"

    # Must raise, never return a degraded value. No silent fallback.
    with pytest.raises(psycopg.Error):
        check_postgres(bad_dsn)


def test_check_postgres_raises_when_pgvector_missing(monkeypatch):
    """Reachable database, no pgvector, must still raise.

    This is the spec's headline property -- db:"ok" is unreachable without a
    pgvector version -- and it was the one branch nothing exercised directly.
    The extension is queried by name, so pointing the query at a name that
    cannot exist reproduces the empty-row case without dropping the real
    extension out from under a live database.
    """
    real_execute = psycopg.Cursor.execute

    def execute_missing_extension(self, query, *args, **kwargs):
        if "pg_extension" in str(query):
            query = (
                "SELECT extversion FROM pg_extension "
                "WHERE extname = 'vector_does_not_exist'"
            )
        return real_execute(self, query, *args, **kwargs)

    monkeypatch.setattr(psycopg.Cursor, "execute", execute_missing_extension)

    with pytest.raises(psycopg.Error, match="pgvector"):
        check_postgres(DSN)
