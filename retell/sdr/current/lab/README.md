# Dialux SDR Local Simulator

A **standalone local runtime for the Dialux SDR chat agent** (V7.9 "slot-lock" build). It replays the
*exact deployed Retell multi-prompt agent* — same `llm.json`, same 9-state machine, same prompts, same
tools, same deterministic webhooks — but runs the brain on **your own OpenAI API key** instead of
Retell-hosted inference, and books **real appointments** through the production Cal.com pipeline.

Born out of a Retell billing wall (new workspaces are prepaid-credit only; free credits exhausted),
this harness proves the entire agent — booking logic included — with **$0 to Retell**, then hands
every trace to self-hosted **Langfuse** for observability.

```
┌────────────┐   function-calling    ┌───────────────┐   HMAC-signed HTTPS   ┌──────────────────────┐
│  GPT-5.2   │◄────────────────────►│  engine.py     │◄────────────────────►│  LIVE production VPS  │
│ (OpenAI)   │    tool_calls JSON    │  (this repo)   │                       │  slots.diallux-ai.site│
└────────────┘                       └──────┬────────┘                       │  :8001 slots+booking  │
       ▲                                    │                                │  :8002 time           │
       │ OpenAI SDK (your key)              │ full transcript,               │  :8003 validator gates│
       ▼                                    │ latency, tokens                └──────────┬───────────┘
┌───────────────┐                            │                                           │
│  Langfuse     │◄───────────────────────────┘                                           ▼
│ (self-hosted) │      every LLM generation + tool span                  Cal.com (real holds, real bookings)
└───────────────┘
```

## What this is NOT

- **Not a re-implementation of the agent.** There is no second state machine, no LangGraph, no agent
  framework. `engine.py` reads the production `llm.json` artifact and executes its edges verbatim.
- **Not connected to Retell.** Zero Retell API calls at runtime. The deployed twin of this agent
  (`agent_f305981ef7b5ce312c1c899bbf`, V7.9_slot_lock) lives in a Retell workspace and uses the same
  source `llm.json` — the simulator mirrors it 1:1 so measurements transfer.

## Files

| File | Role |
|---|---|
| `engine.py` | The Retell-LLM replica (~290 lines). Loads `llm.json`, drives the 9-state machine via OpenAI function calling, executes tools, fills dynamic variables, signs webhook calls. |
| `run_ladder.py` | Acceptance ladder: 5 personas (Maria, Marcus ×2, Danny, Carlos) run sequentially against the engine with an LLM-simulated prospect. Verifies bookings against Cal.com. Saves transcripts to `/tmp/opencode/sim_logs`. |
| `server.py` + `demo.html` | Client-facing demo: FastAPI + single-page chat UI on `:8010`. A visitor chats with "Linda" and gets a **real** call booked. |
| `langfuse_bridge.py` | Persistent observability. Every conversation = one Langfuse trace; every LLM call = a generation (tokens, latency); every tool call = a tool span; the **full conversation transcript** is stored on the root trace at finish. Fail-safe: if Langfuse is down, the ladder still runs. |
| `analysis/` | Post-run analyses per the team's CALL-ANALYSIS-SOP. |

## How it works — every mechanism, precisely

### 1. State machine (the "graph engine")

The agent has 9 states: `Intake → Discovery → Closer → Offer → contact_details → ConfirmSlots →
VerifyLead → Booking → Closing`. The entire runtime is:

```python
def system_message(self):
    return self.subst(self.llm["general_prompt"] + "\n\n" + self.states[self.state]["state_prompt"])
```

Each GPT turn receives **only** `general_prompt + the CURRENT state's prompt` — never all nine.
Edges from `llm.json` become functions named `transition_to_<DestinationState>` (Retell's own
convention). When the model calls one, `self.state = dest` swaps the prompt + toolset for the next
turn. There is no graph library; the graph is data in `llm.json`.

### 2. Tool invocation (function calling)

