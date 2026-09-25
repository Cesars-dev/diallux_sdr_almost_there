# Time Service Architecture

## Design Principles

1. **Agent-Agnostic**: Works with any Retell agent regardless of timezone or format requirements
2. **Flexible Input**: Accepts various Retell dynamic time formats
3. **Multiple Output Formats**: Returns time data in multiple standard formats
4. **Backward Compatible**: Provides `/today` compatible with the cal_slots_endpoint one for existing integrations
5. **Secure**: Uses same HMAC-SHA256 signature verification as cal_slots_endpoint
6. **Observable**: Includes health checks, metrics, and structured logging

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Retell AI Platform                       │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │   heating_uk     │         │   Other Agents   │         │
│  │   Agent          │         │                  │         │
│  │                  │         │                  │         │
│  │  Dynamic Vars:   │         │  Dynamic Vars:   │         │
│  │  {{current_time_ │         │  {{current_time_ │         │
│  │   Europe/London}}│         │   America/NY}}   │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
└───────────┼───────────────────────────────┼─────────────────┘
            │                               │
            │  Webhook Call                │  Webhook Call
            │  POST /parse-time            │  POST /parse-time
            │                               │
            ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Time Service (FastAPI, port 8002)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Webhook Layer                                       │   │
│  │  - Signature Verification (X-Retell-Signature)      │   │
│  │  - Rate Limiting                                     │   │
│  │  - Request ID Tracking                               │   │
│  └─────────────────┬───────────────────────────────────┘   │
│                    │                                       │
│                    ▼                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Time Parsing Layer                                 │   │
│  │  - dateutil Parser (fuzzy)                          │   │
│  │  - IANA Timezone Support (ZoneInfo)                 │   │
│  │  - Format Validation                                │   │
│  └─────────────────┬───────────────────────────────────┘   │
│                    │                                       │
│                    ▼                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Output Generation Layer                           │   │
│  │  - YYYY-MM-DD (today)                               │   │
│  │  - YYYY-MM-DDTHH:MM:SS (now)                        │   │
│  │  - Unix Timestamp                                   │   │
│  │  - ISO-8601 Format                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Agent Call Start

```
Retell Agent → Receives dynamic values
           → Calls time service webhook
```

### 2. Webhook Processing

```
POST https://slots.diallux-ai.site/time-function/parse-time
{
  "source_timezone": "Europe/London",
  "current_time": "Sunday, August 2, 2026 at 07:00 AM BST"
}
```

### 3. Time Parsing

```
dateutil_parser.parse("Sunday, August 2, 2026 at 07:00 AM BST")
↓
datetime object with Europe/London timezone
```

### 4. Format Generation

```
datetime → [today, now, timestamp, iso_format]
↓
{
  "today": "2026-08-02",
  "now": "2026-08-02T07:00:00",
  "timestamp": 1783076400,
  "iso_format": "2026-08-02T07:00:00+01:00"
}
```

### 5. Response to Agent

```
JSON response → Agent prompt injection
           → {{today_uk}}, {{now_uk}}
```

## Security Model

### Signature Verification

Same as cal_slots_endpoint:
- HMAC-SHA256 signature verification (`X-Retell-Signature: v=<ms>,d=<hex>`)
- Timestamp-based replay protection (5-minute window)
- Full raw request body signing

### Rate Limiting

- Per-IP sliding window rate limiter
- Configurable limit (default: 120 requests/minute)
- Defense-in-depth behind signature verification

### Input Validation

- JSON schema validation
- Timezone validation via IANA ZoneInfo
- Time string parsing with error handling

## Error Handling Strategy

### Client Errors (4xx)

- `400 invalid_json` - Malformed request body
- `400 missing_time` - No time string provided
- `400 parse_failed` - Failed to parse time string
- `400 invalid_timezone` - Unknown timezone
- `401 unauthorized` - Invalid signature
- `429 rate_limited` - Too many requests

## Deployment Architecture

### VPS Deployment

```
Hetzner VPS (MainVps)
├── User: 2nd_workspace
├── Services:
│   ├── cal_slots_endpoint (port 8001)
│   └── time_endpoint (port 8002)
└── Systemd:
    ├── cal-slots.service
    └── time-service.service
```

### Caddy Proxy Configuration (existing domain, path-based)

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

The time service is exposed under the existing `slots.diallux-ai.site` domain under the `/time-function` prefix to avoid DNS/cert setup. Public paths: `https://slots.diallux-ai.site/time-function/parse-time` and `/time-function/today`. `/health`, `/ready`, and `/metrics` are intentionally localhost-only (127.0.0.1:8002) because the public paths are owned by cal_slots_endpoint.

## Migration Strategy

### Phase 1: Parallel Deployment

1. Deploy time_endpoint alongside cal_slots_endpoint
2. Keep existing `/today` endpoint in cal_slots_endpoint for backward compatibility
3. Test new service with development agents
4. Gradually migrate agents to use the new service

### Phase 2: Agent Migration

1. Update heating_uk agent/tests to use time_endpoint
2. Monitor both services during transition
3. Remove `/today` endpoint from cal_slots_endpoint after full migration

### Phase 3: Deprecation

1. Remove `/today` endpoint from cal_slots_endpoint
2. Consolidate time functionality into time_endpoint
3. Update documentation and references

## Performance Considerations

- Memory: ~50MB baseline
- CPU: Minimal for parsing operations
- Network: Small JSON payloads
- Stateless design allows horizontal scaling
- Rate limiting prevents abuse

## Future Enhancements

1. **Timezone Conversion API**: Convert between timezones
2. **Time Calculations**: Add/subtract time periods
3. **Calendar Integration**: Direct calendar time queries
4. **Batch Processing**: Parse multiple time strings in one request
