# V7.9_slot_lock — deploy lineage (new account, 2026-09-03)

| # | Folder | chat_agent_id | llm_id | Delta | Status |
|---|--------|---------------|--------|-------|--------|
| 04 | 04_slot_lock_CURRENT_cd0464dd | agent_f305981ef7b5ce312c1c899bbf | llm_cd0464ddca4fa415cc7190cb7f7b | slot-lock booking: native book_appointment_cal → custom create_livecall_booking (/book-livecall); check_availability freeze-2-offer (reservations); extract_booking_intent enum gate (reschedule/cancel); Booking.md minimal delta; ConfirmSlots prompt UNTOUCHED | CURRENT |

Lineage carried from V7.8_reach_details/versions/ (same account):
- 01_baseline_e618dd12 — agent_e99648268be5045d8a49cc9e4e / llm_e618dd126405566695cb511267bc (superseded)
- 02_endcall_rule_REJECTED_2987eab9 — agent_49906d46aa0d1c3f3a524ab5f1 / llm_2987eab94087b3058ec5eb09bf0b (REJECTED, do not reuse)
- 03_bold_constraint_CURRENT_f402d94d — agent_da3959eac4b5f16ee40bbda233 / llm_f402d94db1842e53988b4839cd34 (superseded by 04)

Doctrine honored: new LLM + new chat agent per deploy (never patched), KBs reused via registry, no deletions — orphaned agents kept alive as rollback.
Rollback: redeploy snapshot from versions/03_bold_constraint_CURRENT_f402d94d/ (V7.8 folder) — check_availability legacy mode keeps old agents working.
