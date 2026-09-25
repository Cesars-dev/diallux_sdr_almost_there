# PLAN — iter60: fix audit findings AUD-1..AUD-10 from the iter59 code audit

## Meta
- Date: 2026-09-21
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — apply the 10 fixes from `research/surgeon/iter59-kb-everywhere/04_code_audit.md` on a new branch off the iter59 build, pin each fix, write the fix report. NO other changes, NO deploy.
- Status: **PLAN ONLY (not started — awaits approval)**

## Compaction Context (session 2026-09-21 audit — pin, do not re-derive)

- **Project state:** iter59 (branch `engine/iter59-kb-everywhere-freshness` @ `6d13803`, base `db8e56f`, ONE commit, unmerged) built `rag_fire_mode` (eot|speech-window|round-sync|hybrid), KB-everywhere, semantic dedupe 0.90, transport prewarm + greeting phrase cache. Suite **398 passed** (368 baseline + 30 new pins; 7 old pins re-pinned). NOT deployed. T6 (owner live call) + T7 (closeout) open.
- **The audit (done, read-only):** `research/surgeon/iter59-kb-everywhere/04_code_audit.md` @ worktree `/tmp/opencode/wt-iter59`. Verdict: T3/T4 core solid; T5 has 2 blockers; hybrid consume has 1 HIGH + 1 MED. Owner commissioned the fix session (this plan).
- **The 10 findings (file:line are in the wt-iter59 tree; identical in the new wt-iter60 tree):**
  - **AUD-1 BLOCKER** — prewarm TTS `_drain` task (`/tmp/opencode/*/engine/diallux/media/prewarm.py:113-121`) is never cancelled on adoption; `get()` (prewarm.py:262-264) pops the dict only. `CartesiaTTS.connect(ws=…)` (`diallux/media/cartesia_tts.py:100-109`) starts a 2nd `recv()` → **websockets 16.1.1 (installed venv) raises `ConcurrencyError` on concurrent `recv()`** → the session's recv loop dies → **first call after every pool refill is mute**. Hermetic pins use fake WS so they can't catch it.
  - **AUD-2 BLOCKER** — `prewarm.py:192` `_PHRASE_CACHE[key] = _b64d("".join(chunks))` joins base64 STRINGS; mid-string `=` padding makes `b64decode` **silently discard everything after the first padded chunk** (auditor-proven: `b64decode("QUJDQUI=QUJDRA==")` → 5 bytes, expected 9). Greeting cache ≈ first chunk only → every call's greeting cut off. Fix: decode per chunk, join BYTES.
  - **AUD-3 HIGH (proven)** — `_consume_hybrid` (`diallux/graph/builder.py:1499-1581`): round 1 consume sets `_live_consumed[state]` to laneA's seq (builder.py:1574-1577); rounds 2+ of the SAME turn reject laneA (`seq > floor` fails, builder.py:1516-1519) → merged set = laneB only → KNOWLEDGE silently loses all refer-tag chunks on every tool round (booking chain), `degraded=False`. Proof: lane queries went `['the empathic mirror', 'my calls go to voicemail']` (round 1) → `['my calls go to voicemail']` (round 2).
  - **AUD-4 MED (proven)** — laneB has NO freshness check (builder.py:1520-1539; respawn only when `task_b is None or task_b.cancelled()`). A DONE laneB task from an EARLIER turn/visit is consumed as fresh. Proof: turn-1 `Booking|laneB` ("confirming the booking please") served `degraded=False` to turn-2's Booking round after a mid-turn transition. Key fact: `_live_msgs[f"{state}|laneB"]` (written at spawn, builder.py:1352) already holds the msg the current task was fired with — the freshness check can compare it to the round's `user_msg` with zero new bookkeeping.
  - **AUD-5 MED** — round-sync still fires a wasted "full" bg task at EOT/EagerEOT: `diallux/media/session.py` `_on_eot` dispatch (~lines 396-403) and `_on_eager_eot` dispatch (~lines 477-484) — the `else` branch catches round-sync; the round-sync consume (`builder.py:1429-1440`) never reads `_live_tasks`. Duplicate embed+pgvector per turn.
  - **AUD-6 MED** — semantic dedupe gate `if is_q and spoken_any and stem_window:` (builder.py:2247) and `if pending_is_q and spoken_any and stem_window:` (builder.py:2322) — `spoken_any` is the THIS-TURN flag `turn_spoke` (reset at ingest, builder.py:2617) → the FIRST spoken sentence of every turn is exempt from cross-turn re-ask detection. Master plan T4 specced "window non-empty" only. Undeclared deviation.
  - **AUD-7 MED** — `engine/scripts/live_sql.py:215-228`: the `rag` span INSERT drops `mode`/`degraded`/`await_ms` (no columns) → the T6 gates (degraded ≥90% false, await p50 ≤15/80 ms, lane-A landed ≥90%) are not SQL-computable from the ledger. Ledger: `research/surgeon/iter48-rag-truth/ledger.db` (sqlite, NO sqlite3 CLI on this box — use venv python).
  - **AUD-8 LOW** — `rag_fire_mode` (config.py:271) accepts any string; a typo silently runs eot-fires with speech-window consume semantics.
  - **AUD-9 LOW** — master plan T4 required a token-cost delta note; `02_build_report.md` §F has none. Fixed in the iter60 report (quantify: 4 freed states × ≤1600-char budget per heavy round).
  - **AUD-10 LOW** — `_render_from_raw` increments `_kb_stats` (builder.py:1217-1219) and is called by lane tasks at land time (builder.py:1380) AND by the hybrid consume (builder.py:1572) → hybrid inflates rag_turns/rag_chars ~2-3×. Observability only.
