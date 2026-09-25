#!/usr/bin/env python3
"""Production Webhook Test v2 — build script (no end_call in general_tools).

Fixes the earlier test agent that fired end_call prematurely. This build has
NO general tools; only check_availability + book_calendar in the single state.
Creates a fresh LLM + chat agent. Does NOT touch V3.1 or production.
"""

import json, os, sys, urllib.request, urllib.error

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
API_KEY = os.environ.get("RETELL_API_KEY")
if not API_KEY:
    print("FATAL: RETELL_API_KEY not set.")
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


prompt = open(os.path.join(PROJECT_ROOT, "prompt_context.md")).read()
tool_defs = json.load(open(os.path.join(PROJECT_ROOT, "JSON", "tool_definitions_no_endcall.json")))

llm_payload = {
    "model": "gpt-5.1",
    "model_temperature": 0.1,
    "model_high_priority": True,
    "tool_call_strict_mode": True,
    "general_prompt": "You are a webhook test booking agent for British Heat Services. Always help the caller find and book a slot before ending.",
    "general_tools": tool_defs.get("general_tools", []),
    "states": [
        {
            "name": "booking_test",
            "state_prompt": prompt,
            "edges": [],
            "tools": tool_defs["states"]["booking_test"]["tools"],
        }
    ],
    "starting_state": "booking_test",
    "begin_message": "Hi, British Heat Services. How can I help?",
    "begin_after_user_silence_ms": 2000,
    "knowledge_base_ids": [],
    "kb_config": {"top_k": 3, "filter_score": 0.6},
    "default_dynamic_variables": {},
}

print("=== Creating Retell LLM ===")
r = api("POST", "create-retell-llm", llm_payload)
llm_id = r.get("llm_id")
if not llm_id:
    print(f"  FATAL: {json.dumps(r, indent=2)}")
    sys.exit(1)
print(f"  LLM: {llm_id}")

print("=== Creating chat agent ===")
r3 = api("POST", "create-chat-agent", {
    "agent_name": "Prod Webhook Test v2",
    "response_engine": {"type": "retell-llm", "llm_id": llm_id},
})
agent_id = r3.get("agent_id")
if not agent_id:
    print(f"  FATAL: {json.dumps(r3, indent=2)}")
    sys.exit(1)
print(f"  Chat Agent: {agent_id}")
print(f"\nPROD_WEBHOOK_TEST_V2_LLM_ID={llm_id}")
print(f"PROD_WEBHOOK_TEST_V2_AGENT_ID={agent_id}")
