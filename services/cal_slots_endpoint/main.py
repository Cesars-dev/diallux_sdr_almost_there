import hashlib
import asyncio
import hmac
import json
import logging
import os
import random
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import store
from config import resolve, default_account_id, retell_badge_keys
import notify

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("cal_slots")

RETELL_API_KEYS = retell_badge_keys()
CAL_API_VERSION = os.environ.get("CAL_API_VERSION", "2024-09-04")
CAL_COM_BASE = os.environ.get("CAL_COM_BASE", "https://api.cal.com/v2")
SLOT_DURATION_MIN = int(os.environ.get("SLOT_DURATION_MIN", "60"))
LOOKAHEAD_DAYS = int(os.environ.get("LOOKAHEAD_DAYS", "7"))
MAX_SLOTS = int(os.environ.get("MAX_SLOTS", "20"))
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "10"))
RESERVATION_DURATION_SEC = int(os.environ.get("RESERVATION_DURATION_SEC", "900"))
BOOKING_API_VERSION = os.environ.get("BOOKING_API_VERSION", "2026-05-01")
CANCEL_API_VERSION = os.environ.get("CANCEL_API_VERSION", "2026-02-25")
CAL_USER_AGENT = os.environ.get("CAL_USER_AGENT", "diallux-slot-lock/1.0 (slots.diallux-ai.site)")

_default_acct = resolve()
if _default_acct is None:
    raise SystemExit("cal_slots: refusing to start — no account config (CAL_ACCOUNTS or flat env vars)")

if not RETELL_API_KEYS:
    raise SystemExit("cal_slots: refusing to start — missing RETELL_API_KEYS/RETELL_API_KEY")

store.init()

app = FastAPI(title="Cal.com Slot Checker")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "req id=%s path=%s status=%s %dms",
        request_id, request.url.path, response.status_code, duration_ms,
    )
    return response


def _err(status: int, code: str, message: str | None = None):
    store.incr(code)
    body = {"ok": False, "error": code}
    if message:
        body["message"] = message
    return JSONResponse(status_code=status, content=body)


def _upstream_err():
    return JSONResponse(
        status_code=200,
        content={
            "ok": False,
            "error": "upstream_unavailable",
            "message": (
                "Calendar is temporarily unavailable. "
                "Tell the caller you'll check and try again shortly."
            ),
        },
    )


