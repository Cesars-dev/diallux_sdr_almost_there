# Call Analysis — Issues Tracker

> Reviewed calls from V3 test9 copy agent (`agent_47e4a4fbdfcbdb7bf2424f418a`, LLM `llm_ae461dfc248342f34b13d81108ec`).

---

## call_f4a3894eadf5b74f1da0b0ef288

**Date:** 2026-07-30
**Caller:** Maritza Bali — boiler breakdown (no heating, no hot water, error code 4445)
**Duration:** 264s (4m 24s)
**Cost:** $1.23
**Result:** Booked for next day 9 AM. User hung up satisfied.
**Disconnect:** `user_hangup`
**Sentiment:** Positive

### Per-State Verdict

| State | Verdict | Notes |
|---|---|---|
| Greeter | ✅ | Intent inferred correctly from "boiler isn't working" → `booking`. Name captured. |
| Triage | ✅ | Used approved phrase from `##uk-hvac-trade-kb##` ("pressure or circulation issue"). All fields captured. |
| Address | ⚠️ | Postcode took 3 corrections. See Issue #2. |
| Slot Selection | ⚠️ | Offered time windows ("9 to 12") instead of specific times. See Issue #3. |
| Confirmation | ✅ | Slot confirmed. Transition triggered correctly. |
| Booking | ✅ | `book_calendar` succeeded. Goodbye spoken. `end_call` not fired but user hung up first — acceptable. |

### Latency

| Metric | Value |
|---|---|
| LLM p50 | 927ms |
| LLM p95 | 1306ms |
| E2E p50 | 1554ms |
| E2E p95 | 2865ms |
| TTS p50 | 158ms |
| KB p50 | 91ms |
| `book_calendar` | 6394ms (6.4s) |

---

### Confirmed Issues

#### Issue #1 — Cal.com API returns time windows, not specific slots (Retell bug)

**Severity:** HIGH
**State:** slot_selection
**Description:** `check_availability` returns windowed ranges ("9 to 12, or 12:30 to 7") instead of specific times ("Tomorrow at 9 AM"). This is a Retell platform bug — the Cal.com tool payload doesn't parse individual slots correctly.
**Impact:** Violates Decision 7 (specific times, not windows). Agent offered ranges.
**Fix:** Build a custom webhook/function to replace Retell's built-in `check_availability_cal` tool. Query Cal.com API directly, parse the response into discrete slot objects, and return them as specific `[DAY] at [TIME]` pairs.
**Status:** TODO — add to NEXT_STEPS backlog

#### Issue #2 — Postcode collection chaotic (3 corrections)

**Severity:** MEDIUM
**State:** address
**Description:** Postcode "CT6 7SR" required 3 rounds of correction. STT misheard characters, agent interrupted user's corrections prematurely.
**Impact:** Extra turns, slight caller frustration.
**Assessment:** The address prompt already references `##uk-address-kb##` for hyphenation rules but doesn't enforce them inline. Adding a concise 5-rule enforcement block directly in the address prompt is feasible — current prompt is ~920 tokens, addition would be ~133 tokens → ~1053 total (within 1200 target).
**Fix:** Add inline `Postcode Hyphenation Rules` block to address prompt between Steps 2 and 3. Keep it concise — 5 rules max. Don't duplicate the full KB.
**Status:** ASSESSED — ready to implement if needed

#### Issue #3 — Address/city mismatch not caught (CT6 ≠ Brighton)