- **Verified-safe facts (do not re-check):** eot/speech-window/round-sync/hybrid fire/skip matrix all correct except AUD-5; revert surfaces exact (eot = iter58, all flags off = iter58); the 7 re-pinned old pins are correct and must stay green; dedupe FIFO/embed-fallback safe; phrase-cache KEY construction is byte-correct both sides (same `resolve_delivery(settings,"begin")`, same `begin_message` source via `diallux/state.py:54-56`); mic page schedules audio on an AudioContext playhead (cache burst is browser-safe); `_PHRASE_CACHE`/`pool` are module-level per-process (serve_voice.sh = single uvicorn, no --workers).
- **Pinned facts:** websockets 16.1.1 `Connection.recv` raises `ConcurrencyError` when two coroutines call recv concurrently (docstring + `Assembler.get`). `base64.b64decode` non-strict discards bytes after mid-stream padding. pydantic v2 + pydantic-settings in the venv (`field_validator` available). Deployed transport `browser`; `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` in the worktree `.env`.
- **Key paths:** audit report `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/04_code_audit.md`; build report `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/02_build_report.md`; master plan `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter59-kb-everywhere-freshness/04_master_plan.md`.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Branch `engine/iter60-audit-fixes` from `6d13803` (the iter59 head, unmerged) — NOT from main | fixes must sit on top of the audited tree; iter59 merge is a separate owner decision |
| All 10 fixes in ONE iteration/branch/commit-series, one session | owner commissioned "fix AUD-1 to AUD-10"; each fix is small and local (audit §2 sketches) |
| AUD-3 fix = per-turn merged-set stash in `_consume_hybrid` (reuse on same-turn rounds) + AUD-4 fix = msg-guard on laneB acceptance/respawn | exact shapes below; no redesign of the seq mechanism |
| AUD-10 fix = move `_kb_stats` increments out of `_render_from_raw` into `_live_retrieve` + `_consume_hybrid` | preserves iter58 counting semantics for eot/speech-window/round-sync; counts hybrid once per consume |
| AUD-6 fix = drop `spoken_any` from the two semantic gates (keep `stem_window` non-empty gate) | the non-empty window already proves the call has spoken; empty window (first question ever) behaves identically to today |
| AUD-7 fix = add `mode TEXT, degraded INTEGER, await_ms REAL` to the ledger `rag` table + INSERT, with an ALTER-based migration for the existing db | T6 gates become SQL-computable per SOP |
| AUD-8 fix = pydantic `field_validator` whitelist (fail-fast at startup) | cheapest guard; server refuses to start on a typo |
| All 9 new pins in ONE new file `tests/test_iter60_audit_fixes.py` | per-iteration pin convention; zero edits to existing test files; expected suite **407 passed** |
| AUD-9 = a quantified note in the iter60 fix report (no code) | master plan T4 doc requirement |
| INFO-1..INFO-9 from the audit are NOT fixed in this session | documented in the audit; owner may park them in PENDING_TASKS |
| Laws: no merges, no deploy, no :8020 restart, no prompt edits, Retell GET-only, `.env` never committed, `scripts/keyhound` before any push | LAW 0 + AGENTS.md |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| None | — |

