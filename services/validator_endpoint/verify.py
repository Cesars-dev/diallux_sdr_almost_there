#!/usr/bin/env python3
"""Pure logic for /verify-lead-data and /record-booking-uid (V7.6 VerifyLead state).

Owner-locked contracts:
- CONTEXT FIRST, ASK SECOND: missing values ship literal Say-lines (never LLM-improvised);
  the model pulls from conversation context before ever speaking them.
- Never inject empty/unverified values: missing -> incomplete(+actions),
  unrecoverable data -> incomplete(apologetic re-ask), server trouble -> error(+notify).
- Cal.com v2 UIDs are exactly 22-char [A-Za-z0-9] - anything else is invalid_uid.
"""

import re

from pydantic import BaseModel, ValidationError

from validate import (
    APOLOGETIC_VERIFIES,
    POLITE_ASKS,
    is_empty,
    normalize_phone,
    resolve_timezone,
    time_contained,
)

UID_RE = re.compile(r"^[A-Za-z0-9]{22}$")
TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(:\d{2})?$")


# ---------------------------------------------------------------- pydantic in
class VerifyLeadRequest(BaseModel):
    """Loose strings IN - normalization happens in code below, never in the LLM.
    None-tolerant: Retell pollution arrives as nulls; treated as missing."""

    model_config = {"extra": "ignore"}

    first_name: str | None = ""
    last_name: str | None = ""
    company_name: str | None = ""
    callback_number: str | None = ""
    prospect_timezone: str | None = ""
    selected_time: str | None = ""
    slot_options: str | None = ""

    def coerced(self) -> dict:
        return {k: ("" if v is None else str(v)) for k, v in
                self.model_dump().items()}


class RecordUidRequest(BaseModel):
    """Strict OUT-gate: a polluted/fabricated uid fails parsing before any logic."""

    model_config = {"extra": "ignore"}

    booking_uid: str


def parse_verify_payload(raw: dict):
    """Returns (VerifyLeadRequest|None, error_str)."""
    try:
        return VerifyLeadRequest(**raw), None
    except ValidationError as e:
        return None, "; ".join(
            f"{'.'.join(str(x) for x in err['loc'])}:{err['type']}" for err in e.errors()
        )


def parse_uid_payload(raw: dict):
    """Returns (uid_str|None, error_str). Pattern-fail => invalid_uid."""
    try:
        req = RecordUidRequest(**raw)
    except ValidationError:
        return None, "invalid_uid"
    if not UID_RE.match(req.booking_uid):
        return None, "invalid_uid"
    return req.booking_uid, None


# ------------------------------------------------------------- field fixers
def _clean_name(value):
    return re.sub(r"\s+", " ", str(value)).strip()[:80]


def _fix_time(value):
    """Light coercion: '2026-08-26 15:15' / ISO-without-seconds -> full ISO."""
    m = TIME_RE.match(str(value).strip())
    if not m:
        return None
    date, hm, secs = m.group(1), m.group(2), m.group(3)
    return f"{date}T{hm}{secs or ':00'}"


# ------------------------------------------------------------------- verdict
def verify_lead_data(payload: dict) -> dict:
    """Deterministic gate. Returns the literal payload the LLM will read."""
    try:
        req, perr = parse_verify_payload(payload)
    except Exception as e:  # absolute last resort - never 500 the loop
        return {
            "status": "error",
            "data_verified": False,
            "problems": [{"field": "server", "issue": f"exception:{e}"}],
            "actions": [],
        }
    if req is None:
        return {
            "status": "error",
            "data_verified": False,
            "problems": [{"field": "payload", "issue": perr}],
            "actions": [],
        }
    req = VerifyLeadRequest(**req.coerced())

    problems = []
    actions = []
    injected = {}

    # --- name requirement: first_name OR company_name ---
    first = _clean_name(req.first_name)
    company = _clean_name(req.company_name)
    if is_empty(first) and is_empty(company):
        problems.append({"field": "name", "issue": "missing"})
        actions.append(f"Say: '{POLITE_ASKS['first_name']}'")
    elif not is_empty(first):
        injected["first_name"] = first

    # --- callback_number: missing -> polite; garbled -> apologetic re-ask ---
    if is_empty(req.callback_number):
        problems.append({"field": "callback_number", "issue": "missing"})
        actions.append(f"Say: '{POLITE_ASKS['callback_number']}'")
    else:
        e164, _suggestion = normalize_phone(req.callback_number)
        if e164 is None:
            problems.append({"field": "callback_number", "issue": "unparseable"})
            actions.append(f"Say: '{APOLOGETIC_VERIFIES['callback_number']}'")
        else:
            injected["callback_number"] = e164

    # --- timezone: missing -> polite; alias -> canonical inject ---
    if is_empty(req.prospect_timezone):
        problems.append({"field": "prospect_timezone", "issue": "missing"})
        actions.append(f"Say: '{POLITE_ASKS['prospect_timezone']}'")
    else:
        tz = resolve_timezone(req.prospect_timezone)
        if tz is None:
            problems.append({"field": "prospect_timezone", "issue": "unresolvable"})
            actions.append(f"Say: '{APOLOGETIC_VERIFIES['prospect_timezone']}'")
        else:
            injected["prospect_timezone"] = tz

    # --- selected_time — iter28 gate: empty -> polite; ISO fast-path -> fixed
    # inject (back-compat); human pick passes ONLY when contained in the
    # offered slot_options (NO injection — dvs keeps the human pick, booking
    # resolves it against the holds); anything else -> apologetic re-ask.
    if is_empty(req.selected_time):
        problems.append({"field": "selected_time", "issue": "missing"})
        actions.append(f"Say: '{POLITE_ASKS['selected_time']}'")
    else:
        fixed = _fix_time(req.selected_time)
        if fixed is not None:
            injected["selected_time"] = fixed
        elif not is_empty(req.slot_options) and time_contained(req.selected_time, req.slot_options):
            pass  # contained pick — time resolution remains booking-side
        else:
            problems.append({"field": "selected_time", "issue": "unfixable_format"})
            actions.append(f"Say: '{APOLOGETIC_VERIFIES['selected_time']}'")

    if not is_empty(req.last_name):
        injected["last_name"] = _clean_name(req.last_name)
    if not is_empty(company):
        injected["company_name"] = company

    if problems:
        return {
            "status": "incomplete",
            "data_verified": False,
            "problems": problems,
            "actions": actions,
        }

    return {
        "status": "ok",
        "data_verified": True,
        "problems": [],
        "actions": [],
        **injected,
    }


