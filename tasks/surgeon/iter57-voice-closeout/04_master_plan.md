# 04 MASTER PLAN v2 — iter57 voice closeout (supersedes v1; bug analysis folded in)

Written after live re-verification of every load-bearing claim (2026-09-19). Suite confirmed **361 passed** (64 s) at `abde308` clean. `sys.prefix` through the worktree symlink prints `/tmp/opencode/wt-iter56/engine/.venv` (tested). 21 stale-shebang scripts found in the mirror venv (not 2). `CallRuntime._STATE_KBS` is a class attribute — readable without instantiating the runtime (tested with env loaded).

---

## PART A — BUG ANALYSIS (plan + proposed fixes)

| # | Source | Bug | Verdict / Fix in this plan |
|---|---|---|---|
| B1 | iter57 plan T1 verification | Health gate asserts `python_venv` ends `wt-iter56/engine/.venv` — true ONLY when launched via the worktree symlink. Launched from the main checkout, `sys.prefix` = `/home/julio/projects/clean_diallux_SDR/engine/.venv` (also correct — same venv). Brittle assertion = false red on a healthy launch. | Gate asserts the INVARIANT, not the path: `embedder == "ok"` AND `"Retell_AI_MCP_connection" not in python_venv`. Both paths pass, the old venv can never pass. |
| B2 | my earlier T0 proposal | `pip install --force-reinstall uvicorn` — (a) needs network through the egress proxy, (b) risks version drift 0.52.4→latest on a shared venv, (c) fixes ONE of **21** stale scripts (uvicorn, pip, pip3, pip3.12, fastapi, py.test, httpx, watchfiles, websockets, dotenv, …). | REJECTED. Replaced by offline anchored `sed` sweep of all 21 (line 1 only, exact old-path match) + post-fix verification + before/after evidence snapshot. |
| B3 | preflight design | `urllib.request` honors `http_proxy`/`https_proxy` env if ever set on this box (egress proxy exists) → localhost health check could route through proxy and fail spuriously. | Opener built with `ProxyHandler({})` — proxy-proof by construction. |
| B4 | preflight design (v1) | Hardcoded Intake slug list drifts if `_STATE_KBS` changes in a later iter. | Probe reads `CallRuntime._STATE_KBS["Intake"]` from the code itself (verified: class attr, import with env works, no runtime instantiation needed). |
| B5 | serve_voice.sh (new) | Failure modes: server dies when wrapper exits; silent relaunch while :8020 busy; wrong port (8000-8003 = production); log truncation destroys evidence; preflight-green but server already dead. | `setsid nohup` + PID file `/tmp/opencode/voice_8020.pid`; busy-port check → refuse; port hardcoded 8020 (refuse `8000|8001|8002|8003` regardless); log APPENDS with timestamp header; health poll ≤30 s then preflight; preflight fail → kill PID, exit 1. |
| B6 | test pin design | `scripts/` is not a package — `import voice_preflight` fails; module-level side effects would fire on import. | Pin uses `importlib.util.spec_from_file_location`; script is import-safe (all logic in functions, side effects only under `__main__`). |
| B7 | iter57 plan T1 | "expect 361+passed" — loose. | Exact gate: **363** (361 + 2 new pins). Any other count = STOP. |
| B8 | /health embedder field | First `/health` call pays the fastembed import (~1 s) — a monitoring poller could see a slow first ping. | Accepted (cached in `sys.modules` after first call; this is a boot gate endpoint, not a hot path). Noted in report. |
| B9 | iter57 plan T3 | TTFT gate "worst ≤1,600 ms" vs iter55 band 634-782 — generous, could mask regression. | Keep 1,600 as the HARD gate (matches plan), but the report must ALSO table p50/p90 against the 634-782 band; band drift > +300 ms steady = flag for iter58 even if gate passes. |
| B10 | iter57 plan meta | "TELEGRAM creds via hitl_ping fallback to video_strategy/.env" — false (script loads only `engine/.env`; worktree `.env` has no TELEGRAM keys; bare run silently skips, exit 0). | Every ping uses the export form + requires stdout `hitl_ping: sent`. (Audit F1, carried.) |
| B11 | venv fix scope | The shebang sweep is machine-local state (venv is gitignored) — invisible to future sessions if not recorded. | Evidence: before/after shebang snapshot into the report + PT-57 updated to "FIXED (machine-local, this box)" with the sed command recorded. |
| B12 | shared venv blast radius | Mirror venv is shared by main checkout + all worktrees (symlinks). A bad sed breaks everything. | sed anchored to line 1 + exact old-path prefix; verify 3 scripts after (`uvicorn --version`, `pip --version`, `py.test --version`); `python -m` forms unaffected (they never read shebangs). Old Retell venv NOT touched (production :8000-:8003 runs from it). |

