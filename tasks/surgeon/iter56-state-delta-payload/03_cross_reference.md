# 03 — CROSS-REFERENCE: audit (01) vs action plan (02)

Procedure: `iter56-state-delta-payload`. Question: does the plan address every
finding? Does the audit support every change? Contradictions found are
resolved here or escalated to the master plan.

## Findings → fixes coverage

| Audit finding | Plan fix | Covered? |
|---|---|---|
| F-01 state-block busts prefix | C2.2 → delta | ✅ |
| F-02 {{var}} literal blindness | C2.1 strip | ✅ |
| F-03 16/8 window slides + context loss | C2.3 window=0 | ✅ |
| F-04 freeze machinery dead weight | C2.4 inert-mark (deferred removal) | ✅ (defer noted) |
| F-05 warm semantics | C2.5 no structural change, deferred | ✅ (defer noted) |
| F-06 non-live RAG tail inconsistency | — | ⚠️ CR-1 |
| F-07 stale layout comments | C2.6 | ✅ |
| F-08 test pins | C3 | ✅ |
| F-09 ack delta composition | C2.2 ack bullet | ✅ |

## Audit support for each change

| Plan change | Audit basis | Supported? |
|---|---|---|
| state→delta | A3 (mutation), A5 (delta slot proven), T0 verdict, T2 anatomy | ✅ |
| head strip | A2 (literal tokens), T2 §3b (deployed substitutes values) | ✅ |
| window=0 | A4 + T2 §3d (deployed full history) | ✅ |
| warm untouched | A6 (inherits layout via composer) | ✅ |
| tools untouched | A7 + constraint C4 (FIND-5 quirk) | ✅ |
| lite round untouched | A8 | ✅ |

## Contradictions / gaps found and resolution

**CR-1 — Non-live RAG path (F-06) still appends `_frozen_rag_tail` to the
tail.** With `state_in_delta=True` the tail is empty in live mode, but the
revert mode (`rag_live_retrieve=False`) composes `tail = state-block +
frozen RAG`. RESOLVED: out of scope. Live mode is the deployed default
(iter49); the revert path keeps the old layout by design (it IS the revert).
Documented in 02 §C2.2 — no code change. The `state_in_delta` flag composes
ONLY with live mode; if both revert flags are set, `state_in_delta` wins for
the state-block and the RAG tail still rides pre-history — acceptable for a
revert-only path, noted in master plan open-items table as "documented
behavior, not a bug".

**CR-2 — Delta ordering: state-block vs RAG vs ack directive.** 02 says
"state FIRST, RAG after" but also claims iter32 recency wants state LAST-read.
Contradiction is cosmetic (all inside the last system message) but must be
pinned. RESOLVED: fixed order = `state-block → RAG/pinned → ack directive`.
Rationale: the directive must be the FINAL instruction (it's an imperative);
state anchors before RAG keeps values adjacent to the anchor pointer in the
head ("CURRENT CALL STATE"). Master plan pins this order in the layout spec.

**CR-3 — `frozen_state_block` reads in state_node (1466-1471) reference
`state.get("frozen_state_block")` written by ingest (2187-2192).** Under
`state_in_delta` the read path is bypassed but the write still fires every
turn (harmless dict write). RESOLVED: C2.4 marks inert; optionally gate the
write with `and not state_in_delta` — one-line, included in C2.4.

**CR-4 — Warm payload parity under the new layout.** `_warm` builds
head/tail/history from CURRENT dvs — after C2.2 the warm's tail must also be
empty (or it warms the WRONG shape and the latch poisons the round).
Verified in audit A6 that `_warm` routes through the same composition
helpers; the plan's C3.6 warm-parity test pins it. If `_warm` has its own
tail composition copy (builder.py:399-469), it must take the same
`state_in_delta` branch. **Escalated to master plan preflight: verify
builder.py:399-469 tail composition follows the flag.**

**CR-5 — `first_turn_lite` + `state_in_delta` interaction.** Lite round
carries no state-block today and none after the fix — but the LITE WARM
(`lite:<state>`) warms the lite shape; the HEAVY warm warms the heavy shape.
Under the new layout the heavy warm's shape = `[tools][head][history]` —
correct. No interaction. Closed.

**CR-6 — "One variable" rule vs three knobs (C5).** The iteration SOP says
ONE variable. The plan argues the three knobs are one architectural change.
Owner directive ("delta must always contain main plus state" — mandate)
supports treating relocation as the single variable; head-strip is arguably
a second variable. RESOLVED: master plan offers the split (Commit 1a
relocation, 1b head-strip) as the default sequence — battery runs ONCE after
both, gates attribute failures via the rollback matrix (each knob has an
independent revert).

**CR-7 — Tests count.** 02 says "expect 346" but C3 adds new asserts
(layout pins, head-strip, warm parity). Edited tests keep the count; NEW
tests would raise it. RESOLVED: extend existing pin tests, don't add files;
if new tests are cleaner, the master plan's suite gate becomes
"≥346, zero failures" and the count is recorded at execution.

**CR-8 — History context ceiling for stress personas.** 60-round cap × full
history ≈ 15k tokens; Larry (assassin, gated) and stress personas can run
48+ turns. gpt-5.x context is ample; COST grows (uncached first-send per
round ~200 tokens × rounds — trivial). Closed; recorded in report template.

## Verdict

No unresolved contradictions. Two preflight items for the master plan:
(P1) `_warm` tail composition must follow `state_in_delta` (CR-4);
(P2) delta ordering pinned: state → RAG → directive (CR-2).
