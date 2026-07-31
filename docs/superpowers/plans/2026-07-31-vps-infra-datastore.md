# Formava VPS Infrastructure + Datastore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provision the Vultr VPS to host Formava alongside Clio — Postgres 16 + pgvector, TLS, systemd supervision, security remediation — and prove the full request chain with a `/health` payload, without deploying any Gradio code.

**Architecture:** nginx terminates TLS for `formava.io` (Next.js BFF on `127.0.0.1:3001`) and `clio.lantzbuilds.com` (Clio on `127.0.0.1:3000`). The Next.js BFF fetches server-side from FastAPI on `127.0.0.1:8000`, which reads Postgres over loopback. No application process binds a public interface; nginx is the only thing ufw exposes. Render stays live and untouched as the fallback throughout.

**Tech Stack:** Ubuntu 24.04, Python 3.12, FastAPI + uvicorn, psycopg 3, Postgres 16 + pgvector 0.6.0, Node 20, Next.js 15 (App Router), nginx 1.24, certbot, systemd, ufw, fail2ban.

**Spec:** `docs/superpowers/specs/2026-07-26-formava-vps-infra-design.md`

---

## Global Constraints

- **Never deploy Gradio to the VPS.** `app/pages/*`, `app/routes.py`, `app/theme.py`, `app/config/state.py` are deleted in Spec 4 and must not be installed or run on the host.
- **Render stays live and unmodified.** This plan is not a cutover. Do not touch Render config or DNS for `*.onrender.com`.
- **No schema beyond `CREATE EXTENSION vector`.** Tables, models, and migrations are Spec 2.
- Python **3.12** (system interpreter, `/usr/bin/python3`). Do not install 3.11.
- Node **20** (system, `v20.20.2`). `frontend/Dockerfile` currently says `node:18-alpine` — update to 20.
- Postgres **`postgresql-16`** (`16.14-0ubuntu0.24.04.1`) and **`postgresql-16-pgvector`** (`0.6.0-1`) from Ubuntu repos. No PGDG repo.
- Postgres tuning, exact values: `shared_buffers=256MB`, `effective_cache_size=1GB`, `max_connections=50`.
- systemd memory caps, exact values: `formava-api.service` → `MemoryMax=768M`; `formava-web.service` → `MemoryMax=512M`.
- Bindings: FastAPI `127.0.0.1:8000`, Next.js `127.0.0.1:3001`, Clio `127.0.0.1:3000`, Postgres loopback only. **No process binds `0.0.0.0`.**
- ufw final state: **22, 80, 443 only.**
- Secrets live in `/etc/formava/formava.env`, owner `root:root`, mode `0600`. Never rsynced, never committed.
- Hosts: `formava.io`, `www.formava.io`, `clio.lantzbuilds.com`. **No `api.formava.io`** — FastAPI has no public vhost.
- `/health` response body, exact shape: `{"db": "ok", "pgvector": "<version>"}`. Failure returns HTTP **503**, never a degraded 200.
- **No silent fallbacks.** Do not replicate `app/config/database.py:112` (`_create_mock_database`). Missing config or an unreachable database is a startup failure or a 503.
- CI runs `ruff check app/` and `ruff format --check app/` with no config file, so ruff defaults apply (line length 88). All new `app/` code must pass both.
- VPS: `144.202.88.7`, user `root`. SSH via `scripts/deploy.sh`-style `sshpass`/key auth already configured in `../clio-ai-assitant/.env`.

## Manual Steps (Human, Not Agent)

Three things an agent cannot do. The plan halts at each until confirmed:

| Where | Action |
|-------|--------|
| Task 5 Step 1 | Create DNS A records for `formava.io`, `www.formava.io` → `144.202.88.7` |
| Task 6 Step 1 | Create DNS A record for `clio.lantzbuilds.com` → `144.202.88.7` |
| Task 6 Steps 5, 7 | Edit the iOS Shortcut URL, then its bearer token |

## 🛑 Two Irreversible-Order Gates

**Gate A — Task 6 (Clio cutover).** Steps 1→9 must not be reordered. The iOS Shortcut is a client that cannot be updated remotely; closing port 3000 before the Shortcut is verified on HTTPS breaks voice capture *silently* — no error surfaces, transcripts just stop arriving.

**Gate B — Task 8 (SSH hardening).** Verify key-only login in a **second, separate SSH session** before disabling password auth. Getting this wrong locks you out of the host, and recovery requires Vultr's web console.

---

## File Structure

**New Python — the slim API slice.** Deliberately separate from the Gradio monolith's `requirements.txt`, which is dismantled in Specs 2–4.

| File | Responsibility |
|------|----------------|
| `app/health/__init__.py` | Package marker (empty) |
| `app/health/checks.py` | `check_postgres(dsn)` → `PostgresHealth`. Pure DB probe, no HTTP. |
| `app/health/api.py` | FastAPI app factory + `/health` route. No DB logic. |
| `requirements-api.txt` | Slim production deps for the VPS venv |
| `requirements-api-dev.txt` | Adds test/lint tooling |
| `tests/unit/test_health_api.py` | Route behaviour, DB probe mocked |
| `tests/integration/test_health_checks.py` | Real Postgres via Compose/CI service |
| `docker-compose.postgres.yml` | Local Postgres 16 + pgvector for dev and tests |

**Next.js scaffold repair.**

| File | Responsibility |
|------|----------------|
| `frontend/package.json` | Manifest — **missing, never committed** |
| `frontend/package-lock.json` | Lockfile — **missing**; `npm ci` and CI cache depend on it |
| `frontend/tsconfig.json` | TS config + `@/*` path alias — **missing** |
| `frontend/src/lib/api/client.ts` | `apiClient` — **missing**, imported by `AuthContext.tsx` |
| `frontend/src/app/api/health/route.ts` | BFF route handler; server-side fetch of FastAPI `/health` |

**Host provisioning.**

| File | Responsibility |
|------|----------------|
| `scripts/vps/provision_postgres.sh` | Idempotent Postgres + pgvector install and tuning |
| `scripts/vps/formava-api.service` | systemd unit, uvicorn |
| `scripts/vps/formava-web.service` | systemd unit, Next.js standalone |
| `scripts/vps/nginx-formava.conf` | `formava.io` vhost |
| `scripts/vps/nginx-clio.conf` | `clio.lantzbuilds.com` vhost, allowlist + SSE |
| `scripts/vps/fail2ban-nginx.local` | nginx jails |
| `scripts/vps/pg_backup.sh` + `.service` + `.timer` | Nightly `pg_dump`, 7-day retention |
| `scripts/deploy_vps.sh` | rsync → venv → restart, with subcommands |
| `scripts/vps/verify.sh` | Re-runnable assertion of every §6 exit criterion |

---

## Task 1: FastAPI `/health` slice with real Postgres tests

Pure local work. No VPS access needed. Establishes the ≥80% coverage standard on new code from the outset.

**Files:**
- Create: `app/health/__init__.py`, `app/health/checks.py`, `app/health/api.py`
- Create: `requirements-api.txt`, `requirements-api-dev.txt`, `docker-compose.postgres.yml`
- Create: `tests/integration/__init__.py`, `tests/integration/test_health_checks.py`, `tests/unit/test_health_api.py`
- Modify: `.github/workflows/ci.yml` (add a Postgres service to `test-backend`)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `app.health.checks.PostgresHealth` — Pydantic model, fields `db: str`, `pgvector: str`
  - `app.health.checks.check_postgres(dsn: str) -> PostgresHealth` — raises `psycopg.Error` on failure, never returns a degraded value
  - `app.health.api.create_app() -> FastAPI` and module-level `app` — uvicorn target is `app.health.api:app`
  - `/health` → `200 {"db": "ok", "pgvector": "<version>"}` or `503 {"detail": "..."}`

- [ ] **Step 1: Add the dependency files**

`requirements-api.txt` — versions for shared packages match the existing pins in `requirements.txt`:

