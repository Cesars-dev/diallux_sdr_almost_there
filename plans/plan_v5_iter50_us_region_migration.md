# PLAN — v5 iter50: US-East region migration (runs AFTER iter49 RAG parity)

## Meta
- Date: 2026-09-12
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: **INFRA ONLY** — move the voice pipeline's brain from the Helsinki VPS
  `46.62.233.228` (Hetzner, Finland) to a NEW US-East VPS (owner provisions). Deploy
  the **iter49 branch** (`engine/iter49-rag-parity` — RAG parity + local embedder,
  already green) on the new host, prove latency, cut over Twilio/DNS.
  Target: **e2e ~1,000-1,400ms (from ~1,900-2,400ms projected today)**.
- Status: PLAN ONLY (not started — awaits iter49 green + owner provisioning the box; execute in a NEW session)
- ◀ PREVIOUS (must be done first): `plans/plan_v5_iter49_rag_retrieval_parity.md` —
  the RAG correctness plan (fresh-per-turn retrieval, per-KB quota, local embedder,
  KB re-embed). **iter49 → prove → iter50 (this plan).** Do NOT start iter50 until
  iter49's battery + live proof are green.
- Evidence base: `research/surgeon/iter48-rag-truth/10_latency_findings.md` (all wire
  measurements), `09_sql_report_iter48b.md`, `05_battery_report.md`.

## ▶ ORDER OF WORK
1. **iter49** (`plan_v5_iter49_rag_retrieval_parity.md`) — RAG retrieval redesign +
   local embedder. Engine code, branch `engine/iter49-rag-parity`. Proves correctness
   (tag-KB present, Closing chunks, fresh tail) + local embed p50 ≤30ms on Helsinki.
2. **iter50 (this plan)** — once iter49 is green: stand up the US-East box, migrate the
   data/services, deploy iter49's branch, prove the latency win, cut over.

The reason for the split: iter49 is code (fast, reversible, harness-testable);
iter50 is infrastructure (slow, owner-blocked, one-shot cutover). One session each.

## Compaction Context

**Where things stand (2026-09-12, iter48b session complete):**
- Branch `engine/iter48-rag-truth` @ `033f742` (unmerged — LAW 0): Commit B
  `32d6ea9` (await split 500/100, lite-warm await, warm WARNING + one lite retry),
  `d1dd5a9` harness `--warm-greeting-ms`, `7188db7` live_sql G3 fix, `033f742`
  THE FIX (`LITE_NOOP_TOOL` on lite turn-1 + `prewarm_max_completion_tokens` 16→64).
- Why: raw cURL + OTEL proved **gpt-5.4 only prompt-caches requests carrying `tools`**
  (9/9 no-tools cached=0; 3/3 with-tools cached>0) — FIND-5. battery-iter48 (13
  personas @ `033f742`): **13/13 PASS**, turn-1 cache 12/13 (1664-tok lite prefix),
  LLM TTFT p50 821-1023ms.
- **Latency forensics (cURL, from the VPS — all in `10_latency_findings.md`):**
  - VPS is **Helsinki, Finland** (`46.62.233.228`, Hetzner AS24940 — owner believed UK).
  - OpenAI `api.openai.com`: Cloudflare Helsinki edge (3ms connect) → **San Francisco
    origin**; RTT to origin **~150-180ms**; streaming chat TTFB measured 1.19-1.79s.
  - **Deepgram: TCP connect 120-214ms, API TTFB 457-586ms** (Sacramento origin, no EU
    edge) — the worst offender; hits every STT partial/final.
  - Cartesia `api.cartesia.ai`: 3-4ms edge, TTFB 90-114ms (Seattle origin).
  - ElevenLabs (reference only): ~205ms (Kansas City GCP).
  - Twilio `api.twilio.com`: 3ms connect (Helsinki AWS POP), TTFB 156-172ms — REST is
    the CONTROL plane; **SIP/media is per-chunk RTP** from a US Twilio media gateway to
    Helsinki (~120-140ms one-way + jitter) — cURL cannot measure it.
  - Cal.com lives on US VPS `129.212.184.175` (~75-90ms RTT from Helsinki).