---

## PART B — MASTER PLAN

Branch: `engine/iter56-state-delta-payload` @ `abde308` (worktree `/tmp/opencode/wt-iter56`). All commits on this branch only. No engine payload changes.

### T0 — Venv shebang sweep (machine-local ops fix, no git object)
1. Snapshot BEFORE: `grep -n "^#!" /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/{uvicorn,pip,pip3,fastapi,py.test} > /tmp/opencode/shebang_before.txt` (full list of the 21 into the same file via the grep -rl from audit).
2. Sweep (offline, anchored, line 1 only):
   `grep -rl "^#!/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/dialux-langgraph-production-v5/.venv/bin/python" /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/ | xargs sed -i '1s|^#!/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/dialux-langgraph-production-v5/.venv/bin/python[^ ]*|#!/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python3|'`
3. Verify: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/uvicorn --version` prints 0.52.4; `bin/pip --version` works; `bin/py.test --version` works; re-grep → **0** stale shebangs remain. `python -m uvicorn --version` still 0.52.4.
4. Rollback if anything red: reverse sed (swap paths) — recorded in report.
5. Gate: all green or STOP.

### T1 — Code edits (worktree only) + suite + commit
**Edit 1 — `diallux/app.py`** (health, fail-safe per B1/B8):
- Module top after `import logging`: `import sys`.
- Helper above the route (lazy import — NEVER module-top):
```python
def _embedder_status() -> str:
    try:
        from fastembed import TextEmbedding  # noqa: F401
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"import-failed: {exc}"
```
- In `health()` dict add: `"python_venv": sys.prefix, "embedder": _embedder_status(),` — `ok` stays True on failure (monitoring, not kill switch).

**Edit 2 — `scripts/voice_preflight.py`** (NEW; import-safe per B6, proxy-proof per B3, drift-proof per B4):
- `.env` loader copied from `scripts/hitl_ping.py:22-37`.
- `check_health(url)`: urllib with `ProxyHandler({})`; GET `/health`; assert `embedder == "ok"` AND `"Retell_AI_MCP_connection" not in python_venv` (B1 invariant). Print both fields.
- `check_rag()`: `get_settings()` → `rag.get_kb_store(settings)` (must not be None) → ONE `retrieve_lanes([{"query": "boiler broken no heating urgent repair", "scope": CallRuntime._STATE_KBS["Intake"]}])`; assert ≥1 chunk total; print per-lane counts. Prints `sys.prefix`, `fastembed.__file__`, TextEmbedding result.
- `main(argv)`: `--url` default `http://127.0.0.1:8020`; runs A then B; exit 0 only if both green; every failure caught → named message → exit 1. No retries (a gate that retries is not a gate).
- asyncio via `asyncio.run` for the probe.

**Edit 3 — `scripts/serve_voice.sh`** (NEW; the ONE legal launcher, per B5):
```bash
#!/usr/bin/env bash
# iter57: the only legal voice-test launcher. Usage: scripts/serve_voice.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
PORT=8020
case "$PORT" in 8000|8001|8002|8003) echo "REFUSED: prod port"; exit 1;; esac
if ss -tln | grep -q "127.0.0.1:$PORT "; then echo "REFUSED: :$PORT busy (kill it or check /tmp/opencode/voice_${PORT}.pid)"; exit 1; fi
set -a; . ./.env; set +a
LOG=/tmp/opencode/voice_server_${PORT}.log
echo "=== launch $(date -u +%FT%TZ) ===" >> "$LOG"
setsid nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port $PORT >> "$LOG" 2>&1 &
PID=$!; echo "$PID" > /tmp/opencode/voice_${PORT}.pid
for i in $(seq 1 30); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break; sleep 1; done
.venv/bin/python scripts/voice_preflight.py --url "http://127.0.0.1:$PORT" || { kill "$PID"; echo "PREFLIGHT FAILED — server killed"; exit 1; }
echo "VOICE SERVER READY (pid $PID, log $LOG) — RAG PROVEN"
```
`chmod +x`. Note: wrapper itself contains the port guard + busy check + preflight gate; a plain `nohup … &` launch remains possible but is now unnecessary — and even the OLD forbidden `.venv/bin/uvicorn` form is safe post-T0 (belt) while the wrapper is the suspenders.

