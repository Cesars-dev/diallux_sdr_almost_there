#!/usr/bin/env python3
"""LLM-to-LLM test: GPT-4o caller vs V3 chat agent.

Usage:
  export RETELL_API_KEY=key_...
  python3 test_v3_llm_to_llm.py

Runs 5 scenarios via LLM-driven conversation.
"""

import json, os, sys, urllib.request, urllib.error, time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

RETELL_KEY = os.environ.get("RETELL_API_KEY")
OPENAI_KEY = "${OPENAI_KEY_LEGACY}"
CHAT_AGENT = "agent_f604cbfc7107ea3e6c779d4d09"

BASE_URL = "https://api.retellai.com"

def retell(method, endpoint, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        f"{BASE_URL}/{endpoint}", data=body, method=method,
        headers={"Authorization": f"Bearer {RETELL_KEY}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
        return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  RETELL ERROR {e.code}: {err[:300]}")
        return {"_error": str(e.code)}

def call_gpt(system, history, agent_text):
    url = "https://api.openai.com/v1/chat/completions"
    msgs = [{"role": "system", "content": system}] + list(history)
    msgs.append({
        "role": "user",
        "content": f"Agent said: \"{agent_text}\"\nReply in <=20 words as the customer."
    })
    data = json.dumps({
        "model": "gpt-4o", "messages": msgs, "temperature": 0.7, "max_tokens": 80
    }).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()

def run_scenario(name, system_prompt, first_msg, dynvars=None):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

    create_data = {"agent_id": CHAT_AGENT}
    if dynvars:
        create_data["retell_llm_dynamic_variables"] = dynvars
    chat = retell("POST", "create-chat", create_data)
    cid = chat.get("chat_id")
    if not cid:
        print(f"  FAILED to create chat: {chat}")
        return None, None
    print(f"  Chat: {cid}")

    caller = first_msg
    hist = []
    transcript = []
    booking_uid = None

    for turn in range(25):
        print(f"\n  --- Turn {turn+1} ---")
        print(f"  C: {caller[:200]}")

        resp = retell("POST", "create-chat-completion", {
            "agent_id": CHAT_AGENT, "chat_id": cid, "content": caller
        })
        if resp.get("_error"):
            print(f"  RETELL ERROR stopping")
            break

        agent_text = ""
        for msg in resp.get("messages", []):
            if msg.get("role") == "agent":
                agent_text = msg.get("content", "")
                break

        # Detect booking + extract UID
        has_book_call = any(m.get("name") == "book_calendar" for m in resp.get("messages", []) if m.get("role") == "tool_call_invocation")
        for m in resp.get("messages", []):
            if m.get("role") == "tool_call_result" and "Successfully booked" in m.get("content", ""):
                import re
                m2 = re.search(r"booking_uid[^A-Za-z0-9]*([A-Za-z0-9]+)", m.get("content", ""))
                booking_uid = m2.group(1) if m2 else booking_uid

        if agent_text:
            print(f"  A: {agent_text[:300]}")
            transcript.append(("agent", agent_text))
        else:
            # Agent is mid-tool (e.g. check_availability) and hasn't spoken yet.
            # Use a neutral backchannel, NOT "Okay.", so it can't be read as confirmation.
            print(f"  (no agent speech — agent working on tools, nudging to continue)")
            caller = "Mm-hmm."
            continue

        has_end_call = any(m.get("name") == "end_call" for m in resp.get("messages", []) if m.get("role") == "tool_call_invocation")
        if has_end_call:
            print(f"  [end_call FIRED]")
            transcript.append(("system", "end_call fired"))
            break
        if has_book_call:
            print(f"  [book_calendar FIRED — booking succeeded]")
            transcript.append(("system", "book_calendar fired"))
            break

        if turn + 1 >= 25:
            print(f"  [Max turns reached]")
            break

        # Get next caller response
        hist.append({"role": "assistant", "content": caller})
        try:
            caller = call_gpt(system_prompt, hist, agent_text)
            if len(caller) > 300:
                caller = caller[:300]
        except Exception as e:
            print(f"  GPT error: {e}")
            break

        time.sleep(0.3)

    print(f"\n  --- Result ---")
    print(f"  Turns: {turn+1} | booking_uid: {booking_uid}")

    # End chat
    retell("PATCH", f"end-chat/{cid}")

    try:
        chat_full = retell("GET", f"get-chat/{cid}")
        cost = chat_full.get("chat_cost", {}).get("combined_cost", "?")
        print(f"  Cost: {cost}c")
    except:
        pass

    print(f"{'='*60}")
    return cid, booking_uid


# ── 2 Happy-Path Scenarios (clean, cooperative callers) ──

TODAY_ENDPOINT = "https://slots.diallux-ai.site/time-function/today"


def _today_uk() -> str:
    """Today's date (YYYY-MM-DD) from the /today source of truth (Europe/London).

    The slot webhook rejects a blank slot_target_date (no_start_time), so this
    must never return empty. Primary: GET /today (the canonical day value).
    Fallback: local ZoneInfo Europe/London; last resort: UTC date.
    """
    try:
        req = urllib.request.Request(f"{TODAY_ENDPOINT}?tz=Europe/London")
        with urllib.request.urlopen(req, timeout=5) as r:
            body = json.loads(r.read().decode())
            if body.get("ok") and body.get("today"):
                return str(body["today"])
    except Exception:
        pass
    try:
        return datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


COMMON_VARS = {
    "today_uk": _today_uk(),
    "address_house_number": "14", "address_street": "Victoria Terrace",
    "address_city": "Newcastle", "address_postcode": "NE4 5AB",
    "problem_category": "boiler_breakdown", "symptom_brief": "no heating",
    "boiler_make": "Worcester", "error_code": "F22",
}

scenarios = [
    (
        "TEST A — John, boiler breakdown, morning slot",
        """You are John, a stressed but polite homeowner in Newcastle. Your boiler has gone off — no heating, no hot water.
Name: John. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911111111.
You are free tomorrow all day and would prefer a morning appointment.

Rules — behave like a REAL caller, not a script:
- You have NOT booked anything yet. You called for help, so describe the problem naturally.
- Do NOT mention or request a specific appointment time in your opening message.
- When the agent offers available slots, say a morning slot (e.g. 11am) suits you.
- ONLY once the agent reads a specific slot back and asks you to confirm, answer with a clear "yes" sentence like "Yes, that's fine" or "Yes, go ahead".
- A bare "okay" or "mm-hmm" is not enough — actually affirm out loud.
- Keep every reply under 20 words, natural and human.""",
        "Hi, my boiler's gone off. We've got no heating and no hot water at all. Can you help?",
        dict(COMMON_VARS, customer_name="John Smith"),
        "2026-08-03T10:00:00.000Z",
    ),
    (
        "TEST B — Sarah, boiler breakdown, afternoon slot",
        """You are Sarah, a polite homeowner in Newcastle. Your boiler has stopped — no heating.
Name: Sarah. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911222222.
You are free tomorrow all day and would prefer an afternoon appointment.

Rules — behave like a REAL caller, not a script:
- You have NOT booked anything yet. Describe the problem naturally.
- Do NOT mention or request a specific appointment time in your opening message.
- When the agent offers available slots, say an afternoon slot (e.g. 2pm) suits you.
- ONLY once the agent reads a specific slot back and asks you to confirm, answer with a clear "yes" sentence like "Yes, that works" or "Yes, book it".
- A bare "okay" or "mm-hmm" is not enough — actually affirm out loud.
- Keep every reply under 20 words, natural and human.""",
        "Hi, I think my boiler's broken. There's no heating coming on at all. Can someone take a look?",
        dict(COMMON_VARS, customer_name="Sarah Smith"),
        "2026-08-03T13:00:00.000Z",
    ),
]

results = []
for name, system, opener, dynvars, expected in scenarios:
    cid, uid = run_scenario(name, system, opener, dynvars)
    results.append((name, uid, expected))
    if cid:
        print(f"\n=== FULL DUMP: {name} ===")
        chat_full = retell("GET", f"get-chat/{cid}")
        print(f"\nTranscript:\n{chat_full.get('transcript', '')}\n")
        print(f"Cost: {chat_full.get('chat_cost', {}).get('combined_cost', '?')}c")
        print("\n=== TOOL CALLS & STATE TRANSITIONS ===")
        for msg in chat_full.get("message_with_tool_calls", []):
            role = msg.get("role", "?")
            nm = msg.get("name", "")
            content = msg.get("content", "")
            if role == "tool_call_invocation":
                print(f"  TOOL CALL: {nm}")
            elif role == "agent":
                print(f"  AGENT: {content[:150]}")
            elif role == "tool_call_result":
                print(f"  TOOL RESULT: {nm} — {content[:100]}")
            elif role == "state_transition":
                print(f"  STATE TRANSITION: {msg.get('content','')[:100]}")
            else:
                print(f"  {role}: {content[:100] if content else nm}")
        print()

print("\n" + "=" * 70)
for name, uid, expected in results:
    print(f"{name}\n  booking_uid={uid}\n  EXPECTED Cal start: {expected}")
print("\n=== ALL SCENARIOS COMPLETE ===")
