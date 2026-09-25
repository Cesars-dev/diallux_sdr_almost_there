# CALL-ANALYSIS-SOP — Maria sim run (V7.9 fast config, local engine)

> Run: idx0 Maria · 2026-09-03 22:22 UTC · LF session (full transcript in Langfuse)
> Booking: `qeTqHuZ1EDzH8bxEdhPQ6H` — Cal-accepted, canceled after analysis
> Config: gpt-5.2, no temperature, no reasoning_effort (0.84s avg LLM)

## Test #7: Summary

### State Transitions
Intake → Discovery: ✅
Discovery → Closer: ✅ (after one false trigger — see Redundancy)
Closer → Offer: ✅
Offer → contact_details: ✅
contact_details → ConfirmSlots: ✅
ConfirmSlots → VerifyLead: ✅ (validate_lead slot_verified=true)
VerifyLead → Booking: ✅ (verify_lead_data data_verified=true)
Booking → Closing: ✅ (Cal-accepted UID, record_booking_uid 200)

### Booking
create_livecall_booking: ✅ (qeTqHuZ1EDzH8bxEdhPQ6H, recovered:false, booked at confirmed 2:30 PM slot)
end_call: ⚠️ (sim conversation closed on user goodbye; engine `ended` never fired — Closing asked "anything else?" and waited. On Retell, end_call would close from here. Sim artifact, not agent fault.)

### 1. Prompt Following
- Intake ✅ filler ("Yeah, I hear you—") → single question → extract.
- Discovery ⚠️ asked one question per turn, good content — but see Redundancy (3× extract, one `discovery_completed: False`).
- Closer ❌ **the leak pitch was never delivered.** `extract_leak_inputs` fired (20 × 50% × $650 captured) but `calculate_monthly_leak` was **never called** and the agent never spoke the $6,500/week / $28,000/month numbers. The monetization beat — the core of Closer — was skipped when Maria asked "how does it work?" (agent answered and moved on). The Offer even said "what your numbers look like with it on" — referring to numbers the prospect never heard.
- Offer ✅ 20-min walkthrough, Jay, today/tomorrow choice.
- contact_details ✅ name, company, `record_reach_details` (is_calling_best_number=true, phone_confirmed=true — py-owned booleans working).
- ConfirmSlots ✅ check_current_date → query_livecall_slots → offered EXACTLY the 2 frozen slots (1:00 / 2:30) → confirm → validate_lead.
- VerifyLead ✅ / Booking ✅ / Closing ✅ (confirmation + soft close; but see Bugs: "SMS text confirmation").

### 2. Nonsense / Hallucination
- ❌ **"You'll get an SMS text confirmation"** — nothing in this stack sends SMS. Not agent improvisation: it is **scripted in Booking.md step 3** ("You'll get a text with confirmation"). Prompt-level false promise — must be reworded or the capability must exist.
- No JSON leakage, no self-contradiction, no fabricated policies otherwise.

### 3. Redundancy
- ⚠️ `extract_discovery_details` ×3 — twice with `interest_signal: False` and one `discovery_completed: False` write before the corrected call. The SOP's named "trivial/wasted call" pattern. Self-corrected; also fixed `industry` "medical practice" → "dental practice" on the 3rd pass.
- ⚠️ `extract_person_details` ×2 — progressive (2nd added company_name); borderline acceptable.
- Everything else single-shot.

### 4. Repetition
- ✅ No loops. Confirmation asked twice by design (ConfirmSlots confirm + pre-book confirm). Persona repeated her phone number 4× unprompted — agent never re-asked for it.
- Trivial: "Central time" acknowledged twice.

### 5. Bugs
- `today_date` stale seed: final dvs carry **"2026-08-21"** (hardcoded seed in llm.json). Unused this run (check_current_date overwrote in-flow for slot logic — the BOOKING used the correct date), but it is a landmine for any earlier `{{today_date}}` reader. Fix: seed `""`.
- Leak math (computed by validate_lead): 20 × 50% × $650 = $6,500/wk → $28,000/mo — internally consistent ✅ (but never spoken, see #1).
- All endpoint calls HTTP 200; zero API errors; all params real values (E.164 phone, IANA tz, verbatim slot `2026-09-04T14:30:00`).

### 6. Tool Call Analysis
- Order correct in every state: extract → completed-trigger → transition ✅
- ❌ `calculate_monthly_leak` missing from Closer (leak numbers only surfaced later inside validate_lead's response_variables — and were never spoken).
- All other required tools fired once, with populated args.

### 7. Conversation Flow
- Natural pacing, one question per turn, mirrored the caller's words, no stacking, re-asked nothing unnecessarily.
- Sales-flow gap: prospect explicitly asked "how exactly does Dialux answer those calls?" and got a good answer — but the agent never quantified her loss to her face. That's the money moment, skipped.

### 8. Logs & Metrics
- Turns: 10 (user) | LLM calls: 37 (fast config, ~0.84s avg) | Tool calls: 33 | Transitions: 8
- Endpoints: check_current_date, query_livecall_slots (freeze×2), validate_lead, verify_lead_data, record_reach_details, create_livecall_booking, record_booking_uid — all 200.
- Cost: ≈ $0.40–0.60 OpenAI (sim). Retell cost: $0 (local engine).
- Final dvs: all gates green (slot_verified, data_verified, phone_confirmed, booking_verified=true, booking_failed=false), booking_uid recorded.

## ARE WE DOING WHAT WE'RE SUPPOSED TO DO?

**Mechanically: yes — 9/9 states, all gates, booking perfect.**
**As a SALES call: not yet.** Ranked:
1. **Closer skipped the leak pitch** (no calculate_monthly_leak, numbers never spoken) — stochastic skip, same family as Susan's loop. Fix belongs in the deterministic layer, not the prompt: make the engine/`extract_leak_inputs` result *force* the calculate next turn (same duplicate-guard pattern), or have validate_lead's leak numbers injected as dvs earlier so ConfirmSlots can reference them.
2. **"SMS text confirmation" scripted lie** — one line in Booking.md to fix (or wire SMS).
3. **`today_date` stale seed** — one-line llm.json seed fix, next deploy.
4. Discovery false-trigger noise — cosmetic, self-corrected.
