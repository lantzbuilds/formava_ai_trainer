#!/usr/bin/env bash
# Nightly pg_dump of the formava database with 7-day retention.
set -euo pipefail

BACKUP_DIR="/var/backups/formava"
DB_NAME="formava"
RETENTION_DAYS=7
STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="${BACKUP_DIR}/${DB_NAME}-${STAMP}.sql.gz"
TMP="${TARGET}.partial"

mkdir -p "${BACKUP_DIR}"
chmod 0700 "${BACKUP_DIR}"

# Dump to a .partial name and rename only on success. Writing straight to
# ${TARGET} truncates it before pg_dump runs, so a failed dump left a garbage
# file behind that still satisfied a "does a .sql.gz exist?" check.
cleanup() { rm -f "${TMP}"; }
trap cleanup EXIT

# PIPESTATUS, not $?: `set -e` does not fire when the first command in a
# pipeline fails but gzip succeeds, so a failed pg_dump would otherwise produce
# a valid gzip of nothing.
sudo -u postgres pg_dump --no-owner "${DB_NAME}" | gzip > "${TMP}"
DUMP_STATUS="${PIPESTATUS[0]}"
if [ "${DUMP_STATUS}" -ne 0 ]; then
    echo "ERROR: pg_dump exited ${DUMP_STATUS}; discarding ${TMP}" >&2
    exit 1
fi

SIZE="$(stat -c%s "${TMP}")"

# Absolute floor: catches a completely empty or truncated dump.
if [ "${SIZE}" -lt 100 ]; then
    echo "ERROR: backup is ${SIZE} bytes, below the 100-byte floor" >&2
    exit 1
fi

# Relative floor: catches the failure the absolute one cannot see. Once there
# is real data, a dump that silently captured nothing -- wrong DB_NAME, a
# revoked grant, a renamed role -- still lands near the empty-schema size and
# would sail past a fixed threshold. Compare against the most recent previous
# backup instead and refuse anything under half its size.
PREVIOUS="$(find "${BACKUP_DIR}" -name "${DB_NAME}-*.sql.gz" -type f \
            -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)"
if [ -n "${PREVIOUS}" ]; then
    PREV_SIZE="$(stat -c%s "${PREVIOUS}")"
    if [ "${SIZE}" -lt "$((PREV_SIZE / 2))" ]; then
        echo "ERROR: backup is ${SIZE} bytes, less than half of the previous" \
             "${PREV_SIZE} bytes (${PREVIOUS}). Refusing to accept it." >&2
        exit 1
    fi
fi

# Prove it restores, every night, rather than once by hand during setup.
# A dump that cannot be restored is not a backup, and gzip integrity alone
# does not prove the SQL is loadable. Restored into a scratch database that is
# always dropped, so this never touches ${DB_NAME}.
VERIFY_DB="${DB_NAME}_restore_check"
drop_verify_db() {
    sudo -u postgres dropdb --if-exists "${VERIFY_DB}" >/dev/null 2>&1 || true
}
trap 'drop_verify_db; cleanup' EXIT

drop_verify_db
sudo -u postgres createdb "${VERIFY_DB}"
if ! gunzip -c "${TMP}" | sudo -u postgres psql -v ON_ERROR_STOP=1 \
        -q -d "${VERIFY_DB}" >/dev/null 2>&1; then
    echo "ERROR: backup did not restore into ${VERIFY_DB}; discarding" >&2
    exit 1
fi

# Compare table counts so the restore is checked for content, not just for
# exiting zero. An empty-schema database legitimately reports 0 on both sides.
SRC_TABLES="$(sudo -u postgres psql -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" \
  -d "${DB_NAME}")"
DST_TABLES="$(sudo -u postgres psql -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" \
  -d "${VERIFY_DB}")"
if [ "${SRC_TABLES}" != "${DST_TABLES}" ]; then
    echo "ERROR: restore has ${DST_TABLES} tables, source has ${SRC_TABLES}" >&2
    exit 1
fi

drop_verify_db
mv "${TMP}" "${TARGET}"
trap - EXIT

find "${BACKUP_DIR}" -name "${DB_NAME}-*.sql.gz" \
    -mtime "+${RETENTION_DAYS}" -delete

echo "Backup complete: ${TARGET} ($(du -h "${TARGET}" | cut -f1)," \
     "${SRC_TABLES} tables, restore verified)"
