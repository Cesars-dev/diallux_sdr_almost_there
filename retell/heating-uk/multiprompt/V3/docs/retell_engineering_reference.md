# Retell Engineering Reference — Latency, Extraction Bugs, Architecture

> **Purpose:** The consolidated technical reference for building and debugging voice agents on Retell. Covers the extraction `""` bug, latency debugging, model selection, LLM options tuning, architecture patterns, and platform evolution. Built from canonical Retell docs + community research + production findings.
>
> **Audience:** An AI agent (GLM or similar) helping engineer Retell voice agents. Load this when debugging extraction failures, latency issues, or making architecture decisions.

---

## 1. Platform Architecture Overview

Retell offers three agent architectures. The choice determines everything downstream — tool behaviour, extraction reliability, latency characteristics.

### Single-Prompt Agent
- One comprehensive prompt defines all behaviour
- LLM decides when to call tools and extract variables
- **Limitations at scale:** behavioural drift, function calling issues with 5+ tools, context confusion, maintenance challenges
- **Retell's own threshold:** "Consider using conversation flow agent or multi-prompt agent when your single prompt exceeds 1000 words or uses more than 5 functions."
- **Verdict:** Fine for simple IVR/FAQ. Fails on complex stateful agents. Token load grows linearly with conversation length.

### Multi-Prompt Agent (now tagged "Legacy")
- Conversation organised into a structured tree of states
- Each state has its own focused prompt, state-specific functions, transition logic
- Variables and information flow between states
- **Per-node tool scoping:** only relevant tools available in each state
- **Status:** Tagged "legacy" in 2026. Retell is not adding new features. Not sunset-ted yet — likely 6-12 months before genuine deprecation.
- **Verdict:** Still the most reliable for complex stateful agents today. The "legacy" tag means invest here with eyes open — you'll need to migrate eventually.

### Conversation Flow Agent
- Visual builder with nodes and edges
- Flex Mode compiles the flow into a single structured prompt at runtime
- Extract DV Node provides **deterministic** extraction (fires when flow reaches it, not when LLM decides)
- AI-based edge conditions (LLM-evaluated) for flexible routing
- Logical conditions (`{{ variable == "value" }}`) for deterministic routing
- **Active investment area:** Retell's new features land here first
- **Known issue:** "High Node Transition Inaccuracy" is a tracked QA metric — meaning wrong-node transitions happen often enough to need a metric
- **Verdict:** Fixes the extraction bug by construction but introduces transition reliability issues. Still maturing (Subagent Node migration April 2026).

### The strategic picture
Both Retell and Vapi are independently moving away from pure node-graph state machines:
- **Vapi** is retiring Workflows on August 18, 2026. Their stated reason: *"current AI systems aren't yet capable of acting as truly autonomous agents that can: 1. Maintain awareness of the current node's instructions, 2. Understand all possible next steps and the conditions required to reach them."*
- **Retell** is "legacy-ing" Multi-Prompt and pushing Conversation Flow with Flex Mode (compiles flow to prompt at runtime).

Neither platform has solved the node-graph state machine problem. Both are iterating.

---

## 2. The Extraction `""` Bug — Root Cause and Fix

### The bug

You define an Extract Dynamic Variable tool with N variables. The LLM calls it. Some variables come back as empty strings (`""`). Downstream logic that checks `{{variable}} != ""` fails silently because **Retell treats empty string as "has a value."**

From the canonical Retell docs (`dv.md`):
> *"even an empty string is considered having a value"*

From the Extract DV doc (`dv_extract.md`):
> *"Because the agent chooses when to call the tool, extraction isn't guaranteed to run at an exact point."*
> *"The tool only sets variables it can extract. A value the caller never provides isn't stored, so `{{variable_name}}` stays literal until it's set."*

### Why it happens

Two mechanisms combine:

1. **LLM-decided extraction timing.** In single/multi-prompt, the LLM decides when to call the extract tool. It often calls it early, before all values are present in the conversation.

