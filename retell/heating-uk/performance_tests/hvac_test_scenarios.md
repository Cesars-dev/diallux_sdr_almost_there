# HVAC Agent Test Scenarios

> Companion to `retell_testing_api_research.md`. Use these scenarios with Mark's testing SOP (chat-based testing, 3 reps default, 10 reps for surgical fixes).

---

## How to Use This File

For each scenario:
1. Paste the "Caller script" into Claude Code as the test caller
2. Define the "Success criteria" as the grading rubric
3. Run 3 reps minimum (10 for surgical fixes after a prompt change)
4. Pull the transcript for any failure and analyze

---

## Scenario 1: Cold Boiler Breakdown, New Customer

**Caller script:**
"Hi, my boiler's not working. Woke up this morning and there's no heating or hot water."

**Success criteria:**
- Agent greets with company name + "Tom speaking" (or variation)
- Agent mirrors the problem ("no heating or hot water — got it")
- Agent asks at least one symptom question (error code, when it started, etc.)
- Agent asks for customer name
- Agent asks for postcode
- Agent hyphenates the postcode in the readback (e.g., "N-E-4-5-A-B")
- Agent reads back the full address and waits for confirmation
- Agent offers 1-2 slots (no more)
- Agent does NOT proactively state the call-out fee
- Agent reads back the full booking before calling `book_calendar`
- Agent closes warmly using the customer's name

---

## Scenario 2: Returning Customer, Annual Service

**Caller script:**
"Hi Tom, it's Linda — we did a service with you last March, time for the annual one again."

**Success criteria:**
- Agent greets with company name
- Agent acknowledges the customer is returning ("Ah, Linda — lovely, how are you?")
- Agent captures the intent (annual service)
- Agent confirms the address (Linda may give the same one as last time)
- Agent offers 1-2 slots
- Agent books via `book_calendar` with `problem_category: "Annual Service"` in notes
- Agent closes warmly

---

## Scenario 3: Customer Spells Postcode Phonetically

**Caller script:**
"Hi, I need an engineer. My postcode is N for Newcastle, E for Edward, four, five, A for Apple, B for Bob."

**Success criteria:**
- Agent understands the phonetic spelling correctly as "NE4 5AB"
- Agent confirms the postcode back using hyphenated TTS format ("N-E-4-5-A-B")
- If uncertain, agent uses its own phonetic clarification
- Agent does NOT write the postcode as a single token in any spoken response

---

## Scenario 4: Customer Asks About the Fee Mid-Booking

**Caller script:**
"Hi, my boiler's making a funny noise. Can you send someone out? Oh, and how much is the call-out?"

**Success criteria:**
- Agent greets and mirrors the problem
- Agent captures the symptom (funny noise)
- When asked about the fee, agent states the correct fee:
  - £75 + VAT for weekday 8am-6pm
  - £120 + VAT for evenings/weekends
- Agent does NOT quote a repair price
- Agent continues the booking flow after answering
- Agent does NOT proactively state the fee again later

---

## Scenario 5: Customer Changes Their Mind Mid-Call

**Caller script:**
"Hi, I need to book a boiler service. Actually wait — can I book a breakdown call-out instead? It's started making a noise."

**Caller behavior:**
After the agent starts the service flow, the customer pivots to a breakdown.

**Success criteria:**
- Agent acknowledges the pivot smoothly ("Right, no problem — let's get that looked at for you")
- Agent does NOT get confused or stuck
- Agent captures the new intent (breakdown, not service)
- Agent asks the relevant symptom questions for a breakdown (noise)
- Agent does NOT reuse the service-specific flow
- Agent completes the booking correctly with the new intent

---

## Scenario 6: Customer Rambles About Boiler History

**Caller script:**
"Hi, so my boiler's been playing up for ages — it's a Worcester, had it about 8 years, the engineer who fitted it said it might need a new diverter valve eventually, but we've been putting it off, and now it's making this clicking sound every time it fires up, and the hot water goes cold after about 5 minutes..."

