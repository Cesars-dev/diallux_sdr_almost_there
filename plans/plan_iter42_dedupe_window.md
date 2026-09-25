# PLAN — iter42: TTS dedupe sliding window (kill the multi-sentence double-speak)

## Meta
- Date: 2026-09-10
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — widen the iter41 T1/T1b TTS sentence-dedupe from a 1-sentence memory to a sliding window of the last 6 sentences (same-turn, carried across tool-rounds of the turn), so multi-sentence block doubles (`A,B,A,B`) are dropped from the SPOKEN stream like single doubles already are; unit-test it; re-run the gpt-5.4 LOW+MEDIUM 13-persona batteries; verify the Sofia/Carlos/Jorge doubles are gone from the digests with no new harness regressions. Ends with the full path of this plan.
- Status: PLAN ONLY (not started — awaits approval)

## Compaction Context (verbatim carry — session 2026-09-10, iter41b/41c + HUMANIZED deep-dive)

- **Project:** Dialux SDR voice engine "Linda" — LangGraph 9-state pipeline, Deepgram Flux STT → LLM → gates → Cartesia TTS. Repo FORK = `clean_diallux_SDR` (MAIN workspace). gpt-5.4 is the production-candidate model; **luna (gpt-5.6) is DEAD** — the Responses-API config fix (`use_responses_api=True` + first-class `reasoning_effort="low"`, branch `engine/iter41c-luna-responses-api` @ `ec9c1b3`) restored tool-calling but luna still fails (books only 4/7 book-personas via a booking-completion narration loop) and is ~3× slower (round p50 3.6s vs 5.4's 1.97s). Do NOT revive luna in this plan.
- **gpt-5.4 batteries (2026-09-10, branch `engine/iter41-quality-debt` @ `65d7f3b`, worktree `/tmp/opencode/wt-iter41`):** LOW = 12/13 harness PASS (Pedro over-book = known persona variance), round p50 1970ms, LLM p50 1.2s; MEDIUM = 11/13 (Pedro + Brenda lost), round p50 1433ms. Reports: `research/surgeon/iter41-quality-debt/07_gpt54_low_vs_med.md` (+ `08` stress, `09`/`10` luna). Suite **199 green** at `65d7f3b`.
- **HUMANIZED "FAIL" audit verdict (owner-validated):** the SOP's R5.5 verbatim hard-flag over-counts. Of the LOW "5 fails", only **Sofia t1** is a genuine defect; Ray/Gene (farewell loops — caller won't hang up, `end_call` DID fire every turn), Daniel (correct literal re-answer to "are you AI?") and Susan's `"Is that all correct?"` ×3 (REQUIRED verbatim read-back ceremony, `contact_details.md` Step 6 lines 43–47) are NOT bugs. Genuine double-speak across both batteries: **Sofia (LOW t1), Carlos (MED t1), Jorge (MED t2), Sofia (MED t1/t6/t18)** — all are ONE response emitted twice back-to-back inside a single turn (`A,B,A,B`), zero new content in the 2nd copy.
- **Root cause (verified in code):** the T1/T1b dedupe (`diallux/graph/builder.py:525–580`) flushes tokens per sentence (`_SENTENCE_SPLIT_RE = [.?!]+(?=\s|$)|\n+`, builder.py:83; key = `_norm_sentence` lowercase+whitespace-collapse, builder.py:86) and compares each new sentence against **only the single last-flushed sentence** (`last_flushed_sentence`, builder.py:535/565), whose seed `tts_last_sentence` carries across tool-ROUNDS of the same turn (builder.py:593) and resets to `""` per turn (builder.py:826–828). In `A,B,A,B` the 2nd `A` compares against `B` (≠) and the 2nd `B` against `A` (≠) → both spoken. The gate needs a window, not 1 slot.
- **Key mechanics (owner Q&A, resolved):** the dedupe operates on the **TTS token stream only** — it never re-queries the model, never touches model output/history, and never creates dead air for within-turn doubles (the 1st copy always plays). Owner explicitly rejected a "fast model re-try" (adds latency/cost/loop risk) and rejected cross-turn dedupe (legit re-asks/farewells/ceremony must keep playing). The harness json transcript `agent` field is the **post-dedupe spoken stream** (`tests/llm2llm/harness.py:168` collects `tts_token`, `:178` joins into `speech`, `:358` writes it as `agent`) — so post-fix, doubles DISAPPEAR from `call.py digest` R5.5 for the same-turn cases. Cross-turn R5.5 hits (Ray/Gene/Daniel/Susan) will REMAIN in digests — expected, out of scope.
- **Model settings:** gpt-5.4, `OPENAI_MODEL=gpt-5.4`, config default `openai_reasoning_effort="none"`, `openai_verbosity="low"`; MEDIUM batch via env `OPENAI_VERBOSITY=medium OPENAI_REASONING_EFFORT=none` (pydantic-settings, no prefix). gpt-5.* + tools on chat-completions REQUIRES reasoning_effort='none'.
- **Harness:** `tests/llm2llm/harness.py --personas <Name> --rag --langfuse --max-turns 28` (mock slots default). 13 original personas: Maria, Susan, Danny, Marcus, Carlos, Pedro, Sofia, Jorge, Daniel, Brenda, Gene, Frank, Ray. Larry NEVER in batches. Parallel-safe as separate processes; batteries take ~2–4 min.
- **Latency reference:** T1 dedupe measured ~0.1ms first-token (benchmarked in iter41) — a 6-sentence window is the same order (in-memory list scan), not a latency concern.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Window = last **6** flushed sentence keys, within-turn (carried across tool-rounds of the same turn) | Catches every observed double-speak block (max block = 3 sentences, Carlos t1); 6 gives headroom; cross-TURN stays out of scope |
| Drop = silent removal from TTS stream only; model content/history untouched; NO re-query, NO fast-model re-try | Owner directive; dedupe is ~0.1ms deterministic; 1st copy always plays so no dead air |
| NO cross-turn dedupe | Farewells (Ray/Gene), identity re-answers (Daniel), required ceremony (`Is that all correct?`) are legit repeats — owner verdict |
| Turn-silence guard: if a round's every sentence would be dropped AND nothing spoken yet this turn, keep the first sentence | Belt-and-braces; within-turn doubles can't trigger it, cross-round all-dup rounds could |
| Config knob `tts_dedupe_window: int = 6` beside `tts_dedupe_sentences: bool = True` | Tunable without code edit; `False` still disables dedupe entirely |
| Verify via digests (spoken stream) + unit tests, NOT by expecting R5.5 to hit zero | Cross-turn R5.5 (Ray/Gene/Daniel/Susan) legitimately remains |
| Base branch `engine/iter41-quality-debt` @ `65d7f3b`; new branch `engine/iter42-dedupe-window` | gpt-5.4 is the production candidate; luna dead |
| Larry excluded from all batteries | Permanent assassin gate |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| None — all inputs pinned | — |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12; langgraph 1.2.11, langfuse 4.15.1, httpx, fastapi, pytest).
- Base worktree: `/tmp/opencode/wt-iter41` @ `65d7f3b` (`.env` has `OPENAI_MODEL=gpt-5.4`).
- New worktree this plan: `/tmp/opencode/wt-iter42` (branch `engine/iter42-dedupe-window`), `.venv` symlink → `/home/julio/projects/clean_diallux_SDR/engine/.venv`, `.env` copied from wt-iter41.
- Suite: `cd /tmp/opencode/wt-iter42 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests -q` → **199 passed** at base (plus new dedupe tests after T2).
- Langfuse `http://localhost:3001` (ingest drops traces under 13-parallel load — json_logs are source of truth; OTEL optional here).
- Digest SDK: the fork's `scripts/call.py` LACKS `digest` — temp-copy ORIGINAL's `call.py` into a staging dir per batch and `rm` after (proven pattern). ORIGINAL root: `/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/diallux-langgraph-production-v5`.
- Never touch: `:8000/:8001/:8002/:8003/:8005`, live agent IDs (`agent_f305…`, `agent_1698…`, `agent_87e4…`), `slots.db`, ORIGINAL dirty files.