## Environment & Dependencies
- Main venv (copy-mirror trap): `/home/julio/projects/clean_diallux_SDR/engine/.venv` — ALWAYS `<venv>/bin/python -m pip …`, never the pip script.
- websockets 16.1.1, pydantic v2, pytest — already in the venv. No new dependencies.
- Worktree recipe (T1, exact commands below): worktree `/tmp/opencode/wt-iter60`, branch `engine/iter60-audit-fixes` @ `6d13803`.
- Suite: `cd /tmp/opencode/wt-iter60/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → baseline **398 passed** (~70 s), after pins **407 passed**.
- Ledger DB: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` — read/migrate via `.venv/bin/python -c "import sqlite3; …"` (NO sqlite3 CLI).
- Langfuse `http://localhost:3001` (health only; not required this session).
- `.env` source: `cp -p /tmp/opencode/wt-iter59/engine/.env /tmp/opencode/wt-iter60/engine/.env` (has `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27`, `DEEPGRAM_EAGER_EOT_THRESHOLD=0.7`, `AUDIO_TRANSPORT=browser`, `VOICE_TEST_TOKEN`). If wt-iter59 is gone: copy `/home/julio/projects/clean_diallux_SDR/engine/.env` and append `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` on its own line.
- Telegram ASK at the end: `cd /tmp/opencode/wt-iter60/engine && set -a && . /home/julio/projects/video_strategy/.env && set +a && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "<message>"`.

## Architecture (one block diagram)
```
iter60 FIX SESSION (branch engine/iter60-audit-fixes @ base 6d13803)
  T1 worktree + baseline 398
  T2 prewarm.py        — AUD-1 (drain cancel on get), AUD-2 (b64 byte-join)
  T3 builder.py        — AUD-3+AUD-4 (_consume_hybrid stash + laneB msg-guard),
                         AUD-10 (kb_stats moved out of _render_from_raw)
  T4 session.py        — AUD-5 (round-sync fires nothing)
  T5 builder.py        — AUD-6 (drop spoken_any from the 2 semantic gates)
  T6 config.py         — AUD-8 (rag_fire_mode validator)
  T7 scripts/live_sql.py — AUD-7 (mode/degraded/await_ms columns + migration)
  T8 pins file (9) + suite 407 + fix report (AUD-9 note) + commit + ASK owner
  STOP — merge/deploy/T6-live-call stay owner-gated
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter60/engine/diallux/media/prewarm.py` | AUD-1: module `_companion_tasks` dict; `_spawn_idle_tts` registers its drain task; `get(kind)` cancels+pops the companion before returning the ws. AUD-2: line ~192 → `_PHRASE_CACHE[key] = b"".join(_b64d(c) for c in chunks)` | E |
| `/tmp/opencode/wt-iter60/engine/diallux/graph/builder.py` | AUD-3/AUD-4: `__init__` gains `self._live_merged_turn: dict[str, dict] = {}`; `_consume_hybrid` gains the same-turn stash short-circuit (top), the laneB msg-guard (respawn condition), and the stash write (successful landed path). AUD-10: remove the 3 `_kb_stats` lines from `_render_from_raw`; add them in `_live_retrieve` (after merge, before return) and in `_consume_hybrid` (after its render). AUD-6: two gates lose `spoken_any` | E |
| `/tmp/opencode/wt-iter60/engine/diallux/media/session.py` | AUD-5: `_on_eot` + `_on_eager_eot` fire dispatches gain an explicit `elif mode == "round-sync": pass` branch (before the final `else`); update both comments | E |
| `/tmp/opencode/wt-iter60/engine/diallux/config.py` | AUD-8: `from pydantic import field_validator` + validator on `rag_fire_mode` restricting to {eot, speech-window, round-sync, hybrid} | E |
| `/tmp/opencode/wt-iter60/engine/scripts/live_sql.py` | AUD-7: `rag` table CREATE gains `mode TEXT`, `degraded INTEGER`, `await_ms REAL`; the `rag` span INSERT (≈line 215-228) writes `out.get("mode")`, `1 if out.get("degraded") else 0`, `out.get("await_ms")`; add `_ensure_rag_cols(con)` migration (PRAGMA table_info check + ALTER TABLE ADD COLUMN, each guarded try/except) called right after the sqlite connect in the import path | E |
| `/tmp/opencode/wt-iter60/engine/tests/test_iter60_audit_fixes.py` | 9 pins (exact list in T8) | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/05_fix_report.md` | THE deliverable: per-AUD fix + file:line + pin name + before/after evidence + the AUD-9 token-cost note | N |
| everything else | UNTOUCHED | — |

## Deploy Rules
- NOTHING deploys; :8020 keeps serving whatever it serves (iter59 is NOT deployed — no restart of anything).
- NEVER bind :8000-:8003. No git merges, no branch changes, no `.env` edits, no prompt edits, no Retell API writes (GET-only), production agent IDs untouched.
- Commit(s) ONLY on `engine/iter60-audit-fixes` after suite green. `scripts/keyhound` before any push. Merge = owner decision at the STOP POINT.

## Tasks (in order)

### T1 — Worktree + baseline
Goal: exact tree to fix, suite green before touching anything.
Files: none.
Commands (full):
```
cd /home/julio/projects/clean_diallux_SDR && git worktree add -b engine/iter60-audit-fixes /tmp/opencode/wt-iter60 6d13803
ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter60/engine/.venv
cp -p /tmp/opencode/wt-iter59/engine/.env /tmp/opencode/wt-iter60/engine/.env
cd /tmp/opencode/wt-iter60/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3
```
Dependencies: none.
Verification: `git log --oneline -2` in `/tmp/opencode/wt-iter60` shows `6d13803` on top of `db8e56f`; suite = **398 passed**.

### T2 — Prewarm fixes (AUD-1, AUD-2)
Goal: kill the mute-call blocker and the truncated-greeting blocker.
Files: `/tmp/opencode/wt-iter60/engine/diallux/media/prewarm.py`.
Changes (exact):
1. **AUD-1** — add module level `_companion_tasks: dict[str, asyncio.Task] = {}` next to `pool`. In `_spawn_idle_tts`, after `asyncio.get_running_loop().create_task(_drain())`, capture the task and store `_companion_tasks["tts"] = task`. Rewrite `get(kind)`:
```python
def get(kind: str):
    """Pop one prewarmed socket for adoption (None when empty).
    iter60 AUD-1: cancel the idle companion task FIRST — a live _drain
    recv on an adopted TTS socket races the session's recv loop
    (websockets 16.1.1 ConcurrencyError → dead recv loop → mute call)."""
    t = _companion_tasks.pop(kind, None)
    if t is not None:
        t.cancel()
    return pool.pop(kind, None)