State tools + `general_tools` (`end_call`) + edge-transitions are converted to OpenAI tool schemas:

- `type: "custom"` tools → `{"type":"function", ...}` with the tool's `parameters` JSON schema
- `type: "extract_dynamic_variable"` tools → function whose parameters are the tool's `variables`
  (Retell's `type:"enum"` + `choices` → OpenAI `type:"string"` + `enum`)
- edges → `transition_to_X` functions

The model **cannot execute anything** — it only emits
`{"name": "create_livecall_booking", "arguments": {...}}`. `engine._exec()` dispatches:

| Tool kind | What `_exec` does |
|---|---|
| `transition_to_X` | `self.state = X`, returns `{"status":"ok","state":X}` |
| `end_call` | sets `self.ended = True` |
| extract_dynamic_variable | writes non-empty args into the dynamic-variables dict |
| custom (webhook) | **HMAC-signs and POSTs to the LIVE production endpoint**, copies `response_variables` from the JSON response into the dict, returns the body to the model |
| repeat guard | identical tool+args twice in a row → returns `"already_captured"` nudge instead of re-executing (stochastic loop guard, e.g. Susan's 8× `extract_leak_inputs`) |

### 3. Dynamic variables (the fill mechanism)

One plain Python **dict** seeded from `llm.json`'s `default_dynamic_variables` (41 keys, all empty),
personalized per persona (e.g. `{"callback_number": "+13124001234"}`). Exactly two doors write into it:

1. **extract tools** — the model fills arguments ("my number is 512…" → `dvs["callback_number"] = "+15123120001"`)
2. **`response_variables`** on custom tools — endpoint response keys copied verbatim (fail-closed:
   keys absent on failure → dict untouched → downstream edge conditions can't pass)

And **one reader**: `subst()`, which runs before every GPT call and replaces `{{variable}}` tokens
(and `##slug-kb##` markers, see below) in the system prompt. GPT sees filled values in its
instructions and copies them verbatim into tool args; the deterministic server-side gates
(`validate_lead`, `verify_lead_data`, `/book-livecall`) re-verify everything independently.

### 4. Knowledge bases — no RAG, full inline

Prompts carry Retell KB markers (`##sales-language-kb##` etc.). `subst()` replaces each marker with
the **entire markdown file** from `Knowledge bases/*.md` (the same 9 files Retell embedded).
Corpus ≈ 35 KB → ~9K tokens. **Measured latency impact: zero** (no-KB 0.90s vs with-KB 0.76s —
noise). Trade-off vs Retell's vector retrieval: no retrieval misses, slightly higher input tokens
(~$0.10–0.15/call at GPT-5.2 pricing), deterministic behavior.

### 5. GPT-5.2 configuration — the latency saga (measured, not guessed)

| Config | LLM-only latency | Verdict |
|---|---|---|
| `temperature=0.1` + default reasoning (Retell default) | 22s avg, **87s spikes** | ☠️ pathological |
| `reasoning_effort: low` / `medium` / `high` | 3.0 / 6.7 / 6.8 s | slower — explicit effort forces reasoning tokens |
| `reasoning_effort: high` | 6.8s | **missed the tool call** (reasoning ate the completion budget) |
| **no `temperature`, no `reasoning_effort`** | **avg 0.84s, max ~1.1s** | ✅ production config |

Facts: gpt-5.2 rejects `reasoning_effort:"minimal"` and rejects `temperature` whenever
`reasoning_effort` is set. Prompt size is NOT a latency driver (a 2.1K-token call measured slower
than a 6K-token one — output generation dominates). `REASONING_EFFORT` and `TEMPERATURE` env vars
can override, but the fast defaults are baked in.

### 6. Webhook signing (identical to Retell)

Custom tools are called exactly as Retell would:

```
POST https://slots.diallux-ai.site/<path>
X-Retell-Signature: v=<ms_epoch>,d=<hex>
  where d = HMAC-SHA256(raw_body + str(ms), RETELL_API_KEY)
```

Endpoints hit: `POST /check_availability` (slot-lock mode: releases echoed holds, deterministically
picks + **freezes** the 2 best slots via Cal.com reservations, returns exactly those two with
`reservation_uid`s), `POST /book-livecall` (idempotent booking: recovery pre-check → hold match →
`POST /v2/bookings` → acceptance verify → release holds; `booking_intent` gate for
reschedule/cancel), `POST /validator-function/validate_lead` (+`verify-lead-data`,
`record-booking-uid`, `record-reach-details`), `GET /today`.

**Secrets are never in this repo** — `engine.py` loads `RETELL_API_KEY` / `OPENAI_API_KEY` from the
host machine's environment files at runtime (see `load_root_key`).

### 7. Observability (Langfuse, self-hosted v3)

One trace per conversation (session id `sdr-sim-<hex>`), containing:

- a **generation per LLM call**: state, model, full input messages, output text + tool_calls,
  input/output tokens, exact latency
- a **tool span per tool call**: args, full JSON response, latency, state
- on `finish()`: the **complete conversation transcript** (user/assistant/tool messages verbatim),
  final state, and all 41 dynamic variables' final values — stored as the root trace output

Config via env or an external env file (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`,
`LANGFUSE_HOST`). Keys are read at runtime, never stored here.

## Setup

```bash
pip install openai requests fastapi uvicorn langfuse   # no other deps

# Required at runtime (host env or an env file — NOT in this repo):
#   OPENAI_API_KEY     — gpt-5.2 access
#   RETELL_API_KEY     — HMAC signing key accepted by the webhook services
#   LANGFUSE_*         — optional, enables tracing

# The engine reads the agent artifact from ../llm.json (parent folder, outside this repo)
```

## Run

```bash
# Acceptance ladder (sequential by doctrine — parallel runs race the shared calendar)
python3 run_ladder.py            # Maria, Marcus ×2, Danny, Carlos
python3 run_ladder.py 0          # single persona by index

# Client demo (browser chat that books real calls)
python3 server.py                # http://127.0.0.1:8010 (ssh -L 8010:localhost:8010 to view)
```

The ladder expects the persona set at
`../../testing/test_llm_to_llm.py` (`PERSONAS`) — a sibling of this folder in the parent project.
On a standalone clone, point `PERSONAS_PATH` in `run_ladder.py` at your own persona file
(`name`, `expect: book|no-book`, `dynvars`, `opener`, `system`).

## Results obtained with this harness

| Persona | Result | Booking |
|---|---|---|
| Maria (dental, happy path) | ✅ PASS ×3 runs | Cal-accepted each time |
| Danny (auto repair, no-volunteer) | ✅ PASS | alternate-number path exercised |
| Susan (remodeling, no-volunteer) | ✅ PASS (after repeat-call guard) | Cal-accepted |
| **Marcus (law firm)** | ✅ PASS | the persona that failed twice on Retell's native booking tool — books first try through our own endpoint |

Latency (Langfuse-measured, reasoning off): **LLM avg 0.84s / max ~1.1s**; booking-critical tools
1.7s (slot freeze) + 0.7s (booking) — Cal.com round-trips, platform-independent.

Full findings per the team's analysis framework: [`analysis/CALL-ANALYSIS-maria-fastconfig.md`](analysis/CALL-ANALYSIS-maria-fastconfig.md)
(notable: the Closer's leak-monetization pitch is skipped stochastically — fix queued in the
deterministic layer; the "SMS confirmation" line is a scripted false promise flagged for rewording).

## Privacy & secrets

- No API keys, no passwords, no tokens in this repository — everything loads from the host at runtime.
- Test personas use fictional names + fictional E.164 numbers.
- Booking UIDs appearing in `analysis/` are from canceled test bookings on the team's own calendar.
