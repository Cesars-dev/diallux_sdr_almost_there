# Retell Multi-Prompt Agent — Authoring Rules

Based on hands-on build of a 3-state HVAC booking agent.

---

## 0. Variables — Type Schema

Every variable in `extract_dv` must declare a type. Retell supports exactly these:

| Type | JSON Schema | Example |
|------|-------------|---------|
| `text` | `{ "type": "text" }` | `"customer_name": "Linda Patel"` |
| `boolean` | `{ "type": "boolean" }` | `"greeting_exchanged": true` |
| `enum` | `{ "type": "enum", "enum_options": ["a", "b"] }` | `"classified_intent": "booking"` |
| `number` | `{ "type": "number" }` | `"age": 42` |

### Rules
- Use `text` for names, addresses, postcodes, categories, briefs
- Use `boolean` for flags (exchanged, confirmed, clear, closed)
- Use `enum` when the value must be one of a fixed set (intent types)
- Use `number` rarely — only for numeric data (quantities, ages)

### Critical: variable names must be EXACTLY the same in three places
```
extract_dv variable name  ===  {{variable_name}} in prompt  ===  edge schema required array
```

If they mismatch, the variable won't resolve in the prompt or the transition won't trigger.

### Scoping strategy (from the build)
One `extract_user_details` in `general_tools` with ALL variables. Each state also gets a scoped function with only its relevant subset — this guides the LLM on what to extract when.

```
general_tools:
  extract_user_details (ALL 17 variables)

states[0].tools:
  extract_user_details (greeter subset: greeting_exchanged, customer_name, intent_clear, intent_confirmed, classified_intent, past_customer)

states[1].tools:
  extract_address_details (address subset: customer_name, problem_category, symptom_brief, error_code, boiler_make, address_postcode, address_line1, address_city, address_confirmed)

states[2].tools:
  (booking state uses general_tools extract_user_details + cal tools)
```

---

## 1. Full API Payload

```json
{
  "model": "gpt-5.4",
  "model_temperature": 0,
  "model_high_priority": true,
  "tool_call_strict_mode": true,
  "knowledge_base_ids": ["<kb_id_1>", "<kb_id_2>"],
  "kb_config": {
    "top_k": 3,
    "filter_score": 0.6
  },
  "begin_message": "British Heat Services, Tom speaking — how can I help?",
  "begin_after_user_silence_ms": 2000,
  "starting_state": "greeter",
  "default_dynamic_variables": {},

  "general_prompt": "Shared prompt text for all states...",
  "general_tools": [
    { "type": "end_call", "name": "end_call", "description": "End the call." },
    {
      "type": "extract_dv",
      "name": "extract_user_details",
      "description": "Extract user details when volunteered",
      "variables": [
        { "name": "customer_name", "type": "text" },
        { "name": "past_customer", "type": "boolean" },
        { "name": "classified_intent", "type": "enum", "enum_options": ["booking", "quote", "other"] }
      ]
    }
  ],

  "states": [
    {
      "name": "greeter",
      "state_prompt": "...",
      "edges": [{ "destination_state_name": "address", "description": "Transition when fields populated" }],
      "tools": []
    }
  ]
}
```

## 2. Core Architecture

```
general_prompt (always active)
  + general_tools: tools available in EVERY state (end_call, extract_user_details)
  + states[]:
      - name: "greeter"       (starting_state)
        state_prompt: ...
        edges: [{destination_state_name, description}]
        tools: [state-scoped extract_dv or cal tools]
      - name: "address"
        state_prompt: ...
        edges: [{destination_state_name, description}]
        tools: [state-scoped tools]
      - name: "booking"
        state_prompt: ...
        edges: []  // terminal state
        tools: [cal tools]
```

- `general_prompt` — identity, voice, rules, KBs, emergency scripts
- `states[]` — each state has its own focused prompt
- `edges[]` — defines possible transitions (platform checks required fields automatically)
- `starting_state` — entry point
- `general_tools` — tools like `extract_user_details` with ALL variables available everywhere

---

## 2. Variable Handling (Critical)

### Variables survive across states
Once extracted via `extract_dv`, the variable is available in EVERY subsequent state as `{{variable_name}}`. No need to pass them manually.

### You do NOT list what exists in Context sections
Retell injects all extracted variables automatically. Do NOT add "Context from Previous States" tables — they confuse the LLM and duplicate what the platform already does.

### You do NOT add "transition" instructions in the prompt
The `edges[]` array + required fields on `extract_dv` tools handle transitions. The platform checks if required fields are populated and transitions automatically. No Step 4 "Transition" block needed.

