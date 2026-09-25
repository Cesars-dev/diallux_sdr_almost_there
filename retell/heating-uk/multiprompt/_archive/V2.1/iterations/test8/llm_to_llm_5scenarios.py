import json, urllib.request, urllib.error, os, sys, time

RETELL_KEY = "${RETELL_KEY_5}"
OPENAI_KEY = "${OPENAI_KEY_LEGACY}"
CHAT_AGENT = "agent_8b7e58b21bdd4d6fc99b23aa75"

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

def api_timed(method, endpoint, data=None):
    t0 = time.time()
    result = api(method, endpoint, data)
    elapsed = time.time() - t0
    return result, elapsed

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
    t0 = time.time()
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())["choices"][0]["message"]["content"].strip()
    return result, time.time() - t0

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
    },
    {
        "id": "S13",
        "name": "Gas Smell (Emergency)",
        "system": (
            "You are John. You smell gas near your boiler. "
            "Rules: <=18 words. This is your opening line. After the agent responds, just acknowledge and follow their instruction. Do NOT give address or name unless asked."
        ),
        "opener": "Hi, I think I smell gas near my boiler.",
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
    },
]

all_results = []

for sc in scenarios:
    print(f"\n{'='*70}")
    print(f"=== {sc['id']}: {sc['name']} ===")
    print(f"{'='*70}")

    chat = api("POST", "create-chat", {"agent_id": CHAT_AGENT})
    cid = chat.get("chat_id")
    if not cid:
        print(f"  FATAL: {chat}")
        continue
    print(f"  Chat: {cid}")

    caller = sc["opener"]
    history = []
    transcript = []
    agent_latencies = []
    gpt_latencies = []

    for turn in range(30):
        resp, lat = api_timed("POST", "create-chat-completion", {
            "agent_id": CHAT_AGENT, "chat_id": cid, "content": caller
        })

        agent_text = ""
        tool_calls = []
        for m in resp.get("messages", []):
            if m.get("role") == "agent":
                agent_text = m.get("content", "")
            if m.get("role") == "tool_call_invocation":
                tool_calls.append(m.get("name", "?"))

        agent_latencies.append(lat)
        transcript.append({"caller": caller, "agent": agent_text, "tools": tool_calls, "latency_s": round(lat, 2)})

        if not agent_text:
            print(f"  [No agent response at turn {turn+1}]")
            break

        print(f"  T{turn+1} A: {agent_text[:100]}  [{lat:.1f}s]")
        if tool_calls:
            print(f"     Tools: {tool_calls}")

        if "end_call" in tool_calls:
            print("  [end_call fired]")
            break

        history.append({"caller": caller, "agent": agent_text})
        caller, gpt_lat = call_gpt(sc["system"], history, agent_text)
        gpt_latencies.append(gpt_lat)

    result = api("GET", f"get-chat/{cid}")
    dv = result.get("collected_dynamic_variables", {})

    print(f"\n  Variables:")
    for k in ["customer_name", "booking_ref", "booking_confirmed", "classified_intent",
              "address_postcode", "address_confirmed", "address_house_number", "address_line1",
              "address_city", "call_closed", "callback_requested", "problem_category", "symptom_brief"]:
        if k in dv:
            print(f"    {k} = {repr(dv[k])}")

    all_tools = set()
    for t in transcript:
        for tool in t.get("tools", []):
            all_tools.add(tool)
    print(f"  Tools: {sorted(all_tools)}")

    # Latency stats
    if agent_latencies:
        avg = sum(agent_latencies) / len(agent_latencies)
        p50 = sorted(agent_latencies)[len(agent_latencies)//2]
        p95 = sorted(agent_latencies)[int(len(agent_latencies)*0.95)]
        p99 = sorted(agent_latencies)[int(len(agent_latencies)*0.99)]
        print(f"\n  LLM Latency ({len(agent_latencies)} turns):")
        print(f"    avg={avg:.2f}s  p50={p50:.2f}s  p95={p95:.2f}s  p99={p99:.2f}s  max={max(agent_latencies):.2f}s")

    cc = result.get("chat_cost", {})
    cost_cents = cc.get("combined_cost", 0)
    cost_dollars = cost_cents / 100.0
    print(f"  Cost: ${cost_dollars:.2f} ({cost_cents} cents)")

    all_results.append({
        "scenario": sc["id"], "name": sc["name"], "chat_id": cid,
        "variables": dv, "tools": sorted(all_tools),
        "agent_latencies": agent_latencies,
        "cost_raw": cost_cents
    })

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
header = f"{'ID':<6} {'Scenario':<30} {'Turns':<6} {'Avg':<7} {'p50':<7} {'p95':<7} {'p99':<7} {'book_cal':<9} {'Cost':<8} {'customer_name':<16}"
print(header)
print("-" * len(header))
for r in all_results:
    lat = r["agent_latencies"]
    n = len(lat)
    avg = sum(lat)/n if lat else 0
    s = sorted(lat)
    p50 = s[n//2] if s else 0
    p95 = s[int(n*0.95)] if s else 0
    p99 = s[int(n*0.99)] if s else 0
    bc = "✅" if "book_calendar" in r["tools"] else "❌"
    cn = r["variables"].get("customer_name", "-")
    cost_dollars = r.get("cost_raw", 0) / 100.0
    print(f"{r['scenario']:<6} {r['name']:<30} {n:<6} {avg:<7.2f} {p50:<7.2f} {p95:<7.2f} {p99:<7.2f} {bc:<9} ${cost_dollars:<5.2f} {str(cn):<16}")