2. **Multi-variable schema fill.** When the tool has 8 variables, the LLM fills the ones it heard and sends `""` for the rest. The schema requires every field to have a value — there's no "omit" option.

Result: `address_postcode` gets set to `""` before the customer has given their postcode. Now `{{address_postcode}}` evaluates to empty (not literal), and your conditional logic breaks.

### The fix: 3-tool split

**Do not put 8 variables in one extract tool.** Split into multiple small tools, one per conversation stage, each with 2-4 variables max.

**Example for a booking agent:**

| Tool | Variables | When to call |
|---|---|---|
| `extract_customer_identity` | `customer_name` (Text), `is_returning_customer` (Boolean) | After customer gives their name |
| `extract_problem` | `problem_category` (Enum), `symptom_brief` (Text), `error_code` (Text), `boiler_make` (Text) | After symptom intake is complete |
| `extract_address` | `address_postcode` (Text), `address_line1` (Text), `address_city` (Text), `address_confirmed` (Boolean) | After address is given and confirmed |

**Why this works:**
- Each tool fires only when its specific values are present in the conversation
- No more empty-string pollution — the tool doesn't fire until the data is there
- Smaller schemas = faster validation = lower latency
- Per-node tool scoping means each node only sees the tools relevant to it

### Enum types vs Text types

From the docs:
> *"Variable Type – `Text`, `Number`, `Boolean`, or `Enum`. Optional; defaults to `Text`."*
> *"Enum Options – the allowed values, added one per row."*

**Use Enum wherever a finite set exists.** The model can't send `""` for an Enum — it either picks a value or doesn't set the variable. This is a structural defence against empty-string pollution.

Convert:
- `problem_category` (Text) → Enum: `["boiler_breakdown", "annual_service", "cp12", "leak", "controls", "heat_pump", "other"]`
- `classified_intent` (Text) → Enum: `["booking", "quote", "other"]`
- `address_confirmed` (Text) → Boolean
- `is_returning_customer` (Text) → Boolean

### The deterministic alternative: Extract DV Node (Conversation Flow only)

If you move to Conversation Flow, the Extract DV Node fires deterministically — when the flow reaches it, not when the LLM decides. This kills the `""` bug by construction.

Tradeoff: you gain extraction reliability but lose transition reliability (see Section 1).

### Community confirmation

From Retell community search results (r1-r8.json):
- *"Custom function failure to substitute dynamic variable"* — Dec 19, 2025
- *"Custom Function (GET) not receiving arguments from Extract"* — multiple reports
- *"To send it in the URL, you have to extract it before you call the custom function using the extract dynamic variables function, not extract it [inline]"*

The pattern is well-documented in the community. The fix is consistently "split your extraction into smaller, earlier tools."

---

## 3. Latency Debugging

### How to measure latency

Use the Get Call API to pull the per-component latency breakdown:

