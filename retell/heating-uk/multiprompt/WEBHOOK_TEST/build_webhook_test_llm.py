#!/usr/bin/env python3
"""Webhook Test — build and deploy script.

Usage:
  export RETELL_API_KEY=key_...
  python3 build_webhook_test_llm.py

Creates a NEW disposable Retell LLM with a single state (booking_test) and
two tools: a custom check_availability function + native book_calendar.
No KBs, no edges. Then creates a chat agent for interaction.
Does NOT touch the V3.1 LLM or any voice agent.
"""

import json, os, sys, urllib.request, urllib.error

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

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


# --- Step 1: Read prompt ---
print("=== Step 1: Read prompt ===")
prompt_path = os.path.join(PROJECT_ROOT, "prompt.md")
prompt = read_file(prompt_path)
print(f"  Read: prompt.md")

# --- Step 2: Load tool definitions ---
print("\n=== Step 2: Load tool definitions ===")
tools_path = os.path.join(PROJECT_ROOT, "JSON", "tool_definitions.json")
with open(tools_path) as f:
    tool_defs = json.load(f)
print(f"  Loaded: tool_definitions.json")

general_tools = tool_defs.get("general_tools", [])
state_tools = tool_defs.get("states", {}).get("booking_test", {}).get("tools", [])

# --- Step 3: Assemble LLM payload ---
print("\n=== Step 3: Assemble LLM payload ===")
llm_payload = {
    "model": "gpt-5.1",
    "model_temperature": 0.1,
    "model_high_priority": True,
    "tool_call_strict_mode": True,
    "general_prompt": "You are a test booking agent.",
    "general_tools": general_tools,
    "states": [
        {
            "name": "booking_test",
            "state_prompt": prompt,
            "edges": [],
            "tools": state_tools,
        }
    ],
    "starting_state": "booking_test",
    "begin_message": "Hi, I'm the webhook test booking agent. How can I help?",
    "begin_after_user_silence_ms": 2000,
    "knowledge_base_ids": [],
    "kb_config": {"top_k": 3, "filter_score": 0.6},
    "default_dynamic_variables": {},
}

# --- Step 4: Create the LLM ---
print("\n=== Step 4: Create Retell LLM ===")
r = api("POST", "create-retell-llm", llm_payload)
llm_id = r.get("llm_id")
if not llm_id:
    print(f"  FATAL: {json.dumps(r, indent=2)}")
    sys.exit(1)
print(f"  Created LLM: {llm_id}")

# --- Step 5: Verify the LLM ---
print("\n=== Step 5: Verify LLM ===")
r2 = api("GET", f"get-retell-llm/{llm_id}")
if r2.get("_error"):
    print(f"  WARNING: Could not verify LLM: {r2}")
elif r2.get("llm_id") == llm_id:
    print(f"  Verified: {llm_id} — {len(r2.get('states', []))} states confirmed")
else:
    print(f"  WARNING: Verification returned unexpected response")

# --- Step 6: Create chat agent ---
print("\n=== Step 6: Create chat agent ===")
r3 = api("POST", "create-chat-agent", {
    "agent_name": "Webhook Test",
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

# --- Step 7: Print summary ---
print("\n" + "=" * 60)
print("  DEPLOY SUMMARY")
print("=" * 60)
print(f"  LLM ID:          {llm_id}")
print(f"  Chat Agent ID:   {agent_id}")
print(f"  Model:           {llm_payload['model']}")
print(f"  States:          1 (booking_test)")
print(f"  KBs attached:    0")
print("=" * 60)
print()
print(f"WEBHOOK_TEST_LLM_ID={llm_id}")
print(f"WEBHOOK_TEST_AGENT_ID={agent_id}")
print()
print("Done.")
