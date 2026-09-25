# Call Analysis SOP

> Standard framework for analyzing every test run. Run through ALL categories on every analysis.

## Data Sources

1. **GET `get-chat/{chat_id}`** — full transcript, message_with_tool_calls, dynamic_variables, cost
2. **Test script stdout** — real-time turn-by-turn output
3. **Booking confirmation** — Cal.com API check if booking was created

---

## Analysis Categories

### 1. PROMPT FOLLOWING

Check every state's prompt steps against what the agent actually did. For each state:

- Did the agent follow the prescribed conversation flow steps?
- Were filler phrases used before tool calls?
- Were required questions asked (boiler brand, error code, postcode, etc.)?
- Were forbidden actions avoided (stacking questions, diagnosing, etc.)?
- Did the agent wait for confirmation before transitioning?

**Mark each state:** ✅ followed / ⚠️ partial / ❌ violated

### 2. NONSENSE / HALLUCINATION

- Agent says things it cannot know ("I don't have access to X" when tools exist)
- Raw JSON or technical output leaked into agent speech
- Agent contradicts itself between turns
- Agent claims to do something it cannot
- Agent fabricates tools, policies, or capabilities

### 3. REDUNDANCY

- Same extract tool called multiple times with same data
- Same question asked to customer more than once (without cause)
- Trivial or wasted tool calls (e.g., trigger with `false`)
- State transitions attempted without new data

### 4. REPETITION

- Same phrase or sentence structure repeated across turns
- Agent loops on the same response without progression
- Same slot offered after customer already responded

### 5. BUGS (Code/Config)

- Missing variable values passed as empty strings
- Incorrect tool parameters (wrong format, wrong enum)
- `speak_after_execution` misconfiguration
- Edge schema / tool enum mismatches
- API errors from tools (check_availability, book_calendar)
- Missing required fields in downstream API calls

### 6. TOOL CALL ANALYSIS

- Were all required tools called for each state?
- Were transition tools called in correct order (extract → trigger → transition)?
- Were tool parameters populated with real values (not empty)?
- Were tools called at the right time (not before data collected)?

### 7. CONVERSATION FLOW

- Natural pacing: agent doesn't rush or stall
- One question per turn (no stacking)
- Agent responds to what customer actually said
- Agent re-asks when customer didn't answer
- Goodbye/end_call handled properly

### 8. LOGS & METRICS

- Total turns
- Cost
- Number of agent messages
- Number of tool calls
- Number of state transitions
- Dynamic variables at end of call

---

## Output Format

```
## Test [#]: Summary

### State Transitions
greeter → triage: ✅/❌
triage → address: ✅/❌
address → slot_selection: ✅/❌
slot_selection → confirmation: ✅/❌
confirmation → booking: ✅/❌

### Booking
book_calendar: ✅/❌ (booking_id: X)
end_call: ✅/❌

### 1. Prompt Following
[per-state breakdown]

### 2. Nonsense/Hallucination
[issues found]

### 3. Redundancy
[issues found]

### 4. Repetition
[issues found]

### 5. Bugs
[issues found]

### 6. Tool Call Analysis
[issues found]

### 7. Conversation Flow
[issues found]

### 8. Logs & Metrics
Turns: X | Cost: X¢ | Agent msgs: X | Tool calls: X | Transitions: X
```
