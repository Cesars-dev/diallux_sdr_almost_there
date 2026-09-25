#!/usr/bin/env python3
"""S1.5 unit battery — slot-lock booking (04_master_plan.md STEP 6.1).

Runs the FastAPI app in-process with a FAKE Cal.com (_cal_request + fetch_cal_slots
monkeypatched). No network, no real Cal, separate counter DB in /tmp/opencode.

Run:  python3 test_slot_lock.py
"""
import hashlib
import hmac
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

os.environ["CAL_ACCOUNTS"] = json.dumps({
    "test_acct": {
        "cal_api_key": "cal_live_test",
        "event_type_id": 3801235,
        "timezone": "America/Chicago",
        "duration": 45,
    }
})
os.environ["RETELL_API_KEYS"] = json.dumps(["test_key_123"])
os.environ.pop("TELEGRAM_BOT_TOKEN", None)
os.environ.pop("TELEGRAM_CHAT_ID", None)

import store  # noqa: E402
store.DB_PATH = "/tmp/opencode/test_slot_lock.db"
if os.path.exists(store.DB_PATH):
    os.remove(store.DB_PATH)

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(main.app)
KEY = b"test_key_123"
DAY = "2026-09-10"
ISOS = [f"{DAY}T{h:02d}:00:00.000Z" for h in (15, 16, 17, 18)]  # Chicago: 10,11,12,13
LOCAL = [f"{DAY}T{h:02d}:00:00" for h in (10, 11, 12, 13)]

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not cond else ""))


# ---------------------------------------------------------------- fake Cal.com
class R:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data
        self.text = json.dumps(data)[:200]

    def json(self):
        return self._data


class CalState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.reservations = {}       # uid -> iso
        self.bookings = {}           # uid -> {start, status, phone}
        self.cancelled = set()
        self.fail_reserves = set()   # iso values that fail to reserve
        self.fail_create = None      # status code to fail POST /bookings with
        self.events = []             # ("reserve"|"release"|"create"|"cancel"|"delete_hold", key)
        self._n = 0

    def add_booking(self, uid, iso, phone):
        self.bookings[uid] = {"start": iso, "status": "accepted", "phone": phone}

    def next_uid(self, prefix):
        self._n += 1
        return f"{prefix}_{self._n}"


CS = CalState()


def fake_cal_request(method, url, acct, version, *, json_body=None, params=None, attempts=2):
    if url.endswith("/slots/reservations") and method == "POST":
        iso = json_body["slotStart"]
        if iso in CS.fail_reserves:
            CS.events.append(("reserve_fail", iso))
            return R(409, {"status": "error", "error": {"message": "slot taken"}})
        uid = CS.next_uid("res")
        CS.reservations[uid] = iso
        CS.events.append(("reserve", uid))
        return R(201, {"status": "success", "data": {"reservationUid": uid}})

    if "/slots/reservations/" in url and method == "GET":
        uid = url.rsplit("/", 1)[1]
        if uid in CS.reservations:
            return R(200, {"status": "success", "data": {"slotStart": CS.reservations[uid]}})
        return R(404, {"status": "error"})

    if "/slots/reservations/" in url and method == "DELETE":
        uid = url.rsplit("/", 1)[1]
        CS.reservations.pop(uid, None)
        CS.events.append(("release", uid))
        return R(200, {"status": "success"})

    if url.endswith("/bookings") and method == "GET":
        items = []
        for uid, b in CS.bookings.items():
            if uid in CS.cancelled:
                continue
            items.append({
                "uid": uid, "start": b["start"], "status": b["status"],
                "attendees": [{"phoneNumber": b["phone"]}],
            })
        return R(200, {"status": "success", "data": {"bookings": items}})

    if url.endswith("/bookings") and method == "POST":
        if CS.fail_create:
            code = CS.fail_create
            CS.fail_create = None
            CS.events.append(("create_fail", code))
            return R(code, {"status": "error"})
        uid = CS.next_uid("bk")
        CS.bookings[uid] = {
            "start": json_body["start"], "status": "accepted",
            "phone": json_body["attendee"]["phoneNumber"],
        }
        CS.events.append(("create", uid))
        return R(201, {"status": "success", "data": {"uid": uid}})

    if "/bookings/" in url and url.endswith("/cancel"):
        uid = url.split("/bookings/")[1].split("/")[0]
        CS.cancelled.add(uid)
        CS.events.append(("cancel", uid))
        return R(200, {"status": "success", "data": {"uid": uid}})

    if "/bookings/" in url and method == "GET":
        uid = url.rsplit("/", 1)[1]
        b = CS.bookings.get(uid)
        if b and uid not in CS.cancelled:
            return R(200, {"status": "success", "data": {"uid": uid, "status": b["status"], "start": b["start"]}})
        return R(404, {"status": "error"})

    return R(404, {"status": "error", "error": {"message": f"unrouted {method} {url}"}})


