# Spec 1 — Formava VPS Infrastructure + Datastore

**Date:** 2026-07-26
**Status:** Approved for planning
**Scope:** Provision the Vultr VPS to host Formava, stand up Postgres 16 + pgvector,
establish TLS and process supervision, and prove the full request chain with a
`/health` payload. Remediate security exposures found during assessment.

---

## 1. Why this spec exists

Formava currently runs on Render as three `starter`-plan services (production,
staging, and a staging CouchDB), with production persistence on IBM Cloudant's
free tier. The goal is to consolidate onto an existing Vultr VPS that already
hosts the Clio assistant, then perform substantial refactoring.

This is Spec 1 of four. It deliberately contains **no application code migration**.

### Decomposition

| # | Spec | Scope | Depends on |
|---|------|-------|------------|
| **1** | **VPS infra + datastore** (this doc) | Postgres 16 + pgvector, systemd, nginx + TLS, deploy tooling, `/health` payload, security remediation | — |
| 2 | Persistence swap | Repository interface, SQLAlchemy models from existing Pydantic models, Alembic baseline, delete `views.py` + `couchdb` + `chromadb`, re-embed into pgvector | 1 |
| 3 | LLM provider seam | `app/services/llm/` package, split `openai_service.py`, provider-aware tokenization | 1 (parallel with 2) |
| 4 | REST API + Next.js BFF | FastAPI routes over surviving services, cookie auth, Next App Router, delete Gradio layer | 2, 3 |

### Guiding constraint

**Gradio is never deployed to the VPS.** It has no users worth protecting (one
betatester, ever) and is slated for deletion in Spec 4. Porting ~3,400 lines of
UI code to new infrastructure only to delete it is waste. Render remains live and
untouched as the fallback until Spec 4 completes.

---

## 2. Measured current state

All figures below were measured on the host, not estimated.

### Host (post-resize, verified 2026-07-26)

```
Vultr · Ubuntu 24.04.4 LTS · 144.202.88.7 · hostname: lantzbuilds
CPU      2 vCPU  Intel Xeon (Skylake) @ 2.0 GHz
RAM      3.8 GiB total · 518 MiB used · 3.3 GiB available
Swap     5.3 GiB · 0 B used (never touched)
Disk     75 GB · 59 GB free (18% used)
Runtimes Python 3.12.3 · Node v20.20.2 · nginx 1.24.0
Absent   postgresql · certbot · docker
```

Package availability confirmed in Ubuntu 24.04 repositories — no third-party
apt repos required:

- `postgresql-16` → `16.14-0ubuntu0.24.04.1`
- `postgresql-16-pgvector` → `0.6.0-1`

### Existing tenant

| Unit | Memory | Notes |
|------|--------|-------|
| `clio.service` | 128 MB peak (cgroup) | node, `Restart=on-failure`, `StartLimitBurst=5` |
| `fail2ban` | 68 MB | **`sshd` jail only** — nginx unprotected |
| `nginx` | ~10 MB | stock `default` site, no vhosts, no TLS |
| snapd / postfix / ModemManager / udisks2 / watchdog | ~150 MB | trimmable |

### Application coupling (measured)

Total app code: **10,107 LOC**. Test coverage: **87 LOC in one file** (<1%).

| Component | LOC | Fate |
|-----------|-----|------|
| `app/pages/*` | 2,750 | Deleted (Spec 4) |
| `app/routes.py` | 683 | Deleted (Spec 4) — pure Gradio nav wiring, not HTTP routes |
| `app/theme.py`, `app/config/state.py` | — | Deleted (Spec 4) |
| `app/config/database.py` | 1,116 | Rewritten behind repository interface (Spec 2) |
| `app/config/views.py` | 266 | **Deleted** (Spec 2) — JS map/reduce as Python strings; ports to nothing |
| `app/services/hevy_api.py` | 1,022 | Survives unchanged |
| `app/services/vector_store.py` | 844 | Rewritten for pgvector (Spec 2) |
| `app/services/openai_service.py` | 752 | Split (Spec 3) |
| `app/models/*` (Pydantic v2) | — | Survives; becomes schema source of truth |

**There is no REST API in this codebase.** FastAPI is present only as Gradio 5's
transitive dependency. The API layer is net-new work in Spec 4, not a port.

---

## 3. Security findings requiring remediation

