# PLAN — v5 iter56: state→delta payload relocation (cache fix + {{dv}} rendering + full history)

## Meta
- Date: 2026-09-18
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: relocate the volatile state-block from the cached prefix into the post-history delta, strip literal `{{var}}` tokens from the static head, and switch to full append-only history — making the engine's prompt cache climb with history like the deployed Retell agent, and fixing the {{dv}} blindness that drives the verbatim-question loop (PT-53/PT-55).
- Status: **APPROVED BY OWNER 2026-09-18 ("lets do this iter56 plan on a new session") — a FRESH execution session starts here. Code is ALREADY AUDITED — the executing agent must NOT re-audit or re-derive; it loads context (this plan + the master plan) and executes.**
- Branch: NEW `engine/iter56-state-delta-payload` cut from `engine/iter55-tts-era-turn1-ammo` @ `7ac9879` (iter55 paused at C1 — its observability spans are the before/after instrument).
- Implementation spec (airtight, surgeon-verified): `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter56-state-delta-payload/04_master_plan.md` — this plan operationalizes it.

## Compaction Context (session 2026-09-18 — pin, do not re-derive)

- **Trigger:** two live browser-mic voice calls on the iter55 engine (:8020, isolated) were conversational disasters (verbatim re-asking, 7 question variants in Intake) while latency was GOOD. Owner ordered engine-vs-deployed comparison; verdicts landed in `/home/julio/projects/clean_diallux_SDR/research/surgeon/retell-payload-truth/T0_session_verdict.md`.
- **Disease 1 (cache):** engine cache_read only ever takes {0, 1664, 2688, 3712, 4736} — flat floors, never climbing. Two mutators: (1) state-block re-freezes EVERY turn at ingest (`builder.py:2187-2192`) and sits PRE-history (`builder.py:1466-1471`, `tail_before_history=True` config.py:154) → everything after `[tools][head]` re-bills; (2) the 16/8 history window slides (`builder.py:1345-1359`, config.py:60/65). Waste ~1,000-1,500 uncached tok/round median, ~60-90k/call.
- **Disease 2 ({{dv}} blindness):** `static_head` (`builder.py:1292-1324`) renders `{{var}}` LITERAL (`dvs={}` for byte-stability) → the model reads dead placeholders like "`{{callback_number}}` may already hold the number" and walks Intake.md's scripted questions. Deployed Retell substitutes real values every turn.
- **Deployed ground truth (T2, decoded):** `/home/julio/projects/clean_diallux_SDR/research/surgeon/retell-payload-truth/02_payload_anatomy.md` — deployed = `[system: general + current state prompt, dvs substituted][FULL append-only event history]`; tools/results/transitions/errors are transcript entries; V7.9 runs KB-free (inline); 0 re-asks in 226 sampled turns; full history 113-133 events, never trimmed.
- **API pull (T3) done:** 12 V7.8/V7.9 dashboard chats on disk in `/home/julio/projects/clean_diallux_SDR/research/transcripts/` (3 were fetched via `GET https://api.retellai.com/get-chat/{chat_id}` with `RETELL_API_KEY`). "Jason" real-lead chats DO NOT EXIST via API — all 370 chats across both Retell workspaces are `api_chat` persona calls.
- **Owner architectural mandate:** "the delta should always contain main plus state — mandatory." Verified mapping: prefix `[tools][main head, {{var}} stripped][FULL history]` / delta (last message) `[state: live dvs][pinned-KB][fresh retrieval][ack directive when needed]`.
- **iter55 state:** PAUSED at C1 (`7ac9879`): C0 (Rourke fixture, 333), C0.5 (hitl_ping.py), C1/T0 observability (suite 346; chat trace `d28d7d56b53a`, voice trace `cc29eed37db9`). NOT done: C2 (lite-cap split), T1-T7. **Breadcrumb: iter55 leftovers are re-taken AFTER iter56 lands, re-scoped onto the fixed payload** (see 04_master_plan.md §iter55 BREADCRUMB — T2/T3 turn-1 ammo survive unchanged; T1 warm table re-baselines; floors 2688/3712 assumptions obsolete).
- **Surgeon package:** `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter56-state-delta-payload/` — 01_audit.md (code truth @ 7ac9879, findings F-01…F-09), 02_action_plan.md (fix spec with code patterns), 03_cross_reference.md (CR-1…CR-8 resolved; P1 `_warm` tail at builder.py:476-499 verified, P2 delta order pinned state→RAG→directive), 04_master_plan.md (execution table C0→C3, gates G1-G6, rollback matrix).
- **Cal.com anomaly (open, PT-56):** Rourke run booking uid `qeTqHuZ1EDzH8bxEdhPQ6H` resolves to an OLD cancelled Sep-4 booking; 0 upcoming found. Verify + cancel if real (event 3801235 is REAL).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Fix architecture: state-block → post-history delta; `{{var}}` → "CURRENT CALL STATE" anchor text in head; `history_window=0` (full history) | Owner mandate + T2 deployed anatomy + T0 verdict; kills both cache mutators AND the dv blindness in one relocation |
| Three revert knobs: `state_in_delta=True`, `head_strip_vars=True`, `history_window=0` | One architectural variable, independent reverts (rollback matrix in 04) |
| Delta composition order: state-block → RAG/pinned → ack directive | Directive is imperative = final; state anchors adjacent to head pointer (CR-2/P2) |
| `_warm` tail gated off under `state_in_delta` (builder.py:477) | Warm must prefill the NEW prefix `[tools][head][history]`; delta never rides cache (CR-4/P1, code-verified) |
| iter56 cuts FROM iter55 branch @ `7ac9879` | Keeps the C1 observability instrument on the fix branch — the before/after proof tool |
| iter55 C2/T1-T7 = re-taken after iter56, re-scoped | Owner direction 2026-09-18 ("execute iter56 first, re-take iter55 with fixed cache/prompt/dv structure") |
| Freeze machinery (`frozen_state_block`) + non-live RAG tail: inert-marked, NOT deleted | Revert paths stay intact; deletion only after a merged iteration proves the layout |
| Warm machine structural simplification: DEFERRED | One variable per iteration (SOP) |
| Telegram ping BEFORE every owner ask | Owner directive 2026-09-18 ("notifs before I answer"); bot on file in `/home/julio/projects/video_strategy/.env` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`); pattern `send_telegram()` in `/home/julio/projects/video_strategy/execution/clients.py` |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| iter56 branch approval (this plan) | Owner — ping fires before the ask |
| Rourke-run booking uid reality (PT-56) | `/book-livecall` webhook's Cal credential scope or owner's Cal dashboard |

## Environment & Dependencies
- Worktree protocol (same as iter55): `git -C /tmp/opencode worktree add /tmp/opencode/wt-iter56 -b engine/iter56-state-delta-payload engine/iter55-tts-era-turn1-ammo` then `ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter56/engine/.venv` and `cp /home/julio/projects/clean_diallux_SDR/engine/.env /tmp/opencode/wt-iter56/engine/.env`
- Sanity: `git -C /tmp/opencode/wt-iter56 log --oneline -1` must print `7ac9879`
- Python: `/tmp/opencode/wt-iter56/engine/.venv/bin/python` (3.12.3; NEVER the pip script — always `<venv>/bin/python -m pip`)
- Suite: `cd /tmp/opencode/wt-iter56/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → expect **346 passed**
- Langfuse: `cd /tmp/opencode/wt-iter56/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/lf.py health`
- Ledger import: `cd /home/julio/projects/clean_diallux_SDR/engine && .venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run <name> --commit <sha>` (MAIN checkout, never the worktree — ROOT resolves wrong)
- NO sqlite3 CLI, NO `rg` on this box — `.venv/bin/python -c "import sqlite3…"` and the grep tool
- Key files to edit (all under `/tmp/opencode/wt-iter56/engine/`): `diallux/graph/builder.py` (lines 486, 476-499, 1292-1324, 1466-1471, 1760-1790, 1786-1790, 2187-2192), `diallux/config.py` (lines 60, +new knobs), `tests/` (layout pins — enumerate via grep "CURRENT CALL STATE|tail_before_history|state_block|history_window")
- Evidence dir: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter56-state-delta-payload/` (create at C3)

## Architecture
```
BEFORE (@ 7ac9879)                              AFTER (iter56)
┌────────────────────────────────────┐          ┌────────────────────────────────────┐
│ [tools]                            │ cache    │ [tools]                            │ cache
│ [head: {{var}} LITERAL]            │ dies at  │ [head: {{var}} → "CURRENT CALL     │ climbs
│ [state-block (mutates EVERY turn)] │ [tools]  │   STATE" anchor]                   │ with
│ [history: 16/8 window (slides)]    │ [head]   │ [history: FULL, append-only]       │ history
│ [delta: RAG | ack directive]       │          │ [DELTA: state(live dvs)+pinned+RAG │
│                                    │          │  +ack directive] ← re-bills anyway │
└────────────────────────────────────┘          └────────────────────────────────────┘
  floors {2688,3712}, sawtooth                    monotonic cache_read growth
  {{dv}} blind → 7-variant re-ask loop           values visible every round → 0 re-asks
```

## File Map
| File (absolute) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter56/engine/diallux/config.py` | +`state_in_delta: bool = True`, +`head_strip_vars: bool = True`, `history_window: 16 → 0` | E |
| `/tmp/opencode/wt-iter56/engine/diallux/graph/builder.py` | state_node tail→delta composition (1466-1471, 1760-1790); ack delta (1786-1790); `_warm` tail gate (476-499); `static_head` strip pass (1292-1324); ingest freeze inert-gate (2187-2192); comment rewrites (486, 1489, 1712-1745) | E |
| `/tmp/opencode/wt-iter56/engine/tests/` | layout/head-strip/window/ack/warm-parity pin updates (extend existing tests) | E |
| `/tmp/opencode/wt-iter56/tasks/surgeon/iter56-state-delta-payload/` | surgeon package committed at C0 (rides the branch) | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter56-state-delta-payload/01_report.md` | battery report + gates evidence | N |
| `/home/julio/projects/clean_diallux_SDR/engine/ITERATIONS.md` | iter56 ledger line (at closeout, on branch) | E |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-53/PT-55 flips at closeout | E |

## Deploy Rules
- Branch discipline per LAW 0 v3: code commits on `engine/iter56-state-delta-payload` only; NO merges without owner say-so; `scripts/keyhound` before any push
- NO services started from the fork except owner-ordered test runs (foreground uvicorn, free port, `127.0.0.1` bind) — same :8020-style isolation as the iter55 voice tests if a voice round is needed for G1/G3
- Live infra read-only: :8000-:8003 (ORIGINAL workspace serves), never bind/restart
- Never touch production agents (`agent_16985b5d087e56c35141983396` voice, `agent_f305981ef7b5ce312c1c899bbf` current chat, `agent_87e4d5f08475e5bc558b2f390f` legacy)
- Cancel ALL Cal.com test bookings after the battery (event 3801235 is REAL)
- Happy-path gate first; `--no-happy-gate` only on purpose

## Tasks (in order)
## SESSION START PROTOCOL (fresh agent — execute in order, no memory assumed)
1. Read this plan fully.
2. Read THE implementation spec — `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter56-state-delta-payload/04_master_plan.md` (airtight, preflight-resolved). Its §Execution sequence (C0→C3), §Gates (G1-G6) and §iter55 BREADCRUMB are binding. T0/T1 of this session = RUN THE MASTER PLAN verbatim — do NOT re-audit code, do NOT re-derive findings (01_audit/02_action_plan/03_cross_reference in the same folder are reference-only).
3. Skim for grounding only: `/home/julio/projects/clean_diallux_SDR/research/surgeon/retell-payload-truth/T0_session_verdict.md` + `/home/julio/projects/clean_diallux_SDR/research/surgeon/retell-payload-truth/02_payload_anatomy.md`.
4. Repo law: `/home/julio/projects/clean_diallux_SDR/AGENTS.md` (LAW 0, ledger SOP, traps).
5. Verify environment: worktree protocol (Environment section) → `git log` = `7ac9879` → suite 346 → `scripts/lf.py health`.
6. HITL: Telegram ping BEFORE every owner ask (bot on file, `send_telegram()` pattern in `/home/julio/projects/video_strategy/execution/clients.py`).

## Tasks (in order) — RUN THE MASTER PLAN
All code detail lives in the master plan (§Execution sequence + §02_action_plan code patterns). The tasks below are the session skeleton with verification only.
### C0 — Branch + surgeon package
Goal: cut the branch, commit the 4 surgeon docs.
Commands: worktree protocol above; COPY the package into the worktree first — `mkdir -p /tmp/opencode/wt-iter56/tasks/surgeon && cp -r /home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter56-state-delta-payload /tmp/opencode/wt-iter56/tasks/surgeon/` — then `git -C /tmp/opencode/wt-iter56 add tasks/surgeon/iter56-state-delta-payload && git -C /tmp/opencode/wt-iter56 commit -m "iter56 preflight: surgeon package (audit, action plan, cross-reference, master plan)"`
Verification: `git -C /tmp/opencode/wt-iter56 log --oneline -2` = C0 + `7ac9879`; suite 346.
### C1a — Relocation (state→delta + full history + warm gate + comments + tests)
Goal: the payload moves; old layout reachable via `STATE_IN_DELTA=false`. Edit points + code patterns: master plan §Execution sequence C1a / 02_action_plan §C2.2-C2.4, C2.6, C3.
Verification: layout test green (heavy round = `[head][history][delta(state+rag)]`, ack delta = state+directive, revert = old order); suite 346.
### C1b — Head strip
Goal: `{{var}}` → `CURRENT CALL STATE` in the head, byte-stable. Pattern: 02_action_plan §C2.1.
Verification: head zero `{{` when on; literals when off; suite 346.
### C2 — Observability fields
Goal: `state_in_delta` on round spans; `delta_tokens` on the round usage log line. Pattern: 02_action_plan §C2.7.
Verification: one chat run (Rourke) shows fields in Langfuse; suite 346.
### C3 — Battery + gates + report + ASK
Goal: prove the fix with the iter55 instrument. Battery order + gate definitions: master plan §Gates; ledger import command: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run <name> --commit <sha>` (run from the MAIN engine checkout, never the worktree).
Commands: `cd /tmp/opencode/wt-iter56/engine && set -a && . ./.env && set +a && .venv/bin/python tests/llm2llm/harness.py --personas Maria,Susan --rag --langfuse --max-turns 48` (+ 1 browser-mic voice run per iter55 :8020 protocol); ledger import; gates; cancel ALL Cal.com test bookings (event 3801235 is REAL).
Verification: **G1 cache_climb=0 regressions, G2 last≥first+1000, G3 TTFT in band, G4 zero literal `{{`, G5 zero re-asks, G6 suite 346** → report to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter56-state-delta-payload/01_report.md` + ITERATIONS.md line + PT-53/PT-55 flips → Telegram ping → **ASK JULIO** (merge gate).

## Validation Plan (end-to-end)
1. C0: branch tip = C0 on top of `7ac9879`; suite 346 green.
2. C1a/C1b: new layout pins + revert-path tests green; suite 346.
3. C2: Langfuse shows the new span fields on a smoke run.
4. C3: all six gates PASS with SQL/Langfuse citations in `01_report.md`; bookings cancelled; ping then ASK.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| iter55 C2 (lite-cap split) + T1-T7 | Re-taken after iter56 lands, re-scoped (breadcrumb in 04_master_plan.md) |
| Warm machine structural simplification | One variable per iteration |
| `frozen_state_block` / non-live RAG tail deletion | Revert paths; delete after production proof |
| PT-54 TTS-bleed echo | Separate disease (multi-round turn concat), separate fix |
| PT-56 booking uid anomaly | Services-side verification, not engine |
| Heating-UK line | Different agent, out of scope |
