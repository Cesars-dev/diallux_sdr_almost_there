#!/usr/bin/env python3
"""V3 HVAC Agent — build and deploy script.

Usage:
  export RETELL_API_KEY=key_...
  python3 build_v3_llm.py

Creates a new Retell LLM with 6-state multi-prompt config, links 13 KBs,
then creates a new chat agent for testing. No existing resources are modified.
"""

import json, os, sys, urllib.request, urllib.error

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "prompts")
JSON_DIR = os.path.join(PROJECT_ROOT, "JSON")

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


# --- Step 1: Discover KBs ---
print("=== Step 1: Discover knowledge bases ===")
r = api("GET", "list-knowledge-bases")
existing_kbs = {}
if isinstance(r, list):
    for kb in r:
        existing_kbs[kb["knowledge_base_name"]] = kb["knowledge_base_id"]
elif isinstance(r, dict) and r.get("_error"):
    print("  WARNING: Could not list KBs, continuing with empty list.")

expected_kbs = [
    {"name": "v2-interaction-kb", "file_path": None},
    {"name": "v2-sample-phrases-kb", "file_path": None},
    {"name": "v2-fees-kb", "file_path": None},
    {"name": "v2-gas-mention-kb", "file_path": None},
    {"name": "v2-company-kb", "file_path": None},
    {"name": "v2-knowledge-boundary-kb", "file_path": None},
    {"name": "v2-diagnostic-restraint-kb", "file_path": None},
    {"name": "uk-hvac-trade-kb", "file_path": None},
    {"name": "uk-address-kb", "file_path": None},
    {"name": "v2-call-closing-kb", "file_path": None},
    {"name": "day-logic-kb", "file_path": None},
    {"name": "uk-names-kb", "file_path": None},
    {"name": "name-spelling-kb", "file_path": None},
]

kb_ids = []
for expected in expected_kbs:
    name = expected["name"]
    if name in existing_kbs:
        kid = existing_kbs[name]
        kb_ids.append(kid)
        print(f"  Found: {name} -> {kid}")
    else:
        print(f"  MISSING: {name} not found on Retell")

print(f"  KBs attached: {len(kb_ids)}/13")

# --- Step 2: Read prompt files ---
print("\n=== Step 2: Read prompt files ===")
prompt_files = {
    "general_prompt": "multiprompt_mvp_main_v3.md",
    "greeter": "multiprompt_mvp_greeter_v3.md",
    "triage": "multiprompt_mvp_triage_v3.md",
    "address": "multiprompt_mvp_address_v3.md",
    "slot_selection": "multiprompt_mvp_slot_selection_v3.md",
    "confirmation": "multiprompt_mvp_confirmation_v3.md",
    "booking": "multiprompt_mvp_booking_v3.md",
}

prompts = {}
for key, filename in prompt_files.items():
    path = os.path.join(PROMPTS_DIR, filename)
    try:
        prompts[key] = read_file(path)
        print(f"  Read: {filename}")
    except FileNotFoundError:
        print(f"  FATAL: Missing prompt file: {path}")
        sys.exit(1)

# --- Step 3: Load tool definitions ---
print("\n=== Step 3: Load tool definitions ===")
tools_path = os.path.join(JSON_DIR, "tool_definitions_v3.json")
try:
    with open(tools_path) as f:
        tool_defs = json.load(f)
    print(f"  Loaded: tool_definitions_v3.json")
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"  FATAL: Could not load tools: {e}")
    sys.exit(1)

# --- Step 4: Load edge schemas ---
print("\n=== Step 4: Load edge schemas ===")
edge_files = {
    "greeter": "transition_greeter_to_triage.json",
    "triage": "transition_triage_to_address.json",
    "address": "transition_address_to_slot_selection.json",
    "slot_selection": "transition_slot_selection_to_confirmation.json",
    "confirmation": "transition_confirmation_to_booking.json",
}

edges = {}
for state_name, filename in edge_files.items():
    path = os.path.join(JSON_DIR, filename)
    try:
        edges[state_name] = json.loads(read_file(path))
        print(f"  Loaded: {filename}")
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"  WARNING: Missing edge schema {filename}, using simple edge")
        edges[state_name] = {"destination_state_name": "", "description": ""}

