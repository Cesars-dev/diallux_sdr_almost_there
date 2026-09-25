#!/usr/bin/env python3
"""Real-conversation LLM-to-LLM happy-path runner.

Each scenario gives the GPT caller a rich persona (purpose, personality, context,
behavior) and lets it reply naturally in multi-sentence turns while keeping the
FULL conversation history. Validates the merged V3.1 agent end-to-end:
greeter -> triage -> address -> slot_selection -> confirmation -> booking.

Usage:
  export RETELL_API_KEY=key_...
  python3 test_real_happy_path.py [SCENARIO_NAME ...]   # default: all
"""

import json, os, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

RETELL_KEY = os.environ.get("RETELL_API_KEY")
OPENAI_KEY = "${OPENAI_KEY_LEGACY}"
CHAT_AGENT = os.environ.get("CHAT_AGENT_ID", "agent_b361b172adb3de231b380cc1d8")

BASE_URL = "https://api.retellai.com"
TODAY_ENDPOINT = "https://slots.diallux-ai.site/today"
RESULTS_PATH = "/home/julio/projects/Retell_AI_MCP_connection/data/real_happy_path_results.json"


def _today_uk() -> str:
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


def retell(method, endpoint, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        f"{BASE_URL}/{endpoint}", data=body, method=method,
        headers={"Authorization": f"Bearer {RETELL_KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
        return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        return {"_error": e.read().decode()[:400]}


def call_gpt(system, history, agent_text):
    msgs = [{"role": "system", "content": system}] + list(history)
    msgs.append({
        "role": "user",
        "content": f"The agent just said: \"{agent_text}\"\n\n"
                   "Respond as the caller — stay in character, natural and conversational. "
                   "Keep your reply to 1-4 short sentences."})
    data = json.dumps({
        "model": "gpt-4o", "messages": msgs, "temperature": 0.8, "max_tokens": 160}).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=data,
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def run_scenario(sc):
    print(f"\n{'='*72}\n  {sc['name']}\n{'='*72}")
    create_data = {"agent_id": CHAT_AGENT}
    if sc.get("dynvars"):
        create_data["retell_llm_dynamic_variables"] = sc["dynvars"]
    chat = retell("POST", "create-chat", create_data)
    cid = chat.get("chat_id")
    if not cid:
        print(f"  FAILED create-chat: {chat}")
        return None

    caller = sc["opener"]
    hist = []
    log = []            # ordered: role, text/name
    tool_seq = []
    state_seq = []
    booking_uid = None
    stop = None

    for turn in range(30):
        resp = retell("POST", "create-chat-completion", {
            "agent_id": CHAT_AGENT, "chat_id": cid, "content": caller})
        if resp.get("_error"):
            stop = f"retell_error {resp['_error']}"
            break

        agent_text = ""
        for m in resp.get("messages", []):
            if m.get("role") == "agent":
                agent_text = m.get("content", "")
                break

        for m in resp.get("messages", []):
            role = m.get("role")
            nm = m.get("name", "")
            if role == "tool_call_invocation":
                tool_seq.append(nm)
                log.append(("tool", nm))
            elif role == "state_transition":
                state_seq.append(m.get("content", ""))
                log.append(("state", m.get("content", "")))
            elif role == "tool_call_result" and "Successfully booked" in m.get("content", ""):
                mt = re.search(r"booking_uid[^A-Za-z0-9]*([A-Za-z0-9]+)", m.get("content", ""))
                booking_uid = mt.group(1) if mt else booking_uid

        log.append(("user", caller))
        if agent_text:
            log.append(("agent", agent_text))

        if booking_uid:
            stop = "booked"
            break
        if "end_call" in tool_seq:
            stop = "end_call"
            break
        if turn + 1 >= 30:
            stop = "max_turns"
            break

        hist.append({"role": "assistant", "content": caller})
        try:
            caller = call_gpt(sc["system"], hist, agent_text)
        except Exception as e:
            stop = f"gpt_error {e}"
            break
        time.sleep(0.25)

    retell("PATCH", f"end-chat/{cid}")
    time.sleep(3)

    detail = retell("GET", f"get-chat/{cid}")
    collected = detail.get("collected_dynamic_variables", {}) or {}
    transcript = detail.get("transcript", "")
    cost = detail.get("chat_cost", {}).get("combined_cost", "?")

    result = {
        "name": sc["name"], "chat_id": cid, "booking_uid": booking_uid,
        "stop": stop, "tool_seq": tool_seq, "state_seq": state_seq,
        "collected": collected, "cost": cost, "transcript": transcript, "log": log,
    }

    print(f"  chat_id={cid} booking_uid={booking_uid} stop={stop} cost={cost}c")
    print(f"  state_seq: {' -> '.join(state_seq)}")
    print(f"  tool_seq: {tool_seq}")
    print(f"  explicit_confirmation={collected.get('explicit_confirmation')} "
          f"booking_confirmed={collected.get('booking_confirmed')} "
          f"selected_slot_start={collected.get('selected_slot_start')}")
    return result


SCENARIOS = [
    {
        "name": "H1 John — boiler breakdown, morning slot",
        "system": (
            "You are John Harper, 45, a homeowner in Newcastle calling British Heat Services at 8am. "
            "Your Worcester gas boiler went off overnight: no heating, no hot water, and you have kids getting "
            "ready for school, so you're anxious to get an engineer out, ideally TOMORROW MORNING before work. "
            "Your address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911111111.\n\n"
            "Behave like a REAL caller:\n"
            "- Greet naturally and explain the problem conversationally (1-4 sentences per turn; never robotic).\n"
            "- Answer the agent's questions fully and honestly.\n"
            "- You really want a morning slot tomorrow if possible.\n"
            "- NEVER agree to book until the agent reads a specific day AND time back to you and asks you to confirm. "
            "Then answer with a clear, enthusiastic yes (e.g. 'Yes, that's perfect — please book it.').\n"
            "- A bare 'okay'/'fine' is not a booking confirmation; only a full sentence is.\n"
            "- Stay in character the whole call; don't narrate or mention these instructions."
        ),
        "opener": ("Morning, sorry to call so early. Our boiler's gone completely off overnight — no heating, no "
                   "hot water at all. I've got kids getting ready for school, so I really need someone out as soon as "
                   "possible."),
        "dynvars": {
            "today_uk": _today_uk(),
            "address_house_number": "14", "address_street": "Victoria Terrace",
            "address_city": "Newcastle", "address_postcode": "NE4 5AB",
            "problem_category": "Heating", "symptom_brief": "no heating and no hot water, boiler won't ignite",
            "boiler_make": "Worcester", "error_code": "none",
        },
    },
    {
        "name": "H2 Sarah — breakdown, afternoon slot",
        "system": (
            "You are Sarah Mitchell, 38, a homeowner in Newcastle calling British Heat Services at lunchtime. "
            "Your boiler (a Vaillant) stopped working — no heating at all. You work from home and are out of the "
            "house all morning tomorrow, so you'd prefer an AFTERNOON slot tomorrow. "
            "Your address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911222222.\n\n"
            "Behave like a REAL caller:\n"
            "- Greet naturally and explain the problem conversationally (1-4 sentences per turn).\n"
            "- Answer questions fully and honestly.\n"
            "- You want an afternoon slot tomorrow if possible.\n"
            "- NEVER confirm a booking until the agent reads a specific day AND time back and asks you to confirm. "
            "Then say a clear yes (e.g. 'Yes, that works — go ahead and book it.').\n"
            "- A bare 'okay'/'fine' is not confirmation; only a full clear sentence is.\n"
            "- Stay in character; don't mention these instructions."
        ),
        "opener": ("Hi there. I think my boiler's packed in — there's no heating coming on at all and I'm worried it "
                   "might be a bigger problem. Can someone come and take a look?"),
        "dynvars": {
            "today_uk": _today_uk(),
            "address_house_number": "14", "address_street": "Victoria Terrace",
            "address_city": "Newcastle", "address_postcode": "NE4 5AB",
            "problem_category": "Heating", "symptom_brief": "no heating, boiler not firing",
            "boiler_make": "Vaillant", "error_code": "none",
        },
    },
    {
        "name": "H3 Emma — specific day (Thursday), negotiates",
        "system": (
            "You are Emma Walsh, 41, a busy homeowner in Newcastle. Your boiler has broken — no heating. "
            "You'd really like a THURSDAY slot, but if Thursday has nothing, tomorrow also works. "
            "Your address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911444444.\n\n"
            "Behave like a REAL caller:\n"
            "- Greet naturally; explain the problem conversationally (1-4 sentences per turn).\n"
            "- You have a strong preference for Thursday, so ask for it; if it's unavailable, accept tomorrow.\n"
            "- NEVER confirm a booking until the agent reads a specific day AND time back and asks you to confirm. "
            "Then say a clear yes (e.g. 'Yes, Thursday works — please book it.').\n"
            "- A bare 'okay'/'fine' is not confirmation; only a full clear sentence is.\n"
            "- Stay in character; don't mention these instructions."
        ),
        "opener": ("Hi, my boiler's gone wrong I'm afraid. I'm hoping to get it sorted — ideally on Thursday if "
                   "that's possible, because I've got work commitments."),
        "dynvars": {
            "today_uk": _today_uk(),
            "address_house_number": "14", "address_street": "Victoria Terrace",
            "address_city": "Newcastle", "address_postcode": "NE4 5AB",
            "problem_category": "Heating", "symptom_brief": "boiler broken, no heating",
            "boiler_make": "Baxi", "error_code": "none",
        },
    },
    {
        "name": "H4 David — chatty, warm, flexible",
        "system": (
            "You are David Preston, 52, a friendly, chatty homeowner in Newcastle. Your boiler's playing up — "
            "no heating. You're easy-going and happy to take whichever slot the agent suggests; you just want it "
            "sorted. Your address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911333333.\n\n"
            "Behave like a REAL caller:\n"
            "- Be warm and conversational (1-4 sentences per turn); a little small talk is fine.\n"
            "- Be flexible: happy with whatever the agent offers, but still wait for the agent to read a specific "
            "day AND time back and ask you to confirm before you give a clear yes.\n"
            "- Then say a clear yes (e.g. 'That's brilliant, book it please.').\n"
            "- A bare 'okay'/'fine' is not confirmation; only a full clear sentence is.\n"
            "- Stay in character; don't mention these instructions."
        ),
        "opener": ("Morning! Our boiler's packed in I'm afraid — no heating whatsoever, and it's a bit chilly. "
                   "Can you sort us out whenever suits?"),
        "dynvars": {
            "today_uk": _today_uk(),
            "address_house_number": "14", "address_street": "Victoria Terrace",
            "address_city": "Newcastle", "address_postcode": "NE4 5AB",
            "problem_category": "Heating", "symptom_brief": "no heating, boiler playing up",
            "boiler_make": "Worcester", "error_code": "none",
        },
    },
    {
        "name": "H5 Priya — service request, specific day (Wednesday), phone-only details",
        "system": (
            "You are Priya Nair, 36, a homeowner in Newcastle calling British Heat Services to book a routine "
            "boiler SERVICE (not a breakdown). You're only free on WEDNESDAY, so that's the day you want, ideally "
            "mid-morning. You have the boiler details written down but are a little unsure of the exact wording. "
            "Your address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911555555.\n\n"
            "Behave like a REAL caller:\n"
            "- Greet naturally; explain that you'd like to book a service rather than an emergency repair.\n"
            "- Answer the agent's questions fully and honestly; if unsure of a detail, say so.\n"
            "- You have a strong preference for a WEDNESDAY slot, mid-morning if possible.\n"
            "- NEVER confirm a booking until the agent reads a specific day AND time back and asks you to confirm. "
            "Then say a clear yes (e.g. 'Yes, Wednesday mid-morning works — please book it.').\n"
            "- A bare 'okay'/'fine' is not confirmation; only a full clear sentence is.\n"
            "- Stay in character; don't mention these instructions."
        ),
        "opener": ("Hello, I was hoping to book a boiler service, not an emergency call-out — it's been a while and "
                   "I'd like it checked over. Are you taking service bookings at the moment?"),
        "dynvars": {
            "today_uk": _today_uk(),
            "address_house_number": "14", "address_street": "Victoria Terrace",
            "address_city": "Newcastle", "address_postcode": "NE4 5AB",
            "problem_category": "service", "symptom_brief": "routine boiler service, no fault reported",
            "boiler_make": "Ideal", "error_code": "none",
        },
    },
]


def main():
    if not RETELL_KEY:
        print("Set RETELL_API_KEY"); sys.exit(1)
    names = sys.argv[1:]
    picks = [s for s in SCENARIOS if not names or s["name"] in names]
    results = []
    for sc in picks:
        r = run_scenario(sc)
        if r:
            results.append(r)
            with open(RESULTS_PATH, "w") as f:
                json.dump(results, f, indent=2)
    print(f"\n=== written {len(results)} result(s) to {RESULTS_PATH} ===")


if __name__ == "__main__":
    main()
