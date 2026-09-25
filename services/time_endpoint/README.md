# Time Service — Agent-Agnostic Time Parsing

> **Purpose:** Parse Retell's dynamic time values and return standardized time formats for any AI agent.
> **Location:** `/home/julio/projects/Retell_AI_MCP_connection/time_endpoint/`
> **Public URL:** `https://slots.diallux-ai.site/time-function/*` (same domain as cal_slots_endpoint, routed by path via Caddy)

## Overview

The Time Service provides a flexible, agent-agnostic way to parse Retell's dynamic time variables (like `{{current_time_Europe/London}}`) and return standardized time formats. This replaces the hardcoded `/today` endpoint in cal_slots_endpoint with a more flexible solution.

## Why This Service

Retell provides dynamic time values but no standardized date parsing. Different agents need different formats:
- **heating_uk agent**: `YYYY-MM-DD` format for slot queries
- **Test scenarios**: Various formats for validation
- **Future agents**: Different timezone/format requirements

This service accepts any Retell time format and returns multiple standard formats.

## API Endpoints

### `POST /time-function/parse-time` (Main Endpoint)

Parse Retell dynamic time values and return standardized formats. Requires `X-Retell-Signature` (same HMAC-SHA256 scheme as cal_slots_endpoint, keyed with the shared `RETELL_API_KEY`).

**Request:**
```json
{
  "source_timezone": "Europe/London",
  "current_time": "Sunday, August 2, 2026 at 07:00 AM BST",
  "requested_format": ["today", "now", "timestamp", "iso_format"]
}
```

**Response:**
```json
{
  "ok": true,
  "timezone": "Europe/London",
  "tz_abbrev": "GMT+01:00",
  "parsed_time": "Sunday, August 2, 2026 at 07:00 AM BST",
  "today": "2026-08-02",
  "now": "2026-08-02T07:00:00",
  "timestamp": 1783076400,
  "iso_format": "2026-08-02T07:00:00+01:00"
}
```


### `GET /time-function/today` (Legacy Compatibility)

No signature required. Mirrors the cal_slots_endpoint `/today` so existing agents/tests can switch over without changes.

**Request:**
```
GET https://slots.diallux-ai.site/time-function/today?tz=Europe/London
```

**Response:**
```json
{
  "ok": true,
  "today": "2026-08-20",
  "timezone": "Europe/London",
  "tz_abbrev": "GMT+01:00"
}
```

### `GET /health` / `GET /ready` / `GET /metrics`

Monitoring endpoints. These are **localhost-only** (127.0.0.1:8002) because the public domain paths are taken by cal_slots_endpoint. Check them on the VPS with:

```bash
curl -s http://127.0.0.1:8002/health
```

## Integration with Retell Agents

### Custom function URL

Point a Retell custom function tool at the public URL (the agent then supplies the time string):

```
POST https://slots.diallux-ai.site/time-function/parse-time
```

### Dynamic Variable Usage

The service is designed to receive Retell's injected dynamic values directly, e.g. `{{current_time_Europe/London}}` → `"Sunday, August 2, 2026 at 07:00 AM BST"`.

## Working with cal_slots_endpoint

This service feeds the **Cal.com slot checker** (`cal_slots_endpoint/`). The agent-agnostic flow:

```
Retell {{current_calendar}} (14-day listing, 1st line = "Today")
        │  e.g. "Sunday, August 2, 2026 BST (Today)"
        ▼
time service  POST /time-function/parse-time   →  today (YYYY-MM-DD)
        │
        ▼
cal_slots_endpoint  POST /check_availability  { slot_target_date: today }  →  slots
```

- Retell's `{{current_calendar}}` first line always marks the agent's current day ("… (Today)") and embeds the timezone. Strip the marker and send it to `/parse-time` — it returns the standardized `today` (YYYY-MM-DD).
- That `today` is exactly the `slot_target_date` that `cal_slots_endpoint/check_availability` requires.
- **`bridge.py`** (project root) exercises the full chain live and is reusable.

See `../SERVICES_OVERVIEW.md` and `cal_slots_endpoint/README.md` §10.

## Configuration

Environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `RETELL_API_KEY` | Webhook signature verification key (shared with cal_slots_endpoint) | Required |
| `SERVICE_PORT` | Service port | `8002` |
| `DEFAULT_TIMEZONE` | Default timezone | `Europe/London` |
| `DEFAULT_OUTPUT_FORMAT` | Default output formats | `today,now,timestamp,iso_format` |
| `RATE_LIMIT_PER_MIN` | Rate limit per IP | `120` |

## Deployment

### Local Testing

```bash
cd /home/julio/projects/Retell_AI_MCP_connection/time_endpoint
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

### VPS Deployment

```bash
cd /home/julio/projects/Retell_AI_MCP_connection/time_endpoint
./deploy.sh
```

Then on the VPS:

```bash
systemctl --user link --force time-service.service
systemctl --user daemon-reload
systemctl --user enable time-service
systemctl --user start time-service
systemctl --user status time-service
journalctl --user -u time-service -f
```

### Caddy routing (existing domain, path-based)

Add to the existing `slots.diallux-ai.site` site block — **do not restart cal_slots_endpoint**:

```
slots.diallux-ai.site {
    handle /time-function* {
        uri strip_prefix /time-function
        reverse_proxy 127.0.0.1:8002
    }
    handle {
        reverse_proxy 127.0.0.1:8001
    }
}
```

`/time-function/*` is stripped and forwarded to port 8002; everything else goes to the existing cal_slots_endpoint on port 8001. The `uri strip_prefix` means the agent-facing paths are `/time-function/parse-time` and `/time-function/today`.

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## Migration from cal_slots_endpoint

The existing `/today` endpoint in cal_slots_endpoint remains for backward compatibility. New agents should use the time service (`/parse-time` or the new `/today`).

## Error Handling

The service returns structured error responses:

```json
{
  "ok": false,
  "error": "error_code",
  "message": "Human-readable error message"
}
```

Error codes:
- `unauthorized` — Invalid or missing signature
- `rate_limited` — Too many requests
- `invalid_json` — Malformed request body
- `missing_time` — No time string provided
- `parse_failed` — Failed to parse time string
- `invalid_timezone` — Unknown timezone
