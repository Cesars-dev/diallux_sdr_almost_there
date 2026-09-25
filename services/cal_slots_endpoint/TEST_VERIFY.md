# TEST_VERIFY — cal_slots `timezone` arg + `include_iso` (user runs this)

This file contains the deploy + signed-verify procedure for the `check_availability` changes
(`timezone` output arg, `include_iso` per-account, V2 `time`/`timezone` booking contract).
The implementing agent only wrote files — **deploy and test are yours**.

## 1. Deploy (restart `cal-slots.service`)

```bash
cd /home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint
systemctl --user daemon-reload
systemctl --user restart cal-slots
systemctl --user status cal-slots --no-pager
```

Wait until the service reports `active (running)` and `/health` returns `{"ok":true,"service":"cal_slots"}`.

## 2. Signed caller snippet

The endpoint rejects unsigned calls with `401`. Use this exact HMAC helper
(signature `v=<ms>,d=<hex>`, `d = HMAC-SHA256(raw_body + str(ms))`, key = `RETELL_API_KEY`, 5-min window):

```bash
cd /home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint
set -a; source .env; set +a
python3 - <<'PY'
import hashlib, hmac, json, os, time, urllib.request, urllib.error

URL = "https://slots.diallux-ai.site/check_availability"
KEY = os.environ["RETELL_API_KEY"]

def signed_post(payload):
    raw = json.dumps(payload).encode()
    ts = str(int(time.time() * 1000))
    digest = hmac.new(KEY.encode(), raw + ts.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        URL, data=raw, method="POST",
        headers={"Content-Type": "application/json",
                 "X-Retell-Signature": f"v={ts},d={digest}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

# CASE 1: diallux (default), no timezone arg, include_iso=false on diallux
print("=== CASE 1: diallux default (Europe/London), expect NO iso ===")
code, body = signed_post({"slot_target_date": "2026-08-21"})
print("http", code, "ok", body.get("ok"), "error", body.get("error"))
for s in (body.get("slots") or [])[:3]:
    print("  ", s.get("day"), s.get("time"), "iso=", s.get("iso"))

# CASE 2: diallux_live with timezone=America/Chicago, include_iso unchanged (iso present)
print("=== CASE 2: diallux_live, timezone=America/Chicago, expect iso present ===")
code, body = signed_post({"slot_target_date": "2026-08-21", "account_id": "diallux_live", "timezone": "America/Chicago"})
print("http", code, "ok", body.get("ok"), "error", body.get("error"))
for s in (body.get("slots") or [])[:3]:
    print("  ", s.get("day"), s.get("time"), "iso=", s.get("iso"))
PY
```

## 3. Expected results

- **CASE 1** (`diallux`, default `Europe/London`): each slot has `day` + `time` (bare local, no `Z`/ms) and **NO `iso`** key (because `diallux` sets `include_iso:false`). A 2pm BST slot shows `time = "...T14:00:00"`.
- **CASE 2** (`diallux_live`, `timezone: "America/Chicago"`): each slot's `time` is in Chicago local time **AND** `iso` is present (because `diallux_live` leaves `include_iso` unset → default true). The same instant appears shifted relative to CASE 1 by the zone difference.

## 4. Failure signals

- `http 401` → signature/key/clock mismatch. Re-check `RETELL_API_KEY` in `.env` and that the host clock is within 5 minutes of the signature `ms`.
- `error: invalid_timezone` → the `timezone` value is not a valid IANA name.
- Slots still contain `iso` for CASE 1 → `include_iso:false` not picked up; confirm `.env` `CAL_ACCOUNTS` is valid JSON and `diallux` has `"include_iso": false`.

## 5. After passing

Run the heating_uk happy path per `agents/heating_uk/performance_tests/TEST_HAPPY_PATH_TODAY.md`
to confirm the full booking chain books at the correct UTC instant (no 1h shift).
