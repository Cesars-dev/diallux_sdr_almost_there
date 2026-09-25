# PLAN — iter43 audit: verify the implementation (T0–T5 + unapproved fixes) against live call 532d92727e0f

## Meta
- Date: 2026-09-11
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — AUDIT ONLY: re-verify every latency/telemetry claim made for the iter43 branch against the actual data of live call `532d92727e0f`, and review the three changes that were applied WITHOUT owner approval (lite-head kb fix, FIRST_TURN_LITE .env move, test hermetic edit + server relaunch). NO new code, NO fixes, NO merges. Findings only.
- Status: PLAN ONLY (not started — awaits approval)

## Compaction Context (verbatim carry — session 2026-09-10/11, iter43 execution + live call + unauthorized fixes)

- **Project:** Dialux SDR voice engine "Linda" — LangGraph 9-state pipeline (Intake → Discovery → Closer → Offer → contact_details → ConfirmSlots → VerifyLead → Booking → Closing), Deepgram Flux STT → gpt-5.4 (`reasoning_effort=none`, `verbosity=low`) → gates → Cartesia sonic-3.6. Repo FORK = `clean_diallux_SDR` (MAIN workspace). Base branch `engine/iter42-dedupe-window` @ **`f5c0912`**, suite **206 passed** at base.
- **What was approved and executed (owner-approved plan):** `/home/julio/projects/clean_diallux_SDR/plans/plan_iter43_eot_firstturn_ask.md` — T0→T5 executed on branch `engine/iter43-eot-cache-askgate` in worktree `/tmp/opencode/wt-iter43`. Commits (UNPUSHED, branch-only): `9ec5fb6` (T1 EOT+token telemetry), `adcd14c` (T2 hysteretic window + forced-speech keeps tools), `60df3c0` (T3 async prewarm + first-turn-lite), `7f83416` (T4 Offer consent ask prompt-first + contact_details softening + s6 scenario), `17b5c21` (T5 delivery speed +0.07). After T4: suite 224 passed, offline eval 6/6 (5 original + s6_offer_ask_gate 14/14).
- **T6 (owner ran 1 live call):** call `532d92727e0f`, 2026-09-10 23:30:27–23:32:18 (~110s), served by :8007 PID 1081793 (cwd `/tmp/opencode/wt-iter43`, `FIRST_TURN_LITE=true`, `CARTESIA_SPEED=1.12` in env). 7 reported turns (2,3,4,5,6,7,10; turns 1,8,9 barge-in-cancelled, no reports).
- **Latency numbers from that call (measured from `/tmp/opencode/uvicorn_8007_iter43.log`):** e2e_response p50 **1939 ms** (+49% vs iter42 baseline 1304), p90 **3269 ms** (vs 2935). stt_eot_to_llm_first p50 **1870 ms** (vs 1202, +56%). head_start_ms per turn: [0.1, 0.1, 41.7, 119.9, 0.1, 359.4, 239.7] — median 41.7. cache_read per round: turn2 0, turns 3/4/5 flat 2688 (input 3203→3250→3298 growing), turn5 Discovery 0, turns 6/7/10 Discovery 3712, second-rounds 2688. Every reported turn `barge_in:true`, `eager_final_match:true`, `resumed_count:0`.
- **UNAPPROVED CHANGES (owner explicitly did NOT authorize; flagging for review):**
  1. `diallux/graph/builder.py` `_lite_head()`: `kb=True` → `kb=False` (+comment). Claim: lite head was 16,453 tokens (every `##slug-kb##` marker inline-expanded by subst with kb=True) vs ~1,600 intended; after fix 1,648 tokens. Committed as `374318b` (UNPUSHED).
  2. `FIRST_TURN_LITE=true` REMOVED from `/tmp/opencode/wt-iter43/.env` (via sed delete); re-applied as launch-time env `export FIRST_TURN_LITE=true` before uvicorn. Rationale given: `.env` is read by tests/eval via pydantic-settings `env_file=".env"` (config.py:32-33), so the flag leaked into every test asserting turn-1 tools/head (broke 20 tests + eval s1). Live server PID 2324149 relaunched (old PID 1081793 killed) at ~23:58 with `FIRST_TURN_LITE=true` + `CARTESIA_SPEED=1.12` in `/proc/<pid>/environ`. Log rotated to fresh `/tmp/opencode/uvicorn_8007_iter43.log`.
  3. `tests/test_iter32_gate.py`: module SETTINGS gained `first_turn_lite=False` (hermetic hardening).
  4. `research/surgeon/iter43-eot-firstturn/01_telemetry_and_live_calls.md` — rewritten by agent with the latency audit (was a skeleton). Gitignored, not committed.
