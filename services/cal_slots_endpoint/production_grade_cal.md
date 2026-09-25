# Production-Grade Plan — `cal_slots_endpoint` (Cal.com Slot Webhook)

> **Date:** 2026-08-02
> **Scope:** Promote `main.py` (FastAPI slot webhook) to production grade.
> **Source of truth for format rules:** `cal_slots_endpoint/FINDINGS.md`
> **Predecessor audit:** inline review of `main.py` (A/B/C findings, this session).
> **Status:** PLAN ONLY — no code executed yet. Each change is specced for mechanical implementation.

---

## 0. Immutable rules (violations = bugs)

### Rule R-1 — Never send `Z` suffix to Cal.com

Cal.com **rejects** the `Z` (Zulu/UTC) suffix in ISO 8601 timestamps. All UTC times sent to the Cal.com API must use the `+00:00` offset format. Python's `datetime.isoformat()` with `tzinfo=timezone.utc` outputs `+00:00` by default — this is correct. **Never** `.replace("+00:00", "Z")` or manually append `Z`. This applies to `start`, `end` query params and any booking payloads.

### Rule R-2 — Response `time` field is bare local, no `Z`, no ms

The `slots[].time` returned to the LLM is Europe/London local (`%Y-%m-%dT%H:%M:%S`), no `Z`, no milliseconds. This is the value the agent passes to `book_calendar` as the `time` parameter.

### Rule R-3 — `slot_target_date` is required

Omitting `slot_target_date` is an error (`no_start_time`), not an ASAP fallback. The LLM must always resolve a concrete `YYYY-MM-DD` before calling. For "as soon as possible", the LLM passes today's date.

---

## 1. Resolved decisions (DO NOT revisit)

### Approved for this plan (apply)

| Code | Change | One-liner |
|------|--------|-----------|
| **A1** | Remove `SKIP_SIGNATURE` bypass | Auth must fail-closed; no silent escape hatch in prod. |
| **A2** | Remove legacy plain-hex signature path | Retell only sends the versioned format; legacy path has no replay check. |
| **A3** | Strict date validation | Missing date → `no_start_time`; malformed → `invalid_slot_target_date`. |
| **A4** | Separate upstream errors from empty results | Cal.com failure ≠ "no slots". |
| **B2** | Split `/health` + `/ready` | Shallow liveness vs config-present readiness. |
| **B3** | Cal.com retry + backoff | 1 retry on 5xx/timeout before failing. |
| **C1** | Request ID + structured logging | End-to-end traceability. |
| **C2** | In-process metrics + `/metrics` | Observe error/latency/reject rates. |
| **C3** | Rate limiting (per-IP) | Defense-in-depth behind signature. |
| **C4** | Sync `.env.example` + startup config validation | Example matches code; fail-fast on missing required env. |
| **C5** | Standardize error contract | One table, one shape, applied everywhere. |

### Excluded (with rationale)

