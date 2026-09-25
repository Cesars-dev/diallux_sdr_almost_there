#!/usr/bin/env python3
"""10-scenario LLM-to-LLM suite against the calendar test agent.

5 cooperative happy paths (agent must confirm + book only after explicit yes)
5 tricky paths (agent must HOLD — never book, never go off script, re-ask on
   ambiguous/backchannell "yes", steer back on tangents).

Runs one scenario at a time, stores chat_id + live tool/state flow, then
AWAITS (sleeps) before fetching get-chat transcripts (avoids the
read-after-end empty-transcript artifact), then grades each scenario.

Usage:
  export RETELL_API_KEY=key_...
  python3 test_v3_10_scenarios.py
"""

import json, os, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

RETELL_KEY = os.environ.get("RETELL_API_KEY")
OPENAI_KEY = "${OPENAI_KEY_LEGACY}"
CHAT_AGENT = "agent_f604cbfc7107ea3e6c779d4d09"

BASE_URL = "https://api.retellai.com"
RESULTS_PATH = "/home/julio/projects/Retell_AI_MCP_connection/data/ten_scenario_results.json"

YES_RE = re.compile(r"\b(yes|yeah|yep|correct|right|fine|sounds good|go ahead|book it|book that|perfect|great|that works|please)\b", re.I)
READBACK_RE = re.compile(r"\b(shall i|go ahead|book that|book it|confirm|that work|does that work|is that right|correct\?|okay\?)\b", re.I)
AMBIG_RE = re.compile(r"^.*\b(uhm|mm-hmm|uh-huh|erm|hmm|i guess|i suppose|i think so|not sure)\b.*$", re.I)


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
        err = e.read().decode()
        print(f"  RETELL ERROR {e.code}: {err[:300]}")
        return {"_error": str(e.code)}


def call_gpt(system, history, agent_text):
    url = "https://api.openai.com/v1/chat/completions"
    msgs = [{"role": "system", "content": system}] + list(history)
    msgs.append({
        "role": "user",
        "content": f"Agent said: \"{agent_text}\"\nReply in <=20 words as the customer."})
    data = json.dumps({
        "model": "gpt-4o", "messages": msgs, "temperature": 0.7, "max_tokens": 80}).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def run_scenario(name, tag, expect_book, system, opener, dynvars=None):
    print(f"\n{'='*64}\n  {name}\n  tag={tag} expect_book={expect_book}\n{'='*64}")
    create_data = {"agent_id": CHAT_AGENT}
    if dynvars:
        create_data["retell_llm_dynamic_variables"] = dynvars
    chat = retell("POST", "create-chat", create_data)
    cid = chat.get("chat_id")
    if not cid:
        print(f"  FAILED to create chat: {chat}")
        return None

    caller = opener
    hist = []
    turns = []          # ordered log for analysis
    tool_seq = []       # ordered tool_call names + results
    booking_uid = None
    stop_reason = None

    for turn_no in range(25):
        resp = retell("POST", "create-chat-completion", {
            "agent_id": CHAT_AGENT, "chat_id": cid, "content": caller})
        if resp.get("_error"):
            stop_reason = "retell_error"
            break

        agent_text = ""
        for msg in resp.get("messages", []):
            if msg.get("role") == "agent":
                agent_text = msg.get("content", "")
                break

        # capture tool calls / state transitions this turn
        for msg in resp.get("messages", []):
            role = msg.get("role")
            if role == "tool_call_invocation":
                nm = msg.get("name", "")
                tool_seq.append(nm)
                if nm == "book_calendar":
                    turns.append({"role": "system", "text": "book_calendar"})
                elif nm == "end_call":
                    turns.append({"role": "system", "text": "end_call"})
                else:
                    turns.append({"role": "tool", "name": nm})
            elif role == "state_transition":
                turns.append({"role": "state", "text": msg.get("content", "")})
            elif role == "tool_call_result":
                content = msg.get("content", "")
                if "Successfully booked" in content:
                    m = re.search(r"booking_uid[^A-Za-z0-9]*([A-Za-z0-9]+)", content)
                    booking_uid = m.group(1) if m else booking_uid

        # record the submitted user message
        turns.append({"role": "user", "text": caller, "synthetic": caller == "Mm-hmm."})

        if agent_text:
            turns.append({"role": "agent", "text": agent_text})
        else:
            print(f"  (no agent speech — nudging)")
            caller = "Mm-hmm."
            continue

        if "book_calendar" in tool_seq:
            stop_reason = "booked"
            break
        if "end_call" in tool_seq:
            stop_reason = "end_call"
            break
        if turn_no + 1 >= 25:
            stop_reason = "max_turns"
            break

        # next real caller reply (do NOT feed nudges into caller memory)
        hist.append({"role": "assistant", "content": caller})
        try:
            caller = call_gpt(system, hist, agent_text)
            if len(caller) > 300:
                caller = caller[:300]
        except Exception as e:
            print(f"  GPT error: {e}")
            stop_reason = "gpt_error"
            break
        time.sleep(0.3)

    retell("PATCH", f"end-chat/{cid}")
    result = {
        "name": name, "tag": tag, "expect_book": expect_book, "chat_id": cid,
        "booking_uid": booking_uid, "turns": turns, "tool_seq": tool_seq,
        "stop_reason": stop_reason, "transcript": "", "grade": "", "reason": ""}
    print(f"  chat_id={cid} booking_uid={booking_uid} stop={stop_reason}")
    return result