def fake_fetch_slots(url, headers, params, attempts=2, timeout=10):
    return R(200, {"status": "success", "data": {DAY: [{"start": iso} for iso in ISOS]}})


main._cal_request = fake_cal_request
main.fetch_cal_slots = fake_fetch_slots


def signed_post(path, payload, key=KEY, good_sig=True):
    raw = json.dumps(payload).encode()
    ts = str(int(time.time() * 1000))
    if good_sig:
        digest = hmac.new(key, raw + ts.encode(), hashlib.sha256).hexdigest()
    else:
        digest = "deadbeef"
    return client.post(
        path, content=raw,
        headers={"Content-Type": "application/json", "X-Retell-Signature": f"v={ts},d={digest}"},
    )


def base_args(**over):
    a = {
        "account_id": "test_acct",
        "timezone": "America/Chicago",
        "slot_target_date": DAY,
    }
    a.update(over)
    return a


def base_book(**over):
    a = {
        "account_id": "test_acct",
        "timezone": "America/Chicago",
        "time": LOCAL[0],
        "name": "Marcus Bell",
        "attendeePhoneNumber": "+15551230000",
        "title": "Live call",
        "notes": "test",
        "slot_reservation_uids": "",
        "booking_intent": "",
    }
    a.update(over)
    return a


def events_of(kind):
    return [e for e in CS.events if e[0] == kind]


# ------------------------------------------------------------------- tests
def t01_legacy_shape_unchanged():
    print("T01 legacy shape (no new args) — rollback safety")
    CS.reset()
    r = signed_post("/check_availability", base_args())
    b = r.json()
    check("legacy 200 ok", r.status_code == 200 and b.get("ok") is True)
    check("legacy: 4 slots", len(b.get("slots", [])) == 4)
    check("legacy: no reservation_uid", all("reservation_uid" not in s for s in b["slots"]))
    check("legacy: no reservations created", not events_of("reserve"))


def t02_freeze_default_pair():
    print("T02 freeze default: earliest 2")
    CS.reset()
    r = signed_post("/check_availability", base_args(current_reservation_uids="", preferred_time=""))
    b = r.json()
    check("ok true", b.get("ok") is True)
    check("exactly 2 slots", len(b.get("slots", [])) == 2)
    check("earliest two", [s["time"] for s in b["slots"]] == LOCAL[:2])
    uids = b.get("slot_reservation_uids", "")
    check("uids joined", uids == ",".join(s["reservation_uid"] for s in b["slots"]) and len(uids) > 10)
    check("reissued false", b.get("reissued") is False)
    check("preferred_unavailable false", b.get("preferred_unavailable") is False)


def t03_freeze_preferred_match():
    print("T03 freeze preferred match: preferred + next later")
    CS.reset()
    r = signed_post("/check_availability", base_args(current_reservation_uids="", preferred_time=LOCAL[2]))
    b = r.json()
    check("preferred first", b["slots"][0]["time"] == LOCAL[2])
    check("option 2 is next later", b["slots"][1]["time"] == LOCAL[3])
    check("preferred_unavailable false", b.get("preferred_unavailable") is False)