```
# Slim production dependencies for the Formava API slice (Spec 1).
# Deliberately separate from requirements.txt (the Gradio monolith),
# which is dismantled in Specs 2-4.
fastapi==0.115.12
uvicorn[standard]==0.34.2
pydantic==2.11.5
python-dotenv==1.1.0
psycopg[binary]>=3.2,<4
```

`requirements-api-dev.txt`:

```
-r requirements-api.txt
pytest==8.3.4
httpx==0.28.1
ruff==0.11.12
```

- [ ] **Step 2: Add local Postgres for dev and tests**

`docker-compose.postgres.yml`:

```yaml
# Local Postgres for development and integration tests.
# The VPS runs Postgres natively under systemd; this is dev-only.
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: formava_postgres
    environment:
      POSTGRES_USER: formava
      POSTGRES_PASSWORD: formava_dev
      POSTGRES_DB: formava
    ports:
      - "5432:5432"
    volumes:
      - formava_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U formava -d formava"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  formava_pgdata:
    name: formava_pgdata
```

Start it and enable the extension:

```bash
docker compose -f docker-compose.postgres.yml up -d
docker exec formava_postgres psql -U formava -d formava -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

- [ ] **Step 3: Write the failing integration test**

`tests/integration/__init__.py` — empty file.

`tests/integration/test_health_checks.py`:

```python
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
```

- [ ] **Step 4: Run it to confirm it fails**

Run: `python -m pytest tests/integration/test_health_checks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.health'`

- [ ] **Step 5: Implement the probe**

`app/health/__init__.py` — empty file.

`app/health/checks.py`:

```python
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
```

- [ ] **Step 6: Run the integration test to confirm it passes**

Run: `python -m pytest tests/integration/test_health_checks.py -v`
Expected: 2 passed

- [ ] **Step 7: Write the failing API test**

`tests/unit/test_health_api.py`:

```python
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
```

- [ ] **Step 8: Run it to confirm it fails**

Run: `python -m pytest tests/unit/test_health_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.health.api'`

- [ ] **Step 9: Implement the API**

`app/health/api.py`:

```python
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


app = create_app()
```

- [ ] **Step 10: Run the full suite and the linters**

```bash
export FORMAVA_DATABASE_URL="postgresql://formava:formava_dev@localhost:5432/formava"
python -m pytest tests/ -v
ruff check app/
ruff format --check app/
```

Expected: all tests pass (including the pre-existing `test_hevy_api.py`), both ruff commands clean.

- [ ] **Step 11: Add Postgres to CI so the integration test can run**

In `.github/workflows/ci.yml`, inside the `test-backend` job, add a `services:` block directly after `runs-on: ubuntu-latest` and before `strategy:`:

```yaml
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: formava
          POSTGRES_PASSWORD: formava_dev
          POSTGRES_DB: formava
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U formava -d formava"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
```

Then change the `Install dependencies` step to also install the API dev deps, and add an extension-enabling step before `Run tests`:

```yaml
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-api-dev.txt

    - name: Enable pgvector
      run: |
        PGPASSWORD=formava_dev psql -h localhost -U formava -d formava \
          -c "CREATE EXTENSION IF NOT EXISTS vector;"

    - name: Run tests
      env:
        FORMAVA_DATABASE_URL: postgresql://formava:formava_dev@localhost:5432/formava
        FORMAVA_TEST_DSN: postgresql://formava:formava_dev@localhost:5432/formava
      run: |
        pytest tests/ -v
```

- [ ] **Step 12: Commit**

```bash
git add app/health requirements-api.txt requirements-api-dev.txt \
        docker-compose.postgres.yml tests/unit/test_health_api.py \
        tests/integration .github/workflows/ci.yml
git commit -m "feat: add FastAPI /health slice with pgvector probe

Thin-slice payload for Spec 1. Fails loudly with 503 rather than
reporting healthy on an unreachable database. Slim requirements-api.txt
keeps the VPS venv independent of the Gradio monolith's dependencies."
```

---

## Task 2: Repair the Next.js scaffold and add the BFF health route

The scaffold cannot build today: `package.json`, `package-lock.json`, `tsconfig.json`, and `src/lib/api/client.ts` are all absent, and `AuthContext.tsx` imports that missing module. `git log --all -- frontend/package.json` is empty, so the manifest was never committed.

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/src/lib/api/client.ts`, `frontend/src/app/api/health/route.ts`
- Generate: `frontend/package-lock.json`, `frontend/next-env.d.ts`
- Modify: `frontend/next.config.ts`, `frontend/Dockerfile`

**Interfaces:**
- Consumes: `app.health.api` `/health` contract from Task 1 — `200 {"db": string, "pgvector": string}` or `503 {"detail": string}`.
- Produces:
  - `frontend/src/lib/api/client.ts` exports `apiClient` and `ApiResponse<T>`
  - `apiClient.login(username: string, password: string): Promise<ApiResponse<{ user: User }>>`
  - `apiClient.register(userData: RegisterForm): Promise<ApiResponse<{ user: User }>>`
  - `apiClient.logout(): Promise<void>`
  - `apiClient.health(): Promise<ApiResponse<{ db: string; pgvector: string }>>`
  - `GET /api/health` on the Next.js server, proxying FastAPI server-side
  - `next.config.ts` sets `output: "standalone"`, required by `formava-web.service`

- [ ] **Step 1: Create the manifest**

Tailwind v4 is already implied by `src/app/globals.css` (`@import "tailwindcss"`) and `postcss.config.mjs` (`@tailwindcss/postcss`), so those deps are required, not optional.

`frontend/package.json`:

```json
{
  "name": "formava-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint"
  },
  "dependencies": {
    "next": "^15.1.6",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@eslint/eslintrc": "^3.2.0",
    "@tailwindcss/postcss": "^4.0.0",
    "@types/node": "^20.17.16",
    "@types/react": "^19.0.8",
    "@types/react-dom": "^19.0.3",
    "eslint": "^9.19.0",
    "eslint-config-next": "^15.1.6",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.7.3"
  }
}
```

- [ ] **Step 2: Create the TypeScript config**

The `@/*` alias is what every existing import relies on.

`frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Install and confirm the build fails on the missing module**

```bash
cd frontend && npm install
npx tsc --noEmit
```

Expected: FAIL — `Cannot find module '@/lib/api/client'` from `src/contexts/AuthContext.tsx`. This confirms the gap before filling it.

- [ ] **Step 4: Create the API client**

Signatures are dictated by existing calls in `AuthContext.tsx:55,83,107`. Auth methods throw deliberately — auth is Spec 4, and a throwing stub is honest where a fake success would be misleading.

`frontend/src/lib/api/client.ts`:

```typescript
import type { RegisterForm, User } from '@/types';

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface HealthPayload {
  db: string;
  pgvector: string;
}

/**
 * Base URL for the FastAPI backend.
 *
 * Server-side only. The browser never calls FastAPI directly under the BFF
 * pattern -- it calls Next.js route handlers, which call FastAPI.
 */
const API_BASE_URL = process.env.FORMAVA_API_URL ?? 'http://127.0.0.1:8000';

class ApiClient {
  async health(): Promise<ApiResponse<HealthPayload>> {
    try {
      const res = await fetch(`${API_BASE_URL}/health`, {
        cache: 'no-store',
      });

      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        return { success: false, error: body.detail ?? `HTTP ${res.status}` };
      }

      return { success: true, data: (await res.json()) as HealthPayload };
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : 'Unknown error',
      };
    }
  }

  // ---- Auth: implemented in Spec 4 (REST API + Next.js BFF) ----
  // These throw rather than returning a fake success so that any premature
  // use fails loudly. Signatures match the existing calls in AuthContext.

  async login(
    _username: string,
    _password: string
  ): Promise<ApiResponse<{ user: User }>> {
    throw new Error('apiClient.login is not implemented until Spec 4');
  }

  async register(_userData: RegisterForm): Promise<ApiResponse<{ user: User }>> {
    throw new Error('apiClient.register is not implemented until Spec 4');
  }

  async logout(): Promise<void> {
    throw new Error('apiClient.logout is not implemented until Spec 4');
  }
}

