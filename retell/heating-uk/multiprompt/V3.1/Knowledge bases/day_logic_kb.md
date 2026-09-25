# Day Logic KB — Slot Selection Time Reference

> Retrieved automatically during the slot_selection and confirmation states. The agent MUST follow these rules when offering slots, reading back times, or converting spoken day references to ISO 8601 UTC.

---

## Core Day Definitions

| Customer says | What it means | ISO date calculation |
|---|---|---|
| "Today" | The current date | `{{current_calendar}}` |
| "Tomorrow" | The day after today | `{{current_calendar}}` + 1 day |
| "The day after tomorrow" | Two days from today | `{{current_calendar}}` + 2 days |
| "In a couple of days" | Two days from today | `{{current_calendar}}` + 2 days |

---

## Day of Week Logic

When the customer names a day of the week (Monday, Tuesday, etc.), the agent must determine whether it's THIS WEEK or NEXT WEEK:

### Rule: "Next [Day]" vs "[Day]"

- **"[Day]" alone** (e.g., "Wednesday") = the NEXT occurrence of that day.
  - If today is Monday and they say "Wednesday" → this Wednesday (2 days from now)
  - If today is Friday and they say "Wednesday" → next Wednesday (5 days from now)
  - If today is Wednesday and they say "Wednesday" → today (same day)

- **"Next [Day]"** (e.g., "next Wednesday") = the occurrence AFTER the next one.
  - If today is Monday and they say "next Wednesday" → Wednesday of the following week (9 days from now)
  - If today is Wednesday and they say "next Wednesday" → Wednesday of the following week (7 days from now)

- **"This [Day]"** (e.g., "this Wednesday") = the occurrence in the current week (Monday-Sunday).
  - If today is Monday and they say "this Wednesday" → this Wednesday (2 days from now)
  - If today is Friday and they say "this Wednesday" → has already passed this week; clarify: "Wednesday's gone this week — do you mean next Wednesday?"

### Week Boundaries

- **"This week"** = from today until the upcoming Sunday
- **"Next week"** = Monday through Sunday of the following week
- **"This weekend"** = the upcoming Saturday and Sunday
- **"Next weekend"** = the Saturday and Sunday of the following week

---

## Time of Day Definitions

| Customer says | What it means |
|---|---|
| "Morning" | 8:00 AM to 12:00 PM |
| "Afternoon" | 12:00 PM to 5:00 PM |
| "Evening" | 5:00 PM to 8:00 PM (if the company offers evening slots) |
| "Late morning" | 10:00 AM to 12:00 PM |
| "Early afternoon" | 12:00 PM to 2:00 PM |

---

## Bank Holidays (UK)

UK bank holidays vary by year and region. The agent should NOT assume a specific date is a bank holiday unless the customer mentions it. If the customer asks about a bank holiday:

- "Are you open on the bank holiday?" → "Let me check what we've got available — one moment."

The agent should treat bank holidays as potentially outside normal working hours. If the calendar (Cal.com) returns no slots for a bank holiday, that's the answer.

---

## Slot Return Format from check_availability

The custom `check_availability` webhook returns each slot with TWO fields. The agent does NOT convert or compute either value — it copies the field verbatim from the returned slot.

| Field | Format | What it is | Use it for |
|---|---|---|---|
| `time` | `YYYY-MM-DDTHH:MM:SS` — Europe/London LOCAL, **no Z, no ms** (e.g. `2026-07-30T09:00:00`) | local calendar time | offering the slot, the spoken label, and the `book_calendar` `time` argument |
| `iso` | `YYYY-MM-DDTHH:MM:SS.000Z` — UTC with **Z** + ms (e.g. `2026-07-30T08:00:00.000Z`) | the same instant in UTC | `selected_slot_start` and `booking_slot_string` |

**Where each field goes (copy verbatim, never reformat):**
- `selected_slot_start` / `booking_slot_string` = the slot's **`iso`** field (UTC, with Z).
- The spoken label (`selected_slot_label`) and the booking `time` value = the slot's **`time`** field (local, no Z).

**Never** use `iso` for booking, and **never** use `time` for `selected_slot_start` — mixing them reintroduces the hour offset.

### UK Time Zones (context — the agent does NOT convert)

- **GMT (winter):** UTC+0 — London time = UTC
- **BST (summer):** UTC+1 — London time = UTC + 1 hour

The webhook already applies this offset. When today is BST, a 9 AM London slot returns `time: 09:00:00` (local) and `iso: 08:00:00.000Z` (UTC). The agent stores `iso` and books with `time`.

---

## Slot Offer Format

When offering slots, ALWAYS use this format:

**"[DAY] at [TIME]"** — never offer a window without a specific time.

Examples (correct):
- "Tomorrow at 9 AM or 10 AM — which suits?"
- "Thursday at 2 PM or 3 PM — which works?"
- "I've got Monday at 11 AM — does that work?"

Examples (WRONG — do not use):
- "Between 1 and 5" ❌ (no day, vague window)
- "Tomorrow afternoon" ❌ (no specific time)
- "Morning or afternoon?" ❌ (no day, no time)

---

## When the Customer Is Vague

If the customer says "any day" or "whenever":

1. Ask: <Morning or afternoon — what works better for you?>
2. Once they pick morning or afternoon, call `check_availability` passing the resolved day as `slot_target_date` (YYYY-MM-DD).
3. Offer the 2 closest specific slots: <I've got [DAY1] at [TIME1] or [DAY2] at [TIME2] — which suits?>

If the customer says "next week":

1. Ask: <What day works best — Monday through Friday?>
2. Once they name a day, call `check_availability` passing that day as `slot_target_date` (YYYY-MM-DD).
3. Offer 2 specific slots on that day.

---

## Critical Rules

- **ALWAYS include the day label** when offering a slot. Never offer a time without a day.
- **ALWAYS use specific times** (9 AM, 2 PM), never vague windows ("between 1 and 5").
- **When the customer names a day**, determine this week vs next week using the rules above.
- **The `iso` field comes from `check_availability`** (UTC, with Z) — use it for `selected_slot_start` / `booking_slot_string`. The `time` field (local, no Z) is for booking. Copy verbatim from the tool result — never convert manually.
- **The spoken label is what the agent said** — store it in `selected_slot_label` for readback in the confirmation state.
