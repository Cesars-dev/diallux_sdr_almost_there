# V2.1 Deployment Plan — New Chat Agent

## Pre-Deployment Audit: V2.1 vs Multi-Prompt Architecture

### Architecture Compliance

| Spec Requirement | V2.1 Status | Notes |
|---|---|---|
| `model` | ✅ gpt-5.4 | Unchanged |
| `general_prompt` | ✅ 4,929 chars | 53% reduction from v1 (7 sections → KBs) |
| `general_tools` | ✅ end_call + extract_general_values | Cross-state general extraction added |
| `states[]` | ✅ greeter → address → booking | 3 states, same flow |
| `starting_state` | ✅ greeter | Unchanged |
| `begin_message` | ✅ "British Heat Services..." | Unchanged |
| `knowledge_base_ids` | ✅ 2 existing KBs linked | +7 new V2.1 KBs to be created |
| `tool_call_strict_mode` | ✅ true | Unchanged |
| `model_high_priority` | ✅ true | Unchanged |

### State Machine Design

States use `parameters` edges with `required` fields — deterministic transitions based on populated dynamic variables.

| State | Edge | Required Vars | Behavior |
|---|---|---|---|
| greeter → address | `transition of greeter prompt.json` | greeting_exchanged, intent_clear, classified_intent | Transitions once intent is classified |
| address → booking | `transition of address prompt.json` | customer_name, problem_category, symptom_brief, address_house_number, address_street, address_line1, address_city, address_confirmed | Transitions once address is confirmed |
| booking → (end) | none | — | Terminal state, ends via end_call |

### Tool Design — Per-State Dedicated Tools

Each state has its own named tool. Variables can overlap across tools by name — the dynamic variable system deduplicates by name.

| Scope | Tool | Variables |
|---|---|---|
| General (all states) | `extract_general_values` | customer_name, address_house_number, address_street, address_line1, address_city, address_postcode |
| Greeter | `extract_greeter_values` | customer_name, classified_intent, greeting_exchanged, intent_clear, past_customer |
| Address | `extract_address_details` | customer_name, classified_intent, problem_category, symptom_brief, error_code, boiler_make, address_house_number, address_street, address_line1, address_city, address_postcode, address_confirmed |
| Booking | `extract_booking_values` | customer_name, booking_confirmed, booking_ref, call_closed, callback_requested |

### Variable Cross-Reference — All Layers

| Variable | General | Greeter | Address | Booking | Greeter Edge | Address Edge |
|---|---|---|---|---|---|---|
| customer_name | ✓ | ✓ | ✓ | ✓ | property | **required** |
| address_house_number | ✓ | — | ✓ | — | — | **required** |
| address_street | ✓ | — | ✓ | — | — | **required** |
| address_line1 | ✓ | — | ✓ | — | — | **required** |
| address_city | ✓ | — | ✓ | — | — | **required** |
| address_postcode | ✓ | — | ✓ | — | — | property |
| classified_intent | — | ✓ | ✓ | — | **required** | — |
| greeting_exchanged | — | ✓ | — | — | **required** | — |
| intent_clear | — | ✓ | — | — | **required** | — |
| past_customer | — | ✓ | — | — | property | — |
| problem_category | — | — | ✓ | — | — | **required** |
| symptom_brief | — | — | ✓ | — | — | **required** |
| error_code | — | — | ✓ | — | — | property |
| boiler_make | — | — | ✓ | — | — | property |
| address_confirmed | — | — | ✓ | — | — | **required** |
| booking_confirmed | — | — | — | ✓ | — | — |
| booking_ref | — | — | — | ✓ | — | — |
| call_closed | — | — | — | ✓ | — | — |
| callback_requested | — | — | — | ✓ | — | — |

All variable names are verbatim across tool definitions, edge schemas, and prompt instructions. No mismatches.

### Prompt Size Reduction vs Adapted (v1)

| File | V1 (chars) | V2.1 (chars) | Change |
|---|---|---|---|---|
| general_prompt | 10,479 | 4,929 | −53% |
| greeter prompt | 3,011 | 2,004 | −33% |
| address prompt | 6,933 | 6,708 | −3% |
| booking prompt | 7,381 | 7,093 | −4% |
| **Total** | **27,804** | **20,734** | **−25%** |

### KB Audit