**Severity:** LOW
**State:** address
**Description:** User gave postcode CT6 7SR (Whitstable, Kent) but city "Brighton" (BN prefix). Agent accepted both without flagging the inconsistency.
**Impact:** Minor — engineer routes by postcode + house number, not city name.
**Note:** This was a deliberate test by the caller. The agent captured the correct postcode and house number — the primary routing fields.
**Assessment:** A UK Cities KB with postcode area prefix mapping could catch this (Brighton=BN, CT=Whitstable/Canterbury). ~50-100 entries for main UK cities. Already listed as TODO in NEXT_STEPS.md (task #3, status ❌ Not created).
**Status:** BACKLOG — low priority, nice-to-have

#### Issue #4 — `end_call` not fired (user hung up first)

**Severity:** NONE
**State:** booking
**Description:** Agent spoke goodbye but didn't call `end_call` tool. User hung up immediately after "That's it. Thank you."
**Note:** Not a bug. User terminated before the agent had a turn to fire `end_call`. This is acceptable behavior — the goodbye was spoken, user was satisfied.

#### Issue #5 — Surname "Bali" dropped

**Severity:** LOW
**State:** greeter
**Description:** User said "Maritza Bali" but `customer_name` stored as just "Maritza".
**Note:** Keeping as-is per user direction. Not a priority.

### Not Issues (False Positives from Initial Analysis)

| Item | Why not an issue |
|---|---|
| "Pressure or circulation" diagnostic language | Approved verbatim phrase in `uk-hvac-trade-kb.md:92` |
| `extract_triage_details` called 4x | Known Retell design flaw — LLM calls at go time regardless of "call once" instruction |
| `extract_address_details` called 4x | Same Retell limitation |
| `book_calendar` 6.4s latency | Cal.com API response time — not an agent bug |
| Intent classification "skipped" | LLM correctly inferred `booking` from "boiler isn't working" — schema populated correctly |

---

## call_bcc7408d35a628651e9d29fbac0 (Akrit — UK)

**Date:** 2026-07-30
**Caller:** Akrit — hot water issue only (heating works), started 5am today, boiler brand unknown, display blank (no error code)
**From:** +447927167237 (UK)
**Duration:** 282s (4m 42s)
**Cost:** $1.37
**Result:** Booked for tomorrow at 1 PM. Agent ended call (`agent_hangup`).
**Disconnect:** `agent_hangup`
**Sentiment:** Positive (Retell says Neutral — disagree, user said "Perfect", "Yeah", "Thank you. Have a good one.")
**Booking ID:** 23160216

### State Transitions

```
greeter → triage: ✅ (0:31s)    | extract + transition tools fired correctly
triage → address: ✅ (1:31s)   | triage_complete + transition fired correctly
address → slot_selection: ✅ (2:19s) | address_confirmed + transition fired correctly
slot_selection → confirmation: ✅ (4:04s) | slot_selected + transition fired correctly
confirmation → booking: ✅ (4:12s) | booking_confirmed + transition fired correctly
booking → end_call: ✅ (4:42s) | end_call fired at 282s
```

All 5 transitions fired correctly. Total transition time ~52s of wall clock.

### Per-State Verdict

| State | Verdict | Notes |
|---|---|---|
| Greeter | ✅ | STT heard "Accurate" instead of "Akrit" — agent asked to clarify, user confirmed. Followed Name Capture Logic: spelling check "A-k-r-i-t?" → confirmed. Intent inferred from "heating" → `booking`. |
| Triage | ✅ | Correctly identified "No Hot Water (but heating works)" subcategory. Used TWO approved KB phrases verbatim (lines 92 and 106 of uk-hvac-trade-kb.md). Captured timing detail when user interrupted. All fields populated. |
| Address | ✅ | **Cleanest address capture of any call so far.** One pass, no corrections. BH9 2SE confirmed first read-back. House number "Somebody is fifty five" → correctly parsed to "55". |
| Slot Selection | ⚠️ | **Critical slot loop — 38s of wasted conversation (turns 54–74).** Agent re-offered rejected "9am" 3 times. User explicitly said "I already said no to that." See Issue #6. |
| Confirmation | ✅ | "Tomorrow at 1 PM" confirmed. Dual user acknowledgment ("Yeah" + "Perfect"). Transition fired. |
| Booking | ✅ | `book_calendar` succeeded (4.5s). Closing flow executed correctly this time: recap → anything else → goodbye → end_call. See closing flow analysis below. |

### Latency

| Metric | Value | vs Maritza (call 1) |
|---|---|---|
| LLM p50 | 1079ms | +152ms (927→1079) |
| LLM p95 | 2005ms | +699ms (1306→2005) |
| LLM p99 | 2596ms | — |
| E2E p50 | 1688ms | +134ms (1554→1688) |
| E2E p95 | 3027ms | +162ms (2865→3027) |
| TTS p50 | 158ms | flat |
| KB p50 | 104ms | +13ms (91→104) |
| `book_calendar` | 4492ms | 1902ms slower (6394→4492) |
| `check_availability` avg | 1454ms (4 calls) | — |
| ASR p50 | 167ms | — |
| LLM requests | 52 | — |
| Avg tokens/request | 4286 | — |
| TTS p99 | 484ms | Note: two outliers at 267ms and 573ms |

**Latency assessment:** All within acceptable range. LLM p50/p95 slightly higher than Maritza, likely due to 282s call building more context. TTS had one 573ms spike (turn 73) — isolated outlier, not concerning. `book_calendar` was 4.5s (vs 6.4s for Maritza) — better this time.

### Per-Turn Timeline (key moments only)

| Time | Turn | Event |
|---|---|---|
| 0.6s | [0] | Agent greets |
| 5.6s | [1] | User: "problem with my heating" |
| 10.8s | [2] | Agent mirrors: "trouble with the heating — I can help" + asks name |
| 15.7s | [3] | User: "Accurate" (STT misparse of "Akrit") |
| 17.3s | [4] | Agent: "And your name, please?" — **good recovery from STT misparse** |
| 20.8s | [5] | User: "That is my name, Akrit" |
| 24.1s | [8] | Agent: "is it A-k-r-i-t?" — **Name Capture Logic: spelling check** |
| 29.2s | [9] | User confirms spelling |
| 31.4s | [13] | Agent: "pressure or circulation issue" + "both heating and hot water?" |
| 41.5s | [14] | User: "Just hot water" |
| 44.9s | [15] | Agent: "valve or sensor thing" + "When did it start?" |
| 56.3s | [16] | User: "started today" |
| 58.7s | [17] | Agent: starts repeating "valve or sensor" line (speech collision) |
| 61.8s | [18] | User interrupts: "five in the morning" |
| 69.8s | [19] | Agent: "Started at five this morning" — **good mirroring of interruption** |
| 79.1s | [23] | Agent: "No problem — engineer will identify it" + error code question |
| 96.8s | [32] | User: "b h nine two s e" |
| 101.6s | [33] | Agent confirms: "B-H-9-2-S-E" — **hyphenated correctly** |
| 110.8s | [36] | User: "Somebody is fifty five" — STT correctly parsed to "55" |
| 130.1s | [43] | Full address readback: "55 Highfield, Bournemouth — B-H-9-2-S-E" |
| 140.5s | [49-53] | `check_availability` called (1019ms) → "quickest slot tomorrow 9am" |
| 153.4s | [53] | **PROBLEM STARTS**: offers "tomorrow at 9am" — single time from a 9am-7pm window |
| 158.4s | [54] | User: "No. Can you give me a few other options?" |
| 163.3s | [55] | Agent: "tomorrow 10am or Saturday 9am" — **hallucinated 10am** (not from Cal.com data) |
| 171.9s | [56-58] | User: "a couple more slots", "Is tomorrow 10am the only slot you have?" |
| 181.7s | [61-63] | Agent re-queries Cal.com → offers "tomorrow 9am" AGAIN — **re-offer #1** |
| 198.2s | [64] | User: "I already said no to that" — **frustration visible** |
| 203.4s | [66-67] | Agent re-queries again → same window data |
| 215.7s | [68] | Agent: "Morning or afternoon?" — **finally adapts strategy** |
| 220.2s | [69] | User: "Afternoon" |
| 236.0s | [74] | Agent: "tomorrow 12pm or 1pm" — **correct discrete options from narrowed window** |
| 240.6s | [75] | User: "one PM" |
| 253.5s | [92-93] | `book_calendar` called → success (booking_id 23160216, 4492ms) |
| 266.8s | [94] | Agent: "booked in for tomorrow at 1pm. Is there anything else?" — **closing Step 1** |
| 272.4s | [95] | User: "No. That's fine." |
| 274.6s | [96] | Agent: "Thanks for calling British Heat Services. Have a good day." — **closing Steps 2-3** |
| 279.0s | [97] | User: "Thank you. Have a good one." — **closing Step 4 satisfied** |
| 282.1s | [98] | `end_call` fired — **correct: after user said goodbye** |

### 1. Prompt Following (detailed)

#### Greeter — ✅ Excellent

**Step 1 (Greet):** Verbatim match to prompt: "British Heat Services, Tom speaking — how can I help?" ✅

**Step 2 (Mirror):** "Right, trouble with the heating — I can help" — mirrors in 7 words. Prompt says ≤10 words. ✅ Also appended "Who am I speaking with?" — technically two things in one turn but the name question IS the next step, and the mirror was brief enough. Acceptable.

**Step 3 (Name Capture):** STT heard "Accurate" instead of "Akrit". Agent asked "And your name, please?" — this follows the Name Capture Logic: no KB match → confirm by spelling back. Agent attempted "is it A-k-r-i-t?" — hyphenated TTS format. ✅ User confirmed. Then intent was inferred as `booking` on the second extract (after user said "heating"). ✅

**Step 4 (Confirm Intent):** ⚠️ Agent skipped explicit intent confirmation. Prompt Step 4 says "Mirror the intent back and confirm" with examples like "So you're ringing because your boiler's packed in — I'll get that sorted for you, yeah?" The agent jumped straight from name spelling confirmation to "Sounds like it could be a pressure or circulation issue" (triage symptom question). This mirrors call 1 (Maritza) where intent was inferred without confirm-back. However, the agent DID get `classified_intent: booking` set correctly, so the transition worked. **Same behavior as call 1 — the LLM consistently skips the explicit intent confirm-back and goes straight to triage. This may be intentional LLM optimization or a consistent prompt following gap.**

#### Triage — ✅ Very Good

**Step 1 (Symptom Intake):** Agent correctly matched "heating" complaint to the "No Heating and/or Hot Water" KB category and used the approved phrase verbatim: "Sounds like it could be a pressure or circulation issue." ✅ Then asked the KB-recommended question: "Is it both heating and hot water, or just one?" — this is literally question #1 from the KB at line 97. ✅

When user said "Just hot water", agent correctly switched to the "No Hot Water (but heating works)" subcategory (line 104 of KB) and used the approved phrase verbatim: "If the heating's working but the hot water isn't, it's often a valve or sensor thing — I'll flag it for the engineer." ✅ This is a double-KB-phrase use — both categories matched in sequence. **This is actually correct behavior per the KB — the agent identified the correct subcategory and switched phrases.**

**Repeat at turn 17:** Agent started repeating "valve or sensor thing" again before asking "When did it start?" — this is a partial repeat. The first occurrence was at turn 15 (44.9s) and this was at turn 17 (58.7s) — only 14s apart. The prompt says "vary phrasing — do not repeat verbatim" (KB line 86). ⚠️ However, user interrupted this repeat at 61.8s, so the full phrase wasn't delivered. Minor.

**Step 2 (Boiler Brand):** "Do you know what brand the boiler is?" — verbatim from prompt Step 2. User said "No" → "No problem — the engineer will identify it there" — matches prompt instruction. `boiler_make` set to "unknown". ✅

**Step 3 (Error Code):** "Is there an error code showing?" — prompt says "Is there an error code showing on the display?" — slightly abbreviated but meaning preserved. User said "No. It's blank." Agent captured as `error_code: none`. ✅

**One question per turn rule:** ✅ Each turn asked exactly one question. Good.

#### Address — ✅ Flawless

**Step 1 (Postcode):** "Right Akrit, what's the postcode?" — matches prompt: "Right {{customer_name}}, what's the postcode?" Used customer name naturally. ✅

**Step 2 (Confirm Postcode):** "Just so I've got it — postcode B-H-9-2-S-E, right?" — hyphenated correctly per TTS rules. Used "Just so I've got it" from the address prompt's edge case phrasing (line 44). ✅

**Step 3 (House Number):** "And the house number?" — verbatim from prompt. User said "Somebody is fifty five" — agent parsed to "55" and mirrored: "So that's number 55." ✅

**Step 4 (Street):** "And the street name?" — verbatim from prompt. User: "Highfield". Agent: "Highfield, thanks." ✅

**Step 5 (City):** "And what city?" — verbatim from prompt. User: "In Bournemouth." ✅

**Step 6 (Confirm Full Address):** "So that's 55 Highfield, Bournemouth — postcode B-H-9-2-S-E. Is that right?" — matches prompt format exactly. Hyphenated postcode. Waited for confirmation. ✅

**Cleanest address capture across all calls reviewed. Zero corrections needed.**

#### Slot Selection — ⚠️ Critical Failure Zone (turns 53–74, ~38s wasted)

**Step 1 (Query Slots):** Filler "Let me check that for you." then `check_availability` called at 140.5s (1019ms latency). ✅

**Step 2 (Offer):** Agent said "The quickest slot is tomorrow at 9am. Does that suit?"

**Prompt says:** "Pick the 1–2 closest slots from the result. Offer as: Tomorrow at [TIME1] or [TIME2]"

**Cal.com returned:** `{"date":"Friday","availability_range":["From 9:00 AM to 7:00 PM"]}` — a window, not specific slots.

**Problem:** Agent picked the start of the window ("9am") and offered it as a single slot. Prompt expects 1-2 **specific times** but Cal.com only returns windows. Agent can't follow the prompt correctly because the data format doesn't support it.

**Step 3 (Rejection Handling):** This is where it broke down.

- **Turn 54 (158s):** User: "No. Can you give me a few other options?"
- **Turn 55 (163s):** Agent: "tomorrow at 10am or Saturday at 9am" — **10am is NOT in the Cal.com data.** The agent hallucinated this time. Saturday 9am was the start of the Saturday window. This is a hallucination — the agent invented a time slot that doesn't exist in the availability data.
- **Turn 56 (172s):** User: "a couple more slots"
- **Turn 57-58 (175-178s):** User: "Is tomorrow ten AM the only slot you have? For tomorrow?"
- **Turn 59 (178s):** Agent started "No" — then re-queried Cal.com
- **Turn 63 (195s):** "I've got tomorrow at 9am. Does that work?" — **re-offered the EXACT same rejected slot.** This violates basic conversation logic.
- **Turn 64 (198s):** User: "I already said no to that. I'm asking you for other options." — **explicit frustration**
- **Turn 67 (203s):** Agent re-queried Cal.com AGAIN — got same data
- **Turn 68 (216s):** Agent: "Sorry about that. Morning or afternoon works better?" — **finally adapted strategy.** This follows the prompt's Step 3 guidance: "If the customer is vague: Morning or afternoon — what works better?"
- **Turn 69 (220s):** User: "Afternoon"
- **Turn 72 (223s):** Agent re-queried with afternoon constraint → got narrowed window "12:00 PM to 7:00 PM"
- **Turn 74 (236s):** "tomorrow at 12pm or 1pm" — **correct. Two specific times from narrowed window.**

**4 `check_availability` calls total.** Prompt says max 5 — this used 4. Within limit but wasteful. The first 3 returned identical data because the agent didn't change the query parameters.

**Root cause chain:**
1. Cal.com returns windows, not specific times (Issue #1 — platform bug)
2. Agent can't decompose a "9am-7pm" window into discrete options without a custom webhook
3. Agent defaulted to window start time each time
4. Agent hallucinated a "10am" slot (not in Cal.com data) — this is an LLM fabrication on top of the data problem
5. Agent failed to remember the user had rejected "9am" — re-offered it twice

**Step 4 (Specific Day+Time):** N/A — user didn't name a specific time until after the narrowing process.

#### Confirmation — ✅ Clean

**Step 1:** "So that's Tomorrow at 1 PM — is that right?" — matches prompt format. ✅
**Step 2:** User confirmed with dual acknowledgment ("Yeah" + "Perfect"). ✅
**Transition:** `booking_confirmed: true` extracted, transition fired. ✅

#### Booking — ✅ Closing Flow Executed Correctly

**Step 1 (Book):** Filler "One moment while I get that. Right, I'm getting that booked in now." then `book_calendar` called at 253.5s. Success at 4492ms. ✅

**Step 2 (Result):** At 266.8s (13s after book_calendar returned): "Brilliant, you're booked in for tomorrow at 1pm." — prompt says: "Brilliant, you're booked in. I'll text a confirmation..." — agent abbreviated slightly but captured the key info. ✅

**Step 3 (Close):** Agent followed `##v2-call-closing-kb##` 4-step structure:

| Closing KB Step | Agent Behavior | Time |
|---|---|---|
| Step 1 — Check for other queries | "Is there anything else I can help you with?" | 266.8s ✅ |
| Step 2 — Brief summary | Already included in Step 2 above: "booked in for tomorrow at 1pm" | 266.8s ✅ |
| Step 3 — Warm goodbye | "Thanks for calling British Heat Services. Have a good day." | 274.6s ✅ |
| Step 4 — Wait for response, then end | User: "Thank you. Have a good one." → `end_call` at 282s | 282.1s ✅ |

**This is a textbook closing flow.** The 4-step structure from `call_closing_kb.md` was followed perfectly. The 5.5s gap between user's goodbye (279s) and `end_call` (282s) is normal processing time.

**However:** The booking prompt Step 2 success template says "I'll text a confirmation — the calendar invite has everything the engineer needs." The agent omitted the text confirmation mention. Minor deviation. Also, the fee was not mentioned — but the prompt says "Only state the fee if the customer asks" (main prompt line 76), so this is correct behavior.

**Contrast with Mexico Akrit call:** That call's booking state went: extract → "Let me note that down" → `end_call` (no speech between extract and end). This call went: book → recap + "anything else?" → user says no → goodbye → user says bye → `end_call`. The closing flow IS in the prompts and works when the LLM follows it. The Mexico call was an LLM non-determinism failure.

### 2. Nonsense/Hallucination

| Item | Verdict | Detail |
|---|---|---|
| "Accurate" → Akrit | ✅ Not hallucination | STT misfire. Agent handled with follow-up question. |
| "Valve or sensor thing" | ✅ Not hallucination | Approved verbatim phrase from `uk-hvac-trade-kb.md:106` under "No Hot Water (but heating works)" category. |
| "Pressure or circulation issue" | ✅ Not hallucination | Approved verbatim phrase from `uk-hvac-trade-kb.md:92` under "No Heating and/or Hot Water" category. |
| **"Tomorrow at 10am"** | ❌ **Hallucination** | Agent offered "tomorrow at 10am or Saturday at 9am" at turn 55. Cal.com data only contained windows ("9am to 7pm"). 10am was NOT in the data. The agent fabricated a specific time. **This could have led to a booking at a time that doesn't exist.** Fortunately the user asked for more options instead of accepting it. |

**The "10am" hallucination is a real issue.** If the user had accepted it, the agent would have tried to book 10am — either Cal.com would reject it or it would book at the wrong time. This is more dangerous than the windowed-range issue because it's an LLM fabrication on top of bad data.

### 3. Redundancy

(Skipping known Retell multi-extract design flaws per SOP.)

- `check_availability` called 4 times: calls 1, 2, and 3 returned identical data because the agent didn't change query parameters. Only call 4 (after morning/afternoon narrowing) returned different data. 3 of 4 calls were wasted.
- "Let me check that for you" filler used at turns 43 and 50 — twice in address/slot transition zone. Minor.

### 4. Repetition

- **"Valve or sensor" phrase started twice** (turns 15 and 17, 14s apart). Turn 17 was interrupted by user. KB says "vary phrasing — do not repeat verbatim" (line 86). The LLM regenerated the same KB phrase as pre-fill for the next question. This is the same pattern as the Mexico Akrit call with "pressure or circulation." ⚠️
- **"tomorrow 9am" offered 3 times** (turns 53, 63, and effectively again at 67 which returned the same data). See Issue #6.

### 5. Bugs (Code/Config)

**No code/config bugs found.** All tools returned correct data. All transitions fired. `book_calendar` succeeded. `end_call` fired at correct time. Variables were all populated correctly in `collected_dynamic_variables`.

**`selected_slot_start` timestamp concern:** The extracted value is `"2026-07-31T12:00:00Z"` but the user selected "1 PM" (not 12 PM). The label says "Tomorrow at 1 PM" but the ISO string says 12:00:00Z. If this is UTC, then 12:00 UTC = 1:00 PM BST (British Summer Time = UTC+1). So the slot string is actually correct — it's 12:00 UTC which IS 1 PM local time. ✅

**`check_availability` 3rd call latency spike:** 3404ms at turn 62. Other calls were 640ms, 753ms, 1020ms. The 3404ms spike is unexplained but didn't impact the call negatively (agent was already re-querying). Acceptable.

### 6. Tool Call Analysis (excluding known Retell multi-extract)

| Tool | Times | Prompt Says | Verdict |
|---|---|---|---|
| `transition_to_triage` | 1x | After extract + trigger | ✅ Correct |
| `transition_to_address` | 1x | After triage_complete + trigger | ✅ Correct |
| `transition_to_slot_selection` | 1x | After address_confirmed + trigger | ✅ Correct |
| `transition_to_confirmation` | 1x | After slot_selected + trigger | ✅ Correct |
| `transition_to_booking` | 1x | After booking_confirmed + trigger | ✅ Correct |
| `check_availability` | 4x | Max 5 allowed | ⚠️ Wasted 3 of 4 — same query params |
| `book_calendar` | 1x | Once | ✅ Success |
| `end_call` | 1x | After closing flow | ✅ After user said goodbye |

All transition tools fired in the correct sequence: extract → trigger → transition. No out-of-order transitions. No missing transitions.

### 7. Conversation Flow (detailed)

**Pacing:**
- Greeter+name: 0.6s → 29.2s = 29s (good — quick name capture with STT recovery)
- Triage: 31.4s → 90.2s = 59s (good — 4 questions, one per turn)
- Address: 91.7s → 139.5s = 48s (good — clean single pass)
- Slot Selection: 140.5s → 243s = 103s (bad — 38s wasted on slot loop)
- Confirmation: 243s → 252s = 9s (fast — clean confirm)
- Booking+Close: 252s → 282s = 30s (good — includes 4.5s book_calendar + 13s to speech + closing)

**One question per turn:**
- Greeter: ⚠️ "Right, trouble with the heating — I can help. Who am I speaking with?" — mirror + question in same turn. But mirror was ≤10 words and name question is the natural next step. Acceptable.
- Triage: ✅ Every turn was exactly one question.
- Address: ✅ Every turn was exactly one question. No stacking.
- Slot Selection: ✅ One question/offer per turn.
- Booking: ✅ Closing flow followed KB steps sequentially.

**Responses to user:**
- Turn 19: User interrupted to add timing detail ("five in the morning"). Agent said "Started at five this morning." — **excellent handling of interruption.** Mirrored back the new info, then continued with next question (boiler brand).
- Turn 55: User asked for "a few other options." Agent offered 2 options (10am + Sat 9am). However, 10am was hallucinated. ⚠️
- Turn 64: User expressed frustration. Agent said "Sorry about that" — good acknowledgment, then changed strategy to morning/afternoon. **Good recovery from failure.**
- Turn 94-97: Clean closing exchange. User felt comfortable enough to say "Have a good one." — indicates positive experience despite the slot struggle.

**Filler phrase variety:**
Filler phrases used across the call: "Give me a second", "One moment while I get that", "Let me check that for you", "Taking notes, one moment please", "Right, let me sort that", "Let me note that down", "Let me get that booked for you" (implied). Good variety. Main prompt lists 6 fillers — agent used at least 5 distinct ones. ✅

### 8. Logs & Metrics

| Metric | Value |
|---|---|
| Total transcript entries | 98 |
| User speech turns | 19 |
| Agent speech turns | 19 |
| Tool invocations | 22 (excluding known multi-extract duplicates: 4 check_availability + 6 transition + 6 extract + 4 trigger + 1 book + 1 end_call) |
| LLM requests | 52 |
| Cost | $1.37 |
| Duration | 282s (4m 42s) |
| State transitions | 5 (all 6 states visited) |
| Booking ID | 23160216 |
| Final agent state | `booking` |
| `current_agent_state` | `booking` |
| `previous_agent_state` | `confirmation` |
| All dynamic variables | populated correctly (see Collected Variables above) |

**Cost breakdown:** $75.47 (55%) on LLM tokens, $25.94 (19%) voice engine, $18.87 (14%) TTS, $7.08 (5%) telephony, $5.60 (4%) token surcharge, $2.36 (2%) KB, $1.50 (1%) text testing. LLM token cost is the dominant factor — 52 requests × avg 4286 tokens = ~223K tokens total.

---

### Confirmed Issues from This Call

#### Issue #6 — Slot selection loop + hallucinated time (3 re-offers + fabricated 10am)

**Severity:** HIGH
**State:** slot_selection
**Description:**
1. Agent offered "tomorrow at 9am" (start of 9am-7pm window). User rejected.
2. Agent **hallucinated "tomorrow at 10am"** — this time was NOT in Cal.com data. If accepted, would have caused a booking at a non-existent slot.
3. Agent re-offered "tomorrow at 9am" TWICE MORE despite user having already rejected it. User said "I already said no to that" — explicit frustration.
4. After 38s of wasted conversation, agent finally adapted by asking morning/afternoon, then offered correct discrete times (12pm or 1pm).

**Impact:** 4 wasted turns (38s), user frustration, potential hallucinated booking.
**Root cause:** Cal.com windowed ranges (Issue #1) + LLM fabrication on top of bad data.
**Fix (two-part):**
1. **Immediate — prompt fix:** Add to slot_selection prompt Step 2: "When a window is returned (e.g., '9:00 AM to 7:00 PM'), you MUST pick 2 specific times spread across the window. Example: from '9am to 7pm' offer '9am or 2pm'. NEVER offer just the start time. NEVER offer a time not in the returned data. NEVER re-offer a time the customer has already rejected."
2. **Proper — custom webhook (Issue #1):** Replace Cal.com tool with one that returns discrete `[DAY] at [TIME]` pairs.
**Status:** HIGH — prompt fix is immediate, webhook is backlog

#### Issue #8 update — Closing flow: intermittent, not broken

**Severity:** MEDIUM
**State:** booking
**Description:** This call proves the closing flow works when the LLM follows it. The 4-step structure from `call_closing_kb.md` was executed perfectly: (1) "anything else?" → (2) booking recap → (3) goodbye → (4) wait for user response → `end_call`. The Mexico Akrit call failed because the LLM skipped the speech between extract and end_call. This is LLM non-determinism, not a prompt or config bug.
**Impact:** Some callers get no goodbye/recap (Mexico Akrit), others get perfect closing (this call). Unpredictable.
**Fix:** Add a hard guardrail to booking prompt: "MANDATORY: After book_calendar succeeds, you MUST speak ALL of the following before calling end_call: (1) recap the booking, (2) ask if anything else, (3) say goodbye. If you call end_call without speaking these steps first, the call will end abruptly and the customer will not receive confirmation."
**Status:** MEDIUM — prompt strengthening needed

#### Issue #10 — Cal.com time windows (duplicate of Issue #1)

**Status:** DUPLICATE — root cause of Issue #6. Already tracked.

#### Issue #11 — KB approved phrase repeated within 14s (new)

**Severity:** LOW
**State:** triage
**Description:** "If the heating's working but the hot water isn't, it's often a valve or sensor thing" was started at turn 15 (44.9s) and the agent began repeating it at turn 17 (58.7s) — only 14s apart. User interrupted the repeat. KB line 86 says "vary phrasing — do not repeat verbatim." The LLM used the same KB-retrieved phrase as pre-fill for two consecutive turns.
**Impact:** Minor. User interrupted before the full repeat. Same pattern as "pressure or circulation" repeat in Mexico Akrit call.
**Fix:** Add to triage prompt Step 1: "After using an approved phrase, do NOT use the same phrase again on your next turn. Use a simple transition instead (e.g., 'Right' or 'Got it')."
**Status:** LOW — cosmetic, intermittent

### Not Issues (False Positives — RECLASSIFIED)

| Item | Previous Assessment | Corrected Assessment |
|---|---|---|
| "Valve or sensor thing" | Previously flagged as Issue #7 (unapproved diagnostic) | **FALSE POSITIVE.** Approved verbatim phrase at `uk-hvac-trade-kb.md:106` under "No Hot Water (but heating works)" category. Agent correctly identified the subcategory and used the matching phrase. ✅ |
| "Pressure or circulation issue" at turn 13 | Was correct, no change | Still correct — approved at `uk-hvac-trade-kb.md:92` ✅ |
| Two KB phrases used in sequence | Not previously flagged | **Correct behavior.** User's problem spanned two KB categories. Agent matched "No Heating and/or Hot Water" first (turn 13), then refined to "No Hot Water (but heating works)" after user said "Just hot water" (turn 15). This is exactly how the KB is designed to be used. ✅ |
| STT "Somebody is fifty five" → "55" | Not previously flagged | **Correct parsing.** Agent correctly extracted "55" from the STT output. ✅ |
| Intent confirm-back skipped | Not previously flagged as issue | Same behavior as call 1 — consistent LLM optimization. Intent correctly classified as `booking`. Transition worked. Not a bug. |

---

## Master Flaw List — All Calls Combined

> Deduplicated across call_f4a3894eadf5b74f1da0b0ef288 (Maritza) and call_bcc7408d35a628651e9d29fbac0 (Akrit UK).
> Excludes known Retell platform bugs (multi-extract, speak_after_execution) per SOP.

---

### HIGH

| # | Flaw | State | Seen In | Root Cause |
|---|---|---|---|---|
| F-1 | **Cal.com returns time windows, not specific slots** | slot_selection | Both | Retell platform — `check_availability_cal` parses Cal.com API into ranges ("9am to 7pm") instead of discrete times. Agent can't follow slot_selection prompt which requires offering "[DAY] at [TIME1] or [TIME2]". |
| F-2 | **Agent hallucinated a time not in Cal.com data** | slot_selection | Akrit | Agent offered "tomorrow at 10am" when Cal.com only returned "9am to 7pm". 10am was fabricated. If accepted, would have attempted a booking at a non-existent slot. Cascading from F-1 — LLM invents specific times when only windows exist. |
| F-3 | **Agent re-offers rejected slot multiple times** | slot_selection | Akrit | After user rejected "9am", agent re-offered it twice more (3 re-offers total). User said "I already said no to that." Agent failed to remember rejection and kept querying Cal.com with same params, getting same data. Cascading from F-1 — without discrete slots to offer, agent defaults to window start. |

### MEDIUM

| # | Flaw | State | Seen In | Root Cause |
|---|---|---|---|---|
| F-4 | **Closing flow intermittent — sometimes skipped entirely** | booking | Akrit (Mexico), not Akrit UK | LLM non-determinism. Mexico Akrit: extract → "Let me note that down" → `end_call` (no speech). UK Akrit: recap → "anything else?" → goodbye → `end_call` (perfect). Both calls used same prompt and LLM. Closing flow works when LLM follows it but isn't guaranteed. |
| F-5 | **Postcode collection chaotic — multiple corrections needed** | address | Maritza | "CT6 7SR" required 3 rounds of correction. STT misheard characters, agent read back too fast first time. Address prompt references `##uk-address-kb##` but doesn't enforce hyphenation rules inline. |

### LOW

| # | Flaw | State | Seen In | Root Cause |
|---|---|---|---|---|
| F-6 | **Address/city mismatch not caught** | address | Maritza | User gave CT6 7SR (Whitstable, Kent) but city "Brighton" (BN prefix). Agent accepted both. No KB exists to validate city against postcode prefix. |
| F-7 | **KB approved phrase repeated on consecutive turns** | triage | Both | "Pressure or circulation" repeated twice in Maritza's call. "Valve or sensor thing" started twice in Akrit's call (14s apart). KB says "vary phrasing — do not repeat verbatim" (line 86). LLM uses same KB-retrieved phrase as pre-fill for next turn. |
| F-8 | **Intent confirm-back skipped consistently** | greeter | Both | Prompt Step 4 says "Mirror the intent back and confirm." Agent consistently skips this and jumps from name confirmation straight to triage symptom question. Intent is correctly classified (`booking`) so transitions work, but the explicit confirm-back never happens. Consistent across both calls — may be intentional LLM optimization. |
| F-9 | **Surname dropped** | greeter | Maritza | User said "Maritza Bali" but `customer_name` stored as "Maritza" only. Low priority per user direction. |

### NOT A FLAW (False Positives)

| Claim | Why Not |
|---|---|
| "Pressure or circulation" is diagnostic hallucination | Approved verbatim phrase at `uk-hvac-trade-kb.md:92` |
| "Valve or sensor thing" is unapproved diagnostic | Approved verbatim phrase at `uk-hvac-trade-kb.md:106` for "No Hot Water (but heating works)" subcategory |
| Two KB phrases used in sequence (pressure→valve) | Correct behavior — agent refined category match as it learned more. This is how the KB is designed. |
| Multi-extract (2-4x per state) | Known Retell design flaw — LLM fires extract at go-time regardless of "call once" instruction |
| `book_calendar` latency (4.5-6.4s) | Cal.com API response time — not an agent issue |
| `end_call` not fired (Maritza) | User hung up first. Agent had spoken goodbye. Acceptable. |
| "Accurate" STT misparse | Agent handled correctly — asked to clarify, user confirmed. |
| STT "Somebody is fifty five" → "55" | Correctly parsed. |

---

### Fix Priority Order

| Priority | Fix | Flaws Addressed | Effort |
|---|---|---|---|
| 1 | **Slot selection prompt: add window decomposition rules + rejection memory** | F-2, F-3 | Low — prompt edit only, ~50 tokens |
| 2 | **Booking prompt: hard guardrail on closing flow before end_call** | F-4 | Low — prompt edit only, ~40 tokens |
| 3 | **Custom Cal.com webhook returning discrete slots** | F-1, F-2, F-3 | High — webhook build + deploy |
| 4 | **Address prompt: inline postcode hyphenation enforcement** | F-5 | Low — prompt edit only, ~133 tokens |
| 5 | **Triage prompt: no-repeat rule for approved phrases** | F-7 | Low — prompt edit only, ~20 tokens |
| 6 | **UK Cities KB (postcode prefix → city mapping)** | F-6 | Medium — new KB, ~100 entries |
| 7 | **Greeter prompt: enforce intent confirm-back** | F-8 | Low — prompt edit, but may conflict with LLM optimization |

**Items 1, 2, 4, 5, 7 are all prompt-only fixes** that can be done in one build cycle. Item 3 (custom webhook) is the proper fix but requires dev work. Item 6 (UK Cities KB) is a new knowledge base file.

---

## Backlog (carried from NEXT_STEPS.md)

| # | Task | Priority | Status |
|---|---|---|---|
| 1 | Build custom Cal.com webhook to replace `check_availability_cal` (time windows bug) | HIGH | TODO |
| 2 | Enforce inline postcode hyphenation rules in address prompt | MEDIUM | ASSESSED, ready to implement |
| 3 | Create UK Cities KB (postcode prefix → city mapping) | LOW | BACKLOG |
| 4 | Enforce British Address KB for all address handling | MEDIUM | TODO (from NEXT_STEPS) |
| 5 | End call guardrail pattern | MEDIUM | TODO (from NEXT_STEPS) |
