# Webhook Test Plan — Custom Function Validation Session

> **Date:** 2026-08-01
> **Purpose:** Build an ultra-lean test LLM (2 tools only) to validate that (a) our custom `check_availability` function works end-to-end and (b) Cal.com/Retell's native `book_appointment_cal` integration accepts our verified params. This session produces a NEW isolated test LLM + chat agent — it does NOT touch the V3.1 LLM or any voice agent.

---

## Session Summary (Compaction)

### Project

HVAC voice agent for British Heat Services (Newcastle). 6-state multi-prompt architecture on Retell AI. This session is a **surgical validation spike** — not a polish task. We deploy a throwaway 2-tool agent to prove the slot-checking and booking plumbing before wiring it into V3.1.

### Why This Test Exists

1. We replaced Retell's native `check_availability_cal` with a **custom function** (`webhooks/slots/`) that queries Cal.com directly and returns discrete `{day, time, iso}` slots.
2. We changed Cal.com event from `6389911` (Google Meet, 30 min) to **`6522694`** (Address location, 60 min).
3. We verified Cal.com's booking params manually (see `CAL_SLOTS_CUSTOM_FUNCTION.md`). We must now confirm **Retell's native booking tool** accepts those exact params when wired through the platform — the manual `curl` tests bypass Retell, so they don't prove the Retell integration.

### Goal

Prove two things with an ultra-lean test agent:
- **A.** Our custom function returns discrete slots through Retell (the LLM calls `check_availability`, gets `{day, time, iso}`, offers them).
- **B.** Retell's native `book_appointment_cal` successfully books event `6522694` with our verified params (name, email, attendeePhoneNumber, timeZone, start, title, notes, location).

---

## Live State (confirmed — DO NOT change)

