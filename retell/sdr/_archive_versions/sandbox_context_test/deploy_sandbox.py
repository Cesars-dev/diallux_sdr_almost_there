#!/usr/bin/env python3
"""SANDBOX: main + contact(collect) + verify — context-fill vs incremental extraction.
Creates 2 tiny chat agents (T1 ctx, T2 incr). Never touches production agents."""
import os, json, sys, urllib.request, urllib.error

BASE = "https://api.retellai.com"
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ.get("RETELL_API_KEY")
if not KEY:
    envp = os.path.join(HERE, "..", "..", ".env")
    for line in open(envp):
        if line.strip().startswith("RETELL_API_KEY="):
            KEY = line.strip().split("=", 1)[1]
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def api(method, path, data=None):
    req = urllib.request.Request(f"{BASE}/{path}", data=json.dumps(data).encode() if data else None,
                                 method=method, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        print(f"API {e.code} {path}: {e.read().decode()[:300]}"); sys.exit(1)

FIELDS = ["first_name","last_name","company_name","email","callback_number",
          "prospect_timezone","is_calling_best_number","best_time_window"]

GENERAL = """# Identity
You are Linda, a friendly scheduling assistant at Dialux. Warm, casual, human. Contractions always. ONE question at a time.

# Your job this call
Gather these 8 details from the caller: first name, last name, company name, best email, best phone number, their time zone (Eastern/Central/Mountain/Pacific), whether the number they're on is the best one, and the best time window for a 20-minute call.

# Rules
- NEVER invent or guess a value. Never store an empty value.
- Speak time zones by friendly name only (never "America/Chicago").
- Phone numbers need country code (+1...).
- Keep replies short. Mirror their tone."""

CHECK_CODE = '''const g = k => (dv[k] == null ? "" : String(dv[k])).trim();
const problems = [];
for (const k of ["first_name","last_name","company_name","email","best_time_window"]) {
  if (!g(k)) problems.push({field: k});
}
if (!/^\\+[1-9]\\d{6,14}$/.test(g("callback_number"))) problems.push({field: "callback_number"});
if (["America/New_York","America/Chicago","America/Denver","America/Los_Angeles"].indexOf(g("prospect_timezone")) < 0)
  problems.push({field: "prospect_timezone"});
const b = g("is_calling_best_number");
if (b !== "true" && b !== "false") problems.push({field: "is_calling_best_number"});
return { ok: problems.length === 0, missing_count: problems.length, problems };'''

VAR_DESCS = {
    "first_name": "Caller's first name, their own words",
    "last_name": "Caller's last name, their own words",
    "company_name": "Business / company name",
    "email": "Best email address",
    "callback_number": "Best phone number with country code (E.164)",
    "prospect_timezone": "IANA timezone mapped from friendly name",
    "is_calling_best_number": "true/false — is the number they're on the best one",
    "best_time_window": "Preferred time window for the call",
    "collection_done": "true only when all 8 details are gathered",
    "verify_done": "true only after check_details returned ok:true",
}

def extract_tool(name, desc, fields):
    return {"type": "extract_dynamic_variable", "name": name, "description": desc,
            "speak_after_execution": False,
            "variables": [{"name": f, "type": "string", "description": VAR_DESCS.get(f, f"Value of {f}")}
                          for f in fields]}

COLLECT_PROMPT = """# Mission
Have a natural conversation and collect all 8 details listed above. One question at a time. Mirror their pace.

# Flow
Ask for what's missing, conversationally. When you're confident you have ALL 8, call `collection_done` once, then say "One moment while I confirm everything…" and call `transition_to_Verify`."""

VERIFY_PROMPT_T1 = """# Mission (context-extract variant)
Start: "One moment while I confirm everything…"

1. Call `extract_all_details` ONCE — pull ALL 8 values from the ENTIRE conversation so far, in the caller's own words. If a value was never said anywhere, leave it uncaptured — never guess.
2. Call `check_details`. Read the returned JSON.
3. For EACH item in `problems`: apologize naturally for missing it and ask again — e.g. <Oh— my bad, I didn't catch your company name. What is it?> One field per question.
4. After they answer, call `extract_all_details` again, then `check_details` again. Repeat until `ok: true`.
5. Once ok: give a one-line confirmation, call `verify_done`, done."""

VERIFY_PROMPT_T2 = """# Mission (verify-and-repair variant)
Start: "One moment while I confirm everything…"

1. Call `check_details`. Read the returned JSON. (Values were captured during the conversation.)
2. For EACH item in `problems`: apologize naturally for missing it and ask again — e.g. <Oh— sorry, I didn't catch your last name. Could you give me that?> One field per question.
3. After each answer, capture it with `capture_repair`, then call `check_details` again. Repeat until `ok: true`.
4. Once ok: give a one-line confirmation, call `verify_done`, done."""

def build(variant):
    if variant == "ctx":
        collect_tools = [extract_tool("collection_done",
            "Set collection_done=true ONLY when you believe all 8 details have been gathered.",
            ["collection_done"])]
        verify_tools = [
            extract_tool("extract_all_details",
                "ONE pass: extract ALL 8 values (first_name, last_name, company_name, email, callback_number, "
                "prospect_timezone, is_calling_best_number, best_time_window) from the ENTIRE conversation so far. "
                "prospect_timezone must be stored as IANA mapped from friendly names: Eastern->America/New_York, "
                "Central->America/Chicago, Mountain->America/Denver, Pacific->America/Los_Angeles. "
                "Leave a variable uncaptured if it was never spoken — NEVER store empty or guessed values.",
                FIELDS),
            {"type": "code", "name": "check_details", "description":
                "Validates every detail. Returns {ok, missing_count, problems:[{field}]}. "
                "ok:true means ready. If ok:false, politely re-ask exactly the listed fields.",
             "code": CHECK_CODE, "timeout_ms": 5000, "speak_during_execution": False,
             "speak_after_execution": True},
            extract_tool("verify_done", "Set verify_done=true ONLY after check_details returned ok:true.", ["verify_done"]),
        ]
        collect_prompt, verify_prompt = COLLECT_PROMPT, VERIFY_PROMPT_T1
    else:
        collect_tools = [
            extract_tool("extract_collect_details",
                "Capture details the moment they surface, in the caller's own words: first_name, last_name, "
                "company_name, email, callback_number (+country code), prospect_timezone (IANA mapped: "
                "Eastern->America/New_York, Central->America/Chicago, Mountain->America/Denver, Pacific->America/Los_Angeles), "
                "is_calling_best_number (true/false), best_time_window. NEVER store empty or guessed values — leave uncaptured instead.",
                FIELDS),
            extract_tool("collection_done",
                "Set collection_done=true ONLY when you believe all 8 details have been gathered.",
                ["collection_done"]),
        ]
        repair = extract_tool("capture_repair",
            "Capture ONLY the field(s) just re-asked and answered. Same rules: verbatim, never empty, tz mapped to IANA.", FIELDS)
        verify_tools = [
            {"type": "code", "name": "check_details", "description":
                "Validates every detail. Returns {ok, missing_count, problems:[{field}]}. "
                "If ok:false, apologize for each missing field and re-ask one at a time, capturing answers with capture_repair.",
             "code": CHECK_CODE, "timeout_ms": 5000, "speak_during_execution": False,
             "speak_after_execution": True},
            repair,
            extract_tool("verify_done", "Set verify_done=true ONLY after check_details returned ok:true.", ["verify_done"]),
        ]
        collect_prompt, verify_prompt = COLLECT_PROMPT, VERIFY_PROMPT_T2

    return {
        "model": "gpt-5.1", "model_temperature": 0, "tool_call_strict_mode": True,
        "general_prompt": GENERAL,
        "begin_message": "Thanks for calling Dialux! This is Linda — let's get you set up.",
        "start_speaker": "agent", "starting_state": "Collect",
        "default_dynamic_variables": {f: "" for f in FIELDS},
        "general_tools": [],
        "states": [
            {"name": "Collect", "state_prompt": collect_prompt, "tools": collect_tools,
             "edges": [{"destination_state_name": "Verify",
                        "description": "When collection_done is true, transition to Verify.",
                        "parameters": {"type": "object",
                                       "properties": {"collection_done": {"type": "boolean"}},
                                       "required": ["collection_done"]}}]},
            {"name": "Verify", "state_prompt": verify_prompt, "tools": verify_tools, "edges": []},
        ],
    }

def main():
    out = {}
    for variant, name in [("ctx", "SANDBOX ctx-fill T1"), ("incr", "SANDBOX incremental T2")]:
        payload = build(variant)
        r = api("POST", "create-retell-llm", payload)
        llm_id = r.get("llm_id")
        a = api("POST", "create-chat-agent", {"agent_name": name,
                "response_engine": {"type": "retell-llm", "llm_id": llm_id}})
        out[variant] = {"agent_id": a.get("agent_id"), "llm_id": llm_id}
        print(f"{variant}: agent={a.get('agent_id')} llm={llm_id}")
    json.dump(out, open(os.path.join(HERE, "sandbox_agents.json"), "w"), indent=2)

if __name__ == "__main__":
    main()