def t04_freeze_preferred_miss():
    print("T04 freeze preferred miss: two nearest AFTER preferred")
    CS.reset()
    r = signed_post("/check_availability", base_args(current_reservation_uids="", preferred_time=f"{DAY}T11:30:00"))
    b = r.json()
    check("preferred_unavailable true", b.get("preferred_unavailable") is True)
    check("slots after preferred", [s["time"] for s in b["slots"]] == [LOCAL[2], LOCAL[3]])


def t05_release_on_reissue():
    print("T05 reissue releases echoed holds")
    CS.reset()
    r = signed_post("/check_availability", base_args(current_reservation_uids="old1,old2"))
    b = r.json()
    released = [e[1] for e in events_of("release")]
    check("old holds released", set(released) >= {"old1", "old2"})
    check("reissued true", b.get("reissued") is True)
    check("2 fresh holds", len(events_of("reserve")) == 2)


def t06_all_taken():
    print("T06 every reserve fails → empty holds, fail-closed uids")
    CS.reset()
    CS.fail_reserves = set(ISOS)
    r = signed_post("/check_availability", base_args(current_reservation_uids=""))
    b = r.json()
    check("ok true, slots empty", b.get("ok") is True and b.get("slots") == [])
    check("taken recorded", len(b.get("taken", [])) == 4)
    check("slot_reservation_uids empty string", b.get("slot_reservation_uids") == "")
    check("message present", "taken" in b.get("message", ""))


def t07_book_happy_path():
    print("T07 book happy path: hold → book → verify → release both")
    CS.reset()
    fr = signed_post("/check_availability", base_args(current_reservation_uids="", preferred_time=""))
    holds = fr.json()["slot_reservation_uids"]
    CS.events.clear()
    r = signed_post("/book-livecall", base_book(
        time=LOCAL[0], slot_reservation_uids=holds))
    b = r.json()
    check("status booked", b.get("status") == "booked")
    check("booking_uid present", bool(b.get("booking_uid")))
    check("booking_verified true", b.get("booking_verified") is True)
    check("recovered false", b.get("recovered") is False)
    created = events_of("create")
    check("one booking created", len(created) == 1)
    check("booked at hold iso", CS.bookings[created[0][1]]["start"] == ISOS[0])
    released = [e[1] for e in events_of("release")]
    check("all holds released", set(holds.split(",")) <= set(released))


def t08_recovered_idempotent():
    print("T08 recovery: existing booking same day → return its UID")
    CS.reset()
    CS.add_booking("bk_exist", ISOS[1], "+15551230000")
    r = signed_post("/book-livecall", base_book(time=LOCAL[0]))
    b = r.json()
    check("status booked", b.get("status") == "booked")
    check("returns existing uid", b.get("booking_uid") == "bk_exist")
    check("recovered true", b.get("recovered") is True)
    check("no new booking", not events_of("create"))


def t09_taken_no_silent_fail():
    print("T09 slot genuinely taken → book_failed, NO booking_uid keys")
    CS.reset()
    r = signed_post("/book-livecall", base_book(
        time=f"{DAY}T23:00:00", slot_reservation_uids=""))
    b = r.json()
    check("ok false", b.get("ok") is False)
    check("status book_failed", b.get("status") == "book_failed")
    check("reason slot_taken", b.get("reason") == "slot_taken")
    check("fail-closed: no booking_uid", "booking_uid" not in b)
    check("fail-closed: no booking_verified", "booking_verified" not in b)


def t10_create_error_fail_closed():
    print("T10 Cal create error → honest failure, no booking_uid")
    CS.reset()
    CS.fail_create = 500
    r = signed_post("/book-livecall", base_book())
    b = r.json()
    check("status book_failed", b.get("status") == "book_failed")
    check("fail-closed: no booking_uid", "booking_uid" not in b)


