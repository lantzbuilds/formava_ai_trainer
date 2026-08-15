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
