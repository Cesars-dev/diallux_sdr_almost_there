# iter67 — Twilio live lane: RETURN-TO-WORK context (T5 done LIVE; next = T6 repoint → T7 owner-ears call)

## Meta
- Date: 2026-09-23 (session 2026-09-22 23:30 → 2026-09-23 00:50 UTC)
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: resume the approved Twilio lane work. **T1–T5 are DONE and the phone endpoint is LIVE on the VPS.** Remaining: T6 (repoint number — awaiting owner say-so), T7 (owner calls, ear gates), T8 (docs/merge, LAW 0).
- Status: **IN PROGRESS — live on VPS; next action blocked on owner say-so ("repoint")**
- Master plan: `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter67_twilio_live_lane.md` (approved; this file is its execution state + resume context)

## Compaction Context (what happened in the executed session)
- Branch `engine/iter67-twilio-live-lane` cut from main `5ab75a6` per LAW 0 v2.1 (collision audit clean: no iter67 name/ports/branch; engine/ tree identical to main tip; ports 8024/8026 free; 8020–8023 mic lane + 8000–8003 ORIGINAL untouched). Head now `0394a3b`, worktree `/tmp/opencode/wt-iter67`, status clean, 3 commits.
- Owner pasted Twilio Account SID + Auth Token in chat → written to `/tmp/opencode/wt-iter67/engine/.env` (gitignored, never printed/committed). **NOT on disk anywhere else except `/opt/diallux-production/.env`** (deploy copy). Trial account facts: ACTIVE Trial, $7.555 balance, 1 number `+18885958927` (toll-free, voice_url = Twilio demo), verified caller ID `+523318262230`, 0 SIP trunks/domains → SIP ruled out (Trial can't trunk + engine speaks Media Streams wss, not SIP/RTP).
- T2 baseline: 427/427 passed (`/home/julio/projects/clean_diallux_SDR/research/surgeon/iter67-twilio-live-lane/t67_suite_baseline.log`).
- T3 local loop proven: fake Twilio WS caller → mulaw/8k → Deepgram flux STT → gpt-5.4 → Cartesia sonic-3.6 → mulaw out. turn-1-done, reply 8.2s, turn report ttft 821 ms / e2e turn 1443.8 ms. **Finding F1 (fixed+pinned): `/media` inherited `AUDIO_TRANSPORT` env default (`browser` from mic era) → Deepgram got linear16-coded mulaw garbage → zero transcripts.** Fix: `/media` now pins `transport="twilio"` in code; proven live with `AUDIO_TRANSPORT=browser` still in .env. **Finding F2 (fixed): `scripts/fake_twilio_call.py` hardcoded 6 s reply wait < eager-EOT+gpt-5.4 latency → added `--wait` (default 20).**
- T4 signature gate live: `/twiml` rejects invalid/missing `X-Twilio-Signature` with 403 (HMAC-SHA1 of url + sorted params, `TWILIO_AUTH_TOKEN`); forwarded-URL reconstruction via `X-Forwarded-Proto/Host` (Caddy); stdlib `parse_qsl` form parse (NO python-multipart dep — plan rule). 7 new pins in `/home/julio/projects/clean_diallux_SDR/engine/tests/test_twilio_signature.py`; suite **434/434** (`t67_suite_t4.log`). From-form `From` fallback fixed too (F4: old code read query-only — real Twilio POSTs would have lost `callback_number`).
- T5 DEPLOYED AND LIVE: `/opt/diallux-production` (rsync of worktree @ `0394a3b`), fresh venv (`python -m venv` + `pip -r requirements.txt`), systemd unit `diallux` active + boot-enabled on `127.0.0.1:8026` (User=julio, `python -m uvicorn`), Caddy site block `twilio.diallux-ai.site` applied via caddy-apply (backup `/etc/caddy/backups/Caddyfile.20260923-003028`) exposing ONLY `/twiml` `/media` `/health` (rest 404). Verified: public `/health` 200 (gpt-5.4/cartesia/flux/embedder ok), unsigned POST `/twiml` → 403, `/mic` → 404. DNS: owner added A record `twilio.diallux-ai.site → 46.62.233.228` (Bluehost zone ns1/ns2.bluehost.com).
- Deploy lessons (both committed): Caddyfile inline-brace handles invalid → template multi-line (`e5a87f6`); fresh-venv gap `fastembed` unpinned → `fastembed==0.8.0` in requirements + installed live (`0394a3b`).
- Reports: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter67-twilio-live-lane/01_t1_t4_report.md` + `02_t5_deploy_report.md` (+ logs/wavs in same folder).
- Registry refreshed (backup `ledger.db.iter67.bak`): `engine/iter67-twilio-live-lane` @ `0394a3b` status open.
- iter66 (`engine/iter66-elevenlabs-cutover` @ `e91af1a`) UNMERGED, T7 mic + owner G3 pending; **zero file overlap with iter67** (iter66 touches TTS-side files only; `app.py` untouched). Merge order per plan: iter66 first, then iter67; iter67 phone lane flips to EL voice later via `/opt` rsync + `.env` flip (merge ≠ deploy; deploy = rsync + restart).
- Owner asked/explained this session: SIP trunk (ruled out), subdomain choice (owner picked **`twilio.diallux-ai.site`** over plan's `calls.*`; dedicated subdomain = signature URL binding + 3-path exposure + mic lane independence), transport rationale (Media Streams = engine default, zero-transcode; browser = mic-test lane), merge≠deploy (deploy = rsync copy).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Public host = `twilio.diallux-ai.site` (NOT plan's `calls.*`) | owner choice 2026-09-23; dedicated subdomain: signature binds full URL, 3-path exposure only, mic lane (flores) stays independent |
| No number purchase — repoint existing `+18885958927` | Trial account already owns it; free + reversible |
| Caddy block exposes only `/twiml` `/media` `/health`; all else 404 | minimal public surface for a budget-spending endpoint |
| Prod `.env` = worktree `.env` + `PUBLIC_BASE_URL=wss://twilio.diallux-ai.site` | TwiML stream URL must be the public wss; creds included for signature gate |
| `systemd` unit: User=julio, `python -m uvicorn` (never `bin/uvicorn` shebang) | no `deploy` user on box; copy-mirror shebang trap |
| T6 repoint is OWNER-GATED (owner chose wait) | trial-account caveats: possible Twilio trial-notice preamble on calls; toll-free inbound rates higher |
| T7 merge gate | LAW 0: no merges without owner say-so; iter66 merges first |

## Environment & Dependencies
- Worktree: `/tmp/opencode/wt-iter67` (branch `engine/iter67-twilio-live-lane`, head `0394a3b`); venv `/tmp/opencode/wt-iter67/engine/.venv` (copy-mirror — use `python -m pip`, never `bin/pip`)
- Prod: `/opt/diallux-production` + `/opt/diallux-production/.venv` (FRESH venv); service `diallux` on `127.0.0.1:8026`; public `https://twilio.diallux-ai.site`
- Dev test server: uvicorn `diallux.app:app` on `127.0.0.1:8024` (worktree), log `/tmp/opencode/t67_uvicorn.log`
- Secrets: `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN` in both `.env`s above (also valid as the `/twiml` signature key); never commit; `scripts/keyhound` before any push
- Suite count now 434 (427 + 7 iter67 pins)

## Tasks (remaining, in order)

### T6 — Repoint number → live engine (OWNER SAY-SO: "repoint")
Goal: voice webhook of `+18885958927` → `https://twilio.diallux-ai.site/twiml`.
Files: none.
Commands:
```bash
cd /opt/diallux-production && .venv/bin/python scripts/provision_twilio_number.py --repoint +18885958927 --host twilio.diallux-ai.site
```
Dependencies: none (creds in `/opt/diallux-production/.env`).
Verification: re-run the IncomingPhoneNumbers GET (curl basic auth) → `voice_url: https://twilio.diallux-ai.site/twiml`; console shows same.

### T7 — LIVE call test (owner's ears) + ledger + report
Goal: owner dials `+18885958927` from `+523318262230`. Gates: greeting audible · ≥3 turns · digits read-back · barge-in · post-idle turn.
Watch: `sudo journalctl -u diallux -f` or `curl` health; Langfuse traces for the call.
Then import evidence:
```bash
cd /home/julio/projects/clean_diallux_SDR && set -a && . /tmp/opencode/wt-iter67/engine/.env && set +a
python3 scripts/live_sql.py import --window "<HH:MM-HH:MM>" --run iter67-twilio-live --commit 0394a3b --db research/surgeon/iter48-rag-truth/ledger.db
```
Verification: `calls` row for `iter67-twilio-live`; report `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter67-twilio-live-lane/NN_t67_report.md`; LV-gate table filled; findings logged.

### T8 — Docs + ledger + merge (owner say-so only)
- iter66 merges FIRST (its T7 mic + G3), then iter67 via `git merge main` absorb → merge `--no-ff` → tag `engine/iter67` → `scripts/git-tree.sh` → ITERATIONS.md line.
- To flip the phone lane to the owner-approved EL voice afterwards: rsync main → `/opt/diallux-production` + set `TTS_PROVIDER=elevenlabs` (+ `ELEVENLABS_*` per `.env.example` prod block) in `/opt/diallux-production/.env` + `sudo systemctl restart diallux`.

## BLOCKED / NEEDS INPUT
| Item | Owner action |
|---|---|
| T6 repoint | say-so word: "repoint" |
| T7 live call | dial the number when T6 done |
| T8 merges | say-so after T7 gates pass |

## Deploy Rules (standing)
- NEVER touch ORIGINAL :8000–8003, mic lane 8020–8023, live agent IDs, `validator_endpoint/`.
- Update prod = `sudo rsync -a --delete /tmp/opencode/wt-iter67/engine/ /opt/diallux-production/ --exclude .venv --exclude .git` (or main checkout after merges) + `sudo systemctl restart diallux` (sudo password needed for rsync/restart; `caddy-apply`, `daemon-reload`, `systemctl enable diallux` were passwordless).
- `.env` never in git; `scripts/keyhound` before any push. Cancel any Cal.com test booking after batteries (event 3801235 REAL).
