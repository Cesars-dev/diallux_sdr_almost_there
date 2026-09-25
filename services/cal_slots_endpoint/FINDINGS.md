# webhooks/slots — Custom Function Findings

> Date: 2026-08-01
> Session: Webhook Test Plan validation of the Cal.com slot checker + Retell booking integration.

This README captures the live findings from the webhook validation spike. It is the source of truth for the production (V3.1) integration.

---

## What This Service Is

`webhooks/slots/main.py` is a FastAPI endpoint that queries Cal.com for available slots and returns discrete `{day, time, iso}` slots to a Retell voice/chat agent via a **custom function**.

| Item | Value |
|------|-------|
| Source | `main.py` |
| Endpoint (public) | `https://slots.diallux-ai.site/check_availability` |
| Health | `https://slots.diallux-ai.site/health` |
| DNS | `slots` A → `46.62.233.228` (note: DNS also advertises IPv6 — use `-4` when curling) |
| Service | systemd user `cal-slots.service`, port `8001` |
| Event type | `6522694` (Diallux Booking Demo, 60 min, Address) |
| Cal API key | `${CAL_KEY_3}` (Akrit's) |
| Slots API version | `2024-09-04` |
| Booking API version | `2026-05-01` (NOT `2024-09-04`) |
| Cancel API version | `2026-02-25` |

`.env` keys: `RETELL_API_KEY`, `CAL_COM_API_KEY`, `EVENT_TYPE_ID`, `TIMEZONE`, `CAL_API_VERSION`, `CAL_COM_BASE`, `SLOT_DURATION_MIN`, `LOOKAHEAD_DAYS`, `MAX_SLOTS`, `RATE_LIMIT_PER_MIN`.

---

## CRITICAL FINDING #1 — Retell signature format is versioned

Retell custom-function requests send `X-Retell-Signature` in a **versioned format**, NOT a plain hex digest:

```
X-Retell-Signature: v=1785571461049,d=8f12b317669b5629b0df83d17ab9f8813b34badf6789fe33403f128b268959b0
```

- `v` = Unix timestamp in **milliseconds** when the request was sent.
- `d` = HMAC-SHA256 hex digest of **`raw_body + timestamp`** (string concatenation), keyed with the webhook API key.

Verification rules:
1. Parse `v=(\d+),d=(.*)`.
2. Check timestamp is within **5 minutes** of now (replay protection).
3. Compute `HMAC-SHA256(raw_body + str(v), webhook_key)`.
4. Constant-time compare with `d`.

> Must verify against the **raw request body** (not re-serialized JSON — re-serializing changes whitespace/key order and breaks the signature).

`main.py` now handles both the versioned format and the legacy plain-hex format (backward compatible).

### The webhook key is NOT the normal API key

Retell signs with its designated **webhook API key** (the key shown with a webhook badge in **Retell → Settings → API Keys**). Only that key verifies the signature. It cannot be fetched via the public API.

⚠️ **RESOLVED:** `SKIP_SIGNATURE` has been removed from the codebase and `.env`. Signature verification is now mandatory with no bypass. The webhook-badge key `${RETELL_KEY_3}` is configured as `RETELL_API_KEY`.

---

## CRITICAL FINDING #2 — Native `book_appointment_cal` wants `time` (local), NOT `start`

This is the root cause of the booking failures during the test. Diffed against a real successful production call (`call_f4a3894eadf5b74f1da0b0ef288`):

**Correct native payload (SUCCESS):**
```json
{
  "time": "2026-07-31T09:00:00",      // bare local Europe/London string — NO "Z", NO milliseconds
  "timezone": "Europe/London",        // zone carried here, not in the time string
  "name": "Maritza",
  "email": "jaydiallux@gmail.com",
  "attendeePhoneNumber": "+447759084491",
  "title": "Heating — Maritza",
  "notes": "...",
  "execution_message": "Right, let me get that booked for you."
}
```

**Incorrect payload that FAILED (400 "too soon"):**
```json
{
  "time": "2026-08-01T11:00:00.000Z",  // had "Z" + milliseconds — WRONG
  "start": "2026-08-01T11:00:00.000Z", // native tool does NOT use "start"
  "timeZone": "Europe/London",
  ...
}
```

**Rules:**
- Pass the slot as **`time`** = a bare **Europe/London local** datetime string, `%Y-%m-%dT%H:%M:%S`, **no `Z`, no milliseconds**.
- Pass **`timezone`** = `"Europe/London"`.
- **Do NOT** send a `start` field. **Do NOT** send `timeZone` (camelCase) as a booking arg.
- The local `time` is UTC + 1 hour in BST (e.g. slot `08:00Z` → `time: "09:00:00"`).

### Fix applied to this service

`check_availability` now returns `time` in **Europe/London local** format (no `Z`, no ms), while keeping `iso` as the UTC timestamp for reference:

```json
{"ok": true, "slots": [
  {"day": "2026-08-01", "time": "2026-08-01T12:00:00", "iso": "2026-08-01T11:00:00.000Z"}
]}
```

The prompt tells the agent to pass the slot's `time` field straight through to `book_calendar` as `time` + `timezone`.

---

## CRITICAL FINDING #3 — Give the agent current time

The agent has **no notion of the current time** unless you inject it. Retell auto-provides system variables (no config needed):

- `{{current_time_Europe/London}}` → e.g. "Saturday, August 1, 2026 at 9:16 AM BST"
- `{{current_calendar_Europe/London}}` → 14-day calendar
- `{{current_hour_Europe/London}}` → fractional hour

Add these to the booking state prompt so the agent can judge future slots and describe dates ("today"/"tomorrow") accurately.

---

## CRITICAL FINDING #5 — Vague-date handling requires a tool parameter

The agent does **not** "natively understand" vague dates ("next Monday", "this afternoon", "tomorrow"). It can only act on the date if the tool **exposes a date parameter** and the prompt **instructs extraction**. Proven live:

**Before the fix:** `check_availability` was declared with `parameters.properties: {}` (empty schema). The LLM always called it with `{}` because there was no argument to fill — every request returned the same window, and vague dates were ignored.

**The fix (both parts required):**
1. **Tool schema** — expose a `slot_target_date` property:
   ```json
   "parameters": {
     "type": "object",
     "properties": {
       "slot_target_date": {
         "type": "string",
         "description": "ISO date (YYYY-MM-DD) of the day the caller wants a slot for. If the caller says 'next Monday'/'tomorrow'/'this week', convert to the actual date before passing."
       }
     }
   }
   ```
2. **Prompt** — instruct the agent to convert the caller's phrasing into a concrete date:
   - "next Monday" → the coming Monday
   - "tomorrow" → day after today
   - "this afternoon" / "this week" → today or nearest day with slots
   - "as soon as possible" → omit `slot_target_date`

**Result (verified live, agent chose the slot itself):**
| Caller asked | `slot_target_date` sent | Booked | Correct |
|---|---|---|---|
| "next Monday" | `2026-08-03` (Mon) | Mon 09:00 | ✅ |
| "this afternoon" | `2026-08-01` (today) | today 12:00 | ✅ |
| "tomorrow morning" | `2026-08-02` (Sun, no slots) | next day Mon 10:00 | ✅ fallback |
| "as soon as possible" | `null` | **Mon 11:00 — WRONG** | ❌ (should be today 12:00) |

> `main.py` accepts `slot_target_date` and defaults to today when omitted. The agent needs the schema param + prompt instruction to actually use it. **Date extraction works; "soonest selection" does not — see Finding #7.**

---

## CRITICAL FINDING #7 — "ASAP" selection bug (prompt issue, NOT the function)

When the caller says "as soon as possible", the agent correctly omits `slot_target_date` (sends `null`), and the function correctly returns the **earliest** slot first (today 12:00 London on the test day). **But the agent then picks a later slot (Monday) instead of the earliest returned slot.**

**This is a prompt issue, not a function issue.** The function returns the soonest slot first; the agent's prompt told it "asap → omit slot_target_date" but **never told it to then choose the earliest slot from the response.**

**Missing prompt rules:**
1. When `slot_target_date` is omitted (ASAP), **book the first / earliest slot in the returned list.**
2. Generally, **offer the earliest available slot first** unless the caller specified a day.

**Status at close-out:** date extraction (Finding #5) is fixed and verified; the ASAP/soonest-selection rule (this finding) is **identified but NOT yet fixed/prompted**. Must be added to the V3.1 booking prompt before production.

---

## CRITICAL FINDING #6 — Lookahead window

`LOOKAHEAD_DAYS` in `.env` caps how far ahead the function returns slots. With `2`, "next Monday"/"this week" returned empty because the window ended before real availability (weekend). Widened to **7**. Tune per scheduling needs.

---

## CRITICAL FINDING #4 — Cal.com booking param structure (verified live)

| Payload field | Cal.com location | Required | Notes |
|---------------|------------------|----------|-------|
| `eventTypeId` | top-level | ✅ | `6522694` |
| `start` | top-level | ✅ | ISO 8601 UTC with `Z` |
| `name` | `attendee.name` | ✅ | |
| `email` | `attendee.email` | ✅ | `jaydiallux@gmail.com` |
| `timeZone` | `attendee.timeZone` | ✅ | `Europe/London` |
| `attendeePhoneNumber` | `attendee.phoneNumber` | ⬜ | E.164 |
| `location` | top-level string | ⬜ | Address string; sets `meetingUrl` for `somewhereElse` events |
| `title` | `bookingFieldsResponses.title` | ⬜ | **NOT** top-level (400 if top-level) |
| `notes` | `bookingFieldsResponses.notes` | ⬜ | **NOT** top-level (400 if top-level) |

---

## Caddy routing — two approaches

Route `slots.diallux-ai.site` → `localhost:8001`:

- **NOW (test):** Caddy admin API on `127.0.0.1:2019` (no root, in-memory). The route must be added to **`srv1` (port :443)** where the public hostnames live — NOT `srv0` (:3456). The `routes/-` append syntax is unsupported; use a merged-array `PATCH` on `/config/apps/http/servers/srv1/routes`. **In-memory only — vanishes on Caddy reload/restart.**
- **FUTURE (production):** persistent block in `/etc/caddy/Caddyfile` (root-owned) + `systemctl reload caddy`. Deferred — requires root/sudo.

```
slots.diallux-ai.site {
	reverse_proxy localhost:8001
}
```

---

## Validation results (spike, 2026-08-01)

### Booking path — PASSED (the core goal)
- Custom `check_availability` returned discrete slots through Retell ✅
- Native `book_calendar` booked event `6522694` with correct location/attendee ✅
  - `booking_id 23236205`, `start=2026-08-01T11:00:00Z`, `meetingUrl` = address, attendee John Smith — cancelled after test.
- **Native payload format confirmed against a real production booking** (`call_f4a3894eadf5b74f1da0b0ef288`): native tool wants `time` = bare Europe/London local string (no `Z`, no ms) + `timezone`; NOT `start`, NOT `timeZone`. Enforced correctly across multiple runs.

### Date-handling stress tests (agent chose the slot, not the test script)
| Scenario | Result |
|---|---|
| "next Monday" | ✅ extracted `slot_target_date=2026-08-03`, booked Mon |
| "this afternoon" | ✅ extracted today, booked today 12:00 |
| "tomorrow morning" | ✅ extracted Sun; no Sun slots → fell back to Mon |
| "as soon as possible" | ❌ **booked Monday, should have been today 12:00** (Finding #7) |

All test bookings were cancelled; 0 upcoming remaining on event `6522694`.

### Test artifacts (disposable)
- Final test LLM: `llm_803bf02eb969b452a7d059c10373`
- Final test chat agent: `agent_fc74e20f5bb05c399d03af00b9`
- Earlier disposable LLMs/agents from the spike remain but are unused.

---

## Current `.env` state (close-out)

| Key | Value | Notes |
|-----|-------|-------|
| `SKIP_SIGNATURE` | ~~true~~ | ~~⚠️ **TEST-ONLY bypass.** Must be removed for production (Finding #1).~~ **RESOLVED — removed from code and `.env`.** |
| `LOOKAHEAD_DAYS` | `7` | Widened from `2` (Finding #6). |
| `EVENT_TYPE_ID` | `6522694` | |
| `SLOT_DURATION_MIN` | `60` | |

---

## Before production integration

1. ~~**Restore signature verification** — replace `SKIP_SIGNATURE=true` with the real Retell webhook-badge key.~~ **DONE.**
2. **Persistent Caddy** — apply the root Caddyfile block before the voice agent uses the custom function.
3. **V3.1 integration** — wire the custom function + corrected `book_calendar` (`time` local + `timezone`) into V3.1 `tool_definitions_v3.json` and the booking prompt, following the plan's HITL approval gate.
4. **Prompt: ASAP selection rule (Finding #7)** — add "book the earliest slot when ASAP" to the booking prompt. Still to fix.
5. **Prompt: current time variables** — inject `{{current_time_Europe/London}}` (Finding #3) into the booking state prompt.

---

## CRITICAL FINDING #8 — Retell mangles non-200 bodies; validation must return 200

Tested live (2026-08-02) via Retell `/create-chat-completion` against the disposable test agent.

**When our webhook returned HTTP 400, Retell did NOT pass the body through cleanly.** The custom-function caller treats 4xx as an Axios error and destroys the JSON:

```
response data: [{"ok":false,"error":"1","message":"2"},"no_start_time","slot_target_date is required. ..."]
```

The `{"ok":false,"error":"no_start_time","message":"..."}` object was exploded — Retell replaced `error`/`message` values with `"1"`/`"2"` and appended the real values as separate array items. The LLM cannot reliably read the structured code from that.

**Fix (APPLIED):** `main.py` now returns the two date-validation errors (`no_start_time`, `invalid_slot_target_date`) as **HTTP 200** with the same JSON body. Verified live — the 200 body reaches the LLM as clean, parseable JSON:

```json
{"ok":false,"error":"no_start_time","message":"slot_target_date is required. Ask the caller which day they want, then pass the date as YYYY-MM-DD."}
```

Kept as-is (non-200, infra-level): `401 unauthorized`, `429 rate_limited`, `400 unknown_account`, `400 invalid_json`. The LLM must be prompted to treat ALL `check_availability` responses as 200 and read the `error`/`message` fields (see `prompt_context.md`).

### Cal.com error map (probed 2026-08-02, `GET /v2/slots`)
| Input | Cal status | Cal body | Our mapping |
|---|---|---|---|
| Valid future date | 200 | `data` with slots | `ok:true, slots:[...]` |
| Past date / no availability | 200 | `data: {}` (empty) | `ok:true, slots:[], message:no_availability_in_window` |
| Malformed date (e.g. `2026/08/10`) | 400 | `BadRequestException "start must be valid ISO 8601"` | we validate first → `invalid_slot_target_date` (200) |
| Wrong `eventTypeId` | 200 | still returns slots (falls back) | N/A (we pin event id server-side) |
| Missing `start` / missing params | 400 | `BadRequestException` | we enforce `slot_target_date` → `no_start_time` (200) |
| Bad API key | 401 | `UnauthorizedException "Invalid API Key"` | upstream → `upstream_unavailable` (200) |
| Wrong `cal-api-version` | 404 | `NotFoundException` | upstream → `upstream_unavailable` (200) |

Net: our local function always returns 200 and maps Cal errors into `{ok:false, error, message}` so the LLM reads clean JSON regardless of the upstream cause.

### Test agents (disposable, 2026-08-02)
- Prod webhook test LLM (gpt-5.1, context prompt incl. 200-handling): `llm_42fc4c13375975252737250ac44c`
- Prod webhook test chat agent: `agent_2d81ab76b537bce3673323ad88`
- Earlier lean agent (original ASAP-omit prompt): `agent_168bb34eda7566f70ef1be606d` (LLM `llm_27e4f070cb64ccaf7783e4bfb2be`) — used to prove the 400→200 body passes through.
- `WEBHOOK_TEST/prompt_context.md` updated with the "always 200, read error/message" contract; build script `build_prod_webhook_test_llm.py`.

---

## CRITICAL FINDING #9 — CORRECTED: passing UTC `iso` (Z + ms) to native booking reintroduces the -1hr bug (root cause = Finding #2 format, NOT a Retell tool bug)

> **2026-08-02 correction:** an earlier draft blamed Retell's native `book_appointment_cal`. That was wrong. The true root cause is a **format regression I introduced** — feeding the native tool UTC-with-`Z`+ms instead of the documented bare-local `time`.

Tested live (2026-08-02) via Retell chat agent `agent_f47f3f2caa6c90b80fd9cbc868` (chat `chat_29d434c67374f4d9fcdd863049b`).

User asked for **11:00** London on 2026-08-03. Full chain inspected from `get-chat`:

| Item | Value |
|---|---|
| Webhook returned correct `iso` for 11:00 local | `2026-08-03T10:00:00.000Z` ✅ |
| Agent sent to `book_calendar` (`arguments.time`) | `2026-08-03T10:00:00.000Z` ❌ (**UTC with Z + ms**) |
| Cal.com booking recorded start | `2026-08-03T09:00:00.000Z` ❌ (1 hour early) |

**What went wrong:** the agent sent `time` = the **UTC `iso`** (`...000Z`, with milliseconds). Finding #2 already proved the native `book_appointment_cal` tool must receive `time` as a **bare Europe/London local string, no `Z`, no ms** (e.g. `2026-08-03T11:00:00`) + `timezone: Europe/London`. The `Z` + milliseconds payload is exactly the "incorrect payload that FAILED (400 too soon)" documented in Finding #2 — here it produced a silent 1-hour shift instead.

**The native tool is NOT broken.** Yesterday's spike (2026-08-01) booked correctly with the documented format (`booking_id 23236205`, `start=2026-08-01T11:00:00Z`, matching) across multiple runs.

**Correct fix (matches Finding #2):** the agent MUST pass the slot's **bare local `time`** field (no `Z`, no ms) + `timezone: Europe/London` to `book_calendar`. Do NOT use `iso` for booking.

Rules (locked, per Finding #2):
- `time` = bare Europe/London local `%Y-%m-%dT%H:%M:%S`, **no `Z`, no ms**.
- `timezone` = `"Europe/London"`.
- **Never** pass `start` or `timeZone` (camelCase) to the booking tool.
- `iso` (UTC) is for reference/display only — not for booking.

### v2 test agent (disposable)
- LLM `llm_0b06cb6cbc897edb206cd73e3931`, chat agent `agent_f47f3f2caa6c90b80fd9cbc868`. Build script `build_prod_webhook_test_v2_llm.py`. **Prompt must be corrected to send bare local `time`, not `iso`.**

---

## CRITICAL FINDING #10 — Multi-account support (added 2026-08-07)

The webhook now serves **multiple calendar accounts** behind one URL via `CAL_ACCOUNTS` + an `account_id` arg. Full how-to: **`cal_slots_endpoint/README.md`**.

### Where each account is defined (server-side only)

`.env` → `CAL_ACCOUNTS` is the **only** place the webhook learns "account label → api key → event ID → duration":

```json
CAL_ACCOUNTS={
  "diallux":       {"cal_api_key":"cal_live_a9704f08...", "event_type_id":6522694, "timezone":"Europe/London", "duration":60},
  "diallux_live":  {"cal_api_key":"cal_live_e2d8752e...", "event_type_id":3801235, "timezone":"America/Mexico_City", "duration":45}
}
```

The map key is the **label** the LLM sends as `account_id`. `config.resolve(account_id)` returns that entry's key/event/duration; `main.py` uses `acct["duration"]` (per-account) instead of the global `SLOT_DURATION_MIN`. Keys and event IDs never appear in any prompt.

### Deterministic account selection

`account_id` is set as a **fixed `default`** in the Retell custom tool schema (per agent), so the model passes it verbatim and cannot choose a different account. Example schema in `README.md` §4.

### ⚠️ Backward-compat note — existing HVAC agent

The **existing HVAC agent's LLM is NOT yet sending `account_id`** (its live tool schema predates this change). It relies on `resolve(None)` falling back to the **first** entry in `CAL_ACCOUNTS` (`diallux`, event 6522694). As long as `diallux` stays first, HVAC keeps working with no change. If you reorder/rename accounts, HVAC will silently target the wrong account.

**One-line fix to make HVAC explicit:** add `"account_id": {"type":"string","default":"diallux"}` to the HVAC custom tool's `check_availability` schema (already done in `V3.1/JSON/tool_definitions_v3.json` + `prompts/calendar/tool_definitions_today.json`), then **rebuild the HVAC LLM** (Retell caches — never patch) to publish it.

### Files changed for multi-account
- `config.py` — `resolve()` returns per-account `account_id` + `duration`; flat-env fallback still works.
- `main.py` — uses per-account `duration`, logs `account=.. event=.. duration=..`.
- `.env` — added `diallux_live` account (event 3801235, 45 min).
- `.env.example` — documented multi-account shape.
- `README.md` (new) — full multi-account how-to.
- HVAC tool schemas — `account_id` default `"diallux"`.

---

## FINDING #11 — `timezone` output arg + per-account `include_iso` (2026-08-20)

Extends Finding #2/#9 to make the returned slot `time` **zone-parametric** and to let an account
**omit `iso`** from the response.

### The rule (locked): `time` and `timezone` must be the SAME zone

Native `book_appointment_cal` resolves a booking instant from `time` (bare local, no Z/ms) +
`timezone` (IANA) **in the same zone**. If the endpoint returns `time` in account-tz but the agent
books with a different `timezone`, the instant is wrong.

### New optional `timezone` arg on `POST /check_availability`

```json
{ "slot_target_date": "2026-08-21", "account_id": "diallux_live", "timezone": "America/Chicago" }
```

- `day` + `time` are returned in the **requested** `timezone` (validated as IANA → `invalid_timezone`
  400 if bad).
- Omitted → defaults to the account's own `timezone` (backward compatible; existing callers that
  don't pass `timezone` are unchanged).
- Sort is by the parsed UTC instant, **not** by `iso` string.

### Per-account `include_iso` (default true)

Each `CAL_ACCOUNTS` entry may set `"include_iso": false` to strip `iso` from the slots response:

```json
"diallux":      {"...", "timezone":"Europe/London", "include_iso":false}
"diallux_live": {"...", "timezone":"America/Mexico_City"}          // include_iso unset → true
```

- `diallux` (heating_uk) omits `iso` — airtight against the 1h-shift bug; the agent can only pass
  local `time` + `timezone`.
- `diallux_live` (Dialux) still returns `iso` until its consumers migrate to V2 (`time`+`timezone`).
- Removing `iso` globally is deferred until ALL consumers stop referencing it.

### Why not `start`/UTC

Passing UTC `iso` as `time` silently books 1h early (Finding #9). Dialux's `create_livecall_booking`
`start`=`iso` reference is the same V1 bug, not a real need — it uses the same native tool.

