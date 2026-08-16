#!/usr/bin/env bash
# Assert every Spec 1 exit criterion. Safe to re-run. Exits non-zero on failure.
#
# Usage: ./scripts/vps/verify.sh
#
# Needs key-based root SSH to the VPS. Password auth is off, so sshpass and
# friends will not work. Clio's two scoped tokens are read off the host into
# this script's environment rather than passed in, so no secret reaches shell
# history or the process table of another user.
#
# `set -e` is deliberately omitted: a failing check must not abort the run.
# Every assertion should report, and the exit code is the roll-up.
set -uo pipefail

VPS="${VPS_HOST:-144.202.88.7}"
SSH="ssh -o BatchMode=yes -o ConnectTimeout=10 root@${VPS}"
CLIO="https://clio.lantzbuilds.com"
FAIL=0

pass() { echo "  ok    $1"; }
fail() { echo "  FAIL  $1"; FAIL=1; }

check() { # description, actual, expected
    [ "$2" = "$3" ] && pass "$1 ($2)" || fail "$1 — got '$2', want '$3'"
}

code() { curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$@"; }

# nginx rate-limits /capture and /capture/<id>/fix to 10r/m with burst 5
# (see nginx-clio.conf). This script spends the whole burst, so a re-run inside
# the same minute would get 503s from nginx and report false failures. Back off
# and retry instead: the bucket refills one slot every 6s.
capture_code() {
    local c i
    for i in 1 2 3 4; do
        c="$(code "$@")"
        [ "$c" != "503" ] && { echo "$c"; return; }
        sleep 7
    done
    echo "$c"
}

echo "== SSH =="
if $SSH true 2>/dev/null; then
    pass "key-based root SSH"
else
    echo "  FAIL  key-based root SSH — cannot continue"
    exit 1
fi

# Read once, reuse. Never echoed.
CAPTURE_TOKEN="$($SSH "grep '^CAPTURE_TOKEN=' /opt/clio/.env | cut -d= -f2-")"
SESSION_TOKEN="$($SSH "grep '^SESSION_TOKEN=' /opt/clio/.env | cut -d= -f2-")"
[ -n "$CAPTURE_TOKEN" ] && pass "CAPTURE_TOKEN present" || fail "CAPTURE_TOKEN present"
[ -n "$SESSION_TOKEN" ] && pass "SESSION_TOKEN present" || fail "SESSION_TOKEN present"
check "legacy CAPTURE_API_TOKEN removed" \
  "$($SSH "grep -c '^CAPTURE_API_TOKEN=' /opt/clio/.env")" "0"

echo
echo "== Formava =="
check "http->https redirect" "$(code http://formava.io)" "301"
check "www->apex redirect"   "$(code http://www.formava.io)" "301"
check "https serves app"     "$(code https://formava.io)" "200"

HEALTH="$(curl -s --max-time 15 https://formava.io/api/health)"
echo "$HEALTH" | grep -q '"db":"ok"' \
  && pass "BFF health chain ($HEALTH)" || fail "BFF health chain — got '$HEALTH'"

# This script proves Clio's auth works by deliberately provoking 401s — which is
# exactly the signal the clio-capture-auth jail bans on (maxretry 5, findtime
# 600s, bantime 24h). Left alone, one run bans the operator for a day, and the
# "safe to re-run" guarantee is a lie.
#
# So bracket the Clio section: whitelist this machine in that one jail for the
# duration, then remove it and clear any ban. The IP comes from the host's view
# of our SSH connection, which is the same egress nginx logs, and needs no
# external lookup service. The trap makes removal unconditional so an
# interrupted run never leaves the jail weakened.
MYIP="$($SSH 'echo $SSH_CLIENT' | cut -d' ' -f1)"

f2b_unguard() {
    [ -n "${MYIP:-}" ] || return 0
    $SSH "fail2ban-client set clio-capture-auth delignoreip ${MYIP}; \
          fail2ban-client set clio-capture-auth unbanip ${MYIP}" >/dev/null 2>&1 || true
}

if [ -n "$MYIP" ]; then
    trap f2b_unguard EXIT INT TERM
    $SSH "fail2ban-client set clio-capture-auth addignoreip ${MYIP}" >/dev/null 2>&1 \
      && pass "fail2ban guard armed for ${MYIP}" \
      || fail "fail2ban guard armed for ${MYIP}"
else
    fail "could not determine this machine's source IP — refusing to self-ban"
    echo "SOME CHECKS FAILED"
    exit 1
fi

echo
echo "== Clio: closed paths =="
# Served by `location / { return 404; }`, which carries no limit_req, so these
# cost nothing against the capture bucket.
for p in /status /capture/bulk /capture/fix /capture/fix/recent /v404/exec; do
    check "closed: $p" \
      "$(code -H "Authorization: Bearer ${CAPTURE_TOKEN}" "${CLIO}${p}")" "404"
done

echo
echo "== Clio: published paths =="
check "GET /health reachable" "$(code ${CLIO}/health)" "200"
check "GET /capture rejected by limit_except" \
  "$(capture_code -H "Authorization: Bearer ${CAPTURE_TOKEN}" ${CLIO}/capture)" "403"
check "POST /capture without token" \
  "$(capture_code -X POST -H 'Content-Type: application/json' \
     --data '{"text":"x"}' ${CLIO}/capture)" "401"

echo
echo "== Clio: token scope isolation =="
# The point of the Task 6 token split. Each token must be accepted on its own
# surface and rejected on the other's.
#
# An empty JSON object is used rather than a real payload: it clears auth and
# then fails validation with 400, which proves the token was accepted without
# writing a capture into the vault on every run.
check "capture token accepted on /capture" \
  "$(capture_code -X POST -H "Authorization: Bearer ${CAPTURE_TOKEN}" \
     -H 'Content-Type: application/json' --data '{}' ${CLIO}/capture)" "400"
check "capture token accepted on /capture/<id>/fix" \
  "$(capture_code -X POST -H "Authorization: Bearer ${CAPTURE_TOKEN}" \
     -H 'Content-Type: application/json' --data '{}' \
     ${CLIO}/capture/verify-probe/fix)" "400"
check "capture token REJECTED on /api/sessions" \
  "$(code -H "Authorization: Bearer ${CAPTURE_TOKEN}" \
     ${CLIO}/api/sessions/verify-probe)" "401"

# /api/sessions is published — the Clio CLI depends on it. Proven with a GET on
# an id that does not exist: 404 means the token authenticated and the lookup
# missed, so the session token is live without a session row being created.
check "session token accepted on /api/sessions" \
  "$(code -H "Authorization: Bearer ${SESSION_TOKEN}" \
     ${CLIO}/api/sessions/verify-probe)" "404"
check "session token REJECTED on /capture" \
  "$(capture_code -X POST -H "Authorization: Bearer ${SESSION_TOKEN}" \
     -H 'Content-Type: application/json' --data '{}' ${CLIO}/capture)" "401"
check "/api/sessions requires a token" \
  "$(code ${CLIO}/api/sessions/verify-probe)" "401"

# Close the whitelist window as soon as the last 401-provoking check is done,
# rather than leaving it open for the remaining minute of host checks. The trap
# stays armed as a safety net; a second removal is a no-op.
f2b_unguard
pass "fail2ban guard released"

echo
echo "== Network =="
# Tested from off-host on purpose. Clio still binds 0.0.0.0 (Clio-side finding
# 3, a one-line listen() change), so ufw is the only thing closing this port. A
# loopback test would pass and prove nothing.
timeout 8 curl -s -o /dev/null "http://${VPS}:3000/capture" 2>/dev/null \
  && fail "port 3000 blocked from off-host" \
  || pass "port 3000 blocked from off-host"

# Counting rule lines would read 6, not 3: ufw prints a v4 and a v6 rule for
# each port. Compare the distinct port set instead, which also proves no extra
# port (3000 included) is open.
check "ufw open ports" \
  "$($SSH "ufw status | grep -oE '^[0-9]+' | sort -un | tr '\n' ','")" \
  "22,80,443,"
check "formava binds loopback only" \
  "$($SSH "ss -tln | grep -cE '0\.0\.0\.0:(3001|8000|5432)'")" "0"

echo
echo "== SSH hardening =="
# The property, not the directive. The directive lives in a drop-in
# (/etc/ssh/sshd_config.d/00-hardening.conf), not the main config, so grepping
# sshd_config reports a false negative. What matters is that a password login
# is actually refused.
#
# Capture the output first rather than piping into `grep -q`: under `pipefail`
# a pipeline reports the *first* non-zero status, and this ssh always exits 255
# on the refusal we are trying to observe, so the grep result would be masked.
PWSSH="$(ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no \
             -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
             "root@${VPS}" true </dev/null 2>&1 || true)"
