# PLAN — iter61: prewarm socket staleness (AUD-11/12/13) — the live mic-test blockers

## Meta
- Date: 2026-09-21
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — fix the 3 BLOCKERs found by the 2026-09-21 iter60 live mic test (AUD-11 v1-KeepAlive poison, AUD-12 TTS idle-timeout death, AUD-13 reconnect self-cancel) on branch `engine/iter61-prewarm-staleness` off `c7f8d2d`, pin each fix, restart the :8021 test server, owner re-test, report + ledger status flips, ASK. NO merges, NO :8020 changes, NO deploy.
- Status: **PLAN ONLY (not started — awaits approval)**

## Compaction Context (session 2026-09-21 — pin, do not re-derive)

- **Project state:** iter60 (branch `engine/iter60-audit-fixes` @ `0d21763` + tool commit `c7f8d2d`, unmerged, suite **407 passed** = 398 baseline + 9 pins) fixed audit findings AUD-1..AUD-10. Owner pinged, STOP POINT reached. Live mic test THEN exposed 3 NEW blockers (below). Test server `127.0.0.1:8021` currently runs from worktree `/tmp/opencode/wt-iter60` @ `c7f8d2d` (pid file `/tmp/opencode/voice_8021.pid`, log `/tmp/opencode/voice_server_8021.log`), launched with env-injected `RAG_FIRE_MODE=hybrid CALL_PREWARM=true` (`.env` itself untouched). Production `:8020` = wt-iter58, UNTOUCHED all session.
- **The live test (2026-09-21 04:59 UTC, call `351691ef421a`):** owner connected via `https://flores.diallux-ai.site/voice60/mic?k=<VOICE_TEST_TOKEN>` (Caddy route `handle_path /voice60/* → 127.0.0.1:8021`, APPLIED + verified 200; gate in-app 4401 verified live: no-token → close 4401, token → handshake OK). Owner spoke ~25 s → ZERO replies, ZERO turns. Autopsy: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/06_autopsy_mic_live_test_20260921.md`.
- **The 3 proven root causes (timeline in the autopsy):**
  - **AUD-11 BLOCKER** — prewarm `_ka` (`/tmp/opencode/wt-iter60/engine/diallux/media/prewarm.py` ~lines 86-96) sends `{"type": "KeepAlive"}` every 5 s on the idle STT socket. Deployed API = **v2 listen (flux)**: server's own error text (captured in the log, sequence_id=1) says valid client messages are `CloseStream | ForceEndTurn | Configure` — `KeepAlive` is a **v1-listen** variant. Deepgram replies `UNPARSABLE_CLIENT_MESSAGE`; the Error sits QUEUED on the socket; the session adopts it and the recv loop eats the queued Error at +11 ms → socket dead. The session-side `_keepalive_loop` (`diallux/media/deepgram_stt.py:160-167`) sends the same v1 frame but is gated `if settings.deepgram_mode == "nova3"` → dead code under flux (deployed mode is flux — log: "deepgram adopted prewarmed socket (mode=flux)"), so fresh sockets are NOT poisoned.
  - **AUD-12 BLOCKER** — idle TTS pool socket has NO keepalive sender (`_drain` only receives) → Cartesia killed it server-side: log 04:59:44.507 `received 1000 (OK) connection idle timeout` after ~20 min idle (04:39:51 start → 04:59:44 call). Adopted corpse → no greeting/reply audio path. Exact provider idle-timeout value UNKNOWN — design must not depend on it.
  - **AUD-13 BLOCKER (pre-existing V2-era, first observed here)** — `_recv_loop` (`diallux/media/deepgram_stt.py:185-187`) AWAITS `self.on_disconnect()` from inside the recv task; session `_on_stt_disconnect` (`diallux/media/session.py:587-612`) first calls `await self.stt.close()` whose body does `self._recv_task.cancel()` (`deepgram_stt.py:150-152`) — cancelling the task currently executing the reconnect → CancelledError (not caught by `except Exception`) silently kills the reconnect: NO "deepgram connected" / NO "stt reconnect failed" logged for the remaining 33 s; `send_audio` (`deepgram_stt.py:136-137`) no-ops while `_closed`/`_ws is None` → ALL mic audio dropped silently → zero transcripts → zero turns.
- **Ledger tracking:** `research/surgeon/iter48-rag-truth/ledger.db` findings table — FIND-16..25 = AUD-1..10 (status `fixed-in-iter60 pending live verify`; they need a POST-FIX mic test to close — the failed call produced no rag rows). FIND-26/27/28 = AUD-11/12/13 (status open, autopsy written). Rows carry the LIVE-VERIFY criterion each must meet to flip to verified.
- **Fix report:** `research/surgeon/iter59-kb-everywhere/05_fix_report.md` (iter60, done). Audit: `research/surgeon/iter59-kb-everywhere/04_code_audit.md`. The event puller built this session: `/tmp/opencode/wt-iter60/engine/scripts/mic_events.py` (committed `c7f8d2d`; usage in its docstring — `--sid`, `--window "HH:MM-HH:MM"`, `--tag`, `--langfuse` pulls `micbridge-<sid>` traces via lf.py).
- **Verified-safe facts (do not re-check):** websockets 16.1.1 in the venv; `mic_events.py` works end-to-end (log timeline + Langfuse pull proven on the 8021 log); Deepgram v2 flux error text (KeepAlive invalid) is server-proven; Cartesia idle timeout is server-proven (1000 after ~20 min); token gate 4401 verified live through Caddy; `/voice60` route live in `/etc/caddy` (NOT yet committed to /etc/caddy git — owner sudo one-liner pending, harmless); AUD-1/AUD-2 fixes behaved correctly during the failed call (no ConcurrencyError, drain cancelled cleanly).
- **Key paths:** iter60 plan `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter60_audit_fixes.md`; autopsy `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/06_autopsy_mic_live_test_20260921.md`; audit `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/04_code_audit.md`.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| New branch `engine/iter61-prewarm-staleness` off `c7f8d2d` (NOT off main, NOT a new iter60 commit) | one iteration = one branch per LAW 0; iter60's scope was audited, these 3 findings are its live-verification output; keeps every fix individually revertable |
| AUD-11 fix = DELETE the `_ka` keepalive task from prewarm `_spawn_idle_stt` entirely (no replacement frame) | v2 flux has NO client keepalive variant (server-proven); idle liveness is the maintainer's job (AUD-12 TTL); the session's own nova3-only keepalive stays UNTOUCHED (different path, nova3 builds) |
| AUD-12 fix = TTL-based maintainer: `_spawn_ts[kind]` recorded at spawn; maintainer closes+respawns any pool socket older than `PREWARM_SOCKET_TTL = 240` s; extract loop body into `_maintain_once(settings)` so pins can call it | covers both STT and TTS provider idle timeouts without guessing provider values (observed death at ≤20 min; 240 s is safely under any of them); respawn-on-close already exists — this adds respawn-on-AGE |
| AUD-13 fix = two surgical changes INSIDE `deepgram_stt.py` only: (1) `_recv_loop` schedules `on_disconnect` via `asyncio.get_running_loop().create_task(...)` instead of awaiting it; (2) `close()` skips cancelling a task that is `asyncio.current_task()` | the hook then runs in its OWN task (close()'s cancel can never hit the caller); session.py UNTOUCHED — `_on_stt_disconnect` keeps working as-is, now running in the deferred task |
| Adoption liveness check = NOT in this iteration | bigger surface (what check? provider-specific); the TTL pool guarantees a FRESH socket at adoption time ≤4 min after spawn, which fixes the observed failure; note as follow-up |
| 5 pins in ONE new file `tests/test_iter61_prewarm_staleness.py` | per-iteration pin convention; zero edits to existing test files; expected suite **412 passed** (407 + 5) |
| Re-verify = owner mic call on the SAME URL/token/route (no caddy change) + ledger status flips | the route is live; only the engine code changes |
| Laws: no merges, no deploy to :8020, `.env` never committed, `scripts/keyhound` before any push, Cal event 3801235 REAL (cancel any test booking) | LAW 0 + AGENTS.md |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| None | — |

## Environment & Dependencies
- Main venv (copy-mirror trap): `/home/julio/projects/clean_diallux_SDR/engine/.venv` — ALWAYS `<venv>/bin/python -m pip …`, never the pip script. websockets 16.1.1, pytest already present. No new dependencies.
- Worktree (T1): `/tmp/opencode/wt-iter61`, branch `engine/iter61-prewarm-staleness` @ base `c7f8d2d`.
- Suite: `cd /tmp/opencode/wt-iter61/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → baseline **407 passed**, after pins **412 passed**.
- `.env` source: `cp -p /tmp/opencode/wt-iter60/engine/.env /tmp/opencode/wt-iter61/engine/.env` (has `VOICE_TEST_TOKEN`, `LANGFUSE_*`, `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27`, `AUDIO_TRANSPORT=browser`, `DEEPGRAM_EAGER_EOT_THRESHOLD=0.7`). If wt-iter60 is gone: copy `/home/julio/projects/clean_diallux_SDR/engine/.env` and append `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` on its own line.
- Test server :8021 (the ONLY restart surface): launched from the worktree with env-injected `RAG_FIRE_MODE=hybrid CALL_PREWARM=true` (NOT in .env). Caddy route `flores.diallux-ai.site/voice60/* → 127.0.0.1:8021` already live. Mic URL (same every time): `https://flores.diallux-ai.site/voice60/mic?k=$VOICE_TEST_TOKEN`.
- `:8020` = wt-iter58 production test surface — NEVER restart/touch. Production ports 8000-8003 NEVER bound.
- Langfuse: `http://localhost:3001` (env keys in `.env`); puller via `scripts/lf.py` (`_traces/_obs`), mic traces named `micbridge-<sid>`.
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (NO sqlite3 CLI on this box — use `<venv>/bin/python -c "import sqlite3; …"`).
- Telegram ASK: `cd /tmp/opencode/wt-iter61/engine && set -a && . /home/julio/projects/video_strategy/.env && set +a && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "<message>"`.
- pip trap: always `<venv>/bin/python -m pip …`, never the `bin/pip` script.

