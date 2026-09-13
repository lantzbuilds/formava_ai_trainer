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
# Runtime is roughly a minute from cold, but climbs toward five if it is run
# several times in quick succession: the /capture rate-limit bucket refills at
# one slot every 6s and the backoff below waits for it. A long pause during the
# Clio section is the script being patient, not hung.
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
    # Still limited after 4 tries. Say so, rather than reporting a bare 503 that
    # reads like the endpoint returned it.
    echo "rate-limited(503)"
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
# A 301 alone does not prove the redirect goes anywhere useful -- it could
# point at http, or at the wrong host. Assert the destination too, by following
# the whole chain to its final URL rather than reading one hop.
#
# www is a TWO-hop redirect: http://www.formava.io -> https://www.formava.io
# (certbot's http->https upgrade) -> https://formava.io (the www->apex rule).
# %{redirect_url} only sees the first hop, so it read https://www.formava.io/
# and failed. %{url_effective} after -L is the address the browser actually
# lands on, which is what the criterion is really about.
check "http->https redirect" "$(code http://formava.io)" "301"
check "http->https lands at apex https" \
  "$(curl -sL -o /dev/null -w '%{url_effective}' --max-time 15 http://formava.io)" \
  "https://formava.io/"
check "www->apex redirect" "$(code http://www.formava.io)" "301"
check "www->apex lands at apex https" \
  "$(curl -sL -o /dev/null -w '%{url_effective}' --max-time 15 http://www.formava.io)" \
  "https://formava.io/"

# §6 says the Next.js app renders, not merely that something returns 200. Grep
# for a string only the real page produces.
check "https serves app" "$(code https://formava.io)" "200"
BODY="$(curl -s --max-time 15 https://formava.io/)"
echo "$BODY" | grep -qi 'formava' \
  && pass "app HTML renders (found 'formava' in body)" \
  || fail "app HTML renders — 'formava' not in body, got $(printf '%s' "$BODY" | wc -c) bytes"

# Assert BOTH keys §6 names. db:"ok" is currently unreachable without pgvector,
# but that coupling lives in checks.py and is invisible from here -- if it were
# ever loosened, this check would still hold the line.
HEALTH="$(curl -s --max-time 15 https://formava.io/api/health)"
echo "$HEALTH" | grep -q '"db":"ok"' \
  && pass "BFF health chain ($HEALTH)" || fail "BFF health chain — got '$HEALTH'"
echo "$HEALTH" | grep -qE '"pgvector":"[0-9]' \
  && pass "pgvector version reported" || fail "pgvector version — got '$HEALTH'"

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
#
# Both transitions are read back from the jail rather than inferred from
# fail2ban-client's exit status. Arming is safety-critical: if it silently
# failed and we continued, the 401 probes below would ban the operator for a
# day, which is the exact outcome this guard exists to prevent. So this is one
# of the two places the script aborts rather than recording a failure and
# carrying on.
#
# `ssh -4` pins the SSH connection to IPv4 so MYIP is the same address family
# curl will egress from. The VPS listens on [::]:22, so without this a host
# that preferred IPv6 for SSH would whitelist a v6 address while curl used v4,
# and self-ban anyway.
MYIP="$(ssh -4 -o BatchMode=yes -o ConnectTimeout=10 "root@${VPS}" 'echo $SSH_CLIENT' | cut -d' ' -f1)"

case "$MYIP" in
    *[0-9].*[0-9].*[0-9].*[0-9]) ;;
    *)  fail "could not determine this machine's IPv4 source address — refusing to self-ban"
        echo "SOME CHECKS FAILED"; exit 1 ;;
esac

f2b_ignored() { # is $1 currently in the jail's ignore list?
    $SSH "fail2ban-client get clio-capture-auth ignoreip" 2>/dev/null | grep -qF "$1"
}

# If the address is already ignored via the jail's config file, leave it alone:
# delignoreip strips config entries too, which would leave the running jail
# stricter than its own config until the next reload.
PREIGNORED=no
f2b_ignored "$MYIP" && PREIGNORED=yes

