# Sample UK HVAC Knowledge Base

> This is the contents of the `uk-hvac-trade-kb` Knowledge Base to link to the Retell agent. Save as a `.md` file and upload it as a **Text** source in the Retell Knowledge Base tab. Markdown is the recommended format per Retell's KB docs — clear `##` headings, short paragraphs, no ambiguous pronouns (chunks are retrieved independently).

> **KB design principle:** this file gives the agent **category-level understanding** of UK HVAC issues — enough to sound savvy and capture the right info, **not enough to diagnose**. Each symptom entry contains the **one approved plain-English phrase** the agent may use, plus the **questions to ask**, plus an explicit **"do not say"** list. There are no part-level causes, no repair procedures, no error-code dictionaries.

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

## Common UK Boiler Brands

When a customer mentions any of these, capture the brand name in the `boiler_make_model` field.

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
Customer reports water leaking from the boiler, a pipe, or a radiator. **Run safety triage** — if it's a major leak, advise turning off the stopcock. Book as a breakdown call.

## Symptom Categories — Context for Classification

Each entry describes what the customer is likely experiencing. Use this context to identify the problem category, not to read canned phrases.

### No Heating and Hot Water
- **Category:** Boiler breakdown
- **Context:** Customer has lost both heat and hot water. Likely a pressure issue, circulation fault, or complete boiler lockout. Ask questions to narrow scope.
- **Signals:** "no heating", "no hot water", "boiler's dead", "nothing working"
- **Do NOT say:** which part is faulty, what to press or reset, what the repair will cost.

### No Hot Water (but heating works)
- **Category:** Boiler breakdown
- **Context:** Heating works fine but hot water isn't coming through. Could be a diverter, sensor, or timing issue.
- **Signals:** "hot water not working", "heating works but no hot water", "water runs cold"
- **Do NOT say:** "diverter valve", "plate heat exchanger", "thermistor".

### Intermittent Heating
- **Category:** Boiler breakdown
- **Context:** Heating cuts out or doesn't reach temperature consistently. Often timer, thermostat, or pressure related.
- **Signals:** "heating goes on and off", "doesn't get warm", "cuts out after a bit"
- **Do NOT say:** specific sensors, pump names, PCB.

### Banging / Kettling / Rumbling Noise
- **Category:** Boiler breakdown
- **Context:** Unusual noises from the boiler or pipes. Likely pump, flow, or trapped air.
- **Signals:** "banging noise", "kettling sound", "boiler making noise", "rumbling"
- **Do NOT say:** heat exchanger, sludge, limescale as a diagnosis.

### Cold Spots on Radiators
- **Category:** Boiler breakdown
- **Context:** Radiators aren't heating evenly. Could be trapped air, sludge buildup, or a valve issue.
- **Signals:** "radiator cold at the top", "one radiator not working", "cold spots"
- **Do NOT say:** "power flush", "balance the system", "replace the TRV".

### Pressure Loss
- **Category:** Boiler breakdown
- **Context:** Boiler pressure keeps dropping. Could be a small leak, expansion vessel issue, or needs repressurising.
- **Signals:** "pressure keeps dropping", "gauge is low", "need to top up pressure"
- **Do NOT say:** "filling loop", "expansion vessel replacement", "pressure relief valve".

### Error Code on Display
- **Category:** Boiler breakdown
- **Context:** Boiler display shows an error code. Capture the exact code — do not interpret it.
- **Signals:** "error code", "flashing light", "E1", "F1", "code on the screen"
- **Do NOT say:** what the code means, which component it points to.

### Boiler Not Firing / No Ignition
- **Category:** Boiler breakdown
- **Context:** Boiler won't turn on at all. Could be electrical supply, gas supply, or ignition component.
- **Signals:** "boiler won't fire", "not igniting", "no power", "won't turn on"
- **Do NOT say:** ignition lead, gas valve, PCB, fan.

### Leak from Boiler
- **Category:** Boiler breakdown
- **Context:** Water escaping from the boiler unit itself. Severity varies from drip to active leak.
- **Signals:** "water coming from boiler", "boiler dripping", "leaking underneath"
- **Safety:** If fast, advise turning off the stopcock and the boiler.
- **Do NOT say:** heat exchanger, pump seal, auto-air vent.