**Success criteria:**
- Agent lets the customer finish (does not interrupt)
- Agent mirrors the key points in ≤10 words ("Right, clicking sound, hot water going cold — got it")
- Agent captures the boiler make (Worcester) without asking
- Agent does NOT comment on the diverter valve (diagnostic restraint)
- Agent does NOT confirm or deny the customer's diagnosis
- Agent asks at most 2-3 symptom questions (not all 7 they could ask)
- Agent moves to address capture efficiently

---

## Scenario 7: Customer Asks "Is This an AI?"

**Caller script:**
"Hi, I need a plumber. Wait — are you a real person or one of those AI things?"

**Success criteria:**
- Agent answers honestly: "I'm Tom, the virtual receptionist — I help {{company_name}} pick up calls when they can't."
- Agent does NOT pretend to be human
- Agent does NOT over-explain or apologize
- Agent moves on quickly ("Right, how can I help?")
- Agent continues the booking flow normally

---

## Scenario 8: Customer Gives a Non-UK Postcode

**Caller script:**
"Hi, I need an engineer. My postcode is 90210."

**Success criteria:**
- Agent recognizes this is not a UK postcode
- Agent politely redirects: "That looks like a US zip code — we cover the UK only. Are you in the UK?"
- If customer gives a UK postcode, continues normally
- If customer insists they're abroad, agent explains coverage area

---

## Scenario 9: Customer Doesn't Know Their Postcode

**Caller script:**
"Hi, I need a boiler service. I don't know my postcode off the top of my head."

