# PLAN — iter69: Full-server migration of the Dialux engine + endpoints to a NEW VPS (exact clone, no Docker)

## Meta
- Date: 2026-09-23
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: Move the complete working stack (engine state machine + 3 webhook endpoints + pgvector RAG DB + Caddy + fastembed weights) from this VPS (Hetzner `46.62.233.228`) to a NEW server as an EXACT clone (rsync + fresh venv + systemd + Caddy — NOT Docker), then run a full endpoint/voice/booking audit on the new box before cutover.
- Status: PLAN ONLY (not started — awaits owner approval + BLOCKED items)

## Compaction Context
(the condensed session state; a fresh agent continues from here alone)

**What the system is.** `/home/julio/projects/clean_diallux_SDR/engine` is the LangGraph voice SDR ("Linda"): a 9-state machine (`Intake→Discovery→Closer→Offer→contact_details→ConfirmSlots→VerifyLead→Booking→Closing`) defined config-as-code in `/home/julio/projects/clean_diallux_SDR/engine/agent/llm.json`, prompts in `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/*.md`, KB corpus in `/home/julio/projects/clean_diallux_SDR/engine/agent/knowledge_bases/*.md`, typed dvs in `/home/julio/projects/clean_diallux_SDR/engine/diallux/schema.py`. FastAPI app `/home/julio/projects/clean_diallux_SDR/engine/diallux/app.py` exposes `/twiml`, WS `/media` (Twilio), `/mic` + WS `/mic/ws` (browser, gated by `VOICE_TEST_TOKEN`), `/health`, `/metrics`. Transitions are hard-gated in `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/tools.py`; gate booleans (`slot_verified`, `data_verified`, `phone_confirmed`, `booking_verified`) are SERVER-OWNED — only the webhook endpoints can write them.

**Live topology on the OLD box (verified 2026-09-23).**
- Engine lanes: `:8000` = ORIGINAL (`/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/diallux-langgraph-production-v5`, 0.0.0.0 — DO NOT TOUCH); `:8021/:8022/:8024` test lanes; `:8026` = iter67 lane from `/opt/diallux-production` (systemd `diallux.service`, User=julio, `python -m uvicorn`, 127.0.0.1).
- Endpoints (all loopback, behind Caddy `slots.diallux-ai.site`): cal_slots `:8001` (Cal.com API v2 + SQLite `slots.db` + Telegram notify), time `:8002`, validator `:8003`. Live copies run from the ORIGINAL repo path (`/home/julio/projects/Retell_AI_MCP_connection/{cal_slots_endpoint,time_endpoint,validator_endpoint}`); the fork has equivalent code in `/home/julio/projects/clean_diallux_SDR/services/`.
- DB: engine RAG Postgres at `127.0.0.1:5434`, db `diallux`, user `diallux`, password inside `/home/julio/projects/clean_diallux_SDR/engine/.env` (`DATABASE_URL`). Tables: `kb_chunks` (233 rows), `kb_chunks_v2` (210 rows, THE live table), plus staging tables.
- Embedder: LOCAL in-process fastembed ONNX, model `snowflake/snowflake-arctic-embed-m` (768-d), weights cache at `/home/julio/fastembed/models` (417 MB for `-m`; `-s`/`-l` variants unused). Live .env pins: `RAG_EMBEDDING_MODEL=snowflake/snowflake-arctic-embed-m`, `RAG_TABLE_NAME=kb_chunks_v2`, `RAG_FILTER_SCORE=0.24`.
- Langfuse: self-hosted ON THIS BOX at `:3001` (docker stack with own Postgres/ClickHouse/MinIO). Engine .env: `LANGFUSE_ENABLED=true`, `LANGFUSE_HOST=http://localhost:3001`, keys `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`. Listener is 0.0.0.0:3001.
- Caddy (host systemd) serves many sites; relevant blocks: `slots.diallux-ai.site` (strip_prefix `/validator-function`→:8003, `/time-function`→:8002, default→:8001) and `twilio.diallux-ai.site` (/twiml,/health,/media → 127.0.0.1:8026, else 404).
- HMAC auth: engine signs every tool call with `X-Retell-Signature: v=<ts_ms>,d=hex(HMAC-SHA256(key, raw_body+ts))` using `RETELL_API_KEY` (sign code `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/tools.py:496` — digest over raw+ts ONLY, URL not in digest). All 3 endpoints verify raw_body+ts and REFUSE TO START without `RETELL_API_KEYS`/`RETELL_API_KEY`. No bypass flag exists. Nothing in the endpoints calls Retell — the key is a plain shared secret.
- Twilio: `/twiml` verifies `X-Twilio-Signature` (HMAC-SHA1 of url+sorted params with `TWILIO_AUTH_TOKEN`), fail-closed, default ON (iter67). `/media` pins `transport="twilio"` regardless of `AUDIO_TRANSPORT` env (iter67).

