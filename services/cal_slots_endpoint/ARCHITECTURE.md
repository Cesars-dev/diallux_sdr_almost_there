# Cal.com Slot Checker — Custom Function (Webhook)

> **Purpose:** Replace Retell's native `check_availability_cal` tool with a custom function that queries Cal.com directly and returns **discrete future slots** (`{day, time, iso}`) instead of raw time windows. Fixes F-1/F-2/F-3 (hallucinated times, re-offered rejected slots).
>
> **Status:** DONE — deployed as a FastAPI service on the Hetzner VPS.

---

## Architecture

```
LLM decides to call check_availability
        │
        ▼
Retell custom function ──HTTP POST──► https://slots.diallux-ai.site/check_availability
        │                                 (FastAPI, Caddy reverse proxy, HTTPS)
        │                                       │
        │                                       ▼
        │                            Cal.com GET /v2/slots
        │                            (cal-api-version: 2024-09-04)
        │                                       │
        │                                       ▼
        │                            Parse → filter past → discrete slots
        │                                       │
        ◄─────────── JSON {ok, slots:[{day,time,iso}]} ──────────┘
        │
        ▼
LLM offers 1–2 closest slots ("Thursday at 2 PM")
```

---

## Deployment / Location

| Item | Value |
|------|-------|
| **Host** | Hetzner VPS `MainVps` — user `2nd_workspace`, IP `46.62.233.228` |
| **Public URL** | `https://slots.diallux-ai.site/check_availability` |
| **DNS** | A record `slots` → `46.62.233.228` (Bluehost, `diallux-ai.site`) |
| **Reverse proxy** | Caddy — `slots.diallux-ai.site { reverse_proxy localhost:8001 }` |
| **App port** | `127.0.0.1:8001` (localhost only; Caddy fronts it) |
| **Service manager** | systemd user service `cal-slots.service` (`Restart=always`) |
| **Source dir** | `/home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/` |
| **Config** | `.env` in source dir (`EnvironmentFile`) |
| **Runtime** | Python 3.12 venv `.venv`, FastAPI + uvicorn |

### Files

```
cal_slots_endpoint/
├── main.py            # FastAPI app (health + check_availability)
├── requirements.txt   # fastapi, uvicorn, requests, python-dotenv
├── .env               # config (NOT in git) — see .env.example
├── .env.example       # config template
├── .gitignore
└── cal-slots.service  # systemd user unit (installed to ~/.config/systemd/user/)
```

---

## Config (.env)

| Variable | Value | Notes |
|----------|-------|-------|
| `RETELL_API_KEY` | `${RETELL_KEY_3}` | Webhook-badge key — used to verify `X-Retell-Signature` (HMAC). Must match the key Retell sends with the custom function. |
| `CAL_COM_API_KEY` | `cal_live_a9704f08...` | Akrit's production Cal.com key |
| `EVENT_TYPE_ID` | `6522694` | Diallux Booking Demo (60 min, Address location) |
| `TIMEZONE` | `Europe/London` | Booking timezone |
| `CAL_API_VERSION` | `2024-09-04` | Header for `/v2/slots` |
| `SLOT_DURATION_MIN` | `60` | Slot duration |
| `LOOKAHEAD_DAYS` | `7` | Slots window (days from query date) |
| `MAX_SLOTS` | `20` | Max slots returned to LLM |

---

## Endpoint

### `GET /health`

Liveness probe. Returns `{"ok": true, "service": "cal_slots"}`.

### `POST /check_availability`

**Auth:** Must include `X-Retell-Signature` header — HMAC-SHA256 of the raw request body using the Retell API key. Returns 401 if invalid.

**Request body** (Retell custom function envelope):
```json
{
  "name": "check_availability",
  "args": {}
}
```
`args` may optionally contain `slot_target_date` (YYYY-MM-DD) to query a specific day; otherwise the
window starts from today. Optional `timezone` (IANA) requests `day`/`time` in that zone (default =
account timezone); optional `account_id` selects a `CAL_ACCOUNTS` entry (default = first).

**Behavior:**
1. Verify signature (raw body, not re-serialized).
2. Resolve account + optional output `timezone` (validated IANA → `invalid_timezone` 400).
3. Compute window: `start` = query date 00:00 UTC, `end` = `start` + `LOOKAHEAD_DAYS` − 1s.
4. `GET https://api.cal.com/v2/slots` with `eventTypeId`, `start`, `end`, `duration` and headers `Authorization: Bearer <cal key>`, `cal-api-version: 2024-09-04`.
5. Filter out slots already in the past (vs. current time).
6. Convert each slot to the output `timezone`; emit `iso` only if the account has `include_iso` unset/true.
7. Sort by UTC instant ascending, cap at `MAX_SLOTS`.

**Response:**
```json
{
  "ok": true,
  "slots": [
    { "day": "2026-08-01", "time": "2026-08-01T10:00:00", "iso": "2026-08-01T09:00:00.000Z" },
    { "day": "2026-08-01", "time": "2026-08-01T11:00:00", "iso": "2026-08-01T10:00:00.000Z" }
  ]
}
```
`time` is the local datetime in the **requested** `timezone` — bare `YYYY-MM-DDTHH:MM:SS`, no `Z`, no ms
(this is the value passed to `book_calendar`, which must be paired with the SAME `timezone`).
`iso` is the UTC reference with `Z` + ms, present only for accounts without `include_iso:false`.

On failure returns `{"ok": false, "error": "..."}`.

---

## How to start / stop / status

```bash
# (all run as user 2nd_workspace)
systemctl --user daemon-reload
systemctl --user start cal-slots.service
systemctl --user status cal-slots.service
systemctl --user restart cal-slots.service
journalctl --user -u cal-slots.service -f
```

---

## Retell integration

The `check_availability` tool in the V3.1 LLM must point at the custom function URL instead of the native `check_availability_cal` type. Keep the tool **name** `check_availability` so the prompts don't change.

---

## Verified Cal.com param mapping (booking, for `book_calendar`)

Tested live 2026-08-01 against event `6522694`:

| Payload field | Cal.com location | Required | Notes |
|---------------|------------------|----------|-------|
| `eventTypeId` | top-level | ✅ | `6522694` |
| `start` | top-level | ✅ | ISO 8601 UTC with `Z` |
| `name` | `attendee.name` | ✅ | |
| `email` | `attendee.email` | ✅ | `jaydiallux@gmail.com` |
| `timeZone` | `attendee.timeZone` | ✅ | `Europe/London` |
| `attendeePhoneNumber` | `attendee.phoneNumber` | ⬜ | E.164 (from `{{user_number}}`) |
| `location` | top-level string | ⬜ | Address string; sets `meetingUrl` for `somewhereElse` events |
| `title` | `bookingFieldsResponses.title` | ⬜ | **NOT** top-level (400 if top-level) |
| `notes` | `bookingFieldsResponses.notes` | ⬜ | **NOT** top-level (400 if top-level) |

**Booking API version:** `cal-api-version: 2026-05-01` (NOT `2024-09-04`).
**Cancel API version:** `cal-api-version: 2026-02-25`.