```bash
curl -X GET "https://api.retellai.com/v2/get-call/CALL_ID" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

The response includes a `latency` object with these components:

| Field | What it measures |
|---|---|
| `e2e` | End-to-end: user stops talking → agent starts talking |
| `asr` | Transcription latency |
| `llm` | LLM call start → first speakable chunk |
| `tts` | TTS trigger → first audio byte |
| `knowledge_base` | KB retrieval latency (only if KB is linked) |
| `llm_websocket_network_rtt` | WebSocket roundtrip (only for custom LLM) |
| `s2s` | Speech-to-speech latency (only for Realtime API models) |

Each component has `p50`, `p90`, `p95`, `p99`, `min`, `max`, `num`, `values`.

**Diagnose by component:**
- If `llm.p50` is high → switch model, trim prompt, split tools, enable Fast Tier
- If `knowledge_base.p50` is high → reduce KB count, lower retrieval chunks, merge KBs
- If `tts.p50` is high → switch voice provider, use lower-latency voice
- If `asr.p50` is high → switch transcription mode, check language settings

### The latency inversion finding

**Observed in production (July 2026):**
- GPT-4.1: ~1400ms — but can't handle complex state machines (drops tool calls)
- GPT-5.1: ~2200ms with 8-variable extract tool — works but slow
- GPT-5.4 fast: ~2800ms — slower than 5.1 on this agent type

**Why GPT-5.4 fast is slower than GPT-5.1 on simple tool-call agents:**

1. **Reasoning mode.** GPT-5.1 has reasoning on by default but is optimised for simple turns. GPT-5.4 fast disables deep reasoning but retains the larger model size — more parameters per token evaluated.
2. **Schema validation overhead.** GPT-5.4 fast is optimised for "complex reasoning with tools" workloads. On simple tool-call turns (extract 3 fields, check availability, book), the larger model has more overhead.
3. **GPT-5.4 fast is right-sized for hard reasoning** (multi-step tool chains, ambiguous instructions). For a 3-state linear booking flow, it's overkill.

**The principle:** Match the model to the workload complexity, not to the "newest is best" assumption.

### The platform overhead growth

Retell has added per-turn overhead in the last 6-8 months:

| Feature added | Per-turn overhead added |
|---|---|
| Flex Mode (Conversation Flow) | ~100-200 tokens of framing |
| Subagent Nodes (April 2026) | Restructured tool scoping with more metadata |
| Extract DV improvements (Enum, Boolean types) | Bigger schema definitions per tool |
| AI QA integration | More telemetry per turn |
| Knowledge Base Instruction (query rewrite) | ~50-100ms condensation pass before retrieval |
| Default structured output enforcement | Stricter schema validation per tool call |
| Dynamic variable type system | Type coercion on every variable read |

**Net effect:** 6 months ago, a multi-prompt turn on GPT-4.1 had ~300-500 tokens of platform overhead. Today, the same turn has ~600-900 tokens. That's the ~800ms you're paying.

This isn't a Retell conspiracy — it's the cost of features. But it means **the same agent that worked on GPT-4.1 six months ago may not work on GPT-4.1 today** because the schema complexity crossed 4.1's reliability threshold.

### Latency targets by use case

| Use case | Target p50 | Target p90 | Acceptable max |
|---|---|---|---|
| Emergency services | <800ms | <1200ms | <2000ms |
| High-volume IVR | <1000ms | <1500ms | <2500ms |
| SMB receptionist (your use case) | <1500ms | <2000ms | <3000ms |
| Complex reasoning agent | <2500ms | <3500ms | <5000ms |

From Retell's QA docs: *"When end-to-end latency is too high (e.g., p50 exceeds 2.5 seconds)"* — that's the threshold where they flag it as a problem. Below 2.5s p50 is "acceptable." Below 1.5s p50 is "good for SMB."

From the broader industry research: *"Real-time voice AI latency above 1,500ms consistently degrades conversational quality."* That's the hard line. Above 1500ms, callers notice. Below 1500ms, it feels natural.

---

## 4. LLM Options Tuning

From the canonical Retell docs (`llm_options.md`):

### Temperature

| Range | Behaviour | Best for |
|---|---|---|
| 0.0 - 0.3 | Highly consistent, deterministic | Function calling, data collection, technical support |
| 0.4 - 0.7 | Balanced | General customer service, sales |
| 0.8 - 1.0 | Creative, varied | Brainstorming, casual conversation |

**For booking agents:** 0.1-0.3. You want deterministic tool calls and data capture.

### Structured Output

> *"Ensures that LLM responses strictly follow predefined schemas, particularly important for reliable function calling. When enabled, the model is constrained to output only valid function calls with all required parameters."*

**Enable for production.** Eliminates missing or malformed function arguments. Trade-off: slightly slower agent configuration saves, less flexibility.

### Fast Tier

> *"Routes your LLM calls through dedicated, high-priority infrastructure. 50% reduction in latency variance, 25% improvement in average response time, 99.9% availability vs 99.5% standard."*

**Cost:** 1.5x the standard rate for your selected model.

**When to use:** High-value customer interactions, demonstrations, sales calls, time-sensitive operations.

**For your use case:** Enable on the demo agent. The 1.5x cost is worth killing p90 spikes. A 3000ms p90 on a demo call is deal-killing; Fast Tier compresses that to ~2000ms.

### Reasoning mode

GPT-5.x models have reasoning enabled by default. For voice agents, **turn it off** unless you're doing complex multi-step reasoning. Reasoning adds 500-2000ms per turn.

Check LLM Options → model settings. If "reasoning" or "thinking" is enabled, disable it for voice.

---

## 5. Model Selection Guide

### The models

| Model | Latency (your agent) | Schema reliability | Best for |
|---|---|---|---|
| GPT-4.1 | ~1400ms | ~85% on 5+ field schemas, ~92-95% on 2-3 field | Simple state machines with small tools |
| GPT-4.1 mini | ~800-1000ms | Slightly weaker than 4.1 | High-volume, low-complexity |
| GPT-5.1 | ~2200ms (8-var tool) / ~1500ms (3-tool split) | ~96%+ on complex schemas | Complex state machines, multi-tool |
| GPT-5.4 fast | ~2800ms on simple tools | ~96%+ | Complex reasoning, multi-step tool chains |

### The architecture principle

**Architecture beats model.** A cheap model in a well-designed state machine beats an expensive model in a bloated single prompt. Every time.

The model isn't the variable you can pull on. Your agent's structure is:
- 8 variables in one extract tool → root cause of the silent-extract bug
- Two KBs firing every turn → 200-400ms overhead
- GPT-5.1 with reasoning on + 8-var schema validation + dual KB retrieval = 2200ms
- Fix any one of those three and you drop to ~1700ms. Fix all three and you're at ~1200ms

### When to use GPT-4.1

GPT-4.1 is viable IF you keep every schema small enough:
- Max 2-3 fields per extract tool
- Enum types everywhere a finite set exists
- 4 nodes minimum (more granular = smaller prompts per node)
- Strict JSON Schema validation on every tool

**Latency: ~1200-1500ms p50.** Cheapest viable option. Best margins.

### When to use GPT-5.1

GPT-5.1 is the safe default for complex state machines:
- Handles 4-5 field schemas reliably (~96%+)
- Better edge-schema evaluation than 4.1
- Works with the 3-tool split architecture

**Latency: ~1500-1700ms p50** (with 3-tool split + single KB + Fast Tier).

### When to use GPT-5.4 fast

Only for genuinely complex reasoning:
- Multi-step tool chains (3+ tools in sequence with branching)
- Ambiguous instructions requiring interpretation
- Long-context synthesis across multiple KB chunks

**Not worth it for a 3-state booking flow.** GPT-5.1 handles that faster.

---

## 6. Architecture Patterns

### Per-node tool scoping

In multi-prompt, each node only sees the tools attached to it. Don't attach all tools to all nodes. The greeter node doesn't need `book_calendar` — only the booking node does.

This reduces schema validation overhead per turn because the LLM only sees relevant tools.

### Small extract tools (2-4 fields max)

The single most impactful architectural decision. Every additional field in an extract tool:
- Increases schema validation time (~50-100ms per field)
- Increases the chance of `""` pollution (more fields the LLM might not have data for)
- Decreases extraction accuracy (more fields = more decisions per call)

**Rule: if you can't fit your extract tool in 4 fields or fewer, split it.**

### Enum types for finite sets

From the docs:
> *"Extract variables as enums to enable reliable branching."*

Enums prevent `""` pollution (the model picks a value or doesn't set the variable) and enable deterministic edge conditions (`{{ problem_category == "boiler_breakdown" }}`).

### Strict JSON Schema validation

From the NutriCoach case study (production voice agent):
> *"Strict tool schemas (strict: true, additionalProperties: false, regex on dates) make the provider reject malformed args at the wire — no parsing fallbacks server-side, no silently-ignored extra fields."*

Use `strict: true` on every tool schema. Reject malformed arguments at the wire. Don't try to fix them server-side.

### Per-node KB assignment

In Conversation Flow, you can attach a specific KB to a specific node. The address KB only loads on the address node. The trade KB only loads on the problem intake node.

This saves ~100-200ms per turn vs loading all KBs every turn.

In multi-prompt, KB assignment is agent-level, not node-level. You can work around this by merging KBs or by using the KB Instruction field to steer retrieval.

### The 4-node MVP structure

For a booking agent (HVAC, dental, salon, etc.):

```
Node 1: Greeter
  - Tool: extract_intent (2 fields: customer_first_name, classified_intent)
  - Job: greet, classify intent, confirm

