# AGENTS.md — V7.9_slot_lock repo

> Repo map + operating rules. Full endpoint contract: [`ENDPOINTS.md`](ENDPOINTS.md). For the lab's mechanics read [`lab/AGENTS.md`](lab/AGENTS.md);
> for the agent artifact read [`retell/README.md`](retell/README.md) and [`retell/STATE.md`](retell/STATE.md).

## What this repo is

The complete V7.9 "slot-lock" iteration of the Dialux SDR chat agent, split in two:

- **`retell/`** — the production agent artifact. `llm.json` is BUILT from `prompts/ + tools/ +
  edges/` by `retell/tools/build_llm_json.py` (parity-checked) and deployed by
  `retell/deploy_v68.py` (new LLM + new chat agent per deploy — never patch; KBs reused via
  registry). Currently live on Retell as `agent_f305981ef7b5ce312c1c899bbf`.
- **`lab/`** — a local runtime for the same artifact on raw OpenAI, plus the acceptance ladder,
  the client demo, and Langfuse tracing. Exists because the Retell workspace is out of prepaid
  credits; lets testing/demoing continue with real bookings at ~$0.50/run.

## Non-negotiable rules

1. **Sequential testing only** — parallel agent runs race the shared Cal.com calendar
   (produces fake conflicts). One persona at a time; cancel test bookings after every batch.
2. **One variable at a time** when iterating the agent: clone folder → change →
   `python3 retell/tools/build_llm_json.py` → `python3 retell/deploy_v68.py` → full ladder.
3. **Never patch a deployed agent.** New LLM + new agent per deploy; snapshot into
   `retell/versions/NN_name_<llm8>/` before the next iteration.
4. **No secrets in this repo.** Deploy snapshots of superseded versions contain the old embedded
   Cal.com key — they are gitignored on purpose (see `.gitignore`). Runtime keys load from the
   host environment. Scan with the secret-hunt script before pushing.
5. **gpt-5.2 invocation config is measured, not optional**: no `temperature`, no
   `reasoning_effort` → 0.84s avg. Adding either re-introduces 3–87s latencies. Details in
   `lab/README.md` §5.

## Endpoints (intentionally exposed — for agents working inside this system)

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST https://slots.diallux-ai.site/check_availability` | HMAC `X-Retell-Signature: v=<ms>,d=hex(HMAC_SHA256(raw_body+ms, RETELL_API_KEY))` | Slot-lock availability: returns exactly 2 frozen slots (`{day,time,iso,reservation_uid}`) + `slot_reservation_uids`. Args: `slot_target_date` (YYYY-MM-DD), `timezone` (IANA), `account_id:"diallux_live"`, `current_reservation_uids` (echo back, `""` first call), optional `preferred_time` (local `YYYY-MM-DDTHH:MM`). |
| `POST https://slots.diallux-ai.site/book-livecall` | same HMAC | Idempotent booking. Args: `time` (verbatim `{{selected_time}}`), `timezone`, `name`, `attendeePhoneNumber` (E.164), `title`, `notes`, `account_id:"diallux_live"`, `slot_reservation_uids` (verbatim echo), `booking_intent` (`""`\|`reschedule`\|`cancel`), `preferred_time`. Responses: `{status:"booked", booking_uid, booking_verified}` / `book_failed` / `reschedule_options` / `released`. |
| `POST https://slots.diallux-ai.site/validator-function/validate_lead` | same HMAC | Deterministic data gate → writes `slot_verified`, computes `weekly_leak`/`monthly_leak`. |
| `POST https://slots.diallux-ai.site/validator-function/verify-lead-data` | same HMAC | VerifyLead gate → writes `data_verified`. |
| `POST https://slots.diallux-ai.site/validator-function/record-booking-uid` | same HMAC | Records only Cal-accepted 22-char UIDs → `booking_uid`. |
| `POST https://slots.diallux-ai.site/validator-function/set-callback-number` | same HMAC | Alternate-number write (E.164 or nothing). |
| `GET https://slots.diallux-ai.site/today?tz=<IANA>` | none | Real today (`YYYY-MM-DD`) — the only date source prompts may trust. |

Cal.com: event `3801235` (diallux_live, 45 min, America/Mexico_City); booking API version
`2026-05-01`, cancel `2026-02-25` (body `cancellationReason` required), slot reservations
`2024-09-04`, `User-Agent` header mandatory. Full notes: parent repo `docs/api/CAL_COM_API_NOTES.md`.

## Known open items

1. Closer sometimes skips the leak-monetization pitch (`calculate_monthly_leak` never fires) —
   stochastic; fix queued in the deterministic layer, not the prompt.
2. Booking.md scripts "SMS text confirmation" — nothing sends SMS; reword or wire SMS.
3. `today_date` dv seed hardcoded (stale date) — set to `""` next deploy.
4. Retell workspace awaits credits → then redeploy with `model_fast: true` + full ladder.
