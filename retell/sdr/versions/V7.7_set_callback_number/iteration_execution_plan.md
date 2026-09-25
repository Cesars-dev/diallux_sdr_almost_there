# Iteration Execution Plan — surgical patches to V7.7_set_callback_number

> For an execute-only agent. RULES:
> - SURGICAL ONLY. Do not rewrite, reword, or restructure anything beyond the exact strings below.
> - Everything stays verbatim except the specific fields/strings each step names.
> - Do NOT touch any state prompt, KB, tool, or edge that is not listed here.
> - Work on the V7.7 source of truth in place: `Dialux_SDR/V7.7_set_callback_number/`.
> - After all edits: rebuild + parity-check (`tools/build_llm_json.py`), then stop. Do NOT deploy (owner deploys locally).
> - Paths below are relative to `Dialux_SDR/V7.7_set_callback_number/`.

---

## ITER 1 — Phone confirm boolean (standalone native field)

### 1a. Add the `extract_phone_confirmed` tool
File: `tools/contact_details.tools.json`
Insert this object into the tools array, immediately AFTER the `contact_details_completed` tool object (before the `set_callback_number` object):

```json
  {
    "type": "extract_dynamic_variable",
    "name": "extract_phone_confirmed",
    "speak_after_execution": false,
    "description": "Set phone_confirmed to true ONLY when the caller gave a clear positive confirmation of their phone number (a distinct Yes, Right, Correct, or That's right). If the answer is ambiguous or a correction, do NOT set true — ask again.",
    "variables": [
      {
        "type": "boolean",
        "name": "phone_confirmed",
        "description": "true ONLY on a clear positive confirmation of the phone number. false/unset while unconfirmed."
      }
    ]
  },
```

### 1b. Add `phone_confirmed` to the contact_details edge gate
File: `edges/contact_details.edges.json`
- In `parameters.required`, add `"phone_confirmed"` to the array (after `"is_calling_best_number"`).
- In `parameters.properties`, add this property object (after the `is_calling_best_number` property):
```json
        "phone_confirmed": {
          "type": "boolean",
          "description": "true ONLY after the caller gave a clear positive confirmation of their phone number."
        },
```
- In the edge `description` string, append ` and phone_confirmed` before the period: change `…is_calling_best_number are all filled, transition to Booking.` to `…is_calling_best_number, and phone_confirmed are all filled, transition to ConfirmSlots.`

### 1c. Add the confirmation step to the contact_details prompt
File: `prompts/states/contact_details.md`

Replace the step-4 block (lines 20-26) EXACTLY:

OLD:
```
### 4. Phone number (required)
If {{callback_number}} is empty or not real digits, FIRST ask: <What's the best number to reach you?> and capture the exact digits — never store placeholder text.

<And… is the number you're calling from the best contact number to reach you?>

- YES → set {{is_calling_best_number}} = true. The seeded {{callback_number}} stands.
- NO → set {{is_calling_best_number}} = false. <What's the best number to reach you?> Wait for the digits, then call `set_callback_number` with them. Follow the `action` it returns; confirm once: <So that's [number], correct?>
```

NEW:
```
### 4. Phone number (required)
If {{callback_number}} is empty or not real digits, FIRST ask: <What's the best number to reach you?> and capture the exact digits — never store placeholder text.

<And… is the number you're calling from the best contact number to reach you?>

- YES → set {{is_calling_best_number}} = true. The seeded {{callback_number}} stands.
- NO → set {{is_calling_best_number}} = false. <What's the best number to reach you?> Wait for the digits, then call `set_callback_number` with them. Follow the `action` it returns.

Confirm the number slowly, digit by digit: <So that's [read each digit slowly], correct?>
- Clear yes (Yes / Right / Correct) → call `extract_phone_confirmed` and set {{phone_confirmed}} = true.
- Ambiguous or a correction → do NOT set it. Ask again: <So... just to be sure, that's: [phone string]> Repeat until a clear yes, then set {{phone_confirmed}} = true.
```

### 1d. Require phone_confirmed in the completion flag
File: `prompts/states/contact_details.md`
Replace line 57:

OLD:
```
When this stage's work is done, call `contact_details_completed` to set it to true. When first name, last name, company, timezone and best number are all collected and verified. Never mention this flag to the prospect.
```