**Git state.** Repo `origin` = `https://github.com/Cesars-dev/clean-dialux-sdr.git`. `main` @ `8e06fe9` (contains merged iter52→iter66; tags `engine/iter65`, `engine/iter66`). PENDING merges: `engine/iter67-twilio-live-lane` @ `0394a3b` (4 commits: pins `fastembed==0.8.0` in `engine/requirements.txt`, adds `twilio_signature_check` + `/media` transport pin, rewrites `engine/deploy/Caddyfile` + `engine/deploy/diallux.service` for port 8026, DEPLOYMENT.md) and `engine/iter68-speech-flow` @ `c6159ce` (1 commit: `speech_filter_observability` flag). `git merge-tree` verified BOTH merge clean onto main. Per LAW 0, code merges need owner say-so.

**Resolved decisions from this session.**
1. NO Docker. Exact clone = rsync tree + rebuild venv + systemd + Caddy (matches how the old box actually runs).
2. Retell stack IGNORED (no proxy_guard, no Retell MCP, no retell/ config, no hosted agents). The `RETELL_API_KEY` HMAC stays as the engine↔endpoints shared secret, copied verbatim.
3. Langfuse NOT migrated. New box points `LANGFUSE_HOST` at the OLD box's Langfuse (`http://46.62.233.228:3001`) with the SAME keys. Fail-safe: engine runs fine if Langfuse unreachable.
4. Sizing: 2 vCPU / 4 GB / 40 GB minimum for 1–2 concurrent calls; set `LOCAL_EMBED_THREADS=2` on a 2-vCPU box. No GPU (arctic-m on CPU ≈ 20–35 ms/query).
5. Ports replicated EXACTLY on the new box: engine `:8026`, cal_slots `:8001`, time `:8002`, validator `:8003`, Postgres `:5434` → the only .env edit needed is `LANGFUSE_HOST` (+ nothing else; `DATABASE_URL` stays `localhost:5434`).
6. pgvector on the new box via Docker image `pgvector/pgvector:pg16` mapped `127.0.0.1:5434` (mirrors `engine/docker-compose.yml` db service), data restored from `pg_dump` of the old 5434 cluster.
7. Audit-phase trick: tool URLs in `agent/llm.json` are hardcoded to `https://slots.diallux-ai.site/...`. For the pre-cutover audit we TEMPORARILY rewrite them to `http://127.0.0.1:800x` on the new box (HMAC is URL-independent — verified), audit everything, then restore the pristine `agent/llm.json` before DNS cutover so production runs the exact bytes.
8. `VOICE_TEST_TOKEN`, `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY`, `ELEVENLABS_API_KEY`, Cal.com keys, `RETELL_API_KEY` — copied VERBATIM ("leave everything as is").
9. VOICE LAW carried: `TTS_PROVIDER=cartesia`, `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` (dated pin — NEVER the rolling alias), `CARTESIA_VOICE_ID=829ccd10-f8b3-43cd-b8a0-4aeaa81f3b30`, `CARTESIA_SPEED=1.12` as in the live `.env`. MODEL LAW carried: `OPENAI_MODEL=gpt-5.4`.

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| NEW server: IP, SSH access, OS+arch (assume Ubuntu 24.04 x86_64), 2 vCPU/4GB/40GB | Julio provisions; hostname/IP into `NEWBOX` placeholders before executing |
| Owner approval to merge `engine/iter67-twilio-live-lane` + `engine/iter68-speech-flow` into main (LAW 0) | Julio. Fallback if declined: ship from main @ `8e06fe9` and manually `pip install fastembed==0.8.0` on the new box |
| Twilio creds (`TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`) — NOT in `engine/.env` | Julio / root env. Fallback: run the repoint from the OLD box |
| DNS control for `slots.diallux-ai.site` + `twilio.diallux-ai.site` A-records | Julio / DNS provider |
| Langfuse reachable FROM the new box: confirm firewall allows `NEWBOX → 46.62.233.228:3001` | T2 verification step below |
| pg_dump read access on 5434 (it may be a docker container on the old box) | T4 identifies the 5434 server (`ss -ltnp` + `docker ps` via sudo) |
| Which Cal.com test event to use for the E2E booking + immediate cancel | Event `3801235` is REAL — mandatory cancel after (AGENTS.md) |

