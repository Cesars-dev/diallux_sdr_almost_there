# FINAL PRODUCTION GRADE — 2026-08-25

**V7.5_lean** is the final production-grade build of the Dialux SDR chat agent.

- chat_agent_id: `agent_edf1437704e976c53539c7effe`
- llm_id: `llm_3e9f048aaba0399c162315ec9c12` (version 0)
- model: gpt-5.2 · temperature 0.1 · model_high_priority: false

## What it is
V7.0 skeleton (8-state machine + /validate_lead gate) + sales-craft KB (Loss Playback,
Flip & Second Shot, Punch-Line Bridge) + gpt-5.2 + single `# CRITICAL CONSTRAINTS` block.
Main prompt trimmed: no tool instructions except end_call, redundant sections removed.

## Context budget (tokens, o200k)
main=1059 · Closing 1324 · Offer 1969 · Intake 1998 · Booking 2377 · Discovery 2415 · contact_details 2636 · ConfirmSlots 2999 · Closer 3391

## Lineage verdict
- V7.0 (agent_66df480ff8f240ee9e919d3b53): previous production reference
- V7.2_production: validated baseline (priority=false proof)
- V7.3_craft_kb: craft added; bypass regression under stress personas
- V7.4_hard_gpt52 (agent_a9a7205fa6085e1b0c0246ae60): HARD CONSTRAINTS + gpt-5.2; zero fabrication in 23 chats
- **V7.5_lean: final production grade (this folder)**

## Known accepted trade-offs (fine as-is per owner, 2026-08-25)
- Empty extract_* ceremony calls remain (data flows via transition args)
- ConfirmSlots ~3k tokens from custom-function schemas (gate cost, accepted)
- gpt-5.2 ~2x inference cost vs 5.1 (accepted for discipline)