These were discovered during assessment and are in scope for this spec.

### 3.1 Clio publicly exposed over plaintext HTTP — **critical**

```
ufw:   3000/tcp  ALLOW  Anywhere
clio:  node listening on 0.0.0.0:3000
nginx: no TLS, no certificates
```

Clio's capture API is reachable from the open internet with no transport
encryption. `CAPTURE_API_TOKEN` crosses the network in cleartext on every
request — sniffable in transit and replayable once captured.

**The port is being actively probed.** Observed `GET /v404/exec` against Clio on
port 3000 at 15:31:38 on 2026-07-26.

**The API has never had a legitimate caller.** Every Clio log entry since boot is
internal cron (`Processed 0 captures`, repeatedly). No external source IPs. This
is consistent with `.env`, where `MS_TENANT_ID`, `NOTION_API_KEY`, and
`SUNSAMA_API_KEY` are all commented out — no webhook integration is configured.

**Resolution:** bind Clio to `127.0.0.1`, delete the ufw rule for 3000, access via
SSH tunnel (`ssh -L 3000:localhost:3000`). Grant Clio no domain and no
certificate. If webhook ingress is configured later, add `clio.lantzbuilds.com`
at that point — deliberately *not* on `formava.io`, because Certificate
Transparency logs are public and permanent, and would publish an internal tool
in the product domain's record indefinitely.

### 3.2 Unfiltered hostile scanning — **medium**

261 unsolicited requests to nginx in ~24h, including `zgrab/0.x` (ZMap
internet-wide scanner), a Dahua camera RCE probe (`GET /SDK/webLanguage`), and
CGI path enumeration. fail2ban has only the `sshd` jail, so none of it is
filtered.

**Resolution:** add `nginx-badbots` and `nginx-http-auth` jails.

### 3.3 Credential exposure — **high**

`VPS_PASSWORD` and `CAPTURE_API_TOKEN` were transmitted in plaintext during
assessment and are present in conversation logs. SSH currently permits password
authentication.

**Resolution:** rotate the VPS root password and `CAPTURE_API_TOKEN`; set
`PasswordAuthentication no` (the `VPS_KEY_PATH` in `.env` is already configured).

### 3.4 Silent database fallback — **medium**

`app/config/database.py:112` — `_create_mock_database()` installs a hand-rolled
in-memory dict when CouchDB is unreachable. The application starts healthy and
serves an empty database instead of failing. On Render this could have masked
outages indefinitely.

**Resolution:** the `/health` endpoint delivered by this spec fails loudly on
database unavailability. The pattern is not carried into the new persistence
layer in Spec 2.

---

## 4. Target architecture

```
                        Internet
                           │  ufw: 22, 80, 443 only
                           ▼
                  ┌──────────────────┐
                  │  nginx 1.24      │  TLS (certbot), HTTP→HTTPS,
                  │                  │  HSTS, security headers
                  └──────────────────┘
                     │
       formava.io / www.formava.io
                     │
                     ▼
       ┌──────────────────────────┐        ┌────────────────────────┐
       │ Next.js BFF              │        │ Clio                   │
       │ 127.0.0.1:3001           │        │ 127.0.0.1:3000         │
       │ systemd: formava-web     │        │ systemd: clio          │
       └──────────────────────────┘        │ (rebound from 0.0.0.0) │
                     │                      │ no domain, SSH tunnel  │
                     │ server-side fetch    └────────────────────────┘
                     ▼
       ┌──────────────────────────┐
       │ FastAPI / uvicorn        │  no public vhost — BFF-only consumer
       │ 127.0.0.1:8000           │
       │ systemd: formava-api     │
       └──────────────────────────┘
                     │ unix socket
                     ▼
       ┌──────────────────────────┐
       │ Postgres 16 + pgvector   │  loopback only, scram-sha-256
       │ systemd: postgresql      │
       └──────────────────────────┘
```

### Design decisions and rationale

**Postgres + pgvector over MongoDB or CouchDB.** The queries Formava actually
runs are analytical (`get_workout_stats`, `get_workout_progression`,
`get_workouts_by_date_range`); the `rereduce` block in `views.py` hand-rolls SQL
`GROUP BY`. CouchDB was originally chosen because Render offered a document store,
not for its replication features — which are unused. Decisively, pgvector
collapses `chromadb` into the same database, deleting `chroma-hnswlib` — the C++
compile that forces `build-essential` into the Dockerfile and creates the
build-time memory spike. One datastore instead of two, and Alembic provides real
migrations where `recreate_all_design_documents()` provided redefinition.