## Architecture (one block)
```
builder.py turn loop (per token)
  buffer tokens → flush on [.?!|\n] → key=_norm_sentence
  BEFORE: key == last_flushed_sentence ? drop : speak        (1-slot memory)
  AFTER:  key in last-6 window ? drop : speak                (6-slot window)
          + guard: never silence a turn that hasn't spoken
  window carried across tool-rounds of the turn; reset [] per turn
        ▼
harness transcript 'agent' = joined tts_tokens (SPOKEN stream)
        ▼
T0 suite → T1 code → T2 unit tests → T3 LOW 13 battery + digest
→ T4 MED 13 battery + digest → T5 report + commit + ASK JULIO
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_iter42_dedupe_window.md` | this plan | NEW (commit main) |
| `/tmp/opencode/wt-iter42/diallux/config.py` | add `tts_dedupe_window: int = 6` beside `tts_dedupe_sentences` (line ~86) | EDIT |
| `/tmp/opencode/wt-iter42/diallux/graph/builder.py` | 1-slot → 6-slot window: seed read (~535), flush compare (~564–569), end-of-stream pending check (~577), updates carry (~593: `tts_last_sentence` → `tts_sentence_window`), per-turn reset (~828: `""` → `[]`), silence guard | EDIT |
| `/tmp/opencode/wt-iter42/tests/test_dedupe_window.py` | unit tests (6 cases, see T2) | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter42-dedupe-window/01_dedupe_window_report.md` | before/after report | NEW (gitignored evidence) |
| `/tmp/opencode/sop_batch_w42_{low,med}/` | staged json + temp-copied `call.py` | NEW (temp; rm scripts after) |
| `/tmp/opencode/iter42_{low,med}_<Persona>.log` | battery stdout | NEW (temp) |

## Deploy Rules
- Suite green before launch (199 + new tests).
- Batteries as separate `setsid nohup` background processes; `.env` sourced with `set -a; . ./.env; set +a`; env overrides exported BEFORE the python invocation.
- Mock slots only → NO real bookings, nothing to cancel.
- Temp-copied ORIGINAL `call.py` is `rm`-ed after each digest run.
- NEVER touch `:8000/:8001/:8002/:8003/:8005`, live agent IDs, `slots.db`.
- **LAW 0:** commit on the branch; NO merge to `engine/main` without Julio's explicit say-so. Docs (this plan) commit straight to main.

## Tasks (in order)

### T0 — Branch + worktree + suite
Goal: create the iter branch and confirm the base is green.
Commands:
```bash
cd /tmp/opencode/wt-iter41 && git worktree add -b engine/iter42-dedupe-window /tmp/opencode/wt-iter42 65d7f3b
ln -sfn /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter42/.venv
cp /tmp/opencode/wt-iter41/.env /tmp/opencode/wt-iter42/.env
cd /tmp/opencode/wt-iter42 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests -q
```
Verification: HEAD = `65d7f3b` on `engine/iter42-dedupe-window`; suite exits 0 (199 tests).
Dependencies: none.

### T1 — Sliding-window dedupe (the edit)
Goal: replace the 1-slot memory with a 6-slot window + silence guard.
Files: `/tmp/opencode/wt-iter42/diallux/config.py`, `/tmp/opencode/wt-iter42/diallux/graph/builder.py`.
Edit spec (exact):
1. `config.py` — beside `tts_dedupe_sentences: bool = True` (~line 86) add:
   `tts_dedupe_window: int = 6   # iter42: sentences of within-turn history the dedupe remembers`