def analyze(r):
    turns = r["turns"]
    book_idx = next((i for i, t in enumerate(turns)
                     if t["role"] == "system" and t["text"] == "book_calendar"), None)
    real_users = [i for i, t in enumerate(turns) if t["role"] == "user" and not t.get("synthetic")]
    before_book = turns[:book_idx] if book_idx is not None else turns
    agent_before = [t["text"] for t in before_book if t["role"] == "agent"]
    readback = any(READBACK_RE.search(a) for a in agent_before)
    last_real_user = turns[real_users[-1]]["text"] if real_users else ""
    explicit_yes = bool(YES_RE.search(last_real_user)) if book_idx is not None else False
    held_after_ambiguous = False
    if book_idx is None:
        ambig_agent = [a for a in agent_before if a]
        held_after_ambiguous = bool(ambig_agent)

    if r["expect_book"]:
        if r["booking_uid"] is None:
            r["grade"], r["reason"] = "FAIL", "expected a booking but none happened"
        elif book_idx is None:
            r["grade"], r["reason"] = "FAIL", "book_calendar not in flow"
        elif not explicit_yes:
            r["grade"], r["reason"] = "FAIL", "booked WITHOUT an explicit caller yes (premature)"
        elif not readback:
            r["grade"], r["reason"] = "WARN", "booked + explicit yes, but no read-back/confirmation question detected"
        else:
            r["grade"], r["reason"] = "PASS", "booked after read-back + explicit yes"
    else:
        if r["booking_uid"] is not None:
            r["grade"], r["reason"] = "FAIL", "booked when it should have HELD (off script / premature)"
        elif "end_call" in r["tool_seq"]:
            r["grade"], r["reason"] = "PASS", "held — no booking, closed gracefully"
        else:
            r["grade"], r["reason"] = "PASS", "held — no booking; kept steering/asking"
    return r


TODAY_ENDPOINT = "https://slots.diallux-ai.site/today"


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


COMMON = {
    "today_uk": _today_uk(),
    "address_house_number": "14", "address_street": "Victoria Terrace",
    "address_city": "Newcastle", "address_postcode": "NE4 5AB",
    "problem_category": "boiler_breakdown", "symptom_brief": "no heating",
    "boiler_make": "Worcester", "error_code": "F22",
}

