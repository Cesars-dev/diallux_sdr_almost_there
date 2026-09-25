#!/usr/bin/env python3
"""Assemble edited prompt files + tool definitions → new LLM via POST /create-retell-llm,
then update the existing chat agent to point at it (no new chat agent needed).

Usage:
  python3 build_multiprompt_llm.py [chat_agent_id]

  Pass a chat agent ID to update, or the default will be used.
"""

import json, os, sys, urllib.request, urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))
ADAPTED = os.path.join(BASE, "adapted")
API_KEY = "${RETELL_KEY_6}"
BASE_URL = "https://api.retellai.com"
CHAT_AGENT_ID = sys.argv[1] if len(sys.argv) > 1 else "agent_ff9d4b9646a85b82d7ce8fd837"

def read_prompt(filename):
    path = os.path.join(ADAPTED, filename)
    with open(path) as f:
        return f.read()

def api(method, endpoint, data=None):
    url = f"{BASE_URL}/{endpoint}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  ERROR {e.code}: {err[:500]}")
        return {"_error": str(e.code)}

# --- Read the 4 prompt files ---
main_prompt = read_prompt("multiprompt_mvp_main_v2.md")
greeter_prompt = read_prompt("multiprompt_mvp_greeter_COPY.md")
address_prompt = read_prompt("multiprompt_mvp_address_COPY.md")
booking_prompt = read_prompt("multiprompt_mvp_booking_close_COPY.md")

# --- Tool definitions ---

# extract_user_details — full variable list (general_tools is end_call only per plan)
extract_user_details_variables = [
    {"name": "customer_name", "type": "string", "description": "The customer's full name"},
    {"name": "classified_intent", "type": "string", "description": "Why the customer is calling", "choices": ["booking", "quote", "other"]},
    {"name": "greeting_exchanged", "type": "boolean", "description": "Whether greeting has been exchanged"},
    {"name": "intent_clear", "type": "boolean", "description": "Whether the intent is understood"},
    {"name": "intent_confirmed", "type": "boolean", "description": "Whether the intent has been confirmed"},
    {"name": "past_customer", "type": "boolean", "description": "Whether the customer has used the service before"},
    {"name": "address_house_number", "type": "string", "description": "House number or name if provided in opening"},
    {"name": "address_street", "type": "string", "description": "Street name if provided in opening"},
    {"name": "address_postcode", "type": "string", "description": "UK postcode if provided in opening"},
    {"name": "address_city", "type": "string", "description": "City or town if provided in opening"},
    {"name": "callback_requested", "type": "boolean", "description": "Set to true when customer rejects all slot offers and callback is offered"},
    {"name": "address_incomplete", "type": "boolean", "description": "Set to true when the customer could not provide all 4 address fields"},
]

extract_user_details_tool = {
    "type": "extract_dynamic_variable",
    "name": "extract_user_details",
    "description": "Extract user details when volunteered or when callback is requested.",
    "variables": extract_user_details_variables,
    "speak_after_execution": True,
}

# extract_address_details — address state scoped tool (2 new fields per §4B)
extract_address_details_variables = [
    {"name": "customer_name", "type": "string", "description": "The customer's full name"},
    {"name": "problem_category", "type": "string", "description": "Category of the heating issue"},
    {"name": "symptom_brief", "type": "string", "description": "Brief description of symptoms"},
    {"name": "error_code", "type": "string", "description": "Error code shown on boiler display if any"},
    {"name": "boiler_make", "type": "string", "description": "Boiler brand if mentioned"},
    {"name": "address_postcode", "type": "string", "description": "UK postcode"},
    {"name": "address_house_number", "type": "string", "description": "House number or property name e.g. '14' or 'Rose Cottage'"},
    {"name": "address_street", "type": "string", "description": "Street name only e.g. 'Victoria Terrace' or 'Mill Lane'"},
    {"name": "address_line1", "type": "string", "description": "Combined house number + street (backward compat for booking notes)"},
    {"name": "address_city", "type": "string", "description": "City or town"},
    {"name": "address_confirmed", "type": "boolean", "description": "Whether the customer has confirmed their address"},
]

extract_address_details_tool = {
    "type": "extract_dynamic_variable",
    "name": "extract_address_details",
    "description": "Extract address and symptom details from the customer.",
    "variables": extract_address_details_variables,
    "speak_after_execution": True,
}