2. `builder.py` seed (~535): replace
   `last_flushed_sentence = (state.get("tts_last_sentence") or "") if runtime.settings.tts_dedupe_sentences else ""`
   with
   `window: list[str] = list(state.get("tts_sentence_window") or []) if runtime.settings.tts_dedupe_sentences else []`
   plus `spoken_any = bool(state.get("turn_spoke"))` (silence-guard flag, seeded from turn_spoke).
3. Flush compare (~564–569): replace the `if key and key == last_flushed_sentence: continue` test with:
   - `if key and key in window:`
     - `if not spoken_any: ` → speak it anyway (append key to window; guard: never open a turn with silence) — i.e. fall through to the emit path.
     - `else:` → `continue` (drop from TTS; do NOT append — the key is already in the window).
   - else (no dup): emit tokens, `window.append(key)`, `spoken_any = True`, then trim `window` to the last `runtime.settings.tts_dedupe_window` entries.
4. End-of-stream pending flush (~577): replace `_norm_sentence(pending_text) != last_flushed_sentence` with membership in `window` (+ same guard: if it would be dropped and `not spoken_any`, emit).
5. Updates carry (~593): `"tts_last_sentence": last_flushed_sentence` → `"tts_sentence_window": window`.
6. Per-turn reset (~828): `"tts_last_sentence": ""` → `"tts_sentence_window": []`.
Verification: `grep -n "tts_sentence_window\|tts_dedupe_window" diallux/graph/builder.py diallux/config.py` shows all 6 touch points; no remaining reference to `tts_last_sentence` anywhere (`grep -rn tts_last_sentence diallux/` → empty).
Dependencies: T0.

### T2 — Unit tests
Goal: prove the window catches blocks, over-drops nothing, resets per turn, carries across rounds, and guards silence.
Files: `/tmp/opencode/wt-iter42/tests/test_dedupe_window.py` (NEW; follow the existing T1 dedupe test style in `tests/test_units.py` if one exists — grep `dedupe` in tests/ first and extend rather than duplicate if a harness helper is reusable).
Cases (all via the same token-emulation path the T1 tests use — feed tts-boundary token streams through the turn builder or extract the dedupe helper if trivially callable):
1. `A,A` → second A dropped (regression: old behavior preserved).
2. `A,B,A,B` → second A and second B dropped; spoken = `A,B` (THE fix).
3. `A,B,C,A,B,C` → spoken = `A,B,C`.
4. Distinct sentences `A,B,C,D,E,F,G` → all 7 spoken (no over-drop; window trim works).
5. Same sentence in TWO DIFFERENT turns → both spoken (per-turn reset intact).
6. Cross-round carry: round 1 of a turn speaks `A`; round 2 (after tool calls) repeats `A` → dropped; and a round whose only sentence is a dup with `turn_spoke=False` seeded → spoken anyway (silence guard).
Verification: `cd /tmp/opencode/wt-iter42 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests/test_dedupe_window.py -q` → 6 passed; full suite → 205 passed (199 + 6).
Dependencies: T1.