def verify_retell_signature(raw_body: bytes, signature: str | None) -> bool:
    if not RETELL_API_KEYS or not signature:
        return False
    match = re.fullmatch(r"v=(\d+),d=([0-9a-fA-F]+)", signature.strip())
    if not match:
        return False
    timestamp, digest = match.group(1), match.group(2)
    try:
        if abs(int(time.time() * 1000) - int(timestamp)) > 5 * 60 * 1000:
            return False
    except ValueError:
        return False
    for key in RETELL_API_KEYS:
        expected = hmac.new(
            key.encode("utf-8"),
            raw_body + timestamp.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(expected, digest):
            return True
    return False


def fetch_cal_slots(url, headers, params, attempts: int = 2, timeout: int = 10):
    for attempt in range(attempts):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            if resp.status_code < 500:
                return resp
            logger.warning("Cal.com %s (attempt %d)", resp.status_code, attempt + 1)
        except requests.RequestException as exc:
            logger.warning("Cal.com request error (attempt %d): %s", attempt + 1, exc)
        if attempt < attempts - 1:
            time.sleep(0.5 * (attempt + 1))
    return None


def _rate_limited(client_ip: str) -> bool:
    return store.rate_limited(client_ip, RATE_LIMIT_PER_MIN)


def _read_body(request: Request) -> bytes:
    return asyncio.run(request.body())


# ---------------------------------------------------------------------------
# Slot-lock booking helpers (reservations + bookings)
# ---------------------------------------------------------------------------

def _cal_request(method, url, acct, version, *, json_body=None, params=None, attempts=2):
    headers = {
        "Authorization": f"Bearer {acct['cal_api_key']}",
        "cal-api-version": version,
        "Content-Type": "application/json",
        "User-Agent": CAL_USER_AGENT,
    }
    for attempt in range(attempts):
        try:
            resp = requests.request(
                method, url, headers=headers, json=json_body, params=params,
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code < 500:
                return resp
            logger.warning("Cal.com %s %s (attempt %d): %s", method, resp.status_code, attempt + 1, resp.text[:200])
        except requests.RequestException as exc:
            logger.warning("Cal.com %s error (attempt %d): %s", method, attempt + 1, exc)
        if attempt < attempts - 1:
            time.sleep(0.5 * (attempt + 1))
    return None


def _norm_local(t) -> str:
    """Normalize a local wall-time string to YYYY-MM-DDTHH:MM (empty on garbage)."""
    t = str(t or "").strip().replace(" ", "T")
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::(\d{2}))?", t)
    if not m:
        return ""
    return f"{m.group(1)}T{m.group(2)}"


def _split_uids(raw) -> list:
    return [u for u in re.split(r"[,\s]+", str(raw or "")) if u]


# ---------------------------------------------------------------------------
# Human slot contract: slots carry plain-English day/time so the agent reads
# back exactly what it was given and never speaks a machine ISO timestamp.
# ---------------------------------------------------------------------------

_MACHINE_TIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?")
_HUMAN_TIME_RE = re.compile(
    r"(?P<day>today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)?"
    r".*?(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>a\.?m\.?|p\.?m\.?)",
    re.I,
)
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _fmt_time_human(local_dt) -> str:
    """Natural time form: noon/midnight; drop :00; bare hour only for 1-6 pm
    (the PM rule — the canonicalizer maps bare H back to H:00 pm)."""
    h12 = local_dt.hour % 12 or 12
    minute = local_dt.minute
    ampm = "am" if local_dt.hour < 12 else "pm"
    if local_dt.hour == 12 and minute == 0:
        return "noon"
    if local_dt.hour == 0 and minute == 0:
        return "midnight"
    if 13 <= local_dt.hour <= 18 and minute == 0:
        return str(local_dt.hour - 12)
    if minute == 0:
        return f"{h12} {ampm}"
    return f"{h12}:{minute:02d} {ampm}"


def _fmt_day_human(d, today) -> str:
    delta = (d - today).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    if delta <= 6:
        return d.strftime("%A").lower()
    return (d.strftime("%A, %b ") + str(d.day)).lower()  # >6-day delta: "tuesday, sep 15"


def _time_alt(time_human, local_dt) -> str:
    """Alternate natural rendering of the same instant for template variance.
    iter40: noon/midnight keep their word — remapping to "12 pm"/"12 am"
    collided phone-ear with "two pm" (the 2pm loop, t48–t57). The
    canonicalizer maps noon/midnight to 12:00 pm/am on both sides."""
    if time_human == "noon":
        return "noon"
    if time_human == "midnight":
        return "midnight"
    if time_human.isdigit():
        return f"{time_human} pm"
    return time_human


def _humanize_slot(slot, out_tz) -> dict:
    """Add day_human/time_human/human to a slot dict (machine fields untouched).
    human = random pick of 2-3 natural templates — the canonicalizer collapses
    every variant to one form, so any echo of the offer resolves identically."""
    try:
        local_dt = datetime.strptime(slot["time"], "%Y-%m-%dT%H:%M:%S")
        d = local_dt.date()
        day_human = _fmt_day_human(d, datetime.now(out_tz).date())
        time_human = _fmt_time_human(local_dt)
        templates = [
            f"{day_human} at {time_human}",
            f"{day_human}, {_time_alt(time_human, local_dt)}",
        ]
        if not time_human.isdigit():  # bare "around 5" would not canonicalize
            templates.append(f"{day_human} around {time_human}")
        out = dict(slot)
        out["day_human"] = day_human
        out["time_human"] = time_human
        out["human"] = random.choice(templates)
        return out
    except Exception:
        return dict(slot)


def _time_standalone(slot) -> str:
    """Standalone time form for same-day joined offers ('... at noon or 5:30 pm')."""
    t = _fmt_time_human(datetime.strptime(slot["time"], "%Y-%m-%dT%H:%M:%S"))
    return f"{t} pm" if t.isdigit() else t


def _slots_human(slots) -> str:
    """Top-level joined string for {{requested_slot}}: short same-day form, else full humans."""
    humans = [s.get("human") for s in slots if s.get("human")]
    if not humans:
        return ""
    if len({s.get("day_human", "") for s in slots}) == 1:
        try:
            # iter40: same-day join drops the m/dd date — the model read
            # "tomorrow, 9/10 at 6 pm" back as "nine ten" (caller confusion
            # t41–t43). "tomorrow" carries the day; machine fields keep the date.
            times = " or ".join(_time_standalone(s) for s in slots if s.get("time"))
            return f"{slots[0]['day_human']} at {times}"
        except (KeyError, ValueError):
            pass
    return " or ".join(humans)


_CANON_SYNONYMS = [(re.compile(r"\bnoon\b"), "12:00 pm"), (re.compile(r"\bmidnight\b"), "12:00 am")]
_CANON_AT_RE = re.compile(r"\bat (\d{1,2})(?::(\d{2}))? ?(am|pm)?\b")
_CANON_STANDALONE_RE = re.compile(r"(?<![\d:])(\d{1,2}) (am|pm)\b")
_CANON_FILLER_RE = re.compile(r"\b(around|about) ")
_CANON_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}\b")


def _norm_human(s) -> str:
    """Canonical human-time form: lowercase, collapse spaces, strip commas,
    noon/midnight -> H:MM am|pm, 'at H[:MM] [am|pm]' -> H:MM am|pm (bare hour
    <= 6 -> PM — generator only offers bare hours for afternoon/evening),
    standalone 'H am|pm' -> 'H:00 am|pm', filler + m/d dates dropped.
    Mirror of validator_endpoint canonical() — keep the two in lockstep."""
    t = re.sub(r"\s+", " ", str(s or "").strip().lower()).replace(",", "")
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


