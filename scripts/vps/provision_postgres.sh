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
apt-get update -qq
apt-get install -y --no-install-recommends \
    "postgresql-${PG_VERSION}" \
    "postgresql-${PG_VERSION}-pgvector"

log "Ensuring role ${DB_USER} exists..."
# The password-bearing statements are piped to psql via stdin (heredoc)
# rather than passed with -c, so the plaintext never appears in psql's argv
# either.
if ! sudo -u postgres psql -tAc \
    "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
    sudo -u postgres psql <<SQL
CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
SQL
else
    log "Role exists; syncing password."
    sudo -u postgres psql <<SQL
ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';
SQL
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
sudo -u postgres psql -d "${DB_NAME}" -tAc \
    "SELECT extversion FROM pg_extension WHERE extname='vector'"
ss -tlnp | grep 5432 || true

log "Done."
