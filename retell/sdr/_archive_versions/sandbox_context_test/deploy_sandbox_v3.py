#!/usr/bin/env python3
"""Repair-strategy A/B: R1 prompt-side repair vs R2 code-tool-directed repair."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ.get("RETELL_API_KEY")
if not KEY:
    for line in open(os.path.join(HERE, "..", "..", ".env")):
        if line.strip().startswith("RETELL_API_KEY="):
            KEY = line.strip().split("=", 1)[1]

FIELDS = ["first_name", "last_name", "company_name", "email", "callback_number",
          "prospect_timezone", "is_calling_best_number", "best_time_window"]

VAR_DESCS = {
    "first_name": "Caller's first name, their own words",
    "last_name": "Caller's last name, their own words",
    "company_name": "Business / company name",
    "email": "Best email address",
    "callback_number": "Best phone number with country code (E.164)",
    "prospect_timezone": "IANA timezone mapped from friendly name",
    "is_calling_best_number": "true/false - is the number they're on the best one",
    "best_time_window": "Preferred time window for the call",
}

TZ_MAP = ("Eastern->America/New_York, Central->America/Chicago, Mountain->America/Denver "
          "(Arizona stays America/Phoenix->use America/Denver), Pacific->America/Los_Angeles")

CHECK_CODE_V1 = '''const g = k => (dv[k] == null ? "" : String(dv[k])).trim();
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

# R2: same validation, but response carries an executable repair recipe
CHECK_CODE_R2 = '''const g = k => (dv[k] == null ? "" : String(dv[k])).trim();
const HINT = {
  first_name: "the caller's first name (they stated it earlier in this conversation)",
  last_name: "the caller's last name (stated earlier)",
  company_name: "the business/company name (stated earlier)",
  email: "the email address (stated earlier)",
  callback_number: "phone in +countrycode format (stated earlier)",
  prospect_timezone: "IANA zone: one of America/New_York, America/Chicago, America/Denver, America/Los_Angeles",
  is_calling_best_number: "true or false",
  best_time_window: "e.g. mornings / afternoons / evenings"
};
const problems = [];
for (const k of ["first_name","last_name","company_name","email","best_time_window"]) {
  if (!g(k)) problems.push(k);
}
if (!/^\\+[1-9]\\d{6,14}$/.test(g("callback_number"))) problems.push("callback_number");
if (["America/New_York","America/Chicago","America/Denver","America/Los_Angeles"].indexOf(g("prospect_timezone")) < 0)
  problems.push("prospect_timezone");
const b = g("is_calling_best_number");
if (b !== "true" && b !== "false") problems.push("is_calling_best_number");
if (problems.length === 0) return { ok: true, missing_count: 0, problems: [] };
const recipe = problems.map(p => p + "=[" + HINT[p] + "]").join(", ");
return { ok: false, missing_count: problems.length,
  problems: problems.map(p => ({field: p})),
  repair_recipe: "Call extract_missing_details NOW with exactly these arguments, values taken from what the caller already said: " + recipe +
    ". Do NOT ask the caller anything yet." };'''

def extract_tool(name, desc, fields):
    return {"type": "extract_dynamic_variable", "name": name, "description": desc,
            "speak_after_execution": False,
            "variables": [{"name": f, "type": "string", "description": VAR_DESCS.get(f, f"Value of {f}")}
                          for f in fields]}

GENERAL_PROMPT = """You are Linda, a friendly scheduling assistant for Dialux, an AI receptionist service for small businesses.

Your ONLY job in this opening phase is warm conversation: greet the caller, ask what prompted them to reach out, listen, and show interest. Ask about their business and how things are going with handling their calls. Be curious and personable.

As facts surface naturally (name, company, email, phone, timezone, best time to reach them), capture them right away with extract_collect_details. NEVER invent or store empty values - only store what the caller actually said.

When you have gathered all eight details (first name, last name, company, email, callback number, timezone, whether this is their best number, best time window), say you have everything you need and move to the verification phase.

Keep replies short and conversational."""

COLLECT_PROMPT = """You are continuing a friendly intake call for Dialux. Your job here: gather ALL eight details through natural conversation - first name, last name, company name, email, callback number, their timezone, whether the number they're calling from is their best number, and the best time window to reach them.

Capture each fact the moment it surfaces using extract_collect_details - only fields actually stated, never guesses, never empties.

Do not interrogate. Weave questions into conversation. Once all eight are captured, confirm warmly and transition to the verify phase."""

VERIFY_PROMPT_R1 = """You are verifying the caller's details for Dialux.

