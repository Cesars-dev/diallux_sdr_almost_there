# ENDPOINTS.md — Complete API contract for the Dialux SDR pipeline

> **Purpose:** everything an autonomous agent needs to understand and operate this system —
> every endpoint, every argument, every response shape, every side effect, and the state machine
> that ties them together. No secrets here: auth uses an HMAC signature with a key that lives in
> the host environment (`RETELL_API_KEY`), never in this repo.

---

## 0. Base & auth

- **Base URL:** `https://slots.diallux-ai.site` (Caddy → localhost services on the VPS)
- **All POST endpoints require** header:

  ```
  X-Retell-Signature: v=<epoch_ms>,d=<hex>
  d = HMAC_SHA256( raw_request_body + str(epoch_ms), RETELL_API_KEY ).hexdigest()
  ```

  The timestamp must be within **±5 minutes** of server time. Retell's custom-function calls are
  signed automatically with the workspace API key; a local agent signs the same way.
- **Body envelope:** `{"args": { ...parameters }}` (Retell wraps args; the services accept both
  wrapped and root-level).
- **Rate limit:** per-IP, 120 requests/min.
- **Cal.com account in play:** `account_id: "diallux_live"` → event **3801235** ("Dialux Live
  Demo", 45 min, service timezone `America/Mexico_City`).

---

## 1. `GET /today` — real clock

```
GET https://slots.diallux-ai.site/today?tz=America/Mexico_City
```

**Response 200:**
```json
{"ok": true, "today": "2026-09-03", "timezone": "America/Mexico_City", "tz_abbrev": "CST"}
```
**Why it exists:** the agent must never guess dates. Every "tomorrow / next Monday" is computed
from this response. Invalid tz → 200 `{"ok":false,"error":"invalid_timezone"}`.
**No signature required.** Writes dynamic variable `today_date`.

---

## 2. `POST /check_availability` — slot-lock availability (freezes 2 slots)

```
POST https://slots.diallux-ai.site/check_availability
{"args": {
  "slot_target_date": "2026-09-04",        // YYYY-MM-DD the caller wants (mandatory)
  "timezone": "America/Chicago",           // IANA — response times come back in THIS zone
  "account_id": "diallux_live",
  "current_reservation_uids": "",          // echo of {{slot_reservation_uids}}; "" on first call
  "preferred_time": ""                     // "" or local "YYYY-MM-DDTHH:MM" the caller named
}}
```

**Behavior:** queries live Cal.com availability → deterministically picks the 2 best slots
(preferred time first when given, else the two earliest; if the preferred time is unavailable,
`preferred_unavailable: true` and the two nearest options after it are taken) → **freezes both**
via Cal.com slot reservations (~15 min TTL) → returns **only the frozen slots**. A repeat call
releases the echoed holds and freezes a fresh pair (`reissued: true`). The prospect must be
offered ONLY times present in `slots[]`.

**Response 200 (success):**
```json
{"ok": true,
 "slots": [
   {"day": "2026-09-04", "time": "2026-09-04T13:00:00", "iso": "2026-09-04T18:00:00.000Z",
    "reservation_uid": "2c4b75b4-546f-46fc-bb36-b3a600eb4c65"},
   {"day": "2026-09-04", "time": "2026-09-04T14:30:00", "iso": "2026-09-04T19:30:00.000Z",
    "reservation_uid": "a1f76ae0-6009-4887-90d4-41794a7e949d"}],
 "taken": [],
 "reissued": false,
 "preferred_unavailable": false,
 "slot_reservation_uids": "2c4b75b4-…,a1f76ae0-…"}
```

**Response 200 (all candidates just taken):**
```json
{"ok": true, "slots": [], "taken": ["2026-09-04T13:00:00", "…"],
 "reissued": false, "preferred_unavailable": false, "slot_reservation_uids": "",
 "message": "Every candidate time was just taken. Ask the caller for a different day."}
```

**Other responses:** `{"ok":false,"error":"no_availability_in_window"}` (nothing free in the
window) · `{"ok":false,"error":"no_start_time"|"invalid_slot_target_date", "message": …}` ·
`{"ok":false,"error":"upstream_unavailable","message":"Calendar is temporarily unavailable…"}` ·
401 `{"ok":false,"error":"unauthorized"}` (bad/missing signature) · 429 `rate_limited`.

**Dynamic variables written:** `slot_reservation_uids` ← comma-joined uids (empty string on
failure — fail-closed).

**Side effects:** holds 1–2 Cal.com reservations (auto-expire ~15 min). Every new call with
`current_reservation_uids` releases the previous holds first.

---

## 3. `POST /validator-function/validate_lead` — data gate #1 (ConfirmSlots exit)

```
POST https://slots.diallux-ai.site/validator-function/validate_lead
{"args": {
  "first_name": "Maria", "last_name": "Gonzales",
  "company_name": "Bright Smile Dental",
  "callback_number": "+13124001234",        // E.164, verbatim
  "prospect_timezone": "America/Chicago",
  "selected_time": "2026-09-04T14:30:00",   // verbatim slot the caller confirmed
  "missed_calls_per_week": 20,
  "close_rate_percent": 50,
  "avg_job_value": 650
}}
```

**Response 200 (all good):**
```json
{"ok": true, "data_complete": true, "slot_verified": true, "problems": [], "actions": [],
 "weekly_leak": "$6,500", "monthly_leak": "$28,000", "inputs": {…}}
```
**Response 200 (problems):** `slot_verified: false`, `problems: [ …human-readable fixes… ],
`actions: [{"say": "…"}, …]` — the agent must speak each `Say:` line, re-capture, call again.
Never transition to VerifyLead unless `slot_verified === true`.

**Dynamic variables written:** `slot_verified`, `weekly_leak`, `monthly_leak`.
**Side effects:** none (pure validation + leak math: missed × close% × value).

---

## 4. `POST /validator-function/verify-lead-data` — data gate #2 (VerifyLead state)

Same envelope as `validate_lead` (re-checks everything stored). **Response 200:**
```json
{"ok": true, "data_verified": true, "problems": [], "actions": [],
 "first_name": "Maria", "callback_number": "+13124001234", "prospect_timezone": "America/Chicago", …}
```
Gate: `transition_to_Booking` requires `data_verified: true`. Problems → same speak/re-capture
loop. DV written: `data_verified`.

---

## 5. `POST /validator-function/record-booking-uid` — booking persistence

```
POST https://slots.diallux-ai.site/validator-function/record-booking-uid
{"args": {"booking_uid": "qeTqHuZ1EDzH8bxEdhPQ6H"}}
```
Validates the UID is 22-char and **verifies against Cal.com (`status == "accepted"`)** before
recording. Responses: `{"ok": true, "booking_uid": "…"}` on success; `{"ok": false,
"error": "invalid_uid"|"uid_not_found", …}` → agent retries the exact same uid up to 3×.
DV written: `booking_uid` (fail-closed — nothing written unless Cal confirms).

---

## 6. `POST /validator-function/set-callback-number` — alternate-number write

```
{"args": {"callback_number": "+15123120001"}}
```
Called only when the caller says the dial-in number is NOT the best one. Writes
`callback_number` only if the value normalizes to valid E.164; otherwise returns an error shape
with no write (fail-closed). Companion: `record_reach_details` (same service) sets the
py-owned `phone_confirmed` / `is_calling_best_number` booleans — the LLM cannot fake them.

---

## 7. `POST /book-livecall` — the booking endpoint (Booking state)

```
POST https://slots.diallux-ai.site/book-livecall
{"args": {
  "account_id": "diallux_live",
  "timezone": "America/Chicago",
  "time": "2026-09-04T14:30:00",           // {{selected_time}} verbatim — never recomputed
  "name": "Maria Gonzales",
  "email": "jaydiallux@gmail.com",         // fixed shared system attendee
  "attendeePhoneNumber": "+13124001234",
  "title": "Dialux Live call for Bright Smile Dental",
  "notes": "Industry: dental practice | Pain points: after-hours calls go to voicemail",
  "slot_reservation_uids": "2c4b75b4-…,a1f76ae0-…",   // {{slot_reservation_uids}} verbatim
  "booking_intent": "",                    // "" | "reschedule" | "cancel" (enum-latched upstream)
  "preferred_time": ""                     // "" | new time on a reschedule ask
}}
```

**Dispatch (server-side, deterministic):**

| `booking_intent` | Behavior | Response |
|---|---|---|
| `""` (default) | recovery pre-check (existing booking for this caller+day → return its UID) → match hold by time → `POST /v2/bookings` → verify `accepted` → release ALL holds | `{"ok":true,"status":"booked","booking_uid":"…","recovered":false,"booking_verified":true}` |
| `reschedule` (no confirmed new time yet) | release current holds → freeze 2 fresh options | `{"ok":true,"status":"reschedule_options","slots":[…],"slot_reservation_uids":"…","reissued":true}` |
| `reschedule` + `preferred_time == time` (caller picked) | book the new slot; **only after** the new booking is accepted, cancel the old one (if any) | `booked` + `rescheduled_from` |
| `cancel` | release all holds, never book (existing real booking → reported truthfully, no auto-cancel) | `{"ok":true,"status":"released"}` |

**Failure shapes (fail-closed — NO booking_uid keys):**
```json
{"ok": false, "status": "book_failed", "reason": "slot_taken",
 "message": "That time was just taken. Apologize, do NOT book anything…"}
{"ok": false, "status": "book_failed", "reason": "upstream|cal_4xx", "message": "…hiccup…"}
```
**Dynamic variables written:** `booking_uid`, `booking_verified` — only on `status:"booked"`.
**Side effects:** creates a real Cal.com booking (attendee email is the fixed shared
`jaydiallux@gmail.com`, attendee phone = caller), releases holds, may cancel a superseded booking.
**Idempotency:** a booking call for a caller who already has a booking that day returns the
EXISTING uid (`"recovered": true`) — double calls can never double-book.

---

## 8. The state machine (how the endpoints chain)

```
Intake ──► Discovery ──► Closer ──► Offer ──► contact_details ──► ConfirmSlots
                                                                    │  check_current_date
                                                                    │  query_livecall_slots (freeze 2)
                                                                    │  extract_confirm_details
                                                                    ▼
                                                     validate_lead (slot_verified gate)
                                                                    │
                                                                    ▼
                                                              VerifyLead
                                                                    │  verify-lead-data (data_verified gate)
                                                                    ▼
                                                                Booking ──► create_livecall_booking
                                                                    │         record_booking_uid
                                                                    ▼
                                                                Closing ──► end_call
```

Transitions are functions the model must call (`transition_to_<State>`) whose required parameters
are the gate booleans — which are **server-written only** (`slot_verified`, `data_verified`,
`phone_confirmed`). The LLM cannot fabricate progress; it can only pass data through the gates.

**Booking-state intent gate:** `extract_booking_intent` (enum `reschedule|cancel`) fires only on
post-confirmation deviation; its value flows `booking_intent` → `/book-livecall`. With empty
intent the booking endpoint can NEVER return slots — it books, recovers an existing booking, or
fails honestly.

## 9. Dynamic variables (the 41, grouped)

- **identity/contact:** first_name, last_name, company_name, industry, callback_number,
  prospect_timezone, phone_confirmed, is_calling_best_number
- **discovery:** pain_points, pain_frame, pain_urgency, call_volume, interest_topic,
  inbound_channel, interest_signal, pattern_matched
- **gates (server-written):** intake_completed, discovery_completed, closer_completed,
  offer_completed, contact_details_completed, slot_verified, data_verified, phone_confirmed
- **slots:** selected_time, requested_slot, slot_reservation_uids, today_date
- **economics:** missed_calls_weekly, close_rate_pct, avg_job_value, weekly_leak, monthly_leak
- **booking:** booking_uid, booking_verified, booking_failed, booking_intent
- **misc:** objection_type, interest_level, livecall_agreed, …

## 10. Reference client snippet

```python
import hashlib, hmac, json, time, requests

KEY = os.environ["RETELL_API_KEY"]          # host secret — never in code
def signed_post(path, args):
    raw = json.dumps({"args": args}).encode()
    ts = str(int(time.time() * 1000))
    sig = hmac.new(KEY.encode(), raw + ts.encode(), hashlib.sha256).hexdigest()
    return requests.post("https://slots.diallux-ai.site" + path, data=raw,
        headers={"Content-Type": "application/json",
                 "X-Retell-Signature": f"v={ts},d={sig}"}, timeout=20).json()

print(signed_post("/check_availability", {"slot_target_date": "2026-09-04",
    "timezone": "America/Chicago", "account_id": "diallux_live",
    "current_reservation_uids": "", "preferred_time": ""}))
```