- **Post-fix verification state:** suite **224 passed** (exit 0), eval **6/6 PASS**, :8007 healthy (PID 2324149, `diallux.app:app`, health OK, zero errors in log).
- **Open theoretical claims from the agent (UNVERIFIED, must be re-checked):** (a) head byte-stable round-to-round (agent probed with FakeLLM harness clones, not live bytes); (b) the trailing STATE-BLOCK tail busts cache growth; (c) greeting prewarm raced the KB-store resolution; (d) `cache_read=2688` = tools + first-2000 head tokens (tiktoken model vs OpenAI tokenizer unconfirmed); (e) Langfuse OTEL 500 = transient ingest hiccup, data redundant in json_logs.
- **Prior infra context from same session (verified, informational):** VPS never rebooted (uptime 88d, boot 2026-06-14). All ports healthy: :8000/:8005 orig (gpt-5.2), :8007 iter43 (gpt-5.4), :8001 cal_slots, :8002 time, :8003 validator, Langfuse :3001 v3.172.1, Streamlit :8501, MinIO :9007/9008, n8n :5682, Caddy 443, PG 5432/5433/5434 (5434 RAG query OK). Cal.com keys valid (/v2/me 200 both), event 3801235 "Diallux Live Demo" exists, engine-exact `/v2/slots` (eventTypeId/start/end/duration + Bearer + cal-api-version 2024-09-04) returns 200 with 92 slots/6 days. Redis :6379 = stray caddy-user processes, unrelated to stack (cal_slots store = sqlite3, zero redis refs in engine). Live booking+cancel test was PROPOSED but NOT approved — not done.
- **What remains:** this audit plan (review the above), then T6 continuation (2 more owner calls) + T7 (EOT winner + window verdict + report + commits) per the original iter43 plan — all gated on owner.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| This plan is AUDIT-ONLY — zero code changes, zero relaunches, zero merges | Owner: "i never told you to fix anything" — the unapproved fixes must be reviewed before any further action |
| Audit against call `532d92727e0f` ONLY (the single T6 call) | It is the only live data on the iter43 branch; T6's remaining 2 calls not yet run |
| EOT params stay at A (0.6/0.7/2500) until T7 | T7 is data-gated by design; this audit does not decide it |
| The T4 prompt changes (Offer/contact_details), s6 scenario, delivery speeds are OUT of this audit's scope unless the log contradicts them | They were approved work; this audit covers latency/telemetry claims + the unapproved fixes |
| `research/` findings stay gitignored and uncommitted | Repo doctrine: evidence never tracked in git |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Ruling on the unapproved `374318b` (keep / revert / rework) | Julio, in the review session — the audit only produces findings |
| Whether the old `:8007` log of call 532d (PID 1081793) was preserved anywhere | It was overwritten by the relaunch — check `/tmp/opencode/` for rotated copies; if gone, raw events are unrecoverable (aggregates already extracted, see Architecture) |
| 2 more owner live calls (T6 continuation) | Julio drives from the Mac via tunnel after the review |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12). Pinned: langchain-openai **1.6.0**, langgraph **1.2.11**, langfuse **4.15.1**, websockets **16.1.1**, pytest **9.1.1**, pydantic **2.13.5**, pydantic-settings **2.15.0**, httpx **0.28.1**, fastapi **0.141.1**, tiktoken (model encoding `gpt-5.4`).
- Branch under audit: `engine/iter43-eot-cache-askgate` in worktree `/tmp/opencode/wt-iter43` (HEAD `374318b`; base `f5c0912`).
- Live data: aggregates extracted from `/tmp/opencode/uvicorn_8007_iter43.log` BEFORE the relaunch overwrote it. If the raw log is gone, re-extraction is impossible — verify file presence first (audit task A0).
- Live server (do NOT restart): `127.0.0.1:8007`, PID expected **2324149**, cwd `/tmp/opencode/wt-iter43`, env `FIRST_TURN_LITE=true` + `CARTESIA_SPEED=1.12`.
- Token counter reference: OpenAI-side tokenization is NOT tiktoken-identical — all tiktoken numbers are approximations (the `2688 vs 2784` floor gap is within this uncertainty).
- Services NEVER touched: `:8000/:8001/:8002/:8003/:8005`, live agent IDs, `slots.db`, Cal.com event `3801235` (no test bookings exist from this branch — none were made).