def _is_machine_time(t) -> bool:
    return bool(_MACHINE_TIME_RE.fullmatch(str(t or "").strip()))


def _hold_local_dt(acct, uid, out_tz):
    """Local datetime of a held slot (None if the hold cannot be read)."""
    resp = _cal_request("GET", f"{CAL_COM_BASE}/slots/reservations/{uid}", acct, CAL_API_VERSION, attempts=1)
    if resp is None or resp.status_code != 200:
        return None
    try:
        data = resp.json().get("data") or {}
    except ValueError:
        return None
    iso = data.get("slotStart") or data.get("start") or (data.get("slot") or {}).get("start")
    if not iso:
        return None
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(out_tz)
    except ValueError:
        return None


def _resolve_booking_time(acct, uid_list, out_tz, raw, anchor_day=None):
    """Human → machine local wall time. (1) exact match against held slots'
    human/time_human, (2) deterministic day-word math (today/tomorrow/weekday +
    'H:MM am/pm'). Returns '' when unresolvable — never guesses.
    iter40: anchor_day lets the availability endpoint anchor bare times
    ('2 pm') to the QUERIED slot_target_date instead of today; default (None)
    keeps today-anchoring for the booking path (unchanged)."""
    text = str(raw or "").strip()
    if not text or re.search(r"\bor\b", text, re.I):
        return ""  # empty or ambiguous (joined options) — fail closed
    tod = _HUMAN_TIME_RE.search(_norm_human(text))
    tod_hm = ""
    if tod and tod.group("ampm"):
        h = int(tod.group("hour")) % 12
        if tod.group("ampm").lower().startswith("p"):
            h += 12
        tod_hm = f"{h:02d}:{int(tod.group('minute') or 0):02d}"

    matches = []
    for uid in uid_list:
        dt = _hold_local_dt(acct, uid, out_tz)
        if dt is None:
            continue
        slot = _humanize_slot(
            {"day": dt.strftime("%Y-%m-%d"), "time": dt.strftime("%Y-%m-%dT%H:%M:%S")}, out_tz
        )
        if _norm_human(slot["human"]) == _norm_human(text) or _norm_human(slot["time_human"]) == _norm_human(text):
            return _norm_local(slot["time"])
        if tod_hm and slot["time"][11:16] == tod_hm:
            matches.append(slot["time"])
    if len(matches) == 1:
        return _norm_local(matches[0])

    if not tod or not tod.group("ampm"):
        return ""
    today = anchor_day or datetime.now(out_tz).date()
    day_w = (tod.group("day") or "").lower()
    if day_w == "today":
        d = today
    elif day_w == "tomorrow":
        d = today + timedelta(days=1)
    elif day_w:
        d = today + timedelta(days=(_WEEKDAYS.index(day_w) - today.weekday()) % 7 or 7)
    else:
        d = today
    h = int(tod.group("hour")) % 12
    if tod.group("ampm").lower().startswith("p"):
        h += 12
    return f"{d.isoformat()}T{h:02d}:{int(tod.group('minute') or 0):02d}"


def reserve_slot(acct, iso) -> str | None:
    """POST /v2/slots/reservations — freeze a slot. Returns reservation uid or None."""
    resp = _cal_request(
        "POST", f"{CAL_COM_BASE}/slots/reservations", acct, CAL_API_VERSION,
        json_body={
            "eventTypeId": int(acct["event_type_id"]),
            "slotStart": iso,
            "reservationDuration": RESERVATION_DURATION_SEC,
        },
    )
    if resp is None or resp.status_code not in (200, 201):
        logger.warning("reserve_slot failed iso=%s status=%s", iso, getattr(resp, "status_code", None))
        return None
    try:
        data = resp.json().get("data") or {}
    except ValueError:
        return None
    uid = (
        data.get("reservationUid")
        or data.get("uid")
        or (data.get("slot") or {}).get("reservationUid")
    )
    if uid:
        store.incr("holds_created")
        return str(uid)
    return None


def release_reservation(acct, uid) -> bool:
    """DELETE /v2/slots/reservations/{uid} — best-effort release."""
    resp = _cal_request("DELETE", f"{CAL_COM_BASE}/slots/reservations/{uid}", acct, CAL_API_VERSION, attempts=1)
    ok = resp is not None and resp.status_code in (200, 204)
    if ok:
        store.incr("holds_released")
    else:
        logger.info("release_reservation uid=%s status=%s", uid, getattr(resp, "status_code", None))
    return ok


def release_all(acct, uids) -> int:
    n = 0
    for uid in uids:
        if release_reservation(acct, uid):
            n += 1
    return n


def _same_phone(a, b) -> bool:
    da = re.sub(r"\D", "", str(a or ""))
    db = re.sub(r"\D", "", str(b or ""))
    if not da or not db:
        return False
    return da.endswith(db) or db.endswith(da)


