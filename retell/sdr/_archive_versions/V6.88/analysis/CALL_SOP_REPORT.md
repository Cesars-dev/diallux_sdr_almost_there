# V6.88 — CALL-ANALYSIS-SOP Report (13/13 calls)
Agent `agent_d355c76e75908afc4e944fb3be` · analyzed 2026-08-24 · framework: docs/Testing_guidelines/CALL-ANALYSIS-SOP.md

## Suite-level verdict
| Category | Verdict |
|---|---|
| 1. Prompt Following | ✅ all states; ritual lines verbatim; no stacked questions |
| 2. Nonsense/Hallucination | ✅ zero JSON/tech leaks; zero invented slots/uids/policies |
| 3. Redundancy | ⚠️ benign: incremental re-captures 2–5× (Discovery/person details); verify_info 2–3× only on repair paths |
| 4. Repetition | ✅ zero sentences repeated ≥3× in any call |
| 5. Bugs | ✅ none new; Pedro's booking_uid='' is correct fail-closed behavior |
| 6. Tool Call Analysis | ✅ canonical order 100% on bookers; extract→flag→transition discipline held |
| 7. Conversation Flow | ✅ one-question pacing; graceful refusals honored instantly |
| 8. Logs & Metrics | see per-call table |

## Per-call

### BOOKERS (7/7 — canonical chain, machine booleans, real UIDs)

| # | Persona | Transitions | Booking | Notes |
|---|---|---|---|---|
| 1 | Maria | 6/6 ✅ | ✅ uid sRftdxao…, verified=true/true | verify_info 1× (clean pass); person_details 3× (incremental) |
| 2 | Danny | 6/6 ✅ | ✅ uid mgJBiCTJ… | cleanest run: verify_info 1× |
| 3 | Susan | 6/6 ✅ | ✅ uid bciDfU8G… | last_name+industry empty by design (optional fields); gate correctly didn't block |
| 4 | Marcus | 6/6 ✅ | ✅ uid ns73NjNc… | query_livecall_slots 2× (second day lookup after choice) — legitimate |
| 5 | Sofia | 6/6 ✅ | ✅ uid r9jPaXoM… | **repair loop live**: verify_info 3× → corrective E.164 upsert via extract_confirm_details → converged without asking caller again |
| 6 | Brenda | 6/6 ✅ | ✅ uid u4bkRJzC… | objection gauntlet absorbed pre-Booking; Phoenix DST conversion intact; repair loop 3× |
| 7 | Gene | 6/6 ✅ | ✅ uid n4wa5G5E… | grumpy pacing handled; verify 3× incl. slot_verified set→re-check cycle |

### NON-BOOKERS (5/5 — correct outcomes)
| # | Persona | Behavior | SOP notes |
|---|---|---|---|
| 8 | Carlos (mean) | exit at Offer after leak math | 15 tools, no begging, single end_call |
| 9 | Pedro (dumb, fictional 555#) | **fail-closed textbook**: create ×2 (retry per prompt) → validate invalid → record_booking_outcome(false, failed=true) → fallback speech → end_call. NEVER claimed success | the deterministic chain's finest hour |
| 10 | Jorge (enquiry) | long discovery (extract_discovery_details 5×), exited without pitch pressure | redundancy is curiosity-driven here, not buggy |
| 11 | Daniel (robot?) | exit at Closer after disclosure | 9 tools total |
| 12 | Frank (hostile) | fastest exit: 4 agent turns, 5 tools, zero defensiveness | composure intact |
| 13 | Ray (wants human) | exit at Discovery, honest AI disclosure | — |

## Deep-dive findings

### D1 — Deterministic chain held under its first real stress distribution
Repair paths (Sofia/Brenda/Gene/Pedro) ran verify_info 2–3× each and **every loop converged below the 10-pass valve** — the valve never fired once across the suite. Suggestion-upsert (Sofia's `5551234567`→`+17135551234`) executed silently from context, caller never re-asked.

### D2 — Redundancy profile is structural, not defective
`extract_discovery_details` 2–5× and `extract_person_details` 2–4× correlate with personas dribbling facts across turns (no-volunteer/dumb/grumpy archetypes). Each re-fire carried NEW fields (verified via dv deltas) — matches the incremental-capture design. Flag level: informational.

### D3 — Empty-string hygiene
`""` appears ONLY in legitimately-optional fields (last_name, industry, closer inputs on early exits) and Pedro's booking_uid (empty seed after calendar rejection — correct). **Zero cases of a populated value being clobbered to "".**

### D4 — Pedro's run, step-by-step (the fail-closed proof)
```
verify_info ×2 (converged: phone normalized to +15551234567) → slot_verified=true
→ transition_to_Booking → create_livecall_booking → Cal.com 400 (invalid NANP area code)
→ retry create → 400 again → record_booking_outcome(booking_verified=false, booking_failed=true)
→ "We're having trouble confirming the calendar…" → end_call. No transition_to_Closing fired.
```
Exactly the owner-specified failure ladder.

### D5 — Metrics
Bookers 15.8–22.3¢ (avg ~19¢); exits 6.7–15.8¢; Pedro 30.1¢ (retry + repair loop premium). Agent-msg counts: bookers 11–16, exits 4–22. No correlation between verbosity and success — flow discipline constant.

## Residual (non-blocking) items
1. `calculate_monthly_leak` fired 2× on Maria — harmless recompute, same result.
2. query_livecall_slots 2× on Marcus — second call was a legitimate different-day lookup.
3. Naming debt: Retell display names still say "Dialux SDR V6.8" for all iterations (cosmetic).
