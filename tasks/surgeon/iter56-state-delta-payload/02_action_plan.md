# 02 — ACTION PLAN: the iter56 fix (state→delta, {{var}} strip, full history)

Procedure: `iter56-state-delta-payload`. Target branch:
`engine/iter56-state-delta-payload` cut from `engine/iter55-tts-era-turn1-ammo` @ `7ac9879`.
Target layout (owner mandate + T2 anatomy + T0 verdict):

```
BEFORE (@ 7ac9879)                          AFTER (iter56)
[tools]                                     [tools]
[system: head ({{var}} LITERAL)]            [system: head ({{var}} STRIPPED → stable anchor text)]
[system: state-block (mutates/turn)]        [history: FULL, append-only, no window]
[history: 16/8 window (slides)]             [system: DELTA = state-block (live dvs, fresh/turn)
[system: delta = RAG | ack directive]                  + pinned-KB + fresh RAG
                                                       + ack speech-only directive when needed]
```

Everything mutable rides the delta (re-bills anyway). The prefix becomes
truly append-only → cache_read climbs with history like the deployed agent.

## C1 — Config knobs (config.py)

```python
# iter56: state-block relocation — the volatile dvs block moves from the
# pre-history tail to the post-history delta (last message the model reads).
state_in_delta: bool = True          # False = iter55 layout (revert switch)
# iter56: strip literal {{var}} tokens from the static head — dead anchors
# become "CURRENT CALL STATE" pointers (byte-stable, no dvs in the head).
head_strip_vars: bool = True         # False = literal {{var}} (revert switch)
# iter56: full append-only history (deployed parity). 0 = no trim.
history_window: int = 0              # was 16 (config.py:60) — revert = 16
```
`history_trim_step` stays (inert at window=0). `tail_before_history` stays
(inert: the tail becomes empty in live mode).

## C2 — builder.py changes

### C2.1 Head strip (F-02) — inside `static_head` (builder.py:1292-1324)
After composing the head bytes, when `head_strip_vars`:
```python
import re
_VAR = re.compile(r"\{\{\s*[a-z_][a-z0-9_]*\s*\}\}")
head = _VAR.sub("CURRENT CALL STATE", head)
```
- Applied at head-BUILD time → result still cached per `(state, expand_kb)`,
  still byte-stable across rounds AND calls (no dvs involved).
- Effect: "`{{callback_number}}` may already hold the number…" reads
  "CURRENT CALL STATE may already hold the number they're calling from —
  never ask for it if it exists" → the pointer resolves to the delta block
  that ALWAYS carries the live value. Kills PT-53's blindness.

### C2.2 State-block → delta (F-01) — state_node tail composition (builder.py:1466-1471)
```python
# iter56: the state-block rides the DELTA (post-history) — live values
# re-render every round at the position that re-bills anyway. The prefix
# [tools][head][history] stays append-only; cache climbs with history.
if runtime.settings.state_in_delta:
    tail = ""
    state_delta_block = runtime._state_block(dvs)   # fresh EVERY round
else:
    tail = (state.get("frozen_state_block") if … else runtime._state_block(dvs))
    state_delta_block = ""
```
- `state_delta_block` joins `rag_delta` at the final assembly
  (builder.py:1760-1790): delta = `state_delta_block + rag_delta` (state
  FIRST, RAG after — state is the anchor the model must read last… actually
  FIRST in the delta so RAG tails it; both are last-message, ordering within
  the delta is cosmetic; keep state first for anchor prominence).
- **Ack rounds (F-09)**: delta = `state_delta_block + "\n\n" + speech_only_directive`
  (replaces the current directive-only delta at builder.py:1786-1790).
- **Lite round (turn 1)**: unchanged — no state prompt, no delta (guard
  stays `== 1` exactly).
- `_state_block` itself (builder.py:1326-1341): UNCHANGED content
  (`# CURRENT CALL STATE (live values)`), new placement only.

### C2.3 Full history (F-03)
`history_window=0` already short-circuits `_history_window` to `list(history)`
(builder.py:1352-1353: `if n <= 0 or len(history) <= n: return list(history)`).
**Zero code change** — default flip only. Context ceiling: a 60-round call ×
~2 events/round ≈ 130 messages ≈ ~10-15k history tokens on top of ~3.7k
tools+head — well inside model context; prefill covered by the cache after
the first send.

### C2.4 Retire the freeze machinery (F-04) — inert, not deleted
When `state_in_delta=True`: `ingest`'s `frozen_state_block` write
(builder.py:2187-2192) becomes dead (nothing reads it in the new path).
Keep the code behind the flag for revert; add one comment line marking it
inert under `state_in_delta`.

