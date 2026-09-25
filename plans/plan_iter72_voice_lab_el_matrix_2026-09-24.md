# plan_iter72_voice_lab_el_matrix — ElevenLabs voice lab on lane :8024 (Eryn/Sarah-A&I/Vanessa parameter matrix) + measurement protocol (carries 2026-09-24 session evidence)

## Meta
- Date: 2026-09-24
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: continue the owner's live voice testing on lane :8024 — EL voice A/B (Eryn, Sarah "Approachable & Informative", Vanessa "Beach Girl") across stability/speed/style, measured with the same per-turn latency table + 3-SOP audit as the 2026-09-24 ladder A/B. HITL at every voice change.
- Status: PLAN ONLY (not started — T0 awaits owner GO; owner is mid-testing NOW: Eryn @ stability 0.4 / speed 1.2 live)
- Voice LAW carried: Cartesia `sonic-3.6-2026-08-27` stays the production pin; all EL work is TEST-ONLY via `TTS_PROVIDER` flip, rollback = one .env line.

## Compaction Context (T0 resume point)
This session (2026-09-24) did the following — a fresh agent must continue from exactly here:

1. **Lane A/B deploys (owner say-so each):** lane `diallux-8024.service` first served the iter52→64c LADDER merge `40b3b40` (14 engine files swapped into the working tree from the merge snapshot; backups kept at `/tmp/opencode/lane_backup_main_restore/`), then was RESTORED to main content (merge `50a453f` + the two post-merge owner-directed commits `f236697` EL-default + `87e173f` 900s cap; the working tree now equals main tip engine content — verified byte-for-byte against `/tmp/opencode/lane_backup_main_restore/`).
2. **Live call 1 analyzed:** `micbridge-87b9e9ae4dc9` (Langfuse trace `3b427b42a8c4…`, 04:08–04:18, 50 turns / 60 rounds, ladder code `40b3b40`, HVAC owner Caleb, BOOKED Friday 4pm). Verified per-turn table: ✅ 30 clean · ❌ 5 COLD-ACK (t18, t28, t38, t47, t50 — cache=0 spoken rounds) · ❌ 7 SLOW-e2e (t3,t4,t6,t10,t11,t12,t30 — dominated by caller STT/EOT wait). TTFT p50 966 / p90 1380 / max 1509 (n=42). LLM→TTS p50 ~111ms. Cache ladder 1664→9856 with 3 mid-call dips (t10, t25, t31). Report: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter71-ack-latency/01_latency.md`.
3. **3-SOP audit run + persisted:** CALL redundancy FAIL (transition double-ack t22→t23, company name asked twice t24→t25, same-turn near-dupe r33), SALES 12/14 HIRE, HUMANIZED FAIL (R5 redundancy). 21 rows in ledger `sops` table, run `mic-20260924-87b9e9ae`. Report: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter71-ack-latency/02_sop_report.md`; rows: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter71-ack-latency/03_sop_rows.json`.
4. **Double-sentence answer (owner's question):** 100% exact same-turn doubles exist in MODEL TEXT (t25 "And your last name?\nAnd your last name?", t31 "Thanks. Is that Moral Business?\nThanks. Is that Moral Business?") and are MUTED from speech by the exact-window dedupe (PT-48 fix holds). The AUDIBLE repeats are the ~90% cross-turn near-dupes (company name asked twice; transition double-ack) because `TTS_DEDUPE_SEMANTIC=false` in `.env` (owner call: audible > muted). The iter70 T4' jaccard ≥0.80 same-turn dedupe would catch the r33 same-turn near-variant pair and is NOT in the ladder code.
5. **The cold-ack mechanism (the iter71 pickle) confirmed LIVE on the ladder too:** 3 of 6 state-transition acks ran cache-0 (t18 Offer, t38 ConfirmSlots, t47 Closing) — the transition warm loses the race to the same-turn ack round. The parked cure is iter68 T4 chain-end ack flush (`cc34343` on branch `engine/iter68-speech-flow`), plan option (A) deterministic ack.
6. **ElevenLabs voice lab (owner-driven, current focus):** owner supplied 3 shared-library voice IDs; identified via `/v1/shared-voices` search and Eryn ADDED to the account (`POST /v1/voices/add/{public_user_id}/{voice_id}`): Eryn = `kdnRe2koJdOK4Ovxn2DI` ("Genuine, Friendly and Natural"; public_owner_id `5c9b187b7fc0fd10cfa6bc6e03699490bacc6f4c5e634b9ffcb1e62bd032fdef`), Sarah A&I = `Nhs7eitvQWFTQBsf0yiT` (NOT yet added to account), Vanessa = `8DzKSPdgEQPaK5vKG0Rs` (NOT yet added). Prod Sarah remains `uG1JFy6xppqckhHCs2KG` "Casual & Modern".
7. **New EL key upserted (owner 2026-09-24, full permissions, old key DEPRECATED):** `ELEVENLABS_API_KEY=sk_93675fa93c4eafdbf3aadf8319eb7aeb00035b570d960fe2` in `/home/julio/projects/clean_diallux_SDR/engine/.env` + `/tmp/opencode/wt-iter66/engine/.env` + `/tmp/opencode/wt-iter68/engine/.env` + `/tmp/opencode/wt-iter70/engine/.env`. Verified: account "Cesar", creator tier, voices_write works.
8. **Current .env voice state (owner-directed, live):** `TTS_PROVIDER=elevenlabs` · `ELEVENLABS_MODEL_ID=eleven_turbo_v2_5` (the "v2.5" family — turbo is the balanced one; flash_v2_5 is the light sibling; no other "v2_5" exists) · `ELEVENLABS_VOICE_ID=kdnRe2koJdOK4Ovxn2DI` (Eryn) · `ELEVENLABS_STABILITY=0.4` (tested sequence: 0.0 → 0.6 → 0.4) · `ELEVENLABS_STYLE=1.0` (max) · `ELEVENLABS_SPEED=1.2` (engine clamp max; range 0.7–1.2). Cartesia keys untouched: `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` (Linda `829ccd10-f8b3-43cd-b8a0-4aeaa81f3b30`, speed 1.12). Env backup pre-Eryn: `/tmp/opencode/env_backup_pre_eryn`.
9. **Rollback to production voice = flip `TTS_PROVIDER=cartesia` + restart.** Owner confirmed hearing Linda (not Eryn) when provider was still `cartesia` — not an endpoint bug.
10. **Second live call 04:52** (`micbridge-824023169cad`, 2 rounds only, aborted/short) — NOT analyzed; owner may finish it later.
11. **Endpoints doc:** the EL multi-stream-input WS contract + clamps live in `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/elevenlabs_tts.py` header + iter66 plan `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter66_elevenlabs_cutover.md`; official reference used live: `POST /v1/voices/add/{public_user_id}/{voice_id}` (voice-library share) and `GET /v1/shared-voices?search=`.
12. **Engine pending work (NOT this plan, separate):** iter71 T2 ack-latency fix (options table in `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter71_intake_samples_ack_latency.md`; owner lean = deterministic ack / iter68 T4 concept) + iter70 branch `engine/iter70-speech-fixes` @ `dc62fb9` unmerged.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Lane :8024 = the test surface; code swaps via working-tree file copy + `systemctl --user restart diallux-8024.service` | The proven deploy mechanism all session (owner-directed) |
| Cartesia `sonic-3.6-2026-08-27` stays the PRODUCTION pin; EL = test lane only | VOICE LAW — the proven "out of this world" config; do not lose it again |
| EL model for voice tests = `eleven_turbo_v2_5` | Owner's "Eleven Labs version 2.5" = the turbo_v2_5 pin already in `.env` |
| Eryn profile progress: 0.0/1.0/0.8 → 0.6/1.2 → **0.4/1.2 (current)** | Owner taste test in-flight; continue the matrix |
| EL voices must be ADDED to the account before synth | `voice_not_found` until added; new key has `voices_write` |
| Verdict basis for per-turn tables = AGENT latency only (TTFT/cache/LLM→TTS); stt→llm shown separately | Mixing caller STT wait into verdicts made the first table "make no sense" (owner verdict) |
| Langfuse `usageDetails.inputTokenDetails` is UNRELIABLE for cache on live gens | Cache came out 0 everywhere while the engine journal showed hits — journal `round usage` lines are the ground truth |
| Old EL key `sk_cd4fdd…` DEPRECATED | Owner order 2026-09-24; new key `sk_93675f…` everywhere |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner verdict on Eryn 0.4/1.2 | owner ear test in progress NOW |
| Next voice pick (Sarah A&I / Vanessa) | owner says which; add to account via API (new key) |
| Final Eryn recipe (stability/speed/style) | owner's ear after the matrix |
| Whether prod cutover to EL-Eryn happens | OWNER ONLY; Cartesia stays prod until then |
| iter71 T2 mechanism pick (A deterministic ack / B warm re-fire) | separate session on plan_v5_iter71 |

## Environment & Dependencies
- Lane: systemd `diallux-8024.service`, port :8024, WorkingDirectory `/home/julio/projects/clean_diallux_SDR/engine`; logs `journalctl --user -u diallux-8024.service`
- Mic URL (owner-held token in `.env` `VOICE_TEST_TOKEN`): `https://flores.diallux-ai.site/voice24/mic?k=$VOICE_TEST_TOKEN`
- `.env` knobs: `TTS_PROVIDER` (cartesia|elevenlabs) · `ELEVENLABS_MODEL_ID=eleven_turbo_v2_5` · `ELEVENLABS_VOICE_ID` · `ELEVENLABS_STABILITY` (0.0-1.0) · `ELEVENLABS_STYLE` (0.0-1.0) · `ELEVENLABS_SPEED` (engine clamp 0.7-1.2) · `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` NEVER TOUCH
- EL endpoints: synth `wss://api.elevenlabs.io/v1/text-to-speech/<voice>/multi-stream-input?model_id=<model>` (voice_settings ride FIRST message: stability/style/speed — `elevenlabs_tts.py:74-185`); library search `GET https://api.elevenlabs.io/v1/shared-voices?page_size=5&search=<id>` (header `xi-api-key`); add shared voice `POST https://api.elevenlabs.io/v1/voices/add/{public_owner_id}/{voice_id}` body `{"new_name": "...", "bookmarked": true}`; account voices `GET /v1/voices`; health `GET http://127.0.0.1:8024/health`
- Langfuse SDK: `/home/julio/projects/clean_diallux_SDR/engine/scripts/lf.py` (traces --name micbridge --hours N; _obs via importlib for spans); ledger SDK: `/tmp/opencode/wt-iter44/.venv/bin/python /tmp/opencode/wt-iter44/scripts/live_sql.py` (rounds/sops/sop-import)
- Ground truth for per-round latency/cache = the engine journal `round usage: turn=… state=… input=… cache_read=… ttft=…` lines (NOT Langfuse tokenDetails)
- Per-turn E2E = Langfuse SPAN `turn:<n>` output metrics: `stt_eot_to_llm_first_ms`, `llm_first_to_tts_first_ms`, `tts_first_to_audio_out_ms`, `e2e_response_ms`, `e2e_turn_ms`, `barge_in`
- Evidence dirs: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter71-ack-latency/` (existing) — new voice runs go to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter72-voice-lab/`

