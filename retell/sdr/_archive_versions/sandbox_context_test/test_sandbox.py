#!/usr/bin/env python3
"""Drive personas against the two sandbox agents; dump transcripts + final vars."""
import json, os, sys, urllib.request, urllib.error

BASE = "https://api.retellai.com"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
LOGS = os.path.join(HERE, "logs")
os.makedirs(LOGS, exist_ok=True)

KEY = OPENAI = None
for line in open(os.path.join(ROOT, ".env")):
    if line.strip().startswith("RETELL_API_KEY="): KEY = line.strip().split("=",1)[1]
    if line.strip().startswith("OPENAI_API_KEY="): OPENAI = line.strip().split("=",1)[1]

def api(method, path, data=None):
    req = urllib.request.Request(f"{BASE}/{path}",
        data=json.dumps(data).encode() if data else None, method=method,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        print(f"  RETELL ERROR {e.code}: {e.read().decode()[:200]}")
        return {"_error": e.code}

def gpt_reply(persona_sys, hist):
    msgs = [{"role":"system","content":persona_sys}] + hist[-12:]
    msgs.append({"role":"user","content":'Agent said: "%s"\nReply in <=25 words as the customer.' % hist[-1]["content"]})
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
        data=json.dumps({"model":"gpt-4o","messages":msgs,"temperature":0.7,"max_tokens":90}).encode(),
        headers={"Authorization":f"Bearer {OPENAI}","Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()

PERSONAS = {
 "ramble": ("You are Dana Whitaker, co-owner of Bright Smile Orthodontics in Scottsdale, Arizona. "
   "FIRST MESSAGE ONLY, deliver this exact rambling monologue (natural tone, no lists): 'Oh hey, yeah - Dana "
   "Whitaker, me and my sister run Bright Smile Orthodontics up in Scottsdale. We got your thing in the mail. "
   "Look, I'm slammed between patients but our front desk keeps missing calls. Email's dana@brightsmileortho.com "
   "if that's easier. My cell is four eight zero, five five five, oh one seven seven - that's the best number. And we're Arizona, so like "
   "Mountain time I guess? Mornings before my first patient are really the only good window.' "
   "AFTER THAT: reply ONLY in short confirmations: 'Yep.' / 'That's right.' / 'Already told ya - [brief repeat of the fact].' "
   "NEVER volunteer new information. If asked for something you already gave, say 'Already told ya' plus the fact. "
   "If asked something you never covered, say 'Hm, hadn't thought about it - whatever works for you guys.'"),
 "coop": ("You are Taylor Morgan, owner of Lakeside Family Dental in Madison, Wisconsin (Central time). "
          "Cooperative and efficient. FIRST message, dump nearly everything naturally: 'Hi! Taylor Morgan, "
          "Lakeside Family Dental — saw your ad. Email taylor@lakesidedental.com, best number is my cell "
          "+16085550142. We're Central time. Afternoons work best for a call.' "
          "Answer any follow-up instantly and completely."),
 "withhold": ("You are Jordan Pike, co-owner of Pike & Daughters Landscaping in Portland, Oregon (Pacific time). "
          "ANSWER ONLY WHAT IS ASKED, one fact at a time, never two facts in one reply. Asked first name -> 'Jordan.' "
          "Asked last name -> 'Pike.' Asked company -> 'Pike & Daughters Landscaping.' Asked email -> 'jordan@pikelandscaping.com'. "
          "Asked phone -> '+15035550198, and yes that's the best one.' Asked timezone -> 'Pacific.' Asked best time -> "
          "'Mornings before noon.' If the agent apologizes for missing something and re-asks later, answer normally. "
          "If asked about something already answered, repeat it briefly without annoyance."),
 "coop": ("You are Taylor Morgan, owner of Lakeside Family Dental in Madison, Wisconsin (Central time). "
          "Cooperative and efficient. FIRST message, dump nearly everything naturally: 'Hi! Taylor Morgan, "
          "Lakeside Family Dental — saw your ad. Email taylor@lakesidedental.com, best number is my cell "
          "+16085550142. We're Central time. Afternoons work best for a call.' (You deliberately NEVER said "
          "your email domain spelled out twice or your last name separately — you gave 'Taylor Morgan' once.) "
          "Answer any follow-up instantly and completely."),
 "withhold": ("You are Jordan Pike, co-owner of Pike & Daughters Landscaping in Portland, Oregon (Pacific time). "
          "ANSWER ONLY WHAT IS ASKED, one fact at a time, never two facts in one reply. Asked first name -> 'Jordan.' "
          "Asked last name -> 'Pike.' Asked company -> 'Pike & Daughters Landscaping.' Asked email -> 'jordan@pikelandscaping.com'. "
          "Asked phone -> '+15035550198, and yes that's the best one.' Asked timezone -> 'Pacific.' Asked best time -> "
          "'Mornings before noon.' If the agent apologizes for missing something and re-asks later, answer normally. "
          "If asked about something already answered, repeat it briefly without annoyance."),
}

def run(variant, agent_id, pname):
    persona_sys = PERSONAS[pname]
    c = api("POST", "create-chat", {"agent_id": agent_id})
    if "_error" in c: return
    cid = c["chat_id"]
    print(f"\n=== {variant}/{pname} === chat={cid}")
    caller = ("Hi! Taylor Morgan here from Lakeside Family Dental — saw your ad online." if pname=="coop"
              else "Hey. Got something in the mail about missed calls?")
    hist = []
    for turn in range(24):
        r = api("POST", "create-chat-completion", {"agent_id": agent_id, "chat_id": cid, "content": caller})
        if "_error" in r: break
        msgs = [m for m in r.get("messages", []) if m.get("role") in ("agent","assistant") and m.get("content")]
        agent_text = (msgs[-1]["content"] if msgs else "") or ""
        tools = [tc.get("name") for tc in (r.get("tool_calls") or [])] if isinstance(r.get("tool_calls"), list) else []
        tools += [m.get("name") for m in r.get("messages", []) if m.get("type") == "tool_call"]
        print(f"  T{turn+1:>2} A: {agent_text[:130]}".replace("\n"," "))
        if tools: print(f"       tools: {tools}")
        if r.get("chat_status") == "ended":
            print("       [chat ended]")
            break
        if any("end_call" in str(x) for x in tools):
            print("       [end_call fired]")
            break
        hist.append({"role":"assistant","content":agent_text})
        caller = gpt_reply(persona_sys, hist)
        print(f"       C: {caller[:130]}")
        hist.append({"role":"user","content":caller})
    full = api("GET", f"get-chat/{cid}")
    out = os.path.join(LOGS, f"sandbox_{variant}_{pname}_{cid}.json")
    json.dump(full, open(out,"w"), indent=2)
    dv = full.get("collected_dynamic_variables") or {}
    filled = {k:v for k,v in dv.items() if v not in ("","none",None)}
    print(f"  SAVED {os.path.basename(out)}")
    print(f"  FILLED {len(filled)}/8: {json.dumps(filled)[:300]}")

if __name__ == "__main__":
    agents = json.load(open(os.path.join(HERE,"sandbox_agents_v4.json")))
    import sys as _s
    which = _s.argv[1] if len(_s.argv)>1 else "both"
    pname  = _s.argv[2] if len(_s.argv)>2 else "ramble"
    for variant in (["R1","R2"] if which=="both" else [which]):
        run(variant, agents[variant]["agent_id"], pname)