export const apiClient = new ApiClient();
```

- [ ] **Step 5: Add the BFF route handler**

This is the piece that proves the chain. It runs on the Next.js server, not the browser.

`frontend/src/app/api/health/route.ts`:

```typescript
import { NextResponse } from 'next/server';

import { apiClient } from '@/lib/api/client';

/**
 * BFF health route. Fetches FastAPI server-side over loopback and relays the
 * result, proving TLS -> nginx -> Next.js -> FastAPI -> Postgres end to end.
 */
export async function GET() {
  const result = await apiClient.health();

  if (!result.success || !result.data) {
    return NextResponse.json(
      { error: result.error ?? 'health check failed' },
      { status: 503 }
    );
  }

  return NextResponse.json(result.data, { status: 200 });
}
```

- [ ] **Step 6: Enable standalone output**

`formava-web.service` runs `node server.js`, which only exists with standalone output.

`frontend/next.config.ts`:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits .next/standalone with a self-contained server.js — required by
  // formava-web.service and by the multi-stage Dockerfile.
  output: "standalone",
};

export default nextConfig;
```

- [ ] **Step 7: Update the Dockerfile to Node 20**

In `frontend/Dockerfile`, change the base image line:

```dockerfile
FROM node:20-alpine AS base
```

- [ ] **Step 8: Verify the build, types, and lint all pass**

```bash
cd frontend
npx tsc --noEmit
npm run lint
npm run build
ls .next/standalone/server.js
```

Expected: `tsc` clean, lint clean, build succeeds, `server.js` present.

- [ ] **Step 9: Verify the chain locally**

With Postgres from Task 1 up, in two terminals:

```bash
# terminal 1
export FORMAVA_DATABASE_URL="postgresql://formava:formava_dev@localhost:5432/formava"
python -m uvicorn app.health.api:app --host 127.0.0.1 --port 8000

# terminal 2
cd frontend && FORMAVA_API_URL=http://127.0.0.1:8000 npm run dev
```

Then: `curl -s http://localhost:3000/api/health`
Expected: `{"db":"ok","pgvector":"0.6.0"}` (version may differ)

Now stop uvicorn and re-run the curl.
Expected: HTTP 503 with an `error` field — confirming failures propagate rather than being swallowed.

- [ ] **Step 10: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json \
        frontend/next-env.d.ts frontend/next.config.ts frontend/Dockerfile \
        frontend/src/lib frontend/src/app/api
git commit -m "fix: repair Next.js scaffold and add BFF health route