## Architecture (one block)
```
Owner ear test (mic URL) -> lane :8024 (main content 50a453f+T7)
    ├─ TTS: .env-selected provider (EL Eryn matrix / Cartesia Linda rollback)
    ├─ measurement: journal round-usage lines + Langfuse micbridge trace
    ├─ tables: per-turn ✅/❌ (TTFT/cache/e2e) + TTFT p50/p90 + LLM→TTS + cold-ack count
    ├─ audit: 3 SOPs per call → ledger sops table
    └─ verdict → owner adjusts recipe or swaps voice → repeat
```

## File Map
| File (absolute path) | What changes | New/Edit |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/engine/.env` | T0: current state (EL, Eryn 0.4/1.2) — voice swaps = 2-line edits | Edit (owner say-so each) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter72-voice-lab/01_matrix.md` | voice/recipe × call table (gitignored evidence) | New |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter72-voice-lab/02_sop_rows.json` | per-call SOP rows | New |
| ledger `sops` table | imported rows per recipe | Append via SDK |

## Deploy Rules
- Voice param change (owner say-so per change): edit the ONE `.env` line → `systemctl --user restart diallux-8024.service` → verify `curl -s http://127.0.0.1:8024/health` prints `elevenlabs/<model>` and `tts: ready`.
- Provider rollback: `TTS_PROVIDER=cartesia` + restart → journal MUST print `cartesia connected (model=sonic-3.6-2026-08-27)`.
- Add a new EL voice (when owner picks Sarah A&I / Vanessa): `POST /v1/voices/add/{public_owner_id}/{voice_id}` with the new key from `.env` (search `/v1/shared-voices` for the `public_owner_id` first), then set `ELEVENLABS_VOICE_ID`.
- NEVER touch: `CARTESIA_MODEL_ID` (any .env), `CARTESIA_VOICE_ID`, `CARTESIA_SPEED`, `TTS_PROVIDER` without owner say-so, `VOICE_TEST_TOKEN`, the other lanes (:8020-8023, :8026 processes), `:8000-8003`, `engine/diallux/media/prewarm.py` semantics (it is main-content now), git history (working-tree file swaps only, backups first).
- git working tree discipline: today's swaps are backups-first; the working tree currently EQUALS main content — if owner orders a NEW code variant (e.g. iter70 `dc62fb9`), stage from that commit into `/tmp/opencode/stage_*` and swap only files that differ (same 15-file pattern as this morning).