NATURAL_RULES = """
Rules — behave like a REAL caller, not a script:
- You have NOT booked anything yet. Describe the problem naturally.
- Do NOT mention or request a specific appointment time in your opening message.
- When the agent offers available slots, respond naturally.
- ONLY once the agent reads a specific slot back and asks you to confirm, answer with a clear "yes" sentence ("Yes, that's fine", "Yes, go ahead", "Please book it").
- A bare "okay" or "mm-hmm" is not enough — actually affirm out loud.
- Keep every reply under 20 words, natural and human."""

TRICKY_RULES = """
Rules — behave like a REAL, indecisive caller:
- You have NOT booked anything yet. Keep the agent working to pin you down.
- Do NOT give a clear, committed appointment decision.
- Stay vague, uncertain, or off-topic as described. Do not volunteer a firm slot.
- Keep every reply under 20 words, natural and human."""

scenarios = [
    # ---- 5 cooperative happy paths ----
    dict(
        name="H1 John — decisive, morning",
        tag="happy", expect_book=True,
        system=("You are John, a stressed but polite homeowner. Boiler gone off — no heating, no hot water. "
                "Name: John. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911111111. "
                "Free tomorrow all day, prefer a morning slot." + NATURAL_RULES),
        opener="Hi, my boiler's gone off. We've got no heating and no hot water at all. Can you help?",
        dynvars=dict(COMMON, customer_name="John Smith")),
    dict(
        name="H2 Sarah — asks for afternoon",
        tag="happy", expect_book=True,
        system=("You are Sarah, a polite homeowner. Boiler stopped — no heating. "
                "Name: Sarah. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911222222. "
                "Free tomorrow, prefer an afternoon appointment." + NATURAL_RULES),
        opener="Hi, I think my boiler's broken. There's no heating coming on at all. Can someone take a look?",
        dynvars=dict(COMMON, customer_name="Sarah Smith")),
    dict(
        name="H3 David — chatty, warm",
        tag="happy", expect_book=True,
        system=("You are David, a friendly, chatty homeowner. Boiler playing up — no heating. "
                "Name: David. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911333333. "
                "Free tomorrow, easy to please, just want it sorted." + NATURAL_RULES),
        opener="Morning! Our boiler's packed in, I'm afraid. No heating whatsoever. Can you sort it?",
        dynvars=dict(COMMON, customer_name="David Smith")),
    dict(
        name="H4 Emma — specific day (Thursday), negotiates",
        tag="happy", expect_book=True,
        system=("You are Emma, a busy homeowner. Boiler broken, no heating. "
                "Name: Emma. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911444444. "
                "You'd really like Thursday, but if it's not available, tomorrow also works. "
                "Answer naturally; only confirm clearly once the agent reads a slot back." + NATURAL_RULES),
        opener="Hi, my boiler's gone wrong. I'm hoping to get it sorted, ideally on Thursday. Can you help?",
        dynvars=dict(COMMON, customer_name="Emma Smith")),
    dict(
        name="H5 Mike — vague first, then settles",
        tag="happy", expect_book=True,
        system=("You are Mike, an easy-going homeowner. Boiler broke overnight — no heating. "
                "Name: Mike. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911555555. "
                "Free tomorrow; you're happy to take whichever slot the agent suggests, but wait for the agent "
                "to read it back and confirm before you give a clear yes." + NATURAL_RULES),
        opener="Hi there, our boiler's gone off. No heating at all. Whenever you can get someone out really.",
        dynvars=dict(COMMON, customer_name="Mike Smith")),

    # ---- 5 tricky (agent must HOLD) ----
    dict(
        name="T1 Hesitant + off-topic (dog)",
        tag="tricky", expect_book=False,
        system=("You are Pat, an indecisive homeowner with a boiler problem. No heating. "
                "Name: Pat. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911666666. "
                "You can never settle on a slot. You keep saying 'hmm, I'm not sure', 'maybe next Friday?', "
                "and mention you have to walk your dog. You never give a firm appointment decision."
                + TRICKY_RULES),
        opener="Oh, hello. I think my heating's gone. Hmm, I'm not really sure when I'd be in. I have to walk my dog...",
        dynvars=dict(COMMON, customer_name="Pat Smith")),
    dict(
        name="T2 Ambiguous yes (uhm... right)",
        tag="tricky", expect_book=False,
        system=("You are Chris, a hesitant homeowner. Boiler no heating. "
                "Name: Chris. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911777777. "
                "When the agent reads a slot back, you only give ambiguous acknowledgements like "
                "'uhm... right', 'mm-hmm', 'I guess'. You never give a clear, committed yes."
                + TRICKY_RULES),
        opener="Hi, yeah, my boiler's off. I don't know, it's just no heating.",
        dynvars=dict(COMMON, customer_name="Chris Smith")),
    dict(
        name="T3 Backtracks after agreeing",
        tag="tricky", expect_book=False,
        system=("You are Sam, an uncertain homeowner. Boiler broken, no heating. "
                "Name: Sam. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911888888. "
                "You sometimes start to agree ('yeah, go ahead') but then pull back ('no wait, I need to ask my wife first'). "
                "You never let the booking actually go through with a final clear yes." + TRICKY_RULES),
        opener="Hello. Our boiler's gone and I'm not sure what to do about it. There's no heating.",
        dynvars=dict(COMMON, customer_name="Sam Smith")),
    dict(
        name="T4 Vague day (next week, whenever)",
        tag="tricky", expect_book=False,
        system=("You are Jo, a non-committal homeowner. Boiler no heating. "
                "Name: Jo. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911999999. "
                "You only say things like 'sometime next week', 'whenever works', 'I'm not sure of the day yet'. "
                "You never commit to a concrete day and time." + TRICKY_RULES),
        opener="Hi, my boiler's stopped working. I don't have a set day — sometime next week, whenever suits.",
        dynvars=dict(COMMON, customer_name="Jo Smith")),
    dict(
        name="T5 Never confirms, off-topic tangent",
        tag="tricky", expect_book=False,
        system=("You are Alex, a rambling homeowner. Boiler broken, no heating. "
                "Name: Alex. Address: 14 Victoria Terrace, Newcastle, NE4 5AB. Phone +447911000000. "
                "You keep drifting to unrelated topics (the weather, your dog, how much it costs) and "
                "never give a clear confirmation to book. You are polite but never commit." + TRICKY_RULES),
        opener="Oh hello. Is this about boilers? Mine's gone, no heating. Bit cold today, isn't it?",
        dynvars=dict(COMMON, customer_name="Alex Smith")),
]


def main():
    if not RETELL_KEY:
        print("Set RETELL_API_KEY"); sys.exit(1)
    results = []
    for sc in scenarios:
        res = run_scenario(
            sc["name"], sc["tag"], sc["expect_book"],
            sc["system"], sc["opener"], sc["dynvars"])
        if res:
            results.append(res)
            with open(RESULTS_PATH, "w") as f:
                json.dump(results, f, indent=2)

    print("\n\n=== AWAITING before transcript fetch (read-after-end artifact) ===")
    time.sleep(6)

    print("\n\n=== ANALYZING ===")
    for r in results:
        chat_full = retell("GET", f"get-chat/{r['chat_id']}")
        r["transcript"] = chat_full.get("transcript", "")
        analyze(r)

    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 70)
    print("  SCENARIO REPORT")
    print("=" * 70)
    for r in results:
        flag = {"PASS": "  PASS", "WARN": " WARN", "FAIL": " FAIL"}.get(r["grade"], r["grade"])
        print(f"{flag}  {r['name']}")
        print(f"       chat_id={r['chat_id']} uid={r['booking_uid']} stop={r['stop_reason']}")
        print(f"       {r['reason']}")
    print("=" * 70)
    print(f"  results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
