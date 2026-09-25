import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime
from threading import Lock
from typing import List, Optional
from zoneinfo import ZoneInfo

from dateutil import parser as dateutil_parser
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("time_service")

RETELL_API_KEY = os.environ.get("RETELL_API_KEY", "")

def _retell_badge_keys() -> list[str]:
    """Accepted Retell webhook-badge keys: RETELL_API_KEYS (JSON list) + legacy RETELL_API_KEY."""
    keys: list[str] = []
    raw = os.environ.get("RETELL_API_KEYS", "")
    if raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                keys = [str(k).strip() for k in parsed if str(k).strip()]
        except json.JSONDecodeError:
            keys = [k.strip() for k in raw.split(",") if k.strip()]
    if RETELL_API_KEY and RETELL_API_KEY not in keys:
        keys.append(RETELL_API_KEY)
    return keys


RETELL_API_KEYS = _retell_badge_keys()
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "8002"))
DEFAULT_TIMEZONE = os.environ.get("DEFAULT_TIMEZONE", "Europe/London")
DEFAULT_OUTPUT_FORMAT = os.environ.get(
    "DEFAULT_OUTPUT_FORMAT", "today,now,timestamp,iso_format"
)
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))

if not RETELL_API_KEYS:
    raise SystemExit("time_service: refusing to start — missing RETELL_API_KEYS/RETELL_API_KEY")

app = FastAPI(title="Time Service - Agent Agnostic")


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
    """Verify Retell webhook signature (HMAC-SHA256), same as cal_slots_endpoint."""
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


def parse_retell_time(
    time_str: str, timezone_str: str = "Europe/London"
) -> Optional[datetime]:
    """Parse Retell time format: 'Sunday, August 2, 2026 at 07:00 AM BST'."""
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        logger.warning("Unknown timezone %r", timezone_str)
        return None
    try:
        dt = dateutil_parser.parse(time_str, fuzzy=True)
    except Exception as e:
        logger.warning(f"Failed to parse time '{time_str}': {e}")
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    else:
        dt = dt.astimezone(tz)
    return dt


def generate_time_outputs(dt: datetime, formats: List[str]) -> dict:
    """Generate multiple time format outputs."""
    outputs = {}
    if "today" in formats:
        outputs["today"] = dt.strftime("%Y-%m-%d")
    if "now" in formats:
        outputs["now"] = dt.strftime("%Y-%m-%dT%H:%M:%S")
    if "timestamp" in formats:
        outputs["timestamp"] = int(dt.timestamp())
    if "iso_format" in formats:
        outputs["iso_format"] = dt.isoformat()
    return outputs


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"ok": True, "service": "time_service", "version": "1.0.0"}


@app.get("/ready")
async def ready():
    """Readiness check endpoint."""
    problems = []
    if not RETELL_API_KEYS:
        problems.append("RETELL_API_KEYS/RETELL_API_KEY")
    if problems:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "service": "time_service", "problems": problems},
        )
    return {"ok": True, "service": "time_service", "checks": "pass"}


@app.get("/metrics")
async def metrics():
    """Service metrics endpoint."""
    return {"ok": True, "service": "time_service", "rate_limiter_active": True}


@app.get("/today")
async def today(tz: str = DEFAULT_TIMEZONE):
    """
    Legacy compatibility endpoint - returns today's date in YYYY-MM-DD format.
    Mirrors cal_slots_endpoint /today (real time, IANA timezone).
    """
    try:
        now = datetime.now(ZoneInfo(tz))
    except Exception:
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "error": "invalid_timezone",
                "message": f"Unknown timezone {tz!r}. Use an IANA name like Europe/London.",
            },
        )
    return {
        "ok": True,
        "today": now.strftime("%Y-%m-%d"),
        "timezone": tz,
        "tz_abbrev": now.strftime("%Z"),
    }


@app.post("/parse-time")
async def parse_time(request: Request):
    """
    Main endpoint - parse Retell dynamic time values and return standardized formats.

    Accepts JSON input with Retell's time format and returns multiple time representations.
    """
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    client_ip = (
        request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
        .split(",")[0]
        .strip()
    )

    if rate_limiter.is_rate_limited(client_ip):
        return JSONResponse(
            status_code=429,
            content={
                "ok": False,
                "error": "rate_limited",
                "message": "Too many requests from this IP.",
            },
        )

    raw_body = await request.body()
    if not verify_retell_signature(raw_body, request.headers.get("X-Retell-Signature")):
        logger.warning(f"{request_id}: Invalid or missing signature from {client_ip}")
        return JSONResponse(
            status_code=401,
            content={
                "ok": False,
                "error": "unauthorized",
                "message": "Invalid or missing signature.",
            },
        )

    try:
        payload = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "invalid_json",
                "message": "Request body must be valid JSON.",
            },
        )

    source_timezone = payload.get("source_timezone", DEFAULT_TIMEZONE)
    current_time = payload.get("current_time", "")
    requested_formats = payload.get("requested_format", DEFAULT_OUTPUT_FORMAT.split(","))

    if isinstance(requested_formats, str):
        requested_formats = [fmt.strip() for fmt in requested_formats.split(",")]

    if not current_time:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "missing_time",
                "message": "Missing 'current_time' parameter. Provide Retell's dynamic time value.",
            },
        )

    parsed_dt = parse_retell_time(current_time, source_timezone)
    if not parsed_dt:
        try:
            ZoneInfo(source_timezone)
        except Exception:
            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "error": "invalid_timezone",
                    "message": f"Unknown timezone {source_timezone!r}. Use an IANA name like Europe/London.",
                },
            )
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "parse_failed",
                "message": f"Failed to parse time string: '{current_time}'. Check the format.",
            },
        )

    time_outputs = generate_time_outputs(parsed_dt, requested_formats)

    logger.info(f"{request_id}: Successfully parsed time '{current_time}' → {list(time_outputs.keys())}")

    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "timezone": source_timezone,
            "tz_abbrev": parsed_dt.strftime("%Z"),
            "parsed_time": current_time,
            **time_outputs,
        },
    )


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting time_service on port {SERVICE_PORT}")
    uvicorn.run(app, host="127.0.0.1", port=SERVICE_PORT)
