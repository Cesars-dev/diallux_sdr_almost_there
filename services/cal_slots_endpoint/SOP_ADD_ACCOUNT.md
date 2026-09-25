# SOP — Add a Calendar Account to the Slot Webhook + Wire the Retell Custom Function

> **Purpose:** Make the slot webhook understand a new calendar (account → api key → event ID → duration), and configure + POST the matching Retell **custom function** so the agent calls it with the right `account_id`.
> **Applies to:** `cal_slots_endpoint/` (webhook) + any Retell LLM that uses `check_availability`.
> **Source of truth:** `README.md` (overview), `FINDINGS.md` (Finding #10), `.env.example` (syntax).
> **Every change requires a webhook restart AND an LLM rebuild (Retell caches — never patch).**

---

## 0. The two sides you must keep in sync

| Side | File / place | What it stores |
|------|--------------|----------------|
| **Webhook** | `cal_slots_endpoint/.env` → `CAL_ACCOUNTS` | label → `cal_api_key`, `event_type_id`, `timezone`, `duration` (the secrets) |
| **Retell tool** | custom function in the LLM's `tools[]` | `account_id` **default** = the label (so the model sends it deterministically) + `slot_target_date` |

The **label** is the only thing shared: it's the `account_id` the tool sends, and the key the webhook looks up. Get the label wrong on either side → `unknown_account`.

---

## 1. PART A — Add the account to the webhook (`.env`)

### A.1 Open the env file
```
cal_slots_endpoint/.env
```

### A.2 Edit the `CAL_ACCOUNTS` JSON object

It is a **single-line JSON object** (dict), not an array. One entry per account. **Never a trailing comma** (invalid JSON). Exact shape:

```json
CAL_ACCOUNTS={
  "diallux":       {"cal_api_key":"cal_live_a9704f08...","event_type_id":6522694,"timezone":"Europe/London","duration":60},
  "diallux_live":  {"cal_api_key":"cal_live_e2d8752e...","event_type_id":3801235,"timezone":"America/Mexico_City","duration":45}
}
```

| Field | Type | Required | What it is |
|-------|------|----------|------------|
| map key | string | ✅ | the **label** / `account_id` the agent sends (e.g. `"diallux_live"`) |
| `cal_api_key` | string | ✅ | that account's Cal.com API key (**secret — never put in a prompt**) |
| `event_type_id` | int | ✅ | that account's Cal.com event number |
| `timezone` | string | ⬜ | fallback render tz (defaults `Europe/London`) |
| `duration` | int | ⬜ | slot length in minutes (defaults to `SLOT_DURATION_MIN`) |

To add an account: insert a new `"label": { ... },` entry. To change one: edit only that entry.

### A.3 Validate the JSON (MANDATORY — a typo kills the whole service)

```bash
cd /home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint
python3 -c "
import json
raw=[l.split('=',1)[1] for l in open('.env') if l.startswith('CAL_ACCOUNTS=')][0].strip()
d=json.loads(raw)                      # raises on bad JSON
print('VALID. accounts:', list(d.keys()))
"
```
Expected output: `VALID. accounts: ['diallux', 'diallux_live']` (plus any you added).

### A.4 Restart the webhook service

```bash
systemctl --user restart cal-slots.service
systemctl --user status cal-slots.service   # expect: active (running)
```

### A.5 Verify the account resolves

```bash
cd /home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint
env -u CAL_ACCOUNTS python3 -c "
import sys; sys.path.insert(0,'.')
from dotenv import load_dotenv; load_dotenv()
import config
r=config.resolve('diallux_live')
print('event=%s dur=%s tz=%s key=%s...' % (r['event_type_id'], r['duration'], r['timezone'], r['cal_api_key'][:8]))
print('default (no account_id):', config.resolve(None)['account_id'])
"
```

**⚠️ Backward-compat check:** `resolve(None)` returns the **first** entry in `CAL_ACCOUNTS`. If your existing agent doesn't send `account_id`, keep its intended account **first** in the object, or it will hit the wrong calendar.

---

## 2. PART B — Write the Retell custom-function schema

The custom tool lives in the LLM's `tools[]` under the state that books slots. It must be `type: "custom"` pointing at the webhook, with `account_id` as a **fixed `default`** (deterministic — the model can't choose the account).

**Reference files already updated with `account_id`:**
- `agents/heating_uk/multiprompt/V3.1/JSON/tool_definitions_v3.json`
- `agents/heating_uk/multiprompt/V3.1/prompts/calendar/tool_definitions_today.json`

### Exact tool schema

```json
{
  "type": "custom",
  "name": "check_availability",
  "description": "To query available appointment slots on the calendar.\n\nCRITICAL: This tool ALWAYS returns HTTP 200. A 200 does NOT mean success — you must READ the body and act on its contents, never assume.\n\nOn SUCCESS the body is: {\"ok\": true, \"slots\": [{\"day\": \"YYYY-MM-DD\", \"time\": \"YYYY-MM-DDTHH:MM:SS\", \"iso\": \"YYYY-MM-DDTHH:MM:SS.000Z\"}, ...]}\n- \"time\" = The value for booking.\n- \"iso\" = Reference only, not needed.\n- ONLY offer/book slots literally in the slots list.\n\nOn ERROR the body is: {\"ok\": false, \"error\": \"CODE\", \"message\": \"explanation\"} — please correct the call and retry:\n- \"no_start_time\": the day argument was missing. Retry with a concrete YYYY-MM-DD date.\n- \"invalid_slot_target_date\": the date was missformatted. Retry with a valid YYYY-MM-DD date.\n- \"no_availability_in_window\": no free slots in that window. Check the next available day and offer its closest slots.\n- \"upstream_unavailable\": the calendar is temporarily down. Say you'll retry shortly, then retry.",
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
  },
  "args_at_root": true,
  "speak_after_execution": false
}
```