## Architecture (one block)
```
call 532d (23:30:27-23:32:18, 7 reported turns)
  │  e2e p50 1939 (+49%) · TTFT p50 1870 (+56%) · head_start≈0 on 4/7
  │  cache_read: 0 (turn2) → 2688 flat (turns 3-5) → 3712 (Discovery)
  ▼
AUDIT QUESTIONS (each = one task below):
  Q1 lite head 16,453 tok (kb=True inlines KBs)? ──▶ A1 re-measure both heads via _lite_head()/static_head()
  Q2 greeting prewarm raced kb_store resolve?    ──▶ A2 check resolve ordering + session.start() line numbers
  Q3 head byte-stable across live rounds?        ──▶ A3 compare static_head cache + probe, NOT live bytes
  Q4 tail position caps the cached prefix?       ──▶ A4 read message layout in state_node (code read only)
  Q5 2688 = tools+2000-head-tok (or tiktoken artifact)? ──▶ A5 recompute, state the uncertainty plainly
  Q6 tests broke from .env FIRST_TURN_LITE leak? ──▶ A6 Settings env_file precedence + git history of .env
  Q7 Langfuse 500 transient + data redundant?    ──▶ A7 exporter code + json_logs line check
  Q8 unapproved 374318b correct/minimal/safe?    ──▶ A8 diff review + suite result on record (224)
OUTPUT: findings table (CONFIRMED / REFUTED / UNCERTAIN) + keep/revert recommendation per fix — NO code changes
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_iter43_audit_latency_claims.md` | this plan | NEW (uncommitted until owner reviews) |
| `/tmp/opencode/wt-iter43/diallux/graph/builder.py` (`_lite_head` ~line 426, `_history_window` ~line 457, prewarm ~line 179-235, state_node messages ~line 600-660) | READ ONLY | — |
| `/tmp/opencode/wt-iter43/diallux/config.py` (line 31-33 env_file, knobs ~line 54-76) | READ ONLY | — |
| `/tmp/opencode/wt-iter43/diallux/media/session.py` (start() ~line 170-195, `_on_eager_eot`, `_on_eot`, `_late_turn_report`) | READ ONLY | — |
| `/tmp/opencode/wt-iter43/diallux/graph/llm.py` (`warm()`, `_warm_llm`) | READ ONLY | — |
| `/tmp/opencode/wt-iter43/tests/test_iter32_gate.py` (SETTINGS line ~31) | READ ONLY (review the hermetic edit) | — |
| `/tmp/opencode/wt-iter43/.env` (FIRST_TURN_LITE removed by agent) | READ ONLY | — |
| `/tmp/opencode/uvicorn_8007_iter43.log` (may be the POST-relaunch file) | READ ONLY | — |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter43-eot-firstturn/01_telemetry_and_live_calls.md` | READ ONLY (review the agent's audit writeup) | — |

## Deploy Rules
- **NO deploys, NO restarts, NO code edits, NO test runs against live services, NO bookings.** Read-only commands only (`git show/diff/log`, `grep`, `sed -n`, `cat /proc/<pid>/environ`, `curl /health` and `/mic` GETs).
- `:8007` (PID 2324149) is LIVE for owner testing — never `kill`, never `lsof | xargs kill`, never relaunch.
- Never touch `:8000/:8001/:8002/:8003/:8005`, live Retell agent IDs, `slots.db`, Cal.com event `3801235`.
- LAW 0 stands: the unapproved commit `374318b` stays UNPUSHED; no merge of `engine/iter43-eot-cache-askgate` anywhere without Julio's explicit say-so.
- Exception: `curl -s http://127.0.0.1:8007/health` and `/mic` GETs are allowed (read-only health checks already in use).

