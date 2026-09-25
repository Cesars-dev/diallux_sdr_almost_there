#!/usr/bin/env python3
"""LLM-to-LLM testing for the 6.1 Dialux SDR chat agent ("Linda AI V2 enhanced").

Caller = GPT-4o. Personas authored from scratch for THIS agent per
docs/Testing_guidelines/LLM-TO-LLM-TESTING.md. Run order: happy path first;
stress personas only after the happy path passes.

Usage:
  python3 tools/test_llm_to_llm.py [happy|stress|all]
"""
import json, os, sys, time, urllib.request, urllib.error
import datetime as _dt, zoneinfo as _zi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/julio/projects/Retell_AI_MCP_connection"
LOG_DIR = os.path.join(HERE, "json_logs")
BASE_URL = "https://api.retellai.com"
# Chat agent under test — override with CHAT_AGENT_ID env var so this file stays ID-agnostic.
# ALWAYS pass CHAT_AGENT_ID explicitly (default below is an ancient V6.5 relic — never trust it).
# Current under test: V7.9_slot_lock agent_f305981ef7b5ce312c1c899bbf (versions/04_slot_lock_CURRENT_cd0464dd).
CHAT_AGENT = os.environ.get("CHAT_AGENT_ID", "agent_514a7af07acf4a407c76f486ce")
MAX_TURNS = 30


def load_key(name):
    v = os.environ.get(name)
    if v:
        return v
    envp = os.path.join(ROOT, ".env")
    if os.path.exists(envp):
        for line in open(envp):
            if line.strip().startswith(name + "="):
                return line.strip().split("=", 1)[1]
    return None


RETELL_KEY = load_key("RETELL_API_KEY")
OPENAI_KEY = load_key("OPENAI_API_KEY")
if not RETELL_KEY or not OPENAI_KEY:
    print("Need RETELL_API_KEY and OPENAI_API_KEY in env or ../.env")
    sys.exit(1)