```
Note: the STT `_ka` keepalive is a SENDER only — leave it exactly as is.
2. **AUD-2** — line ~192: replace `_PHRASE_CACHE[key] = _b64d("".join(chunks))` with `_PHRASE_CACHE[key] = b"".join(_b64d(c) for c in chunks)` (each `data` field is a complete base64 string; padding mid-join silently truncates).
Commands: none beyond edits.
Dependencies: T1.
Verification: T8 pins 1-2 pass; suite still green.

### T3 — Hybrid consume fixes (AUD-3, AUD-4, AUD-10)
Goal: rounds 2+ keep the full merged set; stale laneB can never be served; kb_stats counts once.
Files: `/tmp/opencode/wt-iter60/engine/diallux/graph/builder.py`.
Changes (exact):
1. **AUD-3 + AUD-4** — in `CallRuntime.__init__` (next to the `_live_*` dicts, ~line 395): add `self._live_merged_turn: dict[str, dict] = {}`.
   In `_consume_hybrid`, immediately after `self._live_mode_label = "hybrid"` and the `key_a, key_b = …` line, add the same-turn stash short-circuit:
```python
        # iter60 AUD-3: rounds 2+ of the SAME turn reuse the round-1 merged
        # set (the seq floor rightly rejects stale laneA, but it also
        # rejected THIS turn's laneA — knowledge silently shrank to
        # laneB-only on every tool round). Stash validity = same msg AND
        # the laneB task unchanged (a new fire bumps _live_task_seq).
        stash = self._live_merged_turn.get(state_name)
        if stash and stash.get("msg") == msg \
                and self._live_task_seq.get(key_b, -1) == stash.get("b_seq"):
            r = stash["res"]
            return (r["delta"], r["kbs"], r["ms"], r["chunks"],
                    r["lane_qs"], False, 0.0)
