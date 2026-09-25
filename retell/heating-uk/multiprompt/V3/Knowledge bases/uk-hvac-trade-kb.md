# UK HVAC Trade Knowledge Base

> Retrieved automatically during the triage state. Provides UK HVAC trade vocabulary, service classification, boiler brand reference, and symptom-specific approved questions with retrieval-safe phrasing. The agent MUST retrieve questions and approved phrases from this KB when interacting with the customer. NEVER formulate questions independently.

---

## UK HVAC Trade Vocabulary

- **Boiler** — the appliance that heats water for central heating and hot water. UK households have boilers, not furnaces.
- **Central heating** — the system of radiators and pipes fed by the boiler.
- **Radiators** — the heat emitters on the walls. Never call them "baseboards".
- **Hot water cylinder** — the tank that stores hot water. Not "water heater".
- **Engineer** — the qualified person who fixes boilers. Never "technician" or "tech".
- **Call-out fee** — the charge for the engineer's visit, includes up to 1 hour on-site diagnosis.
- **CP12 / Landlord Gas Safety Record** — annual certificate landlords must obtain for rental properties.
- **Gas Safe Register** — the only legal gas engineer body in the UK. Every engineer must be registered.
- **Stopcock** — the main water shut-off valve, usually under the kitchen sink.
- **TRV (Thermostatic Radiator Valve)** — the dial on the side of a radiator that controls its heat.
- **Power flush** — a cleaning process for central heating systems.
- **Postcode** — UK postal code. Never "zip code".

---

## Common UK Boiler Brands

When a customer mentions any of these, capture the brand name in the `boiler_make` field:

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

---

## Service Types We Book

### Boiler Breakdown
Customer reports the boiler is not working properly — no heating, no hot water, error code, noise, leak. Book as a breakdown call. Call-out fee applies.

### Annual Boiler Service
Routine yearly maintenance, not a fault. Customer usually knows when it's due. Book as a service. CP12 fee if it's a landlord property.

### Landlord Gas Safety Certificate (CP12)
Annual legal requirement for rental properties. Engineer inspects gas appliances and issues a certificate. Book as CP12. Fee is fixed.

### New Boiler Quote
Customer wants to replace an old boiler or install a new one. Capture property type and timeline. Route to estimator callback. Do not quote install price.

### Heat Pump Enquiry
Customer is interested in a heat pump, often because of the Boiler Upgrade Scheme grant. Capture property type. Route to estimator.

### Radiator / Pressure Issue
Customer reports cold radiators, pressure dropping, or TRV problems. Book as a breakdown call.

### Thermostat / Controls Issue
Customer reports problems with the thermostat, programmer, or smart controls. Book as a breakdown call.

### Leak
Customer reports water leaking from the boiler, a pipe, or a radiator. Run safety triage — if it's a major leak, advise turning off the stopcock. Book as a breakdown call.

---

## Call Type Classification Hints

| Customer says… | Classify as… |
|---|---|
| "No heating", "no hot water", "boiler's not working" | Boiler Breakdown |
| "Annual service", "yearly service", "boiler service due" | Annual Boiler Service |
| "CP12", "landlord certificate", "gas safety certificate" | Landlord Gas Safety Certificate |
| "New boiler", "replace my boiler", "boiler quote" | New Boiler Quote — estimator callback |
| "Heat pump", "air source", "BUS grant" | Heat Pump Enquiry — estimator callback |
| "Radiator cold", "pressure dropping", "TRV" | Radiator / Pressure Issue |
| "Thermostat not working", "Hive broken", "controls" | Thermostat / Controls Issue |
| "Water leaking", "dripping", "puddle" | Leak — safety triage first |

---

## Symptom Categories — Approved Questions

Use this section AFTER identifying the problem category. Retrieve the matching symptom category, use the approved plain-English phrase verbatim, and ask ONE question at a time. Vary phrasing — do not repeat verbatim. Max 3 questions per category.

---

### No Heating and/or Hot Water

