# iter67 — Twilio LIVE phone lane: number → Caddy wss → engine → real call

## Meta
- Date: 2026-09-22
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: connect a REAL Twilio phone number to the self-hosted engine (TwiML webhook → Media-Streams WebSocket → Deepgram STT → LLM → TTS → ulaw_8000 back to the caller), deployed on this VPS behind Caddy.
- Status: **PLAN ONLY (not started — awaits owner approval + blocked inputs)**

## Compaction Context (session state at plan time)
- Project: Dialux SDR self-hosted voice engine (LangGraph), repo `clean_diallux_SDR` (fork; ORIGINAL still serves :8000–8003 — do not disturb).
- Main @ `5ab75a6`, clean, docs-only. Engine prod code on main = iter64c ladder merge `40b3b40` (tag `engine/iter64`, suite 427 green, Cartesia TTS, gpt-5.4 MODEL LAW).
- Branch `engine/iter66-elevenlabs-cutover` @ `e91af1a` (EL multi-stream TTS cutover + owner-ear-approved prod voice: "Sarah - Casual & Modern" `uG1JFy6xppqckhHCs2KG`, `eleven_turbo_v2_5`, speed 1.06, stability 0.5, style 1.0 — voice trials in `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter66-elevenlabs-cutover/VOICE_IDS.md`). iter66 is UNMERGED: pending T7 live mic test + owner G3 say-so.
- Branch `engine/iter65-model-defaults` @ `031bb73` — parked, has commits (was "zero" at closeout audit; re-preflight required before its own merge, closeout item E2).
- Owner resolved 2026-09-22: iter67 (Twilio) branches FROM MAIN, never stacks on iter66 (LAW 0 v2.1); iter66 merges first (after T7+G3), iter67 then absorbs it via `git merge main` — merging main INTO a side branch is agent-legal.
- Owner said an Twilio API key exists (credentials are NOT on disk anywhere — verified across `/home/julio/projects/.env`, all `/tmp/opencode/env_backup/*.env`, project .envs).
- Owner explicitly does not care about the git remote; push is out of scope.
- T7 mic server for iter66 is running: `127.0.0.1:8023` (pid 2206077, `/tmp/opencode/t7_uvicorn.log`).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| iter67 branches from main tip `5ab75a6`, NEVER from iter66 | LAW 0 v2.1: never stack work on an awaiting-merge branch (iter64c lesson) |
| iter67 = telephony lane work, provider-agnostic | EL provider swap is iter66's scope; iter67 wires the phone transport; final live-call provider = whatever `.env` has at that moment |
| Dev port `8024`, deploy port `8026` | 8000–8003 = ORIGINAL (never touch); 8005/8007/8008/8010/8020–8023 in use; 8024/8026 verified free |
| Deploy via systemd (`deploy/diallux.service`) adapted to `/opt/diallux-production` on port **8026** | service template's port 8000 COLLIDES with ORIGINAL's python on 0.0.0.0:8000 — must change |
| `/twiml` gets Twilio-signature validation (X-Twilio-Signature), fail-closed | Twilio webhooks cannot send bearer tokens; signature validation is the correct control for a public endpoint that spends LLM/TTS budget |
| NO scrapling / NO doc fetching needed for T1–T5 | Twilio Media-Streams protocol + provisioning are ALREADY implemented in the engine (`diallux/app.py` `/twiml` + `/media`, `scripts/provision_twilio_number.py`, `scripts/fake_twilio_call.py`, `deploy/Caddyfile`, `DEPLOYMENT.md`); only live-traffic facts (credentials, number, hostname) are missing |

## BLOCKED / NEEDS INPUT (owner)
| Item | Where to get it |
|---|---|
| `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` (basic-auth pair; an "API key" also works as SID+secret) | Owner pastes into `/tmp/opencode/wt-iter67/engine/.env` (gitignored — NEVER commit; `scripts/keyhound` before any push) |
| Approval to BUY a number (~$1.15/mo + $0.0085/min inbound) | Owner say-so; script buys via Twilio REST |
| Public hostname (proposed `calls.diallux-ai.site`) + DNS A record → VPS `46.62.233.228` | Owner (domain DNS) |
| Host Caddy edit approval (`/etc/caddy` + `caddy-apply`) | Owner (root; git-tracked config) |
| iter66 T7 + G3 merge (recommended BEFORE the final live call so the phone lane can run EL) | Owner (already staged — mic server up on :8023) |

