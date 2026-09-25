# Dialux SDR V6.5 — WORKING / CURRENT (good build)

> **Status: WORKING — current deployable version.** Supersedes the deprecated 6.4 build
> (`./deprecated_6.4/`).

## What this is

This is the **V6.4 edge-schema null-fix build, renamed 6.5** — the current good/working agent
architecture. It is the config that was deployed 2026-08-22 and would have run the acceptance test,
but the Retell account was **blocked with HTTP 402 (payment overdue)** at the time, so the live
happy-path could **not** be executed.

**Deployed (2026-08-22):**
- Chat agent: `agent_74b34a77089cfbc325f02613c9` ("Linda AI V2 enhanced")
- LLM: `llm_043beb4a94649eb959bf31c1e01c` (gpt-5.1)
- KBs: all 9 reused from `MVP_agent/config/kb_registry.json` (no new KBs)

## The fix (vs the deprecated 6.4 lineage)

Each `*.edges.json` transition schema carries **only its `required` params** — no more dumping
not-yet-known vars as JSON `null` into `collected_dynamic_variables`. This eliminates the
`first_name="null"` / `callback_number="null"` / empty-`industry` clobber that V6.3 exhibited while
keeping the deterministic edge-schema `transition_to_*` mechanism.

## Transition graph (edge-schema driven, only required params)

```
Intake ──[inbound_channel, interest_topic, pain_frame, intake_completed]───────────▶ Discovery
Discovery ──[industry, pain_points, interest_signal, pattern_matched, discovery_completed]─▶ Closer
Closer ──[industry, pain_points, interest_level, closer_completed]───────────────────▶ Offer
Offer ──[livecall_agreed, offer_completed]─────────────────────────────────────────▶ contact_details
contact_details ──[first_name, last_name, company_name, prospect_timezone, callback_number, is_calling_best_number, contact_details_completed]─▶ Booking
Booking ──[booking_confirmed, booking_completed]───────────────────────────────────▶ Closing
Closing ──(terminal)
```

## Files

- `llm.json` — full deployable LLM payload (V6.4 null-fix)
- `prompts/` — `general_prompt.md`, `begin_message.txt`, `states/*.md`
- `tools/` — `general_tools.json` + per-state `*.tools.json` (carried over unchanged from 6.4 lineage)
- `edges/` — per-state `*.edges.json` (transition schemas, reduced to required params)
- `Knowledge bases/` — the 9 KBs (reused, no new KBs)
- `knowledge_bases.json` — KB reference list
- `deprecated_6.4/` — the superseded build, archived

## Test status / next step

- **BLOCKED:** the Maria happy-path acceptance test could not run on 2026-08-22 because the Retell
  account returned **HTTP 402 (payment overdue, service stopped)** — `create-chat` was rejected.
- **To test:** once the Retell account is unblocked (new/paid API key), point the harness
  `tools/test_llm_to_llm.py:18` `CHAT_AGENT` at `agent_74b34a77089cfbc325f02613c9` and run:
  ```bash
  python3 tools/test_llm_to_llm.py happy
  ```
  Pass = 6/6 `transition_to_*` + `query_livecall_slots` + `create_livecall_booking` + `end_call`,
  with `collected_dynamic_variables.first_name == "Maria"` (not `"null"`), `callback_number`
  populated, `industry` = dental.

## Deploy

```bash
export RETELL_API_KEY=key_...            # new/paid key
cd "Dialux_SDR/6.1 iterations/MVP_agent"
cp "Dialux_SDR/working_agent/llm.json" config/llm.json
python3 deploy_chat.py                    # creates NEW LLM + NEW chat agent
```
NEVER run `build_llm.py` (regenerates from V1 sources). NEVER PATCH an LLM.

## ⚠️ Deploy target — NEW Retell account — **PAUSED / PENDING REVIEW (2026-08-22)**

> **DEPLOY IS PAUSED** (LLM + chat agent not yet created). This 6.5 build is to be deployed on the
> **NEW Retell workspace account**, not the old one.

### KB state — ALL 9 CREATED (updated 2026-08-22)

`create-knowledge-base` initially returned HTTP 402 (no card on file) on the 9th KB, but a retry
**succeeded** — all 9 Dialux KBs now exist on the new account (verified via `list-knowledge-bases`),
and the 2 original pre-existing KBs were **deleted**. Registry updated → next deploy **reuses** (no
duplicates).

- `are-you-ai-kb` → `knowledge_base_ff29253665591a39`
- `call-closing-kb` → `knowledge_base_6d5e5b576556d107`
- `call-context-kb` → `knowledge_base_653309a94e71b007`
- `discovery-bridge-kb` → `knowledge_base_ddfb4d4d1987ebb5`
- `industry-kb` → `knowledge_base_92d62b0457c9ea64`
- `pain-points-kb` → `knowledge_base_2dc0c4148fc5259a`
- `sales-language-kb` → `knowledge_base_dd0ea1c6963bcadf`
- `sales-psychology-kb` → `knowledge_base_2d6380cf6d5f2aa7`
- `voice-ai-capabilities-kb` → `knowledge_base_09e6970b52579616` (created on retry)

`config/kb_registry.json` now holds all 9 (hashes verified MATCH local files), so `deploy_chat.py`
will **reuse** all 9 on the next run. Old-account registry backed up at
`config/kb_registry.json.old_account.bak`.

### Remaining blocker (2026-08-22)

Deploy still cannot create the LLM / chat agent if the account requires a card for those too —
`create-knowledge-base` 402 was transient (retry passed), so a re-run of `deploy_chat.py` is the
next step to confirm whether LLM + chat-agent creation works. If those succeed, the deploy completes;
if they 402, a card must be added.

### Resume checklist (next step)

1. Re-run `python3 deploy_chat.py` with `RETELL_API_KEY=<redacted - in host env>`.
   - Registry now has all 9 KB ids + matching hashes → all 9 will be **reused** (no re-create, no dupes).
2. If it reaches `create-retell-llm` / `create-chat-agent` and succeeds → new LLM + new chat agent created;
   capture both ids. If it 402s there → a payment card must be added to the workspace first.
3. Point `tools/test_llm_to_llm.py:18` `CHAT_AGENT` at the new chat agent.
4. Run `python3 tools/test_llm_to_llm.py happy` (Maria) — expect 6/6 transitions + booking +
   `first_name=="Maria"` (not `"null"`).

### Key facts (new account)

- Old account (`<deprecated key — redacted>`) is **deprecated in `.env`** — payment-overdue.
- **New active Retell key** in project root `.env`:
  - `RETELL_API_KEY=<redacted - in host env>` (promoted from `RETELL_CESAR_KEY`)
  - Old key retained as `# RETELL_API_KEY_DEPRECATED=<deprecated key — redacted>` for reference only.
- All deploy/test scripts read `RETELL_API_KEY` from `.env` or `$RETELL_API_KEY`.
  `agents/heating_uk/multiprompt/WEBHOOK_TEST/build_name_check_llm.py` hardcoded fallback was updated
  to the new key.