- **Projected e2e budget** (caller stops → hears reply): today **~1,900-2,400ms**
  (EOT/STT 150-350 · LLM TTFT ~880 incl. 150-180 network · TTS first 100-200 ·
  media legs 120-140×2) → after US-East + iter49's local embedder: **~1,000-1,400ms**
  (EOT/STT 80-150 · TTFT ~700-750, 600 best-case on cache hits · local RAG ~15-25 ·
  TTS 60-100 · media 30-50).
- Owner confirmed: all callers US-only; region-match rule = diallux SDR → US VPS,
  heating-uk line stays UK/EU (never move it to the US).
- Open quality debt (NOT this plan): FIND-8/PT-48 in-turn echo duplication; PT-43
  name loop; PT-44 time extraction.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| iter50 = infrastructure ONLY; any code fix goes in iter49 or a new branch | one variable per iteration; infra changes are not engine changes |
| Deploy the iter49 branch as-is (no code edits during migration) | keep the migration reproducible; a code bug found during T4 goes back to iter49 |
| New host = Hetzner **US-East** (Ashburn/Virginia class), Ubuntu 24.04, 2-4 vCPU, ≥8GB RAM | closest to OpenAI/Cartesia/Twilio US + the Cal.com VPS; owner provisions |
| Cutover order: new host fully green → then Twilio/DNS flip (owner-driven) | old Helsinki stays untouched as rollback |
| Heating-uk stays UK/EU | region-match callers; a US box would make UK calls worse |
| Verify OpenAI org is NOT EU-data-pinned before the move | if pinned, the OpenAI RTT win shrinks (other providers' wins remain) |
| After any live/battery session cancel ALL test bookings | Cal.com event 3801235 is REAL |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| NEW US-East VPS: IP, root access, hostname | owner provisions (Hetzner Ashburn `us-east`), then T1 |
| OpenAI org data-pin status (EU-pinned?) | owner: platform.openai.com → org settings → data residency |
| Which components actually run on the old box (full inventory) | T2 inventory: `systemctl --user list-units` + `docker ps` + `/etc/caddy` on `46.62.233.228` |
| Twilio media-stream + webhook URLs currently pointing at Helsinki | Twilio console (owner) — needed for the T5 flip and the rollback |
| Caddy DNS records + certificates to re-issue | `/etc/caddy` on the old host + DNS provider (owner) |
| Storage size of the Postgres DBs (dump size/time estimate) | T2: `psql -c "\l+"` per DB on the old host |

## Environment & Dependencies
- OLD host (source): `/home/julio/projects/clean_diallux_SDR` + `/home/julio/projects/Retell_AI_MCP_connection`
  on `46.62.233.228` (Helsinki; ssh as `julio`). Service user `2nd_workspace` (uid 1003).
- NEW host (target): same tree layout under `/home/julio/projects/`. Python 3.12,
  Postgres 16, Redis 6379, Caddy 80/443, Langfuse self-hosted :3001, n8n 5682 (stays
  on `129.212.184.175`), cal_slots :8001 / time :8002 / validator :8003 (systemd user
  units for `2nd_workspace`), MinIO 9007/9008 (only if used by this line — verify in T2).
- Engine to deploy: branch `engine/iter49-rag-parity` (iter49's HEAD) — create worktree
  `/tmp/opencode/wt-iter49` on the old host first if T1 runs there, then `rsync` the tree.
- Secrets: copy `.env` files by hand (never git): `/home/julio/projects/.env`,
  `/home/julio/projects/clean_diallux_SDR/.env` (OPENAI/ANTHROPIC/DEEPGRAM/CARTESIA/
  LANGFUSE keys), `cal_slots_endpoint/.env`, `validator_endpoint/.env`.
- Cal.com availability badge key for the signed probe: `${RETELL_KEY_3}`.
- Ports: :8007 OWNER live-test — never start/stop. Never bind :8000-:8006 on the old
  host. On the new host, services bind :8001-:8003 + Caddy after cutover only.

## Architecture (one block)
```
BEFORE (Helsinki brain):
  caller(US) → Twilio US media ⇄ Helsinki VPS { Deepgram 120-214ms conn · brain
  ~880ms TTFT (150-180 network) · OpenAI embed 184ms · Cartesia 90-114ms }
  + Cal.com US VPS (75-90ms)                       e2e ≈ 1,900-2,400ms

AFTER (US-East brain, iter49 code):
  caller(US) → Twilio US media ⇄ US-East VPS { Deepgram ~10ms · brain ~700-750ms
  (60-70 network) · LOCAL embed ~15-25ms · Cartesia ~10-20ms } + Cal.com intra-US
                                                   e2e ≈ 1,000-1,400ms
  Helsinki box kept alive = rollback (re-point Twilio/DNS back)
```

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| NEW US host `/home/julio/projects/` | copy of `Retell_AI_MCP_connection` services (cal_slots/time/validator) + `clean_diallux_SDR` clone + hand-copied `.env`s | New |
| `research/surgeon/iter48-rag-truth/12_region_budget.md` | latency budget table before/after (filled from Langfuse at T5/T6) | New |
| `/etc/caddy` on the new host | reverse-proxy routes re-created (copy of old host's, DNS re-pointed at T5) | New |
| systemd user units (`2nd_workspace`) on the new host | `cal-slots`, `time`, `validator` re-installed | New |
| `plans/PENDING_TASKS.md` | PT-50 (this plan's tracker); close PT-45 (harness greeting-warm default) | Edit |

**No engine code changes in this plan.** If T4 finds a bug, it goes back to
`plans/plan_v5_iter49_rag_retrieval_parity.md` / a new branch — never patched here.

## Deploy Rules
- LAW 0: NO merges/pushes without owner say-so. This plan creates NO engine commits.
- Deploy command for the engine (on the new host): `git worktree add /tmp/opencode/wt-iter49 engine/iter49-rag-parity`
  (or `git clone` + `git checkout engine/iter49-rag-parity`), then
  `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
- NEVER touch :8007 (owner live tests), live agent IDs (`agent_f305…` sdr,
  `agent_1698…` heating voice, `agent_87e4…` chat), Cal.com event `3801235`.
- Cutover order: T1-T4 on the new host → owner flips Twilio media-stream + webhooks +
  DNS → T5. Old Helsinki host stays running, untouched, until the owner confirms.
- Rollback: re-point Twilio/DNS to Helsinki (no data loss; old host never stopped).
- After any owner live/battery session: cancel ALL test bookings (Cal.com 3801235 REAL).
- keyhound before any push; never commit `.env`.

## Tasks (in order)

### T0 — Precondition check
Goal: confirm iter49 is green before spending infra effort.
Commands:
```
cd /tmp/opencode/wt-iter44 && git log --oneline -1
.venv/bin/python -m pytest tests -q --tb=no -p no:warnings      # expect 270 + iter49 pins, all green
.venv/bin/python scripts/lf_quick.py bugs --run battery-iter49   # expect ALL COVERED
```
Verification: iter49 battery imported + gates passed; if not, STOP (finish iter49 first).

### T1 — Owner provisions + verify the new host
Goal: a reachable US-East VPS with Docker + Postgres 16 + Redis.
Commands:
```
ssh root@<NEW_IP> 'curl -sS https://ipinfo.io/json'      # expect US / Ashburn-Virginia class
ssh root@<NEW_IP> 'python3 --version && pg_isready && redis-cli ping'
```
Verification: `ipinfo` shows US; `pg_isready` OK; `redis-cli ping` → PONG.

### T2 — Inventory the old host + data migration (old → new)
Goal: know exactly what to move; move it.
Commands:
```
# inventory (old host)
ssh julio@46.62.233.228 'systemctl --user list-units --type=service --state=running; docker ps --format "{{.Names}}"; ls /etc/caddy'
ssh julio@46.62.233.228 'sudo -u postgres psql -c "\l+"'
# migrate (exact DB names from the \l+ output)
ssh julio@46.62.233.228 'pg_dump -Fc <DB> | gzip' | ssh root@<NEW_IP> 'gunzip | pg_restore -d <DB>'
rsync -av --exclude .venv --exclude research --exclude 'tests/llm2llm/json_logs' \
  /home/julio/projects/ jroot@<NEW_IP>:/home/julio/projects/
# hand-copy .env files (names only): /home/julio/projects/.env,
# clean_diallux_SDR/.env, cal_slots_endpoint/.env, validator_endpoint/.env
```
Verification: `psql \l` on the new host matches; Langfuse `:3001` health 200;
`cd <new>/clean_diallux_SDR && .venv/bin/python scripts/lf.py health` PASS.

### T3 — Services parity (cal_slots :8001, time :8002, validator :8003, Caddy)
Commands:
```
# on the new host, as 2nd_workspace: install the same systemd USER units
systemctl --user enable --now cal-slots time validator
# signed probe of the slots endpoint (badge key below) → expect 200 + slots
curl -sS "https://slots.diallux-ai.site/check_availability?..."   # exact URL from ENDPOINTS.md
```
Verification: signed probe returns 200 with real slots; `curl -w %{time_total}` from
the new host < 25ms for cal_slots; validator HMAC round-trip < 30ms.

### T4 — Deploy iter49 engine + harness parity smoke (new host)
Goal: prove brain latency before cutover.
Commands:
```
ssh root@<NEW_IP> 'cd /home/julio/projects/clean_diallux_SDR && git worktree add /tmp/opencode/wt-iter49 engine/iter49-rag-parity'
ssh root@<NEW_IP> 'cd /tmp/opencode/wt-iter49 && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt'
# single smoke, then the 4 happy personas async staggered 15s
ssh root@<NEW_IP> 'cd /tmp/opencode/wt-iter49 && set -a && . ./.env && set +a && \
  .venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --langfuse --max-turns 28 --warm-greeting-ms 2000'
```
Verification: smoke PASS; ledger import `smoke-us` @ the iter49 sha; LLM TTFT p50
**≤ 830ms** (vs 880 Helsinki); OpenAI streaming cURL TTFB from the new host ≤ 1.1s.

### T5 — Cutover + live G6 (OWNER drives :8007)
Goal: real caller-path proof on the new region.
Commands: owner re-points the Twilio media-stream + the webhooks + DNS to the new host
(owner-driven; the agent never flips production routing). Owner asks "what do you guys
do" early in Intake on a live call.
Verification (Langfuse TurnClock): `stt_eot_to_llm_first_ms`,
`llm_first_to_tts_first_ms`, `tts_first_to_audio_out_ms`, `e2e_response_ms` →
`12_region_budget.md`; G6: pitch answer, turn-1 cache>0, turn-1 TTFT ≤1000, rag span
state-anchored; **e2e ≤1,500ms** target band. Write `06_live_report.md`; cancel ALL
test bookings (Cal.com 3801235 REAL).

### T6 — Battery-13 re-proof + close-out
Commands:
```
# 13 personas async staggered 15s on the NEW host (same flags as battery-iter49)
.venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run battery-iter50 --commit <iter49-sha>
.venv/bin/python scripts/lf_quick.py bugs --run battery-iter50
.venv/bin/python scripts/live_sql.py gates --a battery-iter49 --b battery-iter50
```
Verification: 13/13 PASS, no new failure, TTFT p50 improves vs battery-iter49, budget
table filled. Then ASK owner (merge? decommission Helsinki? keep as rollback?).

## Validation Plan (end-to-end)
1. T0 confirms iter49 green — the ONLY entry condition.
2. New host is proven with a harness smoke (T4) BEFORE any production routing change.
3. Cutover is owner-driven; rollback = re-point routing to Helsinki (untouched).
4. Live G6 (T5) + battery (T6) prove the latency win against `10_latency_findings.md`.
5. Any failure during the migration → stop, do not cut over, old host keeps serving.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| RAG retrieval redesign + local embedder code | `plans/plan_v5_iter49_rag_retrieval_parity.md` (runs FIRST) |
| In-turn echo duplication (PT-48/FIND-8) | separate quality plan |
| First-name company-answer loop (PT-43/FIND-1) | owner: fix later |
| Time-extraction 1/500 (PT-44) | owner: fix later |
| Heating-uk relocation | stays UK/EU (region-match rule) |
