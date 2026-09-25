#!/usr/bin/env python3
"""Today-Date Injection Test — build script.

Creates a NEW 3-state chat LLM (slot_selection -> confirmation -> booking):
  - slot_selection: multiprompt_mvp_slot_selection_v3.md (same dir, custom check_availability)
  - confirmation:   multiprompt_mvp_confirmation_v3.md (same dir, custom check_availability)
  - booking:        prompt_booking_state.md (same dir, book_calendar, event 6522694)
  - general_prompt: main_test_prompt.md (same dir, test persona, uses {{today_uk}})

All prompt + tool files are read VERBATIM (never edited here) from this directory.
Edges are loaded from the V3.1 transition JSONs (../../JSON). Always creates fresh
resources — never patches.
"""

import json, os, sys, urllib.request, urllib.error

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = PROJECT_ROOT
V31_JSON = os.path.join(PROJECT_ROOT, "..", "..", "JSON")

API_KEY = os.environ.get("RETELL_API_KEY")
if not API_KEY:
    print("FATAL: RETELL_API_KEY environment variable not set.")
    sys.exit(1)
BASE_URL = "https://api.retellai.com"


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


def read_file(path):
    with open(path) as f:
        return f.read()


def load_json(path):
    with open(path) as f:
        return json.load(f)


# --- Step 1: Read prompts verbatim ---
print("=== Step 1: Read prompt files ===")
prompts = {
    "general_prompt": read_file(os.path.join(PROJECT_ROOT, "main_test_prompt.md")),
    "slot_selection": read_file(os.path.join(PROJECT_ROOT, "multiprompt_mvp_slot_selection_v3.md")),
    "confirmation": read_file(os.path.join(PROJECT_ROOT, "multiprompt_mvp_confirmation_v3.md")),
    "booking": read_file(os.path.join(PROJECT_ROOT, "prompt_booking_state.md")),
}
for key in prompts:
    print(f"  Read: {key} ({len(prompts[key])} chars)")

# --- Step 2: Load tool definitions ---
print("\n=== Step 2: Load tool definitions ===")
tool_defs = load_json(os.path.join(JSON_DIR, "tool_definitions_today.json"))
state_tools = tool_defs["states"]
print("  Loaded: tool_definitions_today.json")

# --- Step 3: Load edge schemas ---
print("\n=== Step 3: Load edge schemas ===")
edges = {
    "slot_selection": load_json(os.path.join(PROJECT_ROOT, "transition_slot_selection_to_confirmation.json")),
    "confirmation": load_json(os.path.join(PROJECT_ROOT, "transition_confirmation_to_booking.json")),
}
for k in edges:
    print(f"  Loaded: {k} -> {edges[k]['destination_state_name']}")

# --- Step 4: Assemble LLM payload ---
print("\n=== Step 4: Assemble LLM payload ===")
state_order = ["slot_selection", "confirmation", "booking"]
states_payload = []
for state_name in state_order:
    edge_entry = None
    if state_name in edges:
        edge_schema = edges[state_name]
        edge_entry = {
            "destination_state_name": edge_schema.get("destination_state_name", ""),
            "description": edge_schema.get("description", f"Transition to {edge_schema.get('destination_state_name', '')}"),
        }
        if "parameters" in edge_schema:
            edge_entry["parameters"] = edge_schema["parameters"]

    states_payload.append({
        "name": state_name,
        "state_prompt": prompts[state_name],
        "edges": [edge_entry] if edge_entry else [],
        "tools": state_tools[state_name]["tools"],
    })

llm_payload = {
    "model": "gpt-5.1",
    "model_temperature": 0.1,
    "model_high_priority": True,
    "tool_call_strict_mode": True,
    "general_prompt": prompts["general_prompt"],
    "general_tools": tool_defs.get("general_tools", []),
    "states": states_payload,
    "starting_state": "slot_selection",
    "begin_message": "Hi, British Heat Services. How can I help?",
    "begin_after_user_silence_ms": 2000,
    "knowledge_base_ids": [],
    "kb_config": {"top_k": 3, "filter_score": 0.6},
    "default_dynamic_variables": {},
}

# --- Step 5: Create the LLM ---
print("\n=== Step 5: Create Retell LLM ===")
r = api("POST", "create-retell-llm", llm_payload)
llm_id = r.get("llm_id")
if not llm_id:
    print(f"  FATAL: {json.dumps(r, indent=2)}")
    sys.exit(1)
print(f"  Created LLM: {llm_id}")

# --- Step 6: Verify the LLM ---
print("\n=== Step 6: Verify LLM ===")
r2 = api("GET", f"get-retell-llm/{llm_id}")
if r2.get("_error"):
    print(f"  WARNING: Could not verify LLM: {r2}")
elif r2.get("llm_id") == llm_id:
    print(f"  Verified: {llm_id} — {len(r2.get('states', []))} states confirmed")
else:
    print("  WARNING: Verification returned unexpected response")

# --- Step 7: Create chat agent ---
print("\n=== Step 7: Create chat agent ===")
r3 = api("POST", "create-chat-agent", {
    "agent_name": "Today Test v5",
    "response_engine": {"type": "retell-llm", "llm_id": llm_id},
})
agent_id = r3.get("agent_id")
if not agent_id:
    print(f"  FATAL: {json.dumps(r3, indent=2)}")
    sys.exit(1)
print(f"  Created chat agent: {agent_id}")

# --- Step 8: Summary ---
print("\n" + "=" * 60)
print("  DEPLOY SUMMARY")
print("=" * 60)
print(f"  LLM ID:          {llm_id}")
print(f"  Chat Agent ID:   {agent_id}")
print(f"  States:          {state_order}")
print("=" * 60)
print(f"\nTODAY_TEST_LLM_ID={llm_id}")
print(f"TODAY_TEST_AGENT_ID={agent_id}")
