#!/usr/bin/env python3
"""S4 ladder — local edition. Runs the 5 acceptance personas through the V7.9 engine
(OpenAI billing, real Cal bookings via live endpoints). Sequential by doctrine.

Run:  python3 run_ladder.py [idx ...]     (default: 0 3 3 1 4)
"""
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from engine import SDREngine, load_root_key  # noqa: E402

# import the shared persona set (name/expect/dynvars/opener/system)
spec = importlib.util.spec_from_file_location(
    "h", "/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/testing/test_llm_to_llm.py")
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)

LOGS = Path("/tmp/opencode/sim_logs")
LOGS.mkdir(parents=True, exist_ok=True)
USER_SIM_MODEL = "gpt-5-mini"
MAX_TURNS = 30
ORDER = [0, 3, 3, 1, 4]


def user_sim(persona, history_text):
    """The simulated prospect. Same spirit as the Retell harness: persona system prompt."""
    from engine import load_root_key
    from openai import OpenAI
    client = OpenAI(api_key=load_root_key("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=USER_SIM_MODEL,
        messages=[
            {"role": "system", "content": persona["system"] + (
                "\n\nYou are talking to a sales agent on a website chat. Stay in character. "
                "Reply with ONE short chat message at a time (1-3 sentences), like a real person typing. "
                "When the conversation naturally reaches its goal (booked, or you're done), reply with "
                "exactly GOODBYE and nothing else.")},
            {"role": "user", "content": f"Conversation so far:\n{history_text}\n\nYour next message:"},
        ],
    )
    text = resp.choices[0].message.content.strip()
    return "" if text.upper().startswith("GOODBYE") else text


def run_persona(idx):
    persona = H.PERSONAS[idx]
    print(f"\n{'=' * 60}\n[{idx}] {persona['name']}  (expect: {persona['expect']})\n{'=' * 60}")
    eng = SDREngine(persona_dynvars=persona.get("dynvars", {}))
    agent_msg = eng.history[-1]["content"]  # begin_message
    print(f"AGENT: {agent_msg}")
    user_msg = persona["opener"]
    turns = 0
    while turns < MAX_TURNS:
        turns += 1
        print(f"USER : {user_msg[:110]}")
        agent_msg = eng.chat(user_msg)
        print(f"AGENT: {(agent_msg or '<end_call>')[:110]}")
        if eng.ended or not agent_msg:
            break
        convo = "\n".join(
            f"{'AGENT' if m['role'] == 'assistant' else 'USER'}: {m['content']}"
            for m in eng.history if m["role"] in ("user", "assistant") and m["content"]
        )
        user_msg = user_sim(persona, convo)
        if not user_msg:
            print("USER : <goodbye>")
            break

    uid = eng.dvs.get("booking_uid") or ""
    verified = False
    if uid:
        import json as _json
        env = {}
        for line in open("/home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/.env"):
            if line.strip().startswith("CAL_ACCOUNTS="):
                env = _json.loads(line.strip().split("=", 1)[1])
        acct = env["diallux_live"]
        cal_key = acct["cal_api_key"]
        vr = requests.get(f"https://api.cal.com/v2/bookings/{uid}",
                          headers={"Authorization": f"Bearer {cal_key}",
                                   "cal-api-version": "2026-05-01",
                                   "User-Agent": "diallux-sim/1.0"}, timeout=15)
        verified = vr.status_code == 200 and vr.json().get("data", {}).get("status") == "accepted"

    expect_book = persona["expect"] == "book"
    ok = (bool(uid) and verified) if expect_book else (not uid)
    print(f"\nRESULT idx={idx} {'PASS' if ok else 'FAIL'} | state={eng.state} | "
          f"booking_uid={uid or '-'} | cal_accepted={verified} | turns={turns}")
    eng.finish()   # persist FULL conversation to Langfuse
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = LOGS / f"sim_{stamp}_idx{idx}_{persona['name'].split('—')[0].strip().replace(' ', '_').lower()}.json"
    out.write_text(json.dumps({
        "persona": persona["name"], "expect": persona["expect"], "pass": ok,
        "booking_uid": uid, "cal_accepted": verified, "turns": turns,
        **eng.dump_transcript(),
    }, indent=2, default=str))
    print(f"transcript: {out}")
    return ok


if __name__ == "__main__":
    idxs = [int(a) for a in sys.argv[1:]] or ORDER
    results = {i: run_persona(i) for i in idxs}
    print(f"\n=== LADDER: {sum(results.values())}/{len(results)} PASS ===")
    sys.exit(0 if all(results.values()) else 1)