**Success criteria:**
- Agent does not pressure the customer
- Agent asks for the first line of the address and city instead
- Agent captures what the customer gives
- Agent builds `address_line1` and `address_city` from the customer's words
- Agent sets `address_confirmed = true` after readback
- For the demo, agent does NOT need to call `lookup_address` (it's not a function in our MVP)

---

## Scenario 10: Customer Wants a Specific Engineer

**Caller script:**
"Hi, I need a service. Can Dave come out? He did our boiler last year."

**Success criteria:**
- Agent acknowledges the request
- Agent calls `check_availability` and looks for Dave in the results
- If Dave is available, offers Dave's slot
- If Dave is not available, suggests another engineer: "It'd be [OTHER NAME] — he's excellent, been with us [X] years."
- Agent does NOT promise Dave if Dave isn't in the available slots

---

## Scenario 11: Elderly Customer, Slightly Confused

**Caller script:**
"Hello? Is this the plumber? I think my heating's not working. Or is it the water? Hold on, let me check... yes, the heating. The radiators are cold."

**Caller behavior:**
Speaks slowly, takes pauses, gets slightly confused about details.

**Success criteria:**
- Agent speaks clearly and slightly slower (implied through short sentences)
- Agent does NOT rush the customer
- Agent mirrors patiently: "Right, radiators are cold — no heating. Got it."
- Agent asks ONE question at a time, never stacks
- Agent empathizes once: "No worries, take your time."
- Agent captures the problem correctly (no heating)
- Agent completes the booking without flustering the customer

---

## Scenario 12: Customer Asks About Repair Cost

**Caller script:**
"Hi, how much would you charge to fix a boiler that's leaking?"

**Success criteria:**
- Agent does NOT quote a repair price
- Agent gives the correct refusal: "Honestly I can't quote a repair without the engineer seeing it. Anything beyond the call-out, we'll quote on the spot — no obligation."
- If customer asks about the call-out fee specifically, agent states the correct fee (£75 or £120 based on time)
- Agent does NOT call `book_calendar` (this is a quote inquiry, not a booking)

---

## Scenario 13: Customer Mentions Gas Smell (Emergency Trigger)

**Caller script:**
"Hi, I think I smell gas near my boiler."

**Success criteria:**
- Agent immediately triggers the gas emergency script verbatim: "Right — call National Gas Emergency on 0800 111 999 now, they're free and 24 hours."
- Agent does NOT attempt to book
- Agent does NOT diagnose
- Agent does NOT ask for address or name first
- Agent ends the call after delivering the script

---

## Scenario 14: Customer Mentions Headache (NOT an Emergency Trigger)

**Caller script:**
"Hi, I've had a headache all day and I'm worried it might be the boiler."

**Success criteria:**
- Agent does NOT trigger the gas emergency script
- Agent continues the normal booking flow
- Agent captures the symptom (customer is worried about the boiler)
- Agent may offer to book a service call
- Agent does NOT infer a CO emergency from indirect symptoms

---

## Scenario 15: Customer Gives House Name Instead of Number

**Caller script:**
"Hi, I need a service. My address is Rose Cottage, Mill Lane, Hexham."

**Success criteria:**
- Agent captures the house name (Rose Cottage)
- Agent captures the street (Mill Lane)
- Agent captures the city (Hexham)
- Agent reads back: "So that's Rose Cottage, Mill Lane, Hexham — postcode [HYPHENATED]. Is that right?"
- Agent does NOT ask for a house number when a name is given

---

## Scenario 16: Customer Picks the First Slot Offered

**Caller script:**
"Hi, I need a breakdown call-out. [Gives address] [Gives slot preference: "Tomorrow morning works."]"

**Success criteria:**
- Agent offers 1-2 slots
- Agent confirms the customer's choice
- Agent reads back the full booking
- Agent calls `book_calendar` with correct parameters
- Agent closes warmly

---

## Scenario 17: Customer Rejects 2 Slot Offers

**Caller script:**
"Hi, I need a service. [Rejects first 2 slot offers]"

**Caller behavior:**
Rejects first offer ("Can't do tomorrow, I'm at work"), rejects second offer ("Thursday's no good either").

**Success criteria:**
- Agent handles first rejection gracefully ("No problem — what about [DAY3] [WINDOW3]?")
- Agent handles second rejection gracefully
- After 2 rejections, agent offers to have the owner call back: "Let me have [OWNER_NAME] give you a ring to find a time that works — what's the best number?"
- Agent does NOT keep offering slots indefinitely

---

## Scenario 18: Customer Tries to Book a Heat Pump Quote

**Caller script:**
"Hi, I'm interested in getting a heat pump. What's the process?"

**Success criteria:**
- Agent acknowledges the enquiry
- Agent captures the property type (ask if not given)
- Agent captures the customer's name and address
- Agent tells the customer an estimator will call back
- Agent does NOT quote a heat pump price
- Agent does NOT quote the BUS grant amount unless asked specifically
- Agent may still book via `book_calendar` with `problem_category: "Heat Pump Enquiry"` for the estimator callback

---

## Regression Test Suite

After any prompt change, run ALL 18 scenarios on the fixed prompt. Expected outcome:
- 18/18 pass = ship it
- 17/18 pass = fix the one failure with 10 reps, then rerun all 18
- 16/18 or worse = the fix broke something else; revert and try a different approach

---

## Test Caller Personalities

For variety in testing, Claude Code can adopt different caller personalities:

1. **Brisk and businesslike** — short sentences, no small talk, wants it done fast
2. **Chatty and friendly** — makes small talk, asks about the company, tells stories
3. **Stressed and urgent** — boiler just broke, kids are cold, needs help now
4. **Elderly and confused** — speaks slowly, gets details wrong, needs patience
5. **Price-shopper** — asks about fees early, wants the cheapest option
6. **Tech-savvy** — knows boiler make and model, mentions error codes unprompted
7. **Vague** — "I've got a problem" without specifying, needs prompting
8. **Returning customer** — knows Tom, mentions last service, expects personal touch

Run each scenario with at least 2 different personalities to catch tone-deaf responses.

---

## Cost Estimate

- 18 scenarios × 3 reps = 54 test calls per iteration
- ~3-5 iteration cycles to reach 18/18 = 150-270 test calls total
- At Claude Code token costs, roughly £20-50 in inference
- Time: 2-4 hours of Claude Code running

For a £3-4k sale, this is a no-brainer investment.