## Environment & Dependencies
New box (Ubuntu 24.04 x86_64 assumed):
- `python3.12` + `python3.12-venv` (matches old box cpython-312 venv)
- `caddy` (official apt repo)
- Docker (for `pgvector/pgvector:pg16` only) OR `postgresql-16` + `postgresql-16-pgvector` — default plan uses Docker
- `libgomp1` (onnxruntime runtime dep), `rsync`, `postgresql-client-16` (for restore), `tzdata`
- Python deps: installed from `/home/julio/projects/clean_diallux_SDR/engine/requirements.txt` (with iter67: includes `fastembed==0.8.0`); endpoint deps from `services/{cal_slots_endpoint,time_endpoint,validator_endpoint}/requirements.txt` (pinned: fastapi==0.135.3, uvicorn[standard]==0.44.0, python-dotenv==1.0.1, requests==2.32.3, python-dateutil==2.9.0.post0, pytz==2026.3.post1)
- Model weights: `/home/julio/fastembed/models/models--Snowflake--snowflake-arctic-embed-m` (417 MB) copied from old box
- Files copied (with .env, since rsync copies gitignored files): `engine/` + `services/{cal_slots_endpoint,time_endpoint,validator_endpoint}/` from `/home/julio/projects/clean_diallux_SDR`
- Services/ports on NEW box: engine 127.0.0.1:8026 · cal_slots 127.0.0.1:8001 · time 127.0.0.1:8002 · validator 127.0.0.1:8003 · pgvector 127.0.0.1:5434 · Caddy 0.0.0.0:80/443. NOTHING else exposed.
- System user: `julio` (uid irrelevant) created on new box; systemd SYSTEM units (not user units) for all 4 services, `User=julio`.

