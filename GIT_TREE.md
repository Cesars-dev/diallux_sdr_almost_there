# GIT_TREE.md — living map (auto-generated: scripts/git-tree.sh)

> Regenerated: **2026-09-23 00:13 UTC** · repo HEAD: `f236697 iter66-T7: tts_provider default -> elevenlabs (owner directive 2026-09-22; Sarah uG1JFy6xppqckhHCs2KG turbo_v2_5 ear test); EL env block to main .env; provider-default-agnostic pins`
> Doctrine: this file is refreshed at EVERY merge/iteration commit. If it's stale, run the script.

## Tree (source zones; evidence/cold zones summarized)
```
docs/
Testing_guidelines/
api/
deprecations/
legacy/
  dialux-groq-era/
    groq-server/
    llms/
platform/
engine/
agent/
  knowledge_bases/
deploy/
diallux/
  graph/
  media/
  observability/
  prompts/
  static/
    mic/
eval/
  scenarios/
plans/
public_repos/
  state_machine_voice/
    agent/
    deploy/
    diallux/
    eval/
    reports/
    scripts/
    tests/
reports/
  phaseb-engine-chain/
    archive/
scripts/
tests/
  llm2llm/
plans/
archive/
  DEPLOY_V6.4_2026-08-22/
  V6.6_ITERATIONS_2026-08-22/
retell/
heating-uk/
  edits/
  multiprompt/
    V3/
    V3.1/
    WEBHOOK_TEST/
    _archive/
  original_design/
  performance_tests/
    archive/
    personas/
    retrieved_chats/
  single_prompt_test/
sdr/
  _archive_versions/
    V6.6/
    V6.7/
    V6.8/
    V6.81/
    V6.82/
    V6.83/
    V6.84/
    V6.85/
    V6.86/
    V6.87/
    V6.88/
    V6.89/
    V6.90/
    V7/
    V7.1/
    V7.2_production/
    V7.3_craft_kb/
    V7.4_hard_gpt52/
    V7_personal_iteration/
    V7_personal_iteration2/
    V7_personal_iteration3/
    sandbox_context_test/
    working_agent/
  config/
  current/
    lab/
    retell/
  kb_authoring/
  testing/
    runners/
  versions/
    V7.5_lean/
    V7.6_verify_state/
    V7.7_set_callback_number/
    V7.8_appt_confirmed/
    V7.8_reach_details/
scripts/
hooks/
services/
cal_slots_endpoint/
proxy_guard/
  logs/
time_endpoint/
validator_endpoint/
```