def record_booking_uid(uid_or_error: str | None, error: str | None) -> dict:
    """22-char contract. Invalid never writes - returns the retry contract."""
    if error or not uid_or_error:
        return {"status": "error", "error": error or "invalid_uid"}
    return {"status": "ok", "booking_uid": uid_or_error}


# ------------------------------------------------------------------- callback number
class SetCallbackNumberRequest(BaseModel):
    """10-digit US/CA number IN. Server normalizes to E.164; never trusts LLM formatting."""
    model_config = {"extra": "ignore"}
    callback_number: str


def _wrong_number(raw):
    """wrong_number payload: a meta-directive the model ACTS ON (never spoken aloud).
    Distinct from the validate_lead Say:-line pattern — no Say: prefix, so the global
    'speak Say: lines verbatim' rule does NOT fire here (prevents jargon to the caller)."""
    return {
        "status": "wrong_number",
        "action": "review_and_recapture",
        "instruction": (
            f"The number '{raw}' is not a valid 10-digit number. "
            "Review your conversation context for the correct callback number. "
            "If context holds a different number, call set_callback_number with that one. "
            "If the number you sent is the only one available, ask the caller to repeat their number."
        ),
    }


def set_callback_number(payload: dict) -> dict:
    """Deterministic writer of callback_number + phone_confirmed.

    ok  -> {"status":"ok","callback_number":"<E.164>","phone_confirmed":true}  (Retell writes both dvs)
    bad -> {"status":"wrong_number","action":...,"instruction":...}  (NO callback_number/phone_confirmed -> no write)
    err -> {"status":"error","problems":[...]}              (NO callback_number/phone_confirmed -> no write)
    """
    try:
        req = SetCallbackNumberRequest(**payload)
    except ValidationError:
        return _wrong_number(payload.get("callback_number", ""))
    raw = (req.callback_number or "").strip()
    if is_empty(raw):
        return _wrong_number(raw)
    try:
        e164, _ = normalize_phone(raw)
    except Exception as e:  # never 500 the loop
        return {"status": "error",
                "problems": [{"field": "callback_number", "issue": f"exception:{e}"}]}
    if e164 is None:
        return _wrong_number(raw)
    return {"status": "ok", "callback_number": e164, "phone_confirmed": True}


# ------------------------------------------------------------------- reach details mirror
_TRUE_RE = re.compile(r"^(yes|y|true|correct|right|yeah|yep|1)$", re.I)
_FALSE_RE = re.compile(r"^(no|n|false|wrong|another|different|0|nope)$", re.I)
_TRUE_WORDS_RE = re.compile(r"\b(yes|true|correct|right|yeah)\b", re.I)
_FALSE_WORDS_RE = re.compile(r"\b(no|false|another|different)\b", re.I)


def _coerce_bool(raw):
    """Tolerant yes/no IN. Bools pass through; ints compare to 1; strings match
    exact words first, then embedded words; anything else -> None (no write)."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return raw == 1
    s = str(raw).strip().lower()
    if not s:
        return None
    if _TRUE_RE.match(s):
        return True
    if _FALSE_RE.match(s):
        return False
    if _TRUE_WORDS_RE.search(s):
        return True
    if _FALSE_WORDS_RE.search(s):
        return False
    return None


def record_reach_details(payload: dict) -> dict:
    """Deterministic writer of is_calling_best_number (+ phone_confirmed on YES only).

    ok YES -> {"status":"ok","is_calling_best_number":true,"phone_confirmed":true}  (Retell writes both dvs)
    ok NO  -> {"status":"ok","is_calling_best_number":false}   (NO phone_confirmed key -> no write;
              a NO answer must never un-confirm an already-confirmed callback number)
    bad    -> {"status":"invalid_answer","instruction":"..."}   (NO dv keys -> no write)
    """
    raw = payload.get("is_calling_best_number") if isinstance(payload, dict) else None
    best = _coerce_bool(raw)
    if best is None:
        return {
            "status": "invalid_answer",
            "action": "ask_and_retry",
            "instruction": (
                f"The value '{raw}' for is_calling_best_number is not a yes/no answer. "
                "Ask the caller: 'Is the number you're calling from the best one to reach you?' "
                "then call record_reach_details AGAIN with exactly true or false — never anything else."
            ),
        }
    if best:
        return {"status": "ok", "is_calling_best_number": True, "phone_confirmed": True}
    return {"status": "ok", "is_calling_best_number": False}