## Architecture (target state on NEW box)
```
Internet ──► Caddy :443 (auto-TLS)
   twilio.diallux-ai.site   /twiml /health /media ──► 127.0.0.1:8026  (engine systemd diallux.service)
   slots.diallux-ai.site    /validator-function* ────► 127.0.0.1:8003  (validator)
                            /time-function* ─────────► 127.0.0.1:8002  (time)
                            /* ──────────────────────► 127.0.0.1:8001  (cal_slots → api.cal.com)
engine :8026 ──► OpenAI (gpt-5.4) · Deepgram flux WS · Cartesia sonic-3.6-2026-08-27 WS
             ──► 127.0.0.1:5434 pgvector (diallux / kb_chunks_v2)
             ──► in-process fastembed arctic-m (/home/julio/fastembed/models)
             ──► https://slots.diallux-ai.site/* (HMAC-signed; via /etc/hosts→127.0.0.1 in audit phase)
             ──► LANGFUSE_HOST=http://46.62.233.228:3001  (OLD box, remote, fail-safe)
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_iter69_server-migration_2026-09-23.md` | this plan | NEW (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/migration-2026-09-23/` | audit receipts (baseline-oldbox.md, health-diff.txt, probe outputs) | NEW (gitignored) |
| NEW box `/opt/diallux-production/` | full rsync of `engine/` + `services/` | NEW |
| NEW box `/opt/diallux-production/engine/agent/llm.json` | audit phase ONLY: tool URLs `https://slots.diallux-ai.site/*` → `http://127.0.0.1:800x/*`; RESTORED byte-exact before cutover | EDIT then RESTORE |
| NEW box `/opt/diallux-production/engine/.env` | one edit: `LANGFUSE_HOST=http://46.62.233.228:3001` (everything else verbatim) | EDIT (1 line) |
| NEW box `/etc/systemd/system/diallux.service` | from `engine/deploy/diallux.service` (paths already `/opt/diallux-production`, port 8026, User=julio) | NEW |
| NEW box `/etc/systemd/system/{cal-slots,time,validator}.service` | adapted from `services/*/​*.service` unit files: WorkingDirectory→`/opt/diallux-production/services/<name>`, ExecStart→new venv path, User=julio, port 8001/8002/8003 | NEW |
| NEW box `/etc/caddy/Caddyfile` | ONLY the two site blocks (`slots.diallux-ai.site`, `twilio.diallux-ai.site`) copied from old `/etc/caddy/Caddyfile` + `engine/deploy/Caddyfile` | NEW |
| OLD box: nothing changes | read-only source | — |

## Deploy Rules
- OLD box stays 100% untouched and serving until cutover (DOCTRINE §6). No stops, no edits.
- NEW box: everything binds `127.0.0.1` except Caddy 80/443. Firewall: allow 22, 80, 443 ONLY.
- `.env` files never enter git; `scripts/keyhound` before any push; never print secret values.
- NEVER touch: old-box `:8000` original engine, live agent IDs, old Langfuse stack.
- Test bookings: Cal.com event `3801235` is REAL — cancel EVERY test booking immediately after each E2E test.
- Merge gate (LAW 0): `engine/iter67` + `engine/iter68` merge only on owner say-so; migration otherwise ships from `main` @ `8e06fe9` + manual fastembed pin.
- Restore byte-exactness: `agent/llm.json` on the new box MUST hash-match the old box copy at cutover (`sha256sum`).

## Tasks (in order)

### T0 — Baseline capture on the OLD box (before anything moves)
Goal: freeze the "known-good" evidence the new box will be diffed against.
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/migration-2026-09-23/baseline-oldbox.md`
Commands (full):
```bash
mkdir -p /home/julio/projects/clean_diallux_SDR/research/surgeon/migration-2026-09-23
cd /home/julio/projects/clean_diallux_SDR/engine
.venv/bin/python -m pytest tests -q 2>&1 | tail -3   # record PASS COUNT verbatim
set -a; . ./.env; set +a
curl -s http://127.0.0.1:8024/health > /home/julio/projects/clean_diallux_SDR/research/surgeon/migration-2026-09-23/health-old.json
curl -s http://127.0.0.1:8002/time-function/today
curl -s -X POST https://slots.diallux-ai.site/check_availability -H 'Content-Type: application/json' \
  -H "X-Retell-Signature: $(python3 - <<'PY'
import hmac,hashlib,time,json,os
raw=json.dumps({"args":{"account_id":"diallux_live","timezone":"Europe/London","slot_target_date":"2026-09-24","current_reservation_uids":""}}).encode()
ts=str(int(time.time()*1000)); key=os.environ["RETELL_API_KEY"].encode()
print(f"v={ts},d={hmac.new(key,raw+ts.encode(),hashlib.sha256).hexdigest()}")
PY
)" -d '{"args":{"account_id":"diallux_live","timezone":"Europe/London","slot_target_date":"2026-09-24","current_reservation_uids":""}}' | head -c 400
.venv/bin/python -c "import sqlite3;print('slots.db rows:',sqlite3.connect('/home/julio/projects/clean_diallux_SDR/services/cal_slots_endpoint/slots.db').execute('select count(*) from sqlite_master').fetchone())"
PGPASSWORD=$(grep -oP 'DATABASE_URL=postgresql://diallux:\K[^@]+' /home/julio/projects/clean_diallux_SDR/engine/.env) psql -h 127.0.0.1 -p 5434 -U diallux -d diallux -tc "select 'kb_chunks_v2',count(*) from kb_chunks_v2 union all select 'kb_chunks',count(*) from kb_chunks;"
sha256sum /home/julio/projects/clean_diallux_SDR/engine/agent/llm.json
```
Dependencies: none.
Verification: `baseline-oldbox.md` exists with: pytest count, `/health` JSON, today-output, availability probe (must be `"ok": true` with slots), DB counts (210/233), llm.json sha256.

### T1 — Approve merges + prepare the source tree
Goal: ship from a tree that has iter67's `fastembed==0.8.0` pin + iter67/68 fixes.
Files: git refs only.
Commands (full, on owner say-so):
```bash
cd /home/julio/projects/clean_diallux_SDR
git merge --no-ff engine/iter67-twilio-live-lane -m "merge: engine/iter67-twilio-live-lane (owner-approved for migration)"
git merge --no-ff engine/iter68-speech-flow -m "merge: engine/iter68-speech-flow (owner-approved for migration)"
scripts/git-tree.sh
```
Dependencies: owner say-so (BLOCKED table).
Verification: `git log --oneline -3` shows both merges; `grep fastembed engine/requirements.txt` → `fastembed==0.8.0`.
Fallback (if NOT approved): skip merges; after T3 run `/opt/diallux-production/engine/.venv/bin/python -m pip install fastembed==0.8.0` and record the deviation in the audit report.

### T2 — Provision the NEW box
Goal: OS ready, packages in, firewall on, user `julio` created.
Commands (full, on NEWBOX):
```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3.12-dev build-essential \
  caddy rsync libgomp1 tzdata docker.io postgresql-client-16