## Architecture (one block diagram)
```
iter61 FIX SESSION (branch engine/iter61-prewarm-staleness @ base c7f8d2d)
  T1 worktree + baseline 407
  T2 prewarm.py  — AUD-11: delete _ka keepalive task (v1 frame on v2 socket = poison)
  T3 prewarm.py  — AUD-12: _spawn_ts + _maintain_once + TTL 240s close+respawn
  T4 deepgram_stt.py — AUD-13: on_disconnect fire-and-forget + close() current-task guard
  T5 pins file (5) + suite 412
  T6 restart :8021 from wt-iter61 + health + preflight + TTL-respawn smoke (log line)
  T7 owner mic re-test (same URL) → ledger FIND-16..28 status flips → 01_fix_report.md → commit → ASK owner
  STOP — merge/deploy/real-Twilio-T6 stay owner-gated
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter61/engine/diallux/media/prewarm.py` | AUD-11: remove the `_ka` function + its `create_task` from `_spawn_idle_stt` (docstring updated: v2 flux has no client keepalive variant; liveness = maintainer TTL). AUD-12: module `_spawn_ts: dict[str, float] = {}`; `_spawn_idle_stt`/`_spawn_idle_tts` record `time.monotonic()`; new `_maintain_once(settings)` (the current maintainer body, plus: if kind in pool AND age > `PREWARM_SOCKET_TTL` (module const 240) → best-effort `ws.close()` on the old socket, drop from pool+`_companion_tasks`+`_spawn_ts`, respawn, log `"prewarm: idle <kind> respawned (ttl <N>s)"`); `_maintainer` loop calls `_maintain_once` | E |
| `/tmp/opencode/wt-iter61/engine/diallux/media/deepgram_stt.py` | AUD-13: in `_recv_loop`'s except path — replace `await self.on_disconnect()` with `asyncio.get_running_loop().create_task(self.on_disconnect())` (comment: the hook closes THIS task — awaiting it self-cancelled the reconnect, CancelledError is invisible to `except Exception`); in `close()` — cancel `_recv_task`/`_keepalive_task` only when `task is not asyncio.current_task()` | E |
| `/tmp/opencode/wt-iter61/engine/tests/test_iter61_prewarm_staleness.py` | 5 pins (exact list in T5) | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter61-prewarm-staleness/01_fix_report.md` | THE deliverable: per AUD-11/12/13 — change + file:line + pin + before/after (cite autopsy) + live-verify results | N |
| everything else (incl. `/tmp/opencode/wt-iter60/*`, `diallux/media/session.py`, `diallux/graph/builder.py`, prompts, `.env`) | UNTOUCHED | — |

## Deploy Rules
- NOTHING deploys. `:8020` (wt-iter58) untouched forever. The ONLY restart surface is the test server `:8021` (exact commands in T6). NEVER bind :8000-:8003. No git merges. `.env` never committed. `scripts/keyhound` before any push. Commits only on `engine/iter61-prewarm-staleness` after suite green. Merge = owner decision at the STOP POINT.
- Kill/restart of :8021 uses the pid file `/tmp/opencode/voice_8021.pid` — never `systemctl`, never `pkill uvicorn` (that would catch :8020).

## Tasks (in order)

### T1 — Worktree + baseline
Goal: exact tree to fix; suite green before touching anything.
Files: none.
Commands (full):
```
cd /home/julio/projects/clean_diallux_SDR && git worktree add -b engine/iter61-prewarm-staleness /tmp/opencode/wt-iter61 c7f8d2d
ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter61/engine/.venv
cp -p /tmp/opencode/wt-iter60/engine/.env /tmp/opencode/wt-iter61/engine/.env
cd /tmp/opencode/wt-iter61/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3
```
Dependencies: none.
Verification: `git -C /tmp/opencode/wt-iter61 log --oneline -2` shows iter61 base `c7f8d2d` on `0d21763`; suite = **407 passed**.

### T2 — AUD-11: remove the v1-KeepAlive poison (prewarm.py)
Goal: the prewarmed STT socket never receives a v1-invalid frame → no queued UNPARSABLE error on adoption.
Files: `/tmp/opencode/wt-iter61/engine/diallux/media/prewarm.py`.
Changes (exact): in `_spawn_idle_stt`, delete the entire inner `async def _ka()` body and the `asyncio.get_running_loop().create_task(_ka())` line; replace with a comment: `# iter61 AUD-11: v2 flux has NO client KeepAlive variant (server rejects it: CloseStream|ForceEndTurn|Configure are the only valid client types) — sending it queues an UNPARSABLE error that kills the first adoption. Idle liveness = maintainer TTL (AUD-12).` The docstring of `_spawn_idle_stt` drops the "KeepAlive every 5 s" claim. Do NOT touch `diallux/media/deepgram_stt.py`'s `_keepalive_loop` (nova3-only path, untouched).
Commands: none beyond edits.
Dependencies: T1.
Verification: T5 pin 1 passes; suite green.

### T3 — AUD-12: TTL-based pool liveness (prewarm.py)
Goal: an idle pool socket older than 240 s is closed + respawned before any call can adopt a corpse.
Files: `/tmp/opencode/wt-iter61/engine/diallux/media/prewarm.py`.
Changes (exact):
1. Module level next to `pool`: add `PREWARM_SOCKET_TTL = 240` and `_spawn_ts: dict[str, float] = {}`.
2. In `_spawn_idle_stt` AND `_spawn_idle_tts`: after `pool[kind] = ws`, add `_spawn_ts[kind] = time.monotonic()`.
3. Extract the maintainer body into:
```python
def _maintain_once(settings) -> None:
    """One maintainer tick. iter61 AUD-12: also respawns sockets that aged
    past PREWARM_SOCKET_TTL — Cartesia idle-times-out silent sockets
    server-side (~minutes; observed death after ~20 min), so an old pool
    entry is a guaranteed-dead adoption."""
    for kind in ("stt", "tts"):
        if kind in pool:
            age = time.monotonic() - _spawn_ts.get(kind, 0.0)
            if age <= PREWARM_SOCKET_TTL:
                continue
            old = pool.pop(kind)
            _companion_tasks.pop(kind, None)
            _spawn_ts.pop(kind, None)
            try:
                asyncio.get_running_loop().create_task(_close_quiet(old))
            except Exception:
                pass
            log.info("prewarm: idle %s respawned (ttl %ss)", kind,
                     PREWARM_SOCKET_TTL)
        if kind not in pool:
            try:
                (await _spawn_idle_stt(settings)) if False else None
            except Exception:
                pass
```
— NOTE the shape: `_maintain_once` must be `async def` (it awaits the spawn helpers); the loop body for the "missing" kind is the EXISTING try/except from the old `_maintainer` (`await _spawn_idle_stt(settings)` + log + except-warning), not the placeholder above. Final shape: async def, iterates `("stt", "tts")`; for each: if present and age <= TTL → skip; if present and stale → close old (via a small `async def _close_quiet(ws)` that awaits `ws.close()` in try/except) + clear dicts; if absent → spawn inside try/except with the existing respawn log line. The `_maintainer` loop becomes `while True: await asyncio.sleep(5.0); await _maintain_once(settings)` (CancelledError → return).
4. On adoption (`get(kind)`), ALSO drop `_spawn_ts.pop(kind, None)` (the maintainer must not age-track an adopted socket).
Commands: none beyond edits.
Dependencies: T1.
Verification: T5 pins 2+3 pass; suite green.

### T4 — AUD-13: reconnect must not self-cancel (deepgram_stt.py)
Goal: a mid-call STT drop actually recovers — new socket binds, audio flows, no silent deafness.
Files: `/tmp/opencode/wt-iter61/engine/diallux/media/deepgram_stt.py`.
Changes (exact):
1. `_recv_loop` except path (~lines 185-187): replace
   `if self.on_disconnect: await self.on_disconnect()`
   with
```python
                if self.on_disconnect:
                    # iter61 AUD-13: the hook CLOSES/CANCELS this recv task
                    # (close() cancels _recv_task) — awaiting it from inside
                    # the recv task self-cancelled the reconnect silently
                    # (CancelledError is not an Exception). Schedule it on
                    # its own task; this recv task just returns.
                    asyncio.get_running_loop().create_task(
                        self.on_disconnect())
```
2. `close()` (~lines 148-153): replace the for-loop cancel with:
```python
        cur = asyncio.current_task()
        for task in (self._recv_task, self._keepalive_task):
            if task and task is not cur:
                task.cancel()
```
   (comment: when close() runs FROM the recv task — the reconnect path — cancelling it would abort the reconnect itself; the loop is already dying.)
3. `diallux/media/session.py` UNTOUCHED — `_on_stt_disconnect` now runs in the deferred task; its `await self.stt.close()` cancels nothing live (old recv task already finished).
Commands: none beyond edits.
Dependencies: T1.
Verification: T5 pins 4+5 pass; existing pins `test_iter38_turn_lifecycle.py` (reconnect pins if any) stay green — grep `tests/` for `reconnect` and re-run any affected file.

### T5 — Pins (5, one file) + suite
Goal: prove every fix hermetically; zero existing pins edited.
Files: `/tmp/opencode/wt-iter61/engine/tests/test_iter61_prewarm_staleness.py` (N). Crib the fake-WS/session-fake patterns from `/tmp/opencode/wt-iter61/engine/tests/test_iter59_rag_freshness.py` (`_session`/object.__new__ pattern) and the settings helpers from `/tmp/opencode/wt-iter61/engine/tests/test_iter49_rag_parity.py` (`_t4_settings`).
The 5 pins:
1. `test_prewarm_sends_no_v1_keepalive` — `assert "KeepAlive" not in inspect.getsource(prewarm)` (the poison frame is GONE from the module; the maintainer/TTL path replaced it).
2. `test_pool_socket_older_than_ttl_respawned` — monkeypatch `prewarm.pool` with a fake ws per kind, set `prewarm._spawn_ts[kind] = time.monotonic() - 999`; monkeypatch `prewarm._spawn_idle_stt`/`_spawn_idle_tts` with counters; `_run(prewarm._maintain_once(settings))` → old fake ws got `.close()` awaited (counted), pool repopulated (spawn counters == 1 each), `_spawn_ts` refreshed.
3. `test_fresh_pool_socket_not_respawned` — same setup with `_spawn_ts` = now → spawn counters == 0, pool entries unchanged.
4. `test_recv_loop_death_schedules_reconnect_not_awaits` — build a bare DeepgramSTT (`__new__` pattern), set `on_disconnect = recorder` (an async fn appending "fired"), `self._closed = False`, `self._recv_task = asyncio.create_task(...)` around a `_recv_loop` whose fake `_ws.recv()` raises `ConnectionClosedError`-like exception once; await the recv task → assert recorder fired (the deferred task ran) and the recv task COMPLETED (not cancelled).
5. `test_close_never_cancels_current_task` — inside `async def go()`: `stt._recv_task = asyncio.current_task()`; `await stt.close()` must NOT raise CancelledError and the coroutine must complete (the current-task guard works).
6. `test_session_reconnect_recovers_audio_path` — session fake (`object.__new__` pattern from test_iter59_rag_freshness): real `DeepgramSTT` with a fake ws whose `recv()` raises once; run a full drop → reconnect → assert `session.stt._ws is not None` (fresh socket bound) and `await session.stt.send_audio(b"")` does not silently drop (fake ws records the send or the STT's `_ws` is live).
   (Total 6 pins — update the expected-suite numbers to **413 passed** if 6 pins land; T5 command block prints the actual count either way.)
Commands (full):
```
cd /tmp/opencode/wt-iter61/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3
```
Dependencies: T2-T4.
Verification: all pins pass; suite = **407 + N pins** (6 → 413), ZERO existing test files edited.

### T6 — Restart :8021 from the fixed tree + smoke
Goal: the test surface runs the fixed code; prove the TTL respawn fires.
Files: none (ops).
Commands (full):
```
kill $(cat /tmp/opencode/voice_8021.pid) 2>/dev/null; sleep 1
cd /tmp/opencode/wt-iter61/engine && git log --oneline -1
set -a && . ./.env && set +a
RAG_FIRE_MODE=hybrid CALL_PREWARM=true setsid nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8021 >> /tmp/opencode/voice_server_8021.log 2>&1 &
echo $! > /tmp/opencode/voice_8021.pid
sleep 6 && curl -sf http://127.0.0.1:8021/health && .venv/bin/python scripts/voice_preflight.py --url http://127.0.0.1:8021 2>&1 | tail -2
```
Then wait ~5 min (TTL) and confirm the age-respawn line:
```
.venv/bin/python scripts/mic_events.py --log /tmp/opencode/voice_server_8021.log --tag WARM | tail -5
```
Dependencies: T5.
Verification: health 200 + preflight GREEN; log shows `prewarm: idle stt respawned (ttl 240s)`-style lines ~240 s after start; `git log -1` = the iter61 commit.

### T7 — Owner re-test + ledger flips + report + ASK
Goal: the deliverable; close the loop.
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter61-prewarm-staleness/01_fix_report.md` (N).
Steps:
1. Telegram the mic URL to the owner (SAME token): use the hitl_ping command from Environment, message: `"iter61 live re-test ready: greeting must play in full, then speak and GET A REPLY — server on fixed tree <sha>, same URL as before"`.
2. Owner makes the calls (greeting full, speech answered). Agent pulls:
```
.venv/bin/python scripts/mic_events.py --sid <new-sid> --langfuse
```
   → asserts: ADOPT lines present, NO STT-ERR/STT-DEAD/TTS-DEAD, `deepgram connected` after any drop, rag/llm spans flowing.
3. Ledger flips (venv python, NO sqlite3 CLI):
   - FIND-26/27/28 (AUD-11/12/13): status → `fixed-in-iter61 verified-live` + fix_commit + evidence.
   - FIND-16..25 (AUD-1..10): the re-test now exercises hybrid consume with REAL rag rows → SQL-gate check (`SELECT state, COUNT(*), ROUND(100.0*SUM(degraded)/COUNT(*),1) deg_pct, ROUND(AVG(await_ms),1) FROM rag WHERE run_id=? AND kind='rag' GROUP BY state`) after `scripts/live_sql.py import` of the re-test window (first import runs the AUD-7 migration on the real ledger); flip each to `verified-live` with the SQL row as evidence.
4. Write `01_fix_report.md` (per-finding: before = autopsy citation, after = file:line + pin + live evidence).
5. Commit on the branch:
```
cd /tmp/opencode/wt-iter61 && git add engine/diallux engine/tests && git commit -m "iter61: prewarm socket staleness fixes AUD-11/12/13 (drop v1 keepalive, TTL pool respawn, reconnect fire-and-forget)"
```
6. ASK owner (hitl_ping): "iter61 done: suite <N> passed, AUD-11/12/13 fixed+verified live, report at research/surgeon/iter61-prewarm-staleness/01_fix_report.md — merge decision yours".
Dependencies: T2-T6.
Verification: suite green; git status clean after commit; report on disk; ledger statuses flipped; ping sent.

## Validation Plan (end-to-end)
1. `tests/test_iter61_prewarm_staleness.py` exists with the 6 named pins; suite = **413 passed, 0 failed**.
2. The autopsy's three proofs flipped and pinned: poison frame gone (pin 1), stale-socket respawn (pins 2-3), reconnect recovers (pins 4-6).
3. `git log --oneline -3` on the branch: iter61 commit on top of `c7f8d2d` on `0d21763`; nothing merged; :8020 untouched.
4. Owner mic re-test: greeting plays in full, speech gets a reply, `mic_events.py` shows a clean timeline (no STT-ERR/STT-DEAD/TTS-DEAD).
5. Ledger: FIND-16..28 statuses flipped with SQL/live evidence.
6. Report on disk + owner ping sent (STOP POINT).

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Merge of iter60/iter61 branches, tag, git-tree.sh | owner decision at the STOP POINT (LAW 0) |
| AUD-14 candidate: adoption transport-match guard (pool sockets are built for ONE `settings.audio_transport`; a Twilio session adopting a browser-coded STT socket would mis-decode) | dormant trap in the current single-transport deploy; park as PT row when iter61 closes |
| Adopted-socket liveness check (post-adoption ping) | the TTL pool already guarantees freshness ≤240 s; adds provider-specific probe surface — separate decision |
| Real Twilio E2E (provisioned number → :8021) | owner-gated T6 territory; `scripts/fake_twilio_call.py` gives a headless proxy test first |
| AUD-9 token-cost note, INFO-1..INFO-9, T6 closeout | unchanged from iter60 plan (`/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter60_audit_fixes.md` §Deferred) |
| VOICE_TEST_TOKEN rotation (Telegram preview fetched the tokenized URL) | owner call; one sed on the worktree .env + server restart |
