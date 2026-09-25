#!/usr/bin/env python3
"""Check: can a custom webhook use the native tool name 'check_availability'?
Builds a fresh disposable LLM (does NOT touch V3.1/prod)."""
import json, os, sys, urllib.request, urllib.error

API_KEY = os.environ.get("RETELL_API_KEY") or "${RETELL_KEY_2}"
BASE = "https://api.retellai.com"

def api(method, endpoint, data=None):
    req = urllib.request.Request(f"{BASE}/{endpoint}",
                                 data=json.dumps(data).encode() if data else None,
                                 method=method)
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return {"_error": str(e.code), "_body": e.read().decode()[:800]}

new_desc = json.load(open(
    "/home/julio/projects/Retell_AI_MCP_connection/agents/heating_uk/multiprompt/V3.1/JSON/check_availability_tool_v3.json"))["description"]

tool = {
    "type": "custom",
    "name": "check_availability",          # same name the native tool uses
    "description": new_desc,
    "url": "https://slots.diallux-ai.site/check_availability",
    "method": "POST",
    "parameters": {
        "type": "object",
        "properties": {
            "slot_target_date": {
                "type": "string",
                "description": "ISO date (YYYY-MM-DD) of the day the caller wants a slot for."
            }
        }
    },
    "args_at_root": True,
    "speak_after_execution": False,
}

payload = {
    "model": "gpt-5.1",
    "model_temperature": 0.1,
    "tool_call_strict_mode": True,
    "general_prompt": "You are a booking test agent. Use check_availability to find slots.",
    "states": [
        {
            "name": "test_state",
            "state_prompt": "Call check_availability with a concrete date and report slots.",
            "edges": [],
            "tools": [tool],
        }
    ],
    "starting_state": "test_state",
    "begin_message": "Hi.",
}

r = api("POST", "create-retell-llm", payload)
if r.get("llm_id"):
    print("BUILD OK — custom tool named 'check_availability' accepted.")
    print("LLM:", r["llm_id"])
    r3 = api("POST", "create-chat-agent", {
        "agent_name": "name-check test",
        "response_engine": {"type": "retell-llm", "llm_id": r["llm_id"]},
    })
    print("Agent:", r3.get("agent_id"))
else:
    print("BUILD FAILED:")
    print(json.dumps(r, indent=2))