def find_existing_booking(acct, phone, day_utc: datetime | None = None):
    """GET /v2/bookings (upcoming) — first non-cancelled booking whose attendee phone matches.

    day_utc: when given, only bookings starting on the same UTC day count
    (silent-success recovery scope = the day being booked).
    """
    if not phone:
        return None
    params = {"status": "upcoming", "eventTypeId": acct["event_type_id"], "limit": 50}
    resp = _cal_request("GET", f"{CAL_COM_BASE}/bookings", acct, BOOKING_API_VERSION, params=params)
    if resp is None or resp.status_code != 200:
        logger.warning("find_existing_booking status=%s", getattr(resp, "status_code", None))
        return None
    try:
        data = resp.json().get("data")
    except ValueError:
        return None
    if isinstance(data, dict):
        bookings = data.get("bookings") or []
    elif isinstance(data, list):
        bookings = data
    else:
        bookings = []
    for b in bookings:
        if str(b.get("status", "")).lower() in ("cancelled", "canceled", "rejected"):
            continue
        if day_utc is not None:
            try:
                b_start = datetime.fromisoformat(str(b.get("start", "")).replace("Z", "+00:00"))
            except ValueError:
                continue
            if b_start.date() != day_utc.date():
                continue
        for att in b.get("attendees") or []:
            if _same_phone(att.get("phoneNumber"), phone):
                return b
    return None


def cancel_booking(acct, uid, reason) -> bool:
    resp = _cal_request(
        "POST", f"{CAL_COM_BASE}/bookings/{uid}/cancel", acct, CANCEL_API_VERSION,
        json_body={"cancellationReason": reason, "cancelSubsequentBookings": False},
    )
    ok = resp is not None and resp.status_code == 200
    if not ok:
        logger.warning("cancel_booking uid=%s status=%s", uid, getattr(resp, "status_code", None))
    return ok


def verify_booking_accepted(acct, uid) -> bool:
    resp = _cal_request("GET", f"{CAL_COM_BASE}/bookings/{uid}", acct, BOOKING_API_VERSION)
    if resp is None or resp.status_code != 200:
        return False
    try:
        return str((resp.json().get("data") or {}).get("status", "")).lower() == "accepted"
    except ValueError:
        return False


def create_booking(acct, start_iso, name, phone, tz_name, title, notes):
    """POST /v2/bookings. Returns (booking_uid, error). error None on success."""
    body = {
        "eventTypeId": int(acct["event_type_id"]),
        "start": start_iso,
        "attendee": {
            "name": name,
            "email": acct.get("attendee_email") or "jaydiallux@gmail.com",
            "timeZone": tz_name,
            "phoneNumber": phone,
        },
        "guests": [],
        "location": "integration",
        "bookingFieldsResponses": {"notes": notes or "", "title": title or ""},
    }
    resp = _cal_request("POST", f"{CAL_COM_BASE}/bookings", acct, BOOKING_API_VERSION, json_body=body)
    if resp is None:
        return None, "upstream"
    if resp.status_code in (200, 201):
        try:
            uid = (resp.json().get("data") or {}).get("uid")
        except ValueError:
            uid = None
        if uid:
            store.incr("bookings_created")
            return str(uid), None
        return None, "bad_response"
    return None, f"cal_{resp.status_code}"


