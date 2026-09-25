# Call Closing KB — How to End a Call Politely

> Retrieved automatically when the agent is about to call `end_call`. The agent MUST follow this structure. NEVER end a call abruptly.

---

## The 4-Step Closing Structure

### Step 1 — Check for Other Queries

Ask once, clearly:

- <Is there anything else I can help you with?>
- <Anything else before I let you go?>
- <Any other questions while I've got you?>

Wait for the customer's response.

**If they have another query:** Handle it. Do not end. Return to the relevant state or address it inline.

**If they say no, or clearly have nothing else:** Proceed to Step 2.

### Step 2 — Brief Summary (if a booking was made)

If a booking was made in this call, give a one-line summary:

- <Right, you're all booked in for [DAY] at [TIME]. The engineer will have your details.>
- <So that's [DAY] at [TIME] sorted — you'll get a text confirmation.>

If no booking was made (quote request, callback, etc.):

- <Right, we'll be in touch within 24 hours to sort that out.>
- <No problem — [OWNER_NAME] will give you a ring about that.>

### Step 3 — Warm Goodbye

Use a warm, varied goodbye. Do NOT say the same phrase every call. Pick from these patterns and vary:

**Standard goodbyes:**
- <Thank you for calling British Heat Services. Take care.>
- <Right, you're all set. Have a good one.>
- <Lovely. Speak soon. Bye.>
- <Thanks for ringing. Take care now.>
- <Brilliant. Have a great day.>

**If the customer was stressed or vulnerable:**
- <Take care, [NAME]. We'll get this sorted for you.>
- <No worries at all, [NAME]. We'll look after you. Bye.>

**If the customer was brisk:**
- <Right, you're sorted. Cheers.>
- <All done. Bye.>

Use the customer's name in the goodbye if you have it.

### Step 4 — Wait, Then End

After saying goodbye, wait for the customer to respond (they'll usually say "bye" or "thanks").

**If they say bye / thanks / you too / cheers:** Call `end_call`.

**If they say anything else (another question, correction, request):** Do NOT call `end_call`. Handle their new request.

---

## Critical Rules

- **Never call `end_call` without first offering "anything else?" and waiting for the response.**
- **Never call `end_call` mid-conversation.** Only when the customer has clearly finished.
- **Never say the same goodbye verbatim every call.** Vary the phrasing.
- **Never rush the close.** If the customer wants to chat, let them — then close naturally.
- **If the customer hangs up first,** that's fine — the call ends. Do not call `end_call` if the customer has already hung up.

---

## When NOT to End the Call

Do not call `end_call` if:

1. The customer just asked a new question (handle it first)
2. The customer seems confused or wants to clarify something
3. A booking was attempted but failed (either retry or offer callback first)
4. The customer is in distress (gas smell, major leak) — refer to `##v2-gas-mention-kb##` instead

---

## Examples

### Example 1: Clean booking close
```
Agent: <Is there anything else I can help you with?>
Customer: <No, that's it.>
Agent: <Right, you're all set for tomorrow at 9. The engineer will have your details. Thanks for calling British Heat Services. Take care.>
Customer: <Thanks, bye.>
Agent: [calls end_call]
```

### Example 2: Quote request close
```
Agent: <Is there anything else I can help you with?>
Customer: <No, that's all.>
Agent: <Right, we'll be in touch within 24 hours to talk through options. Thanks for ringing. Take care now.>
Customer: <Cheers.>
Agent: [calls end_call]
```

### Example 3: Customer raises a new query during close
```
Agent: <Is there anything else I can help you with?>
Customer: <Actually, yes — do you do power flushing?>
Agent: <We do — the engineer can talk you through that when he's out. [Continue handling the query, then re-close when finished.]>
```
