#!/usr/bin/env python3
"""Pure validation logic for /validate_lead.

Design rules (owner-locked):
- Understand anything with recoverable meaning (fuzzy parse); bounce anything without.
- A bounce always ships an ask-line so the loop has an honest exit.
- Rounding: floor to 2 significant digits ($32,578 -> $32,000, $6,756 -> $6,700).
- last_name optional; first_name OR company_name satisfies the name requirement.
"""

import re

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
}

TIMEZONE_ALIASES = {
    "america/new_york": "America/New_York",
    "america/chicago": "America/Chicago",
    "america/denver": "America/Denver",
    "america/los_angeles": "America/Los_Angeles",
    "america/phoenix": "America/Phoenix",
    "eastern": "America/New_York",
    "central time": "America/Chicago",
    "central": "America/Chicago",
    "mountain": "America/Denver",
    "pacific": "America/Los_Angeles",
    "pst": "America/Los_Angeles",
    "est": "America/New_York",
    "cst": "America/Chicago",
    "mst": "America/Denver",
    "arizona": "America/Phoenix",
}

VALID_TIMEZONES = set(TIMEZONE_ALIASES.values())

E164_RE = re.compile(r"^\+1[2-9]\d{9}$")

# Values that mean "nothing was actually captured"
JUNK_VALUES = {"n/a", "na", "none", "unknown", "idk", "tbd", "-", "--", "?"}

# ---------------------------------------------------------------- iter28: human-time containment gate
_CANON_SYNONYMS = [(re.compile(r"\bnoon\b"), "12:00 pm"), (re.compile(r"\bmidnight\b"), "12:00 am")]
_CANON_AT_RE = re.compile(r"\bat (\d{1,2})(?::(\d{2}))? ?(am|pm)?\b")
_CANON_STANDALONE_RE = re.compile(r"(?<![\d:])(\d{1,2}) (am|pm)\b")
_CANON_FILLER_RE = re.compile(r"\b(around|about) ")
_CANON_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}\b")
_DAY_WORD_RE = re.compile(r"^(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b\s*")


def canonical(value):
    """Canonical human-time form — MIRROR of cal_slots_endpoint _norm_human
    (keep in lockstep): lowercase, collapse spaces, strip commas, noon/midnight
    -> H:MM am|pm, 'at H[:MM] [am|pm]' -> H:MM am|pm (bare hour <= 6 -> PM —
    the generator only offers bare hours for afternoon/evening), standalone
    'H am|pm' -> 'H:00 am|pm', filler words + m/d dates dropped."""
    t = re.sub(r"\s+", " ", str(value or "").strip().lower()).replace(",", "")
    for pat, repl in _CANON_SYNONYMS:
        t = pat.sub(repl, t)
    t = _CANON_AT_RE.sub(
        lambda m: f"{m.group(1)}:{m.group(2) or '00'} {m.group(3) or ('pm' if int(m.group(1)) <= 6 else 'am')}",
        t,
    )
    t = _CANON_STANDALONE_RE.sub(lambda m: f"{m.group(1)}:00 {m.group(2)}", t)
    t = _CANON_FILLER_RE.sub("", t)
    t = _CANON_DATE_RE.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


def time_contained(pick, options):
    """iter28 gate: the pick passes only when contained in the offered options.
    A leading day word is strippable ONLY when that same day word appears in
    the options (same-day short offers don't repeat the day on the 2nd time);
    an unoffered day word never strips -> invented slots still bounce."""
    pc, oc = canonical(pick), canonical(options)
    if pc and pc in oc:
        return True
    m = _DAY_WORD_RE.match(pc)
    if m and m.group(1) in oc:
        return pc[m.end():] in oc
    return False


def first_num(value):
    """Extract first recoverable number from messy input.

    "$5,000 to $10,000+" -> 5000 (conservative low end)
    "25 or 30" -> 25 ; "fifty percent" -> 50 ; 20 -> 20
    Returns None when no meaning is recoverable.
    """
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None
    m = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?", s.replace(",", ","))
    if m:
        try:
            return int(float(m.group(0).replace(",", "")))
        except ValueError:
            return None
    for word in re.findall(r"[a-z]+", s):
        if word in WORD_NUMBERS and WORD_NUMBERS[word] > 0:
            return WORD_NUMBERS[word]
    return None