sudo useradd -m -s /bin/bash julio || true
sudo systemctl enable --now caddy docker
sudo ufw allow 22,80,443/tcp && sudo ufw enable
# Langfuse reachability check (must hit OLD box :3001):
curl -s -m 5 http://46.62.233.228:3001/api/public/health ; echo
```
Dependencies: NEWBOX credentials (BLOCKED).
Verification: `python3.12 --version` ok; `caddy version` ok; Langfuse curl returns 200 (if it fails → firewall fix on OLD box, or set `LANGFUSE_ENABLED=false` on the new box as documented degraded mode and note it in the report).

### T3 — Rsync the tree + rebuild venv + copy model weights
Goal: exact byte copy of engine + services, fresh venv, arctic-m weights in place.
Commands (full, from OLD box):
```bash
rsync -avP --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
  --exclude '.git' --exclude 'research' --exclude '_cold_archive' --exclude 'json_logs' \
  /home/julio/projects/clean_diallux_SDR/engine/   NEWBOX:/opt/diallux-production/engine/
rsync -avP --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
  /home/julio/projects/clean_diallux_SDR/services/cal_slots_endpoint/  NEWBOX:/opt/diallux-production/services/cal_slots_endpoint/
rsync -avP --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
  /home/julio/projects/clean_diallux_SDR/services/time_endpoint/       NEWBOX:/opt/diallux-production/services/time_endpoint/
rsync -avP --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
  /home/julio/projects/clean_diallux_SDR/services/validator_endpoint/  NEWBOX:/opt/diallux-production/services/validator_endpoint/
rsync -avP /home/julio/fastembed/models/ NEWBOX:/home/julio/fastembed/models/
```
On NEWBOX:
```bash
cd /opt/diallux-production/engine && python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
for s in cal_slots_endpoint time_endpoint validator_endpoint; do
  cd /opt/diallux-production/services/$s && python3.12 -m venv .venv && \
  .venv/bin/python -m pip install -r requirements.txt; done
