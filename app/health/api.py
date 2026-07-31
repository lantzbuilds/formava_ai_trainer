"""Thin-slice FastAPI application for Spec 1.

Exists to prove the request chain TLS -> nginx -> Next.js -> FastAPI ->
Postgres before any real application code is migrated. Serves exactly one
route.
"""

import logging
import os

import psycopg
from fastapi import FastAPI, HTTPException

from app.health.checks import check_postgres

logger = logging.getLogger(__name__)


def create_app(dsn: str | None = None) -> FastAPI:
    """Build the health application.

    Args:
        dsn: Postgres connection string. Falls back to FORMAVA_DATABASE_URL.

    Raises:
        ValueError: no DSN supplied and none in the environment. Fails at
            startup rather than serving a broken app.
    """
    resolved = dsn if dsn is not None else os.environ.get("FORMAVA_DATABASE_URL", "")
    if not resolved:
        raise ValueError(
            "No Postgres DSN: pass dsn= or set FORMAVA_DATABASE_URL. "
            "Refusing to start without one."
        )

    application = FastAPI(title="Formava API", version="0.1.0")

    @application.get("/health")
    def health() -> dict[str, str]:
        try:
            result = check_postgres(resolved)
        except psycopg.Error as exc:
            logger.error("Health check failed: %s", exc)
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return result.model_dump()

    return application