f2b_unguard() {
    [ "$PREIGNORED" = yes ] && return 0
    $SSH "fail2ban-client set clio-capture-auth delignoreip ${MYIP}; \
          fail2ban-client set clio-capture-auth unbanip ${MYIP}" >/dev/null 2>&1 || true
}

if [ "$PREIGNORED" = yes ]; then
    pass "fail2ban guard not needed — ${MYIP} already ignored by config"
else
    trap f2b_unguard EXIT INT TERM
    $SSH "fail2ban-client set clio-capture-auth addignoreip ${MYIP}" >/dev/null 2>&1
    if f2b_ignored "$MYIP"; then
        pass "fail2ban guard armed for ${MYIP}"
    else
        fail "fail2ban guard NOT armed — skipping Clio auth probes to avoid a 24h self-ban"
        echo "SOME CHECKS FAILED"; exit 1
    fi
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
#
# Read the jail back afterwards. Reporting "released" on faith would be a check
# that passes while the jail is still weakened — the failure mode this script
# exists to catch elsewhere.
f2b_unguard
if [ "$PREIGNORED" = yes ]; then
    pass "fail2ban guard not used (pre-existing config entry left intact)"
elif f2b_ignored "$MYIP"; then
    fail "fail2ban guard STILL ARMED — jail weakened, remove ${MYIP} by hand"
else
    pass "fail2ban guard released"
fi

echo
echo "== Network =="
# Tested from off-host on purpose. Clio now binds 127.0.0.1:3000 (its finding 3
# landed), so this would pass on the bind alone — but ufw is still the control
# that must hold, and a loopback test would prove nothing either way. Keep
# testing reachability from outside.
timeout 8 curl -s -o /dev/null "http://${VPS}:3000/capture" 2>/dev/null \
  && fail "port 3000 blocked from off-host" \
  || pass "port 3000 blocked from off-host"

# Counting rule lines would read 6, not 3: ufw prints a v4 and a v6 rule for
# each port. Compare the distinct port set instead, which also proves no extra
# port (3000 included) is open.
check "ufw open ports" \
  "$($SSH "ufw status | grep -oE '^[0-9]+' | sort -un | tr '\n' ','")" \
  "22,80,443,"

# The port-set check above reads leading digits, so it is blind to rules added
# by application profile: `ufw allow Postfix` renders as `Postfix  ALLOW  ...`
# with no port number, and would open 25 while the set still read 22,80,443.
# Assert the row count too, so any extra rule in any form is caught.
check "ufw rule count (no app-profile rules)" \
  "$($SSH 'ufw status' | grep -cE 'ALLOW|DENY|REJECT|LIMIT')" "6"

# Parsed here rather than in a quoted remote command: the awk needed to do this
# correctly does not survive a second layer of shell quoting, and `ss -Htln` is
# trivially safe to send.
#
# Asserted positively, by what the sockets ARE bound to rather than by the
# absence of one string. The old `grep -c '0\.0\.0\.0:'` missed two ways to be
# exposed: ss renders an IPv6 wildcard as [::]:8000, which on default Linux
# (net.ipv6.bindv6only=0) accepts IPv4 too, and a bind to the public address
# itself never contains '0.0.0.0' at all. Both counted 0 and passed while the
# port was world-reachable.
SOCKETS="$($SSH 'ss -Htln')"
check "formava binds loopback only" \
  "$(printf '%s\n' "$SOCKETS" | awk '
     {n = split($4, a, ":"); p = a[n]}
     (p == 3001 || p == 8000 || p == 5432) && $4 !~ /^(127\.0\.0\.1|\[::1\]):/ {c++}
     END {print c + 0}')" \
  "0"

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
# The old check tested only app/pages and passed while app/main.py (the Gradio
# entrypoint), app/components and app/state sat on the host -- deploy_vps.sh
# never excluded them. This set is now identical to the deploy's Gradio excludes;
# keep the two in lockstep so neither can drift ahead of the other.
GRADIO_PRESENT="$($SSH 'ls -d \
    /opt/formava/app/main.py \
    /opt/formava/app/pages \
    /opt/formava/app/components \
    /opt/formava/app/theme.py \
    /opt/formava/app/routes.py \
    /opt/formava/app/state \
    /opt/formava/app/config/state.py \
    2>/dev/null | wc -l' | tr -d ' ')"