def _fetch_slots(acct, out_tz, start_day, now):
    """Fresh Cal.com slot query → sorted [(utc_dt, {day, time[, iso]})], or None on upstream failure."""
    start_dt = datetime(start_day.year, start_day.month, start_day.day, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=LOOKAHEAD_DAYS) - timedelta(seconds=1)
    params = {
        "eventTypeId": acct["event_type_id"],
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "duration": acct["duration"],
    }
    headers = {
        "Authorization": f"Bearer {acct['cal_api_key']}",
        "cal-api-version": CAL_API_VERSION,
    }
    logger.info(
        "Querying Cal.com slots: account=%s event=%s duration=%d start=%s end=%s",
        acct.get("account_id"), acct["event_type_id"], acct["duration"], start_dt.isoformat(), end_dt.isoformat(),
    )
    resp = fetch_cal_slots(f"{CAL_COM_BASE}/slots", headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    if resp is None or resp.status_code != 200:
        logger.error("Cal.com unavailable (status=%s)", getattr(resp, "status_code", None))
        return None
    try:
        body = resp.json()
    except ValueError:
        logger.error("Cal.com returned non-JSON")
        return None
    data = body.get("data")
    if not isinstance(data, dict):
        logger.error("Cal.com unexpected shape: %s", str(body)[:200])
        return None

    out = []
    include_iso = acct.get("include_iso", True)
    for date_key, times in data.items():
        for entry in times:
            iso = entry.get("start")
            if not iso:
                continue
            try:
                dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            except ValueError:
                continue
            if dt <= now:
                continue
            local_dt = dt.astimezone(out_tz)
            slot = _humanize_slot({
                "day": local_dt.strftime("%Y-%m-%d"),
                "time": local_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            }, out_tz)
            if include_iso:
                slot["iso"] = iso
            out.append((dt, slot))
    out.sort(key=lambda x: x[0])
    return out


def _ordered_candidates(slots_with_dt, preferred):
    """Deterministic pick order around a preferred local time (lexicographic ISO compare).

    Returns (candidates, preferred_unavailable).
    """
    pref = _norm_local(preferred)
    if not pref:
        return list(slots_with_dt), False
    head = None
    for pair in slots_with_dt:
        if _norm_local(pair[1].get("time", "")) == pref:
            head = pair
            break
    if head is None:
        after = [p for p in slots_with_dt if _norm_local(p[1].get("time", "")) > pref]
        return (after or list(slots_with_dt)), True
    later = [p for p in slots_with_dt if p is not head and p[0] > head[0]]
    return [head] + later, False


def _freeze_pair(acct, slots_with_dt, preferred):
    """Reserve up to 2 slots in pick order. Returns (held, taken, preferred_unavailable)."""
    candidates, pref_unavail = _ordered_candidates(slots_with_dt, preferred)
    held, taken = [], []
    for _dt, slot in candidates:
        if len(held) >= 2:
            break
        uid = reserve_slot(acct, slot.get("iso"))
        if uid:
            entry = dict(slot)
            entry["reservation_uid"] = uid
            held.append(entry)
        else:
            taken.append(slot.get("time"))
    return held, taken, pref_unavail


def _hold_iso_for(acct, uid, out_tz, time_local):
    """GET /v2/slots/reservations/{uid} — slotStart if the hold's local time matches, else None."""
    resp = _cal_request("GET", f"{CAL_COM_BASE}/slots/reservations/{uid}", acct, CAL_API_VERSION, attempts=1)
    if resp is None or resp.status_code != 200:
        logger.info("hold lookup uid=%s status=%s", uid, getattr(resp, "status_code", None))
        return None
    try:
        data = resp.json().get("data") or {}
    except ValueError:
        return None
    iso = data.get("slotStart") or data.get("start") or (data.get("slot") or {}).get("start")
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if _norm_local(dt.astimezone(out_tz).strftime("%Y-%m-%dT%H:%M:%S")) == time_local:
        return str(iso)
    return None


@app.get("/health")
async def health():
    return {"ok": True, "service": "cal_slots"}


@app.get("/ready")
async def ready():
    problems = []
    if not RETELL_API_KEYS:
        problems.append("RETELL_API_KEYS/RETELL_API_KEY")
    acct = resolve()
    if not acct or not acct.get("cal_api_key"):
        problems.append("account_cal_api_key")
    if not acct or not acct.get("event_type_id"):
        problems.append("account_event_type_id")
    if problems:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "service": "cal_slots", "problems": problems},
        )
    return {"ok": True, "service": "cal_slots", "checks": "pass"}


@app.get("/metrics")
async def metrics():
    return {"ok": True, "counters": store.snapshot()}


@app.get("/today")
async def today(tz: str = "Europe/London"):
    """Return today's date (YYYY-MM-DD) in the requested IANA timezone, from real time."""
    try:
        now = datetime.now(ZoneInfo(tz))
    except Exception:
        return JSONResponse(
            status_code=200,
            content={"ok": False, "error": "invalid_timezone", "message": f"Unknown timezone {tz!r}. Use an IANA name like Europe/London."},
        )
    return {
        "ok": True,
        "today": now.strftime("%Y-%m-%d"),
        "timezone": tz,
        "tz_abbrev": now.strftime("%Z"),
    }