**Native systemd + venv on the VPS; Docker Compose for local development only.**
Removing `chromadb` eliminates the native-compilation problem that made
containers attractive. Native matches the pattern `scripts/deploy.sh` already
uses for Clio, avoids ~100 MB of daemon overhead, and removes a layer of
indirection when debugging. Compose is retained for local Postgres.

**Python 3.12** (the system version) rather than installing 3.11. The existing
3.11 pin exists largely because `chroma-hnswlib` does not build on 3.12 — and
that dependency is being deleted. Using the system interpreter avoids
maintaining a second runtime.

**Node 20** to match the host; `frontend/Dockerfile` currently specifies
`node:18-alpine`.

**FastAPI receives no public vhost.** Under the BFF pattern the browser never
calls it directly — Next.js does, server-side, over loopback. A public
`api.formava.io` would add attack surface with no consumer. It can be added if a
mobile or third-party client materialises.

**`MemoryMax=` on both Formava units.** `clio.service` uses
`Restart=on-failure` with `StartLimitBurst=5`, so five OOM kills inside 60
seconds leaves Clio permanently dead. Capping Formava's units means the kernel
terminates the capped unit rather than Clio, making co-tenancy failure
non-catastrophic.

### Memory budget

| Component | RAM |
|-----------|-----|
| Existing baseline (Clio, nginx, fail2ban, OS) | 518 MB |
| Postgres 16 (`shared_buffers=256MB`) | ~320 MB |
| FastAPI (after deleting chromadb / onnxruntime / langchain) | ~250 MB |
| Next.js standalone | ~120 MB |
| **Total** | **~1.2 GB of 3.8 GB — 32%** |

Leaves headroom to reintroduce a staging tier later if desired.

---

## 5. Deliverables

### 5.1 DNS

| Record | Type | Value |
|--------|------|-------|
| `formava.io` | A | 144.202.88.7 |
| `www.formava.io` | A | 144.202.88.7 |

No DNS record for Clio or for FastAPI.

### 5.2 Provisioning (idempotent, re-runnable)

- Install `postgresql-16`, `postgresql-16-pgvector`, `certbot`,
  `python3-certbot-nginx`, `python3.12-venv`
- Create `formava` database and role; `CREATE EXTENSION vector`
- Tune `postgresql.conf` for 2 vCPU / 3.8 GB: `shared_buffers=256MB`,
  `effective_cache_size=1GB`, `max_connections=50`
- Postgres bound to loopback, `scram-sha-256` authentication

### 5.3 Security remediation

Implements §3 in full:

- Rebind Clio to `127.0.0.1:3000`; `ufw delete allow 3000/tcp`
- Rotate VPS root password and `CAPTURE_API_TOKEN`
- `PasswordAuthentication no` in `sshd_config`; confirm key auth works **before**
  applying
- fail2ban: add `nginx-badbots` and `nginx-http-auth` jails
- nginx: HTTP→HTTPS redirect, HSTS, `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`

### 5.4 systemd units

- `formava-api.service` — uvicorn on `127.0.0.1:8000`, venv interpreter,
  `EnvironmentFile=/etc/formava/formava.env`, `Restart=on-failure`,
  `MemoryMax=768M`
- `formava-web.service` — `node server.js` on `127.0.0.1:3001`, same restart
  policy, `MemoryMax=512M`

Cap rationale: each ceiling sits roughly 3× above measured steady-state, so
ordinary spikes do not trigger kills, while the combined cap (1,280 MB) plus
Postgres (320 MB) plus existing baseline (518 MB) totals ~2.1 GB against 3.8 GB.
A runaway in either Formava unit is therefore terminated by the kernel before it
can pressure `clio.service` into its `StartLimitBurst=5` permanent-failure state.

### 5.5 Thin-slice payload

- Minimal FastAPI application exposing `GET /health`, asserting **both** Postgres
  connectivity and presence of the `vector` extension, returning JSON
- **Fails loudly.** No fallback, mock, or degraded mode — explicitly the inverse
  of `_create_mock_database()`
