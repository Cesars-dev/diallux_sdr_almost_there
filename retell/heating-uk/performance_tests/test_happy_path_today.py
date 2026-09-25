#!/usr/bin/env python3
"""LLM-to-LLM happy-path test for the V3.1 '{{today}}' agent.

GPT-4o plays a COOPERATIVE caller (no deflection). Two happy paths:
  TEST A: John, boiler repair
  TEST B: Sarah, boiler repair

The injected date variable is the agent-agnostic {{today}} (from the time
service), NOT {{today_uk}}. Each injects matching dynamic variables
(today + customer identity + address) so the booked name matches the caller.
Callers confirm WHICHEVER slot the agent offers (live availability varies),
so no fixed time is asserted. Success = book_calendar fires with a non-empty
time / booking_uid.

Usage:
  set -a; source .env; set +a
  python3 test_happy_path_today.py
"""

import json, os, re, sys, urllib.request, urllib.error, time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

RETELL_KEY = os.environ.get("RETELL_API_KEY")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "${OPENAI_KEY_LEGACY}")
if not RETELL_KEY:
    print("FATAL: RETELL_API_KEY not set"); sys.exit(1)

# T3 output — the new chat agent bound to the V3.1 {{today}} LLM.
AGENT_ID = "agent_c7582c8ecda1f047f7a575c59b"

# Timezone is parametric: change TZ to test an agent in another timezone.
TZ = "Europe/London"
BASE_URL = "https://api.retellai.com"
TODAY_ENDPOINT = "https://slots.diallux-ai.site/time-function/today"


def _today(tz: str = "Europe/London") -> str:
    """Today's date (YYYY-MM-DD) in the given IANA timezone.

    Primary: GET /time-function/today?tz=<tz> (the canonical day value).
    Fallback: datetime.now(ZoneInfo(tz)); last resort: UTC date.
    """
    try:
        req = urllib.request.Request(f"{TODAY_ENDPOINT}?tz={tz}")
        with urllib.request.urlopen(req, timeout=5) as r:
            body = json.loads(r.read().decode())
            if body.get("ok") and body.get("today"):
                return str(body["today"])
    except Exception:
        pass
    try:
        return datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


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


def run(label, system, opener, dynvars):
    print(f"\n{'='*70}\n  {label}\n{'='*70}")
    chat = retell("POST", "create-chat", {
        "agent_id": AGENT_ID,
        "retell_llm_dynamic_variables": dynvars,
    })
    cid = chat.get("chat_id")
    if not cid:
        print(f"  FAILED create-chat: {chat}")
        return None, "", False
    print(f"  Chat: {cid}")

    caller = opener
    hist = []
    fired = False
    for turn in range(40):
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
            # agent still processing — retry this turn instead of giving up
            time.sleep(1.5)
            continue
        print(f"\n  C: {caller}")
        print(f"  A: {agent_text[:220]}")
        # booking fired? (book_calendar with a non-empty time)
        for m in resp.get("messages", []):
            if m.get("name") == "book_calendar":
                args = m.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                if args.get("time"):
                    fired = True
                    print("  -> book_calendar fired with time:", args["time"])
                    break
        if fired:
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
            m2 = re.search(r"booking_uid[^A-Za-z0-9]*([A-Za-z0-9]+)", c)
            uid = m2.group(1) if m2 else ""
    print(f"\n  booking_uid: {uid}  | book_calendar fired: {fired}")
    return cid, uid, fired


# ── Test A — John ──
sysA = """You are John, calling British Heat Services for a boiler repair. Your boiler has no heating.
Name: John. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Postcode NE4 5AB.
You are free tomorrow and want to book. You want to book.
Rules: Be polite and cooperative. Give your name, phone and address when asked, one piece at a time. Accept and confirm WHICHEVER slot time the agent offers (availability varies) — do not insist on a specific time. Say "yes" to the read-back clearly. Do NOT bring up anything irrelevant. Keep replies under 20 words."""

# ── Test B — Sarah ──
sysB = """You are Sarah, calling British Heat Services for a boiler repair.
Name: Sarah. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Postcode NE4 5AB.
You are free tomorrow and want to book. You want to book.
Rules: Be polite and cooperative. Give your name, phone and address when asked, one piece at a time. Accept and confirm WHICHEVER slot time the agent offers (availability varies) — do not insist on a specific time. Say "yes" to the read-back clearly. Do NOT bring up anything irrelevant. Keep replies under 20 words."""

today = _today(TZ)
print(f"Using today = {today} (tz={TZ})")

varsA = {
    "today": today, "customer_name": "John Smith",
    "address_house_number": "14", "address_street": "Victoria Terrace",
    "address_city": "Newcastle", "address_postcode": "NE4 5AB",
    "problem_category": "boiler_breakdown", "symptom_brief": "no heating",
    "boiler_make": "Worcester", "error_code": "F22",
}
openerA = "Hi, my boiler's not working — no heating. Can I book a repair?"

varsB = dict(varsA); varsB["customer_name"] = "Sarah Smith"
openerB = "Hi, I need a boiler repair, please."

results = []
for label, system, opener, vars_ in [
    ("TEST A — John", sysA, openerA, varsA),
    ("TEST B — Sarah", sysB, openerB, varsB),
]:
    cid, uid, fired = run(label, system, opener, vars_)
    results.append((label, uid, fired))

print("\n" + "="*70)
for label, uid, fired in results:
    print(f"{label}: booking_uid={uid}  book_calendar fired={fired}")

ok = all(fired for _, _, fired in results) and any(uid for _, uid, _ in results)
print("\nRESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
