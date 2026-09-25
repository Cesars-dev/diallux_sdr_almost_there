# RUNBOOK — Retell Proxy Guard incidents

Setup context and architecture: see `README.md` in this folder.
Log: `logs/guard.log` · Liveness: `stat logs/last_run`.

---

## Scenario A — `V4-DRIFT` line in guard.log (IPv4 changed, no Telegram)

Retell's A records no longer match `13.248.202.14 3.33.169.178`.
Non-slice processes are still masked (catch-all rule) — only opencode.slice
calls to the NEW IP would leak. The pinned `/32` rules need updating.

1. **Verify it's real** (not resolver garbage):
   ```bash
   dig +short api.retellai.com A @1.1.1.1
   dig +short api.retellai.com A @8.8.8.8
   dig +short api.retellai.com A @9.9.9.9
   ```
   All three must agree. Sanity-check the new IP is plausible
   (AWS: `whois <ip> | grep -i org`).

2. **Update the iptables rules** (any opencode session can run these — sudo is
   pre-authorized for `/usr/sbin/iptables`):
   ```bash
   sudo -n /usr/sbin/iptables -t nat -D REDSOCKS -d 3.33.169.178/32 -p tcp -j REDIRECT --to-ports 12345
   sudo -n /usr/sbin/iptables -t nat -D REDSOCKS -d 13.248.202.14/32  -p tcp -j REDIRECT --to-ports 12345
   sudo -n /usr/sbin/iptables -t nat -I REDSOCKS 1 -d <NEW_IP_1>/32 -p tcp -j REDIRECT --to-ports 12345
   sudo -n /usr/sbin/iptables -t nat -I REDSOCKS 1 -d <NEW_IP_2>/32 -p tcp -j REDIRECT --to-ports 12345
   sudo -n /usr/sbin/netfilter-persistent save
   ```

3. **Update the guard's known-good state** — edit `KNOWN_V4` at the top of
   `retell_guard.sh`.

4. **Verify** (from an opencode session — this is the path that used to leak):
   ```bash
   python3 -c "import urllib.request;print(urllib.request.urlopen('https://api.retellai.com/',timeout=10).status)"
   ss -tn | grep 12345    # must show a mirrored connection = proxied
   ```

---

## Scenario B — Telegram: "IPv6 CHANGED"  🔴 the important one

Retell added/changed AAAA records. IPv6 traffic is NOT redirected by redsocks
(ip6tables has no REDSOCKS chain), so clients preferring IPv6 would exit via
the **direct VPS IP** and leak it. Act on the Telegram contents:

1. **Immediate containment** (run as root on the VPS — one paste). Refuse IPv6
   to Retell so clients fall back to IPv4 → masked again:
   ```bash
   sudo ip6tables -I OUTPUT -p tcp -d <NEW_IPV6_FROM_TELEGRAM>/64 -j REJECT
   ```
   Repeat per distinct IPv6 prefix in the Telegram message. `/64` covers the
   whole announced block. REJECT (not DROP) = instant fallback, no timeouts.

2. **Verify fallback + masking**:
   ```bash
   python3 - <<'PY'
   import socket
   print(socket.getaddrinfo("api.retellai.com", 443, proto=socket.IPPROTO_TCP))
   PY
   ss -tn | grep 12345   # while making a call: mirrored conn = proxied ✓
   ```

3. **Decide the new normal**:
   - Retell keeps IPv6 → set `KNOWN_V6` in `retell_guard.sh` to the new set
     (further changes will alert again), keep the REJECT rules.
   - Retell drops IPv6 → remove REJECT rules once AAAA is gone
     (`sudo ip6tables -D OUTPUT ...`), leave `KNOWN_V6` empty.

4. Note: opencode cannot run `sudo ip6tables` itself (permission config) —
   the paste must be run by you. That's why this scenario is a Telegram push.

---

## Scenario C — `CHECK-FAILED` line in guard.log

Both public resolvers were unreachable (UDP 53 egress problem?). Not an alert.
Check manually: `dig +short api.retellai.com @1.1.1.1`. If persistent, check
DNS egress/firewall. The guard retries hourly by itself.

## Scenario D — Telegram: "IPv6 RESOLVED"

AAAA records returned to the expected (empty) state. Optional cleanup: remove
any REJECT rules added in Scenario B. No other action.

---

## Scenario E — Retell API calls failing / timing out (suspect this setup)

The pin rules force Retell through redsocks → socks5 `216.185.35.17:45295`.
If that proxy is down or slow, Retell calls break or hang.

1. **Restore service first** (this is the documented rollback):
   ```bash
   cd /home/julio/projects/Retell_AI_MCP_connection/proxy_guard
   ./revert.sh iptables
   ```
   Then confirm: `python3 -c "import urllib.request;print(urllib.request.urlopen('https://api.retellai.com/',timeout=10).status)"`
2. **Diagnose what actually broke**:
   ```bash
   systemctl status redsocks                    # redirector alive?
   ss -tn | grep 216.185.35.17                  # upstream reachable?
   curl -x socks5h://127.0.0.1:12345 -s https://api.retellai.com/ -o /dev/null -w '%{http_code}\n'
   ```
3. **Was it really us?** Check the pinned rules match live DNS
   (`dig +short api.retellai.com A @1.1.1.1` vs README chain) — if Retell moved
   IPs, this is Scenario A, not a proxy outage.
4. **Re-enable masking** once root-caused: re-run the Scenario A step 2 commands.

---

## Full revert (when in doubt, back out)

```bash
cd /home/julio/projects/Retell_AI_MCP_connection/proxy_guard
./revert.sh check       # dry-run: shows rules + cron
./revert.sh iptables    # un-pin Retell IPs (catch-all still proxies non-slice traffic)
./revert.sh all         # also remove the hourly cron watcher
```

Effect of `iptables`/`all`: returns to the state before 2026-09-03 —
opencode.slice Retell calls go DIRECT (leak), everything else stays proxied.
