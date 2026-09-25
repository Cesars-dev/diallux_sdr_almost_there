# TEST_HAPPY_PATH_TODAY — heating_uk V3.1 local-`time` booking (user runs this)

This procedure rebuilds the V3.1 `{{today}}` LLM (which already uses **local** `time`, never
`iso`, per the this-session prompt edits), creates a new chat agent, runs the LLM-to-LLM happy
path, and verifies the booking lands at the correct UTC instant (no 1h shift).

The implementing agent only wrote files — **build, run, and cancel are yours.**

## 1. Rebuild the LLM + chat agent

```bash
cd /home/julio/projects/Retell_AI_MCP_connection
set -a; source .env; set +a
python3 agents/heating_uk/multiprompt/V3.1/build_v3_llm.py
```

`build_v3_llm.py` requires `RETELL_API_KEY` in env (the `set -a; source .env; set +a` provides it).
It only reads prompts from `V3.1/prompts/` (the already-applied local-`time` edits), so the rebuild
picks them up.

## 2. Set AGENT_ID in the test

The build script prints a **DEPLOY SUMMARY**. Copy the printed **Chat Agent ID** and set it in
`agents/heating_uk/performance_tests/test_happy_path_today.py`:

```python
AGENT_ID = "agent_..."   # ← paste the new Chat Agent ID here
```

(There is a placeholder `agent_8f94a7dcb044e7b6ce3acd2218` currently in the file — overwrite it.)

## 3. Run the happy path

```bash
cd /home/julio/projects/Retell_AI_MCP_connection
set -a; source .env; set +a
python3 agents/heating_uk/performance_tests/test_happy_path_today.py
```

The harness (Test A = John, Test B = Sarah) already handles empty agent turns and string-parses tool
`arguments`, so it correctly detects `book_calendar` firing.

## 4. Verify the booking instant (no 1h shift)

- `book_calendar` must fire with `time` = the exact **bare local Europe/London** slot value. A slot the
  agent calls "2pm" must send `time = "...T14:00:00"` — **NOT** `13:00:00`. If it sends `13:00:00`
  for "2pm", the endpoint is still leaking UTC-derived values and the 1h bug is back.
- Cross-check on Cal.com — fetch the created booking's `start` (should be correct UTC; 2pm BST → `13:00:00Z`):

```bash
cd /home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint
set -a; source .env; set +a
curl -s -H "Authorization: Bearer $CAL_COM_API_KEY" \
     -H "cal-api-version: 2026-05-01" \
     "https://api.cal.com/v2/bookings/{booking_uid}"
```

Replace `{booking_uid}` with the `booking_uid` printed by the test. Confirm `start` is the UTC
instant that corresponds to the local slot time (2pm BST == `13:00:00Z`).

## 5. Cancel the test booking

```bash
curl -s -X DELETE -H "Authorization: Bearer $CAL_COM_API_KEY" \
     -H "cal-api-version: 2026-02-25" \
     "https://api.cal.com/v2/bookings/{booking_uid}"
```

## 6. Pass / fail

- **PASS** if `book_calendar` fires with local `time` and the Cal.com booking lands at the correct UTC instant.
- **FAIL** if `time` is shifted by 1h — that indicates the endpoint's `include_iso`/local-`time` contract is not live. Confirm `cal-slots.service` was restarted after the `main.py`/`.env` edits (see `cal_slots_endpoint/TEST_VERIFY.md`).