package.json, package-lock.json, and tsconfig.json were never committed,
and AuthContext imported a non-existent @/lib/api/client, so the scaffold
could not build. Adds the manifest (Tailwind v4, Node 20), the TS config
providing the @/* alias, and the API client. Auth methods throw until
Spec 4 rather than returning fake success. Enables standalone output for
formava-web.service."
```

---

## Task 3: Provision Postgres 16 + pgvector on the VPS

**Files:**
- Create: `scripts/vps/provision_postgres.sh`

**Interfaces:**
- Consumes: nothing.
- Produces: a `formava` database owned by role `formava` with the `vector` extension, listening on loopback only. DSN shape: `postgresql://formava:<password>@127.0.0.1:5432/formava`.

- [ ] **Step 1: Write the provisioning script**

`scripts/vps/provision_postgres.sh`:

```bash
#!/usr/bin/env bash
# Provision Postgres 16 + pgvector for Formava. Idempotent: safe to re-run.
#
# Usage: ./provision_postgres.sh <formava_db_password>
set -euo pipefail

DB_PASSWORD="${1:?Usage: $0 <formava_db_password>}"
DB_NAME="formava"
DB_USER="formava"
PG_VERSION="16"
PG_CONF="/etc/postgresql/${PG_VERSION}/main/postgresql.conf"

log() { echo "[provision-postgres] $*"; }

log "Installing packages from Ubuntu repositories..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
    "postgresql-${PG_VERSION}" \
    "postgresql-${PG_VERSION}-pgvector"

log "Ensuring role ${DB_USER} exists..."
if ! sudo -u postgres psql -tAc \
    "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
    sudo -u postgres psql -c \
        "CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';"
else
    log "Role exists; syncing password."
    sudo -u postgres psql -c \
        "ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';"
fi

log "Ensuring database ${DB_NAME} exists..."
if ! sudo -u postgres psql -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
    sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}"
fi

log "Enabling pgvector in ${DB_NAME}..."
sudo -u postgres psql -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS vector;"

log "Applying tuning for 2 vCPU / 3.8 GB..."
# Values are fixed by the spec's memory budget. Appended in a marked block so
# re-runs replace rather than accumulate.
MARKER="# --- formava tuning (managed) ---"
if grep -qF "${MARKER}" "${PG_CONF}"; then
    sed -i "/${MARKER}/,\$d" "${PG_CONF}"
fi
cat >> "${PG_CONF}" <<EOF
${MARKER}
listen_addresses = 'localhost'
shared_buffers = 256MB
effective_cache_size = 1GB
max_connections = 50
password_encryption = scram-sha-256
EOF

log "Restarting Postgres..."
systemctl restart postgresql
systemctl enable postgresql

log "Verifying..."
sudo -u postgres psql -d "${DB_NAME}" -tAc \
    "SELECT extversion FROM pg_extension WHERE extname='vector'"
ss -tlnp | grep 5432 || true

log "Done."
```

- [ ] **Step 2: Make it executable and copy it to the VPS**

```bash
chmod +x scripts/vps/provision_postgres.sh
scp scripts/vps/provision_postgres.sh root@144.202.88.7:/root/
```

- [ ] **Step 3: Generate a password and run it**

```bash
ssh root@144.202.88.7
DB_PW="$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)"
echo "SAVE THIS: ${DB_PW}"
/root/provision_postgres.sh "${DB_PW}"
```

Expected: script completes; final output shows a pgvector version (e.g. `0.6.0`) and a listener on `127.0.0.1:5432`.

- [ ] **Step 4: Verify loopback-only binding and idempotency**

```bash
ssh root@144.202.88.7 '
  ss -tlnp | grep 5432
  PGPASSWORD="'"${DB_PW}"'" psql -h 127.0.0.1 -U formava -d formava \
    -tAc "SELECT extversion FROM pg_extension WHERE extname=\"vector\""
  /root/provision_postgres.sh "'"${DB_PW}"'"
'
```

Expected: listener shows `127.0.0.1:5432` and **not** `0.0.0.0:5432`; psql returns the version; the second run succeeds without errors or duplicated config (`grep -c "formava tuning" /etc/postgresql/16/main/postgresql.conf` returns `1`).

- [ ] **Step 5: Commit**

```bash
git add scripts/vps/provision_postgres.sh
git commit -m "feat: add idempotent Postgres 16 + pgvector provisioning script

Installs from Ubuntu repos (no PGDG), binds loopback only, applies the
spec's tuning values for 2 vCPU / 3.8 GB in a marked block so re-runs
replace rather than accumulate."
```

---

## Task 4: systemd units and the deploy script

**Files:**
- Create: `scripts/vps/formava-api.service`, `scripts/vps/formava-web.service`, `scripts/deploy_vps.sh`

**Interfaces:**
- Consumes: `app.health.api:app` (Task 1); `frontend/.next/standalone/server.js` (Task 2); Postgres DSN (Task 3).
- Produces: `formava-api.service` on `127.0.0.1:8000`, `formava-web.service` on `127.0.0.1:3001`, both reading `/etc/formava/formava.env`. `scripts/deploy_vps.sh` with subcommands `deploy|sync|install|build|restart|logs|status`.

- [ ] **Step 1: Write the API unit**

`scripts/vps/formava-api.service`:

```ini
[Unit]
Description=Formava API (FastAPI)
After=network.target postgresql.service
Requires=postgresql.service
StartLimitBurst=5
StartLimitIntervalSec=60

[Service]
Type=simple
User=root
WorkingDirectory=/opt/formava
EnvironmentFile=/etc/formava/formava.env
ExecStart=/opt/formava/.venv/bin/uvicorn app.health.api:app \
    --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=formava-api

# Cap ~3x measured steady state. Combined with formava-web (512M) and
# Postgres (320M) this stays well inside 3.8 GB, so a runaway here is killed
# by the kernel before it can pressure clio.service into its
# StartLimitBurst=5 permanent-failure state.
MemoryMax=768M

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Write the web unit**

`scripts/vps/formava-web.service`:

```ini
[Unit]
Description=Formava Web (Next.js BFF)
After=network.target formava-api.service
StartLimitBurst=5
StartLimitIntervalSec=60

[Service]
Type=simple
User=root
WorkingDirectory=/opt/formava/frontend/.next/standalone
EnvironmentFile=/etc/formava/formava.env
Environment=NODE_ENV=production
Environment=PORT=3001
Environment=HOSTNAME=127.0.0.1
ExecStart=/usr/bin/node server.js
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=formava-web

MemoryMax=512M

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: Write the deploy script**

`scripts/deploy_vps.sh`:

```bash
#!/usr/bin/env bash
# Deploy Formava to the VPS. Modelled on Clio's scripts/deploy.sh.
#
# Usage:
#   ./scripts/deploy_vps.sh            # build + sync + install + restart
#   ./scripts/deploy_vps.sh sync       # rsync only
#   ./scripts/deploy_vps.sh restart    # restart both units
#   ./scripts/deploy_vps.sh logs api   # follow logs (api|web)
#   ./scripts/deploy_vps.sh status
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

VPS_HOST="${VPS_HOST:-144.202.88.7}"
VPS_USER="${VPS_USER:-root}"
APP_PATH="${APP_PATH:-/opt/formava}"

SSH="ssh ${VPS_USER}@${VPS_HOST}"

GREEN='\033[0;32m'; NC='\033[0m'
log() { echo -e "${GREEN}[deploy]${NC} $1"; }

build_frontend() {
    log "Building Next.js standalone bundle locally..."
    # Built here, not on the host: `next build` wants 1.5-2 GB and would
    # needlessly contend with Clio.
    (cd "$PROJECT_DIR/frontend" && npm ci && npm run build)
}

sync_files() {
    log "Syncing to ${VPS_HOST}:${APP_PATH}..."
    $SSH "mkdir -p ${APP_PATH}"

    # Gradio is deliberately excluded -- it must never reach the VPS.
    rsync -avz --delete \
        --exclude '.git' \
        --exclude '.venv' \
        --exclude 'node_modules' \
        --exclude '__pycache__' \
        --exclude '.env' \
        --exclude '.next/cache' \
        --exclude 'app/pages' \
        --exclude 'app/routes.py' \
        --exclude 'app/theme.py' \
        --exclude 'app/config/state.py' \
        --exclude 'tests' \
        --exclude '*.log' \
        --exclude '.DS_Store' \
        "$PROJECT_DIR/" "${VPS_USER}@${VPS_HOST}:${APP_PATH}/"
}

install_deps() {
    log "Installing Python dependencies in the venv..."
    $SSH "cd ${APP_PATH} && \
        (test -d .venv || python3 -m venv .venv) && \
        .venv/bin/pip install --upgrade pip -q && \
        .venv/bin/pip install -r requirements-api.txt -q"
}

install_units() {
    log "Installing systemd units..."
    $SSH "cp ${APP_PATH}/scripts/vps/formava-api.service /etc/systemd/system/ && \
          cp ${APP_PATH}/scripts/vps/formava-web.service /etc/systemd/system/ && \
          systemctl daemon-reload && \
          systemctl enable formava-api formava-web"
}

restart_services() {
    log "Restarting services..."
    $SSH "systemctl restart formava-api formava-web"
    sleep 3
    $SSH "systemctl is-active formava-api formava-web"
}

case "${1:-deploy}" in
    deploy)  build_frontend; sync_files; install_deps; install_units; restart_services ;;
    build)   build_frontend ;;
    sync)    sync_files ;;
    install) install_deps; install_units ;;
    restart) restart_services ;;
    logs)    $SSH "journalctl -u formava-${2:-api} -f --no-pager -n 50" ;;
    status)  $SSH "systemctl status formava-api formava-web --no-pager" ;;
    *)       echo "Usage: $0 {deploy|build|sync|install|restart|logs|status}"; exit 1 ;;
esac

log "Done."
```

- [ ] **Step 4: Create the secrets file on the VPS**

Never rsynced, never committed. Use the `DB_PW` from Task 3 Step 3.

```bash
ssh root@144.202.88.7 '
  mkdir -p /etc/formava
  cat > /etc/formava/formava.env <<EOF
FORMAVA_DATABASE_URL=postgresql://formava:REPLACE_WITH_DB_PW@127.0.0.1:5432/formava
FORMAVA_API_URL=http://127.0.0.1:8000
EOF
  chown root:root /etc/formava/formava.env
  chmod 0600 /etc/formava/formava.env
  ls -la /etc/formava/formava.env
'
```

Expected: `-rw------- 1 root root`. Replace `REPLACE_WITH_DB_PW` with the real password.

- [ ] **Step 5: Deploy**

```bash
chmod +x scripts/deploy_vps.sh
./scripts/deploy_vps.sh deploy
```

Expected: build succeeds, rsync completes, both units report `active`.

- [ ] **Step 6: Verify both services and the memory caps**

```bash
ssh root@144.202.88.7 '
  curl -s http://127.0.0.1:8000/health; echo
  curl -s http://127.0.0.1:3001/api/health; echo
  ss -tlnp | grep -E ":8000|:3001"
  systemctl show formava-api -p MemoryMax
  systemctl show formava-web -p MemoryMax
  free -h | head -2
'
```

Expected: both curls return `{"db":"ok","pgvector":"..."}`; both listeners on `127.0.0.1` only; `MemoryMax=805306368` and `536870912`; total memory use under 1.5 GB.

- [ ] **Step 7: Confirm Gradio was not deployed**

```bash
ssh root@144.202.88.7 'ls /opt/formava/app/pages /opt/formava/app/routes.py 2>&1'
```

Expected: "No such file or directory" for both.

- [ ] **Step 8: Commit**

```bash
git add scripts/vps/formava-api.service scripts/vps/formava-web.service \
        scripts/deploy_vps.sh
git commit -m "feat: add systemd units and VPS deploy script

MemoryMax caps (768M api, 512M web) keep a Formava runaway from pressuring
clio.service into StartLimitBurst=5 permanent failure. Next.js is built
locally rather than on the host, and the rsync excludes the Gradio layer
so it can never reach the VPS."
```

---

## Task 5: nginx vhost and TLS for formava.io

**Files:**
- Create: `scripts/vps/nginx-formava.conf`

**Interfaces:**
- Consumes: `formava-web.service` on `127.0.0.1:3001` (Task 4).
- Produces: `https://formava.io` serving the Next.js app; `https://formava.io/api/health` proving the chain; `www` redirecting to apex.

- [ ] **Step 1: 🛑 HUMAN — create DNS records, then verify propagation**

Create two A records at your registrar:

| Name | Type | Value |
|------|------|-------|
| `formava.io` | A | `144.202.88.7` |
| `www.formava.io` | A | `144.202.88.7` |

Then verify **before** running certbot — an HTTP-01 challenge against a stale record fails in a way that reads like an nginx misconfiguration:

```bash
dig +short formava.io
dig +short www.formava.io
```

Expected: both output `144.202.88.7`. Do not proceed until they do.

- [ ] **Step 2: Write the vhost (HTTP only, for the ACME challenge)**

certbot rewrites this file to add TLS. Start with port 80 so the challenge can succeed.

`scripts/vps/nginx-formava.conf`:

```nginx
# Formava — Next.js BFF. certbot injects the TLS listener and redirect.
server {
    listen 80;
    listen [::]:80;
    server_name formava.io www.formava.io;

    client_max_body_size 2m;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        "upgrade";
    }
}
```

- [ ] **Step 3: Install it and issue the certificate**

```bash
scp scripts/vps/nginx-formava.conf root@144.202.88.7:/etc/nginx/sites-available/formava
ssh root@144.202.88.7 '
  apt-get install -y --no-install-recommends certbot python3-certbot-nginx
  ln -sf /etc/nginx/sites-available/formava /etc/nginx/sites-enabled/formava
  nginx -t && systemctl reload nginx
  certbot --nginx -d formava.io -d www.formava.io \
      --non-interactive --agree-tos -m lantz@gocascade.ai --redirect
'
```

Expected: certbot reports successful issuance and modifies the vhost to listen on 443 with a redirect from 80.

- [ ] **Step 4: Add HSTS**

Deliberately without `includeSubDomains` or `preload`, so this certificate makes no commitments for other hosts. `preload` in particular is hard to reverse.

```bash
ssh root@144.202.88.7 '
  sed -i "/server_name formava.io www.formava.io;/a \\    add_header Strict-Transport-Security \"max-age=31536000\" always;" \
      /etc/nginx/sites-available/formava
  nginx -t && systemctl reload nginx
'
```

- [ ] **Step 5: Verify the full chain over TLS**

```bash
curl -sI http://formava.io | head -1
curl -s https://formava.io/api/health; echo
curl -sI https://formava.io | grep -i strict-transport
curl -sI https://www.formava.io | head -1
ssh root@144.202.88.7 'certbot renew --dry-run 2>&1 | tail -3'
```

Expected: HTTP returns `301`; `/api/health` returns `{"db":"ok","pgvector":"..."}` over HTTPS; the HSTS header is present; `www` redirects; the renewal dry run succeeds.

- [ ] **Step 6: Commit**

```bash
git add scripts/vps/nginx-formava.conf
git commit -m "feat: add formava.io nginx vhost with TLS

HSTS without includeSubDomains or preload, so this cert constrains no
other hosts. Proxies to the Next.js BFF on loopback; FastAPI gets no
public vhost."
```

---

## Task 6: 🛑 Clio cutover — ordered, do not reorder

**Gate A.** The iOS Shortcut cannot be updated remotely. Closing port 3000 before the Shortcut is verified on HTTPS breaks voice capture **silently**. Steps run strictly in order, and Step 9 is the point of no return.

**Files:**
- Create: `scripts/vps/nginx-clio.conf`

**Interfaces:**
- Consumes: Clio on port 3000 (currently `0.0.0.0`, ends on `127.0.0.1`).
- Produces: `https://clio.lantzbuilds.com` publishing exactly `POST /capture`, `POST /capture/<id>/fix`, `GET /health`, and `/api/sessions/*`. Everything else returns 404 at nginx.

- [ ] **Step 1: 🛑 HUMAN — create the DNS record and verify**

| Name | Type | Value |
|------|------|-------|
| `clio.lantzbuilds.com` | A | `144.202.88.7` |

```bash
dig +short clio.lantzbuilds.com
```

Expected: `144.202.88.7`. Do not proceed until it resolves.

- [ ] **Step 2: Write the allowlist vhost**

This is a security control, not tidiness. `/api/sessions/*` drives an Anthropic-backed orchestrator with vault filesystem access, and one token guards everything, so bounding reachable paths bounds a leaked credential.

`scripts/vps/nginx-clio.conf`:

```nginx
# Clio — allowlist vhost. Only paths with a known caller are published.
# /status, /capture/bulk, /capture/fix, /capture/fix/recent stay closed.
limit_req_zone $binary_remote_addr zone=capture:1m  rate=10r/m;
limit_req_zone $binary_remote_addr zone=sessions:1m rate=60r/m;

server {
    listen 80;
    listen [::]:80;
    server_name clio.lantzbuilds.com;

    client_max_body_size 64k;

    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;

    # iOS Shortcut — new capture
    location = /capture {
        limit_except POST { deny all; }
        limit_req zone=capture burst=5 nodelay;
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host            $host;
        proxy_set_header X-Real-IP       $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # iOS Shortcut — correct an existing capture by id.
    # Regex because an exact match cannot cover a path parameter. Anchored to
    # exactly three segments so /capture/fix and /capture/fix/recent do NOT
    # match and stay closed. nginx evaluates regex locations before plain
    # prefix matches, so `location /` never sees this.
    location ~ ^/capture/[^/]+/fix$ {
        limit_except POST { deny all; }
        limit_req zone=capture burst=5 nodelay;
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host            $host;
        proxy_set_header X-Real-IP       $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # CLI connection validation
    location = /health {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
    }

    # CLI session control. SSE settings are load-bearing: with nginx's
    # default proxy_buffering the chat stream is buffered and typewriter
    # rendering breaks, and the default 60s read timeout severs long turns.
    location /api/sessions {
        limit_req zone=sessions burst=20 nodelay;
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host            $host;
        proxy_set_header X-Real-IP       $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Connection      '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 120s;
    }

    location / { return 404; }
}
```

- [ ] **Step 3: Install and issue the certificate**

Clio stays on `0.0.0.0:3000` for now, so the old direct path and the new HTTPS path work simultaneously.

```bash
scp scripts/vps/nginx-clio.conf root@144.202.88.7:/etc/nginx/sites-available/clio
ssh root@144.202.88.7 '
  ln -sf /etc/nginx/sites-available/clio /etc/nginx/sites-enabled/clio
  nginx -t && systemctl reload nginx
  certbot --nginx -d clio.lantzbuilds.com \
      --non-interactive --agree-tos -m lantz@gocascade.ai --redirect
'
```

- [ ] **Step 4: Verify the allowlist before touching the Shortcut**

Read `CAPTURE_API_TOKEN` from `/opt/clio/.env` on the host and export it locally as `TOKEN`.

```bash
# Published paths reach Clio
curl -s -o /dev/null -w "capture     %{http_code}\n" -X POST \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"text":"allowlist probe"}' https://clio.lantzbuilds.com/capture
curl -s -o /dev/null -w "health      %{http_code}\n" \
  https://clio.lantzbuilds.com/health

# Closed paths 404 at nginx even WITH a valid token -- the property being relied on
for p in /status /capture/bulk /capture/fix /capture/fix/recent /v404/exec; do
  printf "%-22s " "$p"
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer $TOKEN" "https://clio.lantzbuilds.com$p"
done

# Method restriction
curl -s -o /dev/null -w "GET /capture %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" https://clio.lantzbuilds.com/capture
```

Expected: `capture` 200/201; `health` 200; all five closed paths `404`; `GET /capture` `403`.

- [ ] **Step 5: 🛑 HUMAN — update the Shortcut URL**

On the phone, edit the Clio Shortcut's URL action:

```
http://144.202.88.7:3000/capture   →   https://clio.lantzbuilds.com/capture
```

Do the same for the second Shortcut that calls `/capture/<id>/fix`.

- [ ] **Step 6: Verify a real capture end to end**

Run both Shortcuts from the phone, then:

```bash
ssh root@144.202.88.7 '
  tail -20 /var/log/nginx/access.log | grep capture
  journalctl -u clio --no-pager -n 20 | tail -10
'
```

Expected: nginx access log shows `POST /capture` (and the fix route) with **your phone's source IP** — the observability gap is now closed — and Clio's log shows the capture arriving. Confirm the dictated text landed in the inbox.

- [ ] **Step 7: 🛑 HUMAN — rotate the token, then update the Shortcuts again**

The current token was exposed in plaintext during assessment.

```bash
ssh root@144.202.88.7 '
  NEW="$(openssl rand -hex 32)"
  echo "NEW TOKEN: ${NEW}"
  sed -i "s/^CAPTURE_API_TOKEN=.*/CAPTURE_API_TOKEN=${NEW}/" /opt/clio/.env
  systemctl restart clio
  sleep 3 && systemctl is-active clio