NEW:
```
When this stage's work is done, call `contact_details_completed` to set it to true. When first name, last name, company, timezone, best number are all collected and verified AND {{phone_confirmed}} is true. Never mention this flag to the prospect.
```

### 1e. Update the completion-flag tool description to mention phone_confirmed
File: `tools/contact_details.tools.json`
In the `contact_details_completed` tool object, change its `description` and the inner variable `description`:
- OLD description: `Set contact_details_completed to true ONLY after: When first name, last name, company, timezone and best number are all collected and verified. Do not set it early.`
- NEW description: `Set contact_details_completed to true ONLY after: first name, last name, company, timezone, best number are all collected and verified AND phone_confirmed is true. Do not set it early.`
- OLD variable description: `true ONLY after: When first name, last name, company, timezone and best number are all collected and verified.`
- NEW variable description: `true ONLY after: first name, last name, company, timezone, best number are all collected and verified AND phone_confirmed is true.`

---

## ITER 2 — Vary filler phrases, never verbatim (additive notes only)

### 2a. general_prompt.md — sample-explanation note after the ack line
File: `prompts/general_prompt.md`
Find the line:
```
- Acknowledge before moving on: "Got it" "Makes sense" "I hear you"
```
Replace with:
```
- Acknowledge before moving on: "Got it" "Makes sense" "I hear you"
- These acknowledgment phrases are SAMPLES — use them as such. You may read one verbatim once, then use your own variations. NEVER REPEAT A FILLER PHRASE DURING A CALL.
```

### 2b. Booking.md — vary-the-hold-phrase note
File: `prompts/states/Booking.md`
Find line 18:
```
**1. Book:** Say <One moment while I confirm that.> then IMMEDIATELY call `create_livecall_booking`.
```
Replace with:
```
**1. Book:** Say a brief one-line hold phrase (e.g. <One moment while I confirm that.> — vary it, never verbatim twice in one call) then IMMEDIATELY call `create_livecall_booking`.
```

### 2c. Closing.md — vary-the-goodbye note
File: `prompts/states/Closing.md`
Find line 17:
```
<Really glad you called. Jay's looking forward to it. Have a great [rest of your day / evening]. Bye!>
```
Replace with:
```
<Really glad you called. Jay's looking forward to it. Have a great [rest of your day / evening]. Bye!> (Sample — vary the wording, never repeat verbatim in one call.)
```

---

## ITER 3 — Strip all `**` markdown from KBs + prompts (mechanical)

Remove every `**` character from these files (no rewording — just delete the asterisks):

Knowledge bases:
- `Knowledge bases/industry-kb.md` (754 hits)
- `Knowledge bases/pain-points-kb.md` (74)
- `Knowledge bases/sales-psychology-kb.md` (72)
- `Knowledge bases/voice-ai-capabilities-kb.md` (30)

Prompts:
- `prompts/general_prompt.md` (12)
- `prompts/states/Booking.md` (6)
- `prompts/states/Closer.md` (2)
- `prompts/states/Closing.md` (8)
- `prompts/states/ConfirmSlots.md` (8)
- `prompts/states/Offer.md` (6)
- `prompts/states/contact_details.md` (6)

Method: for each file, delete all occurrences of the two-character string `**` (leaving the wrapped text intact, unbolded). Do NOT alter any other characters. Verify zero `**` remain in these files afterward.

NOTE: ITER 2 above deliberately still writes `**1. Book:**` / `**3. Warm goodbye:**` style headers — those `**` get removed by THIS step (Iter 3 runs after Iter 2). Final state: no `**` anywhere in prompts/ or KBs.

---

## ITER 5 — Fix phantom-close (ConfirmSlots misnomer + constraint)

### 5a. Fix the false "transition_to_Booking" wording in ConfirmSlots
File: `prompts/states/ConfirmSlots.md`
Find line 27:
```
- `slot_verified: true` → `transition_to_Booking`.
```
Replace with:
```
- `slot_verified: true` → `transition_to_VerifyLead` (a data checkpoint — NOT a booking).
```

### 5b. Add a CRITICAL CONSTRAINT block at the bottom of ConfirmSlots
File: `prompts/states/ConfirmSlots.md`
Append after the last line of the `# Critical Rules` block (after line 37):
```

# CRITICAL CONSTRAINT
- Never commit to a booking here. You are just pulling a slot and confirming it with the user. You do not book here, you never promise a booking here — you only confirm the slot and any additional details when needed.
```

