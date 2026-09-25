# 01 AUDIT — iter58: EOT 0.8 + PUBLIC Caddy voice endpoint (real-network mic latency)

Date: 2026-09-20. Auditor: opencode (surgeon circle, pre-execution).
Source of truth: plan `plans/plan_v5_iter58_eot08_public_mic.md` + live code at the cut
point `4cfb7a5` (= worktree `/tmp/opencode/wt-iter56`, branch `engine/iter56-state-delta-payload`).
Every claim below was re-verified against the actual files/box on 2026-09-20 — nothing is
copied from the plan unverified.

---

## A. Verified environment facts

| # | Fact | Evidence |
|---|---|---|
| A1 | Suite at cut point: **363 passed, 66.55 s** | `.venv/bin/python -m pytest tests -o addopts="" -q` in wt-iter56/engine (2026-09-20) |
| A2 | Versions: fastapi 0.141.1, starlette 1.6.0, uvicorn 0.52.4, websockets 16.1.1 | venv import check |
| A3 | DNS `voicetest.diallux-ai.site` = **NXDOMAIN today** (still no record) | `getent hosts` 2026-09-20 |
| A4 | DNS `flores.diallux-ai.site` → 46.62.233.228 (resolves) | `getent hosts` |
| A5 | :8020 server: pid **1741047**, started 2026-09-19 10:09:05 UTC, cwd `/tmp/opencode/wt-iter56/engine`, launched `.venv/bin/python -m uvicorn diallux.app:app` | ps + /proc/1741047/cwd; pid file `/tmp/opencode/voice_8020.pid` |
| A6 | Running server's `diallux/` code == `4cfb7a5` (commits 9b1f0a9→4cfb7a5 differ by 1 line in `scripts/voice_preflight.py` only; server started 10:09:05, between them) | `git diff --stat 9b1f0a9 4cfb7a5` |
| A7 | `.env` (wt-iter56 AND main): `DEEPGRAM_EAGER_EOT=true`, `DEEPGRAM_EAGER_EOT_THRESHOLD=0.6`; **no** `VOICE_TEST_TOKEN` anywhere; `LANGFUSE_HOST=http://localhost:3001` | grep of specific keys only |
| A8 | wt-iter56 `engine/.venv` is a **symlink** → `/home/julio/projects/clean_diallux_SDR/engine/.venv`; wt `.env` is a real file (1372 B) | ls -la |
| A9 | Branch `engine/iter58-eot08-public-mic` does NOT exist; worktree `/tmp/opencode/wt-iter58` does NOT exist; `/tmp/caddy` does NOT exist | git branch --list, ls |
| A10 | Telegram: `TELEGRAM_BOT_TOKEN`+`TELEGRAM_CHAT_ID` present in `/home/julio/projects/video_strategy/.env` (2 keys) | grep -c |
| A11 | **sudo is DENIED at the opencode permission layer** (`bash pattern sudo*` deny; allowlist covers iptables/docker/validator/etc. — NOT caddy-apply). OS-level passwordless sudo would still be blocked for me | permission rules observed live this session |
| A12 | Caddy: live `/etc/caddy/Caddyfile` = 161 lines; candidate (full copy + `voicetest` block, `flush_interval -1`) **validates as user julio**: `caddy validate … "Valid configuration"` exit 0 | `/tmp/opencode/caddy-preflight/candidate` |
| A13 | Git: main = `5e119ca`, **ahead 5 / behind 5** of origin/main; `plans/plan_v5_iter58_*.md`, `docs/CALL_FACTS.md`, `tasks/` all UNTRACKED on main | git status |
| A14 | `import_call.py` accepts exactly the plan's T4 flags (`--log --sid --branch --commit --port --model --trace --worktree` + verdicts) | argparse read, lines 91-98 |
| A15 | hitl_ping contract: loads env itself if present, **exits 0 always**; success = stdout `hitl_ping: sent` | scripts/hitl_ping.py:40-68 |

## B. What EXISTS (code, at 4cfb7a5 — with line refs)

