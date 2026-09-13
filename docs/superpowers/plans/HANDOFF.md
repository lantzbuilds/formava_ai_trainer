# Handoff — Spec 1 VPS migration, Task 10 remaining

**Written:** 2026-08-16, at the end of a long session. Read this before Task 10.

## Read these, in order

1. **This file** — what changed since the plan was written.
2. `docs/superpowers/plans/2026-07-31-vps-infra-datastore.md` — Task 10's steps.
   Authoritative for *commands*, but see "Stale" below.
3. `.superpowers/sdd/2026-07-31-vps-infra-datastore/progress.md` — the ledger,
   full decision history and deferred minors.

The plan's Task 10 is the only work left. Tasks 1–9 are complete and reviewed.

## State: everything is live and working

```
https://formava.io/api/health        {"db":"ok","pgvector":"0.6.0"}
https://www.formava.io/              301 → apex
https://clio.lantzbuilds.com/health  200
port 3000                            closed at ufw, unreachable off-host
ssh                                  key-only, passwords refused
fail2ban                             4 jails, all reading real log files
backups                              nightly timer, restore + size guard proven
```

Six services active: `clio`, `clio-cron`, `nginx`, `postgresql`, `formava-api`,
`formava-web`. Local suite: 10 passing in 0.76s.

## 🔴 Stale in the plan — fix these before running Task 10

**1. `verify.sh` uses `CLIO_TOKEN`. That variable no longer exists.**

The legacy `CAPTURE_API_TOKEN` was deleted in Task 6 Step 7c. Clio now has two
scoped tokens in `/opt/clio/.env`: `CAPTURE_TOKEN` and `SESSION_TOKEN`.

Replace `CLIO_TOKEN` with `CAPTURE_TOKEN`, read on the host rather than passed
in, so no secret enters shell history:

```bash
CAP=$(ssh root@144.202.88.7 "grep '^CAPTURE_TOKEN=' /opt/clio/.env | cut -d= -f2-")
```

**2. `/api/sessions` is PUBLISHED. It must not 404.**

The plan's earlier draft had it closed. The Clio CLI uses it. Correct assertions:

| Path | With `CAPTURE_TOKEN` | Reason |
|---|---|---|
| `POST /capture` | not 401 | capture scope |
| `POST /api/sessions` | **401** | scope isolation — the whole point of the split |
| `POST /capture/<id>/fix` | not 401 | published regex route |
| `GET /capture` | 403 | `limit_except POST` |
| `/status`, `/capture/bulk`, `/capture/fix`, `/capture/fix/recent`, `/v404/exec` | 404 | closed at nginx |

`SESSION_TOKEN` is the mirror: 200 on `/api/sessions`, 401 on `/capture`.

**3. Password SSH is gone. Anything using `sshpass` fails.**

Use `ssh -i ~/.ssh/id_ed25519`. `scripts/deploy_vps.sh:19` already uses plain
`ssh`, so it is fine. The CI deploy job in Task 10 Step 3 needs a `VPS_SSH_KEY`
repo secret, as the plan says.

**4. `ss` still shows `*:3000`. That is expected, not a bug.**

Clio binds all interfaces; `ufw` is what closes the port. Test reachability
**from off-host** — a loopback test passes while the port is wide open. Clio
finding 3 (a one-line `app.listen` change) would fix the bind, and is still open
on the Clio side.

**5. Add a `clio-cron` check.** Two Clio units exist, not one.

## Gotchas that cost real time this session

**fail2ban jails can be "active" and blind.** `defaults-debian.conf` sets
`backend = systemd`, which silently overrides `logpath`. Always verify with
`fail2ban-client get <jail> logpath` — it must name a file. Already fixed for the
three nginx jails via `backend = auto`; do not change the global default, the
`sshd` jail legitimately uses systemd and works.

**Never test bans with a routable IP.** Use `203.0.113.7` (RFC 5737). Real IPs in
play: `76.121.153.187` is the human's phone, `144.202.88.7` is the server.

**CI lint is scoped to `app/health/` on purpose.** The Gradio layer carries 107
pre-existing ruff violations and is deleted in Spec 4. Widen the path as later
specs land; do not "fix" it by unscoping.

**Verify the property, not the directive.** `sshd -T` reported
`permitrootlogin yes` while root was already key-only. What mattered was that a
password login was refused.

## Task 10, condensed

1. Write `scripts/vps/verify.sh` with the corrections above.
2. Run it; every check passes.
3. Replace the two `echo` deploy stubs in `.github/workflows/ci.yml` with the
   real VPS deploy job (plan Step 3). Add `VPS_SSH_KEY` and `VPS_HOST` secrets.
   Bump `test-frontend` to Node 20.
4. Push the branch, confirm Actions is green.

Then the whole-branch review, then `superpowers:finishing-a-development-branch`.

## Open, not blocking

- **Clio model ID `claude-sonnet-4-20250514` returns 404.** Every capture
  analysis silently falls back. Clio-side fix.
- Clio vault git sync failing: `Cannot rebase onto multiple branches`.
- Clio finding 3 (loopback bind) and finding 5 (`GET /status`) still open — see
  `../clio-ai-assitant/docs/INFRA-HANDOFF.md`.
- Deferred minors are listed in the ledger for the final review to triage.