---

## 3. Writing State Prompts

### Structure

```
# State: [name]

# Your Mission Right Now
Brief 3–5 bullet overview of what this state does.

# Variable Extraction
Call [function_name] when the user volunteers information or when the conversation requires it.

# Conversation Flow

## Step 1 — [Name]
CHECK: Does {{variable}} exist?
- YES → Skip to Step 2
- NO → <Sample question?> Call [function] and extract {{variable}}. EXTRACT NOW.

## Step 2 — [Name]
...
```

### Step pattern (NEVER deviate)

```
## Step N — [Name]
CHECK: Does {{variable}} exist?
- YES → Skip to Step N+1
- NO → <Question or prompt> Call [function] and extract {{variable}}. EXTRACT NOW.
```

Rules:
- One `CHECK` per step
- `YES` always skips to the next step number
- `NO` has: the prompt in `<>` + `Call [function] and extract {{vars}}. EXTRACT NOW.`
- Extraction is INLINE on the NO line — never on a separate line below

### When the user volunteers information
If the user offers data before being asked, call `extract_user_details` (or state-scoped function) immediately. The CHECK pattern handles the "don't re-ask" part — once the variable is extracted, YES skips the step.

---

## 4. Edge Schema

### API format (exact)
```json
{
  "name": "greeter",
  "state_prompt": "...",
  "edges": [
    {
      "destination_state_name": "address",
      "description": "Transition when all greeter fields are populated"
    }
  ],
  "tools": [...]
}
```

The `edges` array is ONLY `{destination_state_name, description}`. No schema field.

### What triggers a transition
The platform checks the `required` field list on the `extract_dv` tool definitions. When ALL required variables are populated, the edge activates. The LLM does NOT need to manually "transition" — the platform handles it.

### Terminal states
A state with `edges: []` has no outgoing transitions. The call ends naturally via `end_call` tool.

---

## 5. Tool Definitions

### `extract_dv` — the ONLY way to capture variables

```json
{
  "type": "extract_dv",
  "name": "extract_user_details",
  "description": "Extract user details when they provide them",
  "variables": [
    {
      "name": "customer_name",
      "description": "The customer's full name",
      "type": "text"
    },
    {
      "name": "past_customer",
      "description": "Whether the customer has used our service before",
      "type": "boolean"
    },
    {
      "name": "classified_intent",
      "description": "Why the customer is calling",
      "type": "enum",
      "enum_options": ["booking", "quote", "other"]
    }
  ]
}
```

### Scoping variables per state
- `general_tools` — put `extract_user_details` here with ALL possible variables. Available in every state.
- State `tools` — put scoped `extract_dv` functions (e.g. `extract_address_details` with address-only variables) so the LLM is encouraged to extract the right subset at the right time.
- Duplicate names between general_tools and state tools is fine — they're the same function.

### Tool types used
| Type | Purpose |
|------|---------|
| `end_call` | End the call |
| `extract_dv` | Extract variables from user speech |
| `check_availability_cal` | Check Cal.com availability |
| `book_appointment_cal` | Book Cal.com appointment |

---

## 6. Function Calling — When to Call What

### Call `extract_user_details` / `extract_address_details` when:
- User volunteers any of the tracked variables (name, past_customer, postcode, etc.)
- A conversation step explicitly says `Call [function] and extract {{var}}. EXTRACT NOW.`
- Before transitioning out of a state (to ensure all edge fields are populated)

### Call `check_availability` when:
- Address is confirmed and you're ready to offer slots (booking state Step 1)

### Call `book_calendar` when:
- Customer has verbally confirmed the full booking read-back
- You have the exact UTC start time

### Call `end_call` when:
- Gas emergency confirmed — after offering the emergency number
- Booking complete and warm close delivered
- `{{call_closed}}` has been extracted

---

## 7. Cal.com Tool Configuration

### `check_availability_cal`

```json
{
  "type": "check_availability_cal",
  "name": "check_availability",
  "description": "Check available appointment slots",
  "cal_api_key": "cal_live_xxx",
  "event_type_id": 6389911,
  "timezone": "Europe/London",
  "days_buffer": 1
}
```

### `book_appointment_cal`

```json
{
  "type": "book_appointment_cal",
  "name": "book_calendar",
  "description": "Book a calendar appointment",
  "cal_api_key": "cal_live_xxx",
  "event_type_id": 6389911
}
```

