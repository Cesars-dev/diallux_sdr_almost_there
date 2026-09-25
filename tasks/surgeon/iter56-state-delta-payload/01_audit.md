# 01 — AUDIT: engine payload truth @ `engine/iter55-tts-era-turn1-ammo` `7ac9879`

Procedure: `iter56-state-delta-payload`. Audited in the worktree
`/tmp/opencode/wt-iter55` (latest engine code = iter55 C1, suite 346 green).
Deployed-side ground truth: `research/surgeon/retell-payload-truth/02_payload_anatomy.md` (T2).
Evidence for observed behavior: `T0_session_verdict.md` (both parts).

## A. What EXISTS (verified, line numbers @ 7ac9879)

### A1. Round composer — `_build_messages` (builder.py:747-765)
Layout today (`tail_before_history=True`, config.py:154):
```
[tools (request field)]
[system: head        = static_head(state)          ← byte-stable, dvs={}]
[system: tail        = state-block (+frozen RAG in non-live mode)]
[history: 16/8 hysteretic window]
[system: delta       = live RAG (live mode) | drift chunks | ack speech-only directive]
```
The composer itself is layout-agnostic — it takes `(system, tail, delta)` and
places them. **The placement DECISION lives in `state_node`** (A3/A5).

### A2. Static head — `static_head` (builder.py:1292-1324)
- Byte-stable per `(state_name, expand_kb)`, cached in `_head_cache`.
- **`dvs={}` on purpose** — `{{var}}` tokens stay LITERAL in the head. The
  model reads e.g. "`{{callback_number}}` may already hold the number they're
  calling from" as a dead placeholder (T0 Part 2 smoking gun, PT-53).
- VOICE_OUTPUT_RULES fold into the head (static bytes).

### A3. State-block — `_state_block` (builder.py:1326-1341) + freeze
- Renders `# CURRENT CALL STATE (live values)` from flat dvs.
- **Pre-history placement** (rides `tail` before history via A1).
- **Re-frozen EVERY TURN at ingest** (builder.py:2187-2192,
  `frozen_state_block`): "Refresh happens at the NEXT turn's ingest." In
  capture states an extract tool lands nearly every turn → the tail bytes
  mutate at a fixed early position → **everything after `[tools][head]`
  re-bills** (cache floor per state: 2688 Intake / 3712 Discovery-Closer —
  T0 Part 1, 86 round-usage lines + ledger happy-d/happy-plumber-b + iter44 report).

### A4. History window — `_history_window` (builder.py:1345-1359)
`history_window=16`, `history_trim_step=8` (config.py:60,65). Window start
jumps every 8 messages → first history message changes → second cache bust
(the 3712↔2688 sawtooth inside a state). Deployed Retell sends FULL history
(T2 §3d: 113-133 events, never trimmed).

### A5. Delta assembly — state_node (builder.py:1478-1514 live RAG; 1760-1790 final)
- Live mode: `live_delta` = fresh multi-lane retrieval + pinned section,
  REPLACES the post-history delta each round (iter49 T4).
- Entry-ack (`entry_lite`): delta = speech-only directive (builder.py:1786-1790).
- `messages = self._build_messages(state_name, history, tail, system,
  delta=rag_delta)` (builder.py:1790).
- **The delta slot is proven technology**: RAG, pinned-KB, and ack directives
  already ride it. The state-block is the ONE volatile block still parked in
  the prefix.

### A6. Warm machine (builder.py:362-469 + llm.py:234-244)
- `warm_prompt_cache(state, history, dvs, lite, force)` → `_warm` →
  `StreamingLLM.warm` (16-token cap; iter55 C1 added `warm:{key}` spans,
  un-swallowed exceptions, `_await_warm` outcomes).
- Latch once per state per call; `force=True` re-fires post-execute.
- The warm composes via the same `_build_messages` → **it inherits the
  layout change automatically** (verified: `_warm` builds the same
  head/tail/history pieces — builder.py:399-469).
- Warm exists to compensate for the A3/A4 busts. With an append-only prefix
  its job shrinks to cross-call cold starts.

