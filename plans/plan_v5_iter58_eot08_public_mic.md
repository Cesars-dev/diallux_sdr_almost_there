# PLAN — v5 iter58: EOT 0.8 + PUBLIC Caddy voice endpoint (real-network mic latency, no SSH bridge)

## Meta
- Date: 2026-09-20
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: (1) retune the too-aggressive Deepgram eager-EOT threshold 0.6 → 0.8; (2) expose the :8020 test server publicly through Caddy (`wss`, no SSH bridge) so mic latency is measured over the REAL network path — the same shape Twilio will use; (3) instrument BOTH ends (client RTT probe + server chunk-rate metric) so "was it my hardware or the bridge" is finally answerable; (4) log every fact into `call_facts.db` + the tracked index `docs/CALL_FACTS.md`.
- Status: **DECISIONS LOCKED 2026-09-20** (fallback path-route `flores/voice/*`; token = agent-generated; caddy-apply = agent under sudo pending opencode permission rule) — execution pending GO
- Branch: NEW `engine/iter58-eot08-public-mic`, cut from `engine/iter56-state-delta-payload` @ `4cfb7a5` (carries iter57's preflight + `serve_voice.sh` + /health fields).
- The behavior variable of this iteration is EXACTLY ONE: the eager-EOT threshold (0.6 → 0.8). Everything else is measurement (T1) or ops (T2).

## Compaction Context (session 2026-09-19/20 — pin, do not re-derive)

- **iter57 state:** T0-T2 DONE on branch `engine/iter56-state-delta-payload` @ `abde308` + 2 commits (`9b1f0a9` preflight+serve_voice+/health fields, `4cfb7a5` preflight sys.path fix). Rollback branch `engine/iter57-pre-start` @ `abde308`. 21 stale-shebang scripts in `engine/.venv/bin/` were repaired (evidence `/tmp/opencode/shebang_before.txt` / `shebang_after.txt`). `scripts/serve_voice.sh` = the only legal launcher (port guard, busy-refusal, preflight gate). Voice server :8020 live as pid 1741047 since 2026-09-19 10:09:05 UTC; suite **363 passed**.
- **The voice call `56766c0e5a58` (2026-09-19 23:21:54→23:32:02 UTC, 52 turns, cap):** CONFIRMED iter56 code with RAG alive (53 `state_in_delta` markers, 0 RAG failures, trace `2372a40f4e82`, server pid 1741047). Owner complaints verified in-log:
  1. **Audio breaking up = mic-bridge starvation:** mic chunks arrived at **73-198 ms/chunk (nominal 50)** across the WHOLE call → browser→SSH-tunnel→VPS transport starved. No Cartesia/TTS errors server-side (`llm→tts` 120-260 ms, `tts→audio_out` ~1 ms — pipeline clean).
  2. **EOT too sensitive:** `StartOfTurn → EOT adopted` median **2203 ms** but 4 events ≤1 s (967/801/519 ms) — with `DEEPGRAM_EAGER_EOT_THRESHOLD=0.6` a tiny pause fires EagerEOT → agent starts talking.
  3. **5-6 s before the agent's first word:** server-side is only **~2.7 s** (23:21:52.3 session init → 54.0 Deepgram connected (+1.7 s) → 54.5 Cartesia (+0.5 s) → 55.0 greeting first audio OUT (+0.4 s)). KB/RAG loading is ASYNC (`session.py:195-215`, fire-and-forget — never blocks the greeting; completes +3.4/+3.9 s during it). The rest of the 5-6 s is client-side (page load, mic permission, WS handshake, tunnel, playback buffering) — NOT yet measurable, hence the instrumentation task.
  4. **NO wasted/fake LLM calls:** 39 eager starts → **34 adopted** (`no rerun`), **5 abandoned (13%)**; `eager_final_match=false` ×0; barge-in resumes ×5; 6 turns with 2 rounds = the DESIGNED tool+speech two-trip pattern (t7/15/24/31/35/36). Premature EOT did NOT multiply LLM calls.
  - First-5 turns e2e: 1004/1298/1057/1612/867; TTFT 618-1182; warm `warm:Intake` 3360 ms / `warm:lite:Intake` 3858 ms (vs iter55 call 2336/2446 — ~1 s slower but landed; turn-1 cache 1664).
- **The "great latency / dumb agent" reference call:** `1480fbd1f29d` / trace `ecbc42943d42`, ran on `engine/iter38b-gpt54` @ `491a7a3` (:8007, 2026-09-09, gpt-5.4) — turn-1 stt→llm 1966 ms then ~16/17 rounds <1.2 s with one 2.9 s transition spike; agent was blind (no tools/KB at the right moments, 9/10 date bug, 2pm loop, no booking). `491a7a3` is an ancestor of current HEAD, **131 commits back**. Full report: `research/surgeon/iter39-spike-kill/01_analysis_call_1480fbd1f29d.md`.
- **Tracking scaffolding exists:** `research/surgeon/call-facts/` (`call_facts.db` tables calls/turns/rag/warm/facts + view `call_compare`; `import_call.py`; `schema.sql`; `README.md`) + tracked index **`docs/CALL_FACTS.md`** (one line per call, points at the DB). Both calls imported (`1480fbd1f29d`, `56766c0e5a58`); 5 `facts` rows logged for the complaints above. No per-call MD files (owner decision).
- **EOT config today:** `engine/.env` has `DEEPGRAM_EAGER_EOT=true`, `DEEPGRAM_EAGER_EOT_THRESHOLD=0.6`; defaults at `diallux/config.py:277-281` (`deepgram_eot_threshold: 0.7`, `deepgram_eager_eot_threshold: None`, `deepgram_endpointing_ms: 150`). Eager fires the speculative LLM turn; real EOT adopts it (`head_start_ms` = eager→EOT overlap; the mechanism that keeps TTFT off the hot path — DISABLING it would re-add ~850 ms to every turn and break the turn-1 lite-warm await).
- **Mic page:** `diallux/static/mic/index.html` — AudioWorklet `pcm-capture`, `getUserMedia`, WS = `proto + location.host + '/mic/ws'` (~line 103; over HTTPS `proto` becomes `wss` automatically — NO JS change needed for the URL).
- **Caddy (LIVE infra, root-owned):** config `/etc/caddy/Caddyfile` (git-tracked in `/etc/caddy/.git`; backups in `/etc/caddy/backups`); apply tool `/usr/local/bin/caddy-apply <candidate>` = validate → backup → atomic replace → graceful reload, root-owned via sudoers — **2026-09-20: owner granted a 30-min passwordless sudo window AND added the opencode permission rule `bash +sudo /usr/local/bin/caddy-apply*` (active after a TUI reload; verified denied before the reload) — so the AGENT applies; the OWNER runs it only if the rule is absent**. No wildcard DNS: `agent-test.diallux-ai.site` / random subdomains are NXDOMAIN; `flores.diallux-ai.site` → 46.62.233.228 (this VPS) resolves.
- **Stale old test servers still listening — DO NOT TOUCH:** :8000 (pid 2659243, since Sep 6, binds 0.0.0.0, log `/tmp/opencode/uvicorn_bridge.log`), :8005 (pid 2099198, Sep 9), :8007 (pid 1602409, Sep 12), :8008 (pid 3166619, Sep 11). None logged calls on 09-19/20.
- **MongoDB/Mongoose: REJECTED for now** — Langfuse already traces every call (spans/gens) and `call_facts.db` stores the facts; Mongoose is a Node ODM and the engine is Python; a third datastore adds a mess, not information. Deferred (see Deferred table).
- House rules in force: LAW 0 (docs → main, code → branch → ASK), evidence → `research/` (gitignored), `.env` never committed, `scripts/keyhound` before any push, Cal.com event 3801235 is REAL (cancel test bookings), never touch production agents (`agent_16985b…` voice, `agent_f305…` sdr, `agent_87e4…` chat) or live :8001-:8003.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| EOT eager threshold 0.6 → **0.8** via `.env` only (`DEEPGRAM_EAGER_EOT_THRESHOLD`), no code-default change this iter | owner-ordered; one variable; instantly reversible; a couple-hundred-ms pause must no longer end the turn |
| `/health` gains `eager_eot_threshold` field | makes the variable VISIBLE and verifiable without reading .env |
| Public exposure = **path-route `flores.diallux-ai.site/voice/*` → 127.0.0.1:8020** via Caddy `handle_path` (strips `/voice`) — the `voicetest` DNS record is REJECTED (fallback chosen 2026-09-20) | `flores` already resolves to this VPS (46.62.233.228); no DNS change; `handle_path` → ZERO engine path changes; kills the SSH bridge that starved audio |
| **Token gate on `/mic/ws`**: query param `k` must equal `VOICE_TEST_TOKEN` env; fail-closed if env unset. **No such token exists in any `.env` (verified 2026-09-20) → the AGENT generates it at T0** (`openssl rand -hex 24`) and writes it ONLY to `wt-iter58/engine/.env` (gitignored, mode 660); owner supplies nothing | public endpoint without auth = anyone calls the agent → OpenAI/Cartesia spend + REAL Cal bookings |
| `caddy-apply` = **AGENT-run** under the owner's 30-min passwordless sudo, gated on the opencode permission rule `bash +sudo /usr/local/bin/caddy-apply*` (added 2026-09-20; effective after TUI reload); if the rule is absent, OWNER runs the pre-validated candidate | apply is the only root step; candidate validates as user julio (exit 0, pre-proven) |
| Client-side RTT probe (page JS) + server `mic chunk inter-arrival` histogram | mic latency must be measured END-TO-END; server-only metrics cannot separate network from engine |
| NO SSH tunnels for these tests | the 09-19 call proved the bridge starves audio (73-198 ms/chunk vs 50 nominal) |
| Instrumentation rides the branch (measurement only); behavior variable = threshold only | one-variable discipline (iter55 T0 pattern) |
| NO MongoDB/Mongoose | third store adds a mess; Langfuse + SQLite already cover tracing + facts |
| Stale servers :8000/:8005/:8007/:8008 stay untouched | killing them is a separate owner decision; they are old builds but currently harmless |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| ~~DNS `voicetest`~~ **RESOLVED 2026-09-20** → path-route `flores.diallux-ai.site/voice/*` (no DNS needed) | — |
| ~~`VOICE_TEST_TOKEN` from owner~~ **RESOLVED 2026-09-20** → agent-generated at T0, stored in `wt-iter58/engine/.env` only | — |
| `caddy-apply` (root-only) | AGENT runs `sudo /usr/local/bin/caddy-apply /tmp/caddy/iter58-flores-candidate` once the opencode rule `bash +sudo /usr/local/bin/caddy-apply*` exists; otherwise OWNER runs the same one-liner (candidate pre-validated) |
| Owner on the mic for the T4 live call (~10 min, from the Mac, NO tunnel) | owner schedules — Telegram ping fires before the ask |

## Environment & Dependencies
- Worktree: `/tmp/opencode/wt-iter58` — NEW: `cd /home/julio/projects/clean_diallux_SDR && git worktree add /tmp/opencode/wt-iter58 engine/iter58-eot08-public-mic` after `git branch engine/iter58-eot08-public-mic 4cfb7a5`. Venv: `/tmp/opencode/wt-iter58/engine/.venv` (symlink → main venv; fastembed 0.8.0 verified). Suite: `cd /tmp/opencode/wt-iter58/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → expect **363 + new pins**.
- Env: `/tmp/opencode/wt-iter58/engine/.env` (has LANGFUSE_*, OPENAI_*, DEEPGRAM_*, CARTESIA_*, RETELL_API_KEY, RAG_*; ADD `VOICE_TEST_TOKEN=<owner>`; CHANGE `DEEPGRAM_EAGER_EOT_THRESHOLD=0.6` → `0.8`).
- Langfuse: `http://localhost:3001` — `cd /tmp/opencode/wt-iter58/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/lf.py health|traces|show`.
- Call-facts: `/home/julio/projects/clean_diallux_SDR/research/surgeon/call-facts/call_facts.db` + `import_call.py` (see its README).
- Tracked index: `/home/julio/projects/clean_diallux_SDR/docs/CALL_FACTS.md`.
- Caddy: config `/etc/caddy/Caddyfile` (root-owned, git-tracked at `/etc/caddy`); apply tool `/usr/local/bin/caddy-apply` (**agent-run** under the 30-min sudo grant IF the opencode rule `bash +sudo /usr/local/bin/caddy-apply*` is added — else owner); VPS IP `46.62.233.228`; `flores` TLS already live.
- Ports: engine test server **:8020 ONLY** (`serve_voice.sh` hard-codes it + prod-port guard). NEVER bind/start :8000-:8003. :8005/:8007/:8008 stale — untouched.
- NO sqlite3 CLI — use `engine/.venv/bin/python -c "import sqlite3,…"`.
- Telegram ping: `cd /tmp/opencode/wt-iter58/engine && export $(grep -E "^TELEGRAM_(BOT_TOKEN|CHAT_ID)=" /home/julio/projects/video_strategy/.env | xargs) && .venv/bin/python scripts/hitl_ping.py "<text>"` — fires BEFORE every owner ask.
- Reference baseline numbers to beat (this call, SSH bridge): mic inter-arrival 73-198 ms/chunk; EOT-adopt median 2203 ms with 4 fires ≤1 s; first-5 e2e 1004/1298/1057/1612/867; TTFT 618-1182.

## Architecture (one block)
```
Mac Chrome (mic PCM, AudioWorklet)
   │ HTTPS  page https://flores.diallux-ai.site/voice/mic     (NO SSH tunnel)
   │ WSS    wss://flores.diallux-ai.site/voice/mic/ws?k=<VOICE_TEST_TOKEN>
   ▼
Caddy :443 (flores block: handle_path /voice/* → strip prefix, flush_interval -1) ──► 127.0.0.1:8020
   ├─ GET  /mic        → bridge page (sends probe RTT: client t0 → server echo → RTT shown on page)
   ├─ WS   /mic/ws     → token check (fail-closed) → CallSession (SAME pipeline as Twilio /media)
   └─ server metrics: diallux_mic_chunk_interarrival_ms histogram (nominal 50 ms/chunk)
CallSession: Deepgram flux STT (EAGER EOT @ 0.8, EOT @ 0.7) ─ eager LLM start ──► LangGraph (iter56 payload)
   ──► gpt-5.4 ──► Cartesia sonic-3.6 ──► PCM back over the same WSS
Everything logged: Langfuse trace (micbridge-*) + call_facts.db + docs/CALL_FACTS.md row
```

## File Map
| File (absolute) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter58/engine/diallux/app.py` | (a) `/health` += `eager_eot_threshold` (fail-safe); (b) `/mic/ws` handshake: token check `k == VOICE_TEST_TOKEN` (fail-closed, close 4401 on miss); (c) probe echo: `{"event":"probe"}` client msg → immediate server reply `{event:"probe_ack", t_server}` | E |
| `/tmp/opencode/wt-iter56/engine/diallux/static/mic/index.html` → in NEW worktree `/tmp/opencode/wt-iter58/engine/diallux/static/mic/index.html` | pass `?k=` into the WS URL **+ the `/voice` path prefix** (flores route: `.../voice/mic/ws`); send probe every 2 s once WS open; display RTT (ms) + last-5 on the page; log first-audio timestamps (page-open → ws-open → first audio) to console + a `mic_stats` line to the WS | E |
| `/tmp/opencode/wt-iter58/engine/diallux/observability/metrics.py` | + `diallux_mic_chunk_interarrival_ms` histogram, observed from the mic WS receive loop (per-chunk delta, ms) | E |
| `/tmp/opencode/wt-iter58/engine/diallux/media/session.py` | NO behavior change. (EOT threshold comes from env — no edit) | — |
| `/tmp/opencode/wt-iter58/engine/tests/test_iter58_mic_probe.py` | pins: health carries `eager_eot_threshold`; token check closes 4401 without `k`; probe echoes `probe_ack`; metrics histogram registered | N |
| `/tmp/opencode/wt-iter58/engine/.env` | `DEEPGRAM_EAGER_EOT_THRESHOLD=0.8`; `VOICE_TEST_TOKEN=<owner-supplied>` (gitignored — never committed) | E |
| `/tmp/caddy/iter58-flores-candidate` | FULL Caddyfile with the `flores` block rewritten to `handle_path /voice/*` → 127.0.0.1:8020 (see T2 exact content) | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter58-eot08-public-mic/01_report.md` | measurement report (mic latency over real network, EOT delays before/after 0.8, first-audio timeline) | N |
| `/home/julio/projects/clean_diallux_SDR/docs/CALL_FACTS.md` | +1 row per tracked call + observations | E |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/call-facts/call_facts.db` | imports via `import_call.py` + `facts` rows | E |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-58 (EOT threshold adopt/flip), PT-59 (transport verdict), PT-45 note if hit | E |

## Deploy Rules
- Engine server: ONLY via `cd /tmp/opencode/wt-iter58/engine && set -a && . ./.env && set +a && nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8020 > /tmp/opencode/voice_server_8020.log 2>&1 &` — or simply `bash scripts/serve_voice.sh` (which does exactly this + preflight gate). NEVER `.venv/bin/uvicorn` (shebang trap — fixed in iter57 T0 but the rule stands).
- Caddy changes ONLY via the candidate flow: agent writes `/tmp/caddy/iter58-flores-candidate` (FULL Caddyfile = current config with the `flores` block rewritten to `handle_path /voice/*` → 8020), validates locally with `/usr/bin/caddy validate --config <candidate> --adapter caddyfile` (exit 0, pre-proven), then runs `sudo /usr/local/bin/caddy-apply /tmp/caddy/iter58-flores-candidate` (agent-run once the opencode rule exists; else OWNER runs it). NEVER edit `/etc/caddy/Caddyfile` in place.
- NEVER bind/start :8000-:8003 (live ORIGINAL), never kill :8005/:8007/:8008/:8000 stale pids, never touch production agents.
- The public endpoint can create REAL bookings — **cancel every test booking** (Cal event 3801235 is REAL) after every call.
- `scripts/keyhound` before any push. `.env`/tokens never in git or chat.

## Tasks (in order)
### T1 — Instrumentation (measurement only — no behavior change)
Goal: make mic latency END-TO-END visible (client↔server RTT + chunk arrival rate) and the EOT variable visible on /health.
Files: `diallux/app.py`, `diallux/static/mic/index.html`, `diallux/observability/metrics.py`, `tests/test_iter58_mic_probe.py`.
Commands (full):
1. Implement per File Map: `/health` += `eager_eot_threshold` (read `get_settings().deepgram_eager_eot_threshold`, fail-safe); `/mic/ws`: on connect read query param `k`, compare `VOICE_TEST_TOKEN` env — mismatch or unset env → `await ws.close(code=4401)`; on `{"event":"probe","t":<client_ms>}` reply `{"event":"probe_ack","t_server_ms":<monotonic ms>}` (client computes RTT); observe chunk inter-arrival into the new histogram (nominal 50 ms/chunk = 100 chunks/5 s heartbeats already logged).
2. `cd /tmp/opencode/wt-iter58/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → expect **363 + N new pins passed** (exact count from the pins written).
3. Commit on branch: `iter58 T1: mic probe RTT + chunk inter-arrival metric + /health eager_eot_threshold + token gate`.
Verification: suite green; `curl -s http://127.0.0.1:8020/health | .venv/bin/python -m json.tool` shows `eager_eot_threshold`; TestClient pin proves 4401 without token; `/metrics` renders the new histogram after a synthetic probe.
Dependencies: iter57 code (serve_voice.sh, /health fields) on the cut point `4cfb7a5`.
### T2 — Caddy public endpoint via `flores` path-route (ops; agent applies with sudo)
Goal: `https://flores.diallux-ai.site/voice/*` → `127.0.0.1:8020` (WSS supported; `/voice` stripped by `handle_path`).
Commands (full):
1. Agent copies the CURRENT `/etc/caddy/Caddyfile` to `/tmp/caddy/iter58-flores-candidate` and REWRITES the `flores` block (today: bare `reverse_proxy localhost:8000`) to:
```
flores.diallux-ai.site {
	handle_path /voice/* {
		reverse_proxy 127.0.0.1:8020 {
			flush_interval -1
		}
	}
	handle {
		reverse_proxy localhost:8000
	}
}
```
2. Validate (no root): `/usr/bin/caddy validate --config /tmp/caddy/iter58-flores-candidate --adapter caddyfile` → exit 0.
3. **AGENT** (opencode rule `bash +sudo /usr/local/bin/caddy-apply*` granted 2026-09-20; else OWNER) runs: `sudo /usr/local/bin/caddy-apply /tmp/caddy/iter58-flores-candidate`.
4. Verify (from the VPS): `curl -s https://flores.diallux-ai.site/voice/health | head -5` → 200 JSON. From the Mac (NO SSH tunnel): open `https://flores.diallux-ai.site/voice/mic?k=<token>` — page loads; WS connects (page shows RTT).
Verification: page loads over public HTTPS; WS connects only WITH the token; without token the WS closes 4401 (browser console / server log); `/health` reachable via the path.
Dependencies: T1 deployed (restart :8020 first — T3 performs the restart); caddy-apply run (agent or owner).
Note: the `voicetest` DNS record remains an OPTION for the later Twilio cutover — NOT used this iteration.
### T3 — EOT threshold 0.6 → 0.8 (the ONE behavior variable)
Goal: a short pause no longer ends the turn.
Commands (full):
0. Token (no owner input — none exists in any `.env`, verified 2026-09-20): `openssl rand -hex 24` → append `VOICE_TEST_TOKEN=<hex>` to `/tmp/opencode/wt-iter58/engine/.env` (gitignored, mode 660 preserved; never printed to chat/git).
1. `cd /tmp/opencode/wt-iter58/engine && sed -i 's/^DEEPGRAM_EAGER_EOT_THRESHOLD=.*/DEEPGRAM_EAGER_EOT_THRESHOLD=0.8/' .env && grep DEEPGRAM_EAGER_EOT .env`
2. Restart: `kill $(cat /tmp/opencode/voice_8020.pid) 2>/dev/null; sleep 2; ss -tln | grep -q "127.0.0.1:8020 " && echo STOP-port-busy; cd /tmp/opencode/wt-iter58/engine && bash scripts/serve_voice.sh` → last line `VOICE SERVER READY … RAG PROVEN`.
3. Verify: `curl -s http://127.0.0.1:8020/health | .venv/bin/python -c "import sys,json;print(json.load(sys.stdin)['eager_eot_threshold'])"` → `0.8`.
Verification: /health shows 0.8; preflight still exits 0; server log has zero `No module named`.
### T4 — Owner live call over the PUBLIC URL (no SSH) + measurement
Goal: the REAL answer to "hardware or bridge?" and "is 0.8 right?".
Commands: owner opens `https://flores.diallux-ai.site/voice/mic?k=<token>` (URL also delivered via the Telegram ping) and runs a full intake→booking call (~5 min). Agent live-watches `tail -f /tmp/opencode/voice_server_8020.log`.
Extraction: mic chunk inter-arrival (expect ~50 ms/chunk over the real path — if STILL 73-198 ms, the network link is the culprit, NOT the SSH bridge); RTT from the page probe; StartOfTurn→EOT-adopted delays (expect: median up, ≤1 s fires ≈ 0); greeting first-audio (client-side, from page console stats); per-turn TTFT/cache/e2e; import into call_facts: `cd /tmp/opencode/wt-iter58/engine && .venv/bin/python ../research/surgeon/call-facts/import_call.py --log /tmp/opencode/voice_server_8020.log --sid <sid> --branch engine/iter58-eot08-public-mic --commit <sha> --port 8020 --model gpt-5.4 --trace <id> --worktree /tmp/opencode/wt-iter58`.
Verification (gates): mic inter-arrival p90 ≤ 65 ms/chunk (vs 73-198 starved); EOT-adopt: ZERO fires <800 ms (was 4 ≤1 s at 0.6); eager adoption rate ≥ 80%; turn-1 cache ≥ 1664; TTFT p50 ≤ 900 ms; cancel ALL Cal test bookings created (event 3801235 REAL).
### T5 — Report + closeout + ASK
Goal: evidence + decision.
Commands: write `research/surgeon/iter58-eot08-public-mic/01_report.md` (before/after table: transport rate, EOT delays, first-5 turns, client RTT); append `docs/CALL_FACTS.md` row + `facts` rows; Telegram ping (`hitl_ping.py`, export form); commit docs on branch.
Verification: report on disk with SQL/log citations; bookings cancelled; ping sent; then **ASK JULIO** — (a) keep threshold 0.8? (flip config default later), (b) merge branch, (c) keep the `flores/voice` endpoint for Twilio cutover prep.

## Validation Plan (end-to-end)
1. T1: suite green + `/health` shows `eager_eot_threshold` + token 4401 + probe ack works locally.
2. T2: public HTTPS/WSS reachable from the Mac WITHOUT any SSH tunnel; token enforced.
3. T3: /health shows 0.8; preflight green.
4. T4: live call — mic inter-arrival p90 ≤ 65 ms/chunk (vs 73-198 starved), EOT ≤1 s fires = 0, first-5-turn e2e table, trace complete in Langfuse, imported to `call_facts.db`.
5. T5: report + bookings cancelled + ASK.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| MongoDB/Mongoose "log everything" | REJECTED this iter: Langfuse already traces every span/gen and `call_facts.db` stores the facts — a third store (Node-ecosystem ODM in a Python engine) adds mess, not information. If owner insists, separate ops plan |
| Min-trailing-silence EOT guard (~250-300 ms) in `session.py` | the threshold bump may be sufficient; add ONLY if T4 still shows premature EOT (one variable per iteration) |
| `DEEPGRAM_EAGER_EOT=false` (nuclear) | REJECTED — would re-add ~850 ms TTFT to every turn and break the turn-1 lite-warm await |
| iter38b vs iter56 A/B on :8020 | separate session; branch `engine/iter38b-gpt54` @ `491a7a3` ready for it |
| Real Twilio number → `/twiml` test | after T4 proves the public path; needs owner's Twilio config |
| Killing stale :8005/:8007/:8008 servers | owner call; not this plan |
| iter57 T4/T5 closeout (ledger import `voice-iter56`, ITERATIONS.md line, PT flips, merge ASK) | still owed from iter57 — rides T5's ASK, do not silently drop |
