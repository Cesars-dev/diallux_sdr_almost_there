#!/usr/bin/env python3
"""Fixture matrix for validate.py — run: python3 test_validate.py"""

import sys

from validate import first_num, normalize_phone, resolve_timezone, round_2sig, format_money, validate_lead

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        FAILS.append(name)
        print(f"  FAIL  {name}  {detail}")


print("== unit: first_num ==")
check("plain int", first_num(20) == 20)
check("range low end", first_num("$5,000 to $10,000+") == 5000)
check("or-range", first_num("25 or 30") == 25)
check("word number", first_num("fifty percent") == 50)
check("junk", first_num("calling_number") is None)
check("empty", first_num("") is None)
check("none", first_num(None) is None)

print("== unit: round_2sig ==")
check("32,578 -> 32,000", round_2sig(32578) == 32000)
check("6,756 -> 6,700", round_2sig(6756) == 6700)
check("650 stays", round_2sig(650) == 650)
check("money fmt", format_money(6756) == "$6,700")

print("== unit: phone ==")
e164, sug = normalize_phone("(312) 555-1234")
check("normalize parens", e164 == "+13125551234" and sug is None, f"{e164} {sug}")
e164, sug = normalize_phone("+13125551234")
check("already valid", e164 == "+13125551234", f"{e164}")
e164, sug = normalize_phone("3125551234")
check("bare 10 digits", e164 == "+13125551234", f"{e164}")
e164, sug = normalize_phone("calling_number")
check("junk -> none", e164 is None and sug is None, f"{e164} {sug}")
e164, sug = normalize_phone("")
check("empty -> none", e164 is None and sug is None)

print("== unit: timezone ==")
check("alias central", resolve_timezone("Central time") == "America/Chicago")
check("canonical passthrough", resolve_timezone("America/New_York") == "America/New_York")
check("garbage", resolve_timezone("the moon") is None)

print("== integration: full verdicts ==")

clean = {
    "first_name": "Maria", "company_name": "Cornerstone",
    "callback_number": "+13125551234", "prospect_timezone": "Central time",
    "selected_time": "2026-08-27T15:00:00-05:00",
    "missed_calls_per_week": 20, "close_rate_percent": 50, "avg_job_value": 650,
}
r = validate_lead(clean)
check("clean -> verified", r["slot_verified"] is True and r["data_complete"] is True)
check("clean math weekly", r["weekly_leak"] == "$6,500", r["weekly_leak"])
check("clean math monthly", r["monthly_leak"] == "$28,000", r["monthly_leak"])
check("no actions when clean", r["actions"] == [])

r = validate_lead({**clean, "callback_number": ""})
check("empty phone -> fail + polite ask",
      r["slot_verified"] is False
      and any("best number" in a for a in r["actions"]), r["actions"])

r = validate_lead({**clean, "callback_number": "calling_number"})
check("junk phone -> fail + apologetic ask",
      r["slot_verified"] is False
      and any("didn't get your number" in a for a in r["actions"]), r["actions"])

r = validate_lead({**clean, "callback_number": "(312) 555-1234"})
check("messy-but-recoverable phone passes", r["slot_verified"] is True)

r = validate_lead({k: v for k, v in clean.items() if k != "first_name"})
check("last_name optional / company suffices", r["slot_verified"] is True)

r = validate_lead({k: v for k, v in clean.items() if k not in ("first_name", "company_name")})
check("no name at all -> problem",
      r["slot_verified"] is False and any(p["field"] == "name" for p in r["problems"]))

r = validate_lead({**clean, "prospect_timezone": "the moon"})
check("bad tz -> apologetic ask",
      r["slot_verified"] is False and any("timezone" in a for a in r["actions"]), r["actions"])

r = validate_lead({**clean,
                   "missed_calls_per_week": "25 or 30",
                   "close_rate_percent": "fifty percent",
                   "avg_job_value": "$5,000 to $10,000+"})
check("fuzzy math inputs parse", r["inputs_used"]["missed_calls_per_week"] == 25
      and r["inputs_used"]["close_rate_percent"] == 50
      and r["inputs_used"]["avg_job_value"] == 5000, r["inputs_used"])
check("sofia-bomb math safe", r["weekly_leak"] == "$62,000", r["weekly_leak"])