sudo chown -R julio:julio /opt/diallux-production /home/julio/fastembed
chmod 600 /opt/diallux-production/engine/.env /opt/diallux-production/services/*/.env
```
Dependencies: T2, T1 (or fallback pin).
Verification: `NEWBOX:/opt/diallux-production/engine/.venv/bin/python -c "import fastembed,langgraph,langchain_openai,asyncpg;print('imports ok')"`; `ls /home/julio/fastembed/models/models--Snowflake--snowflake-arctic-embed-m` non-empty; `.env` files present with mode 600.

### T4 — Restore the pgvector DB at 127.0.0.1:5434
Goal: identical RAG vector space (same table names, same dims, same password as `DATABASE_URL`).
Commands:
```bash
# OLD box (identify + dump):
sudo ss -ltnp | grep 5434   # confirm owner (docker pgvector expected)
PGPASSWORD=$(grep -oP 'DATABASE_URL=postgresql://diallux:\K[^@]+' /home/julio/projects/clean_diallux_SDR/engine/.env) \
  pg_dump -h 127.0.0.1 -p 5434 -U diallux -d diallux -Fc -f /tmp/diallux-5434.dump
scp /tmp/diallux-5434.dump NEWBOX:/tmp/ && shred -u /tmp/diallux-5434.dump
# NEW box:
docker run -d --name diallux-db --restart unless-stopped \
  -e POSTGRES_USER=diallux -e POSTGRES_PASSWORD=<same-as-DATABASE_URL> -e POSTGRES_DB=diallux \
  -v diallux-pgdata:/var/lib/postgresql/data \
  -p 127.0.0.1:5434:5432 pgvector/pgvector:pg16
docker exec -i diallux-db pg_restore -U diallux -d diallux --clean --if-exists < /tmp/diallux-5434.dump && shred -u /tmp/diallux-5434.dump
```
Dependencies: T2; pg_dump access (BLOCKED — if 5434 is a system cluster, dump exactly the same way with matching credentials).
Verification (NEW box):
```bash
PGPASSWORD=<same> psql -h 127.0.0.1 -p 5434 -U diallux -d diallux -tc \
  "select 'kb_chunks_v2',count(*) from kb_chunks_v2 union all select 'kb_chunks',count(*) from kb_chunks;"
```
→ must print `kb_chunks_v2|210` and `kb_chunks|233` (T0 baseline numbers).

### T5 — Start the 4 services on the NEW box (loopback)
Goal: engine :8026 + 3 endpoints :8001/:8002/:8003 as systemd units.
Files: `/etc/systemd/system/diallux.service`, `/etc/systemd/system/{cal-slots,time,validator}.service` on NEWBOX.
Commands (NEWBOX, as root; unit bodies per File Map):
```bash
# cal-slots/time/validator: copy the unit shape from
#   /opt/diallux-production/services/<name>/<name>.service  (or validator-service.service)
#   with WorkingDirectory=/opt/diallux-production/services/<name>
#   EnvironmentFile=/opt/diallux-production/services/<name>/.env
#   ExecStart=/opt/diallux-production/services/<name>/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port <8001|8002|8003>
# diallux.service: cp /opt/diallux-production/engine/deploy/diallux.service /etc/systemd/system/
sudo sed -i 's#/opt/diallux-production/.venv#/opt/diallux-production/engine/.venv#g' /etc/systemd/system/diallux.service
sudo systemctl daemon-reload
sudo systemctl enable --now cal-slots time validator diallux
```
Then the ONE `.env` edit (NEWBOX):
```bash
sed -i 's#^LANGFUSE_HOST=.*#LANGFUSE_HOST=http://46.62.233.228:3001#' /opt/diallux-production/engine/.env
```
Dependencies: T3, T4.
Verification:
```bash
for p in 8001 8002 8003 8026; do curl -s -m 3 -o /dev/null -w "%{http_code} :$p\n" http://127.0.0.1:$p/health; done
# expect 200 on all four; :8026 /health JSON matches T0 baseline fields (llm=gpt-5.4, tts=cartesia..., checkpoint, eager_eot)
journalctl -u diallux -n 50 --no-pager | grep "cartesia connected"   # must show model=sonic-3.6-2026-08-27
```

### T6 — Audit-phase URL override (temporary, reverted in T10)
Goal: let the new engine call its local endpoints without DNS/TLS, using the HMAC URL-independence fact.
Files: NEWBOX `/opt/diallux-production/engine/agent/llm.json` (TEMP EDIT) + audit receipt copy.
Commands (NEWBOX):
```bash
cp /opt/diallux-production/engine/agent/llm.json /opt/diallux-production/engine/agent/llm.json.Pristine
sed -i 's#https://slots.diallux-ai.site/validator-function#http://127.0.0.1:8003#g;
        s#https://slots.diallux-ai.site/today#http://127.0.0.1:8002/today#g;
        s#https://slots.diallux-ai.site/check_availability#http://127.0.0.1:8001/check_availability#g;
        s#https://slots.diallux-ai.site/book-livecall#http://127.0.0.1:8001/book-livecall#g' \
  /opt/diallux-production/engine/agent/llm.json
grep -c '127.0.0.1:800' /opt/diallux-production/engine/agent/llm.json   # expect 6 tool urls
sudo systemctl restart diallux
```
Dependencies: T5.
Verification: `curl -s http://127.0.0.1:8026/health | grep -c ok` → 1; engine logs show no webhook connection errors on a smoke turn.

### T7 — ENDPOINT AUDIT (the core ask)
Goal: prove every endpoint the engine calls behaves identically on the new box.
Commands (NEWBOX; signature helper inline, key from env):
```bash
set -a; . /opt/diallux-production/engine/.env; set +a
sig() { python3 -c "import hmac,hashlib,time,sys;raw=sys.stdin.buffer.read();ts=str(int(time.time()*1000));print('v=%s,d=%s'%(ts,hmac.new(__import__('os').environ['RETELL_API_KEY'].encode(),raw+ts.encode(),hashlib.sha256).hexdigest()))"; }
# 1) time service
curl -s http://127.0.0.1:8002/time-function/today
# 2) cal_slots availability (freeze-mode probe — safe, no booking)
BODY='{"args":{"account_id":"diallux_live","timezone":"Europe/London","slot_target_date":"2026-09-24","current_reservation_uids":""}}'
curl -s -X POST http://127.0.0.1:8001/check_availability -H 'Content-Type: application/json' -H "X-Retell-Signature: $(echo -n "$BODY" | sig)" -d "$BODY"
# 3) negative auth probe — unsigned MUST be rejected
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8001/check_availability -H 'Content-Type: application/json' -d "$BODY"   # expect non-200 (invalid_signature)
# 4) validator routes (validate_lead / verify-lead-data / record-booking-uid / set-callback-number / record-reach-details)
#    same signed-POST pattern against http://127.0.0.1:8003/<route>; use payload shapes from
#    /opt/diallux-production/services/validator_endpoint/test_validate.py
# 5) endpoint test suites
cd /opt/diallux-production/services/cal_slots_endpoint && .venv/bin/python -m pytest test_slot_lock.py -q
cd /opt/diallux-production/services/validator_endpoint  && .venv/bin/python -m pytest test_validate.py -q
# 6) Telegram notify wiring (cal_slots/validator) — confirm tokens present, DO NOT spam:
grep -c '^TELEGRAM_BOT_TOKEN=' /opt/diallux-production/services/cal_slots_endpoint/.env
```
Dependencies: T5, T6.
Verification: every probe matches the T0 baseline shape (`"ok": true` + `slots` array for availability; today returns London-local date; unsigned → rejected). Suites green. Receipts appended to `baseline-oldbox.md` → `audit-newbox.md`.

### T8 — ENGINE AUDIT (suite + RAG + voice path)
Goal: the state machine is byte-for-byte behaviorally identical on the new box.
Commands (NEWBOX):
```bash
cd /opt/diallux-production/engine
set -a; . ./.env; set +a
.venv/bin/python -m pytest tests -q 2>&1 | tail -3        # count MUST equal T0 baseline count
.venv/bin/python scripts/eval_accuracy.py                 # offline machine checks — 0 failures
.venv/bin/python scripts/voice_preflight.py               # TTS/STT/RAG preflight receipts
curl -s http://127.0.0.1:8026/health | python3 -m json.tool   # embedder must be "ok" (NOT import-failed)
PGPASSWORD=$(grep -oP 'DATABASE_URL=postgresql://diallux:\K[^@]+' .env) psql -h 127.0.0.1 -p 5434 -U diallux -d diallux \
  -tc "select count(*) from kb_chunks_v2;"                # 210
.venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --max-turns 48   # happy-path smoke (mock webhooks path uses local mocks — see note)
```
Dependencies: T5, T6, T7.
Verification: pytest count == T0; `/health` `embedder: "ok"`, `llm: gpt-5.4`, `tts` cartesia, `rag_mode` matches baseline; harness Maria completes with expected book outcome; Langfuse trace visible on OLD box `:3001` (proves remote tracing works). NOTE: if the harness needs live webhooks, it runs with `AUDIO_TRANSPORT=browser` defaults and the T6 local URLs — record which mode was used in the receipt.

### T9 — VOICE AUDIT (browser mic + Twilio gate, no PSTN yet)
Goal: full audio loop on the new box before touching DNS.
Commands (NEWBOX):
```bash
# browser mic bridge: AUDIO_TRANSPORT=browser + VOICE_TEST_TOKEN are already in .env (verbatim copy)
# open https://<NEWBOX-IP-or-temp-domain>/mic from a browser with ?k=<VOICE_TEST_TOKEN> — REQUIRES public TLS,
# so if DNS hasn't cut over yet, use the OLD-box Caddy temp route OR a temporary DNS name (owner choice, BLOCKED if none).
# Alternative zero-DNS audit: run one scripted live-loop on loopback:
cd /opt/diallux-production/engine && set -a; . ./.env; set +a
.venv/bin/python scripts/fake_twilio_call.py --tts-live     # full audio loop against 127.0.0.1:8026
# Twilio signature gate (fail-closed proof — no real call needed):
curl -s -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:8026/twiml?From=%2B15550001111"   # expect 403 (no signature)
curl -s -o /dev/null -w '%{http_code}\n' -X POST "http://127.0.0.1:8026/twiml" -d 'From=%2B15550001111'   # expect 403
```
Dependencies: T8.
Verification: fake call completes ≥1 full turn loop with audible TTS (Cartesia pin confirmed in logs: `model=sonic-3.6-2026-08-27`); both unsigned `/twiml` probes → 403; signed probe (generated with TWILIO_AUTH_TOKEN if available) → 200 TwiML XML.

### T10 — Restore byte-exact `llm.json` + Cutover (DNS + Twilio)
Goal: production parity. Only after T7–T9 are green.
Commands (NEWBOX):
```bash
cp /opt/diallux-production/engine/agent/llm.json.Pristine /opt/diallux-production/engine/agent/llm.json
rm /opt/diallux-production/engine/agent/llm.json.Pristine
sha256sum /opt/diallux-production/engine/agent/llm.json    # MUST equal T0 baseline sha256
sudo systemctl restart diallux
# Caddy: paste the two site blocks (slots.diallux-ai.site from old /etc/caddy/Caddyfile,
#        twilio.diallux-ai.site from /opt/diallux-production/engine/deploy/Caddyfile) into /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
```
Then (Julio/DNS): A records `slots.diallux-ai.site` + `twilio.diallux-ai.site` → NEWBOX IP. Then Twilio repoint (needs creds, BLOCKED):
```bash
cd /opt/diallux-production/engine && .venv/bin/python scripts/provision_twilio_number.py --repoint +18885958927 --host twilio.diallux-ai.site
```
Then pin the number's Voice Region to **US2 (= AWS us-west-2, Oregon)** in the Twilio Console (Voice → Regional) — NEWBOX is in Oregon, so the Media Streams WS then originates ~1–5 ms away instead of ~60–70 ms from the default US1 (Virginia). Latency is the reason for this move (Finland→Oregon): the whole audio path (/twiml, /media, Deepgram, Cartesia, OpenAI) moves together; only Langfuse stays on the Finland box (fire-and-forget tracing, never on the hot path).
Dependencies: T7–T9 green + owner go-ahead.
Verification: `curl -s https://slots.diallux-ai.site/time-function/today` (from anywhere) hits NEW box; `curl -s https://twilio.diallux-ai.site/health` → 200; `sha256sum` match recorded.

### T11 — Post-cutover live audit + rollback window
Goal: prove the live phone path end-to-end on the new box; keep the old box as instant rollback.
Commands: ONE live PSTN call to the number → full booking flow → **CANCEL the Cal.com test booking immediately** (event `3801235` is REAL):
```bash
# verify booking landed, then cancel via Cal.com UI or the cal_slots cancel API; record uid in the receipt
```
Re-run: T7 probes (now via public URLs), `/health` parity, one `/metrics` scrape. OLD box services stay RUNNING untouched for 72 h as rollback; after owner sign-off, quiesce old lanes (owner-ordered, out of scope here).
Dependencies: T10.
Verification: live call books + cancels cleanly; Langfuse trace on OLD box `:3001` named `diallux-call-*` shows the new-box session; `diallux_gate_rejections_total` not growing.

## Validation Plan (end-to-end)
1. T0 baseline frozen (suite count, /health, probes, DB counts, llm.json sha256).
2. T7 endpoint audit green (signed ok, unsigned rejected, suites pass).
3. T8 engine audit green (suite count parity, embedder ok, RAG 210 rows, Maria happy path).
4. T9 voice audit green (audio loop + 403 gates + cartesia pin in logs).
5. T10 cutover with sha256-verified pristine config + public TLS live.
6. T11 one live call booked AND cancelled; parity receipts stored in `/home/julio/projects/clean_diallux_SDR/research/surgeon/migration-2026-09-23/`.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Migrating the Langfuse stack itself | Owner decision: point at the existing OLD-box Langfuse instead (fail-safe if unreachable) |
| Dockerizing the app containers | Owner chose exact rsync clone; Docker only for the pgvector DB |
| proxy_guard / iptables egress masking | Retell stack — explicitly dropped |
| Old-box decommission / lane shutdown | Owner-ordered, ≥72 h after stable cutover |
| `slots.db` WAL shipping / live sync of reservations during the audit window | Audit window is short; slots.db copied once at T3; any drift is re-synced at T10 by re-copying the file before cutover |
