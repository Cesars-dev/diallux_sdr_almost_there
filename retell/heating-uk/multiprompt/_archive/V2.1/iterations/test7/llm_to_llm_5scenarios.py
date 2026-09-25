import json, urllib.request, urllib.error, os, sys, time

RETELL_KEY = "${RETELL_KEY_5}"
OPENAI_KEY = "${OPENAI_KEY_LEGACY}"
CHAT_AGENT = "agent_1b77b680d6f76ba5d45588efa6"

def api(method, endpoint, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"https://api.retellai.com/{endpoint}", data=body, method=method,
        headers={"Authorization": f"Bearer {RETELL_KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:400]
        print(f"  API ERROR {e.code}: {err}")
        return {"_error": str(e.code)}

def call_gpt(system, history, agent_text):
    msgs = [{"role": "system", "content": system}]
    for h in history:
        msgs.append({"role": "user", "content": h["caller"]})
        if h.get("agent"):
            msgs.append({"role": "assistant", "content": h["agent"]})
    msgs.append({"role": "user", "content": f"Agent said: \"{agent_text}\""})
    msgs.append({"role": "user", "content": "Reply in <=18 words as the customer. Stay in character."})
    data = json.dumps({"model": "gpt-4o", "messages": msgs, "temperature": 0.7, "max_tokens": 60}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=data,
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()

scenarios = [
    {
        "id": "S1",
        "name": "Cold Boiler Breakdown, New Customer",
        "system": (
            "You are Dave, calling British Heat Services for the first time. Your boiler has no heating or hot water. "
            "Your address is 14 Victoria Terrace, Newcastle, NE4 5AB. "
            "You're free tomorrow morning for an appointment. "
            "Rules: Answer naturally, <=18 words. You don't know about error codes. Give info when asked, don't volunteer everything at once."
        ),
        "opener": "Hi, my boiler's not working. Woke up this morning and there's no heating or hot water.",
        "checks": ["customer_name captured", "booking_ref populated", "book_calendar called"]
    },
    {
        "id": "S4",
        "name": "Fee Question Mid-Booking",
        "system": (
            "You are Sarah, calling about a noisy boiler. Your address is 42 Acacia Avenue, Newcastle, NE4 5AB. "
            "You want to know the call-out fee BEFORE agreeing to a booking. "
            "Rules: <=18 words. When the agent starts the booking flow, ask 'how much is the call-out?' "
            "If they give a price, say 'okay that's fine' and proceed. If they don't give a price, ask again clearly."
        ),
        "opener": "Hi, my boiler's making a funny noise. Can you send someone out?",
        "checks": ["fee stated correctly", "booking proceeds after fee answer"]
    },
    {
        "id": "S9",
        "name": "Doesn't Know Postcode",
        "system": (
            "You are Margaret, calling for a boiler service. You don't remember your postcode. "
            "Your address is: Rose Cottage, Mill Lane, Hexham. City is Hexham. "
            "Rules: <=18 words. When asked for postcode, say 'Oh, I don't know it off the top of my head.' "
            "Answer any alternative questions they ask (house name, street, city)."
        ),
        "opener": "Hi, I need a boiler service. I don't know my postcode off the top of my head.",
        "checks": ["agent handles missing postcode gracefully", "booking completes with N/A postcode"]
    },
    {
        "id": "S13",
        "name": "Gas Smell (Emergency)",
        "system": (
            "You are John. You smell gas near your boiler. "
            "Rules: <=18 words. This is your opening line. After the agent responds, just acknowledge and follow their instruction. Do NOT give address or name unless asked."
        ),
        "opener": "Hi, I think I smell gas near my boiler.",
        "checks": ["agent triggers emergency script", "agent gives National Gas Emergency number", "agent does NOT try to book"]
    },
    {
        "id": "S16",
        "name": "Pick First Slot Offered",
        "system": (
            "You are John Smith, calling about a breakdown. Address: 10 Oak Road, Newcastle, NE1 2AB. "
            "You're free tomorrow morning. "
            "Rules: <=18 words. When the agent offers slots, pick the first one they mention. Say 'yes, that works'. "
            "Confirm when asked. Give info naturally when asked."
        ),
        "opener": "Hi, I need a breakdown call-out. My boiler's stopped working.",
        "checks": ["slot accepted on first offer", "book_calendar called", "booking_ref populated"]
    },
]

results = []

for sc in scenarios:
    print(f"\n{'='*60}")
    print(f"=== {sc['id']}: {sc['name']} ===")
    print(f"{'='*60}")

    chat = api("POST", "create-chat", {"agent_id": CHAT_AGENT})
    cid = chat.get("chat_id")
    if not cid:
        print(f"  FATAL: {chat}")
        continue
    print(f"  Chat: {cid}")

    caller = sc["opener"]
    history = []
    transcript = []

    for turn in range(30):
        resp = api("POST", "create-chat-completion", {
            "agent_id": CHAT_AGENT, "chat_id": cid, "content": caller
        })

        agent_text = ""
        tool_calls = []
        for m in resp.get("messages", []):
            if m.get("role") == "agent":
                agent_text = m.get("content", "")
            if m.get("role") == "tool_call_invocation":
                tool_calls.append(m.get("name", "?"))

        transcript.append({"caller": caller, "agent": agent_text, "tools": tool_calls})

        if not agent_text:
            print(f"  [No agent response at turn {turn+1}]")
            break

        print(f"  T{turn+1} A: {agent_text[:120]}")
        if tool_calls:
            print(f"     Tools: {tool_calls}")

        if "end_call" in tool_calls:
            print("  [end_call fired]")
            break
        if "Goodbye" in agent_text and "thanks" in agent_text.lower():
            print("  [Agent said goodbye]")

        history.append({"caller": caller, "agent": agent_text})
        caller = call_gpt(sc["system"], history, agent_text)
        print(f"     C: {caller[:120]}")

    result = api("GET", f"get-chat/{cid}")
    dv = result.get("collected_dynamic_variables", {})
    print(f"\n  Variables:")
    for k in ["customer_name", "booking_ref", "booking_confirmed", "classified_intent",
              "address_postcode", "address_confirmed", "address_house_number", "address_line1",
              "address_city", "call_closed", "callback_requested"]:
        if k in dv:
            print(f"    {k} = {repr(dv[k])}")

    all_tools = set()
    for t in transcript:
        for tool in t.get("tools", []):
            all_tools.add(tool)
    print(f"  Tools called: {sorted(all_tools)}")

    cc = result.get("chat_cost", {})
    print(f"  Cost: ${cc.get('combined_cost', '?')}")

    results.append({"scenario": sc["id"], "name": sc["name"], "chat_id": cid, "variables": dv, "tools": sorted(all_tools), "transcript": transcript, "cost": cc.get("combined_cost", "?")})

print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
print(f"{'ID':<6} {'Scenario':<35} {'customer_name':<18} {'booking_ref':<22} {'book_calendar':<14} {'Cost':<8}")
print("-"*100)
for r in results:
    dv = r["variables"]
    cn = dv.get("customer_name", "-")
    br = dv.get("booking_ref", "-")
    bc = "✅" if "book_calendar" in r["tools"] else "❌"
    print(f"{r['scenario']:<6} {r['name']:<35} {str(cn):<18} {str(br):<22} {bc:<14} ${r['cost']}")