r = validate_lead({"first_name": "", "company_name": "", "callback_number": "",
                   "prospect_timezone": "", "selected_time": ""})
check("all empty -> multiple polite asks, never true",
      r["slot_verified"] is False and len(r["actions"]) >= 4, r["actions"])

print()
if FAILS:
    print(f"FAILED: {len(FAILS)} -> {FAILS}")
    sys.exit(1)
print("ALL FIXTURES PASS")

# ============================================================ V7.6 verify.py
from verify import parse_uid_payload, record_booking_uid, record_reach_details, set_callback_number, verify_lead_data

print("\n--- verify_lead_data (V7.6) ---")

r = verify_lead_data({"first_name": "Sam", "last_name": "Ortiz",
                      "company_name": "Ortiz Roofing",
                      "callback_number": "(469) 555-0001",
                      "prospect_timezone": "central",
                      "selected_time": "2026-08-26T15:15:00"})
check("clean payload -> ok + normalized injects",
      r["status"] == "ok" and r["data_verified"] is True
      and r["callback_number"] == "+14695550001"
      and r["prospect_timezone"] == "America/Chicago"
      and r["selected_time"] == "2026-08-26T15:15:00", r)

r = verify_lead_data({"first_name": "  Sam   Ortiz ",
                      "callback_number": "+1 469 555 0001",
                      "prospect_timezone": "central",
                      "selected_time": "2026-08-26 15:15"})
check("messy formats coerced (name spaces, +1 prefix, time no secs)",
      r["status"] == "ok" and r["first_name"] == "Sam Ortiz"
      and r["callback_number"] == "+14695550001"
      and r["selected_time"] == "2026-08-26T15:15:00", r)

r = verify_lead_data({"company_name": "Bright Smile Dental",
                      "callback_number": "+13125551234",
                      "prospect_timezone": "America/New_York",
                      "selected_time": "2026-08-26T09:00:00"})
check("company alone satisfies name (no first_name)",
      r["status"] == "ok" and r.get("company_name") == "Bright Smile Dental", r)

r = verify_lead_data({"first_name": "Sam", "callback_number": "",
                      "prospect_timezone": "", "selected_time": ""})
check("missing fields -> incomplete + polite Say-lines, never verified",
      r["status"] == "incomplete" and r["data_verified"] is False
      and len(r["actions"]) == 3
      and all(a.startswith("Say:") for a in r["actions"]), r["actions"])

r = verify_lead_data({"first_name": "Sam", "callback_number": "555-000-0000",
                      "prospect_timezone": "mars", "selected_time": "tomorrow-ish"})
check("555 passes format (Cal judges), garbage tz/time -> apologetic incomplete",
      r["status"] == "incomplete"
      and {p["issue"] for p in r["problems"]} == {"unresolvable", "unfixable_format"}
      and any("sorry" in a.lower() for a in r["actions"]), r)

r = verify_lead_data({"first_name": "Sam", "last_name": None,
                      "company_name": None, "callback_number": None,
                      "prospect_timezone": None, "selected_time": None})
check("None values tolerated (loose pydantic) -> incomplete not crash",
      r["status"] == "incomplete", r)

r = verify_lead_data({"first_name": "Sam", "callback_number": "+14695550001",
                      "prospect_timezone": "America/Chicago",
                      "selected_time": "2026-08-26T15:15:00",
                      "mystery_junk_key": True})
check("extra junk keys ignored (extra=ignore)", r["status"] == "ok", r)

print("\n--- record_booking_uid (V7.6) ---")
u, e = parse_uid_payload({"booking_uid": "35vvF17una7ZBdFBu8rHPz"})
check("real-shaped 22-char uid ok", u == "35vvF17una7ZBdFBu8rHPz" and e is None)
check("recorder ok payload", record_booking_uid(u, e)["status"] == "ok")

for bad in ["35vvF17una7ZBdFBu8rHP", "35vvF17una7ZBdFBu8rHPzz", "35vvF17una7ZBdFBu8rH-z",
            "", "   ", "booking_35vvF17una7ZBdFBu8rHP"]:
    u, e = parse_uid_payload({"booking_uid": bad})
    check(f"reject malformed uid {bad!r}", u is None and e == "invalid_uid")
    check("invalid -> error payload, no write", record_booking_uid(u, e)
          == {"status": "error", "error": "invalid_uid"})