**Approved phrase (use verbatim):** "Sounds like it could be a pressure or circulation issue."

**Questions (vary phrasing, ask one at a time):**
- Is the boiler showing an error code on the display, or is it completely blank?
- When did it start — today, or has it been a few days?
- Is it both heating and hot water, or just one?
- Has it been gradually getting worse, or did it just stop?

**Do NOT say:** which part is faulty, what to press or reset, what the repair will cost.

---

### No Hot Water (but heating works)

**Approved phrase (use verbatim):** "If the heating's working but the hot water isn't, it's often a valve or sensor thing — I'll flag it for the engineer."

**Questions (vary phrasing, ask one at a time):**
- Has it always been intermittent, or did it just stop?
- Does it happen on every tap, or just one?
- Any pattern — mornings, evenings, after running for a while?

**Do NOT say:** "diverter valve", "plate heat exchanger", "thermistor".

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

**Do NOT say:** what the code means, which component it points to. Capture verbatim only.

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

## Error Code Handling Rule

- Capture the error code **verbatim** — do not interpret it
- Do NOT look up what the code means
- Do NOT suggest which component it points to
- The engineer will interpret the code on site

If the customer asks what the code means: "I'll note it exactly for the engineer — he'll know what it points to when he's with you."

---

## Boiler Brand Reference

When a customer names a brand, match it to the Common UK Boiler Brands list above and capture in `boiler_make`. If unsure, ask: "Could you spell that for me?" When they spell it, confirm back hyphenated for TTS clarity (see TTS Hyphenation Rules in `##name-spelling-kb##`). Use the phonetic alphabet in `##name-spelling-kb##` only as a last resort if a letter is unclear.

---

## Regulatory and Safety Context

### Gas Safe Register
The only legal gas engineer body in the UK. All {{company_name}} engineers are Gas Safe registered. Registration number: {{gas_safe_number}}. The customer can verify an engineer's ID card on arrival.

### National Gas Emergency Service
Phone: **0800 111 999**. Free, 24 hours. For smell of gas, suspected carbon monoxide, or a gas leak. The agent must direct customers to this number immediately and not attempt to diagnose.

### Carbon Monoxide Symptoms
Headaches, nausea, dizziness, breathlessness, collapse — especially when the boiler is on and several people in the property are affected. If suspected, advise opening windows, leaving the property, and calling 0800 111 999.

### Landlord Gas Safety Record (CP12)
Annual legal requirement for rental properties in the UK. Engineer inspects gas appliances and issues a certificate. Certificate usually emailed within 24 hours of the visit.

### Boiler Upgrade Scheme (BUS)
Government grant of £7,500 toward a heat pump installation. Eligibility and details are confirmed by the estimator — the agent must not quote eligibility rules. If asked, say: "The estimator will talk you through the grant and eligibility."

---

## Vulnerable Customer Signals

Treat as vulnerable (prioritise same-day or next-day slots) if the customer mentions:
- Elderly or living alone
- Disabled
- Young baby in the house
- Cold house with no alternative heating
- Medical condition affected by cold

Do not ask directly. Listen for cues and set the flag silently.

---

## Out-of-Hours Behaviour

Calls outside {{opening_hours}} are still answered by Tom. The same flow applies. Out-of-hours call-out fee is higher than the weekday fee — the exact amount is returned by the fee tool when the customer asks. If no engineer is available for an out-of-hours slot, offer the earliest next-day slot and escalate if the customer insists.

---

## What This KB Does NOT Contain

- **Part-level diagnostics** (no "diverter valve", "PCB", "thermistor" as causes)
- **Repair procedures** (no step-by-step fix instructions)
- **Error code dictionaries** (codes are captured verbatim only)
- **Pricing for repairs** (never quoted — only the call-out fee is stated, and only when the customer asks)
- **DIY advice** (no "try resetting it", "bleed the radiator")

If the agent cannot find a relevant entry in this Knowledge Base, the correct response is: "I'll have the engineer look at that when he's with you."