- Deploy the existing Next.js scaffold as-is with a BFF route handler that calls
  `/health` server-side, proving the entire chain: TLS → nginx → Next → FastAPI →
  Postgres
- pytest coverage for the `/health` application against a Compose Postgres,
  establishing the ≥80% standard on new code from the outset

### 5.6 Deploy and operations

- `scripts/deploy_vps.sh` — modelled on Clio's `scripts/deploy.sh` (rsync → venv
  install → `systemctl restart`), with subcommands `deploy|sync|restart|logs|status`
- Secrets in `/etc/formava/formava.env`, root-owned `0600`, referenced via
  systemd `EnvironmentFile` — never rsynced, never committed
- Nightly `pg_dump` via systemd timer to `/var/backups/formava`, 7-day retention
- Replace both `echo "This would trigger Render deployment"` stubs in
  `.github/workflows/ci.yml`
- Build artifacts in CI, not on the host — `npm run build` for Next.js 15 wants
  1.5–2 GB, which is affordable at 3.8 GB but needlessly contends with Clio

---

## 6. Verification

Exit criteria, expressed as a re-runnable assertion script:

```
✓ curl -I http://formava.io            → 301 to https
✓ curl https://formava.io/             → Next.js scaffold renders
✓ curl https://formava.io/api/health   → {"db":"ok","pgvector":"0.6.0"}
✓ systemctl is-active postgresql formava-api formava-web clio nginx
✓ ufw status                           → 22, 80, 443 only
✓ ss -tlnp                             → :3000, :3001, :8000 on 127.0.0.1 only
✓ certbot renew --dry-run              → success
✓ systemctl list-timers                → pg_dump timer scheduled
✓ pg_dump artifact present in /var/backups/formava
✓ ssh with password                    → refused
✓ fail2ban-client status               → sshd, nginx-badbots, nginx-http-auth
✓ systemctl show formava-api -p MemoryMax  → 805306368  (768M)
✓ systemctl show formava-web -p MemoryMax  → 536870912  (512M)
✓ free -h                              → total usage ≤ 1.5 GB
```

**Rollback:** Render remains live and unmodified throughout. This spec is not a
cutover — if VPS work stalls, production is unaffected. Render is decommissioned
only after Spec 4.

---

## 7. Out of scope

- Database schema, tables, or migrations beyond `CREATE EXTENSION vector` (Spec 2)
- Any Gradio deployment (never; deleted in Spec 4)
- LLM provider changes (Spec 3)
- Data migration from Cloudant — data loss is explicitly acceptable
- A staging tier — dropped during migration; reintroduce later if wanted
- `api.formava.io` — add only when a non-browser client exists

---

## 8. Direction recorded for later specs

**Spec 3 (LLM seam)** — agreed direction, revisitable when that spec is written:
define a provider `Protocol` with a single `OpenAICompatibleProvider`
implementation covering OpenAI, OpenRouter, Together, Groq, vLLM, and Ollama.
This covers the possible future of self-hosting an open model on a separate
Vultr GPU instance, since vLLM and Ollama both speak the OpenAI wire protocol.
Native providers (e.g. Anthropic) are added only when a native feature —
prompt caching, extended thinking — justifies the adapter.

Known leaks the seam must address regardless of provider:

1. **Embedding dimensions are schema, not configuration.** A pgvector column is
   declared `vector(N)` at DDL time. Changing embedding model requires an Alembic
   migration plus a full re-embed. Cheap here — the corpus is a 69 KB checked-in
   `hevy_exercise_ids.json` plus `bootstrap_vectorstore.py` — but the schema must
   record which model produced the vectors so staleness is detectable.
   *Verify before choosing a model:* pgvector's HNSW/IVFFlat indexes are believed
   to cap at 2000 dimensions, which would exclude 3072-dim models at full width.
2. **Tokenization.** `openai_service.py:501` calls
   `tiktoken.encoding_for_model("gpt-4-turbo")`. This is OpenAI-specific BPE and
   silently mis-counts against other model families.
3. **Structured output.** `generate_routine` parses JSON from responses. The
   abstraction should return validated Pydantic models, not raw strings.

**Test coverage** is under 1% against 10,107 LOC. Specs 2–4 each carry their own
coverage obligation; retrofitting at the end is not viable given two refactors
that touch the LLM layer and delete the entire UI layer.
