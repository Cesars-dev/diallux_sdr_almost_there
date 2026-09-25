# PLAN — v5 iter38: turn-lifecycle memory/latency fix (eager adopt + hangup + cap)

## Meta
- Date: 2026-09-09
- Project root: `/home/julio/projects/clean_diallux_SDR` (fork = main workspace).
- Branch: `engine/iter38-memory-latency-fix` ← `engine/iter37-browser-mic-tts` (`4e72200`).
- Procedure: **Surgeon framework** — audit/plan/cross-ref/master live in
  `research/surgeon/iter38-memory-latency-fix/01_audit.md … 04_master_plan.md`.
  This plan file is the repo-facing summary; the master plan is the executable one.
- Status: EXECUTING (owner pre-approved execution on a new branch, 2026-09-09).

## Root causes being fixed (from the iter37 autopsy evidence)
Disaster call `baccf630adfd` (2026-09-09, 97 turn indexes / 11 min, 8s latency
spikes, no hangup, "You there?" zombie tail):
1. **B1 (PT-33, critical):** `_on_eot` (session.py:239) cancels the running eager
   turn and re-runs it → user utterance appended to history TWICE (~40 duplicates),
   graph ran 2×/utterance (even-only turn indexes), doubled cost+latency.
2. **B2 (critical, iter37 port regression):** `_late_turn_report` (session.py:371)
   references `config`, a local of `_run_turn` → NameError swallowed by
   `except: pass` → post-goodbye hangup never fires, `_ended` never set, V5
   delivery profiles frozen. Explains turns 96/97 zombies + 44s silent tail.
3. **B3 (PT-34, high):** no hard turn cap → 97-turn drift possible.
4. **B4/B5/B6 (medium/low):** barge_in flag lost on clock swap;
   `tts_first_to_audio_out_ms` structurally ~0; no idempotent user-append guard.

## What worked (evidence — do NOT touch)
- PhaseB chain booked for real: `booking_uid e24H7HdM6URJiFwxBx81eh`, "thursday at 2".
- iter32 silent-mechanical gate: forced-speech round produced the goodbye after
  2 blocked silent `end_call`s.
- end_call truth gate, one-trip routing, C3 static prefix, history_window=16.

## Tasks (in order)
| # | Task | Files |
|---|---|---|
| T1 | F2 hangup fix (`_thread_config` + logged except) | `diallux/media/session.py` |
| T2 | F1 eager-adopt on EOT + resumed-race guard | `session.py` |
| T3 | F4 ingest idempotent user-append | `diallux/graph/builder.py` |
| T4 | F5 barge_in carry + F6 real audio_out stamp | `session.py` |
| T5 | F3 turn cap + graceful close + F7 env | `config.py`, `session.py`, `.env.example` |
| T6 | New tests `tests/test_iter38_turn_lifecycle.py` (7) | tests |
| T7 | Suite green (161), commit per fix | branch |
| T8 | Battery ladder + first-13 + cancel test bookings + cache_read proof | research/ |
| T9 | Report + ITERATIONS.md ledger + ASK JULIO (merge + live :8005 re-test) | docs |

## Validation Plan
1. `pytest tests -q` green after every fix; full suite 161 passed.
2. Battery proves graph behavior unchanged (only the F4 append guard touches graph).
3. All test bookings cancelled (event 3801235 is REAL).
4. Post-battery trace check: `cache_read > 0` on repeat-state generations.
5. Owner-gated live re-test: hangup after goodbye, no duplicated user turns,
   latency p50 back to ~1.3s band.

## Deploy Rules
- Never touch `:8001–:8003`, old `:8000` (pid 2659243), live agents
  (`agent_f305…`, `agent_1698…`, `agent_87e4…`), Cal.com event 3801235 bookings.
- App on :8005 (pid 2099198) untouched until the owner-approved live re-test.
- No merges without Julio's say-so (LAW 0).

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| TTFT prefix / model work | c3 already merged; cache_read proof first |
| Twilio deploy | blocked on TWILIO keys (separate track) |
| RAG scope / KB changes | no evidence of failure in this call |
