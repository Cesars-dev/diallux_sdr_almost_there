# Post-Testing Feedback — Changes & Fix Tracking

Based on Phase 1 broad test (18 scenarios) against agent `agent_6226cbd3e8292efd1fea0581d8` / LLM `llm_ef59f3282d8546646e16c03568f0`.

---

## P0 — Booking Email Kills Every Reservation

**S16** — `book_calendar` called with `noemail@notneeded.com` → Cal.com rejects it: `"email_domain_cannot_receive_mail"`. S01 only worked because the agent randomly used `john@example.com` on the second try.

**Fix — Two places:**

**A. Booking state prompt** — replace all 3 occurrences:
```
email: noemail@notneeded.com  →  email: jaydiallux@gmail.com
- `email` MUST be `noemail@notneeded.com`  →  - `email` MUST be `jaydiallux@gmail.com`
- **Use `noemail@notneeded.com`** for the email field  →  - **Use `jaydiallux@gmail.com`** for the email field
```

**B. book_calendar tool definition** — change description to include default:
```json
{ "name": "email", "description": "attendee email — use jaydiallux@gmail.com as default", "type": "string", "required": true }
```

---

## P1 — Redundancy: Kill Confirm in Greeter, Move to Address State

**The problem:** The greeter state's "confirm intent" step generates `"[X], got it. So this is for [X], yeah?"` in 8/18 scenarios. The customer just told you what they want — restating it verbatim with "yeah?" is robotic.

**The fix:**

1. **Remove the verbal intent confirmation from the greeter state entirely.** The tool (`extract_user_details`) already extracts `intent_confirmed` silently. No need to say it out loud.

2. **Add a natural confirmation in the address state** — later in the conversation, after the customer has provided more info. One line, not a question you need them to answer:

```
"Just to confirm, this is about [INTENT]. Now, what's the postcode?"
```

This serves two purposes:
- It gives the customer a chance to correct you if the intent was wrong (upsert)
- It sounds natural — you're repeating what you understood, not asking for permission

3. **The `extract_user_details` tool stays in the greeter** — it sets `intent_confirmed` silently on extraction. The LLM doesn't need to verbalize it.

---

## P1 — Address: Segregate into Structured Fields

**The problem:** Address capture is inconsistent across scenarios:
- S01/S16: Asked postcode → house number → confirmed. No street captured. Reads as "14, Newcastle upon Tyne" (sound like apartment, not house).
- S17: Agent invented a "what's the street name?" question that doesn't exist in the tools.
- S15: Address given upfront → ignored entirely.

**Root cause:** The address is captured into a single `address_line1` field (free text). The agent doesn't know what parts it has and what's missing.

**Fix:** Restructure address variables into segregated fields so the agent knows exactly what it has:

```
address_house_number: "14"
address_street: "Victoria Terrace"
address_city: "Newcastle upon Tyne"
address_postcode: "NE4 5AB"
```

Update `extract_address_details` tool to capture these as separate fields. The prompt then reads:
- If `address_house_number` is empty → ask for house number/name
- If `address_street` is empty → ask for street
- If `address_postcode` is empty → ask for postcode
- If `address_city` is empty → derive from postcode or ask

Readback becomes: *"So that's 14 Victoria Terrace, Newcastle upon Tyne — postcode N-E-4-5-A-B."*

---

## P1 — S17: Slot Rejection Flow

Replace the open-ended "If flexible" branch with a structured 5-offer max → hard stop → callback:

```
## Slot Rejection Flow — HARD RULE

1. Reject → ask: <Right, which day works for you this week?>
2. Call `check_availability` for a 24hr window around their answer.
3. Offer 2 slots: <I've got [DAY] morning or [DAY] afternoon — which suits?>
4. If vague → ask: <Morning or afternoon? Pick one.>
5. MAX 5 slot offers TOTAL. Count them.
6. AFTER 5TH: <We'll have someone reach out to sort a time.>
   Set `callback_requested` = true. Close. End call.
   No open-ended questions.
```

---

## P1 — S12: Repair Cost Refusal

Add as CRITICAL OVERRIDE at top of general prompt with exact refusal script. Current behavior asked "What sort of leak is it?" instead of refusing.

---

## P2 — S15: Address Extraction in Greeter

Add `extract_address_details` to the greeter state's tool list so when "Rose Cottage, Mill Lane, Hexham" comes in the opener, it can be captured immediately instead of ignored.

---

## Not Our Bugs

### Duplication Bug (S07, S12, S13)
Text repeated twice: *"Are you smelling gas? Are you smelling gas?"* — this is a Retell generation artifact, not a prompt issue. Needs Retell-side fix (research their docs for text deduplication settings or response post-processing).

### S2 — Postcode Loop
Customer never answered the postcode question after 4 asks (said "Thursday afternoon works" and "Yes, sounds good" instead). Even a human can't guess an address from "same address" — not an agent issue.

---

## Pending: Conversation Hardening

User to provide sample phrases for a customer service rule in the general prompt. Focus on:
- Following the conversation naturally
- Doing task extraction in the background (tools) without it showing in the spoken response
- Non-redundant mirroring
- Acknowledging what the customer actually said, not just the intent

---

## Summary

| Priority | Change | Where |
|----------|--------|-------|
| **P0** | Email: `noemail@notneeded.com` → `jaydiallux@gmail.com` | Booking state prompt (3x) + tool description |
| **P1** | Remove verbal intent confirm from greeter | Greeter state prompt |
| **P1** | Add natural "just to confirm" line in address state | Address state prompt |
| **P1** | Segregate address into structured fields (number, street, city, postcode) | `extract_address_details` tool + address state prompt |
| **P1** | S17: Structured 5-offer max → callback flow | Booking state prompt |
| **P1** | S12: Add repair cost refusal to CRITICAL OVERRIDE | General prompt |
| **P2** | Add `extract_address_details` to greeter state tools | Greeter state config |
| **—** | Fix duplication bug | Retell-side (not a prompt fix) |
| **—** | S2 postcode loop | Not an issue — customer never answered |