## Engine iteration branches (the real history)
```
  engine/iter67-twilio-live-lane             6b53d5a  2026-09-23  iter67 T5 prep: deploy artifacts for VPS lane (Caddy calls.diallux-ai.site -> 12
  engine/iter65-model-defaults               fc45536  2026-09-22  iter65: T1 boot prewarm (shared pool, dual entry) + T2 speech sanitizer + T3 dv 
  engine/iter66-elevenlabs-cutover           e91af1a  2026-09-22  docs: prod EL voice config pinned (owner ear test 2026-09-22) — Sarah Casual&Mod
  engine/iter64-industry-gate                801fcdf  2026-09-22  iter64c: MODEL LAW — agent model = gpt-5.4; llm.json field now matches the .env 
  engine/iter63-rag-fire-sim                 2cb810f  2026-09-22  iter63: scripts/rag_replay.py — RAG-ANALYSIS-SOP chunk-text replay SDK (pool/ser
  engine/iter64-elevenlabs-cutover           2cb810f  2026-09-22  iter63: scripts/rag_replay.py — RAG-ANALYSIS-SOP chunk-text replay SDK (pool/ser
  engine/iter62-lane-restore                 6d651ea  2026-09-22  iter62: lane restore E1-E11 + R1/R2 rewrite + 9-pin file (suite 422 green; mic g
  engine/iter61-prewarm-staleness            6c986e8  2026-09-21  iter61: prewarm socket staleness fixes AUD-11/12/13 (drop v1 keepalive, TTL pool
  engine/iter60-audit-fixes                  c7f8d2d  2026-09-21  iter60b: scripts/mic_events.py — one-command mic-call event puller (log timeline
  engine/iter59-kb-everywhere-freshness      6d13803  2026-09-20  iter59 T3-T5: rag_fire_mode (speech-window/round-sync/hybrid), KB-everywhere, de
  engine/iter58-eot08-public-mic             db8e56f  2026-09-20  iter58 T1: mic probe RTT + chunk inter-arrival metric + /health eager_eot_thresh
  engine/iter56-state-delta-payload          4cfb7a5  2026-09-19  iter57 T2-fix: preflight check_rag inserts engine root on sys.path (scripts/ run
  engine/iter57-pre-start                    abde308  2026-09-18  iter56 C2: observability fields — state_in_delta + delta_tokens on the round usa
  engine/iter55-tts-era-turn1-ammo           7ac9879  2026-09-18  iter55 C1 (T0 observability): warm:{key} spans via done-callback (fired_at/ms/ou
  engine/iter52-industry-pin                 054af7b  2026-09-16  iter52: pinned industry vertical + two-layer plumbing (fetch-once metadata pin, 
  engine/chat-tests                          fc2fa2f  2026-09-16  mvp-finally: merge recorded in ledger + GIT_TREE.md regenerated (4559a33, tag mv
  engine/iter49c-engine-finish               1f15e8b  2026-09-16  iter49h T7 (owner-approved fix): flaky cap=0 assert units bug in test_async_boun
  engine/mvp-finally                         1f15e8b  2026-09-16  iter49h T7 (owner-approved fix): flaky cap=0 assert units bug in test_async_boun
  engine/iter49-rag-parity                   fc42a3e  2026-09-15  iter49 T4: live multi-lane fresh retrieval (WORK-IN-PROGRESS save) — kb_slugs_fo
  engine/iter48-rag-truth                    c40f06b  2026-09-13  iter49-ops: session tracking — sessions table (branch/commit) + session stamps o
  engine/iter47-call-ledger                  fd997e5  2026-09-12  iter47 T1: pin iter44 T8 battery run (05:50-06:15) into ledger — the working bas
  engine/iter46-latency-floor                515f81f  2026-09-11  iter46 battery evidence: post-revert battery + ladder reports (12/13 first-13, T
  engine/iter44-cache-floor                  68541f7  2026-09-11  iter43 T3 FIX: lite head kb=True->kb=False (16.5k->1.6k tokens, was 10x heavier 
  engine/iter43-eot-cache-askgate            374318b  2026-09-11  iter43 T3 FIX: lite head kb=True->kb=False (16.5k->1.6k tokens, was 10x heavier 
  engine/iter42-dedupe-window                f5c0912  2026-09-10  iter42: TTS dedupe sliding window (6 sentences) — kills multi-sentence double-sp
  engine/iter41c-luna-responses-api          ec9c1b3  2026-09-10  iter41c: gpt-5.6 (luna) tool-calling fix — Responses API + first-class reasoning
  engine/iter41-quality-debt                 65d7f3b  2026-09-09  iter41 T1b: cross-round double kill — dedupe seed (last SPOKEN sentence) carried
  engine/iter41b-luna                        5810620  2026-09-09  iter41 T3 commit3: mock check_availability is DATE-AWARE — serves slots for the 
  engine/iter40-spike-readback               91aa4ac  2026-09-09  iter40 T6b commit7: Closer-scoped end_call skip gate — spoken end_call from Clos
  engine/iter38-memory-latency-fix           491a7a3  2026-09-09  iter38 hygiene: untrack .venv symlink (retune commit accidentally added it)
  engine/iter38b-gpt54                       491a7a3  2026-09-09  iter38 hygiene: untrack .venv symlink (retune commit accidentally added it)
  engine/iter37-browser-mic-tts              4e72200  2026-09-09  iter37 fix#2: init query='' before frozen-reuse branch (live mic test round-2 cr
  engine/iter33-phaseb-engine-chain          bfbd181  2026-09-09  iter33: GK+BRK live battery 21 personas (19/21, 10 hire/11 solid) + report 09 + 
  engine/iter34-gpt41-model-only             21deffc  2026-09-08  iter36 ledgers: autopilot audit refs + ITERATIONS §25 + git_tree row
  engine/iter35-sdk-sync                     7d90045  2026-09-08  iter35 SDK sync: port call.py digest + lf.py lat from original (fork was strict 
  engine/iter32-silent-round-gate            596f1bb  2026-09-08  iter32 ledgers: ITERATIONS §22 + git_tree row — battery 12/13, ended 13/13, mach
  engine/iter31-c3d-wrap-dampener            5d32c60  2026-09-07  docs: git_tree.md iter30/iter31 branch rows
  engine/iter31-c3e-silent-rounds            5d32c60  2026-09-07  docs: git_tree.md iter30/iter31 branch rows
  engine/iter31-c3c-silent-endcall-dampener  52e8e3b  2026-09-07  iter31 C3c fix: dampener reads the REAL server-owned booking_verified (booking_c
  engine/iter31-c3b-tail-after-history       48d6ad3  2026-09-07  iter31 C3b: STATE BLOCK + frozen RAG section moved to a TRAILING system message 
  engine/iter30-fast                         4acd69b  2026-09-07  iter31 C3: prompt-cache architecture — byte-stable static head (dvs literal, cac
  engine/phaseB-wip-stash                    cb1185e  2026-09-07  On iter29-30-one-trip: phaseB-wip
  engine/iter29-winner                       8272a68  2026-09-07  iter29: one-trip-per-turn — per-round tool dedupe (A1), one-trip routing via rou
  engine/main                                5e9d088  2026-09-07  Merge iter28-server-time-payload (62c9a81 + battery ledgers): server-time-payloa
  engine/iter28-server-time-payload          04583d2  2026-09-07  iter28 battery: first-13 LIVE 13/13 PASS — ledgers (report 20, ITERATIONS §20, g
  engine/iter27-human-slots                  8c0a0bb  2026-09-07  iter27: OTEL amendment — validator human-time contract blocker (Maria x15), Pedr
  engine/iter25-b                            11f4d93  2026-09-06  iter26: iter25-b first-13 ladder + deep-dive done (report 18)
  engine/snap-iter22-aborted                 e9b700b  2026-09-06  snap: snap-iter22-aborted (2026-09-06) — imported from folder-photocopy 'Dialux_
  engine/snap-v1.7-iter19                    261b2bd  2026-09-06  snap: snap-v1.7-iter19 (2026-09-06) — imported from folder-photocopy 'Dialux_SDR
  engine/snap-v1.8-iter20                    07401a3  2026-09-06  snap: snap-v1.8-iter20 (2026-09-06) — imported from folder-photocopy 'Dialux_SDR
  engine/iter25-c                            0fa2d7f  2026-09-06  git_tree: T5 batteries done — a/b/c 5/5 GK book; audit 17_iter25; NO MERGE
  engine/iter25-a                            202b4fd  2026-09-06  git_tree: iter25-a built (29c93a2)
  engine/iter25-d                            942c180  2026-09-06  T0: git_tree.md ledger born; baseline pinned at f65e63d
  engine/snap-v1.5-iter15                    68ed4f4  2026-09-05  snap: snap-v1.5-iter15 (2026-09-05) — imported from folder-photocopy 'Dialux_SDR
  engine/snap-v1.6-iter16                    781712e  2026-09-05  snap: snap-v1.6-iter16 (2026-09-05) — imported from folder-photocopy 'Dialux_SDR
  engine/snap-v1.3-iter10                    7b0fa33  2026-09-04  snap: snap-v1.3-iter10 (2026-09-04) — imported from folder-photocopy 'Dialux_SDR
  engine/snap-v1.3-iter7                     0f3c94a  2026-09-04  snap: snap-v1.3-iter7 (2026-09-04) — imported from folder-photocopy 'Dialux_SDR/
  engine/snap-v1.3-iter7b                    86781f9  2026-09-04  snap: snap-v1.3-iter7b (2026-09-04) — imported from folder-photocopy 'Dialux_SDR
  engine/snap-v1.3-iter8                     ffcf4f0  2026-09-04  snap: snap-v1.3-iter8 (2026-09-04) — imported from folder-photocopy 'Dialux_SDR/
  engine/snap-v1.4-iter13                    45e62be  2026-09-04  snap: snap-v1.4-iter13 (2026-09-04) — imported from folder-photocopy 'Dialux_SDR
```

