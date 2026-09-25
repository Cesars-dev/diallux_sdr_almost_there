# 04 MASTER PLAN — iter58: EOT 0.8 + PUBLIC Caddy voice endpoint (real-network mic latency)

Status: **AIRTIGHT — awaiting owner GO** (circle halted here per owner instruction
2026-09-20: "stop at master plan for my go"). Sources 01_audit / 02_action_plan /
03_cross_reference live alongside; nothing superseded, nothing archived.

Everything below was verified against the live box and the actual code at the cut
point `4cfb7a5` on 2026-09-20: suite **363 passed / 66.55 s**; concurrent-WS-send
safety **empirically proven** (scratch app, zero errors); 4401 pin shape **empirically
proven** (`WebSocketDisconnect code=4401` on `receive_text()`); Caddy candidate
**validates as non-root** (`Valid configuration`, exit 0); DNS `voicetest` **still
NXDOMAIN**; running :8020 server = pid 1741047 from wt-iter56 (diallux code ==
`4cfb7a5`, safe to replace at T3).

---

## PART A — ASK JULIO (the go-gate; execution does not start without these)

| # | Question | Options |
|---|---|---|
| A1 | **GO for execution?** | GO → run PART B in order. NO → park. |
| A2 | **Public URL — DNS or fallback?** (needed before the T1 commit; decides ONE JS line) | (a) Add A record `voicetest.diallux-ai.site` → `46.62.233.228` in your DNS panel (primary; JS unchanged). (b) Fallback: path-route `flores.diallux-ai.site/voice/*` → 127.0.0.1:8020 (no DNS needed; JS WS URL gets `/voice` prefix; Caddy flores block rewritten per 02 T2-alt). |
| A3 | **VOICE_TEST_TOKEN** — the /mic/ws gate is fail-closed; without it nobody (incl. you) can call | Set it yourself in `/tmp/opencode/wt-iter58/engine/.env` after T0 (`VOICE_TEST_TOKEN=<secret>`), or hand me the value at GO (it lands ONLY in that gitignored .env — never chat logs/git). |
| A4 | **caddy-apply mode** (T2) | (a) You run `sudo /usr/local/bin/caddy-apply /tmp/caddy/voicetest-candidate-caddyfile` when I ping (candidate pre-validated). (b) Add opencode permission rule `bash +sudo /usr/local/bin/caddy-apply*` (+ sudoers entry) and I apply autonomously. NOTE: OS-level passwordless sudo alone does NOT reach me — the opencode permission layer denies `sudo *`. |

## PART B — Execution (on GO; exact diffs live in 02_action_plan.md)

Branch: NEW `engine/iter58-eot08-public-mic` @ `4cfb7a5`; worktree `/tmp/opencode/wt-iter58`;
venv = symlink to main `engine/.venv`; `.env` copied from wt-iter56. ONE behavior variable:
`DEEPGRAM_EAGER_EOT_THRESHOLD` 0.6 → 0.8 (env-only; verified wiring deepgram_stt.py:82-83).
Everything else is measurement (T1) or ops (T2).

### T0 — Branch + worktree + env (no code)
Per 02 T0. Verify: `git log --oneline -1` → `4cfb7a5`; `import fastembed; from fastembed import TextEmbedding` OK through the symlinked venv.

### T1 — Instrumentation code + suite + commit
1. Apply 02 Edits 1-5 (app.py token gate 4401 + probe_ack + inter-arrival + /health field;
   metrics.py histogram; index.html `?k=` + RTT probe + first-audio timeline + 4401 surfacing;
   test_units.py F1 fix; NEW tests/test_iter58_mic_probe.py — 4 pins).
   If A2 = fallback: also apply the ONE JS prefix line from 02 T2-alt BEFORE committing.
2. Suite: `cd /tmp/opencode/wt-iter58/engine && .venv/bin/python -m pytest tests -o addopts="" -q`
   → **exact gate 367 passed** (363 + 4). Any other count = STOP, fix, re-run.
