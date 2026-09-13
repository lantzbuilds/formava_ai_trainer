#!/usr/bin/env bash
# Provision Postgres 16 + pgvector for Formava. Idempotent: safe to re-run.
#
# Usage:
#   printf '%s' "$PASSWORD" | ./provision_postgres.sh
#   ./provision_postgres.sh                 # interactive prompt (TTY)
set -euo pipefail

# Read the password from stdin rather than argv: a positional argument is
# visible in ps/proc for the lifetime of the process.
#
# `read` exits nonzero on EOF even when it did capture data -- e.g.
# `printf '%s' "$PASSWORD" | ...` (no trailing newline, as shown in Usage
# above) hits EOF right after the value. Under `set -e` that would abort
# the script immediately after this line despite DB_PASSWORD being set
# correctly, so failure here is tolerated and delegated to the explicit
# emptiness check below.
#
# DB_PASSWORD is pre-initialized so that if fd 0 is fully closed (e.g.
# `... <&-`, as opposed to merely empty/EOF), `read` fails before ever
# assigning it and the `${#DB_PASSWORD}` check below still has a defined
# variable to test under `set -u`, giving our own error message instead of
# a raw "unbound variable" abort.
#
# `IFS=` is scoped to each `read` so bash does not field-split the input:
# plain `read` strips leading/trailing whitespace, which would silently
# truncate a password that has boundary spaces (e.g. pasted from a
# generator or a manager) instead of erroring -- exactly the silent-wrong-
# state failure mode this hardening exists to eliminate. Scoping it to the
# `read` command itself (rather than `export IFS=` or setting it at top of
# script) means it does not leak into any other command in this script.
DB_PASSWORD=""
if [ -t 0 ]; then
    printf 'Postgres password for role formava: ' >&2
    IFS= read -rs DB_PASSWORD || true
    printf '\n' >&2
else
    IFS= read -r DB_PASSWORD || true
fi

if [ "${#DB_PASSWORD}" -eq 0 ]; then
    echo "ERROR: no password supplied on stdin" >&2
    exit 1
fi

DB_NAME="formava"
DB_USER="formava"
PG_VERSION="16"
PG_CONF="/etc/postgresql/${PG_VERSION}/main/postgresql.conf"

log() { echo "[provision-postgres] $*"; }

log "Installing packages from Ubuntu repositories..."
export DEBIAN_FRONTEND=noninteractive
# NEEDRESTART_SUSPEND stops needrestart from bouncing unrelated services when a
# shared library is upgraded underneath them. This script's own apt call once
# restarted clio-cron one second after a libpq5 bump -- on a box whose whole
# premise is that Formava must not disturb its co-tenant.
export NEEDRESTART_SUSPEND=1
apt-get update -qq
apt-get install -y --no-install-recommends \
    "postgresql-${PG_VERSION}" \
    "postgresql-${PG_VERSION}-pgvector"

log "Ensuring role ${DB_USER} exists..."
# The password-bearing statements are piped to psql via stdin (heredoc)
# rather than passed with -c, so the plaintext never appears in psql's argv
# either.
#
# ON_ERROR_STOP=1 is REQUIRED, not decorative: psql exits 0 on a SQL error
# unless it is set, so `set -e` never fires and the script would report
# success having done nothing. Without it, a password containing a single
# quote breaks the statement below, the role keeps its old password (or is
# never created), and /etc/formava/formava.env is written with the new one --
# leaving the API unable to authenticate, with every step reporting success.
#
# The single quote is the only injection vector here. Parameter-expansion
# results are not re-scanned by the shell, so $, backticks and backslashes in
# the password are already inert inside the heredoc; doubling the quote is
# what makes it safe as a SQL literal.
DB_PASSWORD_SQL="${DB_PASSWORD//\'/\'\'}"

if ! sudo -u postgres psql -v ON_ERROR_STOP=1 -tAc \
    "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
    sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD_SQL}';
SQL
else
    log "Role exists; syncing password."
    sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD_SQL}';
SQL
fi

log "Ensuring database ${DB_NAME} exists..."
if ! sudo -u postgres psql -v ON_ERROR_STOP=1 -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
    sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}"
fi

log "Enabling pgvector in ${DB_NAME}..."
# ON_ERROR_STOP again: without it, a missing postgresql-16-pgvector package
# makes this fail while the script prints "Done."
sudo -u postgres psql -v ON_ERROR_STOP=1 -d "${DB_NAME}" \
    -c "CREATE EXTENSION IF NOT EXISTS vector;"

log "Applying tuning for 2 vCPU / 3.8 GB..."
# Keep one pristine copy of the config from before this script ever edited it.
# -n means the first run wins, so a later re-run cannot overwrite the original
# with an already-managed version.
cp -n "${PG_CONF}" "${PG_CONF}.pre-formava" 2>/dev/null || true
# Values are fixed by the spec's memory budget. Appended in a marked block so
# re-runs replace rather than accumulate.
OLD_MARKER="# --- formava tuning (managed) ---"
BEGIN_MARKER="# --- formava tuning (managed) — do not edit between markers ---"
END_MARKER="# --- end formava tuning ---"

# One-time migration from the old unbounded-marker format (no end marker).
# The old block is known to always be the final lines of the file -- it was
# always appended last by this same script and this script never appended
# anything after it -- so old-marker-to-EOF is safe *only* for this specific
# legacy case. This is NOT the general deletion strategy below; it must
# never be used once the bounded format (with END_MARKER) is in place.
if grep -qF "${OLD_MARKER}" "${PG_CONF}" && ! grep -qF "${BEGIN_MARKER}" "${PG_CONF}"; then
    sed -i "/${OLD_MARKER}/,\$d" "${PG_CONF}"
fi

# Delete only the managed block, never to end-of-file: anything an operator
# appends below our block must survive a re-run. Neither marker contains a
# '/', so the default sed delimiter is safe here.
if grep -qF "${BEGIN_MARKER}" "${PG_CONF}"; then
    sed -i "/${BEGIN_MARKER}/,/${END_MARKER}/d" "${PG_CONF}"
fi

cat >> "${PG_CONF}" <<EOF
${BEGIN_MARKER}
listen_addresses = 'localhost'
shared_buffers = 256MB
effective_cache_size = 1GB
max_connections = 50
password_encryption = scram-sha-256
${END_MARKER}
EOF

log "Restarting Postgres..."
systemctl restart postgresql
systemctl enable postgresql

log "Verifying..."
sudo -u postgres psql -v ON_ERROR_STOP=1 -d "${DB_NAME}" -tAc \
    "SELECT extversion FROM pg_extension WHERE extname='vector'"

# `|| true` here used to swallow the one thing this step exists to detect: if
# Postgres is not listening, the script reported success. Assert the bind
# instead, and require it to be loopback -- a wildcard bind would expose the
# database to the internet, which §5.2 forbids.
if ss -tln | grep -qE '127\.0\.0\.1:5432|\[::1\]:5432'; then
    log "Postgres listening on loopback:5432"
else
    log "FATAL: Postgres is not listening on loopback:5432"
    ss -tln | grep 5432 || log "  (nothing bound to 5432 at all)"
    exit 1
fi
if ss -tln | grep -qE '0\.0\.0\.0:5432|\[::\]:5432'; then
    log "FATAL: Postgres is bound to a wildcard address, not loopback"
    exit 1
fi

log "Done."
