# PLAN — v5 iter49f: T6 lite-entry CACHE FIX (dummy tool on the ack + entry-shaped warm)

## Meta
- Date: 2026-09-16
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Work queue this fixes (READ FIRST): `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter49e_t4b_report_registry.md` — a VERBATIM copy of `plan_v5_iter49d_t4b_report_registry.md` (same T6/T7/T8/T9). This plan is the FIX for its T6; T7/T8/T9 stay as written there.
- Scope: ONE defect. iter49 T6 (commit `a4b53b3`) shipped the state-entry lite ack with `tools=[]`, so OpenAI structurally never caches it (FIND-5) and the "silent warm + merge" cache design cannot deliver the cached-first-request the owner requires. Bind the dummy `memory_note` tool on the ack and add the entry-shaped silent warm so the ack's cached tokens are actually READ. Nothing else.
- Status: PLAN ONLY (handoff for the next session).
- **Work branch: `engine/iter49c-engine-finish` @ `a4b53b3`** (lineage `fc42a3e` → `94d0082` T1 → `c8dd05a` T4-final → `a4b53b3` T6). Worktree: `/tmp/opencode/wt-iter49`. ALL code edits happen there. NO merge without owner (LAW 0).
- 49-b checkpoint: `engine/iter49-rag-parity` @ `fc42a3e` — frozen, do not advance.
- Environment, traps, deploy rules, and the T1–T5 history are ALL in the work queue plan above and in `plans/plan_v5_iter49c_finish_iter49_engine.md`. This plan does not repeat them.

## Compaction Context (what happened, pinned — do not re-derive)

**Shipped at `a4b53b3` (iter49 T6 / T4b state-entry lite), suite 304 green, gates re-run PASS:**
- `diallux/config.py`: `state_entry_lite: bool = True`, `state_entry_lite_off: str = ""`.
- `diallux/graph/builder.py`: `CallRuntime._prev_round_state` (per-call, reset in `initial_state()`); the `entry_lite` trigger `(not lite) and settings.state_entry_lite and state.turn_index > 1 and state_name != _prev_round_state and state_name not in _entry_lite_off_states()`; `_entry_lite_off_states()`; `_entry_lite_head()`; ack shape `[state head (kb=False)][state-block dvs][history]`; NO RAG lanes; NO `_await_warm`; tracker updated at the end of every non-turn-1-lite round.
- Heavy rounds unchanged: `[tools][head][state-block][history][fresh RAG delta]`; heavy warm prefills exactly the pre-history prefix (pinned); `_await_warm` 500 ms EOT / 100 ms mid-turn.
- 6 new pins in `tests/test_iter49_rag_parity.py` + 3 re-pins (`tests/test_first_turn_lite.py`, 2 in `tests/test_iter44_cache_floor.py`).

**THE FAILURE (owner-identified 2026-09-16 — the reason this plan exists):**
- The ack round carries **`tools=[]`**. FIND-5 (iter48b, OTEL-proven): **gpt-5.4 prompt-caches ONLY tool-bearing requests**; a toolless request is structurally cache-0. Turn 1 was fixed for exactly this by binding `LITE_NOOP_TOOL`; the state-entry ack shipped WITHOUT it → every ack is structurally cache-0 → the intended "silent bg warm + merge → first request cached, heavy round rides the warm, the RAG delta is the only compute" degrades.
- Owner directive (verbatim): **"Lite turns must have a dummy tool"** — so the ack is cache-eligible like turn 1.

**HONEST CACHE MECHANICS (do not overstate):**
- OpenAI prompt cache is **prefix-from-byte-0**; **tools render FIRST**.
  - ack   = `[dummy memory_note][head][state-block][history]`
  - heavy = `[full tools][head][state-block][history][RAG delta]`
  - ⇒ the dummy-tool ack does **NOT** prefix-match the heavy round. The dummy tool makes the ack **cache-ELIGIBLE (a write)**; it only pays off if a request with the ack's exact bytes follows. That reader is the **`entry:<state>` warm this plan adds**. (Same warm→hot pattern as turn 1's `lite:<state>` warm.)
- The heavy round's speed comes from the heavy warm (unchanged). The fresh RAG delta is the SUFFIX that computes — it is NOT cached tokens.