u, e = parse_uid_payload({})
check("missing key -> invalid_uid", u is None and e == "invalid_uid")

print("\n--- set_callback_number ---")
r = set_callback_number({"callback_number": "3125551234"})
check("bare 10 digits -> ok", r == {"status": "ok", "callback_number": "+13125551234", "phone_confirmed": True}, r)
r = set_callback_number({"callback_number": "+13125551234"})
check("already E.164 -> ok", r["status"] == "ok" and r["callback_number"] == "+13125551234", r)
r = set_callback_number({"callback_number": "(312) 555-1234"})
check("parens -> ok", r["status"] == "ok" and r["callback_number"] == "+13125551234", r)
r = set_callback_number({"callback_number": "13125551234"})
check("11-digit leading 1 stripped -> ok", r["status"] == "ok" and r["callback_number"] == "+13125551234", r)
for bad in ["312555123", "", "   ", "unknown", "-", "5550182", "calling_number", "give me a call"]:
    r = set_callback_number({"callback_number": bad})
    check(f"reject {bad!r} -> wrong_number", r["status"] == "wrong_number", r)
    check(f"no callback_number key on wrong_number {bad!r}", "callback_number" not in r, r)
r = set_callback_number({"callback_number": "3125551234", "junk_extra": True})
check("extra keys ignored", r["status"] == "ok", r)
r = set_callback_number({})
check("missing field -> wrong_number", r["status"] == "wrong_number", r)

print("\n--- record_reach_details ---")
r = record_reach_details({"is_calling_best_number": True})
check("bool true -> ok both true", r == {"status": "ok", "is_calling_best_number": True, "phone_confirmed": True}, r)
r = record_reach_details({"is_calling_best_number": False})
check("bool false -> ok, NO phone_confirmed key (no clobber)", r == {"status": "ok", "is_calling_best_number": False}, r)
r = record_reach_details({"is_calling_best_number": "Yes"})
check("str Yes -> ok true", r["status"] == "ok" and r["phone_confirmed"] is True, r)
r = record_reach_details({"is_calling_best_number": "yes, this is fine"})
check("phrase yes -> ok true", r["status"] == "ok" and r["phone_confirmed"] is True, r)
r = record_reach_details({"is_calling_best_number": 1})
check("int 1 -> ok true", r["status"] == "ok" and r["phone_confirmed"] is True, r)
r = record_reach_details({"is_calling_best_number": "another number"})
check("phrase another -> ok false, no phone_confirmed", r["status"] == "ok" and r["is_calling_best_number"] is False and "phone_confirmed" not in r, r)
r = record_reach_details({"is_calling_best_number": "0"})
check("str 0 -> ok false, no phone_confirmed", r["status"] == "ok" and r["is_calling_best_number"] is False and "phone_confirmed" not in r, r)
r = record_reach_details({"is_calling_best_number": "banana"})
check("junk -> invalid_answer", r["status"] == "invalid_answer", r)
check("junk -> no dv keys", "phone_confirmed" not in r and "is_calling_best_number" not in r, r)
r = record_reach_details({})
check("missing arg -> invalid_answer", r["status"] == "invalid_answer", r)
r = record_reach_details({"is_calling_best_number": "nope"})
check("nope -> ok false, no phone_confirmed", r["status"] == "ok" and r["is_calling_best_number"] is False and "phone_confirmed" not in r, r)
r = record_reach_details(None)
check("non-dict payload -> invalid_answer", r["status"] == "invalid_answer", r)

print("\n--- iter28: canonical() + time_contained() ---")
from validate import canonical, time_contained

check("canonical noon", canonical("Tomorrow at NOON") == "tomorrow 12:00 pm", canonical("Tomorrow at NOON"))
check("canonical midnight", canonical("at midnight") == "12:00 am", canonical("at midnight"))
check("canonical bare pm", canonical("tomorrow at 5") == "tomorrow 5:00 pm", canonical("tomorrow at 5"))
check("canonical bare am", canonical("today at 11") == "today 11:00 am", canonical("today at 11"))
check("canonical standalone", canonical("tomorrow, 12 pm") == "tomorrow 12:00 pm", canonical("tomorrow, 12 pm"))
check("canonical around+date", canonical("tomorrow, 9/8 around noon") == "tomorrow 12:00 pm", canonical("tomorrow, 9/8 around noon"))
check("canonical afternoon word untouched", canonical("this afternoon at 5") == "this afternoon 5:00 pm", canonical("this afternoon at 5"))

