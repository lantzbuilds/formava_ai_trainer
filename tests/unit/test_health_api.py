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
        raise psycopg.OperationalError("connection refused")

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
    assert "connection refused" in response.json()["detail"]


def test_create_app_requires_a_dsn():
    with pytest.raises(ValueError, match="DSN"):
        create_app(dsn="")
