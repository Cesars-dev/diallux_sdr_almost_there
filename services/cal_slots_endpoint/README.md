# Cal.com Slot Webhook — README

> A FastAPI webhook that queries Cal.com `/v2/slots` and returns **discrete future slots** (`{day, time, iso}`) to a Retell AI agent via a custom function tool.
> Replaces Retell's native `check_availability_cal` (which returns collapsed **range windows**) with exact slot times.
> Deployed on the Hetzner VPS at `https://slots.diallux-ai.site/check_availability`.

---

## 1. What it does

```
Retell LLM ── POST /check_availability ──► webhook (FastAPI)
              { account_id, slot_target_date }
                        │
                        ▼
              resolve(account_id) → lookup in CAL_ACCOUNTS (.env)
                        │   (gets cal_api_key, event_type_id, duration)
                        ▼
              GET api.cal.com/v2/slots?eventTypeId=..&start=..&end=..&duration=..
                        │
                        ▼
              parse → filter past → discrete slots
                        │
              ◄──── {ok, slots:[{day,time,iso}]} ────
```

---

## 2. How the account mapping works (single vs multi)

The webhook supports **multiple calendar accounts** behind **one URL**. Each account is an entry in the `CAL_ACCOUNTS` env variable. The LLM tells the webhook *which* account to use by passing a **label** (`account_id`); the webhook maps that label to the real API key + event + duration server-side.

- **One account:** no `account_id` needed. The webhook defaults to the first (or only) entry in `CAL_ACCOUNTS`.
- **Multiple accounts:** the LLM passes `account_id` (e.g. `"diallux_live"`) and the webhook picks the matching entry.

---

## 3. WHERE to configure each account (the only place)

**File: `cal_slots_endpoint/.env`** → the `CAL_ACCOUNTS` JSON.

```json
CAL_ACCOUNTS={
  "diallux":       {"cal_api_key":"cal_live_a9704f08...", "event_type_id":6522694, "timezone":"Europe/London", "duration":60},
  "diallux_live":  {"cal_api_key":"cal_live_e2d8752e...", "event_type_id":3801235, "timezone":"America/Mexico_City", "duration":45}
}
```

| Key | Meaning | Example |
|-----|---------|---------|
| map key / label | the `account_id` you send from Retell | `"diallux_live"` |
| `cal_api_key` | the account's Cal.com API key (secret) | `cal_live_...` |
| `event_type_id` | the Cal.com event number | `3801235` |
| `timezone` | fallback booking/render timezone | `America/Mexico_City` |
| `duration` | slot length in minutes | `45` |

> The API keys and event IDs live **only** here — never in a Retell prompt.

The webhook's `config.py` reads this and `main.py` calls `resolve(args.get("account_id"))` to pick the right entry.

---

## 4. Wiring a new account — the 2 steps

To add "Diallux" as an account the webhook understands:

**Step 1 — server side (`cal_slots_endpoint/.env`):** add one entry to `CAL_ACCOUNTS` with the api key, event ID, timezone, and duration for that account. Then restart the service:

```bash
systemctl --user restart cal-slots.service
```

**Step 2 — Retell side (custom tool config):** in the Retell LLM's **custom function** for this webhook, set the `account_id` parameter's **default** to that label (e.g. `"diallux_live"`). This is deterministic — the model passes it verbatim and cannot choose a different account.

```json
{
  "type": "custom",
  "name": "check_availability",
  "url": "https://slots.diallux-ai.site/check_availability",
  "method": "POST",
  "parameters": {
    "type": "object",
    "properties": {
      "account_id": {
        "type": "string",
        "description": "Which calendar account to use. Fixed per agent — do not change.",
        "default": "diallux_live"
      },
      "slot_target_date": {
        "type": "string",
        "description": "ISO date (YYYY-MM-DD) of the day the caller wants a slot for."
      }
    }
  }
}
```

After editing the tool schema, **rebuild the LLM** (Retell caches; never patch) and point the agent at the new LLM ID.