@app.post("/check_availability")
def check_availability(request: Request):
    request_id = request.state.request_id
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown").split(",")[0].strip()
    if _rate_limited(client_ip):
        return _err(429, "rate_limited")

    raw_body = _read_body(request)

    if not verify_retell_signature(raw_body, request.headers.get("X-Retell-Signature")):
        store.incr("sig_rejected")
        logger.warning("Rejected request: invalid or missing X-Retell-Signature")
        logger.warning("SIG=%s", request.headers.get("X-Retell-Signature"))
        notify.send(request_id, "sig_rejected", "invalid or missing X-Retell-Signature")
        return _err(401, "unauthorized")

    try:
        payload = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        return _err(400, "invalid_json")

    args = payload.get("args", payload) if isinstance(payload, dict) else {}

    acct = resolve(args.get("account_id"))
    if acct is None:
        return _err(400, "unknown_account", f"Unknown account_id={args.get('account_id')!r}")

    out_tz_name = args.get("timezone") or acct["timezone"]
    try:
        out_tz = ZoneInfo(out_tz_name)
    except Exception:
        return _err(400, "invalid_timezone", f"Unknown timezone {out_tz_name!r}. Use an IANA name like Europe/London.")

    store.incr("slot_queries")
    now = datetime.now(timezone.utc)

    raw_date = args.get("slot_target_date")
    if not raw_date or not str(raw_date).strip():
        logger.info("validation: missing slot_target_date")
        return _err(
            200,
            "no_start_time",
            "slot_target_date is required. Ask the caller which day they want, then pass the date as YYYY-MM-DD.",
        )
    try:
        target_dt = datetime.strptime(str(raw_date).strip(), "%Y-%m-%d")
    except ValueError:
        logger.info("validation: bad slot_target_date=%r", raw_date)
        return _err(
            200,
            "invalid_slot_target_date",
            f"slot_target_date must be YYYY-MM-DD (got {raw_date!r}). Re-extract the date and retry.",
        )

    slots_with_dt = _fetch_slots(acct, out_tz, target_dt.date(), now)
    if slots_with_dt is None:
        notify.send(request_id, "upstream_unavailable", "Cal.com slots fetch failed")
        return _upstream_err()

    if not slots_with_dt:
        store.incr("no_availability_in_window")
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "error": "no_availability_in_window",
                "message": "No free slots in that window. Offer the next available day.",
            },
        )

    # iter40: humanized preferred_time → machine local (SAME resolver the
    # booking endpoint uses, main.py /book-livecall) — day anchored to the
    # queried slot_target_date. Plain-English ("2 pm", "noon", "tomorrow at
    # 1 pm") previously fell through to _norm_local (machine-only) and was
    # silently ignored; the tool schema advertised it. Unresolvable strings
    # are left as-is → _norm_local ignores them (behavior unchanged).
    preferred_raw = str(args.get("preferred_time") or "").strip()
    if preferred_raw and not _is_machine_time(preferred_raw):
        resolved = _resolve_booking_time(acct, [], out_tz, preferred_raw,
                                         anchor_day=target_dt.date())
        if resolved:
            args["preferred_time"] = resolved
            logger.info("availability: humanized preferred_time %r -> %s",
                        preferred_raw, resolved)

    freeze_mode = ("current_reservation_uids" in args) or ("preferred_time" in args)
    if not freeze_mode:
        slots_out = [s for _, s in slots_with_dt[:MAX_SLOTS]]
        logger.info("Returning %d future slots (legacy)", len(slots_out))
        return JSONResponse(status_code=200, content={"ok": True, "slots": slots_out, "slots_human": _slots_human(slots_out)})

    # --- slot-lock mode: release echoed holds, freeze the deterministic pair ---
    held_uids = _split_uids(args.get("current_reservation_uids"))
    if held_uids:
        store.incr("reissued_count")
        release_all(acct, held_uids)

    held, taken, pref_unavail = _freeze_pair(acct, slots_with_dt, args.get("preferred_time"))

    if not held:
        store.incr("no_free_slots")
        logger.info("Slot-lock: nothing frozen (taken=%s)", taken)
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "slots": [],
                "taken": taken,
                "reissued": bool(held_uids),
                "preferred_unavailable": pref_unavail,
                "slot_reservation_uids": "",
                "message": "Every candidate time was just taken. Ask the caller for a different day.",
            },
        )

    out_slots = []
    for e in held:
        entry = dict(e)
        entry["reservation_uid"] = e["reservation_uid"]
        out_slots.append(entry)

    logger.info(
        "Slot-lock: returning %d frozen slots (reissued=%s preferred_unavailable=%s taken=%s)",
        len(out_slots), bool(held_uids), pref_unavail, taken,
    )
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "slots": out_slots,
            "taken": taken,
            "reissued": bool(held_uids),
            "preferred_unavailable": pref_unavail,
            "slot_reservation_uids": ",".join(e["reservation_uid"] for e in held),
            "slots_human": _slots_human(out_slots),
        },
    )


# ---------------------------------------------------------------------------
# POST /book-livecall — deterministic booking endpoint (create_livecall_booking)
# ---------------------------------------------------------------------------

def _booked_response(uid, verified, recovered, rescheduled_from=None, booked_human=None):
    content = {
        "ok": True,
        "status": "booked",
        "booking_uid": uid,
        "recovered": bool(recovered),
    }
    if booked_human:
        content["booked_human"] = booked_human
    if verified:
        content["booking_verified"] = True
    if rescheduled_from:
        content["rescheduled_from"] = rescheduled_from
    content["message"] = (
        "Booking confirmed. Close with the booked_human time verbatim if present — "
        "never compose or convert a time."
    )
    return JSONResponse(status_code=200, content=content)


def _booked_human(time_local, out_tz):
    """Plain-English form of the confirmed start for the close-out (None on garbage)."""
    try:
        return _humanize_slot({"time": time_local + ":00"}, out_tz).get("human")
    except Exception:
        return None