- `diallux/app.py` (189 L): `/health` (47-62, already has `eager_eot` bool, `python_venv`, `embedder`); `/metrics` (65-71, lazy `observability.metrics` import, gated by `metrics_enabled`); `/mic` page (141-143, serves `_MIC_PAGE`); **`/mic/ws`** (146-189): `accept()` → loop over `ws.receive()`; bytes → `session.on_media(b64)` (157-160); text → JSON event dispatch (`start` 170-180, `stop` 181-182). `sid = uuid4().hex[:12]` (151). Imports today: base64, json, logging, sys, uuid, Path — **no os/secrets/time**.
- `diallux/static/mic/index.html` (170 L): AudioWorklet `pcm-capture` buffers **800 Int16 samples = 50 ms/message** (line 71); WS URL at 102-103 (`proto + location.host + '/mic/ws'`, auto-wss on HTTPS — plan claim verified); `ws.onmessage` handles ArrayBuffer only, JSON ignored (106-110); `ws.onclose` ignores the close event/code (111); no probe, no RTT, no first-audio stamps, no `?k=`.
- `diallux/observability/metrics.py` (61 L): `REGISTRY` + 6 latency histograms + 5 counters + `observe_turn_report` + `render()`. No mic/interarrival metric.
- `diallux/media/session.py` (754 L): EOT flow — `_on_eot` adopt/cancel (303-356), `_on_eager_eot` (380-400), `_on_turn_resumed` + grace (402-452); `settings.deepgram_eager_eot_threshold = … or 0.6` mutation at **176-177** (only when env unset); chunk counter heartbeats in `on_media` (277-285: first chunk + every 100). Writer task = **the only WS sender today** (714-749).
- `diallux/media/deepgram_stt.py` (212 L): `_url()` puts `eot_threshold`, `eot_timeout_ms`, and — when not None — **`eager_eot_threshold`** into the Deepgram v2 listen URL (74-87). → **EOT threshold is pure env wiring; no code edit needed for 0.6→0.8 (plan claim VERIFIED).**
- `diallux/config.py` (387 L): `deepgram_eot_threshold: 0.7` (277), `deepgram_eager_eot_threshold: None` (279), `deepgram_eager_eot: False` (281) + `deepgram_eager: True` (282). `get_settings()` is `@lru_cache` (385-387).
- `engine/scripts/serve_voice.sh` (37 L): port guard (8000-8003 refuse), busy-refusal, `set -a; . ./.env`, setsid nohup, pid file, 30 s health poll, preflight gate → **exports every .env var incl. a future `VOICE_TEST_TOKEN`**.
- `engine/scripts/voice_preflight.py` (129 L): proxy-proof urllib `/health` check + in-process RAG probe. Unaffected by iter58 changes (additive /health field).
- `engine/tests/`: 27 top-level test files; conventions: `sys.path.insert` header, explicit `Settings(...)` for units, `TestClient(app)` for HTTP/WS pins (`test_units.py:290-303` mic page + **token-less** `/mic/ws` handshake pin; `test_voice_preflight.py:15-25` /health key pins — additive-safe). `pytest.ini`: `testpaths=tests`, `addopts=-q`.
- Caddy live config (161 L): pattern for streaming proxies = `reverse_proxy … { flush_interval -1 }`; `flores` block = bare `reverse_proxy localhost:8000` (51-53).

## C. What's MISSING (gaps the plan must fill)

1. Token gate on `/mic/ws` (nothing checks `k` / `VOICE_TEST_TOKEN` today — public exposure would be an open spend tap).
2. Probe echo (`probe`→`probe_ack`) — no client↔server RTT measurement exists.
3. Server-side mic chunk inter-arrival metric — `on_media` counts chunks but never timestamps arrival deltas.
4. Client-side first-audio timeline (page-open → ws-open → first audio) + RTT display + `mic_stats` report.
5. `/health` `eager_eot_threshold` field.
6. Public TLS path (Caddy site block + DNS) and the `.env` threshold flip 0.6→0.8.

## D. Bugs / risks found (SURGEON FINDINGS)