'
```

Then on the phone, update the `Authorization: Bearer <token>` header in **both** Shortcuts, and run `clio config set-token <new>` for the CLI.

- [ ] **Step 8: Verify captures and CLI still work on the new token**

Run a Shortcut capture, and point the CLI at HTTPS:

```bash
clio config set-url https://clio.lantzbuilds.com
clio config set-token <new-token>
# exercise a session, including a streaming chat, to confirm SSE works
```

Expected: capture lands; CLI connects; **chat streams incrementally rather than arriving all at once** — that confirms `proxy_buffering off` is effective.

- [ ] **Step 9: 🛑 POINT OF NO RETURN — close port 3000 at the firewall**

Only proceed once Step 8 passed. This kills the plaintext path.

**Clio cannot currently bind to loopback.** `src/api/capture.ts:419` calls
`app.listen(config.port, () => {...})` with **no host argument**, so Express binds
`0.0.0.0`, and no `CAPTURE_API_HOST` environment variable exists. Binding to
loopback requires a one-line source change:

```typescript
// src/api/capture.ts:419 — for the Clio session, not this plan
app.listen(config.port, '127.0.0.1', () => { /* ... */ });
```

**The firewall rule is the effective control and does not depend on that change.**
With `3000/tcp` removed from ufw, the port is unreachable externally regardless of
what Express binds, and nginx still reaches it over loopback. The loopback bind is
defence in depth — it protects against a future ufw misconfiguration — so it is
handed to the Clio session rather than blocking this task.

```bash
ssh root@144.202.88.7 '
  ufw delete allow 3000/tcp
  ufw status
  ss -tlnp | grep 3000