case "$PWSSH" in
    *"Permission denied"*) pass "password login refused" ;;
    *) fail "password login refused — got '${PWSSH}'" ;;
esac
check "sshd effective passwordauthentication" \
  "$($SSH "sshd -T | grep '^passwordauthentication' | awk '{print \$2}'")" "no"

echo
echo "== Services =="
check "six units active" \
  "$($SSH 'systemctl is-active postgresql formava-api formava-web clio clio-cron nginx | sort -u | tr -d "\n"')" \
  "active"
check "api MemoryMax" \
  "$($SSH 'systemctl show formava-api -p MemoryMax --value')" "805306368"
check "web MemoryMax" \
  "$($SSH 'systemctl show formava-web -p MemoryMax --value')" "536870912"
check "gradio absent from host" \
  "$($SSH 'test -e /opt/formava/app/pages; echo $?')" "1"

echo
echo "== fail2ban =="
# A jail reports "active" even when it is monitoring nothing: defaults-debian
# sets backend=systemd, which silently overrides logpath. Assert the file, not
# the status. sshd is exempt — it reads the journal by design and works.
check "sshd jail active" \
  "$($SSH 'fail2ban-client status sshd >/dev/null 2>&1; echo $?')" "0"
for jail in nginx-badbots nginx-http-auth clio-capture-auth; do
    LOGPATH="$($SSH "fail2ban-client get ${jail} logpath 2>/dev/null" | grep -oE '/var/log/[^ ]+')"
    [ -n "$LOGPATH" ] \
      && pass "jail ${jail} reads ${LOGPATH}" \
      || fail "jail ${jail} monitors no file (backend=systemd override?)"
done

echo
echo "== Backups =="
check "backup timer" "$($SSH 'systemctl is-active formava-backup.timer')" "active"
$SSH 'ls /var/backups/formava/*.sql.gz >/dev/null 2>&1' \
  && pass "backup artifact present" || fail "backup artifact present"

echo
echo "== TLS =="
$SSH 'certbot renew --dry-run' >/dev/null 2>&1 \
  && pass "cert renewal dry-run" || fail "cert renewal dry-run"

echo
echo "== Memory =="
$SSH 'free -h | head -2'

echo
[ "$FAIL" -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit "$FAIL"