def t11_reschedule_options():
    print("T11 reschedule ask: release old holds, freeze fresh pair, NO booking")
    CS.reset()
    r = signed_post("/book-livecall", base_book(
        time=LOCAL[0], preferred_time=LOCAL[2], booking_intent="reschedule",
        slot_reservation_uids="resA,resB"))
    b = r.json()
    check("status reschedule_options", b.get("status") == "reschedule_options")
    check("2 fresh slots", len(b.get("slots", [])) == 2)
    check("old holds released", {"resA", "resB"} <= {e[1] for e in events_of("release")})
    check("no booking created", not events_of("create"))
    check("reissued true", b.get("reissued") is True)


def t12_reschedule_commit_order():
    print("T12 reschedule commit: book new FIRST, cancel old SECOND")
    CS.reset()
    CS.add_booking("bk_old", ISOS[0], "+15551230000")
    r = signed_post("/book-livecall", base_book(
        time=LOCAL[2], preferred_time=LOCAL[2], booking_intent="reschedule",
        slot_reservation_uids="resC"))
    b = r.json()
    check("status booked", b.get("status") == "booked")
    check("new uid differs", b.get("booking_uid") not in (None, "bk_old"))
    check("rescheduled_from bk_old", b.get("rescheduled_from") == "bk_old")
    kinds = [e[0] for e in CS.events]
    check("create before cancel", "create" in kinds and "cancel" in kinds
          and kinds.index("create") < kinds.index("cancel"))


def t13_cancel_releases():
    print("T13 cancel: release all, never book")
    CS.reset()
    r = signed_post("/book-livecall", base_book(booking_intent="cancel", slot_reservation_uids="resX,resY"))
    b = r.json()
    check("status released", b.get("status") == "released")
    check("holds released", {"resX", "resY"} <= {e[1] for e in events_of("release")})
    check("never books", not events_of("create"))
    check("no booking keys", "booking_uid" not in b and "booking_verified" not in b)


def t14_cancel_with_existing_truth():
    print("T14 cancel but booking exists → truth (booked), no auto-cancel")
    CS.reset()
    CS.add_booking("bk_real", ISOS[0], "+15551230000")
    r = signed_post("/book-livecall", base_book(booking_intent="cancel"))
    b = r.json()
    check("status booked (truth)", b.get("status") == "booked")
    check("booking_uid bk_real", b.get("booking_uid") == "bk_real")
    check("old booking NOT cancelled", "bk_real" not in CS.cancelled)


def t15_signature_rejection():
    print("T15 bad signature → 401")
    CS.reset()
    r = signed_post("/book-livecall", base_book(), good_sig=False)
    check("401", r.status_code == 401)
    r = signed_post("/check_availability", base_args(), good_sig=False)
    check("401 slots too", r.status_code == 401)


def t16_missing_details():
    print("T16 default path validation: missing name/phone")
    CS.reset()
    r = signed_post("/book-livecall", base_book(name=""))
    b = r.json()
    check("error missing_details", b.get("error") == "missing_details")
    check("no booking", not events_of("create"))


for fn in [
    t01_legacy_shape_unchanged, t02_freeze_default_pair, t03_freeze_preferred_match,
    t04_freeze_preferred_miss, t05_release_on_reissue, t06_all_taken,
    t07_book_happy_path, t08_recovered_idempotent, t09_taken_no_silent_fail,
    t10_create_error_fail_closed, t11_reschedule_options, t12_reschedule_commit_order,
    t13_cancel_releases, t14_cancel_with_existing_truth, t15_signature_rejection,
    t16_missing_details,
]:
    fn()

print(f"\n=== {len(PASSED)} passed, {len(FAILED)} failed ===")
if FAILED:
    print("FAILED:", ", ".join(FAILED))
    sys.exit(1)