| Code | Excluded because |
|------|------------------|
| **A5** | No PII in request bodies (caller data isn't passed to this function). Redaction unnecessary. |
| **B1** | Removed — see §0 rule. Window anchoring (UTC vs London midnight) is a non-issue given 09:00 London earliest availability. |
| **B4** | Automated tests are a separate, dedicated effort (see §9). |

---

## 2. Error contract (single source of truth — drives A3, A4, C5)

Every response uses the same shape: `{ "ok": bool, ... }`. On failure add `error` (machine code) + `message` (LLM-readable instruction).

| Condition | HTTP | Body |
|-----------|------|------|
| Bad/missing `X-Retell-Signature` | **401** | `{"ok":false,"error":"unauthorized"}` |
| Missing `slot_target_date` | **400** † | `{"ok":false,"error":"no_start_time","message":"slot_target_date is required. Ask the caller which day they want, then pass the date as YYYY-MM-DD."}` |
| Malformed `slot_target_date` | **400** † | `{"ok":false,"error":"invalid_slot_target_date","message":"slot_target_date must be YYYY-MM-DD (got <value>). Re-extract the date and retry."}` |
| Cal.com 5xx/timeout (after retry) | **200** | `{"ok":false,"error":"upstream_unavailable","message":"Calendar is temporarily unavailable. Tell the caller you'll check and try again shortly."}` |
| Cal.com 4xx / unexpected shape | **200** | `{"ok":false,"error":"upstream_unavailable","message":"..."}` (same as above) |
| Valid query, no slots in window | **200** | `{"ok":true,"slots":[],"message":"no_availability_in_window"}` |
| Valid query, slots found | **200** | `{"ok":true,"slots":[{"day","time","iso"},...]}` |
| Rate limited | **429** | `{"ok":false,"error":"rate_limited"}` |

> **† Retell 4xx verification (mandatory before sign-off).** It is not guaranteed that Retell surfaces a **4xx body** to the LLM — some versions treat non-2xx as a hard tool failure and the model never sees `no_start_time`. **Action:** after implementing, send one deliberate missing-date call *from the Retell chat agent* and confirm the LLM reads the `message` and asks for a date. If the body is swallowed, downgrade the two 400 rows to **HTTP 200** with identical bodies (guaranteed LLM-visible). Keep 401 as the only 4xx in that fallback. Default implementation = 400 per spec; flip only if the test proves it necessary.

---

## 3. Zero new dependencies

All changes are implementable with the **current** `requirements.txt` + stdlib:

- `pydantic` ships transitively with `fastapi` (for response models, optional).
- Request IDs, metrics, rate limiting, retry → stdlib (`uuid`, `time`, `collections`, `threading`).
- Config validation → manual `assert`/checks at startup (avoids `pydantic-settings`, which is a separate package).

No additions to `requirements.txt`.

---

## 4. Change specifications

All edits target **`main.py`** unless a different file is named. Line references are to the current file (pre-change).

---

### CH-1 — Remove `SKIP_SIGNATURE` bypass + legacy signature path (A1, A2)

**Why:** `SKIP_SIGNATURE` is a silent full-auth bypass that leaked into `.env` during testing. The legacy plain-hex path (no timestamp) is dead code (Retell only sends `v=...,d=...`) and weakens replay protection.

**Before** (`main.py:43`, `47-72`):
```python
SKIP_SIGNATURE = os.environ.get("SKIP_SIGNATURE", "false").lower() in ("1", "true", "yes")

def verify_retell_signature(raw_body, signature):
    if SKIP_SIGNATURE:
        return True
    ...
    match = re.fullmatch(r"v=(\d+),d=([0-9a-fA-F]+)", sig)
    if match:
        ... versioned: timestamp check + HMAC(raw_body+ts) ...
        return hmac.compare_digest(expected, digest)
    # ---- legacy plain-hex (NO timestamp check) ----
    expected = hmac.new(RETELL_API_KEY.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
```

**After:**
```python
def verify_retell_signature(raw_body: bytes, signature: str | None) -> bool:
    if not RETELL_API_KEY or not signature:
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
    expected = hmac.new(
        RETELL_API_KEY.encode("utf-8"),
        raw_body + timestamp.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, digest)
```

**Also:**
- Delete the `SKIP_SIGNATURE` line entirely.
- Remove `SKIP_SIGNATURE` from `FINDINGS.md:27` key list and `FINDINGS.md:237` row (mark resolved) — doc cleanup, no behaviour.

---

### CH-2 — Strict date validation (A3)

**Why:** missing/malformed dates silently fall back to `now`, masking LLM extraction bugs and making the function own "pick soonest" (Finding #7).

**Before** (`main.py:75-81`, `99-105`):
```python
def normalize_date(value, default_dt):
    if not value:
        return default_dt
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return default_dt            # <-- swallows bad input

...
target_dt = normalize_date(args.get("slot_target_date"), now)
start_dt  = datetime(target_dt.year, target_dt.month, target_dt.day, tzinfo=timezone.utc)
```

**After:** delete `normalize_date`; inline strict validation in the handler:
```python
raw_date = args.get("slot_target_date")
if not raw_date or not str(raw_date).strip():
    METRICS.incr("no_start_time")
    logger.info("validation: missing slot_target_date")
    return _err(400, "no_start_time",
                "slot_target_date is required. Ask the caller which day they want, then pass the date as YYYY-MM-DD.")

try:
    target_dt = datetime.strptime(str(raw_date).strip(), "%Y-%m-%d")
except ValueError:
    METRICS.incr("invalid_slot_target_date")
    logger.info("validation: bad slot_target_date=%r", raw_date)
    return _err(400, "invalid_slot_target_date",
                f"slot_target_date must be YYYY-MM-DD (got {raw_date!r}). Re-extract the date and retry.")

start_dt = datetime(target_dt.year, target_dt.month, target_dt.day, tzinfo=timezone.utc)
end_dt   = start_dt + timedelta(days=LOOKAHEAD_DAYS) - timedelta(seconds=1)
```

(`_err` helper — see CH-5.)

> **Downstream ripple (not in this file):** `slot_target_date` becomes effectively required. When wiring the agent, update `tool_definitions_v3.json` description from "Omit for ASAP" → "Always pass a concrete YYYY-MM-DD; for ASAP pass today's date", and the slot_selection prompt's ASAP rule accordingly. Tracked separately in the agent plan; **do not** edit agent files here.

---

### CH-3 — Separate upstream errors from empty results (A4)

**Why:** a Cal.com error currently returns `{ok:true, slots:[]}`, indistinguishable from genuine "no availability" — the LLM wrongly offers "no slots".

**Before** (`main.py:127-133`):
```python
if resp.status_code != 200:
    logger.error("Cal.com returned %s: %s", resp.status_code, resp.text[:200])
    return JSONResponse(status_code=200, content={"ok": False, "error": "slot lookup failed"})
body = resp.json()
slots = []
for date_key, times in (body.get("data") or {}).items():
    ...
```

**After:**
```python
resp = fetch_cal_slots(url, headers, params)          # CH-4 retry wrapper
if resp is None or resp.status_code != 200:
    METRICS.incr("upstream_unavailable")
    logger.error("Cal.com unavailable (status=%s)", getattr(resp, "status_code", None))
    return _upstream_err()

try:
    body = resp.json()
except ValueError:
    METRICS.incr("upstream_unavailable")
    logger.error("Cal.com returned non-JSON")
    return _upstream_err()

data = body.get("data")
if not isinstance(data, dict):                         # unexpected envelope
    METRICS.incr("upstream_unavailable")
    logger.error("Cal.com unexpected shape: %s", str(body)[:200])
    return _upstream_err()

slots = []
for date_key, times in data.items():
    ...

if not slots:                                         # valid query, nothing free
    METRICS.incr("no_availability_in_window")
    return JSONResponse(status_code=200,
                        content={"ok": True, "slots": [], "message": "no_availability_in_window"})
```

Helpers:
```python
def _upstream_err():
    return JSONResponse(status_code=200, content={
        "ok": False, "error": "upstream_unavailable",
        "message": "Calendar is temporarily unavailable. Tell the caller you'll check and try again shortly."
    })
```

---

### CH-4 — Cal.com retry + backoff (B3)

**Why:** a single transient 503/timeout shouldn't surface as a user-visible failure.

```python
def fetch_cal_slots(url, headers, params, attempts: int = 2, timeout: int = 10):
    """GET /v2/slots with one retry on 5xx/network error. Returns Response or None."""
    for attempt in range(attempts):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            if resp.status_code < 500:        # 2xx/4xx not retried
                return resp
            logger.warning("Cal.com %s (attempt %d)", resp.status_code, attempt + 1)
        except requests.RequestException as exc:
            logger.warning("Cal.com request error (attempt %d): %s", attempt + 1, exc)
        if attempt < attempts - 1:
            time.sleep(0.5 * (attempt + 1))    # 0.5s then bail
    return None
```

Note: switch from `url` with pre-built `urlencode` query to passing `params=` (cleaner, correct encoding).

---

### CH-5 — Error helper + contract standardization (C5)

Centralize every error response through one helper so the contract can't drift:

```python
def _err(status: int, code: str, message: str | None = None):
    METRICS.incr(code)
    body = {"ok": False, "error": code}
    if message:
        body["message"] = message
    return JSONResponse(status_code=status, content=body)
```

Use `_err(401, "unauthorized")` for signature failure (replaces the inline 401 at `main.py:92`).

---

### CH-6 — Request ID middleware + structured logging (C1)

```python
import uuid

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info("req id=%s path=%s status=%s %dms", request_id, request.url.path, response.status_code, duration_ms)
    return response
```

Log format gains `id=` on every line; correlate with the `/metrics` counters and Caddy logs.

---

### CH-7 — In-process metrics + `/metrics` (C2)

Lightweight, dependency-free counters:

```python
from collections import defaultdict
import threading

class Counters:
    def __init__(self):
        self._lock = threading.Lock()
        self._c = defaultdict(int)
    def incr(self, name: str, n: int = 1):
        with self._lock:
            self._c[name] += n
    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._c)

METRICS = Counters()

@app.get("/metrics")
async def metrics():
    return {"ok": True, "counters": METRICS.snapshot()}
```

Tracked counters: `slot_queries`, `no_start_time`, `invalid_slot_target_date`, `upstream_unavailable`, `no_availability_in_window`, `sig_rejected`, `rate_limited`. Increment `slot_queries` at the top of `check_availability`; `sig_rejected` in the 401 path.

---

### CH-8 — Rate limiting, per-IP sliding window (C3)

Defense-in-depth only (signature is the primary gate). Generous limit to never block legitimate voice traffic:

```python
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))

_rl_lock = threading.Lock()
_rl_hits: dict[str, list[float]] = defaultdict(list)

def _rate_limited(client_ip: str) -> bool:
    now = time.time()
    window = 60.0
    with _rl_lock:
        hits = _rl_hits[client_ip]
        _rl_hits[client_ip] = [t for t in hits if now - t < window] + [now]
        return len(_rl_hits[client_ip]) > RATE_LIMIT_PER_MIN
```

Call at top of `check_availability` (derive IP from `request.client.host` or `X-Forwarded-For` set by Caddy). On exceed → `METRICS.incr("rate_limited")` + `return _err(429, "rate_limited")`.

Add `RATE_LIMIT_PER_MIN` to `.env.example` (CH-9).

---

### CH-9 — `.env.example` sync + startup config validation (C4)

**`.env.example`** — add missing keys, drop `SKIP_SIGNATURE`:
```env
RETELL_API_KEY=
CAL_COM_API_KEY=
EVENT_TYPE_ID=6522694
TIMEZONE=Europe/London
CAL_API_VERSION=2024-09-04
CAL_COM_BASE=https://api.cal.com/v2
SLOT_DURATION_MIN=60
LOOKAHEAD_DAYS=7
MAX_SLOTS=20
RATE_LIMIT_PER_MIN=120
```

**Startup validation** (fail-fast — better than 500s at request time):
```python
REQUIRED_ENV = ["RETELL_API_KEY", "CAL_COM_API_KEY", "EVENT_TYPE_ID"]
_missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
if _missing:
    raise SystemExit(f"cal_slots: refusing to start — missing required env: {_missing}")
```
Place after the env reads at module top. systemd `Restart=always` will keep cycling, which is the correct signal (visible in `journalctl`) that the deploy is misconfigured rather than silently serving 401s.

---

## 5. Resulting `main.py` structure (top-to-bottom)

```
imports (stdlib + fastapi + requests + dotenv)
load_dotenv()
logging setup (logger = "cal_slots")
env reads (RETELL_API_KEY ... MAX_SLOTS, RATE_LIMIT_PER_MIN)
REQUIRED_ENV startup check                      # CH-9
app = FastAPI(...)
Counters + METRICS                              # CH-7
request_id_middleware                           # CH-6
helpers: _err, _upstream_err                    # CH-5
verify_retell_signature (versioned only)        # CH-1
fetch_cal_slots (retry)                         # CH-4
_rate_limited                                   # CH-8
GET  /health        (shallow: process alive)
GET  /ready         (config present)            # CH-9/B2
GET  /metrics       (counters)                  # CH-7
POST /check_availability:
    rate limit -> sig verify -> parse json -> strict date (CH-2)
    -> build window -> fetch_cal_slots (CH-4) -> shape (CH-3)
    -> {ok, slots[]} | error
```

---

## 6. File-change summary

| File | Changes |
|------|---------|
| `cal_slots_endpoint/main.py` | CH-1 … CH-8 (all behavioural edits) |
| `cal_slots_endpoint/.env.example` | CH-9 (add `CAL_COM_BASE`, `RATE_LIMIT_PER_MIN`; remove `SKIP_SIGNATURE`) |
| `cal_slots_endpoint/FINDINGS.md` | Mark Finding #1 `SKIP_SIGNATURE` resolved (CH-1 doc cleanup); note new error contract. No behaviour. |
| `cal_slots_endpoint/.env` | Add `RATE_LIMIT_PER_MIN=120` (live config). Confirm `SKIP_SIGNATURE` absent (already removed). |
| `cal_slots_endpoint/requirements.txt` | **No change** (zero new deps). |
| systemd `cal-slots.service` | **No change.** |

---

## 7. Verification / rollout (after implementation)

1. `systemctl --user restart cal-slots.service && systemctl --user status cal-slots.service`
2. `curl -4 https://slots.diallux-ai.site/health` → `{"ok":true,"service":"cal_slots"}`
3. `curl -4 https://slots.diallux-ai.site/ready` → `{"ok":true,...}`
4. `curl -4 https://slots.diallux-ai.site/metrics` → counters JSON
5. Temporarily set `SKIP_SIGNATURE` is **gone** — confirm an unsigned POST → 401 `{"ok":false,"error":"unauthorized"}`.
6. Missing-date test (signature bypassed locally for curl OR via Retell):
   `POST /check_availability {"args":{}}` → 400 `{"ok":false,"error":"no_start_time",...}`
7. Bad-date test: `{"args":{"slot_target_date":"tomorrow"}}` → 400 `invalid_slot_target_date`
8. Valid test: `{"args":{"slot_target_date":"2026-08-10"}}` → 200 with real slots, `time` local/no-Z.
9. **Retell 4xx verification (the † gate):** drive a missing-date call **from the chat agent**; confirm the LLM reads the `message` and asks for a date. If swallowed → flip the two 400 rows to 200 (§2 note).
10. `journalctl --user -u cal-slots.service -f` — confirm `id=` structured lines + counter increments.

---

## 8. Out of scope (recorded, not done here)

- **A5** PII redaction — no PII present in this function's inputs.
- **B1** Removed — window tz-anchoring is a non-issue (09:00 London earliest availability, 8-hour buffer).
- **B4** Automated tests — separate effort (§9).
- Agent-side wiring (`tool_definitions_v3.json`, slot_selection prompt ASAP rule, booking prompt `time`/`timezone`) — owned by the agent integration plan, not this webhook plan.
- Voice agent deploy / publish — chat-agent testing only per parent plan.

---

## 9. Future / optional (not in this plan)

- Split `main.py` into `config.py / security.py / cal_client.py / slots.py / errors.py / schemas.py` once tests exist.
- Prometheus `/metrics` (text format) + Grafana if traffic warrants.
- `pip-compile` hashed lockfile; Docker image; CI (lint + test on push).
- Persistent Caddy hardening (request body size limit, timeouts) at the proxy layer.

---

## 10. Checklist

- [x] CH-1 remove `SKIP_SIGNATURE` + legacy sig path
- [x] CH-2 strict date validation (`no_start_time` / `invalid_slot_target_date`)
- [x] CH-3 upstream-error separation
- [x] CH-4 Cal.com retry wrapper
- [x] CH-5 `_err` helper + contract standardization
- [x] CH-6 request ID middleware + structured logging
- [x] CH-7 metrics + `/metrics`
- [x] CH-8 rate limiting
- [x] CH-9 `.env.example` sync + startup validation
- [x] `.env` add `RATE_LIMIT_PER_MIN=120`
- [x] FINDINGS.md doc cleanup (SKIP_SIGNATURE resolved)
- [x] Restart + §7 verification steps 1–8
- [ ] **Retell 4xx gate** (§7 step 9) — decide 400 vs 200 fallback

---

## 11. Follow-up — multi-account support (2026-08-07)

This plan's hardening (CH-1…CH-9) assumed a **single** account (flat `CAL_COM_API_KEY`/`EVENT_TYPE_ID`). A separate change added **multi-account** support on top of the hardened webhook — **not** part of the checklist above:

- `config.py` `resolve()` now returns per-account `account_id` + `duration` from `CAL_ACCOUNTS`.
- `main.py` uses per-account `duration` and logs `account=.. event=.. duration=..`.
- `.env` / `.env.example` now document multiple `CAL_ACCOUNTS` entries (e.g. `diallux`, `diallux_live`).
- New `README.md` (in this dir) is the full multi-account how-to.
- HVAC tool schemas gained `account_id` with a fixed `default`.

**⚠️ Backward-compat caveat:** the **existing HVAC agent's live LLM is not yet passing `account_id`** — it relies on the `resolve(None)` default to the first `CAL_ACCOUNTS` entry (`diallux`). Fine while `diallux` stays first. To make it explicit, publish the `account_id` default (already in the V3.1 tool schemas) by rebuilding the HVAC LLM.

See `FINDINGS.md` Finding #10 and `README.md`.