def round_2sig(n):
    """Floor to 2 significant digits: 32578 -> 32000, 6756 -> 6700."""
    n = int(n)
    if n <= 0:
        return 0
    magnitude = 10 ** (len(str(n)) - 2)
    return (n // magnitude) * magnitude


def format_money(n):
    return "${:,}".format(round_2sig(int(n)))


def normalize_phone(raw):
    """Digit-extract then normalize. Returns (e164_or_None, suggestion_or_None).

    "(312) 555-1234" -> ("+13125551234", None)      recovered
    "+13125551234"   -> ("+13125551234", None)      already valid
    "312555123"      -> (None, "+1312555123")       unrecoverable, show cleaned attempt
    "calling_number" -> (None, None)                nothing there
    """
    if raw is None:
        return None, None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "23456789":
        e164 = "+1" + digits
        if E164_RE.match(e164):
            return e164, None
    if not digits or len(digits) < 7:
        return None, None
    return None, "+" + digits


def resolve_timezone(raw):
    """Map aliases/enums to canonical IANA. Returns canonical or None."""
    if not raw:
        return None
    key = str(raw).strip().lower()
    if key in TIMEZONE_ALIASES:
        return TIMEZONE_ALIASES[key]
    for canon in VALID_TIMEZONES:
        if key == canon.lower():
            return canon
    return None


def is_empty(value):
    if value is None:
        return True
    s = str(value).strip()
    return s == "" or s.lower() in JUNK_VALUES


POLITE_ASKS = {
    "callback_number": (
        "Quick thing - what's the best number to reach you on?"
    ),
    "first_name": "Sorry, who am I speaking with?",
    "company_name": "And what's your company called?",
    "prospect_timezone": "What timezone are you in?",
    "selected_time": "Which of those slots works best for you?",
}

APOLOGETIC_VERIFIES = {
    "callback_number": (
        "Oh sorry, I didn't get your number quite right - could you verify it real quick?"
    ),
    "first_name": "Whoops, my bad - could you give me your name again?",
    "company_name": "Whoops, my bad - what's your company name again?",
    "prospect_timezone": "Sorry, which timezone was that again?",
    "selected_time": "Sorry, I lost track - which slot did you pick?",
}


def validate_lead(payload):
    """Full verdict. Returns dict with machine boolean + LLM speech guidance."""
    problems = []
    actions = []

    # --- text fields ---
    field_checks = [
        ("first_name", payload.get("first_name")),
        ("company_name", payload.get("company_name")),
        ("callback_number", payload.get("callback_number")),
        ("prospect_timezone", payload.get("prospect_timezone")),
        ("selected_time", payload.get("selected_time")),
    ]

    # Name requirement: first_name OR company_name
    name_ok = not is_empty(payload.get("first_name")) or not is_empty(
        payload.get("company_name")
    )
    if not name_ok:
        problems.append({"field": "name", "reason": "missing"})
        actions.append(f"Say: '{POLITE_ASKS['first_name']}'")

    # callback_number: empty -> polite; present-broken -> apologetic (+suggestion)
    cb_raw = payload.get("callback_number")
    if is_empty(cb_raw):
        problems.append({"field": "callback_number", "reason": "missing"})
        actions.append(f"Say: '{POLITE_ASKS['callback_number']}'")
    else:
        e164, suggestion = normalize_phone(cb_raw)
        if e164 is None:
            reason = f"unparseable:{cb_raw!r}"
            if suggestion:
                reason += f";suggest:{suggestion}"
            problems.append({"field": "callback_number", "reason": reason})
            actions.append(f"Say: '{APOLOGETIC_VERIFIES['callback_number']}'")

    # timezone
    tz_raw = payload.get("prospect_timezone")
    if is_empty(tz_raw):
        problems.append({"field": "prospect_timezone", "reason": "missing"})
        actions.append(f"Say: '{POLITE_ASKS['prospect_timezone']}'")
    else:
        tz = resolve_timezone(tz_raw)
        if tz is None:
            problems.append({"field": "prospect_timezone", "reason": f"unresolvable:{tz_raw!r}"})
            actions.append(f"Say: '{APOLOGETIC_VERIFIES['prospect_timezone']}'")

    # selected_time — iter28: empty -> polite ask; slot_options present ->
    # containment gate (the pick must be one the server offered); no
    # slot_options -> back-compat (non-empty pick passes, booking re-gates).
    st = payload.get("selected_time")
    if is_empty(st):
        problems.append({"field": "selected_time", "reason": "missing"})
        actions.append(f"Say: '{POLITE_ASKS['selected_time']}'")
    else:
        slot_options = payload.get("slot_options")
        if not is_empty(slot_options) and not time_contained(st, slot_options):
            problems.append({"field": "selected_time", "reason": f"not_offered:{st!r}"})
            actions.append(f"Say: '{APOLOGETIC_VERIFIES['selected_time']}'")

    data_complete = len(problems) == 0

    # --- leak math (only meaningful once complete; compute anyway from clamped inputs) ---
    calls = first_num(payload.get("missed_calls_per_week"))
    close = first_num(payload.get("close_rate_percent"))
    job = first_num(payload.get("avg_job_value"))
    weekly_leak = monthly_leak = None
    if calls is not None and close is not None and job is not None:
        calls = max(0, min(calls, 500))
        close = max(0, min(close, 100))
        job = max(0, min(job, 100000))
        weekly = int(calls * (close / 100.0) * job)
        weekly_leak = format_money(weekly)
        monthly_leak = format_money(weekly * 4.33)

    result = {
        "ok": True,
        "data_complete": data_complete,
        "slot_verified": data_complete,
        "problems": problems,
        "actions": actions,
        "weekly_leak": weekly_leak,
        "monthly_leak": monthly_leak,
        "inputs_used": {
            "missed_calls_per_week": calls,
            "close_rate_percent": close,
            "avg_job_value": job,
        },
    }
    return result