Node 2: Problem Intake
  - Tool: extract_problem (4 fields: problem_category [Enum], symptom_brief, error_code, boiler_make)
  - Job: 1-3 symptom questions, capture category

Node 3: Address
  - Tool: extract_address (4 fields: address_postcode, address_line1, address_city, address_confirmed [Boolean])
  - Job: capture postcode, read back with TTS-friendly formatting, confirm

Node 4: Booking + Close
  - Tools: check_availability (Retell native), book_calendar (Retell native), end_call (Retell native)
  - Job: offer 1-2 slots, read back full booking, book, close
```

Per-node tool count: 1-3. Per-node prompt size: ~600-1500 tokens. Per-turn total load: ~2500-3500 tokens. Well inside GPT-4.1 and GPT-5.1's effective windows.

---

## 7. QA Metrics for Diagnosis

From the canonical Retell docs (`address_metrics.md`):

### High Tool Call Inaccuracy (Single/Multi-Prompt only)

> *"When the agent calls the wrong tools, misses required tool calls, or passes incorrect arguments."*

**Fix:**
- Spell out when to call which tools (and when not to) in the agent prompt
- Use clear tool names and descriptions
- Add examples for parameters
- Split large tools into smaller focused ones

### High Node Transition Inaccuracy (Conversation Flow only)

> *"When node transitions are inaccurate, the agent is moving to the wrong conversation state."*

**Fix:**
- Clarify transition conditions in node prompts
- Add examples demonstrating correct transition behaviour for edge cases
- Keep transition prompts unambiguous
- Avoid overlapping conditions between nodes

### High Agent Hallucination Rate

> *"When the agent generates incorrect or fabricated information not supported by the conversation context or knowledge base."*

**Fix by type:**
- **Fabrication** (inventing facts): Add correct info to KB or system prompt
- **Contradiction** (conflicting with provided info): Simplify or clarify conflicting instructions
- **Confusion** (misunderstanding user intent): Break complex instructions into simpler steps, use conversation flow nodes

### Low KB Recall

> *"When relevant knowledge base chunks are not being retrieved."*

**Fix:**
- Reduce KB retrieval threshold (more permissive matching)
- Increase number of chunks retrieved
- Improve KB document structure (clear headings, short paragraphs)
- Add explanatory text so related information stays in the same chunk

### High Latency (p50 > 2.5s)

**Fix:**
- Use latency breakdown to find the bottleneck (LLM, TTS, KB, network)
- If LLM: switch to faster model, trim prompt, split tools, enable Fast Tier
- If TTS: choose lower-latency voice provider
- If KB: reduce retrieval chunks, merge KBs, scope per-node
- If tool calls: optimise tool endpoints, reduce response size

### High Overlapping Speech Count

| Scenario | Fix |
|---|---|
| High latency (p50 > 2.5s) | Fix latency first. Users talk over the agent when it's too slow. |
| Normal latency | Decrease agent responsiveness or increase interruption sensitivity. |

---

## 8. Platform Evolution Awareness

### What Retell has added (2025-2026)

Features that add per-turn overhead:
- Flex Mode (Conversation Flow compilation)
- Subagent Nodes (replaced Conversation Node tools, April 2026)
- Extract DV improvements (Enum, Boolean types)
- AI QA integration
- Knowledge Base Instruction (query rewrite step)
- Default structured output enforcement
- Dynamic variable type system

### What's deprecated

- **Multi-Prompt:** tagged "legacy" in 2026. Not sunset-ted. 6-12 months before genuine deprecation likely.
- **ElevenLabs Turbo models:** replaced with Flash equivalents on July 12, 2026. Lower latency.
- **Conversation Node tools:** deprecated April 18, 2026 in favour of Subagent Nodes.

### What's coming

- Conversational Flow is the active investment area
- New features land here first
- Multi-Prompt is in maintenance mode

### How to stay ahead of platform bloat

1. **Monitor your latency weekly.** Use the Get Call API to pull p50/p90 trends. If latency creeps up 200ms in a month, something changed on the platform.
2. **Keep your agent architecture lean.** Small tools, Enum types, strict schemas. The leaner your agent, the more headroom you have against platform overhead growth.
3. **Don't chase new features immediately.** Let them settle for 1-2 months before adopting. The Subagent Node migration (April 2026) is still settling.
4. **Have a migration plan.** If Multi-Prompt gets sunset-ted, know your path to Conversation Flow or Custom LLM. Don't get caught without options.

---

## 9. Quick Reference: Fix Decision Tree

### Symptom: Silent extraction returning `""`
1. Check: how many variables in the extract tool? If >4, split into multiple tools.
2. Check: are any fields Text when they should be Enum/Boolean? Convert.
3. Check: is the tool attached to the right node? Per-node scope it.
4. If still failing: consider moving to Conversation Flow with Extract DV Node (deterministic).

### Symptom: Latency above 1500ms p50
1. Pull the Get Call API latency breakdown. Which component is the bottleneck?
2. If LLM: trim prompt, split tools, disable reasoning, enable Fast Tier, consider cheaper model.
3. If KB: merge KBs, reduce retrieval chunks, scope per-node.
4. If TTS: switch to lower-latency voice (ElevenLabs Flash, not Turbo).
5. If still above 1500ms: the platform overhead is the floor. Consider Custom LLM WebSocket.

### Symptom: Agent calls wrong tool or wrong order
1. Check: are tool names and descriptions clear? Rename if ambiguous.
2. Check: does the prompt spell out when to call which tool? Add explicit triggers.
3. Check: are there too many tools in context? Per-node scope them.
4. Check: is the model capable enough? GPT-4.1 struggles with 5+ tools. Move to GPT-5.1.

### Symptom: Agent gets stuck in a loop
1. Check: is there a tool dedup mechanism? Add SHA1 fingerprint dedup.
2. Check: are there per-tool timeouts? Set 8s for reads, 30s for writes.
3. Check: is there a hard cap on tool hops per turn? Cap at 3.
4. Check: is the prompt circular? "If X, then Y. If Y, then X." Break the cycle.

### Symptom: Agent hallucinates trade details
1. Check: is the KB linked? If not, link it.
2. Check: does the prompt say "only use KB context"? Add the anti-hallucination snippet.
3. Check: is the KB well-structured? Clear headings, short paragraphs, no ambiguous pronouns.
4. Check: is retrieval returning relevant chunks? Use the KB Instruction field to steer retrieval.

---

## Sources

- Retell Extract Dynamic Variables: https://docs.retellai.com/build/single-multi-prompt/extract-dv
- Retell LLM Options: https://docs.retellai.com/build/llm-options
- Retell AI QA Metric Issues: https://docs.retellai.com/ai-qa/address-metric-issues
- Retell Check Actual Latency: https://docs.retellai.com/reliability/check-actual-latency
- Retell Dynamic Variables: https://docs.retellai.com/build/dynamic-variables
- Retell Single/Multi Prompt Overview: https://docs.retellai.com/build/single-multi-prompt/prompt-overview
- Retell Function Calling: https://docs.retellai.com/build/single-multi-prompt/function-calling
- Retell Custom Function: https://docs.retellai.com/build/single-multi-prompt/custom-function
- Retell Knowledge Base: https://docs.retellai.com/build/knowledge-base
- Retell Community: extract variable empty, custom function failure threads
- Production findings: user's HVAC agent on GPT-4.1 / 5.1 / 5.4 fast (July 2026)
