# UK HVAC Symptom Intake KB

> Retrieved automatically during the triage state. The agent MUST retrieve questions and approved phrases from this KB. NEVER formulate questions independently.

---

## How to Use This KB

1. After the customer states their problem, retrieve the matching symptom category from this KB.
2. Ask ONE question from that category. Vary the phrasing — do not repeat verbatim.
3. Mirror the customer's answer in ≤10 words.
4. Use the approved plain-English phrase for that category verbatim — do not improvise.
5. Move to the next question only if needed (max 3 questions total).

**Never formulate your own questions. Always retrieve from this KB.**

---

## Symptom Categories

### No Heating and/or Hot Water

**Approved phrase (use verbatim):** "Sounds like it could be a pressure or circulation issue."

**Questions (vary phrasing, ask one at a time):**
- Is the boiler showing an error code on the display, or is it completely blank?
- When did it start — today, or has it been a few days?
- Is it both heating and hot water, or just one?
- Has it been gradually getting worse, or did it just stop?

**Do NOT say:** which part is faulty, what to press or reset, what the repair will cost.

---

### Intermittent Heating or Hot Water

**Approved phrase (use verbatim):** "Intermittent hot water is often a sensor or valve thing."

**Questions (vary phrasing, ask one at a time):**
- Does it cut out after a few minutes, or never quite reach temperature?
- Does it happen on every tap, or just one?
- Any pattern — mornings, evenings, after running for a while?
- Does it come back on its own, or do you need to reset it?

**Do NOT say:** "diverter valve", "plate heat exchanger", "thermistor".

---

### Banging, Kettling, or Rumbling Noise

**Approved phrase (use verbatim):** "A banging noise is usually pump or pipework related."

**Questions (vary phrasing, ask one at a time):**
- Is it when the boiler fires up, or while it's running?
- How loud — can you hear it in the next room?
- Does it happen every time, or just sometimes?
- Has it got worse recently, or been the same for a while?

**Do NOT say:** heat exchanger, sludge, limescale as a diagnosis. The engineer will identify the cause.

---

### Cold Spots on Radiators

**Approved phrase (use verbatim):** "Cold spots on radiators often point to sludge or a TRV."

**Questions (vary phrasing, ask one at a time):**
- Is it the top of the radiator that's cold, or just one side?
- Is it all radiators, or just one or two?
- Have you noticed any cold radiators upstairs vs downstairs?
- Have they been bled recently?

**Do NOT say:** "power flush", "balance the system", "replace the TRV".

---

### Pressure Loss

**Approved phrase (use verbatim):** "Pressure dropping is often a leak or expansion vessel thing."

**Questions (vary phrasing, ask one at a time):**
- What's the pressure gauge reading now — do you know?
- Have you had to top it up recently? How often?
- Any visible water anywhere — under the boiler, near the pipes?
- Does it drop overnight, or while the heating is on?

**Do NOT say:** "filling loop", "expansion vessel replacement", "pressure relief valve".

---

### Error Code on Display

**Approved phrase (use verbatim):** "Right, that error code — I'll note it exactly for the engineer."

**Questions (vary phrasing, ask one at a time):**
- Can you read the code back to me exactly as it appears?
- Is it flashing, or steady on the display?
- Did it appear at the same time as the problem started, or before?
- Have you tried resetting it — and if so, did the code come back?

**Do NOT say:** what the code means, which component it points to. The agent MUST NOT attempt to interpret error codes — capture verbatim only.

---

### Boiler Not Firing / No Ignition

**Approved phrase (use verbatim):** "If it's not firing up at all, we'll need to get the engineer to look at it."

**Questions (vary phrasing, ask one at a time):**
- Is there any sound at all when you turn it on — a click, a fan, anything?
- Has the pilot light gone out, if you have one?
- Have you had any power cuts or tripped switches recently?
- Are the lights on the front panel on, or is it completely dead?

**Do NOT say:** ignition lead, gas valve, PCB, fan.

---

### Leak from Boiler or Pipes

**Approved phrase (use verbatim):** "A leak from the boiler — we'll get an engineer out to you."

**Questions (vary phrasing, ask one at a time):**
- How fast is it dripping — a drop every few seconds, or faster?
- Is the water coming from underneath the boiler, or higher up?
- Have you put anything down to catch it?
- Have you turned the boiler off, or is it still running?

**Safety note:** If the leak is fast, advise: "If you know where your stopcock is — usually under the kitchen sink — turn it off now."

**Do NOT say:** heat exchanger, pump seal, auto-air vent.

---

### Thermostat or Controls Issue

**Approved phrase (use verbatim):** "Right, controls playing up — we'll get an engineer to check it."

**Questions (vary phrasing, ask one at a time):**
- Is the thermostat completely blank, or just not responding?
- Have you changed the batteries, if it's wireless?
- Is it the thermostat, the timer, or a smart control like Hive or Nest?
- When did it stop responding — recently, or has it been a while?

**Do NOT say:** specific replacement parts, brand-specific fixes beyond what the customer says.

---

## Boiler Brand Capture (Opportunistic)

If the customer mentions any of these brands, capture it in `boiler_make`. Do NOT ask for it as a separate question.

- **Worcester Bosch** (often just "Worcester") — most common UK domestic brand
- **Vaillant** — German, premium
- **Ideal** — popular mid-range
- **Baxi** — common in social housing
- **Glow-worm** — budget brand
- **Viessmann** — German, premium
- **Potterton** — older housing stock
- **Intergas** — newer, fewer moving parts
- **Alpha** — less common
- **Ferroli** — less common

If the customer is unsure of the brand, do not push. Say: "No problem — the engineer will identify it when he's there." Move on.

---

## Error Code Handling Rule

- Capture the error code **verbatim** — do not interpret it
- Do NOT look up what the code means
- Do NOT suggest which component it points to
- The engineer will interpret the code on site

If the customer asks what the code means: "I'll note it exactly for the engineer — he'll know what it points to when he's with you."

---

## What This KB Does NOT Contain

- **Part-level diagnostics** (no "diverter valve", "PCB", "thermistor" as causes)
- **Repair procedures** (no step-by-step fix instructions)
- **Error code dictionaries** (codes are captured verbatim only)
- **Pricing for repairs** (only call-out fee is stated, and only when asked)
- **DIY advice** (no "try resetting it", "bleed the radiator")

If a symptom doesn't match any category in this KB, the correct response is: "I'll have the engineer look at that when he's with you."
