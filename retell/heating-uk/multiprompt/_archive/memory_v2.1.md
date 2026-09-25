# Memory — HVAC Agent State (2026-07-25)

## Status: Mess to Fix

The multi-prompt architecture works (test7 and test8 deployed, booked successfully) but has critical inefficiencies that make it slow and unreliable.

### Current Deployed Resources

| Resource | ID | Notes |
|----------|-----|-------|
| test7 LLM | `llm_a7cf884aed0950275809ed6813ac` | Adapted booking prompt + fee KB ref |
| test7 agent | `agent_1b77b680d6f76ba5d45588efa6` | UK HVAC V2.1 (test7) — isolated |
| test8 LLM | `llm_954face069f5df77d84451098d72` | Variable Handling section stripped |
| test8 agent | `agent_8b7e58b21bdd4d6fc99b23aa75` | UK HVAC V2.1 (test8) — isolated |
| test8 copy (live voice) | `agent_ed8fc268f2c8c2bd8203f7435c` | Uses LLM `llm_698479480ef60916f79173f27263` (gpt-5.1, v11) — user's live mods |

### Known Issues

1. **Address fields in greeter tool** — `extract_greeter_values` has 5 address variables (house_number, street, line1, city, postcode) that belong in the address state. This causes the LLM to keep calling the tool to fill them during address collection instead of transitioning.

2. **`customer_name` empty-string bypass** — Address state Step 1 checks `Does {{customer_name}} exist?`. After greeter sets it to `""` (empty), the check passes and the agent skips asking. Name is never captured in address state.

3. **4 redundant extraction calls** — The greeter prompt tells the LLM to call `extract_greeter_values` piecemeal per turn instead of once at the end. 4 calls = 4x latency on the first 20 seconds of the call.

4. **`classified_intent` misclassification** — `choices: ["booking", "quote", "other"]`. "Do you guys do boiler repair?" gets classified as `other` instead of `booking` because the description is vague.

5. **`booking_confirmed` set before `book_calendar`** — The LLM sometimes calls `extract_booking_values` with `booking_confirmed=false` before `book_calendar` completes.

6. **`call_closed` often `false`** — The close routine rarely completes the full sequence (offer help → wait → farewell → end_call → extract call_closed).

### Deploy Path for Next Iteration

Build script: `V2.1/build_v2.1_llm.py` (reads from `V2.1/iterations/test8/`)

To deploy: `python3 V2.1/build_v2.1_llm.py --deploy` (requires RETELL_API_KEY in env)

Next version should:
- Consolidate extraction to a single call per state
- Remove address fields from greeter tool
- Fix customer_name empty-string guard
- Ensure greeting_exchanged is the last field set (transition signal)