## History-preserving refs (nested-repo archaeology)
```
  history/old-parent-main-baseline
  history/parent-cal-slots-hardening
  history/parent-merging-logic
```

## Root repo — recent main
```
  f236697 iter66-T7: tts_provider default -> elevenlabs (owner directive 2026-09-22; Sarah uG1JFy6xppqckhHCs2KG turbo_v2_5 ear test); EL env block to main .env; provider-default-agnostic pins
  0146492 docs: GIT_TREE refresh — iter66+iter65 merged
  89a2eea docs: ITERATIONS — iter65 merged sha + rebase note
  50a453f merge: engine/iter65-model-defaults — T1 boot prewarm (shared pool, dual entry) + T2 speech sanitizer + T3 dv carryover DAILY + T4 mic spans + model/fire-mode defaults (gpt-5.4, hybrid); rebased over iter66, suite 463
  fc45536 iter65: T1 boot prewarm (shared pool, dual entry) + T2 speech sanitizer + T3 dv carryover DAILY + T4 mic spans + model/fire-mode defaults (gpt-5.4, hybrid) + gpt-5.2 sweep
  40328b4 docs: ITERATIONS — iter66 EL cutover merged (84fd1ce) + iter65 model-defaults line
  84fd1ce merge: engine/iter66-elevenlabs-cutover — EL multi-stream adapter rewrite, factory transport, prewarm gate, pins (T1-T7); owner ear test e91af1a
  6e8800e plan: iter67 twilio live lane — number→Caddy wss→engine (ports 8024/8026, signature gate, systemd deploy, provisioning; blocked on owner Twilio creds+number+hostname; iter66 merges first per LAW 0 v2.1)
```

## Cold archive (tarballs, gitignored — NOT in git)
```
  96M      _cold_archive/diallux-twin-stale-correct-spelling.tar Sep 8
  17M      _cold_archive/dialux-6.1-iterations-era.tar Sep 8
  6.6M     _cold_archive/retellai-mcp-server-nested.tar Sep 8
  207K     _cold_archive/state-machine-copy.tar Sep 8
  192M     _cold_archive/v5-snapshots-all-9.tar Sep 8
```
