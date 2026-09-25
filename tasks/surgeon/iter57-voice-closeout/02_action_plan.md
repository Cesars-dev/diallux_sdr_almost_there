# 02 ACTION PLAN — iter57 voice closeout

Fixes audit flaws F1 (hitl_ping env), F2/F3 (fail-safe embedder check), F5 (preflight probe shape), F4 (suite gate). Order: T1 → T2 → T3 → T4. No engine payload changes. All commits on `engine/iter56-state-delta-payload` only.

## T1 — Relaunch :8020 + boot self-check (the RAG gate)

### T1.1 Create `scripts/voice_preflight.py` (NEW)
Spec:
- stdlib only (argparse, json, sys, os, urllib.request, asyncio).
- `--url` (default `http://127.0.0.1:8020`).
- Loads `ROOT/.env` (same loader pattern as `hitl_ping.py`).
- **Check A (server, per F2):** GET `--url`/health, assert:
  - HTTP 200;
  - `python_venv` ends with `wt-iter56/engine/.venv`;
  - `embedder` == `ok`.
- **Check B (in-process RAG probe, per F5):** resolve `get_kb_store(get_settings())`; `retrieve_lanes([{"query": "boiler breakdown no heating", "scope": ["Intake"]}])` (scope slugs: use the same lane scoping the Intake state uses — read `graph/builder.py` lane tables at write time, hardcode only what the code actually declares); assert ≥ 1 chunk total.
- Print a report block: `sys.prefix`, `fastembed.__file__`, TextEmbedding import result, health fields, lane chunk counts.
- Exit 0 on all green; exit 1 on ANY failure with the failing check named.
- Never raises to the shell; all exceptions caught → exit 1 with message.

### T1.2 Patch `diallux/app.py` /health (E)
Inside `async def health()` add, fail-safe (F3):
```python
import sys
out["python_venv"] = sys.prefix
try:
    from fastembed import TextEmbedding  # noqa: F401  (lazy — never module-top)
    out["embedder"] = "ok"
except Exception as exc:
    out["embedder"] = f"import-failed: {exc}"   # ok stays True — monitoring, not a kill switch
```
Import `sys` at module top (stdlib, safe). No other app.py changes.

### T1.3 Test pin (N)
New `tests/test_voice_preflight.py`:
- pin 1: `/health` via `fastapi.testclient.TestClient` contains `embedder` key and `python_venv` key, `embedder` == `"ok"` (main venv in CI = has fastembed).
- pin 2: preflight script module imports cleanly (`importlib` on scripts path) — guard against syntax drift.
Suite must go 361 → 363 (2 new). If either pin is flaky, restructure — never weaken the assert.

### T1.4 Run order (exact commands)
1. `cd /tmp/opencode/wt-iter56/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → **363 passed** (F4: any other count = STOP, report).
2. Commit: `iter57 T1: voice preflight + /health venv+embedder fields` on the branch.
3. Launch (MANDATORY form): `cd /tmp/opencode/wt-iter56/engine && set -a && . ./.env && set +a && nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8020 > /tmp/opencode/iter57_voice_server.log 2>&1 & sleep 6 && curl -s http://127.0.0.1:8020/health`
   - NEVER `.venv/bin/uvicorn` (shebang trap).
4. `cd /tmp/opencode/wt-iter56/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/voice_preflight.py --url http://127.0.0.1:8020` → exit 0, ≥1 chunk.
5. Verify: health JSON `python_venv` tail `wt-iter56/engine/.venv`, `embedder: ok`; `grep -c "No module named" /tmp/opencode/iter57_voice_server.log` → 0.
6. **Gate:** anything red → kill server, fix, relaunch. Do NOT proceed to T2 with an unproven embedder.

## T2 — Voice call (owner on mic)

1. Telegram ping (F1 — ALWAYS this form):
   `cd /tmp/opencode/wt-iter56/engine && export $(grep -E "^TELEGRAM_(BOT_TOKEN|CHAT_ID)=" /home/julio/projects/video_strategy/.env | xargs) && .venv/bin/python scripts/hitl_ping.py "iter57: :8020 up + preflight green. Ready for the voice call — open http://127.0.0.1:8020/mic (tunnel if remote: ssh -N -L 8020:127.0.0.1:8020 julio@46.62.233.228). ~5 min, full intake→booking."`
   Confirm stdout `hitl_ping: sent` (bare invocation is FORBIDDEN — F1).
2. Owner runs the full intake→booking call on the mic page.
3. Fallback (only if mic path misbehaves): TTS a caller WAV, then `cd /tmp/opencode/wt-iter56/engine && .venv/bin/python scripts/fake_twilio_call.py --url ws://127.0.0.1:8020/media --input /tmp/opencode/caller.wav --output /tmp/opencode/out.wav`.
4. Live-watch during the call: `tail -f /tmp/opencode/iter57_voice_server.log` — RAG lanes chunk>0, zero `retrieve_lanes failed`.
- Scope: ONE call. No stress. Never touch :8000-:8003 or any production agent id.

## T3 — Trace + gates + ledger

1. Pull traces: `cd /tmp/opencode/wt-iter56/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/lf.py traces --hours 2 --name micbridge --limit 5` → pick newest.
2. Extract per-turn: TTFT, cache_read ladder, warm spans (`warm:lite:Intake`, `warm:Intake`), greeting anchors, RAG spans (industry pin, chunk counts) via `lf.py show/gens`.
3. Import ledger (MAIN checkout — json_logs live there): `cd /home/julio/projects/clean_diallux_SDR/engine && .venv/bin/python scripts/live_sql.py import --window "<HH:MM-HH:MM of call>" --run voice-iter56 --commit abde308 --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`
4. Gates (SQL-verified, not vibes):
   - turn-1 cache ≥ 1664;
   - cache_read climbs ≥ +1,000 first→peak;
   - zero `retrieve_lanes failed` lines in server log;
   - industry pin present in RAG spans;
   - TTFT worst ≤ 1,600 ms (voice band 634-782 steady from iter55).
5. Write `research/surgeon/iter56-state-delta-payload/03_voice_report.md`: transcript summary, gate table with SQL citations, warm spans, launcher note (trap + fix), any autopsy if a gate fails.

## T4 — Closeout + ASK

1. Cancel Cal.com test bookings created by THIS call (event 3801235 is REAL; PT-56 caveat F6 — list first, cancel only this session's uids; if key scope unknown → owner). Commands live at write time from the relevant `.env` (Cal API v2 `POST /v2/bookings/{uid}/cancel`).
2. Docs on the branch (iter56 pattern): commit `03_voice_report.md` evidence refs + `engine/ITERATIONS.md` iter56 line + `plans/PENDING_TASKS.md`: PT-53 flip → VERIFIED (battery), PT-55 flip → VERIFIED (battery), PT-45 note (harness greeting-warm default 0, chat-only), **new PT-57** (launcher trap → ops ticket).
3. Telegram ping (F1 form): closeout summary.
4. **ASK JULIO — merge gate. HOLD.** No merge, no tag, no `git-tree.sh` without say-so.

## Failure handling
- Any crash/fail → autopsy per AGENTS.md to `research/surgeon/iter57-voice-closeout/` + findings row + PT.
- Suite count drift → STOP, report, no proceed.
- Server log `No module named` after relaunch → interpreter sanity re-check (which python is uvicorn running) before anything else.
