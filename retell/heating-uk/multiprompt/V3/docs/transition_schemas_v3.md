# Transition Schemas (V3 — 5 forward transitions, no backward)

> All transitions use the 2-tool pattern: extract_strings (sets string fields) + trigger_transition (sets boolean). The boolean only fires after the strings are verified non-null.

---

## 1. Greeter → Triage

```json
{
  "destination_state_name": "triage",
  "description": "Transition when greeting is exchanged and intent classified",
  "parameters": {
    "type": "object",
    "properties": {
      "greeting_exchanged": {
        "type": "boolean",
        "description": "Whether greeting has been exchanged"
      },
      "customer_name": {
        "type": "string",
        "description": "The customer's full name"
      },
      "classified_intent": {
        "type": "string",
        "description": "Why the customer is calling",
        "enum": ["booking", "quote", "other"]
      }
    },
    "required": ["greeting_exchanged", "customer_name", "classified_intent"]
  }
}
```

---

## 2. Triage → Address

```json
{
  "destination_state_name": "address",
  "description": "Transition when triage is complete",
  "parameters": {
    "type": "object",
    "properties": {
      "triage_complete": {
        "type": "boolean",
        "description": "Whether triage is complete"
      },
      "problem_category": {
        "type": "string",
        "description": "Category of the heating issue",
        "enum": ["boiler_breakdown", "annual_service", "cp12", "leak", "controls", "heat_pump", "other"]
      },
      "symptom_brief": {
        "type": "string",
        "description": "Brief description of symptoms"
      }
    },
    "required": ["triage_complete", "problem_category", "symptom_brief"]
  }
}
```

---

## 3. Address → Slot Selection

```json
{
  "destination_state_name": "slot_selection",
  "description": "Transition when address is confirmed",
  "parameters": {
    "type": "object",
    "properties": {
      "address_confirmed": {
        "type": "boolean",
        "description": "Whether the customer has confirmed their address"
      },
      "address_house_number": {
        "type": "string",
        "description": "House number or property name"
      },
      "address_postcode": {
        "type": "string",
        "description": "UK postcode or N/A"
      }
    },
    "required": ["address_confirmed", "address_house_number", "address_postcode"]
  }
}
```

---

## 4. Slot Selection → Confirmation

```json
{
  "destination_state_name": "confirmation",
  "description": "Transition when slot is selected",
  "parameters": {
    "type": "object",
    "properties": {
      "slot_selected": {
        "type": "boolean",
        "description": "Whether a slot has been selected"
      },
      "selected_slot_start": {
        "type": "string",
        "description": "ISO 8601 UTC with Z suffix"
      }
    },
    "required": ["slot_selected", "selected_slot_start"]
  }
}
```

---

## 5. Confirmation → Booking

```json
{
  "destination_state_name": "booking",
  "description": "Transition when booking is confirmed by customer",
  "parameters": {
    "type": "object",
    "properties": {
      "booking_confirmed": {
        "type": "boolean",
        "description": "Whether the customer has confirmed the booking"
      },
      "booking_slot_string": {
        "type": "string",
        "description": "The final ISO 8601 UTC string for Cal.com"
      }
    },
    "required": ["booking_confirmed", "booking_slot_string"]
  }
}
```

---

## Notes

- **No backward transitions.** Retell multi-prompt is linear. If the customer wants to change a value, use the upsert pattern: call the same extract tool again with the new value. Retell overwrites the variable. The agent stays in the current state.
- **Verbatim variable names.** Each variable name must match exactly across all tools that touch it. `customer_name` is the same in greeter, triage (if used), and booking pre-flight. `selected_slot_start` is the same in slot_selection and confirmation. `booking_slot_string` is the same in confirmation and booking. This is what makes upsert work.
- **Booleans are separate tools.** `greeting_exchanged`, `triage_complete`, `address_confirmed`, `slot_selected`, `booking_confirmed` are each in their own `trigger_*_transition` tool. They can only fire after the string extract tool has been called and verified. This prevents accidental transitions.