# --- Step 5: Assemble LLM payload ---
print("\n=== Step 5: Assemble LLM payload ===")

general_tools = tool_defs.get("general_tools", [])
state_tools = tool_defs.get("states", {})

states_payload = []
state_order = ["greeter", "triage", "address", "slot_selection", "confirmation", "booking"]
transition_targets = ["triage", "address", "slot_selection", "confirmation", "booking"]

for i, state_name in enumerate(state_order):
    edge_schema = edges.get(state_name, {})
    state_tools_list = state_tools.get(state_name, {}).get("tools", [])

    state_entry = {
        "name": state_name,
        "state_prompt": prompts[state_name],
        "edges": [],
        "tools": state_tools_list,
    }

    if i < len(transition_targets):
        target = transition_targets[i]
        edge_entry = {
            "destination_state_name": edge_schema.get("destination_state_name", target),
            "description": edge_schema.get("description", f"Transition to {target}"),
        }
        if "parameters" in edge_schema:
            edge_entry["parameters"] = edge_schema["parameters"]
        state_entry["edges"] = [edge_entry]

    states_payload.append(state_entry)

llm_payload = {
    "model": "gpt-5.1",
    "model_temperature": 0.1,
    "model_high_priority": True,
    "tool_call_strict_mode": True,
    "general_prompt": prompts["general_prompt"],
    "general_tools": general_tools,
    "states": states_payload,
    "starting_state": "greeter",
    "begin_message": "British Heat Services, Tom speaking — how can I help?",
    "begin_after_user_silence_ms": 2000,
    "knowledge_base_ids": kb_ids,
    "kb_config": {"top_k": 3, "filter_score": 0.6},
    "default_dynamic_variables": {},
}

# --- Step 6: Create the LLM ---
print("\n=== Step 6: Create Retell LLM ===")
r = api("POST", "create-retell-llm", llm_payload)
llm_id = r.get("llm_id")
if not llm_id:
    print(f"  FATAL: {json.dumps(r, indent=2)}")
    sys.exit(1)
print(f"  Created LLM: {llm_id}")

# --- Step 7: Verify the LLM ---
print("\n=== Step 7: Verify LLM ===")
r2 = api("GET", f"get-retell-llm/{llm_id}")
if r2.get("_error"):
    print(f"  WARNING: Could not verify LLM: {r2}")
elif r2.get("llm_id") == llm_id:
    print(f"  Verified: {llm_id} — {len(r2.get('states', []))} states confirmed")
else:
    print(f"  WARNING: Verification returned unexpected response")

# --- Step 8: Create chat agent ---
print("\n=== Step 8: Create chat agent ===")
agent_name = "British Heat Services V3 Chat_test9"
r3 = api("POST", "create-chat-agent", {
    "agent_name": agent_name,
    "response_engine": {
        "type": "retell-llm",
        "llm_id": llm_id,
    },
})
agent_id = r3.get("agent_id")
if not agent_id:
    print(f"  FATAL: {json.dumps(r3, indent=2)}")
    sys.exit(1)
print(f"  Created chat agent: {agent_id}")

# --- Step 9: Print summary ---
print("\n" + "=" * 60)
print("  DEPLOY SUMMARY")
print("=" * 60)
print(f"  LLM ID:          {llm_id}")
print(f"  Chat Agent ID:   {agent_id}")
print(f"  Model:           {llm_payload['model']}")
print(f"  KBs attached:    {len(kb_ids)}/13")
print("=" * 60)
print()
print("=== TEST INSTRUCTIONS ===")
print("  1. Update CHAT_AGENT_ID in performance_tests/run_phase1_test.py")
print(f"     Set CHAT_AGENT_ID = \"{agent_id}\"")
print()
print("  2. Run the test suite:")
print("     python3 /home/julio/projects/Retell_AI_MCP_connection/agents/heating_uk/performance_tests/run_phase1_test.py")
print()
print("Done.")
