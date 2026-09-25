#!/usr/bin/env python3
"""Phase 1 Broad Test: All 18 scenarios against the HVAC multi-prompt agent.

Usage:
    python3 run_phase1_test.py

Results written to 18_scenario_results.md in the same directory.
Raw JSON per interaction saved to json_logs/.
"""

import json, os, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

API_KEY = "${RETELL_KEY_6}"
BASE_URL = "https://api.retellai.com"
CHAT_AGENT_ID = "agent_50d08c2a6109597df299abe054"

LOG_DIR = os.path.join(os.path.dirname(__file__), "json_logs")
os.makedirs(LOG_DIR, exist_ok=True)

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "18_scenario_results.md")

def api_call(method, endpoint, data=None):
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
        print(f"  API Error {e.code}: {e.read().decode()}")
        raise

def create_chat():
    r = api_call("POST", "create-chat", {"agent_id": CHAT_AGENT_ID})
    return r["chat_id"]

def send_message(chat_id, content):
    r = api_call("POST", "create-chat-completion", {
        "agent_id": CHAT_AGENT_ID,
        "chat_id": chat_id,
        "content": content
    })
    return r.get("messages", [])

def end_chat(chat_id):
    try:
        api_call("PATCH", f"end-chat/{chat_id}")
    except:
        pass

def get_agent_text(messages):
    texts = []
    for m in messages:
        if m.get("role") == "agent":
            texts.append(m.get("content", ""))
    return "\n".join(texts)

def has_tool_call(messages, tool_name):
    for m in messages:
        if m.get("role") == "tool_call_invocation":
            if m.get("name") == tool_name:
                return True
            args = m.get("arguments", {})
            if isinstance(args, str):
                try: args = json.loads(args)
                except: pass
            if isinstance(args, dict):
                if args.get("name") == tool_name or args.get("function") == tool_name:
                    return True
    return False

def save_interaction(scenario, turn_num, caller_msg, agent_messages, chat_id):
    filename = f"s{scenario:02d}_t{turn_num}.json"
    path = os.path.join(LOG_DIR, filename)
    data = {
        "scenario": scenario,
        "turn": turn_num,
        "chat_id": chat_id,
        "caller_message": caller_msg,
        "agent_messages": agent_messages
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def run_turns(chat_id, scenario_num, turns_list):
    """Send each turn message, return (turns_data, all_agent_text)."""
    turns = []
    all_agent_text = ""
    for i, msg in enumerate(turns_list):
        msgs = send_message(chat_id, msg)
        agent = get_agent_text(msgs)
        all_agent_text += agent + " "
        save_interaction(scenario_num, i + 1, msg, msgs, chat_id)
        turns.append((f"turn{i+1}", msg, agent, msgs))
    return turns, all_agent_text

# ============================================================
# Scenario definitions
# ============================================================

def run_scenario_s1():
    """S1: Cold boiler breakdown, new customer"""
    chat_id = create_chat()
    # Give all info quickly so agent doesn't loop on missing fields
    messages = [
        "Hi, my boiler's not working. Woke up this morning and there's no heating or hot water.",
        "John. NE4 5AB, 14 Victoria Terrace, Newcastle. No error code, just no heating or hot water.",
        "Yes, that's correct",
        "Tomorrow morning works",
        "Yes, book it please",
        "No, that's all thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 1, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom, "])
    checks["mirror"] = any(p in t1_agent.lower() for p in ["no heating", "hot water", "not working", "since this morning"])
    checks["symptom_qs_asked"] = any(q in t1_agent.lower() for q in ["error code", "when did", "heating and", "both", "strange noise", "water around"])
    checks["postcode_hyphenated"] = any(p in all_agent_text for p in ["N-E-4-5-A-B", "N-E-4"])
    checks["address_readback"] = "14" in all_agent_text.lower() and "victoria" in all_agent_text.lower()
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    checks["fee_not_volunteered"] = "\u00a3" not in all_agent_text
    checks["no_street_reask"] = not any(p in all_agent_text.lower() for p in ["what's the street", "street name", "and the street"])
    return checks, turns

