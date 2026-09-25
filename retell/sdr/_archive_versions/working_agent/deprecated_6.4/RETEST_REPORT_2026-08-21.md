# Dialux Working Agent — Re-test Report After KB Wipe

- **Date:** 2026-08-21 (10:49–10:58 UTC)
- **Agent under test:** "Linda AI V2 enhanced"
- **New chat agent:** `agent_622d357f685e64b39426e75ca9`
- **New LLM:** `llm_71ce39ed60b33447840865c8e356` (gpt-5.1, temp 0.1, tool_call_strict_mode)
- **Source config:** `working_agent/llm.json` (== `6.1 iterations/V6.3/llm.json`, byte-identical, md5 `0df0f4db63111720155dcdc543b2eec2`)
- **Deploy path:** `deploy_chat.py` (registry-based; 9 KBs CREATED once, registered in `MVP_agent/config/kb_registry.json`)
- **Purpose:** Prove the v63e working config still passes the full happy-path after all 192 KBs were wiped from Retell, i.e. the earlier 6/6 PASS was not an accident.

---

## Executive Summary

**VERDICT: PASS.** All 4 happy-path personas (Maria, Danny, Susan, Marcus) completed the full
7-state traversal: **6/6 `transition_to_*` (all `is_state_transition: True`)** + `query_livecall_slots`
(correct `slot_target_date = 2026-08-22`, i.e. injected `today` + 1) + `create_livecall_booking`
(real Cal.com booking) + `end_call`. All 4 bookings were **verified, cancelled, and leak-guarded
(`accepted left: 0`)**. Total cost 76.2¢ across 4 calls (15.8–22.3¢ each).

The config generalizes across 4 different verticals (dental, auto-repair, home remodeling, personal-injury law).
The earlier 6/6 PASS is reproduced — **not an accident.**

---

## Deploy Summary

| Artifact | Value |
|----------|-------|
| New chat agent | `agent_622d357f685e64b39426e75ca9` |
| New LLM | `llm_71ce39ed60b33447840865c8e356` |
| Model | gpt-5.1 |
| 9 KBs | CREATED once (registry empty + account at 0 KBs) → now reused on next deploy |
| KB registry | `MVP_agent/config/kb_registry.json` — 9 slug → `{kb_id, sha256}` |
| Config backups | `config/llm.json.v4.bak` (pre-deploy V4), `config/llm.json.v63.bak` (== working) |
| Harness `CHAT_AGENT` | `tools/test_llm_to_llm.py:18` → `agent_622d357f685e64b39426e75ca9` |
| Deployed LLM check | `get-retell-llm/llm_71ce…` → model gpt-5.1, transition line present, 9 `knowledge_base_ids` bound |

New 9 KB ids (registered): `are-you-ai-kb`→`…71aab631cdd971cd`, `call-closing-kb`→`…94768ac6f693507b`,
`call-context-kb`→`…019218768d83737f`, `discovery-bridge-kb`→`…a1b0229ab65f7e60`, `industry-kb`→`…93eda0f484aa984e`,
`pain-points-kb`→`…117022b3b40e884d`, `sales-language-kb`→`…d8f0a0284d202cb7`, `sales-psychology-kb`→`…ea0d9bd86b369e0f`,
`voice-ai-capabilities-kb`→`…b0b9c693d4790171`.

---

## Chat IDs to Check Later (deep-dive per call)

> Re-fetch any transcript with:
> `curl -s "https://api.retellai.com/get-chat/<CHAT_ID>" -H "Authorization: Bearer $RETELL_API_KEY"`
> Local transcript dumps are also in `MVP_agent/tools/json_logs/BOOK_chat_<cid>.json`.

| Persona | Chat ID | Local json_logs dump | Booking UID (cancelled) |
|---------|---------|----------------------|--------------------------|
| Maria (dental) | `chat_951eea621607faed5662388e41a` | `BOOK_chat_951eea621607faed5662388e41a.json` | `9VvVvaceKZYvqrQhChnoiL` |
| Danny (auto repair) | `chat_b38b357b527e854172b47cfe65b` | `BOOK_chat_b38b357b527e854172b47cfe65b.json` | `oo8td68GFepPWqUXR2n2F6` |
| Susan (home remodeling) | `chat_2ba0f66e1269da0edec47be3d26` | `BOOK_chat_2ba0f66e1269da0edec47be3d26.json` | `mQvoQP9DYAPEZCjCJCWy6e` |
| Marcus (law firm) | `chat_8a400ab8e9338a0a9c820868dce` | `BOOK_chat_8a400ab8e9338a0a9c820868dce.json` | `4iZZCsj8qhZR622QrFEu8j` |

---

## Per-Call Metrics

| Metric | Maria | Danny | Susan | Marcus |
|--------|-------|-------|-------|--------|
| Duration (s) | 148.0 | 90.0 | 89.1 | 102.4 |
| Cost (¢) | 15.8 | 18.4 | 19.7 | 22.3 |
| User turns | 10 | 12 | 13 | 15 |
| Agent turns | 11 | 13 | 14 | 16 |
| Tool invocations | 31 | 33 | 30 | 32 |
| Tool results | 24 | 26 | 23 | 25 |
| State transitions | 6 | 6 | 6 | 6 |
| Industry | dental practice | *(empty)* | HVAC & Home Services | personal injury law firm |
| Timezone | America/Chicago | America/Chicago | America/New_York | America/New_York |
| Slot `slot_target_date` | 2026-08-22 ✅ | 2026-08-22 ✅ | 2026-08-22 ✅ | 2026-08-22 ✅ |
| Booking time | 2026-08-22T10:45 | 2026-08-22T10:45 | 2026-08-22T13:30 | 2026-08-22T14:30 |
| Attendee phone | +1 312 555 1234 | +1 512 312 0001 | +1 303 915 0001 | +1 917 212 0001 |
| Monthly leak shown | $28,100/mo | $17,500/mo | $43,300/mo | $65,400/mo |
| Booking + end_call fired | True / True | True / True | True / True | True / True |