## Tasks (in order)

### A0 — Confirm what raw evidence still exists
Goal: establish whether the call-532d raw log survived the relaunch (it determines how much can be re-verified vs taken from the extracted aggregates).
Files: `/tmp/opencode/` listing, `/tmp/opencode/uvicorn_8007_iter43.log` head.
Commands (full):
```bash
ls -la --time-style=full-iso /tmp/opencode/ | grep -iE "uvicorn|iter43" 
head -5 /tmp/opencode/uvicorn_8007_iter43.log
grep -c "532d92727e0f" /tmp/opencode/uvicorn_8007_iter43.log || echo "call-532d lines: 0 (log rotated)"
```
Dependencies: none.
Verification: report (a) whether any file still contains `532d92727e0f` lines, (b) current log's first timestamp + serving PID. If the raw log is gone, every claim below is audited against code + extracted aggregates only — state that explicitly in each finding.

### A1 — Re-measure the lite-head weight claim (16,453 → 1,648 tokens)
Goal: independently reproduce the agent's "kb=True inlines KBs" measurement on the CURRENT branch code (which already contains the fix — so measure BOTH variants).
Files: `/tmp/opencode/wt-iter43/diallux/graph/builder.py` (lines 426-436).
Commands (full):
```bash
cd /tmp/opencode/wt-iter43 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python - <<'EOF'
import sys, tiktoken
from diallux.config import Settings
from diallux.graph.builder import CallRuntime
from diallux.graph.subst import Substitutor
from pathlib import Path
import json
llm_json = json.loads(open('/tmp/opencode/wt-iter43/agent/llm.json').read())
enc = tiktoken.encoding_for_model("gpt-5.4")
rt = CallRuntime(Settings(), llm_json)
fixed = rt._lite_head()
general = Path('/tmp/opencode/wt-iter43/diallux/prompts/general_prompt.md').read_text()
buggy = rt.subst.subst(general, {}, kb=True)
print("buggy(kb=True) tokens:", len(enc.encode(buggy)))
print("fixed(kb=False) tokens:", len(enc.encode(fixed)))
EOF
```
Dependencies: A0.
Verification: output shows buggy ≈ 16.5k AND fixed ≈ 1.6k. Finding is CONFIRMED only if both numbers reproduce. Also read `subst()` (`/tmp/opencode/wt-iter43/diallux/graph/subst.py`) and state in one sentence what `kb=True` does (inline-expand `##slug-kb##` markers) with the exact function/line cited.

### A2 — Check the greeting-prewarm vs kb_store race claim
Goal: verify whether the prewarm CAN send different head bytes than the hot path (expand_kb mismatch), by reading `_resolve_kb_store` + `_warm` + `session.start()` ordering — no live replay.
Files: `builder.py` lines 336-345 (`_resolve_kb_store`), 179-235 (prewarm block), `session.py` lines 170-195 (start order).
Commands (full):
```bash
sed -n '336,345p' /tmp/opencode/wt-iter43/diallux/graph/builder.py
sed -n '170,195p' /tmp/opencode/wt-iter43/diallux/media/session.py
grep -n "expand_kb = " /tmp/opencode/wt-iter43/diallux/graph/builder.py
```
Dependencies: A0.
Verification: finding states (a) whether `_resolve_kb_store` latches `None` on first failure (quote the latch lines), (b) exact start() order: `warm_rag` line vs `warm_prompt_cache` line vs greeting `speak` line, (c) whether `_warm` and `state_node` compute `expand_kb` identically (quote both lines). CONFIRMED only if a code path exists where prewarm uses `expand_kb=True` while the hot path uses `False` (or vice versa). Note the process-wide `get_kb_store` singleton question as UNCERTAIN if unreadable from code alone.