### A7. Tools channel (builder.py:1712-1745)
- Tools are dvs-FREE, cached per `(state, expand_kb)`, byte-identical across
  ack/heavy/warm rounds (FIND-5 port). **Unaffected by the fix.**

### A8. first_turn_lite (builder.py:1383+)
- Turn 1 = general_prompt + VOICE_OUTPUT_RULES + ONE noop tool (iter48b
  FIND-5: gpt-5.4 only caches requests WITH tools). No state prompt, no tail,
  no RAG. **Unaffected by the fix** (no state-block in the lite shape anyway).

### A9. Observability (iter55 C1, @ 7ac9879 — the instrument)
- `warm:{key}` spans (fired_at/ms/outcome/degraded/error), `_await_warm`
  outcomes, greeting spans, `rag` spans, per-round `round usage` logging
  (cache_read visible per round), Langfuse traces. **This is what will prove
  the iter56 fix** (cache_read must climb with history instead of flooring).

## B. What's MISSING / BROKEN (findings)

| ID | Finding | Evidence |
|---|---|---|
| F-01 | **State-block in prefix position mutates every turn** → cache dies at `[tools][head]` floor; history never rides. Median waste ~1,000-1,500 uncached tok/round; ~60-90k/call; ~150-400 ms extra prefill/round. | A3 + T0 Part 1 (three independent sources) |
| F-02 | **`{{var}}` literal in the head** → the model can't see "step done" anchors → walks Intake.md's scripted questions (7 verbatim variants observed live). | A2 + T0 Part 2 + 02_payload_anatomy.md §3b |
| F-03 | **16/8 window slides** → second cache bust + the model LOSES old context the deployed agent keeps (full history). | A4 + T2 §3d |
| F-04 | **`frozen_state_block` machinery is complexity in service of the bust** (freeze per turn, refresh at next ingest) — becomes dead weight once the state-block moves to the delta. | builder.py:2187-2192, 1466-1471 |
| F-05 | Warm machine's per-state latch/force dance exists to re-prime after busts it causes indirectly — semantics need revisit (NOT removal: cross-call cold starts remain). | A6 |
| F-06 | Non-live RAG path still appends `_frozen_rag_tail` to the TAIL (pre-history) — inconsistent with live mode; only matters if `rag_live_retrieve=False` (revert switch). | builder.py:1668-1680 |
| F-07 | Comments/docstrings across builder.py pin the OLD layout ("EXACTLY [tools][head][state-block][history]", "would bust the state-block out of the prefix") — must be rewritten or they'll mislead the next agent. | builder.py:486, 1489, 1712-1745, 1762-1790 |
| F-08 | Tests pin layout: suite asserts `[head][tail][history]` order and state-block content placement (exact test list in 02_action_plan §C3 — to be enumerated by `grep -rn "CURRENT CALL STATE\|tail_before_history\|state_block" engine/tests`). | suite @ 346 |
| F-09 | The entry-ack directive currently OWNS the delta slot on ack rounds (builder.py:1786-1790) — after the move, the ack delta must compose state-block + directive together (ordering decision needed). | A5 |

## C. Risks / constraints (do not violate)

1. **LAW 0**: code changes ride a NEW branch `engine/iter56-state-delta-payload`
   cut from `engine/iter55-tts-era-turn1-ammo` @ `7ac9879`. No merges without
   owner say-so.
2. **One flag rollback**: every layout change behind a settings knob
   (`state_in_delta`, `head_strip_vars`, `history_window=0` is already a knob)
   — defaults flipped, revert = env/one-line.
3. **Voice TTFT gates stand**: first 3-4 interactions ≤900 ms; worst ≤1,100 /
   user-hears ≤1,400 (owner, iter55). The fix should REDUCE prefill; verify no
   regression via T0 spans + ledger.
4. **gpt-5.4 tools-cache quirk** (iter48b FIND-5): every cached round must
   keep the full tools array — the fix does not touch the tools channel.
5. **iter32 recency finding**: state must be the LAST thing the model reads —
   the delta IS the last message → the move PRESERVES this (improves it: dvs
   become fresher, re-rendered every round instead of frozen per turn).
6. **Eval SOP**: battery + SQLite ledger import + gates named SQL, no "feels
   okay". Happy-path gate first. Cancel test bookings after battery.