## Tasks (in order) — HITL at every T
### T0 — HITL ASK (resume)
Owner verdict on Eryn 0.4/1.2 (in-flight). Options: keep recipe / adjust / next voice.

### T1 — Eryn recipe matrix (owner-driven)
For each recipe the owner dictates: edit `.env` lines → restart → owner calls the mic URL → pull table + import.
Commands (full):
```
cd /home/julio/projects/clean_diallux_SDR/engine
sed -i 's/^ELEVENLABS_STABILITY=.*/ELEVENLABS_STABILITY=<v>/' .env   # and/or SPEED/STYLE
systemctl --user restart diallux-8024.service && sleep 6
curl -s http://127.0.0.1:8024/health | grep -o '"tts": "eleven[^"]*"'
journalctl --user -u diallux-8024.service --since "<window>" --no-pager | grep "round usage"
```
Measurement (same as call 1): `lf.py` trace pull → turn spans (e2e) + gen metadata (ttft) + journal cache → per-turn ✅/❌ table → `live_sql.py import --window "<HH:MM-HH:MM>" --run mic-20260924-<slug> --commit <lane-code-sha>` → 3-SOP audit → `sop-import`.
Verification: every voice recipe row lands in `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter72-voice-lab/01_matrix.md` with TTFT p50/p90, LLM→TTS, cold-ack count, SOP verdicts, owner's ear note.