# Calendar tools (unchanged except book_calendar email desc per §4A)
check_availability_tool = {
    "event_type_id": 6389911,
    "cal_api_key": "${CAL_KEY_1}",
    "timezone": "Europe/London",
    "speak_after_execution": True,
    "name": "check_availability",
    "description": "Check available appointment slots for the next 7 days",
    "type": "check_availability_cal",
}

book_calendar_tool = {
    "event_type_id": 6389911,
    "cal_api_key": "${CAL_KEY_1}",
    "cal_fields": [
        {"name": "name", "description": "attendee name", "type": "string", "required": True},
        {"name": "email", "description": "attendee email — use jaydiallux@gmail.com as default", "type": "string", "required": True},
        {"name": "attendeePhoneNumber", "description": "attendeePhoneNumber (number must be valid number in e.164 format)", "type": "string", "required": False},
        {"name": "title", "description": "title", "type": "string", "required": True},
        {"name": "notes", "description": "notes", "type": "string", "required": False},
        {"name": "guests", "description": "guests (must be valid email addresses)", "type": "array", "required": False},
        {"name": "rescheduleReason", "description": "rescheduleReason", "type": "string", "required": False},
    ],
    "timezone": "Europe/London",
    "speak_after_execution": True,
    "name": "book_calendar",
    "description": "Book a confirmed appointment slot via Cal.com API",
    "location_type": "integration",
    "type": "book_appointment_cal",
}

end_call_tool = {
    "execution_message_type": "prompt",
    "execution_message_description": "",
    "speak_after_execution": True,
    "name": "end_call",
    "description": "End the call politely when the user has no more queries",
    "type": "end_call",
    "speak_during_execution": False,
}

# --- Assemble LLM payload ---
llm_payload = {
    "model": "gpt-5.4",
    "model_temperature": 0,
    "model_high_priority": True,
    "tool_call_strict_mode": True,
    "general_prompt": main_prompt,
    "general_tools": [end_call_tool],
    "states": [
        {
            "name": "greeter",
            "state_prompt": greeter_prompt,
            "edges": [
                {
                    "destination_state_name": "address",
                    "description": "Transition when all greeter fields are populated",
                }
            ],
            "tools": [extract_user_details_tool],
        },
        {
            "name": "address",
            "state_prompt": address_prompt,
            "edges": [
                {
                    "destination_state_name": "booking",
                    "description": "Transition when all address fields are populated",
                }
            ],
            "tools": [extract_address_details_tool],
        },
        {
            "name": "booking",
            "state_prompt": booking_prompt,
            "edges": [],
            "tools": [
                check_availability_tool,
                book_calendar_tool,
                extract_user_details_tool,
            ],
        },
    ],
    "starting_state": "greeter",
    "begin_message": "British Heat Services, Tom speaking — how can I help?",
    "begin_after_user_silence_ms": 2000,
    "knowledge_base_ids": [
        "knowledge_base_d00023e51fae35ab",
        "knowledge_base_b9eb9dcc29315240",
    ],
    "kb_config": {"top_k": 3, "filter_score": 0.6},
    "default_dynamic_variables": {},
}

# --- Deploy ---
print("=== Step 1: Create new LLM ===")
r = api("POST", "create-retell-llm", llm_payload)
new_llm_id = r.get("llm_id")
if not new_llm_id:
    print(f"FATAL: {r}")
    sys.exit(1)
print(f"  New LLM: {new_llm_id}")

print(f"\n=== Step 2: Point chat agent {CHAT_AGENT_ID} to new LLM ===")
r2 = api("PATCH", f"update-chat-agent/{CHAT_AGENT_ID}", {
    "response_engine": {
        "type": "retell-llm",
        "llm_id": new_llm_id,
    },
})
if r2.get("agent_id"):
    print(f"  SUCCESS — {CHAT_AGENT_ID} now uses {new_llm_id}")
else:
    print(f"  Response: {json.dumps(r2, indent=2)[:200]}")

print(f"\n=== Step 3: Run Phase 1 test ===")
print(f"  python3 performance_tests/run_phase1_test.py")
print(f"  (CHAT_AGENT_ID already set to {CHAT_AGENT_ID} in the test script)")

print(f"\n=== Step 4 (after tests pass): Create voice agent & publish ===")
print(f"  POST /create-agent with response_engine.llm_id = {new_llm_id}")
print(f"  POST /publish-agent-version")

print(f"\nDone. New LLM ID: {new_llm_id}")
