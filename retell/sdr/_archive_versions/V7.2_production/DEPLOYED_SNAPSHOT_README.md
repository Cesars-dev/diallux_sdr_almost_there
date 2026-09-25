# DEPLOYED SNAPSHOT — PRODUCTION TRUTH (2026-08-25)
`DEPLOYED_llm_snapshot.json` = exact payload fetched from Retell for the LIVE production agent:
- chat_agent_id: agent_66df480ff8f240ee9e919d3b53
- llm_id:        llm_97474e866ccc2c89586c8f120ea2 (version 0)

## WARNING
The markdown sources in this folder DIVERGED from this snapshot after deployment:
(user manual edits to Intake/Discovery/Booking/contact_details + V7.1 Closer/Offer sales edits
+ Loss Playback KB append). Those later iterations showed a state-machine bypass failure mode.
DO NOT rebuild/redeploy from these folders without reconciling against the snapshot JSON.

Test evidence backing this build: GK suite 5/5 booked · happy batch 5/5 booked · adversarial contained.