## Environment & Dependencies
- Engine venv: `/tmp/opencode/wt-iter67/engine/.venv/bin/python` (worktree venv copy — use `python -m pip`, never `bin/pip`).
- Runtime deps (already in engine venv): `uvicorn`, `httpx`, `python-dotenv`, `websockets`, Deepgram/Cartesia/ElevenLabs adapters — versions as pinned in the engine requirements; no new packages for T1–T5. Twilio REST is called with raw `httpx` basic auth (no twilio package needed).
- Ports: dev `8024` (loopback), deploy `8026` (loopback), Caddy `443` public.
- Public URL: `https://<CALLS_HOST>/twiml` (webhook) and `wss://<CALLS_HOST>/media` (Media Streams; REQUIRES valid TLS — Caddy auto).
- Live webhooks used by the engine graph are the EXISTING `https://slots.diallux-ai.site/...` services — untouched.
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`; import via `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` (root SDK; NO sqlite3 CLI on this box — use `python3 -c "import sqlite3,..."`).
- Suite baseline: **427 passed** (main). Any new test pins are additive.

## Architecture
```
Owner phone (PSTN)
   └─► Twilio number (voice webhook = https://calls.diallux-ai.site/twiml)
          └─► Caddy :443 (auto TLS) ──reverse_proxy──► 127.0.0.1:8026  uvicorn diallux.app:app
                 ├─ POST /twiml  → TwiML: <Connect><Stream url="wss://calls.diallux-ai.site/media">
                 └─ WS  /media   → CallSession(transport="twilio")
                        ├─ inbound: audio/x-mulaw 8 kHz → Deepgram STT (wss)
                        ├─ brain: LangGraph agent (gpt-5.4) + RAG + slots/validator webhooks
                        └─ outbound: TTS → ulaw_8000 base64 media frames → Twilio → phone
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/app.py` | add X-Twilio-Signature validation on `/twiml` (fail-closed) | EDIT |
| `/home/julio/projects/clean_diallux_SDR/engine/tests/test_twilio_signature.py` | new pins for signature gate (valid/invalid/missing) | NEW |
| `/home/julio/projects/clean_diallux_SDR/engine/deploy/Caddyfile` | hostname template → `calls.diallux-ai.site`, port → 8026 | EDIT |
| `/home/julio/projects/clean_diallux_SDR/engine/deploy/diallux.service` | WorkingDirectory/ExecStart → `/opt/diallux-production`, port 8000 → **8026** | EDIT |
| `/home/julio/projects/clean_diallux_SDR/engine/DEPLOYMENT.md` | refresh: port 8026, systemd path, signature gate, fake-call command (drop stale `--tts-live` mention) | EDIT |
| `/etc/caddy/Caddyfile` (HOST, root — via `caddy-apply`) | add `calls.diallux-ai.site` site block per updated deploy/Caddyfile | HOST EDIT |
| `/opt/diallux-production/` (HOST) | rsync of engine tree from the worktree + `.env` with Twilio creds + `PUBLIC_BASE_URL=wss://calls.diallux-ai.site` | HOST NEW |
| `/tmp/opencode/wt-iter67/engine/.env` | owner-added Twilio creds + `PUBLIC_BASE_URL` (gitignored) | OWNER INPUT |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter67-twilio-live-lane/` | report + evidence | NEW (gitignored) |

## Deploy Rules
- NEVER touch: ORIGINAL's services (:8000–8003), live agents (`agent_f305…`, `agent_1698…`, `agent_87e4…`), `validator_endpoint/`.
- Host Caddy changes ONLY through the `caddy-apply` wrapper; Caddyfile is git-tracked at `/etc/caddy`.
- New systemd unit binds `127.0.0.1:8026` only; public exposure exclusively via Caddy.
- Secrets never printed; `.env` never committed; `scripts/keyhound` before any push.
- Cancel every Cal.com test booking (event 3801235 is REAL) after any battery.

## Tasks (in order)

### T1 — Branch + worktree
Goal: cut `engine/iter67-twilio-live-lane` from main `5ab75a6`.
Files: none (git only).
Commands:
```bash
cd /home/julio/projects/clean_diallux_SDR
git branch engine/iter67-twilio-live-lane 5ab75a6
git worktree add /tmp/opencode/wt-iter67 engine/iter67-twilio-live-lane
```
Dependencies: none.
Verification: `git -C /home/julio/projects/clean_diallux_SDR rev-parse engine/iter67-twilio-live-lane` == `5ab75a6`; `git -C /tmp/opencode/wt-iter67 status --short` clean.

### T2 — Suite baseline on the new branch
Goal: prove the branch is green before any change.
Commands:
```bash
cd /tmp/opencode/wt-iter67/engine && .venv/bin/python -m pytest tests -q
```
Verification: `427 passed, 0 failed` (or current main count per GIT_TREE).

### T3 — Local Twilio-lane loop (no Twilio account needed)
Goal: exercise `/media` end-to-end with the simulator (mulaw in → STT → LLM → TTS → mulaw out → `out.wav`).
Files: none changed (validation only).
Commands:
```bash
cd /tmp/opencode/wt-iter67/engine
ss -tln | grep '127.0.0.1:8024 ' || true        # must be free
set -a; . ./.env; set +a
.venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8024 &
sleep 5
.venv/bin/python scripts/fake_twilio_call.py --url ws://127.0.0.1:8024/media --input <test wav> --output /tmp/opencode/t67_out.wav
```
Dependencies: Deepgram + Cartesia keys already in `.env`.
Verification: non-empty `out.wav` with agent audio; log shows `contextId`/rounds; keep server log at `/tmp/opencode/t67_uvicorn.log`.

### T4 — Signature gate (hardening, fail-closed)
Goal: `/twiml` rejects requests without a valid `X-Twilio-Signature` (HMAC-SHA1 of URL+params with AUTH_TOKEN). Env flag `TWILIO_SIGNATURE_CHECK=true` default ON (dev override `=false` ONLY for `fake_twilio_call.py` local runs, which post without a signature).
Files: `diallux/app.py`, `tests/test_twilio_signature.py`, `.env.example`.
Commands: implement, then `cd /tmp/opencode/wt-iter67/engine && .venv/bin/python -m pytest tests/test_twilio_signature.py -q`.
Verification: new tests pass; full suite green (427+N).

### T5 — Deploy lane on the VPS (owner-gated commands)
Goal: systemd service on `127.0.0.1:8026` + public `calls.diallux-ai.site` via Caddy.
Files: `/etc/caddy/Caddyfile` (host), `/opt/diallux-production/` (host), systemd unit.
Commands (each needs owner say-so; run sequentially):
```bash
sudo rsync -a --delete /tmp/opencode/wt-iter67/engine/ /opt/diallux-production/ --exclude .venv --exclude .git
sudo cp /tmp/opencode/wt-iter67/engine/deploy/diallux.service /etc/systemd/system/
# owner edits /opt/diallux-production/.env (Twilio creds + PUBLIC_BASE_URL=wss://calls.diallux-ai.site)
sudo /opt/diallux-production/.venv/bin/python -m venv /opt/diallux-production/.venv  # or pip install -r requirements
sudo systemctl daemon-reload && sudo systemctl enable --now diallux
curl -s http://127.0.0.1:8026/health
# then Caddy: add site block (deploy/Caddyfile) to /etc/caddy + caddy-apply
```
Verification: `curl -s https://calls.diallux-ai.site/health` returns 200; wss handshake `wss://calls.diallux-ai.site/media` reachable.

### T6 — Buy number + point webhook (needs BLOCKED inputs)
Goal: real Twilio number ringing `calls.diallux-ai.site`.
Commands:
```bash
cd /opt/diallux-production && .venv/bin/python scripts/provision_twilio_number.py --area-or-code <owner choice> --host calls.diallux-ai.site
```
Verification: script prints the number + TwiML; Twilio console shows voice webhook `https://calls.diallux-ai.site/twiml`.

### T7 — LIVE call test (owner's ears) + ledger + report
Goal: owner calls the number; gates: greeting audible · ≥3 turns · digits read-back · barge-in · post-idle turn. Then import evidence.
Commands:
```bash
cd /home/julio/projects/clean_diallux_SDR
set -a && . /tmp/opencode/wt-iter67/engine/.env && set +a
python3 scripts/live_sql.py import --window "<HH:MM-HH:MM>" --run iter67-twilio-live --commit <branch sha> --db research/surgeon/iter48-rag-truth/ledger.db
```
Verification: `calls` row exists for `iter67-twilio-live`; report written to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter67-twilio-live-lane/NN_t67_report.md`; findings logged in ledger `findings`.

### T8 — Docs + iteration ledger (after owner say-so for merge)
`scripts/git-tree.sh`, ITERATIONS.md line, commit on branch; MERGE + tag `engine/iter67` = owner say-so only (LAW 0).

## Validation Plan (end-to-end)
1. T2 suite 427 green → T4 suite ≥428 green.
2. T3 simulator: bidirectional mulaw loop completes on `:8024` with real STT/LLM/TTS.
3. T5 `https://calls.diallux-ai.site/health` 200; invalid-signature POST to `/twiml` → 403 (fail-closed proven).
4. T6 console shows number + webhook; test call from owner's phone greets.
5. T7 ledger row + LV-gate table filled in the report.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| EL provider on the phone lane | iter66 scope — merge first (T7 mic + G3), then flip `.env` (`TTS_PROVIDER=elevenlabs`, `ELEVENLABS_*` per `.env.example` prod block) |
| iter65 re-preflight (E2) | separate closeout item, its own session |
| Outbound calls / SIP / recording | not requested |
| Repo push (Phase D) | owner said irrelevant for now |