'
```

Expected: ufw no longer lists 3000. `ss` still shows `0.0.0.0:3000` — that is
expected until the Clio change lands, and is why Step 10 verifies external
unreachability directly rather than inferring it from the bind address.

- [ ] **Step 10: Verify external unreachability directly**

Because Express still binds `0.0.0.0`, this must be tested **from off-host** — a
loopback test would succeed and prove nothing.

```bash
# From your laptop, NOT via ssh:
curl -m 8 -s -o /dev/null -w "direct: %{http_code}\n" \
  http://144.202.88.7:3000/capture || echo "direct: blocked (expected)"
curl -s -o /dev/null -w "https:  %{http_code}\n" \
  https://clio.lantzbuilds.com/health
```

Expected: the direct request times out or is refused (ufw drops it); HTTPS returns
200. Run one more Shortcut capture to be certain, and exercise a CLI chat to
confirm SSE still streams.

- [ ] **Step 11: Commit**

```bash
git add scripts/vps/nginx-clio.conf
git commit -m "feat: add Clio allowlist vhost with TLS and SSE support

Publishes only paths with a known caller: POST /capture, the
/capture/<id>/fix regex, GET /health, and /api/sessions/*. /status,
/capture/bulk, /capture/fix, and /capture/fix/recent 404 at nginx even
with a valid token, bounding a leaked credential. SSE settings prevent
buffering of the CLI chat stream."
```

---

## Task 7: fail2ban jails for nginx

The host takes ~261 unsolicited requests a day — `zgrab/0.x`, a Dahua camera RCE probe, CGI enumeration — and fail2ban currently runs only the `sshd` jail.

**Files:**
- Create: `scripts/vps/fail2ban-nginx.local`, `scripts/vps/fail2ban-filter-clio-auth.conf`

**Interfaces:**
- Consumes: nginx access/error logs from Tasks 5–6.
- Produces: active `nginx-http-auth`, `nginx-badbots`, and `clio-capture-auth` jails.

- [ ] **Step 1: Write a custom filter for upstream 401s**

The spec requires a jail on repeated `401`s against the capture route. The stock
`nginx-http-auth` filter matches nginx's **own** `auth_basic` failures in
`error.log` — it does **not** match a 401 returned by an upstream application. Clio
returns its own 401s, so this needs a filter over `access.log`.

`scripts/vps/fail2ban-filter-clio-auth.conf`:

```ini
# Match repeated 401s against Clio's capture routes in nginx's access log.
# The stock nginx-http-auth filter only catches nginx's own auth_basic
# failures in error.log, not 401s returned by an upstream app.
#
# Default combined log format:
#   $remote_addr - $remote_user [$time_local] "$request" $status ...
[Definition]
failregex = ^<HOST> - \S+ \[[^\]]+\] "(?:GET|POST) /capture(?:/[^/"]+/fix)?(?:\?\S*)? HTTP/[\d.]+" 401
ignoreregex =
datepattern = \[%%d/%%b/%%Y:%%H:%%M:%%S %%z\]
```

- [ ] **Step 2: Write the jail config**

`scripts/vps/fail2ban-nginx.local`:

```ini
# nginx jails for Clio and Formava. Installed to /etc/fail2ban/jail.d/.
[nginx-http-auth]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log
maxretry = 5
findtime = 600
bantime  = 3600

[nginx-badbots]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/access.log
maxretry = 2
findtime = 600
bantime  = 86400

# Brute-force protection for the capture bearer token. The legitimate client
# is a human dictating, so repeated 401s are never normal traffic.
[clio-capture-auth]
enabled  = true
port     = http,https
filter   = clio-capture-auth
logpath  = /var/log/nginx/access.log
maxretry = 5
findtime = 600
bantime  = 86400
```

- [ ] **Step 3: Install and restart**

```bash
scp scripts/vps/fail2ban-filter-clio-auth.conf \
    root@144.202.88.7:/etc/fail2ban/filter.d/clio-capture-auth.conf
scp scripts/vps/fail2ban-nginx.local \
    root@144.202.88.7:/etc/fail2ban/jail.d/nginx.local
ssh root@144.202.88.7 'systemctl restart fail2ban && sleep 2 && fail2ban-client status'
```

- [ ] **Step 4: Verify the custom filter actually matches**

A filter that compiles but matches nothing is worse than no filter, because it
looks like protection. Test it against a real log line:

```bash
ssh root@144.202.88.7 '
  printf "%s\n" \
    "203.0.113.9 - - [31/Jul/2026:12:00:00 +0000] \"POST /capture HTTP/1.1\" 401 20 \"-\" \"curl/8.0\"" \
    "203.0.113.9 - - [31/Jul/2026:12:00:01 +0000] \"POST /capture/abc123/fix HTTP/1.1\" 401 20 \"-\" \"curl/8.0\"" \
    > /tmp/f2b-test.log
  fail2ban-regex /tmp/f2b-test.log /etc/fail2ban/filter.d/clio-capture-auth.conf
  rm /tmp/f2b-test.log
'
```

Expected: `2 match(es)` for the failregex. If it reports 0, the log format differs
— check `grep log_format /etc/nginx/nginx.conf` and adjust the regex.

- [ ] **Step 5: Verify all four jails are active**

```bash
ssh root@144.202.88.7 '
  fail2ban-client status
  fail2ban-client status clio-capture-auth | head -8
'
```

Expected: jail list contains `sshd`, `nginx-http-auth`, `nginx-badbots`, and
`clio-capture-auth`.

- [ ] **Step 6: Commit**

```bash
git add scripts/vps/fail2ban-nginx.local scripts/vps/fail2ban-filter-clio-auth.conf
git commit -m "feat: add nginx fail2ban jails incl. capture token brute-force

The host takes ~261 unsolicited requests/day (zgrab, Dahua RCE probes,
CGI enumeration) with only the sshd jail active. The capture-401 jail needs
a custom access.log filter because stock nginx-http-auth only matches
nginx's own auth_basic failures, not upstream 401s from Clio."
```

---

## Task 8: 🛑 SSH hardening — key-only authentication

**Gate B.** Verify key auth in a **second, separate SSH session** before disabling passwords. A mistake here locks you out and recovery needs Vultr's web console.

**Files:** none (host configuration only).

- [ ] **Step 1: Confirm a key is installed and works**

In a **new terminal**, leaving your current session open:

```bash
ssh -i ~/.ssh/id_ed25519 -o PasswordAuthentication=no root@144.202.88.7 'echo KEY_AUTH_OK'
```

Expected: `KEY_AUTH_OK`. If this fails, install your public key first:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@144.202.88.7
```

Do not continue until the `PasswordAuthentication=no` probe succeeds.

- [ ] **Step 2: Rotate the root password**

Exposed in plaintext during assessment.

```bash
ssh root@144.202.88.7 'openssl rand -base64 24'
# store it in your password manager, then:
ssh root@144.202.88.7 'passwd root'
```

- [ ] **Step 3: Disable password authentication**

```bash
ssh root@144.202.88.7 '
  sed -i "s/^#*PasswordAuthentication.*/PasswordAuthentication no/" /etc/ssh/sshd_config
  sed -i "s/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/" /etc/ssh/sshd_config
  grep -E "^PasswordAuthentication|^PermitRootLogin" /etc/ssh/sshd_config
  sshd -t && systemctl reload ssh