Leak calc consistency (weekly × ~4.33): Maria 6500×4.33≈$28,145 ✓, Danny 4050×4.33≈$17,536 ✓,
Susan 10000×4.33≈$43,300 ✓, Marcus 15119×4.33≈$65,465 ✓. All internally consistent.

---

## Tool Sequence (identical across all 4 personas)

```
extract_intake_details → intake_completed → transition_to_Discovery
  → extract_discovery_details → discovery_completed → transition_to_Closer
  → extract_leak_inputs → calculate_monthly_leak → extract_closer_details
  → closer_completed → transition_to_Offer
  → extract_offer_details → offer_completed → transition_to_contact_details
  → extract_contact_details → contact_details_completed → transition_to_Booking
  → check_current_date → query_livecall_slots
  → extract_booking_details → create_livecall_booking → booking_completed → transition_to_Closing
  → end_call
```

All 6 transitions verified with `is_state_transition: True` in `message_with_tool_calls`.

---

## Findings & Observations

### Confirmed working (the point of this re-test)
1. **6/6 transitions on every persona** — the edge-schema + lowercase `*_completed` flags +
   `"Then call transition_to_<dest> once the completion flag is set."` prompt line reproduce perfectly.
2. **Slot date injection** — `query_livecall_slots.slot_target_date == 2026-08-22` (= `today_date`
   `2026-08-21` + 1) on all calls. Correct tomorrow-relative behavior.
3. **Real booking** — `create_livecall_booking` produces a genuine Cal.com booking each time; all cancelled.
4. **Zero KB waste** — registry-based deploy created exactly 9 KBs once; account is no longer at the
   hundreds-of-KBs point.

### Data-quality issues worth a deeper look
1. **`first_name` variable = literal `"null"` on every call** (`collected_dynamic_variables.first_name == "null"`),
   and Marcus `last_name == ""`. Booking `name` reflects this:
   - Maria → `"null Gonzales"` (correct last name, first missing)
   - Marcus → `"null "` (both missing; trailing space)
   - Danny/Susan → correct `"Danny Reyes"` / `"Susan Park"` — so the booking tool sourced first name from
     somewhere the dynamic variable does not (or the var got overwritten mid-call). **Inconsistency to inspect**
     in the transcripts: where does `create_livecall_booking` read `name` vs where the `first_name` dynamic var
     is stored.
2. **`callback_number` stays `"null"` and `is_calling_best_number: false` on all calls** even though the
   attendee phone in the booking is correct. The booking phone is reliable, but the `callback_number` variable
   is not populated. Decide whether the tool should read a single canonical phone variable.
3. **Danny `industry == ""` (empty)** — auto-repair but the industry field is blank in `notes`
   (`"Industry:  |"`). The `discovery_completed` edge still fired with an empty `industry`, confirming empty
   strings satisfy the edge `required` check. If industry integrity matters downstream, the edge/prompt should
   require a non-empty value.
4. **All bookings use shared attendee email `jaydiallux@gmail.com`** — by design (single demo host),
   but every booked "prospect" share one email; fine for tests, flag if production needs distinct attendee emails.
5. **`inbound_channel`**: Maria=Facebook/Meta ad, Danny=Facebook/Meta ad, Susan=flyer, Marcus=other —
   the agent correctly honors the persona's stated source.

---

## Verification (booking hygiene)

| Step | Result |
|------|--------|
| Verify booking (GET) | All 4 `status: success`, real Cal.com event 3801235, correct times/zones |
| Cancel (POST) | All 4 `status: success` → `status: cancelled` |
| Leak guard (`accepted` count ≥ 2026-08-21) | **`accepted left: 0`** |

No test bookings leaked into the calendar.

---

## Files / Logs for Later Inspection

- Harness stdout: `/tmp/kilo/dialux_working_agent_maria.log`, `/tmp/kilo/dialux_working_agent_happy3.log`
- Fetched LLM: `/tmp/kilo/working_llm.json`
- Fetched transcripts: `/tmp/kilo/maria_chat.json`, `/tmp/kilo/chat_b38b357b527e854172b47cfe65b.json`,
  `/tmp/kilo/chat_2ba0f66e1269da0edec47be3d26.json`, `/tmp/kilo/chat_8a400ab8e9338a0a9c820868dce.json`
- Retell transcripts (persistent): `https://api.retellai.com/get-chat/<CHAT_ID>` (see Chat IDs table)

---

## Deferred / Not In This Run

- Doc updates (`iterations.md`, `STATE.md`, `AGENTS.md`) with the new agent/llm ids + results — only after user acceptance.
- Cleaning up the old V4 agent/LLM (`agent_1e90c63e…` / `llm_0fbb0ac6…`) — PT-26.
- `stress`/`all` persona runs (Carlos/Pedro/Sofia/Jorge/Daniel) — pending happy + happy3 acceptance.
- `notify_callback_telegram` placeholder URL fix — latent, not a transition blocker.