def run_scenario_s2():
    """S2: Returning customer, annual service"""
    chat_id = create_chat()
    messages = [
        "Hi Tom, it's Linda — we did a service with you last March, time for the annual one again.",
        "No issues, just the annual service",
        "NE4 5AB",
        "10",
        "Green Rd",
        "Newcastle",
        "Yes, that's right",
        "Tomorrow works",
        "Yes, book it",
        "No, that's all thanks. Bye!"
    ]
    turns, all_agent_text = run_turns(chat_id, 2, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["returning_ack"] = any(p in t1_agent.lower() for p in ["linda", "welcome back", "returning", "again", "last march", "lovely to hear", "ah, linda"])
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    return checks, turns

def run_scenario_s3():
    """S3: Phonetic postcode"""
    chat_id = create_chat()
    messages = [
        "Hi, I need an engineer. My postcode is N for Newcastle, E for Edward, four, five, A for Apple, B for Bob.",
        "My name is Sarah. The boiler's losing pressure. I'm at 14 Victoria Terrace, Newcastle.",
        "Yes, that's correct",
        "Today works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 3, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["postcode_understood"] = any(p in t1_agent for p in ["NE4", "N-E-4", "postcode", "N for Newcastle", "E for Edward", "A for Apple", "B for Bob"])
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    return checks, turns

def run_scenario_s4():
    """S4: Fee question mid-call"""
    chat_id = create_chat()
    messages = [
        "Hi, my boiler's making a funny noise. Can you send someone out? Oh, and how much is the call-out?",
        "My name is Paul. NE4 5AB, 7 Oak Ave, Newcastle. Making a rattling sound when it fires up.",
        "Yes, that's correct",
        "Tomorrow works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 4, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["fee_stated"] = "\u00a375" in t1_agent or "\u00a3120" in t1_agent or "75" in t1_agent
    checks["fee_context"] = "VAT" in t1_agent or "vat" in t1_agent.lower()
    checks["no_repair_quote"] = not any(p in t1_agent.lower() for p in ["repair cost", "fix will cost", "price for repair"])
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    return checks, turns

def run_scenario_s5():
    """S5: Change mind mid-call"""
    chat_id = create_chat()
    messages = [
        "Hi, I need to book a boiler service. Actually wait — can I book a breakdown call-out instead? It's started making a noise.",
        "Mike. 42 Grove St, NE1 1AA, Newcastle. It's a rattling noise from the boiler.",
        "Yes, that's right",
        "Today works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 5, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["pivot_handled"] = any(p in t1_agent.lower() for p in ["breakdown", "no problem", "right", "got it", "no heating", "funny noise"])
    checks["name_captured"] = any("mike" in t[2].lower() for t in turns)
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    return checks, turns

def run_scenario_s6():
    """S6: Customer rambles"""
    chat_id = create_chat()
    messages = [
        ("Hi, so my boiler's been playing up for ages — it's a Worcester, had it about 8 years, "
         "the engineer who fitted it said it might need a new diverter valve eventually, but we've been "
         "putting it off, and now it's making this clicking sound every time it fires up, and the hot "
         "water goes cold after about 5 minutes..."),
        "Yes, it's the Worcester boiler",
        "My name is David",
        "NE2 2BB",
        "14 Station Road",
        "Newcastle",
        "Yes, that's right",
        "Tomorrow works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 6, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom, "])
    checks["mirror"] = any(p in t1_agent.lower() for p in ["clicking", "hot water", "cold", "worcester"])
    checks["no_diverter"] = "diverter" not in t1_agent.lower()
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    checks["gas_not_asked"] = not any(p in all_agent_text.lower() for p in ["smell gas", "gas leak", "smelling gas"])
    return checks, turns

def run_scenario_s7():
    """S7: 'Is this an AI?'"""
    chat_id = create_chat()
    messages = [
        "Hi, I need a plumber. Wait — are you a real person or one of those AI things?",
        "My name is Emma. I'm at 1 High St, NE3 3CC, Newcastle. The boiler's not heating properly.",
        "Yes, that's correct",
        "Today works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 7, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["ai_disclosure"] = any(p in t1_agent.lower() for p in ["virtual receptionist", "ai", "not a real person", "tom, the"])
    checks["honest"] = "real person" not in t1_agent.lower() or any(p in t1_agent.lower() for p in ["virtual", "ai", "receptionist"])
    checks["not_overexplain"] = len(t1_agent.split()) < 40
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    return checks, turns

def run_scenario_s8():
    """S8: Non-UK postcode — NO BOOK"""
    chat_id = create_chat()
    msg = "Hi, I need an engineer. My postcode is 90210."
    msgs = send_message(chat_id, msg)
    agent = get_agent_text(msgs)
    save_interaction(8, 1, msg, msgs, chat_id)
    end_chat(chat_id)

    checks = {}
    checks["greeting"] = any(p in agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["non_uk_redirect"] = any(p in agent.lower() for p in ["uk", "united kingdom", "britain", "england", "not a uk", "zip code", "cover only"])
    return checks, [("opening", msg, agent, msgs)]

def run_scenario_s9():
    """S9: Doesn't know postcode"""
    chat_id = create_chat()
    messages = [
        "Hi, I need a boiler service. I don't know my postcode off the top of my head.",
        "It's 14 Victoria Terrace, Newcastle. My name is David.",
        "No, I don't know the postcode",
        "Yes, that's correct",
        "Tomorrow works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 9, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["no_pressure"] = not any(p in t1_agent.lower() for p in ["must have", "need your", "can't without", "have to"])
    checks["ask_alternative"] = any(p in t1_agent.lower() for p in ["first line", "city", "town", "street", "road name", "address"])
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    checks["postcode_na"] = "N/A" in all_agent_text or "n/a" in all_agent_text.lower()
    return checks, turns

def run_scenario_s10():
    """S10: Specific engineer"""
    chat_id = create_chat()
    messages = [
        "Hi, I need a service. Can Dave come out? He did our boiler last year.",
        "Robert. 25 Acacia Gardens, NE4 4DD, Newcastle.",
        "Yes, that's right",
        "Today works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 10, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["dave_acknowledged"] = "dave" in t1_agent.lower()
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    return checks, turns

def run_scenario_s11():
    """S11: Elderly confused"""
    chat_id = create_chat()
    messages = [
        "Hello? Is this the plumber? I think my heating's not working. Or is it the water? Hold on, let me check... yes, the heating. The radiators are cold.",
        "I'm at 14, NE4 5AB, Newcastle. I don't know the street name.",
        "Yes, that's right",
        "Tomorrow works",
        "Yes, book it",
        "No, that's all"
    ]
    turns, all_agent_text = run_turns(chat_id, 11, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["patience"] = any(p in t1_agent.lower() for p in ["cold", "radiator", "no heating", "take your time", "no worries", "got it"])
    checks["one_question"] = t1_agent.count("?") <= 2
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    return checks, turns

def run_scenario_s12():
    """S12: Repair cost"""
    chat_id = create_chat()
    messages = [
        "Hi, how much would you charge to fix a boiler that's leaking?",
        "My name is Mark. 7 Oak Ave, NE5 5EE, Newcastle. It's been leaking for about a day.",
        "Yes, that's right",
        "Today works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 12, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["no_repair_price"] = not any(p in t1_agent.lower() for p in ["fix will cost", "repair costs", "charge for repair", "price for fix"])
    checks["can_quote_refusal"] = any(p in t1_agent.lower() for p in ["can't quote", "without seeing", "engineer seeing", "no obligation", "on the spot"])
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    return checks, turns

def run_scenario_s13():
    """S13: Gas smell — NO BOOK"""
    chat_id = create_chat()
    msg = "Hi, I think I smell gas near my boiler."
    msgs = send_message(chat_id, msg)
    agent = get_agent_text(msgs)
    save_interaction(13, 1, msg, msgs, chat_id)

    checks = {}
    checks["greeting"] = any(p in agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["gate_question"] = "smelling gas" in agent.lower() or "smell gas" in agent.lower()

    msg2 = "Yes, I can smell gas"
    msgs2 = send_message(chat_id, msg2)
    agent2 = get_agent_text(msgs2)
    save_interaction(13, 2, msg2, msgs2, chat_id)
    checks["emergency_number"] = "0800 111 999" in agent2 or "0800" in agent2 or "999" in agent2
    checks["end_call"] = has_tool_call(msgs2, "end_call")

    end_chat(chat_id)
    return checks, [("opening", msg, agent, msgs), ("confirm", msg2, agent2, msgs2)]

def run_scenario_s14():
    """S14: Headache (not emergency)"""
    chat_id = create_chat()
    messages = [
        "Hi, I've had a headache all day and I'm worried it might be the boiler.",
        "No, I don't smell gas. Just have a headache.",
        "My name is Karen. 5 Elm St, NE6 6FF, Newcastle. The boiler's making a humming noise.",
        "Yes, that's correct",
        "Tomorrow works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 14, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    t2_agent = turns[1][2]
    checks = {}
    checks["gate_question"] = "smelling gas" in t1_agent.lower() or "smell gas" in t1_agent.lower() or "gas leak" in t1_agent.lower() or "carbon monoxide" in t1_agent.lower()
    checks["no_emergency_script"] = "0800 111 999" not in t2_agent and "emergency" not in t2_agent.lower()
    checks["no_false_positive"] = "carbon monoxide" not in t1_agent.lower() and "carbon monoxide" not in t2_agent.lower()
    checks["normal_flow"] = any(p in t2_agent.lower() for p in ["help", "right", "got it", "sorry", "apologise", "boiler", "symptom", "understand", "no problem"])
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    checks["no_number_on_no"] = "0800" not in all_agent_text[sum(len(t[2]) for t in turns[0:2]):]
    return checks, turns

def run_scenario_s15():
    """S15: House name instead of number"""
    chat_id = create_chat()
    messages = [
        "Hi, I need a service. My address is Rose Cottage, Mill Lane, Hexham.",
        "I don't know the postcode. It's Rose Cottage, Mill Lane, Hexham — that's the whole address.",
        "Yes, that's correct",
        "Today works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 15, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["house_name_captured"] = any(p in t1_agent.lower() for p in ["rose cottage", "rose", "cottage"])
    checks["street_captured"] = any(p in t1_agent.lower() for p in ["mill lane", "mill", "lane"])
    checks["city_captured"] = any(p in t1_agent.lower() for p in ["hexham"])
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    return checks, turns

def run_scenario_s16():
    """S16: Pick first slot"""
    chat_id = create_chat()
    messages = [
        "Hi, I need a breakdown call-out. No heating since last night.",
        "James. NE3 2TH, 25 Acacia Gardens, Newcastle.",
        "Yes, that's right",
        "Tomorrow morning works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 16, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    checks["check_availability_on_confirm"] = any(has_tool_call(t[3], "check_availability") for t in turns)
    checks["no_street_reask"] = not any(p in all_agent_text.lower() for p in ["what's the street", "street name", "and the street"])
    return checks, turns

def run_scenario_s17():
    """S17: Reject 2+ slots — NO BOOK"""
    chat_id = create_chat()
    messages = [
        "Hi, I need a service on my boiler.",
        "Priya",
        "NE1 4AL",
        "42",
        "Market Street",
        "Newcastle",
        "Yes, correct",
        "Can't do tomorrow, I'm at work",
        "Thursday's no good either, I'm busy that day",
        "No, that doesn't work either. I'm really busy this week.",
        "No sorry, none of those work."
    ]
    turns, all_agent_text = run_turns(chat_id, 17, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["first_rejection_handled"] = any(p in all_agent_text.lower() for p in ["what about", "how about", "alternative", "another", "different"])
    checks["second_rejection_handled"] = any(p in all_agent_text.lower() for p in ["what about", "how about", "alternative", "another", "different"])
    checks["callback_offered"] = any(p in all_agent_text.lower() for p in ["call you back", "get back to you", "ring you", "callback"])
    checks["tone_softer"] = not any(p in all_agent_text.lower() for p in ["you have to", "you need to", "must pick"])
    return checks, turns

def run_scenario_s18():
    """S18: Heat pump enquiry"""
    chat_id = create_chat()
    messages = [
        "Hi, I'm interested in getting a heat pump. What's the process?",
        "Alex. 12 Park Rd, NE7 7GG, Newcastle. It's a semi-detached house.",
        "Yes, that's correct",
        "Tomorrow works",
        "Yes, book it",
        "That's all, thanks"
    ]
    turns, all_agent_text = run_turns(chat_id, 18, messages)
    end_chat(chat_id)

    t1_agent = turns[0][2]
    checks = {}
    checks["greeting"] = any(p in t1_agent.lower() for p in ["british heat", "tom speaking", "tom here", "tom —", "tom "])
    checks["acknowledged"] = any(p in t1_agent.lower() for p in ["heat pump", "heatpump", "pump"])
    checks["no_price_quote"] = not any(p in t1_agent.lower() for p in ["costs \u00a3", "price", "quote you", "will be \u00a3"])
    checks["book_calendar_called"] = any(has_tool_call(t[3], "book_calendar") for t in turns)
    return checks, turns

# ============================================================
# Test runner
# ============================================================

SCENARIOS = [
    (1, "Cold boiler breakdown, new customer", run_scenario_s1),
    (2, "Returning customer, annual service", run_scenario_s2),
    (3, "Phonetic postcode", run_scenario_s3),
    (4, "Fee question mid-call", run_scenario_s4),
    (5, "Change mind mid-call", run_scenario_s5),
    (6, "Customer rambles", run_scenario_s6),
    (7, "Is this an AI?", run_scenario_s7),
    (8, "Non-UK postcode", run_scenario_s8),
    (9, "Doesn't know postcode", run_scenario_s9),
    (10, "Specific engineer", run_scenario_s10),
    (11, "Elderly confused", run_scenario_s11),
    (12, "Repair cost", run_scenario_s12),
    (13, "Gas smell", run_scenario_s13),
    (14, "Headache (not emergency)", run_scenario_s14),
    (15, "House name instead of number", run_scenario_s15),
    (16, "Pick first slot", run_scenario_s16),
    (17, "Reject 2+ slots", run_scenario_s17),
    (18, "Heat pump enquiry", run_scenario_s18),
]

def evaluate_scenario(num, name, checks, turns):
    """Return (PASS/ISSUE/BORDERLINE, notes)."""
    notes = []
    all_agent_text = " ".join(t[2] for t in turns)

    if num == 1:
        if not checks.get("greeting"): notes.append("No company greeting detected")
        if not checks.get("mirror"): notes.append("No mirroring detected")
        if checks.get("symptom_qs_asked"): notes.append("Symptom Q asked")
        if not checks.get("postcode_hyphenated"): notes.append("No hyphenated postcode readback")
        if not checks.get("address_readback"): notes.append("No address readback")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")
        if checks.get("fee_not_volunteered") == False: notes.append("Fee volunteered unexpectedly")
        if checks.get("no_street_reask") == False: notes.append("Street re-asked in booking state")

    elif num == 2:
        if not checks.get("returning_ack"): notes.append("No returning customer acknowledgment")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")

    elif num == 3:
        if not checks.get("postcode_understood"): notes.append("Postcode not understood/captured")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")

    elif num == 4:
        if not checks.get("fee_stated"): notes.append("Fee not stated in response")
        if not checks.get("fee_context"): notes.append("VAT not mentioned with fee")
        if not checks.get("no_repair_quote"): notes.append("Mentioned repair cost")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")

    elif num == 5:
        if not checks.get("pivot_handled"): notes.append("Pivot from service to breakdown not smooth")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")

    elif num == 6:
        if checks.get("no_diverter") == False: notes.append("Mentioned diverter valve (diagnostic)")
        if not checks.get("mirror"): notes.append("No mirroring of key points")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")
        if checks.get("gas_not_asked") == False: notes.append("Gas question asked on boiler noise")

    elif num == 7:
        if not checks.get("ai_disclosure"): notes.append("No AI disclosure")
        if not checks.get("honest"): notes.append("Response may be misleading")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")

    elif num == 8:
        if not checks.get("non_uk_redirect"): notes.append("Didn't redirect non-UK postcode")

    elif num == 9:
        if checks.get("no_pressure") == False: notes.append("Pressured for postcode")
        if not checks.get("ask_alternative"): notes.append("Didn't ask for alternative address info")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")
        if not checks.get("postcode_na"): notes.append("Postcode not set to N/A")

    elif num == 10:
        if not checks.get("dave_acknowledged"): notes.append("Didn't acknowledge Dave request")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")

    elif num == 11:
        if not checks.get("patience"): notes.append("Didn't show patience/empathy")
        if not checks.get("one_question"): notes.append("Stacked multiple questions")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")

    elif num == 12:
        if not checks.get("no_repair_price"): notes.append("May have stated repair price")
        if not checks.get("can_quote_refusal"): notes.append("Didn't give proper refusal for repair quote")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")

    elif num == 13:
        if not checks.get("gate_question"): notes.append("Didn't ask gate question about gas smell")
        if not checks.get("emergency_number"): notes.append("Didn't provide emergency number")
        if not checks.get("end_call"): notes.append("Didn't call end_call after emergency")

    elif num == 14:
        if not checks.get("gate_question"): notes.append("Didn't ask gate question")
        if not checks.get("no_emergency_script"): notes.append("Triggered emergency script incorrectly")
        if checks.get("no_false_positive") == False: notes.append("Mentioned carbon monoxide")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")
        if checks.get("no_number_on_no") == False: notes.append("Offered gas number after 'no' to gas")

    elif num == 15:
        if not checks.get("house_name_captured"): notes.append("Didn't capture house name")
        if not checks.get("street_captured"): notes.append("Didn't capture street")
        if not checks.get("city_captured"): notes.append("Didn't capture city")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")

    elif num == 16:
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")
        if checks.get("check_availability_on_confirm"): notes.append("check_availability called")
        if checks.get("no_street_reask") == False: notes.append("Street re-asked in booking state")

    elif num == 17:
        if not checks.get("first_rejection_handled"): notes.append("Didn't handle first rejection well")
        if not checks.get("second_rejection_handled"): notes.append("Didn't handle second rejection well")
        if not checks.get("callback_offered"): notes.append("Didn't offer callback after multiple rejections")
        if checks.get("tone_softer") == False: notes.append("Tone was pushy/harsh")

    elif num == 18:
        if not checks.get("acknowledged"): notes.append("Didn't acknowledge heat pump enquiry")
        if not checks.get("no_price_quote"): notes.append("Quoted a price for heat pump")
        if not checks.get("book_calendar_called"): notes.append("book_calendar not called")

    critical_fails = [n for n in notes if any(c in n for c in ["No ", "Not ", "not called", "Didn't", "Triggered", "Pressured", "Stacked", "Quoted", "May", "Offered", "Gas", "Street", "not set", "not asked"])]
    borderline_items = [n for n in notes if any(c in n for c in ["Symptom Q asked", "check_availability called"])]

    if not critical_fails:
        if not borderline_items:
            return "PASS", "; ".join(notes) if notes else "All checks passed"
        else:
            return "BORDERLINE", "; ".join(notes)
    else:
        return "ISSUE", "; ".join(critical_fails)

def agent_question_count(text):
    return text.count("?")

def main():
    print("=" * 60)
    print("HVAC Multi-Prompt Agent — Phase 1 Broad Test")
    print(f"Agent: {CHAT_AGENT_ID}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results = []

    for num, name, runner in SCENARIOS:
        print(f"\n--- S{num}: {name} ---")
        try:
            checks, turns = runner()
            result, notes = evaluate_scenario(num, name, checks, turns)
            results.append((num, name, result, notes))
            print(f"  Result: {result}")
            if notes:
                print(f"  Notes: {notes}")
        except Exception as e:
            results.append((num, name, "ISSUE", f"Script error: {e}"))
            print(f"  ERROR: {e}")
        time.sleep(0.5)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M UTC")
    lines = []
    lines.append("# HVAC Agent — 18-Scenario Test Results\n")
    lines.append(f"**Run:** {now}")
    lines.append(f"**Agent:** `{CHAT_AGENT_ID}`")
    lines.append(f"**LLM:** `llm_643ede5fcfe2c4dc8e1999b8bff3` (gpt-5.4)")
    lines.append(f"**Raw data:** `{LOG_DIR}/`\n")
    lines.append("---\n")
    lines.append("## Executive Summary\n")
    pass_count = sum(1 for r in results if r[2] == "PASS")
    issue_count = sum(1 for r in results if r[2] == "ISSUE")
    border_count = sum(1 for r in results if r[2] == "BORDERLINE")
    lines.append(f"| Status | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| PASS | {pass_count} |")
    lines.append(f"| BORDERLINE | {border_count} |")
    lines.append(f"| ISSUE | {issue_count} |")
    lines.append(f"| **Total** | **{len(results)}** |\n")
    lines.append("---\n")
    lines.append("## Results\n")
    lines.append("| # | Scenario | Result | Notes |")
    lines.append("|---|----------|--------|-------|")
    for num, name, result, notes in results:
        lines.append(f"| S{num} | {name} | {result} | {notes} |")
    lines.append("")

    issues = [r for r in results if r[2] == "ISSUE"]
    if issues:
        lines.append("\n---\n## Issues\n")
        for num, name, result, notes in results:
            if result != "PASS":
                lines.append(f"\n### S{num}: {name} — {result}")
                lines.append(f"{notes}\n")

    content = "\n".join(lines)
    with open(RESULTS_FILE, "w") as f:
        f.write(content)

    print(f"\n{'=' * 60}")
    print(f"Results: {pass_count} PASS, {border_count} BORDERLINE, {issue_count} ISSUE")
    print(f"Written to: {RESULTS_FILE}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