check "gradio absent from host (entrypoint + UI)" "$GRADIO_PRESENT" "0"

echo
echo "== fail2ban =="
# A jail reports "active" even when it is monitoring nothing: defaults-debian
# sets backend=systemd, which silently overrides logpath. Assert the file, not
# the status. sshd is exempt — it reads the journal by design and works.
check "sshd jail active" \
  "$($SSH 'fail2ban-client status sshd >/dev/null 2>&1; echo $?')" "0"
for jail in nginx-badbots nginx-http-auth clio-capture-auth web-probes; do
    LOGPATH="$($SSH "fail2ban-client get ${jail} logpath 2>/dev/null" | grep -oE '/var/log/[^ ]+')"
    [ -n "$LOGPATH" ] \
      && pass "jail ${jail} reads ${LOGPATH}" \
      || fail "jail ${jail} monitors no file (backend=systemd override?)"
done

# Reading a file is still only the directive. A filter whose regex matches
# nothing in that file protects nothing — which is exactly what happened with
# nginx-badbots: green on logpath for the whole spec while the zgrab and
# /SDK/webLanguage traffic §3.2 names went unfiltered. Assert that each filter
# actually matches its log.
#
# nginx-http-auth is deliberately excluded: it can only ever match auth_basic
# failures, and this host has no auth_basic. It is documented as a no-op in
# fail2ban-nginx.local rather than asserted here.
for jail in web-probes clio-capture-auth; do
    # fail2ban-regex prints "Lines: N lines, X ignored, Y matched, Z missed".
    # The count is the number before " matched" -- grepped as a pair rather
    # than split on whitespace, because the field is literally "matched," with
    # a trailing comma, so $i=="matched" never hit and this always read empty.
    MATCHED="$($SSH "fail2ban-regex /var/log/nginx/access.log /etc/fail2ban/filter.d/${jail}.conf 2>/dev/null" \
               | grep -oE '[0-9]+ matched' | grep -oE '^[0-9]+')"
    [ -n "$MATCHED" ] && [ "$MATCHED" -gt 0 ] 2>/dev/null \
      && pass "filter ${jail} matches live traffic (${MATCHED} lines)" \
      || fail "filter ${jail} matches NOTHING in access.log — jail is blind"
done

# §6 requires captures to be attributable in the access log. The log is also
# what clio-capture-auth reads, so a format change that dropped $remote_addr
# would silently blind that jail too.
check "access log records source IPs" \
  "$($SSH "grep -cE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+ ' /var/log/nginx/access.log" \
     | awk '{print ($1 > 0) ? "yes" : "no"}')" "yes"

echo
echo "== Backups =="
check "backup timer" "$($SSH 'systemctl is-active formava-backup.timer')" "active"
# Existence alone passes forever on a stale artifact while every run since has
# failed. Assert freshness and the last run's result instead.
check "backup artifact fresh (< 2 days)" \
  "$($SSH "find /var/backups/formava -name '*.sql.gz' -mtime -2 | wc -l" | tr -d ' ' | grep -qE '^[1-9]' && echo yes || echo no)" \
  "yes"
check "last backup run result" \
  "$($SSH 'systemctl show formava-backup.service -p Result --value')" "success"

echo
echo "== Response headers =="
# §5.3's headers, and the single most valuable assertion in this script.
#
# Task 6 found that Clio's own helmet emits HSTS *with* includeSubDomains, which
# would bind every other host under lantzbuilds.com to HTTPS-only, and fixed it
# with proxy_hide_header + a replacement add_header. If that pair is ever lost —
# one edited line, or a helmet config change upstream — nothing else here would
# notice, and browsers cache the mistake for a year. It is not rollback-able.
CLIO_HDRS="$(curl -sI --max-time 15 ${CLIO}/health | tr -d '\r')"
if echo "$CLIO_HDRS" | grep -qi '^strict-transport-security: max-age=[1-9]'; then
    echo "$CLIO_HDRS" | grep -qi 'includesubdomains' \
      && fail "clio HSTS carries includeSubDomains — would bind ALL of lantzbuilds.com" \
      || pass "clio HSTS present without includeSubDomains"