### Leak from Pipe or Radiator
- **Category:** Boiler breakdown
- **Context:** Water escaping from pipework or a radiator, not the boiler itself.
- **Signals:** "pipe leaking", "radiator leaking", "water on the floor", "dripping from pipe"
- **Safety:** If major, advise stopcock off.
- **Do NOT say:** which joint, what to tighten.

### Thermostat / Controls Not Responding
- **Category:** Boiler breakdown
- **Context:** Thermostat, timer, or smart controls aren't communicating with the boiler or responding to input.
- **Signals:** "thermostat not working", "controls not responding", "can't change temperature", "Hive not working"
- **Do NOT say:** replacement part names, specific brand troubleshooting.

## Regulatory and Safety Context

### Gas Safe Register
The only legal gas engineer body in the UK. All {{company_name}} engineers are Gas Safe registered. Registration number: {{gas_safe_number}}. The customer can verify an engineer's ID card on arrival.

### National Gas Emergency Service
Phone: **0800 111 999**. Free, 24 hours. For smell of gas, suspected carbon monoxide, or a gas leak. The agent must direct customers to this number immediately and not attempt to diagnose.

### Carbon Monoxide Symptoms
Headaches, nausea, dizziness, breathlessness, collapse — especially when the boiler is on and several people in the property are affected. If suspected, advise opening windows, leaving the property, and calling 0800 111 999.

### Landlord Gas Safety Record (CP12)
Annual legal requirement for rental properties in the UK. Engineer inspects gas appliances and issues a certificate. Fee is confirmed by the `get_call_out_fee` tool when the customer asks. Certificate usually emailed within 24 hours of the visit.

### Boiler Upgrade Scheme (BUS)
Government grant of £7,500 toward a heat pump installation. Eligibility and details are confirmed by the estimator — the agent must not quote eligibility rules. If asked, say: "The estimator will talk you through the grant and eligibility."

## Call Type Classification Hints

| Customer says… | Classify as… |
|---|---|
| "No heating", "no hot water", "boiler's not working" | Boiler Breakdown |
| "Annual service", "yearly service", "boiler service due" | Annual Boiler Service |
| "CP12", "landlord certificate", "gas safety certificate" | Landlord Gas Safety Certificate |
| "New boiler", "replace my boiler", "boiler quote" | New Boiler Quote → estimator callback |
| "Heat pump", "air source", "BUS grant" | Heat Pump Enquiry → estimator callback |
| "Radiator cold", "pressure dropping", "TRV" | Radiator / Pressure Issue |
| "Thermostat not working", "Hive broken", "controls" | Thermostat / Controls Issue |
| "Water leaking", "dripping", "puddle" | Leak → safety triage first |

## Vulnerable Customer Signals

Treat as vulnerable (prioritise same-day or next-day slots) if the customer mentions:
- Elderly or living alone
- Disabled
- Young baby in the house
- Cold house with no alternative heating
- Medical condition affected by cold

Do not ask directly. Listen for cues and set the flag silently.

## Out-of-Hours Behaviour

Calls outside {{opening_hours}} are still answered by Tom. The same flow applies. Out-of-hours call-out fee is higher than the weekday fee — the exact amount is returned by the `get_call_out_fee` tool when the customer asks. If no engineer is available for an out-of-hours slot, offer the earliest next-day slot and escalate if the customer insists.

## What the Knowledge Base Does NOT Contain

- **Part-level diagnostics** (no "diverter valve", "PCB", "thermistor" as causes)
- **Repair procedures** (no step-by-step fix instructions)
- **Error code dictionaries** (codes are captured verbatim only)
- **Pricing for repairs** (never quoted — only the call-out fee is stated, and only by reading the `get_call_out_fee` tool response verbatim)
- **DIY advice** (no "try resetting it", "bleed the radiator")

If the agent cannot find a relevant entry in this Knowledge Base, the correct response is: "I'll have the engineer look at that when he's with you."
