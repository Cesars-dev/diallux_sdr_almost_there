#!/usr/bin/env python3
"""Lead validator service — agent agnostic, key agnostic.

Auth/ratelimit skeleton mirrors time_endpoint (proven pattern):
- RETELL_API_KEYS (JSON list) + legacy RETELL_API_KEY env badge
- HMAC-SHA256 Retell signature: v=<ts_ms>,d=<hex> over raw_body+ts
- Per-IP rate limiter

Additive only: shares nothing with slots/time routes.
"""

import hashlib
import hmac
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from validate import validate_lead
from verify import parse_uid_payload, record_booking_uid, record_reach_details, set_callback_number, verify_lead_data

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("validator_service")


def _retell_badge_keys():
    keys = []
    raw = os.environ.get("RETELL_API_KEYS", "")
    if raw:
        try:
            for k in json.loads(raw):
                if k:
                    keys.append(k)
        except json.JSONDecodeError:
            logger.error("RETELL_API_KEYS is not valid JSON")
    legacy = os.environ.get("RETELL_API_KEY", "")
    if legacy and legacy not in keys:
        keys.append(legacy)
    return keys


RETELL_API_KEYS = _retell_badge_keys()

if not RETELL_API_KEYS:
    raise SystemExit(
        "validator_service: refusing to start — missing RETELL_API_KEYS/RETELL_API_KEY"
    )

RATE_LIMIT_PER_MIN = int(os.environ.get("VALIDATOR_RATE_LIMIT_PER_MIN", "120"))

app = FastAPI(title="Lead Validator - Agent Agnostic")


class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 120):
        self.max_requests = max_requests_per_minute
        self.lock = Lock()
        self.requests = defaultdict(deque)

    def is_rate_limited(self, client_ip: str) -> bool:
        with self.lock:
            now = time.time()
            window_start = now - 60
            requests = self.requests[client_ip]
            while requests and requests[0] < window_start:
                requests.popleft()
            if len(requests) >= self.max_requests:
                return True
            requests.append(now)
            return False


rate_limiter = RateLimiter(RATE_LIMIT_PER_MIN)


def verify_retell_signature(raw_body: bytes, signature: str | None) -> bool:
    """Verify Retell webhook signature (HMAC-SHA256), same as time_endpoint."""
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


@app.post("/validate_lead")
async def validate_lead_endpoint(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    signature = request.headers.get("X-Retell-Signature")
    raw_body = await request.body()

    if rate_limiter.is_rate_limited(client_ip):
        return JSONResponse(status_code=429,
                            content={"ok": False, "error": "rate_limited"})

    if not verify_retell_signature(raw_body, signature):
        logger.warning("Rejected request from %s: bad/missing signature", client_ip)
        return JSONResponse(status_code=401,
                            content={"ok": False, "error": "invalid_signature"})

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(status_code=400,
                            content={"ok": False, "error": "invalid_json"})

    # Retell custom tools send args nested under "args" when args_at_root=false
    if isinstance(payload, dict) and isinstance(payload.get("args"), dict):
        payload = payload["args"]

    result = validate_lead(payload)
    logger.info("verdict=%s problems=%s", result["slot_verified"], result["problems"])
    return JSONResponse(content=result)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "validator"}


def _tg_notify(text: str):
    if TG_TOKEN and TG_CHAT:
        try:
            import urllib.request as _u
            req = _u.Request(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                data=json.dumps({"chat_id": TG_CHAT, "text": text}).encode(),
                headers={"Content-Type": "application/json"})
            _u.urlopen(req, timeout=5)
        except Exception as e:
            logger.warning("telegram failed: %s", e)


@app.post("/verify-lead-data")
async def verify_lead_data_endpoint(request: Request):
    """V7.6 pre-booking gate. Deterministic verdict + dv injections."""
    client_ip = request.client.host if request.client else "unknown"
    signature = request.headers.get("X-Retell-Signature")
    raw_body = await request.body()
    if rate_limiter.is_rate_limited(client_ip):
        return JSONResponse(status_code=429,
                            content={"ok": False, "error": "rate_limited"})
    if not verify_retell_signature(raw_body, signature):
        logger.warning("verify-lead-data rejected from %s: bad/missing signature",
                       client_ip)
        return JSONResponse(status_code=401,
                            content={"ok": False, "error": "invalid_signature"})
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(status_code=400,
                            content={"ok": False, "error": "invalid_json"})
    if isinstance(payload, dict) and isinstance(payload.get("args"), dict):
        payload = payload["args"]

    result = verify_lead_data(payload)
    logger.info("verify-lead-data status=%s problems=%s",
                result.get("status"), result.get("problems"))
    if result.get("status") == "error":
        _tg_notify(
            "[validator] verify_lead_data ERROR\n"
            f"problems={result.get('problems')}\ninputs={payload}")
    return JSONResponse(content=result)


@app.post("/set-callback-number")
async def set_callback_number_endpoint(request: Request):
    """Deterministic writer of callback_number. E.164 on ok; no dv write on wrong/error."""
    client_ip = request.client.host if request.client else "unknown"
    signature = request.headers.get("X-Retell-Signature")
    raw_body = await request.body()
    if rate_limiter.is_rate_limited(client_ip):
        return JSONResponse(status_code=429,
                            content={"ok": False, "error": "rate_limited"})
    if not verify_retell_signature(raw_body, signature):
        logger.warning("set-callback-number rejected from %s: bad/missing signature",
                       client_ip)
        return JSONResponse(status_code=401,
                            content={"ok": False, "error": "invalid_signature"})
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(status_code=400,
                            content={"ok": False, "error": "invalid_json"})
    if isinstance(payload, dict) and isinstance(payload.get("args"), dict):
        payload = payload["args"]

    result = set_callback_number(payload)
    logger.info("set-callback-number status=%s", result.get("status"))
    if result.get("status") == "error":
        _tg_notify(
            "[validator] set_callback_number ERROR\n"
            f"problems={result.get('problems')}\ninputs={payload}")
    return JSONResponse(content=result)