### T3 — Battery LOW (13 personas, gpt-5.4, config-default low) + digest
Goal: no behavioral regression; Sofia's t1 double gone from the SPOKEN stream.
Commands:
```bash
cd /tmp/opencode/wt-iter42 && set -a && . ./.env && set +a && \
for p in Maria Susan Danny Marcus Carlos Pedro Sofia Jorge Daniel Brenda Gene Frank Ray; do \
  setsid nohup /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python \
    tests/llm2llm/harness.py --personas $p --rag --langfuse --max-turns 28 \
    > /tmp/opencode/iter42_low_$p.log 2>&1 < /dev/null & done; disown -a
# poll: grep -lE "ALL PASS|FAILURES PRESENT" /tmp/opencode/iter42_low_*.log | wc -l  → 13, then ps -ef | grep -c "[h]arness.py" → 0
# stage: copy each persona's json matched to its stdout-log mtime (min |Δ|; proven matcher) into /tmp/opencode/sop_batch_w42_low/tests/llm2llm/json_logs/
#   and cp /home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/diallux-langgraph-production-v5/scripts/call.py into /tmp/opencode/sop_batch_w42_low/scripts/
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python /tmp/opencode/sop_batch_w42_low/scripts/call.py digest --hours 12 --out /tmp/opencode/iter42_low_sop_digest.txt
rm /tmp/opencode/sop_batch_w42_low/scripts/call.py
```
Verification: ≥12/13 `ALL PASS` (Pedro may fail — known); digest Sofia transcript t1 shows the ad-acknowledgement block **once**; NO call has an agent turn that is empty where the pre-fix run had speech (spot-check: every turn line with `T:` also has `A:` text or is a known tool-only round); harness PASS count not worse than baseline.
Dependencies: T2.

### T4 — Battery MEDIUM (13 personas) + digest
Goal: Carlos t1 and Jorge t2 doubles gone; MED baseline held.
Commands: identical to T3 with `export OPENAI_VERBOSITY=medium OPENAI_REASONING_EFFORT=none` before the loop, log tag `iter42_med_$p.log`, staging dir `/tmp/opencode/sop_batch_w42_med/`, digest out `/tmp/opencode/iter42_med_sop_digest.txt`.
Verification: ≥11/13 `ALL PASS` (Pedro + Brenda may fail — known); digest Carlos t1 and Jorge t2 show their blocks **once**; Sofia MED doubles gone; PASS count not worse than 11/13 baseline.
Dependencies: T3.

### T5 — Report + commits + ASK
Goal: evidence on the branch, plan on main, owner gate.
Commands:
```bash
cd /tmp/opencode/wt-iter42 && git add diallux/config.py diallux/graph/builder.py tests/test_dedupe_window.py && git commit -m "iter42: TTS dedupe sliding window (6 sentences) — kills multi-sentence double-speak"
cd /home/julio/projects/clean_diallux_SDR && git add plans/plan_iter42_dedupe_window.md && git commit -m "plan: iter42 dedupe sliding window" && git push
```
Write `research/surgeon/iter42-dedupe-window/01_dedupe_window_report.md`: before/after digest quotes (Sofia/Carlos/Jorge), suite counts, battery PASS tables, any regression.
Verification: branch commit exists; plan on main; **then STOP and ASK JULIO** before any merge (LAW 0).
Dependencies: T3, T4.

## Validation Plan (end-to-end)
1. T0: HEAD `65d7f3b`, suite 199.
2. T1: 6 touch points converted; zero `tts_last_sentence` references remain.
3. T2: 6 new tests pass; suite 205.
4. T3: LOW ≥12/13; Sofia t1 single-spoken in digest.
5. T4: MED ≥11/13; Carlos/Jorge/Sofia singles in digest.
6. T5: report + commits; ASK JULIO.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Cross-turn dedupe (farewells, Ray/Gene) | Not a bug — caller-driven; owner verdict |
| R5.5 exemption list in the SOP digest (ceremony/identity lines) | SOP-doc change; separate owner-gated edit to `full_call_analysys.md` |
| luna booking-completion loop / latency | luna dropped (iter41c evidence) |
| Live (real-calendar) happy-path + T8 A/B on :8007 | Owner-gated, unchanged from iter41 plan |
| Pedro over-book retrain | Pre-existing, iter43 candidate |

Plan file: `/home/julio/projects/clean_diallux_SDR/plans/plan_iter42_dedupe_window.md`