**Edit 4 — `tests/test_voice_preflight.py`** (NEW, 2 pins, per B6):
- Pin 1: `TestClient(app).get("/health")` → `embedder == "ok"` and `python_venv` non-empty and `"Retell" not in python_venv` (pattern from `test_units.py:293-296`).
- Pin 2: load `scripts/voice_preflight.py` via `importlib.util.spec_from_file_location` → module has `check_health` and `check_rag` callables (import-safe contract).

**T1 run order:**
1. Write Edits 1-4.
2. `cd /tmp/opencode/wt-iter56/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → **363 passed** exactly (B7). Else STOP.
3. Commit on branch: `iter57 T1: voice preflight gate + serve_voice.sh launcher + /health venv+embedder fields`.

### T2 — Launch + boot gate
1. `cd /tmp/opencode/wt-iter56/engine && scripts/serve_voice.sh` → expect `VOICE SERVER READY … — RAG PROVEN`, preflight exit 0, ≥1 chunk.
2. `grep -c "No module named" /tmp/opencode/voice_server_8020.log` → 0.
3. Gate: green or STOP (fix on branch, re-run).

### T3 — Voice call (owner on mic)
1. Telegram ping (B10 — ALWAYS this form, require `hitl_ping: sent` on stdout):
   `cd /tmp/opencode/wt-iter56/engine && export $(grep -E "^TELEGRAM_(BOT_TOKEN|CHAT_ID)=" /home/julio/projects/video_strategy/.env | xargs) && .venv/bin/python scripts/hitl_ping.py "iter57: :8020 up, RAG proven. Ready for the voice call — http://127.0.0.1:8020/mic (tunnel: ssh -N -L 8020:127.0.0.1:8020 julio@46.62.233.228). ~5 min, full intake→booking."`
2. Owner on mic: ONE full intake→booking call. Live-watch `tail -f /tmp/opencode/voice_server_8020.log` — chunks > 0, zero `retrieve_lanes failed`.
3. Fallback only if mic path broken: TTS a caller WAV → `scripts/fake_twilio_call.py --url ws://127.0.0.1:8020/media --input /tmp/opencode/caller.wav --output /tmp/opencode/out.wav` (flags verified against argparse).

### T4 — Trace + gates + ledger
1. `lf.py traces --name micbridge` → newest trace; extract per-turn TTFT/cache, warm spans (`warm:lite:Intake`, `warm:Intake`), RAG spans (industry pin, chunk counts).
2. Ledger import FROM MAIN CHECKOUT (json_logs live there — AGENTS.md trap): `cd /home/julio/projects/clean_diallux_SDR/engine && .venv/bin/python scripts/live_sql.py import --window "<actual call window>" --run voice-iter56 --commit abde308 --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`
3. Gates (SQL-cited): turn-1 cache ≥1664; cache_read +≥1,000 first→peak; 0 `retrieve_lanes failed` log lines; industry pin in RAG spans; TTFT worst ≤1,600 ms hard + band report vs 634-782 (B9: >+300 ms steady drift = iter58 flag even on PASS).
4. Write `research/surgeon/iter56-state-delta-payload/03_voice_report.md` (gates table, warm spans, launcher autopsy→fix narrative incl. T0 evidence).

### T5 — Closeout + ASK
1. Cancel ONLY this session's Cal.com bookings (event 3801235 REAL; PT-56 anomaly → list-then-cancel; owner if key scope unknown).
2. Commit docs on branch: report refs + `engine/ITERATIONS.md` iter56 line + `plans/PENDING_TASKS.md` (PT-53→VERIFIED, PT-55→VERIFIED, PT-45 note, PT-57 = launcher trap FIXED machine-local + shebang sweep recorded).
3. Final Telegram ping (B10 form) with closeout summary.
4. **ASK JULIO — merge gate. HOLD.** No merge/tag/`git-tree.sh` without say-so.

---

## Hard rules
- Commits ONLY on `engine/iter56-state-delta-payload`. NEVER :8000-:8003 or production agent ids (`agent_16985b…`, `agent_f305…`, `agent_87e4…`). Old Retell venv NEVER touched (prod runs from it).
- NO sqlite3 CLI; NO bare hitl_ping; pip only as `python -m pip` (and T0 needs no pip at all). Evidence → research/. Keyhound before any push. Cancel ALL test bookings.

## External dependencies (owner)
- ~5 min mic for T3. Cal.com credential scope for T5 cancel, only if needed.

## Failure protocol
Gate red → fix on branch → full re-run. Crash/regression → autopsy to `research/surgeon/iter57-voice-closeout/` + ledger findings row + PT. No silent failures.

## Open issues
NONE. B1-B12 all resolved above.