---

## 5. Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /check_availability` | Slot query (Retell custom function). Body: `{account_id?, slot_target_date}` |
| `GET /health` | Liveness probe |
| `GET /ready` | Config-present readiness check |
| `GET /metrics` | In-process counters |

---

## 6. Response format

**Success:**
```json
{"ok": true, "slots": [
  {"day": "2026-08-01", "time": "2026-08-01T10:00:00", "iso": "2026-08-01T09:00:00.000Z"}
]}
```

- `time` = local value (no `Z`, no ms) — pass this to `book_calendar`.
- `iso` = UTC reference (display only, not for booking).

**Errors** (always read the body — a 200 does not mean success):
```json
{"ok": false, "error": "CODE", "message": "human instruction"}
```

| error | Meaning / what to do |
|-------|----------------------|
| `unauthorized` | bad/missing `X-Retell-Signature` (HTTP 401) |
| `no_start_time` | missing `slot_target_date` — ask for the day, pass YYYY-MM-DD |
| `invalid_slot_target_date` | malformed date — re-extract |
| `no_availability_in_window` | no free slots — offer the next available day |
| `upstream_unavailable` | Cal.com down — say you'll retry |
| `rate_limited` | too many requests (HTTP 429) |
| `unknown_account` | `account_id` not in `CAL_ACCOUNTS` |

---

## 7. Signature verification

Retell signs requests with `X-Retell-Signature: v=<ms-timestamp>,d=<hmac>`. The webhook verifies HMAC-SHA256 of `raw_body + timestamp` keyed with the webhook-badge API key (`RETELL_API_KEY` in `.env`). Requests without a valid signature → HTTP 401. See `FINDINGS.md` Finding #1.

---

## 8. Deployment / config files

| Item | Value |
|------|-------|
| Host | Hetzner VPS `MainVps`, user `2nd_workspace`, IP `46.62.233.228` |
| Public URL | `https://slots.diallux-ai.site/check_availability` |
| Proxy | Caddy → `localhost:8001` |
| Service | systemd user `cal-slots.service` |
| Source | `cal_slots_endpoint/` |
| Config | `.env` (`CAL_ACCOUNTS`, `RETELL_API_KEY`, etc.) |

Restart / logs:
```bash
systemctl --user restart cal-slots.service
systemctl --user status cal-slots.service
journalctl --user -u cal-slots.service -f
```

See `ARCHITECTURE.md` and `FINDINGS.md` for the full design and verified Cal.com param mapping.

## 9. Adding a new account — follow the SOP

For the exact, step-by-step procedure (edit `CAL_ACCOUNTS` → validate → restart → write the Retell custom-function schema → POST a new LLM → verify), see **`SOP_ADD_ACCOUNT.md`**.

---

## 10. Time service (related but separate)

Time/date concerns (Retell's `{{current_time_...}}` parsing, standardized formats) live in the **agent-agnostic `time_endpoint/`** service, exposed on the same domain under the `/time-function` prefix:

- `POST https://slots.diallux-ai.site/time-function/parse-time` — parse Retell time strings into standardized formats (signed)
- `GET https://slots.diallux-ai.site/time-function/today` — today's date in a requested IANA timezone (no signature)

### How they work together

The time service supplies the `slot_target_date` this endpoint needs:

```
Retell {{current_calendar}} (14-day listing, 1st line = "Today")
        ▼
time service  /time-function/parse-time  →  today (YYYY-MM-DD)
        ▼
this endpoint  /check_availability  { slot_target_date: today }  →  slots
```

- Retell's `{{current_calendar}}` first line marks the agent's current day ("… (Today)") and embeds the timezone; the time service turns it into a clean `YYYY-MM-DD`.
- `bridge.py` (project root) exercises the full chain live.

The `/today` endpoint of **this** service remains for backward compatibility; new integrations should use the time service. See `../time_endpoint/README.md` and `../SERVICES_OVERVIEW.md`.