### 5c. (adjacent same-class fix) Correct the misnomer in contact_details.md
File: `prompts/states/contact_details.md`
Find line 58:
```
Then call `transition_to_Booking` once the completion flag is set.
```
Replace with:
```
Then call `transition_to_ConfirmSlots` once the completion flag is set.
```
(The real edge destination from contact_details is ConfirmSlots, not Booking — same hallucination class as 5a.)

---

## ITER 6 + ITER 4 — leave as TO-DO for prod (no code/endpoint edit)

File: `manual_iterations.md`
- Iter 6 status line: change `**Status:** DEFERRED — endpoint architecture deep-dive scheduled for tomorrow. DO NOT fix now.` to `**Status:** TO-DO for prod — not in this batch. Revisit when concurrent load is real.`
- Iter 4 status line: change `**Status:** NOT BUILT — tracked option only. Skip for now at 10 calls/day. Revisit only if collisions actually show up.` to `**Status:** TO-DO for prod — nice-to-have, not in this batch. Revisit only if slot collisions appear.`

No edits to `cal_slots_endpoint/` or any endpoint code.

---

## NOTE 7 — Purge fake 555 numbers from test personas

Files:
- `testing/test_llm_to_llm.py` (regular PERSONAS)
- `testing/runners/adversarial_suite.py` (adversarial personas)
- `/tmp/opencode/adversarial_suite.py` (mirror — keep in sync)

Rule: replace every phone number that contains the exchange `555` with a real, Cal-acceptable non-555 number. Use the existing real-number pattern already in the file (e.g. `+15123120001`, `+13039150001`, `+19172120001` — valid area code [2-9], non-555 exchange, 10 digits). Keep personas — do NOT delete any (none exist purely to test fake numbers; their agendas are objection/pressure/waffle/etc.). Update BOTH the `dynvars.callback_number` value AND any in-text reference to that number so they match.

Specific replacements (dynvar + text):
- `+13125551234` → `+13124001234`
- `+16025550017` → `+16024000017`
- `+18165550022` → `+18164000022`
- `+12065550033` → `+12064000033`
- `+14695550001` → `+14694000001`
- `+17185550002` → `+17184000002`
- `+13055550003` → `+13054000003`
- `+16025550004` → `+16024000004`
- `+16175550005` → `+16174000005`
- `+12125550006` → `+12124000006`
- `+12125550007` → `+12124000007`
- `+12125550008` → `+12124000008`
- `+12125550009` → `+12124000009`
- `+12125550010` → `+12124000010`
- `+12125550011` → `+12124000011`
- `+12125550012` → `+12124000012`

Also: in persona instruction text, replace any literal `555-000-0000` / `555` mention in a phone context with the new non-555 number. Keep the anti-555 guard sentences ("NEVER use a 555 number") — they are harmless and reinforce the intent.

After editing, verify: `grep -n "555" testing/test_llm_to_llm.py testing/runners/adversarial_suite.py` should return ONLY the "NEVER use a 555 number" guard sentences (no 555 in any actual phone value).

---

## FINAL — rebuild + verify (do NOT deploy)

```bash
cd Dialux_SDR/V7.7_set_callback_number
python3 tools/build_llm_json.py          # rebuilds llm.json from prompts/tools/edges; prints parity check
python3 tools/build_llm_json.py --check   # confirm parity, no write
```
- Confirm `build_llm_json.py` reports parity OK and no errors.
- Do NOT run `deploy_v68.py` — the owner deploys locally.
- Update `manual_iterations.md`: mark Iter 1, 2, 3, 5 and NOTE 7 as DONE; Iter 4, 6 as TO-DO for prod (per their status edits above).
- Update the STATUS block: note that surgical patches landed, rebuild done, awaiting local deploy + acceptance re-run.

## DONE CONDITIONS
- `grep -rn '\*\*' prompts/ "Knowledge bases/"` → zero hits.
- `grep -n "555" testing/test_llm_to_llm.py testing/runners/adversarial_suite.py` → only guard sentences.
- `prompts/states/ConfirmSlots.md` contains `transition_to_VerifyLead` and the `# CRITICAL CONSTRAINT` block; no `transition_to_Booking` remains in ConfirmSlots.
- `tools/contact_details.tools.json` contains `extract_phone_confirmed`; `edges/contact_details.edges.json` requires `phone_confirmed`.
- `build_llm_json.py --check` → parity OK.
