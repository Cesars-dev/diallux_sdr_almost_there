# Bug Analysis — UK HVAC Agent (V2.1 test8 copy)

> Live call analysis from 2026-07-25 through 2026-07-29.
> Agent: `agent_ed8fc268f2c8c2bd8203f7435c` (UK HVAC V2.1 test8 copy)
> LLM: `llm_698479480ef60916f79173f27263` (gpt-5.1)

---

## 1. Extraction Tool Called as No-Op (Empty Arguments)

**Root cause:** The LLM invokes `extract_greeter_values`, `extract_address_details`, and `extract_booking_values` with empty arguments (`""`). The tool returns the current variable state but sets nothing new. This means every call is a no-op.

**Observed in every call.** Examples:
- Call 1: `extract_address_details` at 100s with `args=""` — `customer_name` stayed `""` even though user said "Accurate" 3s earlier
- Call 2: `extract_greeter_values` 4 times (13s, 34s, 53s, 100s) — all empty, never set `greeting_exchanged` or `intent_clear`

**Downstream failures caused by this:**
- `customer_name` never captured from speech → passed as `""` to `book_calendar` → Cal.com rejects with 400
- `greeting_exchanged` / `intent_clear` never set to `true` → greeter→address edge never fires → agent trapped in greeter for entire call
- 4-7 redundant extraction calls per conversation, all returning the same unchanged state
- Token bloat from repeated no-op calls increases LLM latency

**Fix required:** The prompt needs to tell the LLM to call extraction tools **once per state, with specific values** — not as a "check current state" action. Remove the `EXTRACT NOW` scatter pattern and replace with a single "call when you have all the data to hand off."

---

## 2. No Dependency Guard Before `book_calendar`

**Root cause:** `book_calendar` fires without checking that required fields (`customer_name`, etc.) are populated. The tools have no ordering enforcement — the LLM can call any tool in any sequence.

**Evidence:** First `book_calendar` at 118s used `"name":""`. Cal.com returned `400: "responses - {name}error_required_field"`. The booking only succeeded on the second attempt after the agent re-asked for the name.

**Fix required:** Either (a) add a prompt-level guard — "Before calling book_calendar, verify customer_name is set and non-empty" — or (b) restructure the booking state tools so `book_calendar` can only be called after `extract_booking_values` has confirmed the name.

---

## 3. Slot Offer Day Mismatch — Agent Said "Tomorrow" But Booked Today

**What the prompt says (lines 94-95 of `booking.md`):**
```
- <I've got a slot tomorrow morning between 8 and 12, or Thursday afternoon between 1 and 5 — which suits?>
- <I can get you in today between 1 and 5, or tomorrow morning — which works better?>
```
Both example offers include a day label on each time option.

**What the agent actually did:**
1. `check_availability` returned two days with identical 9AM-7PM windows: Wednesday July 29 (today) and Thursday July 30 (tomorrow)
2. Agent ignored the example format and stripped day labels: *"Do you prefer between nine and one, or between one and five?"*
3. User picked *"Second option"* — meaning the 1-5 window, but with no day specified
4. Agent now had to guess a day. Both days had the same 1-5 window available. It guessed "tomorrow."
5. Agent verbally said **"tomorrow"** 4 times across the conversation
6. But the `book_calendar` tool call used `"time":"2026-07-29T13:00:00"` — **today's date**, not tomorrow

**Why this is a failure:** The customer was told "tomorrow between 1 and 5." The actual booking is today at 1pm. If the customer waits for Thursday, they miss the appointment. The engineer shows up today; the customer isn't home.

**Root cause:** The LLM removed day labels from the offer format. This made the choice ambiguous — the user could only pick a time window, not a day+time combination. Once the user picked a time, the LLM had to invent a day assignment on its own, and the speech didn't match the tool call.

**Fix required:** Replace the example-based format with an explicit rule: "When offering slots, you MUST label each time range with its day. Never offer time ranges without specifying which day they belong to."

---

## 4. Full Booking Readback Skipped Before `book_calendar`

**Root cause:** The prompt has an explicit hard rule — *"Never call book_calendar before the customer has verbally confirmed the full booking read-back"* — but the LLM ignores it.

**Evidence:** In every successful booking, the agent never read back the full address + date + time and asked for confirmation before calling the API. It read back partial info (just postcode, or just time) and proceeded to book.

**Fix required:** Reinforce the rule with stricter prompt language. Consider moving the readback into the state machine as an edge condition.

---

## 5. `address_confirmed` Set to `true` Without User Confirmation

**Root cause:** The LLM sets `address_confirmed: true` inside the extraction tool call even though the user never explicitly confirmed the full address readback.

**Evidence:** At 91s the agent said *"So that's M-4-6-D-E. Who am I speaking with?"* — confirmed only the postcode. At 100s, `extract_address_details` returned `address_confirmed: true`. The full address (house number + street + city + postcode) was never read together, and the user never said "yes" or "correct."

**Fix required:** The prompt already says *"Wait for explicit verbal confirmation before setting address_confirmed = true"* — but the LLM bypasses it. Investigate why and tighten enforcement.

---

## 6. No Terminal State for "Quote" Intent

**Root cause:** The state machine has one path: greeter → address → booking. When `classified_intent` is `"quote"`, the agent enters address state but has nowhere to go — it tries to collect symptoms and problem category that don't apply, then either gets stuck or fabricates an exit.