3. Commit on branch: `iter58 T1: mic token gate (4401) + probe RTT + chunk inter-arrival metric + /health eager_eot_threshold + client first-audio timeline`.

### T2 — Caddy public endpoint (ops; per A2/A4 answers)
1. Build candidate: full copy of `/etc/caddy/Caddyfile` + voicetest block (or flores
   rewrite per fallback) at `/tmp/caddy/voicetest-candidate-caddyfile`; validate with
   `/usr/bin/caddy validate --config … --adapter caddyfile` (exit 0 — pre-proven in audit A12).
2. Apply per A4. Verify: `curl -s https://<host>/health` → 200 JSON from the VPS; from the
   Mac with NO tunnel: page loads, WS connects only with `?k=`, console shows 4401 without.

### T3 — EOT 0.8 + token + restart (the behavior variable)
1. Owner token in place (A3); `sed` threshold to 0.8 in wt-iter58 `.env`.
2. `kill $(cat /tmp/opencode/voice_8020.pid)` (pid 1741047 — verified replaceable, NOT a
   stale do-not-touch pid); wait port-free; `bash scripts/serve_voice.sh` from wt-iter58.
3. Gates: launcher prints `VOICE SERVER READY … RAG PROVEN`; `/health` → `eager_eot_threshold: 0.8`,
   `embedder: ok`; zero `No module named` in the fresh log section.

### T4 — Owner live call over the PUBLIC URL (no SSH tunnel)
1. Telegram ping (export form; REQUIRE stdout `hitl_ping: sent`) with the public URL + token reminder.
2. Owner: ~10 min full intake→booking call. Agent live-watches
   `tail -f /tmp/opencode/voice_server_8020.log` (chunks flowing, `mic_stats` line, zero
   `retrieve_lanes failed`).
3. Extract + import (`import_call.py` per 02 T4.3 — flags pre-verified).
4. Gates: inter-arrival **p90 ≤ 65 ms/chunk** (vs 73-198 starved); **ZERO** EOT-adopts
   < 800 ms (was 4 ≤ 1 s at 0.6); eager adoption ≥ 80%; turn-1 cache ≥ 1664; TTFT p50 ≤ 900 ms.
5. Cancel ALL Cal test bookings (event 3801235 is REAL).

### T5 — Report + closeout + ASK
Per 02 T5: report `research/surgeon/iter58-eot08-public-mic/01_report.md`; CALL_FACTS.md row +
`facts` rows (venv-python SQLite only); PENDING_TASKS PT-58/PT-59; ONE docs commit to main
(includes the currently-untracked plan/CALL_FACTS/tasks files — F13); telegram closeout;
**ASK JULIO**: keep 0.8? merge? keep voicetest for Twilio cutover? + iter57 owed closeout (F16).

## Hard rules (violations = revert on sight)
- Commits ONLY on `engine/iter58-eot08-public-mic`. NO merge/tag/push without owner say-so
  (main is ahead 5/behind 5 origin — do not push/pull). `scripts/keyhound` before any push.
- Engine server :8020 ONLY via `scripts/serve_voice.sh` from wt-iter58. NEVER bind :8000-:8003;
  NEVER touch stale :8000/:8005/:8007/:8008 pids or production agents (`agent_16985b…`,
  `agent_f305…`, `agent_87e4…`).
- Token/secrets never in git, chat logs, or server logs (rejection log line carries no `k`).
- NO sqlite3 CLI (venv python). pip only as `python -m pip` (not needed here). Evidence → research/.
- NO SSH tunnels for T4 — the whole point is the real network path.

## Failure protocol
Gate red → fix on branch → full suite re-run → re-verify. Crash/regression → autopsy to
`research/surgeon/iter58-eot08-public-mic/` + findings row + PT. Rollbacks (seconds-scale):
threshold sed back to 0.6; token removal = fail-closed; per-file `git checkout 4cfb7a5 -- <file>`;
Caddy restore via `/etc/caddy/backups/` (owner).

## Open issues
NONE. All flaws found by the circle are resolved in 02; remaining decisions are PART A
(owner) by design.
