# AGENTS.md — simulator/ subfolder

> **Read this before touching anything in this folder.** It explains WHAT this is, WHY it exists,
> every file, every mechanism, every external dependency — written so an agent with zero prior
> context can operate safely.

## 1. What this folder is

A **local mirror of a production Retell AI chat agent** ("Linda", the Dialux SDR). The production
agent is a 9-state multi-prompt machine deployed on Retell AI. This folder contains a Python engine
that runs the SAME agent on a raw OpenAI API key — because the Retell workspace ran out of prepaid
credits and the owner needed to keep testing and demoing.

- Source of truth for the agent: `../retell/llm.json` (one level UP, outside this folder — it belongs to
  the V7.9_slot_lock iteration and is the deployed artifact; **do not edit it from here**).
- This folder = the EXPERIMENTAL zone. Everything experimental lives HERE and nowhere else.
- The parent folder structure (`prompts/ tools/ edges/ Knowledge bases/ versions/`) belongs to the
  V7.9 agent iteration — leave it exactly as it is.

## 2. Files (complete map)

| Path | What | May edit? |
|---|---|---|
| `engine.py` | The agent runtime. Reads `../retell/llm.json`, drives states, calls GPT-5.2 (OpenAI SDK), executes tools, signs webhooks, fills dynamic variables. | yes — this is the lab |
| `run_ladder.py` | Acceptance-ladder runner. Imports `PERSONAS` from `../../testing/test_llm_to_llm.py` (parent project). Sequential runs ONLY (parallel runs race the shared Cal calendar). | yes |
| `server.py` | FastAPI demo server on 127.0.0.1:8010. Endpoint `POST /chat {session_id?, message}` → engine reply. In-memory sessions. | yes |
| `demo.html` | The demo chat UI (plain HTML/JS, dark theme). Loaded by `server.py` at `/`. | yes |
| `langfuse_bridge.py` | Observability. One Langfuse trace per conversation; generations per LLM call; tool spans; full transcript on `finish()`. Reads Langfuse keys from `/home/julio/projects/leasing_tenant_scorer/.env` or env — **never hardcode keys**. | yes |
| `analysis/` | Post-run call analyses (team SOP format). | append-only |
| `__pycache__/` | junk | ignored |

## 3. How the engine works (mechanics an operator must know)

### State machine
- `llm.json` → `states[]` (9 states), each with `state_prompt`, `tools`, `edges`.
- `self.state` is a string. Each GPT turn: system = `general_prompt + current state prompt`.
- Edges become tools named `transition_to_<State>`. Model calls one → `self.state` changes.
- **Never** put all 9 state prompts in one message. One state per turn, exactly like Retell.

### Tools
- Custom webhooks: HMAC-signed `POST` (`X-Retell-Signature: v=<ms>,d=HMAC_SHA256(body+ms, key)`)
  to `https://slots.diallux-ai.site/*` — the LIVE production endpoints. These hit the real
  Cal.com calendar. A demo conversation books a REAL appointment.
- The booking endpoint is idempotent: booking with the same caller phone on the same day returns
  the EXISTING booking uid (`recovered: true`) instead of double-booking.
- Extract tools: model fills args → values written to the dynamic-variables dict. Enum-locked
  values (e.g. `booking_intent` ∈ {reschedule, cancel}) come from tool `variables[].choices`.
- Repeat guard: same tool + same args twice consecutively → synthetic "already_captured" response
  (prevents stochastic extract loops).

### Dynamic variables
- One dict `self.dvs`, seeded from `llm.json` `default_dynamic_variables` (41 keys).
- Written by: extract tools (model args) and webhook `response_variables` (response key → dv).
- Read by: `subst()` — replaces `{{var}}` in prompts before every GPT call.
- Fail-closed by design: webhook responses omit keys on failure → dvs stay empty → gates block.

### Knowledge bases
- Prompt markers `##<slug>-kb##` → replaced by the FULL text of `../Knowledge bases/<slug>.md`.
- No vector search, no retrieval. ~9K tokens per call. Measured: zero latency impact.