Step 1: Call check_details. It validates all eight stored values.
Step 2: If it returns ok:false - DO NOT ask the caller anything yet. Re-fire extract_missing_details ONCE, filling ONLY the fields listed in problems, with each value taken verbatim from what the caller ALREADY said earlier in this conversation. Store the plain value itself, e.g. first_name=Taylor - NEVER wrap values in brackets or quotes.
Step 3: Call check_details again.
ONLY if a field was genuinely NEVER spoken by the caller, briefly apologize ('Oh - sorry, I didn't catch your phone number') and ask for that one thing alone. Ask at most ONE follow-up question per missing field - never repeat yourself.
When check_details returns ok:true, set verify_done=true, thank them warmly, tell them their dedicated Dialux specialist will call at their preferred time, say goodbye, then use end_call."""

VERIFY_PROMPT_R2 = """You are verifying the caller's details for Dialux.

Call check_details. It validates all eight stored values.
If it returns ok:false, follow its repair_recipe EXACTLY - it tells you precisely which arguments to pass to extract_missing_details and where the values come from. Store plain values only - NEVER wrap them in brackets or quotes. Execute the recipe at most twice, calling check_details after each pass.
Only for a field that was genuinely NEVER spoken by the caller, briefly apologize ('Oh - sorry, I didn't catch your phone number') and ask for that one thing alone. At most ONE follow-up question per missing field - never repeat yourself.
When check_details returns ok:true, set verify_done=true, thank them warmly, tell them their dedicated Dialux specialist will call at their preferred time, say goodbye, then use end_call."""

def build(variant):
    assert variant in ("R1", "R2")
    verify_code = CHECK_CODE_V1 if variant == "R1" else CHECK_CODE_R2
    verify_prompt = VERIFY_PROMPT_R1 if variant == "R1" else VERIFY_PROMPT_R2
    return {
        "model": "gpt-5.1",
        "model_temperature": 0.1,
        "tool_call_strict_mode": True,
        "starting_state": "main",
        "start_speaker": "agent",
        "begin_message": "Hello! You have reached Dialux, this is Linda speaking - how may I help you today?",
        "general_prompt": GENERAL_PROMPT,
        "states": [
            {"name": "main", "edges": [
                {"description": "After greeting and any opening exchange, move to intake.",
                 "destination_state_name": "collect"}]},
            {"name": "collect", "tools": [
                extract_tool("extract_collect_details",
                    "Capture details the moment they surface, in the caller's own words: "
                    "first_name, last_name, company_name, email, callback_number (+country code), "
                    "prospect_timezone (IANA mapped: " + TZ_MAP + "), "
                    "is_calling_best_number (true/false), best_time_window. "
                    "NEVER store empty or guessed values - leave uncaptured instead.", FIELDS),
                {"type": "end_call", "name": "end_call",
                 "description": "End politely if caller refuses everything.",
                 "speak_after_execution": True,
                 "execution_message": "Thanks for your time - have a great day!"}],
             "state_prompt": COLLECT_PROMPT, "edges": [
                {"description": "All eight details captured and confirmed.",
                 "destination_state_name": "verify"}]},
            {"name": "verify", "tools": [
                {"type": "code", "name": "check_details",
                 "description": "Validates all eight stored details. Returns ok, missing_count, problems"
                     + (" and repair_recipe." if variant == "R2" else "."),
                 "code": verify_code, "timeout_ms": 5000,
                 "speak_during_execution": False, "speak_after_execution": True},
                extract_tool("extract_missing_details",
                    "Repair pass: fill ONLY the fields flagged by check_details, each value taken "
                    "verbatim from what the caller already said earlier in this conversation "
                    "(e.g. first_name=[Taylor]). Leave nothing guessed.", FIELDS),
                {"type": "end_call", "name": "end_call",
                 "description": "End the call warmly AFTER verify_done=true and the goodbye is spoken.",
                 "speak_after_execution": True,
                 "execution_message": ""},
                {"name": "verify_done", "type": "extract_dynamic_variable",
                 "description": "Set verify_done=true ONLY after check_details returned ok:true.",
                 "speak_after_execution": False,
                 "variables": [{"name": "verify_done", "type": "string",
                                "description": "true only after check_details returned ok:true"}]}],
             "state_prompt": verify_prompt, "edges": []},
        ],
        "llm_websocket_url": "",
        "version": 0,
    }

def api(method, path, data=None):
    import urllib.request, urllib.error
    req = urllib.request.Request(f"https://api.retellai.com/{path}",
        data=json.dumps(data).encode() if data else None, method=method,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        print(f"API {e.code}: {e.read().decode()[:300]}")
        sys.exit(1)

if __name__ == "__main__":
    out = {}
    for variant in ("R1", "R2"):
        llm = api("POST", "create-retell-llm", build(variant))
        out_llm_id = llm.get("retell_llm_id") or llm["llm_id"]
        agent = api("POST", "create-chat-agent",
                    {"response_engine": {"type": "retell-llm", "llm_id": out_llm_id, "version": 0},
                     "agent_name": f"SANDBOX repair-v3 {variant}"})
        out[variant] = {"agent_id": agent["agent_id"], "llm_id": out_llm_id}
        print(f"{variant}: agent={agent['agent_id']} llm={out_llm_id}")
    json.dump(out, open(os.path.join(HERE, "sandbox_agents_v3.json"), "w"), indent=2)
