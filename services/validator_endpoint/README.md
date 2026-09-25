# validator_endpoint — Lead Validation Gate (`/validate_lead`)

> **Agent-agnostic booking gate.** FastAPI service on MainVps, port 8003 (localhost-only),
> exposed via Caddy at `https://slots.diallux-ai.site/validator-function/*`.
> Systemd user unit: `validator-service.service` (`systemctl --user start validator-service`).

## What it does

Server-side truth check that runs BEFORE any calendar booking is allowed. The Retell agent calls
it as a custom function in its ConfirmSlots state; the endpoint parses/validates fuzzy human data
and returns a verdict. The verdict is written into the conversation's dynamic variables as
`slot_verified` — and the state-machine edge `ConfirmSlots → Booking` requires
`slot_verified == true`. **No boolean, no booking. This kills fabricated bookings at the root.**

## Endpoint

```
POST /validator-function/validate_lead
Headers: X-Retell-Signature: <HMAC>   (multi-key auth, same scheme as time_endpoint)
Body (Retell posts {"args": {...}} when args_at_root=false — we unwrap both shapes):
{
  "close_rate_percent": 50,          // fuzzy: "fifty", 0.5 → 50
  "weekly_missed_calls": 12,         // word-numbers ok ("twelve")
  "avg_job_value": 450,              // "$450ish" ok; money floor-rounded to 2 sig figs ($32,578→$32,000)
  "callback_number": "+13125551234", // digit-extraction from "(312) 555-1234" etc. → E.164
  "timezone": "America/Chicago",     // aliases accepted ("central", "CST")
  "company_name": "Bright Smile Dental"
}
Response: { ok, slot_verified, monthly_leak, sanitized fields... }
```

## Files

| File | Purpose |
|---|---|
| `main.py` | FastAPI app + HMAC auth + nested-args unwrap |
| `validate.py` | parsing/sanitizing logic (pure functions) |
| `test_validate.py` | 33 fixtures — run before every deploy: `python3 test_validate.py` |

## Deploy / ops

```bash
cp validator-service.service ~/.config/systemd/user/ && systemctl --user daemon-reload
systemctl --user enable --now validator-service
curl -s localhost:8003/docs            # sanity
```

Caddy route is injected at RUNTIME via admin API (root-owned Caddyfile — do not edit):
`curl 127.0.0.1:2019/config/... ` — see `docs/custom_endpoints.md`. **Re-inject if Caddy restarts.**

## Related

- Sibling services: [`time_endpoint/`](../time_endpoint/) (:8002), [`cal_slots_endpoint/`](../cal_slots_endpoint/)
- Overview: [`docs/SERVICES_OVERVIEW.md`](../docs/SERVICES_OVERVIEW.md)
- Used by production agent `V7.5_lean` (see `Dialux_SDR/SKILL.md` §4 — "the gate")