### C2.5 Warm machine (F-05) — one edit point, no structural change
PREFLIGHT-VERIFIED (CR-4): `_warm` composes its OWN tail at builder.py:476-499
— `tail = self._state_block(dvs)` under `prewarm_byte_exact` (line 477-478).
Required edit:
```python
tail = ""
if self.settings.prewarm_byte_exact and not self.settings.state_in_delta:
    tail = self._state_block(dvs)
    …  # staged-RAG branch unchanged (revert mode only)
```
Under `state_in_delta=True` the warm prefills exactly `[tools][head][history]`
— the new append-only prefix (the delta never rides cache, so warming it is
pointless). Per-state latch + force semantics stay (they now serve cross-call
cold starts and state swaps). **Deeper warm simplification = deferred** (see
04 §Deferred) — iter56 must not stack two variables.

### C2.6 Comment rewrites (F-07)
Update the layout-pinning comments at builder.py:486, 1489-1491, 1712-1745,
1762-1790 to the new truth. Zero behavior.

### C2.7 Span additions (verify with the iter55 instrument)
Add to the existing `rag`/round spans one field: `"state_in_delta": bool`
on the round LLM span (or reuse `warm:{key}` span output). Minimal: extend
the per-round usage log line with `delta_tokens=<len>` so the report can show
delta size distribution. (No new span machinery — piggyback.)

## C3 — Tests

1. Enumerate pins: `grep -rn "CURRENT CALL STATE\|tail_before_history\|state_block\|history_window" engine/tests` → every hit reviewed.
2. Layout test: assert message order for a heavy round under
   `state_in_delta=True` = `[head][history...][delta]` with delta containing
   `# CURRENT CALL STATE` + RAG; under `False` = old order (revert test).
3. Head-strip test: `static_head("Intake")` contains ZERO `{{` when
   `head_strip_vars=True`; contains them when False.
4. Window test: `history_window=0` returns full history (already covered by
   the `n<=0` short-circuit — add explicit pin).
5. Ack test: entry-lite delta = state-block + speech directive.
6. Warm parity test: warm payload shape == hot-path shape under the new
   layout (the existing "identical bytes for identical inputs" composer test
   extended to the delta pieces).
7. Suite must stay green: expect **346 passed** (updated pins count as the
   same tests, edited — not added).

## C4 — Verification battery (the proof)

1. **Cache gate (THE gate)**: run 2 chat harness personas (Maria + Susan) +
   1 voice browser-mic call; import to ledger; **cache_read must climb
   monotonically with history within a state** (sawtooth GONE; floor only at
   genuine cold/turn-1). Named SQL gate: `cache_climb` = per-call rounds
   where `cache_read < previous_round AND state unchanged` → expect 0
   (window-jump allowance removed since window=0).
2. **TTFT gate**: ledger TTFT p50/p90 per round class within iter55 bands
   (heavy p50 ≤ ~888 ms observed; hard gates: first 3-4 ≤900, worst ≤1,100).
3. **Fidelity gate**: question-redundancy per chat run ≤ deployed baseline
   (0 re-asks of extracted facts; PT-53 regression check on Intake flow —
   the 7-variant loop must not reproduce).
4. **No literal {{var}}** in any rendered prompt: grep the Langfuse
   generation inputs for `{{` → 0 hits (head) post-fix.
5. Happy-path gate first (`--no-happy-gate` never default). Cancel ALL test
   bookings after battery (Cal.com event 3801235 is REAL).
6. Report → `research/surgeon/iter56-state-delta-payload/01_report.md` +
   ITERATIONS.md ledger line + PT-53/PT-55 flips. ASK Julio (LAW 0).

## C5 — Execution order (commits)

| Commit | Content | Suite after |
|---|---|---|
| 0 | surgeon package (this folder) rides the branch | 346 |
| 1 | C1 knobs + C2.1 head strip + C2.2/C2.3 state→delta + window=0 + C2.4 inert-mark + C2.6 comments + C3 test updates | 346 |
| 2 | C2.7 span/usage-log fields | 346 |
| 3 | battery + ledger import + report (evidence commits, no code) | 346 |

Commit 1 is intentionally ONE variable (the payload relocation) despite
touching three knobs — they are one architectural change with three revert
switches, matching the owner mandate. If the owner wants them split, C2.1
(head strip) can ride its own commit with zero interaction (it only rewrites
head bytes).

## Rollback matrix

| Symptom | Switch | Revert |
|---|---|---|
| Cache still floors | any | `STATE_IN_DELTA=false` |
| {{var}} strip degrades prompts | `head_strip_vars` | `HEAD_STRIP_VARS=false` |
| Context growth concern | `history_window` | `HISTORY_WINDOW=16` |
| All at once | — | `git revert` commit 1 |
