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