def _commit_booking(acct, out_tz, request_id, *, time_local, name, phone,
                    uid_list, title, notes, reschedule=False, existing_before=None):
    """The ONLY path that creates a booking. Fail-closed: booking_uid keys appear
    in the response only on success."""
    tz_name = out_tz.key
    day_utc = None
    try:
        day_utc = datetime.fromisoformat(time_local + ":00").replace(tzinfo=ZoneInfo(tz_name)).astimezone(timezone.utc)
    except Exception:
        day_utc = None

    if not reschedule:
        # Silent-success recovery: if a booking for this caller already exists on
        # this day, report it (idempotent — double calls get the existing UID).
        existing = find_existing_booking(acct, phone, day_utc)
        if existing and existing.get("uid"):
            store.incr("recovered")
            logger.info("recovered existing booking uid=%s", existing["uid"])
            return _booked_response(existing["uid"], verify_booking_accepted(acct, existing["uid"]), True,
                                    booked_human=_booked_human(time_local, out_tz))

    # Resolve the start ISO: hold match → fresh-validation fallback.
    start_iso = None
    for uid in uid_list:
        start_iso = _hold_iso_for(acct, uid, out_tz, time_local)
        if start_iso:
            break

    if not start_iso:
        start_day = None
        try:
            start_day = datetime.strptime(time_local[:10], "%Y-%m-%d").date()
        except ValueError:
            start_day = None
        if start_day is None:
            return _err(200, "invalid_time", "time must be a local wall time like 2026-09-04T11:00 (or with seconds).")
        now = datetime.now(timezone.utc)
        fresh = _fetch_slots(acct, out_tz, start_day, now)
        if fresh is None:
            notify.send(request_id, "upstream_unavailable", "slots fetch during booking failed")
            return _upstream_err()
        for _dt, slot in fresh:
            if _norm_local(slot.get("time", "")) == time_local:
                start_iso = slot.get("iso")
                break
        if not start_iso:
            store.incr("book_failed_taken")
            logger.info("book_failed slot_taken time=%s", time_local)
            return JSONResponse(
                status_code=200,
                content={
                    "ok": False,
                    "status": "book_failed",
                    "reason": "slot_taken",
                    "message": (
                        "That time was just taken. Apologize, do NOT book anything, and ask the "
                        "caller if another time works."
                    ),
                },
            )
        # Slot is free on a fresh query — try to shield it, but booking does not
        # depend on the reservation succeeding.
        reserve_slot(acct, start_iso)

    uid, err = create_booking(acct, start_iso, name, phone, tz_name, title, notes)
    if err:
        store.incr("booking_error")
        notify.send(request_id, "booking_error", f"{err} start={start_iso}")
        logger.warning("create_booking failed err=%s start=%s", err, start_iso)
        if reschedule:
            return JSONResponse(
                status_code=200,
                content={
                    "ok": False,
                    "status": "book_failed",
                    "reason": err,
                    "message": (
                        "The new time could not be booked. The existing appointment is untouched. "
                        "Apologize and ask the caller to keep the current time or pick another."
                    ),
                },
            )
        # create-then-retry-sees-itself self-heal: a 4xx may hide a booking that
        # actually landed — check before reporting failure.
        existing = find_existing_booking(acct, phone, day_utc)
        if existing and existing.get("uid"):
            store.incr("recovered")
            logger.info("recovered booking after create err=%s uid=%s", err, existing["uid"])
            return _booked_response(existing["uid"], verify_booking_accepted(acct, existing["uid"]), True,
                                    booked_human=_booked_human(time_local, out_tz))
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "status": "book_failed",
                "reason": err,
                "message": (
                    "The booking system hiccuped. Apologize, tell the caller you will call them "
                    "right back to confirm, and end politely. Do not retry the booking."
                ),
            },
        )

    verified = verify_booking_accepted(acct, uid)
    release_all(acct, uid_list)

    old_uid = None
    if reschedule and existing_before and existing_before.get("uid") and existing_before["uid"] != uid:
        # Old booking captured BEFORE the new one was created — never strand the caller.
        if cancel_booking(acct, existing_before["uid"], "Rescheduled by the caller"):
            old_uid = existing_before["uid"]
            store.incr("reschedule_cancels")

    logger.info("booked uid=%s verified=%s reschedule_from=%s", uid, verified, old_uid)
    return _booked_response(uid, verified, False, old_uid,
                            booked_human=_booked_human(time_local, out_tz))


