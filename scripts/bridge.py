#!/usr/bin/env python3
"""Bridge: Retell current_calendar -> time service (today) -> cal_slots_endpoint (slots).

Verifies the three pieces co-exist:
  1. Extract the agent's "Today" line from Retell's {{current_calendar}} (14-day listing).
  2. Call time_endpoint /time-function/parse-time (signed) -> today (YYYY-MM-DD).
  3. Call cal_slots_endpoint /check_availability (signed) with slot_target_date = today -> slots.

Usage:
  python3 bridge.py                      # run against a generated current_calendar for *now*
  python3 bridge.py "Sunday, August 2, 2026 BST (Today)\\n..."   # pass a real Retell calendar
"""

import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.abspath(__file__))
TIME_ENV = os.path.join(ROOT, "time_endpoint", ".env")

TIME_URL = "https://slots.diallux-ai.site/time-function/parse-time"
SLOTS_URL = "https://slots.diallux-ai.site/check_availability"

RETELL_API_KEY = ""
for line in open(TIME_ENV):
    line = line.strip()
    if line.startswith("RETELL_API_KEY="):
        RETELL_API_KEY = line.split("=", 1)[1].strip()
        break
if not RETELL_API_KEY:
    sys.exit("bridge: RETELL_API_KEY not found in " + TIME_ENV)

DEFAULT_TZ = "Europe/London"


def _signed(method, url, body):
    raw = json.dumps(body).encode()
    ts = str(int(time.time() * 1000))
    digest = hmac.new(RETELL_API_KEY.encode(), raw + ts.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        url, data=raw, method=method,
        headers={
            "Content-Type": "application/json",
            "X-Retell-Signature": f"v={ts},d={digest}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def first_line_to_time_string(current_calendar: str) -> str:
    """Pull the 'Today' line out of the 14-day calendar and strip its marker.

    Retell first line looks like:  "Sunday, August 2, 2026 BST (Today)"
    """
    first = (current_calendar.strip().splitlines() or [""])[0].strip()
    return re.sub(r"\s*\(Today\)\s*$", "", first).strip()


def today_from_calendar(current_calendar: str, tz: str = DEFAULT_TZ) -> dict:
    """Call the time service to turn the calendar into a standardized today."""
    time_string = first_line_to_time_string(current_calendar)
    code, body = _signed("POST", TIME_URL, {
        "source_timezone": tz,
        "current_time": time_string,
        "requested_format": ["today", "now", "iso_format"],
    })
    body["_time_string"] = time_string
    body["_http"] = code
    return body


def slots_for_date(today: str, account_id: str | None = None) -> dict:
    """Call cal_slots_endpoint for the day derived from the calendar."""
    payload = {"slot_target_date": today}
    if account_id:
        payload["account_id"] = account_id
    code, body = _signed("POST", SLOTS_URL, payload)
    body["_http"] = code
    return body


def _sample_calendar(tz: str = DEFAULT_TZ, days: int = 14) -> str:
    """Generate a realistic current_calendar for *now* (for local testing)."""
    z = ZoneInfo(tz)
    today = datetime.now(z).date()
    lines = []
    for i in range(days):
        d = today + timedelta(days=i)
        label = " (Today)" if i == 0 else ""
        lines.append(f"{d.strftime('%A, %B %-d, %Y')} {today.strftime('%Z')}{label}")
    return "\n".join(lines)


def run(current_calendar: str | None = None, tz: str = DEFAULT_TZ, account_id: str | None = None):
    cal = current_calendar or _sample_calendar(tz)
    print("=== STEP 1: Retell current_calendar (first 3 lines) ===")
    print("\n".join(cal.strip().splitlines()[:3]))

    print("\n=== STEP 2: time service /parse-time ===")
    t = today_from_calendar(cal, tz)
    today = t.get("today")
    print(f"http={t.get('_http')} ok={t.get('ok')} today={today} tz={t.get('timezone')} "
          f"(parsed '{t.get('_time_string')}')")
    if not today:
        print("STOP: could not derive today from calendar:", json.dumps(t, default=str))
        return

    print("\n=== STEP 3: cal_slots_endpoint /check_availability (slot_target_date=" + today + ") ===")
    s = slots_for_date(today, account_id)
    slots = s.get("slots", [])
    print(f"http={s.get('_http')} ok={s.get('ok')} error={s.get('error')} n_slots={len(slots)}")
    for slot in slots[:3]:
        print("  ", slot.get("day"), slot.get("time"))
    if s.get("message"):
        print("message:", s.get("message"))

    print("\n=== RESULT ===")
    print("Pipeline OK" if (t.get("ok") and s.get("ok")) else "Pipeline has issues")


if __name__ == "__main__":
    cal_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(cal_arg)
