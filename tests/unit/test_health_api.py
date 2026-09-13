import psycopg
import pytest
from fastapi.testclient import TestClient

from app.health.api import create_app
from app.health.checks import PostgresHealth


@pytest.fixture
def client_with_healthy_db(monkeypatch):
    def fake_check(dsn: str) -> PostgresHealth:
        return PostgresHealth(db="ok", pgvector="0.6.0")

    monkeypatch.setattr("app.health.api.check_postgres", fake_check)
    return TestClient(create_app(dsn="postgresql://unused"))


@pytest.fixture
def client_with_broken_db(monkeypatch):
    def fake_check(dsn: str) -> PostgresHealth:
        # Shaped like a real psycopg failure, which names the host, port, role
        # and database. The test below asserts none of that reaches the client.
        raise psycopg.OperationalError(
            'connection to server at "127.0.0.1", port 5432 failed: FATAL: '
            'password authentication failed for user "formava"'
        )

    monkeypatch.setattr("app.health.api.check_postgres", fake_check)
    return TestClient(
        create_app(dsn="postgresql://unused"), raise_server_exceptions=False
    )


def test_health_returns_exact_spec_shape(client_with_healthy_db):
    response = client_with_healthy_db.get("/health")

    assert response.status_code == 200
    assert response.json() == {"db": "ok", "pgvector": "0.6.0"}


def test_health_returns_503_when_database_unreachable(client_with_broken_db):
    response = client_with_broken_db.get("/health")

    # Must fail loudly. A degraded 200 would defeat the purpose.
    assert response.status_code == 503
    assert response.json()["detail"] == "database unavailable"


def test_health_error_does_not_leak_connection_details(client_with_broken_db):
    """/health is unauthenticated and the BFF relays this body to the public
    internet, so the psycopg error must not reach the client."""
    body = client_with_broken_db.get("/health").text

    for secret in ("127.0.0.1", "5432", "formava", "password authentication"):
        assert secret not in body


def test_create_app_requires_a_dsn():
    with pytest.raises(ValueError, match="DSN"):
        create_app(dsn="")


def test_create_app_reads_dsn_from_environment(monkeypatch):
    monkeypatch.setenv("FORMAVA_DATABASE_URL", "postgresql://from-env")
    # Must not raise: this is the production invocation, uvicorn --factory
    # calls create_app() with no arguments.
    app = create_app()
    assert app is not None


def test_create_app_raises_when_environment_dsn_is_absent(monkeypatch):
    monkeypatch.delenv("FORMAVA_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DSN"):
        create_app()
