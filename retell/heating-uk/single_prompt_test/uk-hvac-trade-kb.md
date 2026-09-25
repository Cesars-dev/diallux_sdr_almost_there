# UK HVAC Trade — Knowledge Base

> This file gives the agent category-level understanding of UK HVAC issues — enough to sound savvy and capture the right info, not enough to diagnose. There are no part-level causes, no repair procedures, no error-code dictionaries. GPT-5.4 handles the wording naturally.

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

When a customer mentions any of these, capture the brand name.

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
Customer wants to replace an old boiler or install a new one. Capture property type and timeline. Route to estimator callback.

### Heat Pump Enquiry
Customer is interested in a heat pump, often because of the Boiler Upgrade Scheme grant. Capture property type. Route to estimator.

### Radiator / Pressure Issue
Customer reports cold radiators, pressure dropping, or TRV problems. Book as a breakdown call.

### Thermostat / Controls Issue
Customer reports problems with the thermostat, programmer, or smart controls. Book as a breakdown call.

### Leak
Customer reports water leaking from the boiler, a pipe, or a radiator. Run safety triage — if it's a major leak, advise turning off the stopcock. Book as a breakdown call.

## Symptom Categories — Identification Context Only

> Each entry describes what the customer's words likely point to. Use this context to understand what they're experiencing. Let the customer describe it in their own words.

### No Heating and Hot Water
The boiler isn't producing any heat at all. Questions to ask: "Is the boiler showing an error code, or is the display blank?" "When did it start?" "Have you checked the pressure gauge?"

### No Hot Water (but heating works)
Heating works but hot water taps run cold. Questions to ask: "Is it completely cold, or does it run hot then cold?" "Does it happen on every tap, or just one?"

### Intermittent Heating
Heating cuts out or fails to reach temperature. Questions to ask: "Does it cut out after a few minutes, or never quite reach temperature?" "Any pattern — mornings, evenings?"

### Banging / Kettling / Rumbling Noise
Unusual sounds from the boiler or pipes. Questions to ask: "Is it when the boiler fires up, or while it's running?" "How loud?"

### Cold Spots on Radiators
Some radiators are cold at the top or on one side. Questions to ask: "Is it the top of the radiator that's cold, or just one side?" "Is it all radiators, or just one?"

### Pressure Loss
The boiler pressure gauge keeps dropping. Questions to ask: "What's the gauge reading now?" "Have you had to top it up recently?" "Any visible water anywhere?"

### Error Code on Display
The boiler screen shows an error code. Questions to ask: "Can you read the code back to me exactly as it appears?" "Is it flashing, or steady?" Capture the code verbatim.

### Boiler Not Firing / No Ignition
The boiler doesn't fire up at all when turned on. Questions to ask: "Is there any sound at all when you turn it on — a click, a fan, anything?" "Has the pilot light gone out, if you have one?"

### Leak from Boiler
Water coming from the boiler unit itself. Questions to ask: "How fast is it dripping?" "Is the water coming from underneath, or higher up?" Safety: If the leak is fast, advise turning off the stopcock and the boiler.

### Leak from Pipe or Radiator
Water coming from a pipe joint or radiator. Questions to ask: "Where is the water coming from — a pipe joint, a radiator, or can't you tell?" "How fast?" Safety: If major, advise stopcock off.

### Thermostat / Controls Not Responding
The thermostat or programmer isn't working. Questions to ask: "Is the thermostat completely blank, or just not responding?" "Have you changed the batteries, if it's wireless?"

## Regulatory and Safety Context

### Gas Safe Register
The only legal gas engineer body in the UK. All {{company_name}} engineers are Gas Safe registered. Registration number: {{gas_safe_number}}. The customer can verify an engineer's ID card on arrival.

### National Gas Emergency Service
Phone: **0800 111 999**. Free, 24 hours. For smell of gas, suspected carbon monoxide, or a gas leak. The agent must direct customers to this number immediately.

### Carbon Monoxide Symptoms
Headaches, nausea, dizziness, breathlessness, collapse — especially when the boiler is on and several people in the property are affected. If suspected, advise opening windows, leaving the property, and calling 0800 111 999.

### Landlord Gas Safety Record (CP12)
Annual legal requirement for rental properties in the UK. Engineer inspects gas appliances and issues a certificate. Certificate usually emailed within 24 hours of the visit.

### Boiler Upgrade Scheme (BUS)
Government grant of £7,500 toward a heat pump installation. If asked, say: "The estimator will talk you through the grant and eligibility."

## Call Type Classification

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

Do not ask directly. Listen for cues and flag silently.

## Out-of-Hours Behaviour

Calls outside {{opening_hours}} are still answered. Same flow applies. Out-of-hours call-out fee is higher than weekday fee. If no engineer is available for an out-of-hours slot, offer the earliest next-day slot and escalate if the customer insists.
