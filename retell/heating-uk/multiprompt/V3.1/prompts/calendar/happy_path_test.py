#!/usr/bin/env python3
"""Happy-path test for the Today Test agent (agent_67ac6e033ab6dbc4360d414995).

Drives a chat via create-chat (injecting today_uk + dummy vars) + create-chat-completion,
then reads get-chat to extract book_calendar.arguments.time. Ends the chat after.
"""

import json, os, sys, urllib.request, urllib.error, time

RETELL_KEY = os.environ.get("RETELL_API_KEY")
if not RETELL_KEY:
    print("FATAL: RETELL_API_KEY not set")
    sys.exit(1)

AGENT_ID = "agent_167b5c39073797673e9652c2aa"
BASE_URL = "https://api.retellai.com"

DUMMY_VARS = {
    "today_uk": "2026-08-02",
    "customer_name": "John Smith",
    "address_house_number": "14",
    "address_street": "Victoria Terrace",
    "address_city": "Newcastle",
    "address_postcode": "NE4 5AB",
    "problem_category": "boiler_breakdown",
    "symptom_brief": "no heating",
    "boiler_make": "Worcester",
    "error_code": "F22",
}


def retell(method, endpoint, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        f"{BASE_URL}/{endpoint}", data=body, method=method,
        headers={"Authorization": f"Bearer {RETELL_KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
        return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  RETELL ERROR {e.code}: {err[:500]}")
        return {"_error": str(e.code)}


def run_test(label, turns, expected_time):
    print(f"\n{'='*70}\n  {label}  (expect book time {expected_time})\n{'='*70}")
    chat = retell("POST", "create-chat", {
        "agent_id": AGENT_ID,
        "retell_llm_dynamic_variables": DUMMY_VARS,
    })
    cid = chat.get("chat_id")
    if not cid:
        print(f"  FAILED to create chat: {json.dumps(chat, indent=2)[:800]}")
        return
    print(f"  Chat: {cid}")

    for i, u in enumerate(turns, 1):
        print(f"\n  --- Turn {i}: C: {u}")
        resp = retell("POST", "create-chat-completion", {
            "agent_id": AGENT_ID, "chat_id": cid, "content": u,
        })
        if resp.get("_error"):
            print(f"  stop on error")
            break
        for msg in resp.get("messages", []):
            role = msg.get("role")
            if role == "agent":
                print(f"  A: {msg.get('content','')[:200]}")
            elif role == "tool_call_invocation":
                print(f"  TOOL: {msg.get('name')} {json.dumps(msg.get('parameters'))}")
            elif role == "state_transition":
                print(f"  STATE: {msg.get('content','')[:100]}")
        time.sleep(0.5)

    full = retell("GET", f"get-chat/{cid}")
    found = []
    for msg in full.get("message_with_tool_calls", []):
        if msg.get("role") == "tool_call_invocation" and msg.get("name") == "book_calendar":
            params = msg.get("parameters") or {}
            t = params.get("time")
            if t:
                found.append(t)
    print(f"\n  book_calendar.time value(s): {found}")
    print(f"  EXPECTED: {expected_time}  ->  {'PASS' if expected_time in found else 'CHECK'}")

    retell("PATCH", f"end-chat/{cid}")
    print(f"  ended chat {cid}")
    return cid


if __name__ == "__main__":
    test = sys.argv[1] if len(sys.argv) > 1 else "A"
    if test.upper() == "A":
        run_test(
            "TEST A — 11:00 local tomorrow",
            [
                "I need a boiler repair tomorrow.",
                "11am tomorrow is good.",
                "Name John, phone +447911111111.",
                "Yes confirm.",
            ],
            "2026-08-03T11:00:00",
        )
    else:
        run_test(
            "TEST B — 14:00 local tomorrow",
            [
                "I need a boiler repair tomorrow.",
                "2pm tomorrow is good.",
                "Name Sarah, phone +447911222222.",
                "Yes confirm.",
            ],
            "2026-08-03T14:00:00",
        )