**MEASURED TOKEN FACTS (tiktoken o200k_base — pinned so nobody re-guesses):**
- `diallux/prompts/general_prompt.md` = 6,503 chars ≈ **1,648 tok** with `VOICE_OUTPUT_RULES`; last modified iter21 (`2dc13ff`); byte-identical to `agent/llm.json`'s embedded `general_prompt`; `git diff c40f06b..a4b53b3` on `diallux/prompts/` + `agent/llm.json` = EMPTY (iter49 did not touch prompts).
- Ack head (state kb=False, markers stripped) + state-block: Intake **2,373 tok**, Discovery **2,824**, Closer **2,963**, Closing **2,053**. Turn-1 lite head = **1,648 tok**.
- Intake tools JSON = 2,943 chars ≈ **688 tok** (heavy-only on-wire cost).
- ⇒ parent plans' "~1200-tok ack" estimate is WRONG (head-bound ~2.0–3.0k tok). Recorded; head slimming is DEFERRED.

**Dummy tool definition (do not re-create):** `LITE_NOOP_TOOL` in `/tmp/opencode/wt-iter49/diallux/graph/llm.py:37-46` = `{"type":"function","function":{"name":"memory_note","description":"Internal pacing tool. NEVER call this — always reply in text only.","parameters":{"type":"object","properties":{},"required":[],"additionalProperties":False}}}`. It is already imported in `builder.py` (`from .llm import LITE_NOOP_TOOL, StreamingLLM, build_tool_schemas`).

**Key line numbers at `a4b53b3` (verify by grep — numbers drift):**
- `builder.py`: `warm_prompt_cache` def ~293; `_warm` def ~327; `_entry_lite_off_states` ~581; `_entry_lite_head` ~588; `entry_lite = (` ~1163; `elif entry_lite:` (head) ~1173; `elif entry_lite:` (await) ~1205; `tools = [LITE_NOOP_TOOL]` ~1481; `elif entry_lite:` (tools=[]) ~1482; transition warm `warm_prompt_cache(dest` ~1609; post-execute warm `warm_prompt_cache(new_state` ~1723.
- `tests/test_iter49_rag_parity.py`: `test_state_entry_lite_turn2_initial_state_shape` ~579 (ack tools assert ~607); `test_state_entry_lite_transition_ack_then_heavy` ~630; `test_state_entry_lite_opt_out_and_kill_switch` ~676; `test_warm_prefills_rag_free_prefix_equal_heavy_prehistory` ~728; `test_transition_chain_replay_logs_shapes_and_byte_budgets` ~759.
- `tests/test_first_turn_lite.py`: `test_turn2_state_entry_lite_turn3_full_payload` ~66 (ack tools assert ~80).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Lite-entry acks bind `LITE_NOOP_TOOL` (dummy `memory_note`) | FIND-5: gpt-5.4 caches only tool-bearing requests; `tools=[]` = structurally cache-0 (the exact failure iter48b fixed on turn 1). Owner 2026-09-16: "Lite turns must have a dummy tool". |
| An `entry:<state>` silent warm in the ack's EXACT bytes fires at transition detection + post-execute | the ack is one-shot per state visit; a cache write with no reader buys nothing. Turn 1 uses its same-shape `lite:<state>` warm; the entry ack needs its own. The ack still NEVER awaits (T6 rule). |
| The dummy tool is bound unconditionally on entry acks (no new config flag) | mirrors turn-1 `first_turn_lite`; `state_entry_lite=false` remains the whole-feature kill switch. |
| Everything else from T6 is UNCHANGED (head/state-block/history shape, no RAG lanes, no await, `force_speech` exemption, tracker semantics, heavy warm + triggers) | T6 shipped correct except the cache defect; one variable per fix. |
| Code lands on `engine/iter49c-engine-finish`; LAW 0; no merge without owner | git crystal ball v2. |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| None blocking T6-fix. | — |
| Owner go for the LIVE battery (and merge consents) | ASK at the work-queue plan's report step (its T8) |
| Live proof that the ack now reads cached tokens (`cache_read > 0` on the ack round) | LIVE session, not here |

## Environment & Dependencies
- Identical to the work queue plan (`plan_v5_iter49e_t4b_report_registry.md` §Environment): worktree `/tmp/opencode/wt-iter49`, `.venv/bin/python` (never the `pip` script), Postgres `localhost:5434/diallux`, run everything from the worktree.