| KB | Purpose | Source |
|---|---|---|
| `##uk-hvac-trade-kb##` | Trade vocabulary, symptom categories | Existing (unchanged) |
| `##uk-address-kb##` | Address format, postcodes, field mapping | Existing (+ field mapping merged in) |
| `##v2-interaction-kb##` | Mirror/match energy, off-script handling | `kb_v2_interaction_rules.md` |
| `##v2-sample-phrases-kb##` | "Didn't catch that" variants | `kb_v2_sample_phrases.md` |
| `##v2-fees-kb##` | £75/£120 call-out, repair cost response | `kb_v2_fee_rules.md` |
| `##v2-emergency-kb##` | Gas smell/leak protocol | `kb_v2_emergency_gas.md` |
| `##v2-company-kb##` | Company details, engineers, hours | `kb_v2_company_briefing.md` |
| `##v2-knowledge-boundary-kb##` | KB boundary rules (no trade knowledge) | `kb_v2_knowledge_boundary.md` |
| `##v2-diagnostic-restraint-kb##` | Diagnostic restraint rules | `kb_v2_diagnostic_restraint.md` |

**7 new KBs to create** (files in `V2.1/` as `kb_v2_*.md`).

### Edge Cases Checked

| Concern | Resolution |
|---|---|
| Empty tool call (V1 bug) | Reduced tool surfaces per state. General tool available everywhere for volunteered data. gpt-5.4 handles strict mode reliably |
| Transition without data | Edge parameters prevent transition until required vars are set |
| Context window growth | 25% smaller prompts = less growth per turn |
| KB not retrieved | `##v2-*##` naming consistent with Retell conventions. Retrieval triggered by conversation context |
| Booking without address | Address→booking edge requires address_confirmed=true |
| Name correction mid-call | `customer_name` in all 4 tools — can be updated from any state |
| Abrupt end_call | Main prompt and booking prompt both enforce: ask anything else? → warm goodbye → wait for customer farewell → end_call |

### Pre-Deployment Checklist

- [ ] Create 7 new KBs in Retell from `kb_v2_*.md` files
- [ ] Update `knowledge_base_ids` array in `build_v2.1_llm.py` with new KB IDs
- [ ] Run `python3 build_v2.1_llm.py` (dry run) to verify assembly
- [ ] Run `python3 build_v2.1_llm.py --deploy` to create new LLM + new chat agent
- [ ] Update test script `run_phase1_test.py` with new chat agent ID
- [ ] Run test suite against new agent
- [ ] If passing, create voice agent and publish

## Deployment Steps

### Step 1: Create 7 New Knowledge Bases

Upload each `kb_v2_*.md` file as a new KB in Retell:

```
POST /create-knowledge-base
{
  "name": "V2.1 Interaction Rules",
  "description": "Smart interaction rules — mirror, match energy, off-script"
}
```

Repeat for all 7 files. Save the returned `knowledge_base_id` for each.

Expected KB names: `##v2-interaction-kb##`, `##v2-sample-phrases-kb##`, `##v2-fees-kb##`, `##v2-emergency-kb##`, `##v2-company-kb##`, `##v2-knowledge-boundary-kb##`, `##v2-diagnostic-restraint-kb##`

### Step 2: Update KB References in Build Script

Add the 7 new KB IDs to `knowledge_base_ids` array in `build_v2.1_llm.py`.

The build script's dry run output will show the correct count once updated.

### Step 3: Deploy

```bash
python3 build_v2.1_llm.py          # Dry run — verify assembly
python3 build_v2.1_llm.py --deploy  # Create new LLM + new chat agent
```

This creates:
1. `POST /create-retell-llm` with the V2.1 payload → returns new `llm_id`
2. `POST /create-chat-agent` with the new `llm_id` → returns new `agent_id`

Agent name: `UK HVAC V2.1 (test)`

### Step 4: Test

```bash
python3 agents/heating_uk/performance_tests/run_phase1_test.py
```

Update `CHAT_AGENT_ID` in the test script to the new agent's ID.

### Step 5 (optional): Create Voice Agent & Publish

If test results pass:
```bash
POST /create-agent
POST /publish-agent-version
```

### Rollback Plan

If V2.1 underperforms:

1. New LLM and chat agent are isolated — production uses the existing `agent_16985b5d087e56c35141983396`
2. Delete V2.1 LLM: `DELETE /delete-retell-llm/{v2.1_llm_id}`
3. Delete V2.1 chat agent: `DELETE /delete-chat-agent/{v2.1_agent_id}`
4. No production disruption

## Estimated Impact

| Metric | V1 (call 2) | V2.1 (projected) | Improvement |
|---|---|---|---|
| LLM p50 latency | 1,947ms | ~800-1,000ms | −50-60% |
| LLM p99 latency | 5,244ms | ~2,000-2,500ms | −50-55% |
| Avg tokens per call | 7,003 | ~4,500-5,000 | −30-35% |
| Cost per 4-min call | $88-116 | ~$60-75 | −30-35% |
| Total prompt chars | 27,804 | 20,734 | −25% |