'
```

`sshd -t` validates the config before reload — it refuses to apply a broken file.

- [ ] **Step 4: Verify key auth still works and passwords are refused**

**Keep your current session open** while testing in a new terminal:

```bash
ssh -i ~/.ssh/id_ed25519 root@144.202.88.7 'echo STILL_IN'
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password \
    root@144.202.88.7 'echo SHOULD_NOT_PRINT' || echo "password auth refused (expected)"
```

Expected: `STILL_IN`, then `Permission denied` for the password attempt.

- [ ] **Step 5: Note the deploy-script implication**

Clio's `scripts/deploy.sh` prefers `VPS_PASSWORD` over `VPS_KEY_PATH` when both are set (`../clio-ai-assitant/scripts/deploy.sh:42-51`), so it will break after this change. Remove or comment `VPS_PASSWORD` in `../clio-ai-assitant/.env` so the script takes the key-auth branch. `scripts/deploy_vps.sh` already uses keys only.

- [ ] **Step 6: Verify ufw is at its final state**

```bash
ssh root@144.202.88.7 'ufw status verbose'
```

Expected: allow rules for `22`, `80`, `443` only. No `3000/tcp`.

---

## Task 9: Nightly pg_dump backups

**Files:**
- Create: `scripts/vps/pg_backup.sh`, `scripts/vps/formava-backup.service`, `scripts/vps/formava-backup.timer`

**Interfaces:**
- Consumes: the `formava` database (Task 3).
- Produces: nightly gzipped dumps in `/var/backups/formava`, 7-day retention, via `formava-backup.timer`.

- [ ] **Step 1: Write the backup script**

`scripts/vps/pg_backup.sh`:

```bash
#!/usr/bin/env bash
# Nightly pg_dump of the formava database with 7-day retention.
set -euo pipefail

BACKUP_DIR="/var/backups/formava"
DB_NAME="formava"
RETENTION_DAYS=7
STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="${BACKUP_DIR}/${DB_NAME}-${STAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"
chmod 0700 "${BACKUP_DIR}"

sudo -u postgres pg_dump --no-owner "${DB_NAME}" | gzip > "${TARGET}"

# Fail loudly on an empty or tiny dump rather than silently keeping garbage.
if [ ! -s "${TARGET}" ] || [ "$(stat -c%s "${TARGET}")" -lt 100 ]; then
    echo "ERROR: backup ${TARGET} is empty or truncated" >&2
    exit 1
fi

find "${BACKUP_DIR}" -name "${DB_NAME}-*.sql.gz" \
    -mtime "+${RETENTION_DAYS}" -delete

echo "Backup complete: ${TARGET} ($(du -h "${TARGET}" | cut -f1))"
```

- [ ] **Step 2: Write the unit and timer**

`scripts/vps/formava-backup.service`:

```ini
[Unit]
Description=Formava Postgres backup
After=postgresql.service
Requires=postgresql.service

[Service]
Type=oneshot
ExecStart=/opt/formava/scripts/vps/pg_backup.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=formava-backup
```

`scripts/vps/formava-backup.timer`:

```ini
[Unit]
Description=Nightly Formava Postgres backup

[Timer]
OnCalendar=daily
# Spread load off the hour, and survive missed windows after a reboot.
RandomizedDelaySec=1800
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Step 3: Install and enable**

```bash
chmod +x scripts/vps/pg_backup.sh
./scripts/deploy_vps.sh sync
ssh root@144.202.88.7 '
  chmod +x /opt/formava/scripts/vps/pg_backup.sh
  cp /opt/formava/scripts/vps/formava-backup.service /etc/systemd/system/
  cp /opt/formava/scripts/vps/formava-backup.timer   /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable --now formava-backup.timer
'
```

- [ ] **Step 4: Run it once and verify the artifact**

```bash
ssh root@144.202.88.7 '
  systemctl start formava-backup.service
  journalctl -u formava-backup --no-pager -n 10
  ls -la /var/backups/formava/
  systemctl list-timers formava-backup --no-pager
'
```

Expected: journal reports "Backup complete"; a non-empty `.sql.gz` exists; the timer shows a next-run time.

- [ ] **Step 5: Verify the dump actually restores**

An untested backup is not a backup.

```bash
ssh root@144.202.88.7 '
  LATEST=$(ls -t /var/backups/formava/*.sql.gz | head -1)
  sudo -u postgres createdb formava_restore_test
  gunzip -c "${LATEST}" | sudo -u postgres psql -q formava_restore_test
  sudo -u postgres psql -d formava_restore_test -tAc \
    "SELECT extversion FROM pg_extension WHERE extname=\"vector\""
  sudo -u postgres dropdb formava_restore_test
  echo "restore verified"
'
```

Expected: the pgvector version prints, then `restore verified`.

- [ ] **Step 6: Commit**

```bash
git add scripts/vps/pg_backup.sh scripts/vps/formava-backup.service \
        scripts/vps/formava-backup.timer
git commit -m "feat: add nightly pg_dump backups with restore verification

Fails loudly on an empty or truncated dump rather than retaining garbage.
Persistent=true so a missed window runs after reboot."
```

---

## Task 10: Verification script and CI deploy wiring

**Files:**
- Create: `scripts/vps/verify.sh`
- Modify: `.github/workflows/ci.yml` (replace both `echo` deploy stubs)

**Interfaces:**
- Consumes: every prior task.
- Produces: `scripts/vps/verify.sh`, a re-runnable assertion of every spec §6 exit criterion, exiting non-zero on any failure.

- [ ] **Step 1: Write the verification script**

`scripts/vps/verify.sh`:

```bash
#!/usr/bin/env bash
# Assert every Spec 1 exit criterion. Safe to re-run. Exits non-zero on failure.
#
# Usage: CLIO_TOKEN=<token> ./scripts/vps/verify.sh
set -uo pipefail

VPS="${VPS_HOST:-144.202.88.7}"
SSH="ssh root@${VPS}"
FAIL=0

pass() { echo "  ok    $1"; }
fail() { echo "  FAIL  $1"; FAIL=1; }

check() { # description, actual, expected
    [ "$2" = "$3" ] && pass "$1 ($2)" || fail "$1 — got '$2', want '$3'"
}

echo "== Formava =="
check "http->https redirect" \
  "$(curl -s -o /dev/null -w '%{http_code}' http://formava.io)" "301"
check "https serves app" \
  "$(curl -s -o /dev/null -w '%{http_code}' https://formava.io)" "200"

HEALTH="$(curl -s https://formava.io/api/health)"
echo "$HEALTH" | grep -q '"db":"ok"' \
  && pass "BFF health chain ($HEALTH)" || fail "BFF health chain — got '$HEALTH'"

echo "== Clio allowlist =="
if [ -n "${CLIO_TOKEN:-}" ]; then
    for p in /status /capture/bulk /capture/fix /capture/fix/recent /v404/exec; do
        check "closed: $p" \
          "$(curl -s -o /dev/null -w '%{http_code}' \
             -H "Authorization: Bearer ${CLIO_TOKEN}" \
             "https://clio.lantzbuilds.com${p}")" "404"
    done
    check "GET /capture rejected" \
      "$(curl -s -o /dev/null -w '%{http_code}' \
         -H "Authorization: Bearer ${CLIO_TOKEN}" \
         https://clio.lantzbuilds.com/capture)" "403"
else
    echo "  skip  allowlist checks (set CLIO_TOKEN)"
fi
check "clio /health reachable" \
  "$(curl -s -o /dev/null -w '%{http_code}' https://clio.lantzbuilds.com/health)" "200"
check "capture 401 without token" \
  "$(curl -s -o /dev/null -w '%{http_code}' -X POST \
     -H 'Content-Type: application/json' -d '{"text":"x"}' \
     https://clio.lantzbuilds.com/capture)" "401"

# Tested from off-host on purpose: Clio still binds 0.0.0.0 (see Task 6 Step 9),
# so ufw is what makes port 3000 unreachable. A loopback test would pass and
# prove nothing.
timeout 8 curl -s -o /dev/null "http://${VPS}:3000/capture" 2>/dev/null \
  && fail "port 3000 externally blocked" \
  || pass "port 3000 externally blocked"

echo "== Host =="
check "services active" \
  "$($SSH 'systemctl is-active postgresql formava-api formava-web clio nginx | sort -u | tr -d "\n"')" \
  "active"
check "ufw ports" \
  "$($SSH "ufw status | grep -cE '^(22|80|443)'")" "3"
check "no 3000 in ufw" "$($SSH 'ufw status | grep -c 3000')" "0"
# 3000 deliberately excluded: Clio binds 0.0.0.0 until the Clio session applies
# the one-line listen() change. Firewall coverage is asserted above instead.
check "formava binds loopback only" \
  "$($SSH "ss -tln | grep -cE '0\.0\.0\.0:(3001|8000|5432)'")" "0"
check "api MemoryMax" \
  "$($SSH 'systemctl show formava-api -p MemoryMax --value')" "805306368"
check "web MemoryMax" \
  "$($SSH 'systemctl show formava-web -p MemoryMax --value')" "536870912"
check "gradio absent" "$($SSH 'test -e /opt/formava/app/pages; echo $?')" "1"
check "password auth off" \
  "$($SSH "grep -c '^PasswordAuthentication no' /etc/ssh/sshd_config")" "1"
for jail in nginx-badbots nginx-http-auth clio-capture-auth; do
    check "fail2ban jail ${jail}" \
      "$($SSH "fail2ban-client status ${jail} >/dev/null 2>&1; echo \$?")" "0"
done
check "backup timer" \
  "$($SSH 'systemctl is-active formava-backup.timer')" "active"
$SSH 'ls /var/backups/formava/*.sql.gz >/dev/null 2>&1' \
  && pass "backup artifact present" || fail "backup artifact present"
$SSH 'certbot renew --dry-run' >/dev/null 2>&1 \
  && pass "cert renewal dry-run" || fail "cert renewal dry-run"

echo
echo "== Memory =="
$SSH 'free -h | head -2'

[ "$FAIL" -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit "$FAIL"
```

- [ ] **Step 2: Run it**

```bash
chmod +x scripts/vps/verify.sh
CLIO_TOKEN=<new-token> ./scripts/vps/verify.sh
```

Expected: `ALL CHECKS PASSED`, exit 0. Fix any failures before continuing.

- [ ] **Step 3: Replace the CI deploy stubs**

In `.github/workflows/ci.yml`, replace the `deploy-staging` and `deploy-production` jobs — both currently just `echo "This would trigger Render deployment"` — with a single VPS deploy job. Staging is dropped per the spec, so `main` deploys to the VPS while Render remains live and untouched as fallback.

```yaml
  # Deploy to the VPS (main branch). Render remains live as fallback
  # until Spec 4; this workflow does not touch it.
  deploy-vps:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'

    steps:
    - uses: actions/checkout@v4

    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json

    - name: Build frontend
      working-directory: ./frontend
      run: npm ci && npm run build

    - name: Configure SSH
      run: |
        mkdir -p ~/.ssh
        echo "${{ secrets.VPS_SSH_KEY }}" > ~/.ssh/id_ed25519
        chmod 600 ~/.ssh/id_ed25519
        ssh-keyscan -H ${{ secrets.VPS_HOST }} >> ~/.ssh/known_hosts

    - name: Deploy
      env:
        VPS_HOST: ${{ secrets.VPS_HOST }}
      run: |
        ./scripts/deploy_vps.sh sync
        ./scripts/deploy_vps.sh install
        ./scripts/deploy_vps.sh restart

    - name: Verify
      run: |
        curl -sf https://formava.io/api/health | grep '"db":"ok"'
```

Also bump `node-version: '18'` to `'20'` in the existing `test-frontend` job, and drop `feature/nextjs-migration` from the `on.push.branches` list if that branch is no longer in use.

Add two repository secrets: `VPS_SSH_KEY` (a deploy private key, not your personal one) and `VPS_HOST`.

- [ ] **Step 4: Verify CI passes**

```bash
git add .github/workflows/ci.yml scripts/vps/verify.sh
git commit -m "feat: add verification script and wire CI to deploy to the VPS

Replaces both echo-stub deploy jobs with a real VPS deploy. verify.sh
asserts every Spec 1 exit criterion and is safe to re-run. Render is
untouched and remains the fallback until Spec 4."
git push -u origin spec/vps-infra-migration
```

Then confirm the Actions run is green (the deploy job is skipped on a non-`main` branch, which is expected).

- [ ] **Step 5: Final full verification**

```bash
CLIO_TOKEN=<new-token> ./scripts/vps/verify.sh
```

Expected: `ALL CHECKS PASSED`.

---

## Definition of Done

- [ ] `https://formava.io/api/health` returns `{"db":"ok","pgvector":"..."}` over TLS
- [ ] `scripts/vps/verify.sh` exits 0 with all checks passing
- [ ] iOS Shortcuts (capture and fix) work over HTTPS on a rotated token
- [ ] Clio CLI works over HTTPS, and chat **streams incrementally** (SSE unbuffered)
- [ ] Telegram bot still responds (long polling, unaffected)
- [ ] `ufw status` shows 22, 80, 443 only
- [ ] Port 3000 unreachable **from off-host** (ufw; Clio still binds `0.0.0.0` pending its one-line `listen()` change)
- [ ] Formava processes bind loopback only on 3001, 8000, 5432
- [ ] Password SSH refused; key auth works
- [ ] A `pg_dump` artifact exists and has been proven to restore
- [ ] No Gradio file exists under `/opt/formava`
- [ ] Total host memory use ≤ 1.5 GB
- [ ] Render still live and untouched

## Deferred to Later Specs

| Item | Spec |
|------|------|
| Tables, SQLAlchemy models, Alembic baseline, re-embed into pgvector | 2 |
| Delete `views.py`, `couchdb`, `chromadb`, `langchain` | 2 |
| LLM provider seam; split `openai_service.py`; fix `tiktoken` | 3 |
| Real REST API, cookie auth, `apiClient` auth methods, delete Gradio | 4 |
| Retire Render | after 4 |
| Clio token splitting, fail-fast config, source-IP logging, `/status` | `../clio-ai-assitant/docs/INFRA-HANDOFF.md` |
