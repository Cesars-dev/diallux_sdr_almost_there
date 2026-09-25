#!/usr/bin/env python3
"""LLM-to-LLM happy-path test for the Today Test agent.

GPT-4o plays a COOPERATIVE caller (no deflection). Two happy paths:
  TEST A: John, boiler repair tomorrow at 11:00 local
  TEST B: Sarah, boiler repair tomorrow at 14:00 local

Each injects matching dynamic variables (today_uk + customer identity + address)
so the booked name matches the caller. Extracts book_calendar time + Cal verification.
"""

import json, os, sys, urllib.request, urllib.error, time

RETELL_KEY = os.environ.get("RETELL_API_KEY")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "${OPENAI_KEY_LEGACY}")
if not RETELL_KEY:
    print("FATAL: RETELL_API_KEY not set"); sys.exit(1)

AGENT_ID = "agent_167b5c39073797673e9652c2aa"
BASE_URL = "https://api.retellai.com"


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
        print(f"  RETELL ERROR {e.code}: {err[:400]}")
        return {"_error": str(e.code)}


def call_gpt(system, history, agent_text):
    msgs = [{"role": "system", "content": system}] + list(history)
    msgs.append({"role": "user", "content": f'Agent said: "{agent_text}". Reply in <=20 words as the customer.'})
    data = json.dumps({
        "model": "gpt-4o", "messages": msgs, "temperature": 0.7, "max_tokens": 80,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=data,
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def run(label, system, opener, dynvars, expected):
    print(f"\n{'='*70}\n  {label}  (expect {expected})\n{'='*70}")
    chat = retell("POST", "create-chat", {
        "agent_id": AGENT_ID,
        "retell_llm_dynamic_variables": dynvars,
    })
    cid = chat.get("chat_id")
    if not cid:
        print(f"  FAILED create-chat: {chat}")
        return None
    print(f"  Chat: {cid}")

    caller = opener
    hist = []
    for turn in range(25):
        resp = retell("POST", "create-chat-completion", {
            "agent_id": AGENT_ID, "chat_id": cid, "content": caller,
        })
        if resp.get("_error"):
            break
        agent_text = ""
        for m in resp.get("messages", []):
            if m.get("role") == "agent":
                agent_text = m.get("content", "")
                break
        if not agent_text:
            break
        print(f"\n  C: {caller}")
        print(f"  A: {agent_text[:220]}")
        # booking fired?
        if any(m.get("name") == "book_calendar" for m in resp.get("messages", [])):
            print("  -> book_calendar fired")
            # one more caller ack so transcript closes
            time.sleep(0.5)
            retell("POST", "create-chat-completion", {"agent_id": AGENT_ID, "chat_id": cid, "content": "Great, thanks."})
            break
        if any(w in agent_text.lower() for w in ["goodbye", "bye for now", "take care"]):
            break
        hist.append({"role": "assistant", "content": caller})
        try:
            caller = call_gpt(system, hist, agent_text)
        except Exception as e:
            print(f"  GPT error: {e}")
            break
        time.sleep(0.3)

    retell("PATCH", f"end-chat/{cid}")
    full = retell("GET", f"get-chat/{cid}")
    uid = ""
    for m in full.get("message_with_tool_calls", []):
        c = m.get("content", "")
        if "Successfully booked" in c:
            import re
            uid = re.search(r"booking_uid[^A-Za-z0-9]*([A-Za-z0-9]+)", c)
            uid = uid.group(1) if uid else ""
    print(f"\n  booking_uid: {uid}  | expected {expected}")
    return cid, uid


# ── Test A — John, 11:00 ──
sysA = """You are John, calling British Heat Services for a boiler repair. Your boiler has no heating.
Name: John. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Postcode NE4 5AB.
You are free tomorrow and want the 11am slot. You want to book.
Rules: Be polite and cooperative. Give your name, phone and address when asked, one piece at a time. When the agent reads back tomorrow at 11am, say "yes" clearly. Do NOT bring up anything irrelevant. Keep replies under 20 words."""
varsA = {
    "today_uk": "2026-08-02", "customer_name": "John Smith",
    "address_house_number": "14", "address_street": "Victoria Terrace",
    "address_city": "Newcastle", "address_postcode": "NE4 5AB",
    "problem_category": "boiler_breakdown", "symptom_brief": "no heating",
    "boiler_make": "Worcester", "error_code": "F22",
}
openerA = "Hi, my boiler's not working — no heating. Can I book a repair for tomorrow at 11am?"

# ── Test B — Sarah, 14:00 ──
sysB = """You are Sarah, calling British Heat Services for a boiler repair.
Name: Sarah. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Postcode NE4 5AB.
You are free tomorrow and want the 2pm slot. You want to book.
Rules: Be polite and cooperative. Give your name, phone and address when asked, one piece at a time. When the agent reads back tomorrow at 2pm, say "yes" clearly. Do NOT bring up anything irrelevant. Keep replies under 20 words."""
varsB = dict(varsA); varsB["customer_name"] = "Sarah Smith"
openerB = "Hi, I need a boiler repair tomorrow at 2pm, please."

results = []
for label, system, opener, vars_, exp in [
    ("TEST A — 11:00 local", sysA, openerA, varsA, "2026-08-03T10:00:00.000Z"),
    ("TEST B — 14:00 local", sysB, openerB, varsB, "2026-08-03T13:00:00.000Z"),
]:
    r = run(label, system, opener, vars_, exp)
    results.append((label, r[1], exp))

print("\n" + "="*70)
for label, uid, exp in results:
    print(f"{label}: booking_uid={uid}  expect Cal start {exp}")
