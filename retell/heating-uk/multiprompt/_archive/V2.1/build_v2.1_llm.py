#!/usr/bin/env python3
"""
V2.1 Build Script — Assembles trimmed prompts + KB references + reduced tools into an LLM payload.

Reads from iterations/<name>/ folder. Defaults to test8; override with --iteration.

Usage:
  python3 build_v2.1_llm.py                                  # Dry run, test8
  python3 build_v2.1_llm.py --iteration test9                # Dry run, test9
  python3 build_v2.1_llm.py --iteration test9 --deploy       # Create new LLM + new chat agent
"""

import argparse, json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))

def parse_args():
    parser = argparse.ArgumentParser(
        description="V2.1 Build Script — assembles prompts + KB refs + tools into a Retell LLM payload."
    )
    parser.add_argument(
        "--iteration", "-i",
        default="test8",
        help="Iteration folder name under iterations/ (default: test8)",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Create new LLM + new chat agent in Retell",
    )
    return parser.parse_args()

args = parse_args()
SRC = os.path.join(BASE, "iterations", args.iteration)

if not os.path.isdir(SRC):
    print(f"FATAL: iteration folder not found: {SRC}")
    avail = os.listdir(os.path.join(BASE, "iterations"))
    print(f"  Available iterations: {', '.join(sorted(avail))}")
    sys.exit(1)

def read_file(filename):
    with open(os.path.join(SRC, filename)) as f:
        return f.read()

def read_json(filename):
    with open(os.path.join(SRC, filename)) as f:
        return json.load(f)

# --- Read prompts ---
general_prompt = read_file("main.md")
greeter_prompt = read_file("greeter.md")
address_prompt = read_file("address.md")
booking_prompt = read_file("booking.md")

# --- Read edges from combined format ---
edges_data = read_json("edges.json")
greeter_edge = edges_data["greeter"][0]
address_edge = edges_data["address"][0]

# --- Read tool definitions ---
tool_defs = read_json("tools.json")

# --- Assemble LLM payload ---
llm_payload = {
    "model": "gpt-5.4",
    "model_temperature": 0,
    "model_high_priority": False,
    "tool_call_strict_mode": True,
    "general_prompt": general_prompt.strip(),
    "general_tools": tool_defs["general_tools"],
    "states": [
        {
            "name": "greeter",
            "state_prompt": greeter_prompt.strip(),
            "edges": [greeter_edge],
            "tools": tool_defs["states"]["greeter"]["tools"],
        },
        {
            "name": "address",
            "state_prompt": address_prompt.strip(),
            "edges": [address_edge],
            "tools": tool_defs["states"]["address"]["tools"],
        },
        {
            "name": "booking",
            "state_prompt": booking_prompt.strip(),
            "edges": [],
            "tools": tool_defs["states"]["booking"]["tools"],
        },
    ],
    "starting_state": "greeter",
    "begin_message": "British Heat Services, Tom speaking — how can I help?",
    "begin_after_user_silence_ms": 2000,
    "knowledge_base_ids": read_json("kb_ids.json"),
    "kb_config": {"top_k": 3, "filter_score": 0.6},
    "default_dynamic_variables": {},
}

# --- Summary ---
total_prompt_chars = len(general_prompt) + len(greeter_prompt) + len(address_prompt) + len(booking_prompt)
AGENT_NAME = f"UK HVAC V2.1 ({args.iteration})"

print("=== V2.1 LLM Payload Summary ===")
print(f"  Source: {SRC}")
print(f"  Model: gpt-5.4")
print(f"  general_prompt: {len(general_prompt):,} chars")
print(f"  greeter prompt: {len(greeter_prompt):,} chars")
print(f"  address prompt: {len(address_prompt):,} chars")
print(f"  booking prompt: {len(booking_prompt):,} chars")
print(f"  Total prompt chars: {total_prompt_chars:,}")
print(f"  States: greeter → address → booking")
print(f"  Greeter transitions: {greeter_edge['destination_state_name']} ({len(greeter_edge['parameters']['required'])} required vars)")
print(f"  Address transitions: {address_edge['destination_state_name']} ({len(address_edge['parameters']['required'])} required vars)")
print(f"  Greeter tools: {[t['name'] for t in tool_defs['states']['greeter']['tools']]}")
print(f"  Greeter extract vars: {len(tool_defs['states']['greeter']['tools'][0]['variables'])}")
print(f"  Address tools: {[t['name'] for t in tool_defs['states']['address']['tools']]}")
print(f"  Address extract vars: {len(tool_defs['states']['address']['tools'][0]['variables'])}")
print(f"  Booking tools: {[t['name'] for t in tool_defs['states']['booking']['tools']]}")
print(f"  Booking extract vars: {len(tool_defs['states']['booking']['tools'][2]['variables'])}")
print(f"  KBs linked: {len(read_json('kb_ids.json'))}")
print(f"  New agent name: {AGENT_NAME}")
print()
print("  Dry run — no API calls made. Pass --deploy to create LLM + agent.")

if not args.deploy:
    sys.exit(0)

# --- Deploy ---
API_KEY = os.environ.get("RETELL_API_KEY")
if not API_KEY:
    print("FATAL: Set RETELL_API_KEY env var")
    sys.exit(1)

BASE_URL = "https://api.retellai.com"

def api(method, endpoint, data=None):
    import urllib.request, urllib.error
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

print("=== Step 1: Create new LLM ===")
r = api("POST", "create-retell-llm", llm_payload)
new_llm_id = r.get("llm_id")
if not new_llm_id:
    print(f"FATAL: {r}")
    sys.exit(1)
print(f"  New LLM: {new_llm_id}")

print(f"\n=== Step 2: Create new chat agent '{AGENT_NAME}' ===")
r2 = api("POST", "create-chat-agent", {
    "agent_name": AGENT_NAME,
    "response_engine": {
        "type": "retell-llm",
        "llm_id": new_llm_id,
    },
})
new_agent_id = r2.get("agent_id")
if new_agent_id:
    print(f"  SUCCESS — new agent '{AGENT_NAME}' created: {new_agent_id}")
else:
    print(f"  Response: {json.dumps(r2, indent=2)[:200]}")

print(f"\nDone. New LLM ID: {new_llm_id}")
print(f"New chat agent ID: {new_agent_id}")