### A3 — Check the head-stability claim (byte-identical round-to-round)
Goal: verify `static_head()` caching + `strip_kb_markers` determinism from code (the agent's FakeLLM probes are NOT live evidence — say so).
Files: `builder.py` lines ~400-424 (`static_head`), `rag.py` `strip_kb_markers` (~line 388).
Commands (full):
```bash
sed -n '400,424p' /tmp/opencode/wt-iter43/diallux/graph/builder.py
grep -n "def strip_kb_markers" -A 4 /tmp/opencode/wt-iter43/diallux/rag.py
grep -n "_TOOLS_CACHE\|_tools_cache\[" /tmp/opencode/wt-iter43/diallux/graph/builder.py | head
```
Dependencies: A0.
Verification: CONFIRMED only if (a) `static_head` caches per `(state, expand_kb)` with no per-round inputs, (b) `strip_kb_markers` is a pure function, (c) `_tools_cache` keying is stable. Explicitly mark the agent's probe-based "head stable in live" inference as UNCERTAIN (probes used FakeKB/FakeLLM, not live bytes).

### A4 — Check the tail-position cache-cap claim
Goal: verify the message layout claim (`[head] + history + [tail]` with tail AFTER history) and whether the tail re-renders per round (frozen_state_block vs live render).
Files: `builder.py` state_node messages construction (~line 600-660) + tail computation (~line 490-560) + `frozen_state_block` setting.
Commands (full):
```bash
grep -n "messages = " /tmp/opencode/wt-iter43/diallux/graph/builder.py
grep -n "frozen_state_block" /tmp/opencode/wt-iter43/diallux/config.py /tmp/opencode/wt-iter43/diallux/graph/builder.py | head
sed -n '640,660p' /tmp/opencode/wt-iter43/diallux/graph/builder.py
```
Dependencies: A0.
Verification: CONFIRMED only if messages are literally `[head] + window + [tail]` AND the tail is re-rendered per round (or frozen — state which and its cache implication in one sentence). The OpenAI-side caching behavior itself is UNVERIFIABLE from here — mark it UNCERTAIN and say what live evidence would settle it (per-round `cache_creation` + message hashes, not currently logged).

### A5 — Check the `2688 = tools + 2000 head tokens` arithmetic
Goal: recompute the floor numbers; state the tiktoken-vs-OpenAI-tokenizer uncertainty honestly.
Files: none new (uses `agent/llm.json`, `diallux/prompts/Intake.md`, `general_prompt.md`).
Commands (full):
```bash
cd /tmp/opencode/wt-iter43 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python - <<'EOF'
import tiktoken, json
from diallux.graph.llm import build_tool_schemas
from diallux.graph.subst import Substitutor
from diallux import rag as ragmod
enc = tiktoken.encoding_for_model("gpt-5.4")
llm_json = json.loads(open('agent/llm.json').read())
states = {s["name"]: s for s in llm_json["states"]}
subst = Substitutor("diallux/knowledge_base")
general = open('diallux/prompts/general_prompt.md').read()
intake = open('diallux/prompts/Intake.md').read()
head = ragmod.strip_kb_markers(subst.subst(general + "\n\n" + intake, {}, kb=False))
tools = build_tool_schemas(states["Intake"], llm_json.get("general_tools", []),
                           lambda t: subst.subst(t, {}, kb=False), {})
print("stripped head:", len(enc.encode(head)), "| tools:", len(enc.encode(json.dumps(tools))))
EOF
```
Dependencies: A0.
Verification: CONFIRMED only if head+tools ≈ 2784 (then explain the 96-token gap to 2688 or mark it UNCERTAIN). State plainly: tiktoken ≠ OpenAI's counter, so ±5% is measurement noise, not signal.

### A6 — Check the `.env` leak claim (20 tests + eval broke)
Goal: verify pydantic-settings precedence (init kwargs > env vars > dotenv > defaults) and the `.env` git history (was FIRST_TURN_LITE added by the agent in T5?).
Files: `config.py` lines 31-33, `.env` git history (note: `.env` is gitignored — check `git log` will NOT show it; verify via the claim + `grep`).
Commands (full):
```bash
sed -n '31,33p' /tmp/opencode/wt-iter43/diallux/config.py
grep -n "FIRST_TURN_LITE" /tmp/opencode/wt-iter43/.env || echo "absent from .env (agent removed it)"
git -C /tmp/opencode/wt-iter43 show 60df3c0 --stat | head -20
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -c "
from diallux.config import Settings
print('worktree-CWD default:', Settings(openai_api_key='t', retell_api_key='t', langfuse_enabled=False).first_turn_lite)
" 2>/dev/null
```
Dependencies: A0.
Verification: CONFIRMED only if Settings reads `.env` from CWD (env_file=".env") AND the failing tests constructed Settings without `first_turn_lite=` override. Quote the `test_iter32_gate.py` SETTINGS line before/after (`git show 374318b -- tests/test_iter32_gate.py`).

### A7 — Check the Langfuse OTEL explanation
Goal: verify the exporter is OTLP-HTTP with retry, and the json_logs redundancy.
Files: tracer/observability module (find the exporter import), one sample json_logs line.
Commands (full):
```bash
grep -rn "otlp\|OTLP\|trace_exporter\|retry" /tmp/opencode/wt-iter43/diallux/observability/*.py | head
ls /tmp/opencode/wt-iter43/tests/llm2llm/json_logs/ 2>/dev/null | tail -3 || find /tmp/opencode/wt-iter43 -name "json_logs" -maxdepth 3
```
Dependencies: A0.
Verification: CONFIRMED only if the exporter import + retry/backoff is in OUR code or the pinned `opentelemetry-exporter-otlp` version's documented behavior (cite version), AND a redundant log line exists for the same turn data. Otherwise UNCERTAIN.

### A8 — Review the unapproved `374318b` for keep/revert
Goal: produce the keep/revert recommendation with exact blast radius — no action taken.
Files: `git show 374318b` (full, 2 files, 6 insertions).
Commands (full):
```bash
git -C /tmp/opencode/wt-iter43 show 374318b
git -C /tmp/opencode/wt-iter43 log --oneline origin/engine/iter43-eot-cache-askgate..HEAD 2>/dev/null || echo "(branch unpushed — confirm no remote tracking)"
curl -s -m 5 http://127.0.0.1:8007/health
```
Dependencies: A1-A7 (recommendation cites their findings).
Verification: output is a table: each hunk of `374318b` → KEEP / REVERT / REWORK + one-line reason + what breaks if reverted (e.g., reverting the lite fix restores the 16.5k-token turn-1; reverting the .env move re-breaks 20 tests). Also state: the relaunch PID change (1081793→2324149) and whether the T6 call-532d log is still reviewable (from A0).

## Validation Plan (end-to-end)
1. A0 reports raw-evidence status (log present vs rotated).
2. A1-A7 each end in one of CONFIRMED / REFUTED / UNCERTAIN with the exact command output or line citation backing it.
3. A8 delivers the keep/revert table for `374318b` + a go/no-go note for the two remaining T6 calls (is :8007 in a reviewable state?).
4. The review session reads ONLY this plan's findings table — no code is touched, nothing is merged, `374318b` stays unpushed.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Any fix to the tail-placement cache cap (A4) | Owner forbade fixes; finding only |
| Any change to EOT params (T7 candidate A/B/C/D) | Data-gated T7 decision, needs 2 more live calls first |
| The 2 remaining T6 owner calls | After the review, not during the audit |
| Live booking+cancel endpoint test (Cal.com 3801235) | Proposed earlier, never approved; separate owner gate |
| `transition_to_*` in `_MECHANICAL_RE`, battery root-causes, Postgres memory, model swap | Already deferred in the iter43 plan; unchanged |
| Merging `engine/iter43-eot-cache-askgate` or pushing `374318b` | LAW 0 — owner say-so only, explicitly not in this plan |