**Evidence:** Call 2 had `classified_intent: "quote"`. The LLM was trapped in the greeter state (never transitioned) and ultimately hallucinated *"we only cover the North East"* as an exit — not a real rule, just a fabricated escape.

**Fix required:** Either (a) define a quote terminal state, or (b) add prompt-level handling for quote-only callers: collect address → say "we'll have someone call you with a quote" → end call.

---

## 7. LLM Latency Too High

**Raw latency data from the 3 calls** (filtering out 1-2ms no-op tool call outliers):

| Metric | Call 1 (187s) | Call 2 (287s) | Call 3 (64s) |
|--------|-------------|-------------|-------------|
| LLM p50 | 1434ms | 861ms | 951ms* |
| LLM p90 | 3046ms | 1883ms | — |
| LLM p95 | 3908ms | 2133ms | — |
| LLM max | 3908ms | 2210ms | 951ms |
| LLM samples | 13 (real) | 21 (real) | 1 (real) |
| E2E p50 | 3142ms | 2724ms | — |
| E2E p95 | 5147ms | 3744ms | — |
| TTS p50 | 160ms | 159ms | 168ms |
| ASR p50 | 132ms | 248ms | — |
| KB p50 | 83ms | 75ms | 176ms |
| Avg tokens | 5797 | 4505 | 3843 |

*\*Call 3 only had 1 real LLM call before user hung up — insufficient data.*

**Observations:**
- The 1-2ms "LLM calls" in the raw data are the no-op extraction tool invocations — the LLM doesn't generate any text, just returns the tool result instantly. They are not real LLM inference.
- Real LLM p50 ranges from **861ms to 1434ms** across the two meaningful calls.
- The 2ms no-op calls inflate the token count without doing useful work — each one adds to the context window for the next real LLM call, compounding latency.
- E2E p50 is 2.7-3.1s — the user experiences a 3-second delay on average.
- The dominant factor is LLM inference time (gpt-5.1). TTS, ASR, and KB retrieval are fast (<250ms combined).

**Potential improvements:**
- Eliminating redundant no-op extraction calls would reduce token bloat, which should improve LLM latency incrementally
- Each tool call no-op adds ~15-30 empty tokens to the context for every subsequent LLM request, slowing each one slightly

---

## 8. Hallucinated Booking — Zero Tool Calls Fired

**Call:** `call_3afe9029f1b33f75067a82bffc9` (2026-07-25 08:02 UTC, 200s)
**Model:** gpt-5.1 (v11) — this agent uses `llm_698479480ef60916f79173f27263`, not gpt-5.4

**What happened:** Agent told the customer *"All set for Monday at 8 AM"* and *"You're all set"* but never called `check_availability` or `book_calendar`. Zero booking-related tool calls fired. The appointment was completely fabricated.

**Why this matters:** If this hit production, the customer would wait for an engineer who never arrives. This is the worst possible failure mode for a booking agent.

**Possible cause:** The model was gpt-5.1, not gpt-5.4. The hallucination may be a model capability issue — gpt-5.1 may not handle the multi-state prompt reliably. The agent was also stuck in address state (never transitioned to booking) and invented the confirmation as an exit.

**Fix required:** Investigate whether this reproduces on gpt-5.4. If not, restrict this agent to gpt-5.4. If it does reproduce, add stronger guardrails: never say "booked" or "all set" without a successful `book_calendar` tool result.

---

## 9. Vague Booking Time Window

**Call:** `call_b4c562ae8a51bba96a41bf7a239` (2026-07-25 08:30 UTC, 171s — Akrit Phun)

**What happened:** User said *"One thirty"* when asked which slot they wanted. The agent responded *"You're all set for today between half one and three"* — a 1.5-hour window instead of a specific booked time. The `book_calendar` call used `"time":"2026-07-29T13:00:00"` (1pm), but the agent told the customer "between half one and three," which is a range.

**Why this matters:** The customer expects an engineer to arrive sometime in a 1.5-hour window. The engineer has a specific time (1pm). If the customer isn't home at that exact time, there's a miss.

**Fix required:** The prompt should instruct the LLM to convert the user's vague time preference into a specific slot from the available range, and confirm the exact time back to the user — not a range.

---

## Summary — Priority Order

| # | Bug | Impact | Fix scope |
|---|-----|--------|-----------|
| 1 | Extraction tool called as no-op (empty args) | Blocks state transitions, fails name capture, causes booking failures | Prompt restructure |
| 2 | No dependency guard before `book_calendar` | First booking attempt always fails | Prompt guard |
| 3 | Slot offer day mismatch (said tomorrow, booked today) | Customer expects wrong day | Prompt fix |
| 4 | Full booking readback skipped | Hard prompt rule ignored | Prompt reinforcement |
| 5 | `address_confirmed` set without user confirmation | Address not verified | Prompt reinforcement |
| 6 | No terminal state for "quote" | Agent fabricates exits or gets stuck | State machine design |
| 7 | LLM latency too high | Poor user experience | Multi-factor fix |
| 8 | Hallucinated booking (zero tool calls) | Customer waits for engineer who never arrives | Model/prompt guardrails |
| 9 | Vague booking time window (1.5h range instead of specific time) | Customer/engineer time mismatch | Prompt fix |
