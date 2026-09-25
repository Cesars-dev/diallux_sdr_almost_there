# `/today` Endpoint Documentation

> **Purpose:** Provides today's date in a specific timezone for dynamic variable injection into Retell AI agents.
> **Status:** ACTIVE — deployed as part of the `cal_slots_endpoint` service.
> **Location:** `cal_slots_endpoint/main.py` (lines 158-173)

---

## Overview

The `/today` endpoint returns the current date in a requested timezone, primarily used to inject the `{{today_uk}}` dynamic variable into Retell AI agents at call/chat start time. This enables agents to understand the current date when discussing relative timeframes like "today", "tomorrow", or "next week".

---

## Technical Details

### Function Location

```python
# File: cal_slots_endpoint/main.py
# Lines: 158-173

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
```

### Dependencies

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi.responses import JSONResponse
```

---

## API Specification

### Endpoint

```
GET /today
```

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tz` | string | No | `Europe/London` | IANA timezone identifier (e.g., `Europe/London`, `America/New_York`) |

### Request Examples

```bash
# Using default timezone (Europe/London)
curl "https://slots.diallux-ai.site/today"

# Explicit timezone
curl "https://slots.diallux-ai.site/today?tz=America/New_York"

# Mexico City timezone
curl "https://slots.diallux-ai.site/today?tz=America/Mexico_City"
```

### Response Format

#### Success Response

```json
{
  "ok": true,
  "today": "2026-08-20",
  "timezone": "Europe/London",
  "tz_abbrev": "BST"
}
```

#### Error Response

```json
{
  "ok": false,
  "error": "invalid_timezone",
  "message": "Unknown timezone 'Invalid/Timezone'. Use an IANA name like Europe/London."
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | `true` if successful, `false` if error |
| `today` | string | Current date in `YYYY-MM-DD` format |
| `timezone` | string | The IANA timezone identifier used |
| `tz_abbrev` | string | Timezone abbreviation (e.g., `BST`, `EST`, `CDT`) |
| `error` | string | Error code (only on error) |
| `message` | string | Human-readable error message (only on error) |

---

## Integration with Retell AI

### Purpose in Retell AI Context

The `/today` endpoint solves a critical limitation in Retell AI's built-in dynamic variables:

**Problem:** Retell provides `{{current_time_Europe/London}}` but NO bare "today's date" variable like `{{current_date}}` or `{{now}}`.

**Solution:** The `/today` endpoint provides a clean `YYYY-MM-DD` date that can be:
1. Called during webhook injection at call start
2. Injected as `{{today_uk}}` dynamic variable
3. Used by agents for date calculations ("tomorrow" = today + 1)

### Dynamic Variable Injection Flow

```
1. Call/Chat Start
   ↓
2. Webhook calls /today?tz=Europe/London
   ↓
3. Returns {"ok": true, "today": "2026-08-20", ...}
   ↓
4. Webhook injects "today_uk": "2026-08-20" 
   ↓
5. Agent prompt contains {{today_uk}} = "2026-08-20"
   ↓
6. Agent can now calculate relative dates accurately
```

### Example Webhook Injection Code

```python
# File: agents/heating_uk/performance_tests/test_v3_llm_to_llm.py
# Lines: 153-174

TODAY_ENDPOINT = "https://slots.diallux-ai.site/today"

def _today_uk() -> str:
    """Today's date (YYYY-MM-DD) from the /today source of truth (Europe/London).

    The slot webhook rejects a blank slot_target_date (no_start_time), so this
    must never return empty. Primary: GET /today (the canonical day value).
    Fallback: local ZoneInfo Europe/London; last resort: UTC date.
    """
    try:
        req = urllib.request.Request(f"{TODAY_ENDPOINT}?tz=Europe/London")
        with urllib.request.urlopen(req, timeout=5) as r:
            body = json.loads(r.read().decode())
            if body.get("ok") and body.get("today"):
                return str(body["today"])
    except Exception:
        pass
    try:
        return datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
```

### Usage in Retell Agent Prompts

```markdown
# Example: agents/heating_uk/multiprompt/V3.1/prompts/multiprompt_mvp_slot_selection_v3.md

Today's date: {{today_uk}} (YYYY-MM-DD — the day the caller is on)

**Date Rules:**
- **"Today"** = {{today_uk}}
- **"Tomorrow"** = {{today_uk}} + 1 day  
- **"Next Monday"** = calculate from {{today_uk}}
- **"This week"** = calculate from {{today_uk}}
```

### Dynamic Variable Configuration

```python
# In webhook response for call_inbound/chat_inbound:

{
  "call_inbound": {
    "dynamic_variables": {
      "today_uk": "2026-08-20",  # Retrieved from /today endpoint
      "customer_name": "John",
      # ... other dynamic variables
    },
    "override_agent_id": None,
    "begin_message": "Hello, thanks for calling British Heat Services."
  }
}
```

---

## Date Format Specification

### Why `YYYY-MM-DD`?

1. **ISO 8601 Standard** - Internationally recognized date format
2. **Sortable** - Chronologically sortable as strings
3. **Machine-readable** - Easy to parse and manipulate
4. **Cal.com Compatible** - Works directly with Cal.com slot queries
5. **Timezone-neutral** - Date only, no time component to confuse calculations

### Example Dates

```
2026-08-20  # August 20, 2026
2026-12-25  # December 25, 2026  
2027-01-01  # January 1, 2027
```

---

## Timezone Handling

### Supported Timezones

The endpoint accepts any valid IANA timezone identifier:

| Region | Example IANA Timezone | Abbreviation |
|--------|----------------------|--------------|
| UK | `Europe/London` | `BST` (British Summer Time) or `GMT` |
| US Eastern | `America/New_York` | `EST` or `EDT` |
| US Central | `America/Chicago` | `CST` or `CDT` |
| US Mountain | `America/Denver` | `MST` or `MDT` |
| US Pacific | `America/Los_Angeles` | `PST` or `PDT` |
| Mexico | `America/Mexico_City` | `CST` or `CDT` |
| Australia East | `Australia/Sydney` | `AEST` or `AEDT` |

### Date Boundaries

The endpoint returns the **local date** for the requested timezone:

- If it's 2:00 AM on August 20th in London, returns `"2026-08-20"`
- If it's 8:00 PM on August 19th in London (but 2:00 AM August 20th in Mexico City), London request returns `"2026-08-20"`, Mexico City request returns `"2026-08-20"`

### Daylight Saving Time

The endpoint automatically handles DST transitions:
- Uses `ZoneInfo` which includes historical and current DST rules
- Returns correct local date even during DST transitions
- Provides `tz_abbrev` (e.g., `BST` vs `GMT`) for current state

---

## Error Handling

### Error Cases

| Scenario | HTTP Status | Error Code | Handling |
|----------|-------------|------------|----------|
| Invalid timezone | 200 | `invalid_timezone` | Returns helpful message with example |
| Network issues | N/A | N/A | Caller should implement fallback logic |
| Service unavailable | N/A | N/A | Caller should implement retry logic |

### Recommended Client Error Handling

```python
def get_today_uk() -> str:
    """Robust client with fallbacks for /today endpoint."""
    try:
        # Primary: Use the /today endpoint
        response = requests.get("https://slots.diallux-ai.site/today?tz=Europe/London", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and data.get("today"):
                return data["today"]
    except Exception:
        pass
    
    try:
        # Fallback 1: Local timezone calculation
        return datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%d")
    except Exception:
        pass
    
    try:
        # Fallback 2: UTC calculation
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        pass
    
    # Last resort: Use fixed current date (prevent empty return)
    return datetime.now().strftime("%Y-%m-%d")
```

---

## Deployment Information

### Service Configuration

| Item | Value |
|------|-------|
| **Service** | `cal_slots_endpoint` (FastAPI) |
| **Host** | Hetzner VPS `MainVps` (IP: `46.62.233.228`) |
| **Public URL** | `https://slots.diallux-ai.site/today` |
| **Proxy** | Caddy → `localhost:8001` |
| **Systemd Service** | `cal-slots.service` |
| **Port** | `8001` (localhost only) |

### Health Check

```bash
# Check if the service is running
curl "https://slots.diallux-ai.site/health"
# Expected: {"ok": true, "service": "cal_slots"}

# Test the /today endpoint directly
curl "https://slots.diallux-ai.site/today"
# Expected: {"ok": true, "today": "2026-08-20", "timezone": "Europe/London", "tz_abbrev": "BST"}
```

### Service Management

```bash
# Check service status
systemctl --user status cal-slots.service

# Restart service
systemctl --user restart cal-slots.service

# View logs
journalctl --user -u cal-slots.service -f
```

---

## Use Cases

### Primary Use Case: Date-Aware Conversational AI

The main purpose is enabling Retell AI agents to understand and work with relative time expressions:

```markdown
# Without {{today_uk}} - Agent confusion:
User: "Can I book for tomorrow?"
Agent: "I need to know what date tomorrow is..."

# With {{today_uk}} - Agent understands:
User: "Can I book for tomorrow?"  
Agent: "I can check slots for August 21st (tomorrow)..."
```

### Secondary Use Cases

1. **Timezone-aware scheduling** - Different regions use different timezones
2. **Date validation** - Ensure proposed dates are in the future
3. **Calendar integration** - Feed correct dates to Cal.com slot queries
4. **Testing automation** - Get consistent "today" values for test scenarios

---

## Related Components

### Integration Points

| Component | Relationship | Files |
|-----------|--------------|-------|
| **Custom Function** | Uses `{{today_uk}}` for date calculations | `V3.1/prompts/multiprompt_mvp_slot_selection_v3.md` |
| **Test Scripts** | Fetch today's date for test scenarios | `performance_tests/test_v3_llm_to_llm.py` |
| **Cal.com Integration** | Provides dates for slot queries | `cal_slots_endpoint/main.py` - `/check_availability` |
| **Webhook Injection** | Injects `{{today_uk}}` at call start | Test files & webhook handlers |

### Companion Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Service health check |
| `/ready` | Configuration readiness check |
| `/metrics` | Service metrics and counters |
| `/check_availability` | Cal.com slot queries (main custom function) |

---

## Testing

### Manual Testing

```bash
# Test with different timezones
curl "https://slots.diallux-ai.site/today?tz=Europe/London"
curl "https://slots.diallux-ai.site/today?tz=America/New_York"
curl "https://slots.diallux-ai.site/today?tz=Asia/Tokyo"

# Test error handling
curl "https://slots.diallux-ai.site/today?tz=Invalid/Timezone"
```

### Automated Testing

```python
def test_today_endpoint():
    """Test the /today endpoint functionality."""
    import requests
    
    # Test default timezone
    response = requests.get("https://slots.diallux-ai.site/today")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] == True
    assert "today" in data
    assert len(data["today"]) == 10  # YYYY-MM-DD format
    
    # Test specific timezone
    response = requests.get("https://slots.diallux-ai.site/today?tz=America/New_York")
    assert response.status_code == 200
    data = response.json()
    assert data["timezone"] == "America/New_York"
    
    # Test invalid timezone
    response = requests.get("https://slots.diallux-ai.site/today?tz=Invalid/Timezone")
    assert response.status_code == 200  # Returns 200 with error body
    data = response.json()
    assert data["ok"] == False
    assert "error" in data
```

---

## Monitoring and Maintenance

### Monitoring

Monitor the `/today` endpoint alongside the main `cal_slots_endpoint` service:

```bash
# Check service health
curl "https://slots.diallux-ai.site/health"

# View service logs for /today requests
journalctl --user -u cal-slots.service -f | grep "/today"
```

### Maintenance Considerations

1. **Timezone Database Updates** - `ZoneInfo` uses system timezone database, keep updated
2. **Endpoint Availability** - Monitor uptime and response times
3. **Fallback Reliability** - Ensure client fallbacks work when endpoint is unavailable
4. **Service Restart** - Restart after code changes: `systemctl --user restart cal-slots.service`

---

## Security Considerations

### Security Status

- **No Authentication Required** - This is a public, read-only endpoint
- **Rate Limiting** - Protected by global service rate limiter
- **Input Validation** - Timezone input validated via `ZoneInfo`
- **No Sensitive Data** - Only public timezone information is returned

### Best Practices

1. **Use HTTPS Only** - Never use HTTP (enforced by Caddy)
2. **Implement Timeouts** - Client-side timeout recommended (5 seconds)
3. **Fallback Strategy** - Always implement client-side fallbacks
4. **Error Handling** - Gracefully handle invalid timezone requests

---

## Changelog

### Version History

| Date | Change | Impact |
|------|--------|--------|
| 2026-08-07 | Added multi-account support to main service | `/today` endpoint remains unchanged |
| 2026-08-02 | Initial deployment with `/today` endpoint | Provides date injection capability |

---

## Support and Troubleshooting

### Common Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Wrong date returned | Date doesn't match expected timezone | Check IANA timezone spelling and region |
| Endpoint unreachable | Connection timeout or refused | Check service status: `systemctl --user status cal-slots.service` |
| Invalid timezone error | Error response with `invalid_timezone` | Use correct IANA timezone name (e.g., `Europe/London` not `London`) |

### Getting Help

1. **Check service logs**: `journalctl --user -u cal-slots.service -f`
2. **Test endpoint directly**: `curl "https://slots.diallux-ai.site/today"`
3. **Review related documentation**: See `README.md`, `ARCHITECTURE.md`, `FINDINGS.md`
4. **Check main service health**: `curl "https://slots.diallux-ai.site/health"`

---

## Conclusion

The `/today` endpoint provides a critical piece of infrastructure for date-aware conversational AI by supplying the current date in a timezone-aware, machine-readable format. Its integration with Retell AI's dynamic variable system enables agents to understand and work with relative time expressions naturally and accurately.