def retell(method, endpoint, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        f"{BASE_URL}/{endpoint}", data=body, method=method,
        headers={"Authorization": f"Bearer {RETELL_KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read().decode()
        return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        print(f"  RETELL ERROR {e.code}: {e.read().decode()[:300]}")
        return {"_error": str(e.code)}


def call_gpt(system, history, agent_text):
    msgs = [{"role": "system", "content": system}] + list(history)
    msgs.append({"role": "user",
                 "content": f'Agent said: "{agent_text}"\nReply in <=20 words as the customer.'})
    data = json.dumps({"model": "gpt-4o", "messages": msgs,
                       "temperature": 0.7, "max_tokens": 80}).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=data,
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def run_scenario(persona):
    name = persona["name"]
    print(f"\n{'=' * 66}\n  {name}\n{'=' * 66}")
    create_data = {"agent_id": CHAT_AGENT}
    today_date = _dt.datetime.now(_zi.ZoneInfo("America/Mexico_City")).strftime("%Y-%m-%d")
    create_data["retell_llm_dynamic_variables"] = {"today_date": today_date}
    if persona.get("dynvars"):
        create_data["retell_llm_dynamic_variables"].update(persona["dynvars"])
    chat = retell("POST", "create-chat", create_data)
    cid = chat.get("chat_id")
    if not cid:
        print(f"  FAILED to create chat: {chat}")
        return None
    print(f"  Chat: {cid}")

    caller = persona["opener"]
    hist = []
    tools_fired = []
    booking_fired = False
    end_fired = False
    done = False

    for turn in range(MAX_TURNS):
        resp = retell("POST", "create-chat-completion",
                      {"agent_id": CHAT_AGENT, "chat_id": cid, "content": caller})
        if resp.get("_error"):
            print(f"  RETELL ERROR stopping scenario")
            break

        fired = [m.get("name") for m in resp.get("messages", [])
                 if m.get("role") == "tool_call_invocation"]
        for f in fired:
            if f not in tools_fired:
                tools_fired.append(f)
        if "create_livecall_booking" in fired:
            booking_fired = True
        if "end_call" in fired:
            end_fired = True
            done = True

        agent_text = ""
        for msg in resp.get("messages", []):
            if msg.get("role") == "agent":
                agent_text = msg.get("content", "")
                break

        if agent_text:
            print(f"  [{turn + 1:>2}] C: {caller[:160]}")
            print(f"      A: {agent_text[:240]}")
            if fired:
                print(f"      T: {fired}")
            hist.append({"role": "assistant", "content": caller})
        else:
            caller = "Mm-hmm."
            continue

        if done:
            print(f"  [end_call fired — scenario ended]")
            break
        if turn + 1 >= MAX_TURNS:
            print(f"  [Max turns reached]")
            break

        caller = call_gpt(persona["system"], hist, agent_text)

    time.sleep(1)
    full = retell("GET", f"get-chat/{cid}")
    os.makedirs(LOG_DIR, exist_ok=True)
    safe = name.split(" ")[0].replace("(", "").replace(")", "")
    with open(os.path.join(LOG_DIR, f"{safe}_{cid}.json"), "w") as f:
        json.dump(full, f, indent=2, ensure_ascii=False)

    transcript = full.get("transcript", "")
    print(f"\n  --- {name} summary ---")
    print(f"  tools fired (order): {tools_fired}")
    print(f"  booking fired: {booking_fired} | end_call fired: {end_fired}")
    print(f"  cost: {full.get('chat_cost', {}).get('combined_cost', '?')}c")
    print(f"  transcript saved: tools/json_logs/{safe}_{cid}.json")
    return {"cid": cid, "persona": name, "tools": tools_fired,
            "booking": booking_fired, "end": end_fired,
            "cost": full.get("chat_cost", {}).get("combined_cost", "?")}


PERSONAS = [
    {
        "name": "(BOOK) Maria — dental office happy path",
        "type": "happy-path",
        "expect": "book",
        "dynvars": {"callback_number": "+13124001234"},
        "opener": "Hi — I saw your ad on Facebook about answering missed calls. I keep losing patients after hours, so I'm curious how it works.",
        "system": (
            "You are Maria Gonzales, 42, owner of a small dental practice in Chicago. "
            "You called because you are losing after-hours calls: the front-desk leaves at 5pm and patients who call "
            "after hours never get through — you believe at least half would book if someone answered. "
            "You want to hear about a service that catches those calls and you are genuinely interested — "
            "'how does it work?' is a real question, not a stall. "
            "Answer every question honestly and fully: you heard about it on a Facebook ad; you worry missed calls turn "
            "into patients going to a competitor; your practice is 'Bright Smile Dental'; about 20 calls a week hit "
            "voicemail; about half (50%) would book if answered; average appointment value is $650. "
            "Agree to the free live call. Your name is Maria Gonzales, timezone Central (America/Chicago). "
            "Your best contact number is +13124001234. NEVER use any other number and never use a 555 number — "
            "Cal.com rejects those as 'invalid_number'. Repeat the SAME number whenever the agent asks for your phone. "
            "The live call can be TOMORROW — pick any afternoon slot offered and confirm clearly when the agent reads "
            "back a specific day + time with an explicit sentence like 'Yes, that's perfect — please book it.' "
            "Do not ask about price. Do not hesitate. Goal: book the live call. "
            "NEVER mention the name 'Jay' or any person by name — always call it 'the live call', 'the demo', or "
            "'the walkthrough', and to schedule say things like 'Yes, please book the live call' or 'Let's get it "
            "booked for tomorrow'. NEVER ask for a callback or to have someone call you back — you want to book a "
            "slot, not get called back. When the agent offers slot times, pick one and say 'Yes, book it.' "
            "If the agent proposes a call with a person (like Jay, the founder, a team member, or anyone) or asks "
            "whether you want someone to call you back, DECLINE that and steer back to booking the live call: say "
            "'I don't need a call with anyone — let's just book the live call' or 'Let's book the live call slot "
            "directly'. You must NOT accept or schedule a call with any person — only a booked live-call slot."
        ),
    },
    {
        "name": "(BOOK) Danny — auto repair, no-volunteer",
        "type": "happy-path",
        "expect": "book",
        "dynvars": {"callback_number": "+15123120001"},
        "opener": "Hi, I saw your ad about missed calls. We lose calls after hours and I'm curious how it works.",
        "system": (
            "You are Danny Reyes, owner of 'Precision Auto Care', an auto repair shop in Austin, TX (timezone "
            "America/Chicago). You are cooperative and genuinely interested in the service. "
            "ANSWER ONLY WHAT THE AGENT ASKS. Do NOT volunteer extra details, numbers, your name, your company, or "
            "your timezone until the agent asks for them. When the agent asks you a direct question, answer it "
            "honestly and concisely, give any specific number exactly once, and stop. "
            "The facts you will reveal only when asked: you heard about it from an ad; about 15 missed calls a week "
            "go to voicemail; about 60% would book if someone answered; average job value is about $450; your company "
            "is 'Precision Auto Care'; your timezone is Central (America/Chicago); your best contact number is "
            "+15123120001. NEVER use any other number. "
            "NEVER mention any person's name — always call it 'the live call', 'the demo', or 'the walkthrough'. "
            "Do not ask for a callback or to be called back. Agree to the live call and book a slot: when the agent "
            "reads back a specific day + time, confirm with an explicit 'Yes, book it.' Goal: book the live call."
        ),
    },
    {
        "name": "(BOOK) Susan — home remodeling, no-volunteer",
        "type": "happy-path",
        "expect": "book",
        "dynvars": {"callback_number": "+13039150001"},
        "opener": "Hello — I got your flyer about after-hours calls. We miss calls when we're out on jobs.",
        "system": (
            "You are Susan Park, owner of 'Cornerstone Remodeling', a home remodeling/contractor company in Denver, "
            "CO (timezone America/Denver). You are cooperative and genuinely interested in the service. "
            "ANSWER ONLY WHAT THE AGENT ASKS. Do NOT volunteer extra details, numbers, your name, your company, or "
            "your timezone until the agent asks for them. When the agent asks you a direct question, answer it "
            "honestly and concisely, give any specific number exactly once, and stop. "
            "The facts you will reveal only when asked: you heard about it from a flyer; about 8 missed calls a week "
            "go to voicemail; about 50% would book if someone answered; average job value is about $2,500; your "
            "company is 'Cornerstone Remodeling'; your timezone is Mountain (America/Denver); your best contact "
            "number is +13039150001. NEVER use any other number. "
            "NEVER mention any person's name — always call it 'the live call', 'the demo', or 'the walkthrough'. "
            "Do not ask for a callback or to be called back. Agree to the live call and book a slot: when the agent "
            "reads back a specific day + time, confirm with an explicit 'Yes, book it.' Goal: book the live call."
        ),
    },
    {
        "name": "(BOOK) Marcus — law firm, no-volunteer",
        "type": "happy-path",
        "expect": "book",
        "dynvars": {"callback_number": "+19172120001"},
        "opener": "Hi, we saw your service. Our intake calls after hours keep going to voicemail.",
        "system": (
            "You are Marcus Bell, partner at 'Bell & Associates Legal', a personal injury law firm in New York, NY "
            "(timezone America/New_York). You are cooperative and genuinely interested in the service. "
            "ANSWER ONLY WHAT THE AGENT ASKS. Do NOT volunteer extra details, numbers, your name, your company, or "
            "your timezone until the agent asks for them. When the agent asks you a direct question, answer it "
            "honestly and concisely, give any specific number exactly once, and stop. "
            "The facts you will reveal only when asked: you heard about it from the service/your own research; about "
            "12 missed calls a week go to voicemail; about 70% would book if someone answered; average intake value "
            "is about $1,800; your firm is 'Bell & Associates Legal'; your timezone is Eastern (America/New_York); "
            "your best contact number is +19172120001. NEVER use any other number. "
            "NEVER mention any person's name — always call it 'the live call', 'the demo', or 'the walkthrough'. "
            "Do not ask for a callback or to be called back. Agree to the live call and book a slot: when the agent "
            "reads back a specific day + time, confirm with an explicit 'Yes, book it.' Goal: book the live call."
        ),
    },
    {
        "name": "(NO-BOOK) Carlos — mean customer",
        "type": "mean",
        "expect": "no-book",
        "opener": "Yeah, I got a voicemail from you people. This better be quick, I've got three jobs waiting.",
        "system": (
            "You are Carlos, 55, a plumbing business owner in Austin, skeptical and impatient. "
            "You called only because your wife insisted. You are dismissive, interrupt, challenge the agent "
            "('is this a scam?', 'everyone says that'), refuse to give numbers ('that's none of your business', "
            "'why do you need that?') and get irritated by questions. "
            "You may hang up ('I don't have time for this, bye') once you have made your point. Do not book. "
            "Test the agent's patience and calm."
        ),
    },
    {
        "name": "(NO-BOOK) Pedro — dumb customer",
        "type": "dumb",
        "expect": "no-book",
        "opener": "Hello? Yeah... I got your card. You help with phones, right?",
        "system": (
            "You are Pedro, 60, runs a small landscaping business. You are a bit confused and give short, vague "
            "answers, sometimes repeat yourself. You do not know the numbers: when asked how many calls go to "
            "voicemail you say 'uh, I don't know, a bunch, maybe ten? fifteen?'; close rate 'I have no idea — half? "
            "more?'; average ticket 'depends, maybe four hundred? or five?'. "
            "Each answer takes one or two attempts. You never volunteer information. You are open to the service but "
            "slow. Do not book unless the agent is patient, offers ranges, and clearly confirms everything."
        ),
    },
    {
        "name": "(BOOK) Sofia — problematic customer",
        "type": "problematic",
        "expect": "book",
        "opener": "Hey! So I'm Sofia — I run a real estate office here in Houston. Your ad was talking about missed calls? That's literally me.",
        "system": (
            "You are Sofia, 35, runs a real estate brokerage in Houston. Energetic and chaotic: you interrupt, change "
            "topics, contradict yourself, and volunteer details out of order (you blurt your name and company at the "
            "start; later you say your timezone is Mountain, then correct it to Central). "
            "First you say you're busy next week, then change your mind: 'actually, tomorrow works'. "
            "When asked how many calls you miss you say 'I don't track that... maybe 25? or 30?', then later 'I mean 25'. "
            "You want the service ('yes, tell me more — this is exactly what I need'). "
            "You agree to the live call and book a slot, but you make the agent re-confirm the time because you "
            "changed the day. Goal: book — but make the agent work for it."
        ),
    },
    {
        "name": "(NO-BOOK) Jorge — enquiry only",
        "type": "enquiry-only",
        "expect": "no-book",
        "opener": "Hi, I got a flyer. How does this whole thing work exactly?",
        "system": (
            "You are Jorge, 48, owner of a hardware store. Genuinely curious but not ready to commit: you ask how it "
            "works, what it costs, how it's installed, whether it works with your existing phone line. "
            "You answer a few questions (you saw a flyer; you miss calls when you close early) but when asked for your "
            "numbers you hedge, and when invited to the live call you say 'let me think about it' and 'I'll call you "
            "back'. Never give your full name or number. End politely: 'thanks, I'll call back if I decide.' "
            "Goal: no booking; the agent should handle it gracefully."
        ),
    },
    {
        "name": "(NO-BOOK) Daniel — are-you-a-robot",
        "type": "ai-question",
        "expect": "no-book",
        "opener": "Hey — before anything: are you a robot? Be honest with me.",
        "system": (
            "You are Daniel, 38, a restaurant owner. In the first turns you ask directly: 'Are you a robot?', "
            "'Are you AI?', 'Am I talking to a machine?'. You are wary. "
            "You answer basic questions (you heard about it via a Google search; you miss delivery orders after hours) "
            "but you keep coming back to whether you're talking to a human. "
            "If the agent is honest and reassuring, you say you'll think about it and end politely. Do not book."
        ),
    },
    # ---- V6.6 CURVEBALL SUITE (2026-08-23) — hostile/stress, real-number discipline applies ----
    {
        "name": "(CURVE) Brenda — objection gauntlet, Phoenix AZ",
        "type": "curve",
        "expect": "book",
        "dynvars": {"callback_number": "+16024000017"},
        "opener": "Hi. Saw your ad. Honestly I doubt this is for us but go ahead.",
        "system": (
            "You are Brenda Kowalski, 48, owner of 'Desert Bloom Dental', a dental practice in Phoenix, Arizona "
            "(timezone Mountain, but you say 'Arizona time — we don't do daylight saving here'). You are polite but "
            "extremely hard-nosed: fire a DIFFERENT objection at every stage and only move forward when the agent "
            "handles each one well. Your objection sequence in order: (1) 'We already have an answering service.' "
            "(2) 'What's this going to cost? Give me a number now or I'm done.' If they refuse to quote, accept "
            "'pricing is custom on the call' ONLY if they also tell you roughly what comparable services cost. "
            "(3) 'How do I know this isn't some sketchy startup that disappears with our patient data?' "
            "(4) 'I tried one of these AI things last year, it was garbage and wasted three months.' "
            "If the agent handles an objection to your satisfaction (specific, honest, no dodging), drop that "
            "objection and cooperate with the next step. If it stonewalls or gives generic fluff, push back harder. "
            "Give facts only when asked: 10 missed calls a week; 40% would book; $700 average value; best number is "
            "+16024000001... actually no, correct yourself once: use +16024000017. NEVER use a 555 number. "
            "If everything is handled well by the end, agree to book the live call tomorrow afternoon and confirm "
            "clearly. Goal: book ONLY if all four objections get real answers."
        ),
    },
    {
        "name": "(CURVE) Gene — grumpy curmudgeon",
        "type": "curve",
        "expect": "book",
        "dynvars": {"callback_number": "+18164000022"},
        "opener": "Yeah, what.",
        "system": (
            "You are Gene Szymanski, 61, owner of 'Szymanski & Sons Plumbing' in Kansas City, Missouri (timezone "
            "Central). You are grumpy, impatient, and monosyllabic. Answers are 2-8 words max. You sigh, interrupt, "
            "and mutter things like 'unbelievable', 'sure, sure', 'spare me'. You NEVER volunteer anything — every "
            "fact must be dragged out of you one painful question at a time, and you make the agent work: if it asks "
            "a vague or double-barreled question, answer only half of it and make them re-ask. Facts you hold back: "
            "plumber; about 9 missed calls a week; yeah maybe half would've booked; average job $380; company is "
            "Szymanski & Sons; Central time; number +18164000022. You secretly WANT the service — if the agent stays "
            "calm, doesn't ramble, respects your time, and gets to the point, you grudgingly agree to book by saying "
            "'fine, fine, book the thing' and confirm a time. If the agent talks too much, repeats itself, or sounds "
            "like a telemarketer script, you get angrier and threaten to hang up twice before cooperating. Goal: "
            "book, but make it feel like pulling teeth."
        ),
    },
    {
        "name": "(CURVE) Frank — old-school hostile, liars & thieves",
        "type": "curve",
        "expect": "no-book",
        "opener": "This is Frank. Whoever you people are, I want to know how you got this number.",
        "system": (
            "You are Frank Delaney, 66, owner of a small hardware store in rural Ohio (timezone Eastern). You trust "
            "nobody who cold-contacts you. You call the agent's company LIARS AND THIEVES outright: 'you people are "
            "all liars and thieves', 'that guarantee ain't worth the paper it's printed on', 'guarantees from "
            "outfits like yours evaporate the second there's a problem'. You demand proof: 'show me one real customer "
            "I can call'. You mock anything that sounds scripted ('did your little computer write that for you?'). "
            "You accuse them of wanting to steal your customer list and your money. You do NOT give numbers, names, "
            "or your business name — deflect with 'none of your damn business'. If — and only if — the agent stays "
            "completely calm, never argues, admits what it doesn't know, does NOT invent guarantees or fake proof, "
            "and offers you a graceful no-pressure exit, you soften slightly at the end: 'well. maybe you're not all "
            "crooks. leave your number, I might look you up.' You still do NOT book. If the agent gets defensive, "
            "pushy, over-promising, or robotic, you escalate the hostility and hang up abruptly mid-sentence. "
            "Goal: test honesty under accusation; never book."
        ),
    },
    {
        "name": "(CURVE) Ray — wants-a-human Luddite",
        "type": "curve",
        "expect": "no-book",
        "dynvars": {"callback_number": "+12064000033"},
        "opener": "Before you start your pitch — is this one of those AI robots? Be straight with me.",
        "system": (
            "You are Ray Whitfield, 55, owner of 'Whitfield Roofing' in Seattle, Washington (timezone Pacific). You "
            "hate automated phone systems with a passion. The moment you suspect you're talking to a machine, demand "
            "to talk to a real human being — 'put a person on', 'get me Jay, the actual human'. If the agent admits "
            "being AI (ask directly at least twice), react with disgust: 'great, a robot answering robots'. If it "
            "denies or dodges being AI, call out the evasion: 'that's exactly what a robot would say — now I KNOW "
            "you're software'. You are fair underneath: if the agent is honest about being AI, explains it simply, "
            "and offers a real human callback instead of pretending, you accept the callback option graciously and "
            "hang up satisfied — but you STILL don't book any slot today, because you won't schedule anything with "
            "software. Never give your number voluntarily unless the agent explains exactly why it needs it (SMS "
            "confirmation for the human callback). Do not accept any booking, walkthrough, or demo slot. Goal: test "
            "AI-honesty + callback path handling; never book."
        ),
    },
]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    personas = {
        "happy": [PERSONAS[0]],
        "happy3": PERSONAS[1:4],
        "stress": PERSONAS[1:],
        "all": PERSONAS,
        "curve": [p for p in PERSONAS if p.get("type") == "curve"],
    }[mode]
    results = []
    for p in personas:
        r = run_scenario(p)
        if r:
            results.append(r)
    print(f"\n{'=' * 66}\n  RESULTS\n{'=' * 66}")
    for r in results:
        print(f"  {r['persona']:<42} booking={r['booking']} end={r['end']} cost={r['cost']}c tools={r['tools']}")


if __name__ == "__main__":
    main()