| # | Sev | Finding | Resolution taken in this plan |
|---|---|---|---|
| F1 | HIGH | **Plan File Map missed an existing-test edit**: `tests/test_units.py:290-303` (`test_mic_page_serves_and_ws_handshakes`) connects `/mic/ws` WITHOUT a token and expects a live connection. The token gate (fail-closed) closes it with 4401 → **this pin breaks** the moment `VOICE_TEST_TOKEN` exists in `.env` (T3 adds it) or env is armed in the test process. | Action plan edits this pin to control `VOICE_TEST_TOKEN` explicitly (monkeypatch delenv/setenv + `?k=`), and pins the 4401 rejection as a NEW assertion inside it. |
| F2 | HIGH | **Sudo grant does not reach the agent**: opencode's permission layer denies `sudo *` (allowlist has no `caddy-apply`). Even with OS passwordless sudo granted, I cannot run `sudo /usr/local/bin/caddy-apply`. | Master plan keeps apply = OWNER-run (plan's original design). Alternative documented for owner: add opencode permission rule `bash +sudo /usr/local/bin/caddy-apply*` (then agent can apply autonomously). |
| F3 | HIGH | DNS `voicetest.diallux-ai.site` still NXDOMAIN (A3) → T2/T4 blocked until record exists OR fallback chosen. Plan says decide BEFORE T2. | Surfaced as a go-gate ASK: (a) owner adds A record → 46.62.233.228, or (b) fallback path-route `flores.diallux-ai.site/voice/*` (JS WS-URL prefix change rides T1; Caddy `handle_path` strips `/voice`, server unchanged). |
| F4 | MED | `VOICE_TEST_TOKEN` absent from all `.env`s → once the gate deploys, fail-closed locks everyone out (including the owner's test call) until set. | Owner supplies token at go (written ONLY into wt-iter58 `.env`, gitignored). Token never printed to chat/logs/git. |
| F5 | MED (resolved) | Concurrent WS sends: probe_ack from the mic handler would race the session writer's PCM sends (writer is the sole sender today). websockets 16.1.1 new-asyncio impl behavior unknown from docs. | **Tested empirically** (uvicorn 0.52.4 + websockets 16.1.1, scratch app on 127.0.0.1:8127): 178 binary + 101 text interleaved, zero errors → direct `send_text` from the handler is SAFE. Evidence: `/tmp/opencode/iter58_sendtest_app.py`. |
| F6 | MED (resolved) | Pin shape for the 4401 gate + `query_params` support unverified. | **Tested empirically**: `WebSocketDisconnect code=4401` surfaces on `receive_text()` inside `with client.websocket_connect(...)`; `ws.query_params.get("k")` works (starlette 1.6.0). Evidence: `/tmp/opencode/iter58_testclient_check.py`. |
| F7 | LOW | `get_settings()` is lru_cached and `session.start()` MUTATES `settings.deepgram_eager_eot_threshold` to 0.6 when env-unset (session.py:176-177) → `/health` shows the mutated value after any call starts. With env=0.8 no mutation fires (0.8 truthy). | Accepted — fail-safe display semantics: field shows the EFFECTIVE threshold. Documented, no code change. |
| F8 | LOW | Inter-arrival must be observed at the app.py receive loop (transport boundary), NOT in `session.on_media` (no timestamps there; also shared with Twilio path where inter-arrival means something else). | Action plan observes in `/mic/ws` loop only, gated by `metrics_enabled`. |
| F9 | LOW | Probe/mic_stats frames arrive on the text path BEFORE `start` (session is None) — handler must not require a session. | Handler is session-optional by construction (dispatch before `start` check). |
| F10 | LOW | Suite runs may inherit `VOICE_TEST_TOKEN` from a sourced env → pins must control the var explicitly, not assume unset. | All token pins use `monkeypatch.delenv(..., raising=False)` / `setenv`. |
| F11 | LOW | Caddy `flores` fallback needs `handle_path /voice/*` + wrapping the existing bare proxy in `handle` (Caddyfile 51-53) — the naive "add a line inside the block" from the plan is not valid Caddy syntax. | Exact fallback block written in action plan T2-alt. |
| F12 | LOW | main is ahead 5/behind 5 of origin → no push/pull in this iter (LAW 0; keyhound before any push anyway). | Master plan: commits on branch only; docs commit decision rides T5 ASK. |
| F13 | LOW | Untracked docs on main (plan file, CALL_FACTS.md, tasks/) — last session never committed them (LAW 0 says docs → main). | Ride T5 closeout ASK (with iter57's owed closeout). |
| F14 | LOW | Old server must be stopped before relaunch — `serve_voice.sh` REFUSES a busy port (by design). | T3 kills pid from `/tmp/opencode/voice_8020.pid`, waits for port-free, then launches from wt-iter58. |
| F15 | INFO | Running server (A5/A6) will be replaced at T3 by wt-iter58 build (same lineage + instrumentation). Old pid 1741047 is NOT one of the do-not-touch stale pids (:8000/:8005/:8007/:8008 untouched). | Confirmed safe to kill at T3. |
| F16 | INFO | iter57 closeout debt (ledger import `voice-iter56`, ITERATIONS.md line, PT flips, merge ASK) still owed — plan's deferred table already carries it. | Rides iter58 T5 ASK. |

## E. Claims from the plan — verified TRUE (no action)

- EOT 0.6→0.8 is `.env`-only: `DEEPGRAM_EAGER_EOT_THRESHOLD` → `Settings.deepgram_eager_eot_threshold` → Deepgram URL param (deepgram_stt.py:82-83). No `session.py` edit needed (File Map "—" is correct).
- Mic page needs NO JS change for wss (proto auto-switch, index.html:102-103) — only `?k=` + probe/RTT additions.
- `serve_voice.sh` is the only legal launcher and exports `.env` fully (VOICE_TEST_TOKEN will reach `os.environ`).
- `import_call.py` T4 command matches its argparse exactly.
- Telegram ping form (export from video_strategy/.env + require `hitl_ping: sent`) is correct per hitl_ping.py contract.
- Suite gate "363 + new pins" baseline confirmed (A1); pytest addopts override works.
- Caddy candidate validates as non-root (A12) — apply remains the only root step.

## F. Open items requiring OWNER input (carried to master plan ASK)

1. DNS: A record `voicetest` → 46.62.233.228 **or** fallback `flores/voice/*` (F3) — needed before T2.
2. `VOICE_TEST_TOKEN` value (F4).
3. caddy-apply: owner runs it, or adds opencode permission rule for the agent (F2).
4. Go for execution (this circle stops at 04_master_plan.md per owner instruction).
