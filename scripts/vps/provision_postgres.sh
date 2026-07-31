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