```
   Change the laneB respawn condition (currently `if task_b is None or task_b.cancelled():`) to also respawn on msg mismatch:
```python
        if task_b is None or task_b.cancelled() \
                or self._live_msgs.get(key_b) != msg:
            # iter60 AUD-4: a DONE laneB from an earlier turn/visit has no
            # seq/msg freshness check — reject on msg mismatch and respawn
            # with the CURRENT round's utterance (same kill as the task
            # path's msg-match).
            self.spawn_live_retrieve(state_name, dvs, msg, lane="laneB")
            task_b = self._live_tasks.get(key_b)
```
   At the end of the successful landed path (right after `self._live_consumed_res[state_name] = fresh`), add the stash write:
```python
        self._live_merged_turn[state_name] = {
            "msg": msg, "b_seq": self._live_task_seq.get(key_b, -1),
            "res": fresh}
```
   Semantics pinned: same-turn reuse mirrors the task path's msg-match reuse (eot/speech-window) — round-2 knowledge = round-1 merged set; a NEW turn always re-fires laneB (b_seq bump) or changes msg → stash invalidated.
2. **AUD-10** — remove the three `_kb_stats` lines from `_render_from_raw` (lines ~1217-1219); paste them (same fields) into `_live_retrieve` right after the `merged = ragmod.merge_lane_chunks(...)` block (before `ms = round(...)`) — this preserves iter58 semantics for eot/speech-window bg tasks AND the round-sync inline path; paste them once more into `_consume_hybrid` right after its `_render_from_raw(...)` call. Net: hybrid counts exactly one rag_turn per consumed round.
Dependencies: T1.
Verification: T8 pins 3, 4, 8 pass; existing hybrid pins (`test_hybrid_lane_split_and_merge`, `test_hybrid_lane_b_only_when_lane_a_absent`, `test_hybrid_degrades_never_raises`) stay green.

### T4 — Round-sync fire skip (AUD-5)
Goal: no wasted duplicate retrieval per round-sync turn.
Files: `/tmp/opencode/wt-iter60/engine/diallux/media/session.py`.
Changes (exact): in BOTH `_on_eot` (~line 396-403) and `_on_eager_eot` (~line 477-484), insert a `round-sync` branch so the dispatch reads:
```python
        if mode == "hybrid":
            self._fire_live_retrieve(transcript, lane="laneB")
        elif mode == "speech-window" and self._update_fired:
            pass
        elif mode == "round-sync":
            pass    # iter60 AUD-5: consume retrieves INLINE — firing a
                    # "full" task here was a wasted embed+pgvector per turn
        else:
            self._fire_live_retrieve(transcript)
```
Update the two dispatch comments (they currently say "eot/round-sync — iter58 surface").
Dependencies: T1.
Verification: T8 pin 5 passes; existing pins `test_eot_mode_fires_at_eot_as_iter58` and `test_round_sync_retrieves_inline` stay green (first grep `tests/` for any pin asserting round-sync FIRES at EOT — expect none).

### T5 — Semantic dedupe gate (AUD-6)
Goal: a turn-OPENING near-verbatim re-ask is dropped when the cross-turn window is non-empty.
Files: `/tmp/opencode/wt-iter60/engine/diallux/graph/builder.py`.
Changes (exact): line ~2247 `if is_q and spoken_any and stem_window:` → `if is_q and stem_window:`; line ~2322 `if pending_is_q and spoken_any and stem_window:` → `if pending_is_q and stem_window:`. Update both comments (the never-silent guard is preserved by the non-empty `stem_window` itself — an empty window means no question was ever spoken this call).
Risk note: the exact-path `spoken_any` guards are UNTOUCHED (they protect a different thing — in-turn doubles); only the two semantic gates change. No existing pin asserts first-sentence exemption (verified in the audit).
Dependencies: T1.
Verification: T8 pin 6 passes; existing dedupe pins (`tests/test_iter59_dedupe_semantic.py`, iter42 pins) stay green.

### T6 — Fire-mode validator (AUD-8)
Goal: a typo'd `RAG_FIRE_MODE` refuses to start instead of misbehaving.
Files: `/tmp/opencode/wt-iter60/engine/diallux/config.py`.
Changes (exact): add `from pydantic import field_validator` to the imports; inside `Settings`, after the `rag_fire_mode` field:
```python
    @field_validator("rag_fire_mode")
    @classmethod
    def _rag_fire_mode_whitelist(cls, v: str) -> str:
        # iter60 AUD-8: an invalid mode silently ran eot-fires with
        # speech-window consume semantics — fail fast at Settings load.
        allowed = ("eot", "speech-window", "round-sync", "hybrid")
        if v not in allowed:
            raise ValueError(
                f"rag_fire_mode must be one of {allowed}, got {v!r}")
        return v