### Rules for this schema (airtight)

1. **`type` must be `"custom"`** — NOT `check_availability_cal` (native returns ranges, not discrete slots).
2. **`url`** = the webhook: `https://slots.diallux-ai.site/check_availability`.
3. **`account_id.default`** = the exact label you put in `CAL_ACCOUNTS` (Part A). One label per agent.
4. **`slot_target_date`** must be present and required at runtime — the webhook returns `no_start_time` otherwise.
5. Keep the **same tool `name`** (`check_availability`) so the state prompts don't change.
6. `parameters.properties.account_id` should NOT be in `required` (it has a `default`; the model fills it). If Retell's UI requires it, add it to `required` — the `default` still forces the value.

---

## 3. PART C — POST the custom function to Retell (create a NEW LLM)

**NEVER patch an existing LLM** (Retell caching bug — a PATCH may not propagate to runtime). Always **create a new LLM** with the full payload, then repoint the agent.

### Option 1 — REST (curl)

```bash
export RETELL_API_KEY="${RETELL_KEY_5}"

# Build the full LLM payload with your states/prompts, and put the custom
# tool (Part B) inside the booking state's "tools" array. Then:
curl -s -X POST "https://api.retellai.com/create-retell-llm" \
  -H "Authorization: Bearer $RETELL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "model": "gpt-5.4",
        "model_temperature": 0,
        "tool_call_strict_mode": true,
        "general_prompt": "<your general prompt>",
        "general_tools": [{ "type": "end_call", "name": "end_call", "description": "End the call." }],
        "states": [
          {
            "name": "slot_selection",
            "state_prompt": "<your slot_selection prompt>",
            "tools": [ <PUT THE PART B CUSTOM TOOL HERE> ],
            "edges": []
          }
        ],
        "knowledge_base_ids": [],
        "kb_config": { "top_k": 3, "filter_score": 0.6 }
      }'
# -> returns {"llm_id": "llm_..."}
```

### Option 2 — via the existing build script

Prefer the project's builder (it already assembles prompts + tools correctly):

```bash
cd /home/julio/projects/Retell_AI_MCP_connection
export RETELL_API_KEY="${RETELL_KEY_5}"
python3 agents/heating_uk/multiprompt/V3.1/build_v3_llm.py
# -> prints the NEW llm_id
```

### Option 3 — via MCP

Call `retell_create_llm` with the same payload shape (`model`, `general_prompt`, `tools`, `states`, ...) where the booking state's `tools` array includes the Part B custom tool. Returns `llm_id`.

### Repoint + publish the agent

```bash
# chat agent (test first, no phone minutes)
curl -s -X PATCH "https://api.retellai.com/update-chat-agent/<agent_id>" \
  -H "Authorization: Bearer $RETELL_API_KEY" -H "Content-Type: application/json" \
  -d '{"response_engine":{"type":"retell-llm","llm_id":"<NEW_LLM_ID>"}}'

# voice agent (production) after chat tests pass
curl -s -X PATCH "https://api.retellai.com/update-agent/<agent_id>" \
  -H "Authorization: Bearer $RETELL_API_KEY" -H "Content-Type: application/json" \
  -d '{"response_engine":{"type":"retell-llm","llm_id":"<NEW_LLM_ID>"}}'
curl -s -X POST "https://api.retellai.com/publish-agent-version/<agent_id>" \
  -H "Authorization: Bearer $RETELL_API_KEY"
```

---

## 4. Verification checklist (run all)

- [ ] `.env` `CAL_ACCOUNTS` validates as JSON (A.3)
- [ ] `systemctl --user restart cal-slots.service` → active (A.4)
- [ ] `curl -4 https://slots.diallux-ai.site/ready` → `{"ok":true,...}` (no `problems`)
- [ ] `config.resolve('<label>')` returns the right event/duration (A.5)
- [ ] LLM rebuilt (NEW id), not patched (Part C)
- [ ] Agent repointed to new LLM id
- [ ] Live test from the Retell chat agent: agent calls `check_availability`, gets `{ok:true, slots:[...]}` with the **new account's** event; booking uses that event
- [ ] Confirm no `unknown_account` in webhook logs: `journalctl --user -u cal-slots.service -f`

---

## 5. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `{"ok":false,"error":"unknown_account"}` | label sent ≠ key in `CAL_ACCOUNTS` | Align Part B `default` with Part A map key |
| Service won't start / cycles | bad JSON in `CAL_ACCOUNTS` | run A.3; fix comma/quotes |
| Agent hit the **wrong** calendar | agent doesn't send `account_id`; it defaulted to first entry | send `account_id` OR reorder first entry (A.5 note) |
| LLM still returns ranges | tool still `check_availability_cal` (native) | change to `type:"custom"` + rebuild |
| 401 on POST | bad/missing `X-Retell-Signature` | confirm webhook-badge `RETELL_API_KEY` in `.env` matches Retell |
| `no_start_time` | `slot_target_date` missing | prompt must always pass a concrete YYYY-MM-DD |