### Custom Function (our code)
| Item | Value |
|------|-------|
| Source | `webhooks/slots/main.py` |
| URL | `https://slots.diallux-ai.site/check_availability` |
| DNS | `slots` A → `46.62.233.228` (live) |
| Caddy (NOW) | Route **added in-memory** via admin API into `srv1` (:443) — **test-only, vanishes on Caddy reload/restart** |
| Caddy (FUTURE) | Persistent block `slots.diallux-ai.site { reverse_proxy localhost:8001 }` in `/etc/caddy/Caddyfile` (needs root) |
| Service | systemd user `cal-slots.service` (running, port 8001) |
| Event type | `6522694` |
| Cal API key | `${CAL_KEY_3}` (Akrit's) |
| Slots API version | `2024-09-04` |

### Retell / Cal.com
| Item | Value |
|------|-------|
| Retell API key | `${RETELL_KEY_5}` |
| Event type | `6522694` (Diallux Booking Demo, 60 min, Address) |
| Attendee email | `jaydiallux@gmail.com` |
| Booking API version | `2026-05-01` |
| Cancel API version | `2026-02-25` |

---

## Caddy Reverse Proxy — Two Approaches

We use **two distinct approaches** to route `slots.diallux-ai.site` → `localhost:8001`:

### NOW (in use): Caddy Admin API — no root, test-only

Caddy's admin API on `127.0.0.1:2019` is unauthenticated and reachable without root. We add the route **in-memory**. **This is what we are using right now for the test.**

> ⚠️ **In-memory only** — it disappears on the next Caddy reload/restart/system reboot. Good enough for the webhook test, but NOT persistent.

**Key detail (learned live):** the route must go into **`srv1` which listens on `:443`** (where all public hostnames live). Adding it to `srv0` (`:3456`) silently returns Caddy's empty default response (200, empty body).

The append syntax `routes/-` is **not** supported by this Caddy version — use a merged-array PATCH instead:

```bash
# Dump current srv1 routes
curl -s http://127.0.0.1:2019/config/apps/http/servers/srv1/routes/ > /tmp/routes_srv1.json
# Append the slots route to the JSON array (match host, reverse_proxy localhost:8001)
# then PATCH the whole array back
curl -s -X PATCH "http://127.0.0.1:2019/config/apps/http/servers/srv1/routes" \
  -H "Content-Type: application/json" --data @/tmp/routes_srv1_new.json
```

The route object to append (mirrors the existing srv1 routes, no `terminal` on the inner subroute):

```json
{
  "handle": [{"handler": "subroute", "routes": [
      {"handle": [{"handler": "reverse_proxy", "upstreams": [{"dial": "localhost:8001"}]}]}
  ]}],
  "match": [{"host": ["slots.diallux-ai.site"]}],
  "terminal": true
}
```

**Verify:** `curl -s -4 https://slots.diallux-ai.site/health` → `{"ok":true,"service":"cal_slots"}`

> Use `-4` (IPv4) because DNS also advertises an IPv6 address; without `-4` the request may hit a non-Caddy endpoint.

---

### FUTURE (to be done, deferred): Persistent root config

Before the custom function goes live in production, the in-memory route **must** be made persistent. This requires **root/sudo**, which we do not yet have for user `2nd_workspace` (uid 1003). We are to update the config to root in the future.

**Persistent Caddyfile block** (root-owned file `/etc/caddy/Caddyfile`):

```
slots.diallux-ai.site {
	reverse_proxy localhost:8001
}
```

Then, as root:
```bash
sudo systemctl reload caddy
```

**Verify:** `curl -s -4 https://slots.diallux-ai.site/health` → `{"ok":true,"service":"cal_slots"}`

**When:** this root config update must be completed during the V3.1 integration step, before the voice agent goes live with the custom function (otherwise the route drops on the next Caddy reload/restart).

---

## Execution Order

```
Step 1 → Route slots.diallux-ai.site → localhost:8001 via Caddy admin API (srv1, :443) — in-memory, done
Step 2 → Verify public URL health + signed check_availability over HTTPS — done
Step 3 → Build ultra-lean "Webhook Test" LLM (custom check_availability + book_calendar)
Step 4 → Create chat test agent pointing at the new LLM
Step 5 → Interact with the chat agent: offer slots → pick one → book
Step 6 → Verify the booking exists in Cal.com; confirm discrete slots returned
Step 7 → Clean up test booking(s) / report results
```

---

## Step 1 — Route via Caddy Admin API (DONE, in-memory)

Route added into `srv1` (:443) via admin API — no root. Confirmed `https://slots.diallux-ai.site/health` → 200. **Persistent root config deferred (see FUTURE section above).**

## Step 2 — Verify Public Endpoint Over HTTPS

```bash
# health (use -4 IPv4; DNS also advertises IPv6)
curl -s -4 https://slots.diallux-ai.site/health

# signed check_availability (mirror Retell's HMAC envelope)
python3 - << 'EOF'
import hashlib, hmac, json, urllib.request
KEY = "${RETELL_KEY_5}"
body = json.dumps({"name": "check_availability", "args": {}}).encode()
sig = hmac.new(KEY.encode(), body, hashlib.sha256).hexdigest()
req = urllib.request.Request("https://slots.diallux-ai.site/check_availability",
    data=body, headers={"Content-Type":"application/json","X-Retell-Signature":sig})
with urllib.request.urlopen(req) as r:
    print(r.status, r.read().decode()[:500])
EOF
```

**Expected:** `200` + `{"ok":true,"slots":[...]}` with discrete future slots.

---

## Step 3 — Build the Ultra-Lean "Webhook Test" LLM

### Design: single state, 2 tools, no KBs, minimal prompt

Create a fresh build script + assets in a new dir so it NEVER touches V3.1.

```
agents/heating_uk/multiprompt/WEBHOOK_TEST/
├── build_webhook_test_llm.py
├── prompt.md
└── JSON/
    └── tool_definitions.json
```

### prompt.md (ultra lean, ~150 tokens)

```
You are a test booking agent. You help the caller find a slot and book it.

Conversation:
1. When the caller wants a slot, call check_availability. It returns discrete
   {day, time, iso} slots. Offer the 1-2 closest as "[DAY] at [TIME]".
2. When the caller picks a slot, call book_calendar with the exact iso as
   start, and these fixed values:
     name = the caller's name
     email = jaydiallux@gmail.com
     attendeePhoneNumber = the caller's number if known
     timeZone = Europe/London
     title = "Webhook Test"
     notes = "Webhook test booking"
     location = "14 Victoria Terrace, Newcastle, NE4 5AB"
3. Confirm success or report failure naturally.

Only call book_calendar after the caller explicitly picks a slot.
```

### tool_definitions.json

**general_tools:**
- `end_call` (optional; the chat test may not need it — include for realism)

**state "booking_test" tools:**
1. **`check_availability`** — type `custom`, the crucial one:
```json
{
  "type": "custom",
  "name": "check_availability",
  "description": "Check available appointment slots. Returns discrete {day, time, iso} slots.",
  "url": "https://slots.diallux-ai.site/check_availability",
  "method": "POST",
  "parameters": {
    "type": "object",
    "properties": {}
  },
  "args_at_root": true,
  "speak_after_execution": false
}
```
2. **`book_calendar`** — type `book_appointment_cal`:
```json
{
  "type": "book_appointment_cal",
  "name": "book_calendar",
  "description": "Book a confirmed appointment via Cal.com.",
  "cal_api_key": "${CAL_KEY_3}",
  "event_type_id": 6522694,
  "timezone": "Europe/London"
}
```

### Build script
Clone `V3.1/build_v3_llm.py`, strip to a single state, no edges, no KBs. POST to `/create-retell-llm`. Print `llm_id`.

---

## Step 4 — Create Chat Test Agent

```bash
# POST /create-chat-agent with response_engine {type: retell-llm, llm_id: <NEW_ID>}
python3 - << 'EOF'
import json, urllib.request
KEY = "${RETELL_KEY_5}"
LLM_ID = "<NEW_ID>"
url = "https://api.retellai.com/create-chat-agent"
data = json.dumps({
    "response_engine": {"type": "retell-llm", "llm_id": LLM_ID},
    "agent_name": "Webhook Test"
}).encode()
req = urllib.request.Request(url, data=data, method="POST")
req.add_header("Authorization", f"Bearer {KEY}")
req.add_header("Content-Type", "application/json")
with urllib.request.urlopen(req) as r:
    print(json.loads(r.read().decode()))
EOF
```
**Save `agent_id`.** This is the chat agent we interact with — no phone needed.

---

## Step 5 — Interact With the Chat Agent

Use Retell's chat completion endpoint (`/create-chat-completion`) or the SDK to send messages. Sequence:
1. `User: "I need a booking."`
2. Expect agent to call `check_availability` → confirm it returns discrete slots.
3. `User: "I'd like the first slot."`
4. Expect agent to call `book_calendar` with our params → confirm it books.
5. Confirm agent reports success.

**This is the exact validation:** does the custom function return slots through Retell, and does Retell's native booking accept our params?

---

## Step 6 — Verify the Booking in Cal.com

```bash
curl -s -H "Authorization: Bearer $CAL_COM_API_KEY" -H "cal-api-version: 2026-05-01" \
  "https://api.cal.com/v2/bookings?eventTypeId=6522694&status=upcoming" | head -c 1000
```
Confirm a booking exists with our test attendee + the `location` address string set.

---

## Step 7 — Clean Up / Report

Cancel any test booking via `/v2/bookings/{uid}/cancel` (version `2026-02-25`). Report:
- Did the custom function return discrete slots? (A ✅/❌)
- Did Retell's native booking accept our params? (B ✅/❌)
- If ❌: capture the exact error, note which param Retell rejected, and feed back into the V3.1 tool-definition update.

---

## Deploy Rules

1. **NEVER patch the V3.1 or production LLM.** Create a fresh throwaway LLM for this test.
2. **This test LLM + chat agent are disposable.** After validation, note the IDs in case of reuse but don't wire them to any phone.
3. Build with `export RETELL_API_KEY=${RETELL_KEY_5}`.

---

## Reference Files

| File | Use |
|------|-----|
| `CAL_SLOTS_CUSTOM_FUNCTION.md` | Custom function architecture + verified booking param mapping |
| `webhooks/slots/main.py` | Our endpoint code |
| `webhooks/slots/.env` | Keys + event config |
| `CAL_COM_API_NOTES.md` | Cal.com API versions + event types |
| `docs/MCP_Guidelines/RETELL_CURRENT_API_REFERENCE.md` | Retell endpoints |
| `agents/heating_uk/multiprompt/V3.1/build_v3_llm.py` | Template for the lean build script |

---

## Success Criteria

| # | Test | Pass |
|---|------|------|
| 1 | Public HTTPS URL health | `curl https://slots.diallux-ai.site/health` → 200 |
| 2 | Signed `check_availability` via HTTPS | Returns discrete future slots |
| 3 | Chat agent calls custom function | Slot data flows into conversation |
| 4 | Chat agent calls native `book_calendar` | Booking created on Cal.com event 6522694 |
| 5 | Booking has correct location/attendee | Verified via `/v2/bookings` |

---

## Deferred / Not In This Plan

| Item | Why |
|------|-----|
| Wire custom function into V3.1 tool_definitions | After this test proves A + B |
| Update V3.1 `book_calendar` def (event 6522694, location field) | After this test proves B |
| Update V3.1 booking prompt to send `location` | After B is confirmed |
| Full 18-scenario regression | Post-deploy, separate session |