OPTS = "tomorrow, 9/8 at noon or 5:30 pm"
for pick in ["tomorrow at noon", "tomorrow, 9/8 at noon", "noon", "12 pm", "5:30 pm",
             "at 5:30", "tomorrow around noon", "tomorrow, 12 pm"]:
    check(f"contained pick passes: {pick!r}", time_contained(pick, OPTS), canonical(pick))
for pick in ["tomorrow at 6:30 pm", "friday at noon", "midnight", "tomorrow at 4",
             "today at noon", "9 pm"]:
    check(f"invented pick bounces: {pick!r}", not time_contained(pick, OPTS), canonical(pick))

SHORT = "today, 9/7 at 11 am or 2:30 pm"
for pick in ["2:30 pm", "today at 2:30 pm", "11 am", "today at 11 am", "today, 9/7 at 2:30 pm"]:
    check(f"same-day short form contains: {pick!r}", time_contained(pick, SHORT), canonical(pick))
check("unoffered day never strips", not time_contained("friday at 2:30 pm", SHORT))

print("\n--- iter28: validate_lead containment gate ---")
base = {k: v for k, v in clean.items() if k != "selected_time"}
r = validate_lead({**base, "selected_time": "tomorrow at noon", "slot_options": OPTS})
check("validate: contained pick -> verified", r["slot_verified"] is True and r["actions"] == [], r)
r = validate_lead({**base, "selected_time": "tomorrow at 6:30 pm", "slot_options": OPTS})
check("validate: invented pick -> not_offered + apologetic Say-line",
      r["slot_verified"] is False
      and any(p["reason"].startswith("not_offered") for p in r["problems"])
      and any("which slot did you pick" in a for a in r["actions"]), r)
r = validate_lead({**base, "selected_time": "tomorrow at noon"})
check("validate: no slot_options -> back-compat pass", r["slot_verified"] is True, r)
r = validate_lead({**base, "selected_time": "", "slot_options": OPTS})
check("validate: empty pick -> polite ask",
      r["slot_verified"] is False and any("Which of those slots" in a for a in r["actions"]), r)

print("\n--- iter28: verify_lead_data containment gate ---")
vbase = {"first_name": "Sam", "callback_number": "+14695550001", "prospect_timezone": "central"}
r = verify_lead_data({**vbase, "selected_time": "tomorrow at noon", "slot_options": OPTS})
check("verify: contained pick -> ok, NO selected_time injection (stays human)",
      r["status"] == "ok" and r["data_verified"] is True and "selected_time" not in r, r)
r = verify_lead_data({**vbase, "selected_time": "5:30 pm", "slot_options": OPTS})
check("verify: bare/noon variant contained -> ok", r["status"] == "ok", r)
r = verify_lead_data({**vbase, "selected_time": "tomorrow at 6:30 pm", "slot_options": OPTS})
check("verify: invented pick -> unfixable_format + apologetic",
      r["status"] == "incomplete"
      and {"unfixable_format"} <= {p["issue"] for p in r["problems"]}
      and any("which slot did you pick" in a for a in r["actions"]), r)
r = verify_lead_data({**vbase, "selected_time": "tomorrow at noon"})
check("verify: human pick without slot_options -> still bounced (fail closed)",
      r["status"] == "incomplete" and "unfixable_format" in {p["issue"] for p in r["problems"]}, r)
r = verify_lead_data({**vbase, "selected_time": "2026-09-08 12:00", "slot_options": OPTS})
check("verify: ISO fast-path retained -> fixed inject",
      r["status"] == "ok" and r["selected_time"] == "2026-09-08T12:00:00", r)
r = verify_lead_data({**vbase, "selected_time": "", "slot_options": OPTS})
check("verify: empty pick -> polite Say-line",
      r["status"] == "incomplete" and any("Which of those slots" in a for a in r["actions"]), r)
r = verify_lead_data({**vbase, "selected_time": "today at 2:30 pm",
                      "slot_options": SHORT})
check("verify: same-day short-form pick (day-strip) -> ok", r["status"] == "ok", r)

print(f"\n== {'ALL PASS' if not FAILS else str(len(FAILS)) + ' FAILS'} ==")
sys.exit(1 if FAILS else 0)