## Architecture (before → after, the ack round only)
```
BEFORE (a4b53b3 — the defect):
  ack   = [no tools][head][state-block][history]      -> cache-0 (FIND-5)
  warm  = [full tools][head][state-block][history]    -> heavy round only

AFTER (this plan):
  entry warm = [memory_note][head][state-block][history]   <- NEW, silent, lands pre-ack
  ack        = [memory_note][head][state-block][history]   -> READS the entry warm's cache
  heavy warm = [full tools][head][state-block][history]    -> UNCHANGED
  heavy      = [full tools][head][state-block][history][RAG delta]
```
- gate on the entry warm: fire it only when the destination would actually be `entry_lite` (i.e. `settings.state_entry_lite` ON AND `dest not in _entry_lite_off_states()`); opted-out / disabled destinations keep only the heavy warm.

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter49/diallux/graph/builder.py` | T6-fix(a): `tools = []` → `tools = [LITE_NOOP_TOOL]` on the `entry_lite` branch. T6-fix(b): `warm_prompt_cache(..., entry_lite=False)` + `_warm(..., entry_lite=False)` (entry shape, key `entry:<state>`) + fire at both transition sites | Edit |
| `/tmp/opencode/wt-iter49/tests/test_iter49_rag_parity.py` | T6-fix(a): re-pin the 4 ack-tool asserts to `["memory_note"]`. T6-fix(b): new entry-warm byte-equality pin + `entry:`/full coexistence | Edit |
| `/tmp/opencode/wt-iter49/tests/test_first_turn_lite.py` | T6-fix(a): `test_turn2_state_entry_lite_turn3_full_payload` ack assert → `["memory_note"]` | Edit |

## Deploy Rules
- Identical to the work queue plan (commits only on `engine/iter49c-engine-finish`; no merge/push without owner; docs → main; never touch live ports/services; `<venv>/bin/python -m pip` only; keyhound before any push; cancel test bookings after live sessions).

## Tasks

### T6-fix — bind the dummy tool on lite-entry acks + add the entry-shaped silent warm
Goal: every state-entry ack request is tool-bearing (cache-eligible, FIND-5 parity with turn 1) AND an identical-bytes silent warm lands first so the ack actually reads cached tokens. The ack still never awaits.

Files: `/tmp/opencode/wt-iter49/diallux/graph/builder.py`, `/tmp/opencode/wt-iter49/tests/test_iter49_rag_parity.py`, `/tmp/opencode/wt-iter49/tests/test_first_turn_lite.py`.

Procedure:
1. **(a) the dummy tool.** In `state_node`'s tools block, the `elif entry_lite:` branch (grep `elif entry_lite:` near `tools = [LITE_NOOP_TOOL]`, ~line 1482): change `tools = []` → `tools = [LITE_NOOP_TOOL]`. Update the comment: FIND-5 — without a tool the ack is structurally cache-0 (the failure iter48b fixed on turn 1); the tool is a dummy, so the ack still SPEAKS only and extraction/slots still fire on the later heavy rounds. Nothing else in the branch changes.
2. **(a) re-pin the asserts** (the ack now carries exactly ONE dummy tool):
   - `tests/test_iter49_rag_parity.py::test_state_entry_lite_turn2_initial_state_shape` (~line 607): `assert fake.seen_tools[1] == []` → `== ["memory_note"]`.
   - `tests/test_iter49_rag_parity.py::test_state_entry_lite_transition_ack_then_heavy` (~line 630): the ack assert `== []` → `== ["memory_note"]`.
   - `tests/test_iter49_rag_parity.py::test_transition_chain_replay_logs_shapes_and_byte_budgets` (~line 759): shape classifier `"entry-ack" if fake.seen_tools[i] == [] else "heavy"` → `... == ["memory_note"] ...`; the per-ack loop `if fake.seen_tools[i] == []:` → `== ["memory_note"]:`; keep the "no post-history delta" assert.
   - `tests/test_first_turn_lite.py::test_turn2_state_entry_lite_turn3_full_payload` (~line 80): `== []` → `== ["memory_note"]`.
   - `test_state_entry_lite_opt_out_and_kill_switch` (~line 676) is unchanged (it asserts the opted-out ack is HEAVY via truthy tools) — re-read comments only.
3. **(b) the entry warm.** Extend `warm_prompt_cache(self, state_name, history=None, dvs=None, lite=False, force=False, entry_lite=False)`:
   - key = `f"entry:{state_name}"` when `entry_lite` (distinct from `lite:<state>` — the turn-1 lite warm uses the GENERAL head shape; a key collision in `self._prewarmed` would suppress re-fires). Register `self._latest_warm[f"entry:{state_name}"] = task`.
   - keep the latch semantics (`if key in self._prewarmed and not force: return`); callers pass `force=True` so it re-fires on a state revisit.
4. **(b) the entry warm shape.** Extend `_warm(self, state_name, history, dvs=None, lite=False, entry_lite=False)`; when `entry_lite`, build through the SAME composer the hot ack uses so the bytes are identical:
   - `dvs = DynamicVariables.from_flat(dvs or {}).to_flat()` (same normalization as the heavy warm)
   - `system = self._entry_lite_head(state_name, await self._resolve_kb_store())`
   - `tail = self._state_block(dvs)` when `self.settings.prewarm_byte_exact` (the ack renders the frozen-at-ingest state-block from the same dvs; both paths call `_state_block(dvs)` → identical bytes)
   - `messages = self._build_messages(state_name, history, tail, system)` — NO delta
   - `await self.llm.warm(messages, [LITE_NOOP_TOOL])`
   - on failure: reuse the existing lite-shape retry / log — never raise.
5. **(b) fire it.** At BOTH existing transition warm sites (grep `warm_prompt_cache(dest` ~line 1609 and `warm_prompt_cache(new_state` ~line 1723), right next to the heavy warm), add the entry warm **only when the destination would be `entry_lite`**:
   ```python
   dest_entry_lite = (bool(getattr(runtime.settings, "state_entry_lite", False))
                      and new_state not in runtime._entry_lite_off_states())
   if dest_entry_lite:
       runtime.warm_prompt_cache(new_state, list(history) + list(new_history),
                                 dvs=dict(dvs), entry_lite=True, force=True)
   ```
   (the detection-site call uses the same predicate with `list(history)`; use the destination variable in scope — `dest` / `new_state`).
6. **(b) new pins** (`tests/test_iter49_rag_parity.py`):
   - `test_entry_warm_bytes_equal_ack_prehistory`: drive the same transition flow as `test_state_entry_lite_transition_ack_then_heavy` with a `_WarmSpyLLM`; assert the `entry:` warm's `messages` == the ack round's messages (list equality) and its tools == `[LITE_NOOP_TOOL]`; assert the ack round still shows NO `_await_warm` (reuse `_AwaitRecorder`).
   - `test_entry_and_full_warms_coexist`: after a transition, `entry:<state>` and `<state>` both present in `rt._latest_warm` (mirrors the iter48b lite/full coexistence pin).

Verification:
- `.venv/bin/python -m pytest tests -q -p no:warnings` → green, `≥304` after step 2, `≥306` after step 6.
- `.venv/bin/python scripts/iter49_offline_replay.py --smoke` → 7/7 PASS.
- `.venv/bin/python scripts/iter49_offline_replay.py --replay` → GATE PASS (right-vertical 0.788 pooled AND mean, zero-chunk 1/47, chunks/turn 2.17).
- Commit on `engine/iter49c-engine-finish` (long single-paragraph message, repo style), e.g.:
  `iter49 T6-fix: lite-entry acks bind the dummy memory_note tool (FIND-5 cache eligibility — tools=[] made every ack structurally cache-0) + entry:<state> silent warm in the ack's exact bytes (fired at transition detection + post-execute) so the ack READS cached tokens; ack still no-RAG/no-await, heavy warm unchanged; measured ack ~2.0-3.0k tok head-bound (parent plan's ~1200-tok estimate wrong); suite NNN green, smoke 7/7, replay GATE PASS`.

## Validation Plan
1. T6-fix(a) proven by the ack shape pins (exactly `["memory_note"]`) + the chain-test audit.
2. T6-fix(b) proven by the entry-warm byte-equality pin (warm `messages` == ack `messages`; tools == `[LITE_NOOP_TOOL]`) + `entry:`/full coexistence.
3. Both offline gates re-run after the change (smoke 7/7, replay GATE PASS).
4. LIVE proof of the fix (next session, owner-gated): the ack round's `cache_read > 0` (today it is 0), plus the existing floors 2688/3712 and the ack TTFT ≤800ms / first heavy ≤1300ms gates.
5. Then continue with the work queue plan's T7 (cache-floor pins) → T8 (report + ASK, must record this defect + fix) → T9 (registry).

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Head slimming (`general_prompt.md` ~1,648 tok; ack heads ~2.0–3.0k tok) | the ack's real weight is the head; separate plan if the live 800 ms ack gate misses. |
| Full-tools ack variant (ack carries the REAL tool array + speech-only directive → prefix-matches the heavy round) | would let the ack itself seed the heavy round's cache, but costs +0.7–3k tok on the ack and needs the `force_speech` guard; live-measured decision AFTER this fix. |
| Everything else (live battery, US-East migration, deferral lane-A, PT-43/44/48, registry merge) | unchanged — see the work queue plan's Deferred table. |