### Exact book_calendar payload (from the build)
```
name: {{customer_name}}
email: noemail@notneeded.com
phoneNumber: {{user_number}}
timeZone: Europe/London
start: <ISO 8601 UTC with Z suffix — e.g. 2026-01-19T10:00:00Z>
title: "{{problem_category}} — {{customer_name}}"
notes: "CUSTOMER: {{customer_name}} | ADDRESS: {{address_line1}}, {{address_city}}, {{address_postcode}} | PHONE: {{user_number}} | PROBLEM: {{problem_category}} | SYMPTOMS: {{symptom_brief}}{{error_code_block}}{{boiler_make_block}}"
```

### Critical payload rules
- `start` MUST have Z suffix (UTC, not local time)
- `email` MUST be `noemail@notneeded.com` (phone-booking system, no email)
- `phoneNumber` MUST be E.164 format (handled by `{{user_number}}` system variable)
- Do NOT add parameters beyond what's listed above

### Variable blocks for notes
- `{{error_code_block}}` = ` | ERROR CODE: {{error_code}}` if exists, else empty
- `{{boiler_make_block}}` = ` | BOILER: {{boiler_make}}` if exists, else empty

---

## 8. The EXTRACT NOW Convention

`EXTRACT NOW` is a marker that tells the LLM "at this point in the conversation flow, call the named function to persist the value the user just provided."

### Rules
- ALWAYS inline on the same line as the prompt — never on its own line
- ALWAYS name the specific function — never just "EXTRACT NOW" alone
- Extraction happens AFTER the user responds, not before

### Correct
```
- NO → <What's your first name?> Call extract_address_details and extract {{customer_name}}. EXTRACT NOW.
```

### Incorrect
```
- NO → <What's your first name?>
Wait for response.
**EXTRACT NOW:** Set {{customer_name}}.
```

### Extraction after volunteered data
If the user offers information before being asked (e.g. "I'm Linda, same as last year"), the LLM should call the function immediately. The prompt's Variable Extraction section covers this:

```
Call extract_user_details when the user volunteers information or when the conversation requires it.
```

---

## 9. Prompt ↔ Function Name Matching

The function name in the prompt MUST match the `name` field in the tool definition.

### Tool definition
```json
{
  "type": "extract_dv",
  "name": "extract_user_details",
  "description": "...",
  "variables": [...]
}
```

### Prompt reference
```
Call extract_user_details and extract {{customer_name}}. EXTRACT NOW.
```

### Naming conventions used in the build
| Tool name | Purpose | State |
|-----------|---------|-------|
| `extract_user_details` | All variables (in general_tools) | Every state |
| `extract_user_details` | Greeter subset (in state tools) | Greeter |
| `extract_address_details` | Address subset (in state tools) | Address |
| `check_availability` | Cal.com slots | Booking |
| `book_calendar` | Cal.com booking | Booking |
| `end_call` | End conversation | Every state |

---

## 10. Structured Schema on Prompt When Calling a Function

When the prompt tells the LLM to call a function, the instruction includes:
1. The trigger condition (when to call)
2. The exact function name (what to call)
3. The variables to extract (what to pass)

### Pattern
```markdown
Call [function_name] and extract [variable_list]. EXTRACT NOW.
```

### Examples from the build
```
Call extract_user_details and extract {{greeting_exchanged}} and {{customer_name}}. EXTRACT NOW.

Call extract_address_details and extract {{symptom_brief}} and {{problem_category}}. EXTRACT NOW.

Call extract_user_details and extract {{selected_slot}}. EXTRACT NOW.
```

### For non-extract functions (end_call, check_availability, book_calendar)
```
Then call `end_call`.

Call `check_availability` for the next 7 days.

Calculate UTC time. Call `book_calendar` with the exact payload.
```

The function name is always in backticks or plain text — never in `< >`.

---

## 11. Sample Phrases Convention

```
When you see text between `<` and `>`, that is a sample phrase. Do not say it verbatim — use variations of the idea.

<Sorry, I didn't quite catch that — could you say it again?>
  - Sorry, I missed that — can you repeat it?
  - Didn't catch that — say it again?
  - One more time?
```

- `< >` = sample phrase, never say verbatim — use variations
- `" "` = approved vocabulary ("right", "lovely") or critical verbatim ("Are you smelling gas?")
- `< >` is ONLY used in conversation flow steps (where LLM speaks to customer)
- Do NOT use `< >` in rules, tool descriptions, customer examples, or "What You Never Do" sections

---

## 12. What NOT to Do