### GPT-5.2 rules (MEASURED — do not "improve" without re-measuring)
- Do NOT send `temperature` (interacts pathologically with reasoning: 22–87s calls observed).
- Do NOT send `reasoning_effort` (even `low` triples latency; `high` skips tool calls).
- Plain gpt-5.2, no extra params: **~0.84s avg**. Override via env `TEMPERATURE` /
  `REASONING_EFFORT` only for experiments.
- `user_sim` (the fake prospect in the ladder) uses `gpt-5-mini` with default temperature —
  gpt-5-mini rejects custom temperature values.

### External runtime dependencies (NOT in this repo — loaded from the host)
- `OPENAI_API_KEY`, `RETELL_API_KEY` — read from the host root env by `load_root_key()`.
- `LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST` — read from the leasing-scorer env file or env.
- `../retell/llm.json` + `../retell/Knowledge bases/*.md` — the agent artifact.
- `../../testing/test_llm_to_llm.py` — the persona set ( Maria/Danny/Susan/Marcus/Carlos …).
- LIVE services: `slots.diallux-ai.site` (:8001 slots+booking, :8002 time, :8003 validator) behind
  HMAC; Cal.com account `diallux_live` (event 3801235, 45-min, America/Mexico_City service tz).

## 4. Operating procedures

### Run the acceptance ladder
```bash
python3 run_ladder.py            # default order: 0 3 3 1 4 (Maria, Marcus ×2, Danny, Carlos)
python3 run_ladder.py 0          # one persona (0=Maria, 1=Danny, 2=Susan, 3=Marcus, 4=Carlos)
```
- ALWAYS sequential. After every batch: cancel test bookings on Cal (attendee phones from the
  persona `dynvars`), then analyze per `docs/Testing_guidelines/CALL-ANALYSIS-SOP.md`.
- Transcripts land in `/tmp/opencode/sim_logs/`; full traces in self-hosted Langfuse
  (`http://localhost:3001`, project "Leasing Tenant Scorer", sessions named `sdr-sim-*`).

### Run the client demo
```bash
python3 server.py     # then open http://127.0.0.1:8010 (or ssh -L 8010:localhost:8010)
```

### Langfuse notes (SDK v4 — API differs from v3 docs!)
- Root observation per conversation: `lf.start_observation(as_type="agent", ...)`.
- Session id MUST be set via `propagate_attributes(session_id=...)` context manager wrapping the
  root creation — metadata alone does NOT populate the session field.
- Children: `root.start_observation(as_type="generation"|"tool", ...)` then `.end()` AFTER the work
  (open before, close after — otherwise latency reads 0).
- `finish()` stores the FULL conversation transcript as the root output.
- If Langfuse is down: bridge disables itself, ladder keeps running.

## 5. Known findings / queue (as of 2026-09-03)

1. **Closer leak-pitch skip (stochastic)**: model sometimes transitions without calling
   `calculate_monthly_leak` / speaking the leak numbers. Fix queued in the deterministic layer
   (same pattern as the repeat guard) — do NOT patch prompts for it unilaterally.
2. **"SMS text confirmation" scripted promise** in `../retell/prompts/states/Booking.md` — nothing sends
   SMS. Needs owner decision: reword or wire SMS.
3. **`today_date` seed is hardcoded** (`"2026-08-21"` in `../retell/llm.json` defaults) — harmless on the
   happy path (ConfirmSlots calls `check_current_date` before date math) but should be `""`.
4. Retell deployment of this agent exists (`agent_f305981ef7b5ce312c1c899bbf`, workspace out of
   credits). When credits return: redeploy with `model_fast: true`, one variable, full ladder.

## 6. Non-negotiable rules

- **No secrets in this folder.** Keys load from the host at runtime. Scan before committing
  (`keyhound.sh`), never commit `.env`, never print key values.
- **This folder is a PUBLIC repo.** Anything written here is world-visible. Business logic is fine;
  credentials, customer data, and real phone numbers are not (personas are fictional).
- **One variable at a time** when changing agent behavior; run the ladder after any change.
- **Do not touch** `../retell/llm.json`, `../prompts/`, `../tools/`, `../edges/`, `../versions/` from
  inside experiments — changes to the agent artifact go through the owner's iteration doctrine
  (clone → change → build → deploy → ladder).