@app.post("/record-reach-details")
async def record_reach_details_endpoint(request: Request):
    """Deterministic mirror-writer of is_calling_best_number + phone_confirmed. No dv write on invalid."""
    client_ip = request.client.host if request.client else "unknown"
    signature = request.headers.get("X-Retell-Signature")
    raw_body = await request.body()
    if rate_limiter.is_rate_limited(client_ip):
        return JSONResponse(status_code=429,
                            content={"ok": False, "error": "rate_limited"})
    if not verify_retell_signature(raw_body, signature):
        logger.warning("record-reach-details rejected from %s: bad/missing signature",
                       client_ip)
        return JSONResponse(status_code=401,
                            content={"ok": False, "error": "invalid_signature"})
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(status_code=400,
                            content={"ok": False, "error": "invalid_json"})
    if isinstance(payload, dict) and isinstance(payload.get("args"), dict):
        payload = payload["args"]

    result = record_reach_details(payload)
    logger.info("record-reach-details status=%s", result.get("status"))
    if result.get("status") == "error":
        _tg_notify(
            "[validator] record_reach_details ERROR\n"
            f"result={result}\ninputs={payload}")
    return JSONResponse(content=result)


@app.post("/record-booking-uid")
async def record_booking_uid_endpoint(request: Request):
    """V7.6 deterministic UID recorder - 22-char contract, invalid never writes."""
    client_ip = request.client.host if request.client else "unknown"
    signature = request.headers.get("X-Retell-Signature")
    raw_body = await request.body()
    if rate_limiter.is_rate_limited(client_ip):
        return JSONResponse(status_code=429,
                            content={"ok": False, "error": "rate_limited"})
    if not verify_retell_signature(raw_body, signature):
        logger.warning("record-booking-uid rejected from %s: bad/missing signature",
                       client_ip)
        return JSONResponse(status_code=401,
                            content={"ok": False, "error": "invalid_signature"})
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(status_code=400,
                            content={"ok": False, "error": "invalid_json"})
    if isinstance(payload, dict) and isinstance(payload.get("args"), dict):
        payload = payload["args"]

    uid, err = parse_uid_payload(payload)
    if err:
        result = record_booking_uid(uid, err)
    else:
        # Machine truth: the uid MUST exist on Cal AND be an accepted booking.
        # Kills hallucinated uids and cancelled-booking ghosts.
        cal_key = os.environ.get("CAL_COM_API_KEY", "")
        try:
            creq = urllib.request.Request(
                f"https://api.cal.com/v2/bookings/{uid}",
                headers={"Authorization": cal_key,
                         "cal-api-version": "2026-05-01",
                         "User-Agent": "diallux-test"})
            with urllib.request.urlopen(creq, timeout=8) as resp:
                bstatus = json.loads(resp.read()).get("data", {}).get("status")
            if bstatus == "accepted":
                result = record_booking_uid(uid, None)
            else:
                logger.warning("record-booking-uid: cal status=%s for %s",
                               bstatus, uid[:6])
                result = {"status": "error", "error": f"uid_not_accepted:{bstatus}"}
        except urllib.error.HTTPError as e:
            logger.warning("record-booking-uid: cal rejected %s (%s)", uid[:6], e.code)
            result = {"status": "error",
                      "error": "uid_not_found" if e.code in (404, 410) else "cal_unavailable"}
        except Exception as e:
            logger.warning("record-booking-uid: cal unreachable: %s", e)
            result = {"status": "error", "error": "cal_unavailable"}
    logger.info("record-booking-uid status=%s uid=%s", result.get("status"),
                (uid or "")[:6])
    return JSONResponse(content=result)


TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")


@app.post("/call_outcome")
async def call_outcome(request: Request):
    """Fire-and-forget telemetry. Telegram on booking=false with reason."""
    client_ip = request.client.host if request.client else "unknown"
    signature = request.headers.get("X-Retell-Signature")
    raw_body = await request.body()
    if rate_limiter.is_rate_limited(client_ip):
        return JSONResponse(status_code=429, content={"ok": False})
    if not verify_retell_signature(raw_body, signature):
        return JSONResponse(status_code=401, content={"ok": False})
    try:
        p = json.loads(raw_body.decode("utf-8"))
        if isinstance(p.get("args"), dict):
            p = p["args"]
    except Exception:
        return JSONResponse(status_code=400, content={"ok": False})
    booked = bool(p.get("booked"))
    if not booked:
        text = (
            f"NO-BOOK | agent={p.get('agent_id','?')[:20]}\n"
            f"state={p.get('last_state','?')} reason={p.get('reason','unspecified')}\n"
            f"name={p.get('first_name','')} company={p.get('company_name','')}"
        )
        if TG_TOKEN and TG_CHAT:
            try:
                import urllib.request as _u
                req = _u.Request(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                    data=json.dumps({"chat_id": TG_CHAT, "text": text}).encode(),
                    headers={"Content-Type": "application/json"})
                _u.urlopen(req, timeout=5)
            except Exception as e:
                logger.warning("telegram failed: %s", e)
    logger.info("outcome booked=%s reason=%s", booked, p.get("reason"))
    return JSONResponse(content={"ok": True})