else
    fail "clio HSTS missing — got '$(echo "$CLIO_HDRS" | grep -i strict || echo none)'"
fi

FORMAVA_HDRS="$(curl -sI --max-time 15 https://formava.io/ | tr -d '\r')"
for h in strict-transport-security x-content-type-options x-frame-options referrer-policy; do
    echo "$FORMAVA_HDRS" | grep -qi "^${h}:" \
      && pass "formava header ${h}" || fail "formava header ${h} missing"
done

echo
echo "== TLS =="
# Every name §6 requires must be covered by a cert. `certbot renew --dry-run`
# succeeds if *some* cert renews, so it does not prove coverage on its own.
CERTS="$($SSH 'certbot certificates' 2>/dev/null)"
for name in formava.io www.formava.io clio.lantzbuilds.com; do
    echo "$CERTS" | grep -qF "$name" \
      && pass "cert covers ${name}" || fail "cert covers ${name}"
done

# Not-expiring check, done locally against each live endpoint. This is the
# property that actually matters on a routine run -- a cert valid for weeks --
# and it costs a TLS handshake, not an ACME round trip.
for host in formava.io clio.lantzbuilds.com; do
    END="$(echo | openssl s_client -servername "$host" -connect "${host}:443" 2>/dev/null \
           | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)"
    if [ -n "$END" ] && openssl x509 -checkend 1209600 -noout \
         -in <(echo | openssl s_client -servername "$host" -connect "${host}:443" 2>/dev/null) >/dev/null 2>&1; then
        pass "cert for ${host} valid > 14 days (until ${END})"
    else
        fail "cert for ${host} expires within 14 days or is unreadable (end: ${END:-unknown})"
    fi
done

# The full renewal dry-run is the slowest check in the script (~70s: it does a
# real ACME round trip to Let's Encrypt for every cert) and it hits LE's own
# rate limits, so it should not run on every casual re-run. It is the only
# thing that proves renewal is actually WIRED -- webroot/plugin, port 80 open
# -- so keep it available behind a flag. An unbounded ACME call is also what
# turned one earlier run into a 9-minute hang, so cap it regardless.
if [ "${VERIFY_CERT_RENEWAL:-0}" = "1" ]; then
    timeout 120 $SSH 'certbot renew --dry-run' >/dev/null 2>&1 \
      && pass "cert renewal dry-run" || fail "cert renewal dry-run (or timed out)"
else
    echo "  skip  cert renewal dry-run (set VERIFY_CERT_RENEWAL=1; ~70s, hits Let's Encrypt)"
fi

echo
echo "== Memory =="
# Spec §6 sets a 1.5 GB ceiling. This used to print `free -h` for a human to
# eyeball, which meant ALL CHECKS PASSED claimed coverage the script did not
# have: a slow leak would never have failed a run.
MEM_MB="$($SSH 'free -m' | awk '/^Mem:/ {print $3}')"
if [ -n "$MEM_MB" ] && [ "$MEM_MB" -lt 1536 ] 2>/dev/null; then
    pass "host memory ${MEM_MB}M < 1536M"
else
    fail "host memory — got '${MEM_MB}M', want < 1536M"
fi

echo
echo "== Manual — NOT asserted by this script =="
# Spec §6 has three criteria that need a human and a phone. Listing them keeps
# ALL CHECKS PASSED honest about its scope.
echo "  - iOS Shortcut: new capture over HTTPS"
echo "  - iOS Shortcut: correct an existing capture by id"
echo "  - Telegram bot still responds"
echo "  - Clio CLI chat streams incrementally (SSE unbuffered)"

echo
[ "$FAIL" -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit "$FAIL"