### ❌ DO NOT add "Context from Previous States" sections
Variables flow between states automatically via the platform. Listing them in the prompt adds noise.

### ❌ DO NOT add "Transition" steps in conversation flow
The edge schema + platform handles transitions. No `## Step 4 — Transition` block needed.

### ❌ DO NOT add JSON Schema blocks inside prompt files
They belong in the API payload or separate reference files.

### ❌ DO NOT add "Variables to be set during this state" lists
The `extract_dv` function definition in the API payload documents this. The prompt should only say "Call [function] when the user volunteers information."

### ❌ DO NOT write extraction as separate lines
```
WRONG:
Wait for response.
**EXTRACT NOW:** Set {{variable}}.

RIGHT:
- NO → <Question?> Call [function] and extract {{variable}}. EXTRACT NOW.
```

### ❌ DO NOT duplicate variable descriptions in every extraction call
Just say `Call [function] and extract {{var}}`. The types and descriptions live in the tool definition.

---

## 13. The CHECK Pattern (Solidified)

```
CHECK: Does {{variable}} exist?
- YES → Skip to Step N+1
- NO → <What's your first name?> Call extract_address_details and extract {{customer_name}}. EXTRACT NOW.
```

- ONE variable per CHECK (or logical group like `problem_category` + `symptom_brief`)
- YES always skips forward (never loops back)
- EXTRACT NOW is always inline at the end of the NO line
- Function name is ALWAYS explicit — never say "EXTRACT NOW" without naming the function

---

## 14. Gas Emergency Pattern

```
**CRITICAL — if you are about to route the user to an emergency action, first ask: "Are you smelling gas?"**

- **YES** → Offer the emergency number, then call `end_call`
- **NO or unsure** → Apologize and continue with the normal flow

Emergency number to offer:
<sample emergency message>

Do not attempt to book. Do not diagnose. Do not ask follow-up questions.
```

Binary branch. Clear YES/NO. Never ambiguous.

---

## 15. Edge Case: Booking Failure

If a tool call fails (e.g. `book_calendar` fails twice), the LLM needs a fallback instruction so it doesn't get stuck. Always include:

```
### On Failure (Second Time)
<fallback message for customer>
Then continue to Step N to close the call.
```

This ensures `call_closed` gets extracted and the call ends gracefully even if the booking failed.

---

## 16. Company Config

For single-company demos, hardcode values directly in the prompt text:

```
- Company: British Heat Services
- Gas Safe Reg No: GB-123456
- Region served: Newcastle upon Tyne
- Engineers: Dave, Steve, Mark
- Opening hours: Mon-Fri 8am-6pm, Sat 9am-1pm
- Years in business: over 5
```

For multi-company, replace with `{{variable}}` placeholders and inject via `retell_llm_dynamic_variables`.

---

## 17. General Prompt vs State Prompt

### General prompt (shared — always loaded)
Contains everything the LLM needs regardless of state:
- Identity and role ("You are Tom...")
- Voice and tone rules (short sentences, one question per turn)
- Knowledge boundary rules (rely on KBs, do not invent)
- Diagnostic restraint (do not diagnose, do not name parts)
- Fee rules (only state if asked)
- Emergency scripts (gas leak gate)
- Trade vocabulary (say/never say)
- What You Never Do list
- Tone target
- Sample Phrases convention with examples
- Variable Handling — multi-state persistence explanation
- Company briefing (hardcoded or {{}} placeholders)
- Knowledge Bases Linked list

### State prompt (loaded per state)
Contains ONLY what is relevant to THAT state:
- Mission (2-5 bullets of what this state does)
- Variable extraction instruction (one-line: "Call [function] when user volunteers or conversation requires")
- Conversation flow steps with CHECK patterns
- State-specific rules (e.g. postcode hyphenation for address)
- State-specific edge cases
- State-specific critical rules

### What NEVER goes in a state prompt
- Identity/role (in general prompt)
- Voice/tone rules (in general prompt)
- Knowledge boundary (in general prompt)
- Fee rules (in general prompt)
- Trade vocabulary (in general prompt)
- Company briefing (in general prompt)
- KB references list (in general prompt)
- Variable handling explanation (in general prompt)

---

## 18. System Variables (Available Automatically)

These are injected by Retell without any extraction:

| Variable | Description |
|----------|-------------|
| `{{current_agent_state}}` | Current state name |
| `{{previous_agent_state}}` | Previous state name |
| `{{current_time}}` | Current time in agent timezone |
| `{{current_time_[timezone]}}` | Current time in specified timezone (e.g. `{{current_time_Europe/London}}`) |
| `{{current_calendar}}` | 14-day calendar view |
| `{{current_calendar_[timezone]}}` | Same, in specified timezone |
| `{{current_hour}}` | Current hour as fraction |
| `{{session_type}}` | `voice` or `chat` |
| `{{session_duration}}` | How long the session has been running |
| `{{user_number}}` | Caller's phone number (phone calls only) |
| `{{agent_number}}` | Agent's phone number |
| `{{call_id}}` | Current call ID |
| `{{direction}}` | `inbound` or `outbound` |

Use these directly in prompt text: `<It's {{current_time_Europe/London}} right now.>`

---

## 19. `begin_message` Rules

- `begin_message` plays BEFORE the first state loads
- The LLM is already in `starting_state` when `begin_message` fires
- After `begin_message` plays, the state prompt takes over
- The greeter's Step 1 CHECK should handle `greeting_exchanged` in case the LLM re-enters — but on first entry, the `begin_message` already greeted
- Keep it short (one sentence)

---

## 20. Knowledge Base Config

```json
{
  "knowledge_base_ids": ["kb_id_trade", "kb_id_address"],
  "kb_config": {
    "top_k": 3,
    "filter_score": 0.6
  }
}
```

- `top_k`: how many relevant chunks to inject per turn (default 3)
- `filter_score`: minimum relevance threshold (default 0.6)
- KBs are automatically retrieved when conversation hits relevant terms
- KB content appears in the LLM context as retrieved text
- The LLM does NOT choose which KB to query — the platform does it automatically

### In prompt text, reference KBs by name with double hashes:
```
Everything you say about the trade must come from the linked KBs:
`##uk-hvac-trade-kb##` and `##uk-address-kb##`.
```

---

## 21. The Caching Bug (Critical)

**NEVER use `PATCH /update-retell-llm`.** Retell's API stores the update but does NOT propagate it to runtime. New chat agents created after the update still use the OLD cached prompt.

**Always create a NEW LLM** via `POST /create-retell-llm` with the updated prompt.

This affects both `general_prompt` and `states` arrays.

---

## 22. State Machine Behavior

- The LLM is always in exactly ONE state at a time
- Each state loads: `general_prompt` + that state's `state_prompt` + that state's `tools`
- When all required `extract_dv` fields for the current state's edge are populated, the platform offers the transition
- The LLM can request a transition via the edge definition
- On transition: the new state's prompt + tools load, but ALL extracted variables persist
- `{{previous_agent_state}}` reflects the state you just left
- Terminal states (no edges) stay active until `end_call`

### The LLM does NOT need to:
- Manually track which state it is in ({{current_agent_state}} is always available)
- Ask for permission to transition (the platform gates it on required fields)
- Re-extract variables from previous states (they persist automatically)

---

## 23. Extraction Rate

- Call `extract_dv` when the user volunteers new information
- Call `extract_dv` at key transition points (after customer answers a question)
- Do NOT call `extract_dv` every single turn — 2-3x per state is enough
- The function only stores populated fields — empty fields are ignored
- Over-extracting creates unnecessary API calls and token usage

---

## 24. `tool_call_strict_mode`

```json
{
  "tool_call_strict_mode": true
}
```

When true, the LLM MUST call the tool with the EXACT parameters specified. It cannot invent parameters. This prevents the LLM from:
- Passing extra fields to `book_calendar`
- Creating variables that don't exist in the tool definition
- Using wrong types (e.g. string instead of boolean)

Always set to `true` for production.

---

## 25. `default_dynamic_variables`

```json
{
  "default_dynamic_variables": {
    "customer_name": ""
  }
}
```

Default values for dynamic variables. If a variable is referenced as `{{customer_name}}` before it has been extracted, this default is used. Useful for preventing `{{}}` resolution errors during the first turn.

---

## 26. Multi-Prompt vs Single-Prompt Decision

| Use Multi-Prompt (`states[]`) when | Use Single-Prompt when |
|------------------------------------|----------------------|
| Conversation has distinct phases | Simple Q&A without phases |
| Each phase needs different tools | Same tools throughout |
| You need different rules per phase | One set of rules covers everything |
| State-specific behaviors needed | 1-2 turns max |
| Complex branching logic | Straightforward flow |
| Each phase has unique failure modes | Single error handling path |

Multi-prompt is worth the complexity when you need focused prompts per phase. For simple agents, single-prompt is simpler and cheaper.
