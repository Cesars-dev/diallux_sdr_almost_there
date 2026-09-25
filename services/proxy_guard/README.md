# Retell Proxy Guard

Keeps Retell AI API traffic masked behind the redsocks VPS proxy (`216.185.35.17`)
and watches for anything that could break that masking.

## 🚨 BREAK-GLASS — Retell API calls are broken, fix now, read later

```bash
cd /home/julio/projects/Retell_AI_MCP_connection/proxy_guard
./revert.sh iptables   # removes both Retell pin rules + persists — calls go direct again
```

That returns the VPS to its exact pre-2026-09-03 state: Retell calls work like
they did before this setup (opencode.slice direct, everything else still proxied
by the pre-existing catch-all). Then diagnose at leisure (RUNBOOK.md scenario E).
`./revert.sh all` additionally removes the hourly watcher cron.

Installed: 2026-09-03 · Host: this VPS (`46.62.233.228` direct, `216.185.35.17` proxied)

## How the blocking works (already live, kernel-level)

All outbound TCP from user `julio` (UID 1002) hits the `REDSOCKS` iptables chain
(`iptables -t nat -A OUTPUT -p tcp -m owner --uid-owner 1002 -j REDSOCKS`).
Retell's two IPv4 endpoints are redirected to redsocks BEFORE the opencode.slice
exemption, so **every process** — including opencode sessions and scripts they
launch — exits via the proxy for Retell:

```
iptables -t nat -S REDSOCKS   (order matters)

-A REDSOCKS -d 3.33.169.178/32 -p tcp -j REDIRECT --to-ports 12345   ← Retell IP 1
-A REDSOCKS -d 13.248.202.14/32 -p tcp -j REDIRECT --to-ports 12345  ← Retell IP 2
-A REDSOCKS -m cgroup --path "/user.slice/user-1002.slice/user@1002.service/opencode.slice" -j RETURN
-A REDSOCKS -d 127.0.0.0/8   -j RETURN
-A REDSOCKS -d 10.0.0.0/8    -j RETURN
-A REDSOCKS -d 172.16.0.0/12 -j RETURN
-A REDSOCKS -d 192.168.0.0/16 -j RETURN
-A REDSOCKS -d 216.185.35.17/32 -j RETURN                             ← proxy itself
-A REDSOCKS -p tcp -j REDIRECT --to-ports 12345                       ← catch-all
```

Path: `app → 13.248.202.14/3.33.169.178:443 → (REDIRECT) → 127.0.0.1:12345 (redsocks)
→ socks5 216.185.35.17:45295 → Retell`. Verified 2026-09-03: 8/8 live calls
returned HTTP 200 through the proxy chain.

- `api.retellai.com` is **IPv4-only** (AWS Global Accelerator, static IPs, DNS TTL 300s).
- Non-slice processes are covered by the catch-all rule for ANY IPv4, known or not.
- The only theoretical leak: opencode.slice traffic to a Retell IP that is not one
  of the two above (i.e. Retell re-platforms), or Retell adding IPv6 (ip6tables has
  no redirect — v6 always goes direct).

## What this folder adds: the watcher (retell_guard.sh)

Hourly cron (as `julio`, no root): resolves `api.retellai.com` A + AAAA records
via `1.1.1.1` and `8.8.8.8` (public resolvers, cached answers — **zero traffic to
Retell**, no footprint) and compares against the known-good state at the top of
the script.

| Event | Action |
|---|---|
| No change | silent (touches `logs/last_run` so liveness is checkable) |
| IPv4 drift (new/missing A record) | one line in `logs/guard.log` — **no message** |
| **IPv6 change (AAAA appears/changes/disappears)** | **one Telegram message** + log line |
| Resolvers unreachable | log line only, retried next hour |

Telegram messages are deduped: one message per new state, retried hourly if the
send fails, and a "RESOLVED" message if it returns to normal. Credentials are read
from `/home/julio/projects/Voicemail_drops/.env` (`TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`) — never copied into this git repo.

## Files

| File | Purpose |
|---|---|
| `retell_guard.sh` | hourly watcher (`--selftest` sends a labeled TEST message) |
| `revert.sh` | one-command revert: `check` / `iptables` / `all` |
| `RUNBOOK.md` | what to do when a V4-DRIFT log line or IPv6 Telegram fires |
| `logs/guard.log` | change/failure events only (no hourly noise) |
| `logs/last_run` | mtime = last successful check (`stat logs/last_run`) |
| `logs/last_alerted_v6` | last IPv6 state we Telegram'd about (dedupe) |

## Cron (added, nothing existing was modified)

```
0 * * * * /home/julio/projects/Retell_AI_MCP_connection/proxy_guard/retell_guard.sh >> /home/julio/projects/Retell_AI_MCP_connection/proxy_guard/logs/cron.log 2>&1
```

## Liveness check

```bash
stat -c '%y' /home/julio/projects/Retell_AI_MCP_connection/proxy_guard/logs/last_run
tail /home/julio/projects/Retell_AI_MCP_connection/proxy_guard/logs/guard.log
```

`last_run` older than ~2h = guard not running (check `crontab -l`, `logs/cron.log`).

## Revert

```bash
./revert.sh           # see current state
./revert.sh iptables  # remove the two Retell REDIRECT rules + persist  (restores pre-fix behavior)
./revert.sh all       # also remove the hourly cron entry
```

Full manual revert (if scripts are unavailable): delete the two `-A REDSOCKS -d 13.248.202.14/3.33.169.178 …
-j REDIRECT --to-ports 12345` lines from `/etc/iptables/rules.v4`, run
`sudo netfilter-persistent reload`, and remove the `retell_guard.sh` crontab line.
Reverting the iptables part re-opens the opencode.slice Retell leak this setup closed.