### T2 — Sarah A&I + Vanessa (owner pick, if any)
Add to account via the share endpoint (new key), swap `ELEVENLABS_VOICE_ID`, same matrix. Sarah A&I `Nhs7eitvQWFTQBsf0yiT` · Vanessa `8DzKSPdgEQPaK5vKG0Rs` (public_owner_ids UNKNOWN — must be fetched via `/v1/shared-voices?search=<voice_id>` at run time).

### T3 — EL latency baseline vs Cartesia (zero extra spend beyond the owner's own test calls)
One table comparing: Cartesia Linda lane calls (this morning) vs Eryn calls — TTFT p50/p90, LLM→TTS p50, cold-ack count, e2e. EL first-byte latency is the known risk vs Cartesia's ~92ms prewarm.

### T4 — Verdict + keep/park
Owner verdict: keep EL recipe in `.env` / revert `TTS_PROVIDER=cartesia`. Record in `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter72-voice-lab/01_matrix.md` + PENDING_TASKS row. If Eryn wins: owner decides prod cutover (separate owner-gated decision, VOICE LAW amendment).

### T5 — Handoff back to iter71 (separate session)
The ack-latency fix (plan option A/B, `plan_v5_iter71_intake_samples_ack_latency.md`) and Intake seeds resume AFTER the voice lab; iter70 branch `engine/iter70-speech-fixes` @ `dc62fb9` remains the unmerged code tip.

## Validation Plan (end-to-end)
1. Every .env change = owner say-so + restart + `/health` verify.
2. Every call = journal round-lines + Langfuse trace pulled BEFORE the next test (windows don't overlap — the 04:52 contamination lesson: filter by trace id AND time window).
3. Every analyzed call: ledger import + 21-row SOP table minimum.
4. Cartesia rollback verified by journal line `cartesia connected (model=sonic-3.6-2026-08-27)`.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| iter71 T2 ack-latency fix + T3 Intake seeds | Own plan exists; resume after voice lab |
| iter70 merge / iter68 chain-end port | Owner-gated (LAW 0) |
| Prod cutover to EL-Eryn | Owner-only decision after matrix |
| EL key rotation for the leaked old key | Owner-deprecated it; rotation via EL UI optional |
| Second 04:52 call analysis | 2 rounds only, likely aborted; analyze if owner completes it |