```
Dependencies: T1.
Verification: T8 pin 7 passes; suite green (all pins use valid modes).

### T7 — Ledger columns (AUD-7)
Goal: the T6 gates become SQL-computable from the ledger.
Files: `/tmp/opencode/wt-iter60/engine/scripts/live_sql.py`.
Changes (exact):
1. Find the `rag` table CREATE TABLE (schema/create section) and add three columns: `mode TEXT`, `degraded INTEGER`, `await_ms REAL`.
2. Add a migration helper and call it on the sqlite connection right before the import INSERT loop (so the EXISTING `ledger.db` gains the columns without recreation):
```python
def _ensure_rag_cols(con) -> None:
    """iter60 AUD-7: add mode/degraded/await_ms to an existing rag table
    (idempotent — checks PRAGMA table_info first)."""
    have = {r[1] for r in con.execute("PRAGMA table_info(rag)")}
    for col, decl in (("mode", "TEXT"), ("degraded", "INTEGER"),
                      ("await_ms", "REAL")):
        if col not in have:
            con.execute(f"ALTER TABLE rag ADD COLUMN {col} {decl}")
    con.commit()
```
3. In the `rag` span INSERT (~line 215-228): extend the column list and values with `out.get("mode")`, `1 if out.get("degraded") else 0`, `out.get("await_ms")`.
Dependencies: T1.
Verification: T8 pin 9 passes; `cd /tmp/opencode/wt-iter60/engine && .venv/bin/python -c "import sqlite3; con=sqlite3.connect('/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db'); print([r[1] for r in con.execute('PRAGMA table_info(rag)')])"` — do NOT run the migration against the real ledger in this session (the migration runs at the first T6 import); the pin proves it on a temp db.

### T8 — Pins + suite + report + commit + ASK
Goal: prove every fix, write the deliverable, stop for the owner.
Files: `/tmp/opencode/wt-iter60/engine/tests/test_iter60_audit_fixes.py` (N), `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/05_fix_report.md` (N).
The 9 pins (hermetic; crib the `_t4_settings` / `_LLM_JSON` / `mock_client` / `LanesStore` / `_run` helpers from `/tmp/opencode/wt-iter60/engine/tests/test_iter49_rag_parity.py` and the session fake pattern from `/tmp/opencode/wt-iter60/engine/tests/test_iter59_rag_freshness.py`):
1. `test_tts_drain_task_cancelled_on_get` — monkeypatch `prewarm.pool["tts"]` with a fake ws and `prewarm._companion_tasks["tts"]` with a real never-ending asyncio task; `get("tts")` returns the ws AND the task is cancelled within a tick.
2. `test_b64_join_padded_chunks_no_truncation` — `prewarm`-level: chunks `[_b64e(b"AB"), _b64e(b"ABCD"), _b64e(b"ABC")]` (mixed padding) decoded-and-joined == `b"ABABCDABC"` (the audit's truncation case, now byte-exact).
3. `test_hybrid_round2_reuses_full_merged_set` — AUD-3 regression pin (the audit's P1 proof as a test): laneA+laneB fire+land → consume round 1 → consume round 2 (same state, same msg) → assert round 2 `lane_qs` still contains the laneA query and `degraded is False`.
4. `test_hybrid_stale_laneb_respawned_with_current_msg` — AUD-4 regression pin (the audit's P2 proof as a test): turn-1 Booking laneB ("confirming the booking please") fire+land+consume; turn-2 fires laneA/laneB for Intake; consume a Booking round whose user_msg is the NEW utterance → assert the served `lane_qs`/chunks contain the NEW utterance's query (respawned), NOT "confirming the booking please", and `degraded is False`.
5. `test_round_sync_fires_nothing_at_eot` — copy the fake-runtime session pattern from `test_eot_mode_fires_at_eot_as_iter58` with `rag_fire_mode="round-sync"`; assert the fake runtime's `spawn_live_retrieve` calls == `[]` and `_turn_task` is created.
6. `test_turn_opening_reask_dropped_when_window_nonempty` — full-round pin: graph payload pre-seeded with `question_stem_window=[{"text": "what's the name of your company?", "vec": _VEC_A}]` (add the key to the astream payload dict alongside `user_text` — it merges into state); `rt._resolve_kb_store` patched to return a fake store whose `embed_query` returns `_VEC_A`; FakeLLM streams the near-verbatim question as the FIRST sentence; capture `custom` stream events → assert the question produced NO `tts_token` events, and a control statement in the same stream still speaks. (Crib the token-capture pattern from the iter42 dedupe pins: glob `/tmp/opencode/wt-iter60/engine/tests/test_iter42*`.)
7. `test_rag_fire_mode_rejects_invalid` — `pytest.raises(ValidationError)` on `_t4_settings(rag_fire_mode="spech-window")`; and `_t4_settings(rag_fire_mode="hybrid")` still constructs.
8. `test_hybrid_kb_stats_count_once` — after the P1 flow (laneA+laneB fire+land+ONE consume), assert `_kb_stats["rag_turns"]` delta == 1 (was 2-3 before AUD-10).
9. `test_live_sql_rag_migration_adds_columns` — temp sqlite db: create the OLD rag table shape (no new cols), run `live_sql._ensure_rag_cols(con)` (import the module by path or via `sys.path` — it lives at `/tmp/opencode/wt-iter60/engine/scripts/live_sql.py`; check how existing tests import scripts, e.g. the iter57 preflight pin pattern), assert PRAGMA shows the 3 new columns, and the INSERT path accepts a span dict with mode/degraded/await_ms.
Commands (full):
```
cd /tmp/opencode/wt-iter60/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3
```
Then write `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/05_fix_report.md`: per AUD-1..10 — what changed, file:line, pin name, before/after (cite the audit proofs as "before"); plus the **AUD-9 token-cost note**: KB-everywhere adds lane-B retrieval on 4 freed states (Booking, VerifyLead, ConfirmSlots, contact_details) — bounded by `rag_char_budget=1600` chars per heavy round per state ≈ ≤~400 tokens/round; lite/ack rounds still skip retrieval by design.
Then commit on the branch:
```
cd /tmp/opencode/wt-iter60 && git add engine/diallux engine/scripts engine/tests && git commit -m "iter60: audit fixes AUD-1..AUD-10 (prewarm drain/b64, hybrid consume, round-sync fire, dedupe gate, validator, ledger cols)"
```
Then the ASK:
```
cd /tmp/opencode/wt-iter60/engine && set -a && . /home/julio/projects/video_strategy/.env && set +a && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "iter60 audit fixes done: 407 passed, AUD-1..10 fixed + pinned, report at research/surgeon/iter59-kb-everywhere/05_fix_report.md — merge + T6 deploy decision yours"
```
Dependencies: T2-T7.
Verification: suite = **407 passed** (398 + 9 new, ZERO existing pins edited); `cd /tmp/opencode/wt-iter60 && git status --short` clean after commit; report on disk; ping sent.

## Validation Plan (end-to-end)
1. `/tmp/opencode/wt-iter60/engine/tests/test_iter60_audit_fixes.py` exists with the 9 named pins; suite = 407 passed, 0 failed.
2. The three audit proofs flipped: P1 (round-2 laneA) now keeps laneA; P2 (stale laneB) now respawns — both covered by pins 3 and 4.
3. `git log --oneline -2` on the branch: iter60 commit on top of `6d13803`; nothing merged, nothing deployed.
4. `05_fix_report.md` on disk with the AUD-9 token-cost quantification.
5. Owner ping sent (STOP POINT).

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Merging `engine/iter60-audit-fixes` (or iter59) | owner decision at the STOP POINT (LAW 0) |
| T6 owner live call + `RAG_FIRE_MODE=hybrid` deploy | master plan iter59 T6 — runs only after owner digests the fix report |
| T7 closeout (CALL_FACTS, PENDING_TASKS, ITERATIONS, ASK items) | iter59 master plan T7, still blocked behind T6 |
| INFO-1..INFO-9 from `04_code_audit.md` (duplicate `_cosine`, mic-page `clear` handling, Twilio burst pacing, maintainer shutdown, nova3×fire-mode guard, config cosmetics, reconnect eager-wiring) | documented in the audit; park as PT rows during iter59 T7 if the owner wants them tracked |
| Phase C lane-B latency compression | master plan Phase C — separate session |
