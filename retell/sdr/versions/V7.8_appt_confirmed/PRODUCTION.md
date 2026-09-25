# V7.7_set_callback_number — PRODUCTION (2026-08-27)

chat_agent_id: agent_87e4d5f08475e5bc558b2f390f
llm_id:        llm_c5157c4e1795cda2dbdc88fda69b (v0, gpt-5.2)

9-state machine: VerifyLead checkpoint between ConfirmSlots and Booking.
- verify_lead_data     -> :8003 /validator-function/verify-lead-data      (data_verified gate)
- record_booking_uid   -> :8003 /validator-function/record-booking-uid    (22-char + Cal accepted-only)
- set_callback_number  -> :8003 /validator-function/set-callback-number   (deterministic callback_number writer)
- extract_reach_details writes is_calling_best_number ONLY (callback_number variable stripped)
- validate_booking JS tool DELETED; extract_confirm_details corrective callback_number DELETED
Prompt: prompts/states/contact_details.md §4 edited (YES = seeded number stands; NO = call set_callback_number).
Acceptance so far: Maria happy-path 1/1 + signed /set-callback-number smoke 5/5. FULL LADDER PENDING.
Full context: Dialux_SDR/STATE.md + tasks/surgeon/set-callback-number/.
