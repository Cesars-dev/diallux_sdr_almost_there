# 04 — MASTER PLAN: iter56 state→delta payload relocation (AIRTAIGHT)

Procedure: `iter56-state-delta-payload`. Status: **READY FOR OWNER APPROVAL —
no code touched.** Branch to cut: `engine/iter56-state-delta-payload` from
`engine/iter55-tts-era-turn1-ammo` @ `7ac9879` (carries the iter55 C1
observability instrument — the before/after proof tool).

Preflight items from 03_cross_reference — RESOLVED:
- **P1 (CR-4)**: `_warm` tail composition verified at builder.py:476-499;
  edit point added to 02 §C2.5. The warm inherits the new prefix shape.
- **P2 (CR-2)**: delta order pinned: **state-block → RAG/pinned → ack
  directive** (directive is imperative = final; state anchors before RAG).

## The change (one architectural variable, three revert switches)

```
AFTER (iter56 target layout — every round):
[tools]                                            byte-stable, cached
[system: head, {{var}} → "CURRENT CALL STATE"]     byte-stable, cached
[history: FULL, append-only, no window]            cache climbs with history
[system: DELTA = # CURRENT CALL STATE (live dvs)   re-bills ~400-700 tok/round
                 + pinned-KB + fresh RAG
                 + ack speech-only directive (ack rounds only)]
```

| Knob (config.py) | New default | Revert |
|---|---|---|
| `state_in_delta` | `True` | `False` = iter55 layout |
| `head_strip_vars` | `True` | `False` = literal `{{var}}` |
| `history_window` | `0` (full) | `16` = old window |

## Execution sequence

| Step | What | Files | Verify | Suite |
|---|---|---|---|---|
| **C0** | Cut branch + worktree; commit surgeon package (this folder) | `tasks/surgeon/iter56-state-delta-payload/` rides the branch | `git log` = `7ac9879` + C0; worktree venv+env symlinks per iter55 protocol | 346 |
| **C1a** | Relocation: `state_in_delta` knob + state_node tail→delta (builder.py:1466-1471, 1760-1790) + ack delta composition (1786-1790) + `_warm` tail gate (477) + ingest freeze inert-gate (2187-2192) + `history_window=0` default + comment rewrites (486, 1489, 1712-1745) + test pin updates | builder.py, config.py, engine/tests | layout test: heavy round = `[head][history][delta(state+rag)]`; revert test old order | 346 |
| **C1b** | Head strip: `head_strip_vars` knob + `_VAR.sub` in `static_head` (builder.py:1292-1324) + tests | builder.py, config.py, engine/tests | head contains zero `{{` when on; contains them when off | 346 |
| **C2** | Span/log fields: `state_in_delta` on round spans + `delta_tokens` on the round usage log line | builder.py, llm.py | one chat run shows the fields in Langfuse | 346 |
| **C3** | **Battery + proof**: happy-path gate first → 2 chat personas (Maria, Susan) + 1 browser-mic voice call → ledger import → gates → report `research/surgeon/iter56-state-delta-payload/01_report.md` → ITERATIONS.md line → PT-53/PT-55 flips → **ASK JULIO** (LAW 0) | evidence only | gates below | 346 |

Order rationale: C1a and C1b are separable commits but ONE battery (CR-6):
the rollback matrix attributes any failure to a single knob without re-running
the code phase.

## Gates (named, SQL/Langfuse — never "feels okay")

| Gate | Query/Check | PASS |
|---|---|---|
| **G1 cache_climb** | per call: rounds where `cache_read` DECREASES while state unchanged | **0** (window jumps eliminated; only genuine cold/turn-1 may floor) |
| **G2 cache_growth** | `cache_read` at last round of each call vs first | last ≥ first + 1,000 (history riding) |
| **G3 ttft_band** | ledger TTFT p50/p90 per round class | p50 ≤ 900 ms; worst ≤ 1,100 ms (owner gates); no regression vs iter55 bands (heavy p50 888) |
| **G4 no_literal_var** | Langfuse generation inputs contain `{{` in the head | **0 hits** |
| **G5 fidelity** | re-asks of extracted facts per chat run (PT-53 check) | 0 on Maria/Susan runs |
| **G6 suite** | `pytest tests -o addopts="" -q` | 346 passed, 0 failed |

Post-battery: **cancel ALL test bookings** (Cal.com event 3801235 is REAL).

## iter55 BREADCRUMB (do not lose this)

**iter55 is PAUSED at C1 (`7ac9879`), NOT dead. Its leftovers — C2 (lite-cap
split) and T1–T7 (warm p90 table, turn-1 ammo, filler, battery, report) —
will be RE-TAKEN after iter56 lands, re-scoped onto the fixed payload:**

1. T1 (warm-completion p90 table) — the warm machine now serves cross-call
   cold starts only; the table's meaning changes (measure the NEW warm's
   registration time; the F-07 lite-twin split may shrink or vanish).
2. T2/T3 (turn-1 ammo-locked probe + cap sweep) — turn-1 lite shape is
   UNCHANGED by iter56 (no state-block there anyway) — tasks survive as-is.
3. O5 greeting runway, filler fallback — unchanged, voice-path work.
4. The iter55 plan's cache-floor assumptions (floors 2688/3712) are OBSOLETE
   post-iter56 — its report must re-baseline from the new cache_climb data.
5. Sequence: iter56 branch merges (owner say-so) → iter55 resumes FROM its
   branch or a fresh cut on top of main — owner's call at that gate.

## Deferred (NOT in iter56)

| Item | Why |
|---|---|
| Warm machine simplification (latch/force/lite-twin rework) | One variable per iteration; iter56 changes the payload the warm warms — simplify after the new shape is proven |
| `frozen_state_block` / non-live RAG tail code DELETION | Revert paths stay; delete only after a merged iteration proves the new layout in production |
| Retell-side {{dv}} substitution parity in head | Superseded: head stays byte-stable, values ride the delta — BETTER than Retell's mid-state system mutation (T2 §3a) |
| Heating-UK line | Different agent, out of scope |

## Open items — NONE

All audit findings have fixes (03 §coverage table); both preflight items
resolved against code (P1: builder.py:476-499 verified; P2: order pinned).
This plan is airtight per the Surgeon Framework. **Awaiting owner approval.**