@app.post("/book-livecall")
def book_livecall(request: Request):
    request_id = request.state.request_id
    client_ip = request.headers.get(
        "X-Forwarded-For", request.client.host if request.client else "unknown"
    ).split(",")[0].strip()
    if _rate_limited(client_ip):
        return _err(429, "rate_limited")

    raw_body = _read_body(request)

    if not verify_retell_signature(raw_body, request.headers.get("X-Retell-Signature")):
        store.incr("sig_rejected")
        logger.warning("book-livecall: rejected invalid X-Retell-Signature")
        notify.send(request_id, "sig_rejected", "book-livecall invalid or missing X-Retell-Signature")
        return _err(401, "unauthorized")

    try:
        payload = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        return _err(400, "invalid_json")

    args = payload.get("args", payload) if isinstance(payload, dict) else {}

    acct = resolve(args.get("account_id"))
    if acct is None:
        return _err(400, "unknown_account", f"Unknown account_id={args.get('account_id')!r}")

    out_tz_name = args.get("timezone") or acct["timezone"]
    try:
        out_tz = ZoneInfo(out_tz_name)
    except Exception:
        return _err(400, "invalid_timezone", f"Unknown timezone {out_tz_name!r}.")

    booking_intent = str(args.get("booking_intent") or "").strip().lower()
    uid_list = _split_uids(args.get("slot_reservation_uids"))
    name = str(args.get("name") or "").strip()
    phone = str(args.get("attendeePhoneNumber") or "").strip()

    time_raw = str(args.get("time") or "").strip()
    if time_raw and not _is_machine_time(time_raw):
        time_raw = _resolve_booking_time(acct, uid_list, out_tz, time_raw)
        if not time_raw:
            return _err(
                200,
                "invalid_time",
                "Could not resolve that time. Re-check availability, then pass the offered time verbatim.",
            )
        args["time"] = time_raw
    time_local = _norm_local(time_raw)
    preferred_raw = str(args.get("preferred_time") or "").strip()
    if preferred_raw and not _is_machine_time(preferred_raw):
        resolved = _resolve_booking_time(acct, uid_list, out_tz, preferred_raw)
        if resolved:
            args["preferred_time"] = preferred_raw = resolved
    preferred = preferred_raw

    store.incr("booking_calls")

    # --- Path B: cancel — release everything, never book ---
    if booking_intent == "cancel":
        existing = find_existing_booking(acct, phone)
        if existing and existing.get("uid"):
            logger.info("cancel call but booking exists uid=%s — reporting truth", existing["uid"])
            return JSONResponse(
                status_code=200,
                content={
                    "ok": True,
                    "status": "booked",
                    "booking_uid": existing["uid"],
                    "recovered": False,
                    "message": (
                        "A booking already exists for this caller. Report it as booked; the team "
                        "handles cancellations — do not book anything new."
                    ),
                },
            )
        release_all(acct, uid_list)
        store.incr("cancel_releases")
        logger.info("cancel path: released %d holds", len(uid_list))
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "status": "released",
                "message": (
                    "Everything is released. The caller does not want the call. Do not book "
                    "anything and do not offer times."
                ),
            },
        )

    # --- Path C: reschedule ---
    if booking_intent == "reschedule":
        pref_norm = _norm_local(preferred)
        if pref_norm and time_local and pref_norm == time_local:
            # Caller confirmed one of the reissued options → commit.
            if not name or not phone:
                return _err(200, "missing_details", "name and attendeePhoneNumber are required to book.")
            store.incr("reschedules")
            existing_before = find_existing_booking(acct, phone)
            return _commit_booking(
                acct, out_tz, request_id, time_local=time_local, name=name, phone=phone,
                uid_list=uid_list, title=args.get("title"), notes=args.get("notes"),
                reschedule=True, existing_before=existing_before,
            )
        # First reschedule ask → release current holds, freeze a fresh pair.
        if uid_list:
            release_all(acct, uid_list)
        store.incr("reschedules")
        now = datetime.now(timezone.utc)
        anchor = None
        pref_day = _norm_local(preferred)[:10] if preferred else ""
        if pref_day:
            try:
                anchor = datetime.strptime(pref_day, "%Y-%m-%d").date()
            except ValueError:
                anchor = None
        if anchor is None:
            anchor = datetime.now(out_tz).date()
        fresh = _fetch_slots(acct, out_tz, anchor, now)
        if fresh is None:
            notify.send(request_id, "upstream_unavailable", "slots fetch during reschedule failed")
            return _upstream_err()
        held, taken, pref_unavail = _freeze_pair(acct, fresh, preferred)
        out_slots = []
        for e in held:
            entry = dict(e)
            entry["reservation_uid"] = e["reservation_uid"]
            out_slots.append(entry)
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "status": "reschedule_options",
                "slots": out_slots,
                "taken": taken,
                "reissued": True,
                "preferred_unavailable": pref_unavail,
                "slot_reservation_uids": ",".join(e["reservation_uid"] for e in held),
                "slots_human": _slots_human(out_slots),
                "message": (
                    "Offer these two times. When the caller picks one, call this tool again with "
                    "time AND preferred_time both set to the chosen option."
                ),
            },
        )

    # --- Path A: default — book the held slot (no availability checks offered) ---
    if not time_local:
        return _err(200, "no_start_time", "time is required (local wall time like 2026-09-04T11:00).")
    if not name or not phone:
        return _err(200, "missing_details", "name and attendeePhoneNumber are required to book.")
    return _commit_booking(
        acct, out_tz, request_id, time_local=time_local, name=name, phone=phone,
        uid_list=uid_list, title=args.get("title"), notes=args.get("notes"),
        reschedule=False,
    )
