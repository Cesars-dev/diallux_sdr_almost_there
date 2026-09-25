# SKILL.md — Build an SDR Agent (State-Machine Architecture)

> Reverse-engineered from the Dialux SDR program (V6.0 -> V7.5_lean, final production grade
> `agent_edf1437704e976c53539c7effe`). This is THE BUILD. Swap niche/script = edit **3 states +
> 2 KBs**; everything else is copy-exact machinery.
> Reference implementation: `V7.5_lean/` - treat it as the canonical source to clone.

---

## 0. Doctrine (never violate)

1. **States follow structure; craft lives in the retrieval layer.** Sales psychology, objection
   language, punch lines -> KBs. State prompts = procedure only. Rewriting state prose to be
   "better at sales" breaks the machine (proven: V7.1 regression).
2. **Machine truth gate.** A booking exists only when a server-side endpoint writes a success
   boolean into dynamic variables (`slot_verified`). The prospect saying "book it" is intent,
   not a booking.
3. **Never patch a live LLM.** Every iteration = new llm_id + agent_id. Folder name = display name.
4. **KB registry.** Reuse by slug+sha256, upsert same id on content change, create only when new.
5. **One variable per iteration**, then run the acceptance ladder before keeping it.
6. **Hard constraints beat long constraints.** One `# CRITICAL CONSTRAINTS` block in main,
   bold NEVERs. Discipline also comes from model tier - gpt-5.2-class models obey; weaker models
   improvise under pressure regardless of prompt.
7. **No exit hatches.** Never give the model permission to stop ("two declines -> wrap up").
   Binary outcomes only: booked or prospect leaves.

---

## 1. The fixed skeleton (copy-exact, 8 states)

```
Intake -> Discovery -> Closer -> Offer -> contact_details -> ConfirmSlots -> Booking -> Closing
```

| State | Role | Niche-dependent? |
|---|---|---|
| Intake | channel, interest, name/company | **script only** (channel list) |
| Discovery | bridge their topic -> phone-gap pain | **YES - niche pain logic** |
| Closer | quantify leak, value-prop punch | **YES - niche math + rows** |
| Offer | assume the demo, get commitment | generic |
| contact_details | name / company / tz / number | generic |
| ConfirmSlots | date -> slots -> validate gate | generic |
| Booking | create booking -> verify -> outcome record | generic |
| Closing | confirm, warm goodbye, end_call | generic |

**Niche swap = edit Discovery.md + Closer.md (+Intake channel wording) + industry-kb +
pain-points-kb. Nothing else.**

---

## 2. State prompt spec (template for every state)

```
# Context you have
{{vars carried in}} - one line

# Your Mission
1-2 sentences. What this stage is FOR.

# Conversation Flow
### 1..N steps
ONE QUESTION AT A TIME. Examples in < > are patterns to vary, never read verbatim.

# Extraction reference          <- exactly ONE block, never repeat capture rules
- Immediate: {{var}} ... (only what changes what you ask next)
- Completion: all required vars listed once

# Critical Rules
- Mirror their words; APPEND semantics for accumulating vars
- Stage boundaries (what NOT to do here - e.g., never schedule outside ConfirmSlots)
- The call never ends here (except disqualification handling)

# Completion flag
When done -> call `<stage>_completed`. Then call `transition_to_<Next>` once flag is set.
```

Learned the hard way:
- State totals (main+state+tools) <= ~3.4k tokens; early states <= 2k.
- Stating a rule twice makes the model perform theater (100 empty extract calls came from a
  triple-stated capture mandate). Say it once.
- Edge gates carry the data: `transition_to_X` args include every var the next state needs.

---

## 3. Main general_prompt spec (<= ~1.1k tokens)

Owner-owned sections: Identity / Personality & Style / Voice / What you're doing /
Call Context / When to use each KB / Language Rules / Are You AI / Ending the call.
No tool instructions in main except `end_call`. Then exactly ONE constraints block:

```
# CRITICAL CONSTRAINTS - override everything
- **NEVER claim a booking or say "you're set/confirmed" unless a booking tool returned success this call.**
- **NEVER promise a call-back, email, text, or link - there is no callback team.**
  Can't book? Offer another slot. Tool failed? Say the calendar's having trouble and offer another time.
- **NEVER invent details - names, numbers, phones, emails, prices.** Use only what they actually said;
  a missing figure means ask, not guess.
- **NEVER let rush, anger, objections, or tangents skip stages.** Acknowledge in one line,
  answer directly, return to the stage's next question.
- **NEVER speak machine language** - no JSON, function names, variables, { } [ ].
```

---

## 4. Tool architecture per state

| State | Tools |
|---|---|
| every state | `extract_<stage>_details` (extract_dynamic_variable), `<stage>_completed`, `transition_to_<Next>` (edge tool carrying data args) |
| Closer | + `extract_leak_inputs`, `calculate_monthly_leak` (JS code tool, floor-round) |
| ConfirmSlots | + `check_current_date` (custom time endpoint), `query_livecall_slots` (custom slot webhook), **`validate_lead` (custom validator)** |
| Booking | `create_livecall_booking` (Cal.com, cal_fields pinned), `record_booking_uid`, `validate_booking`, `record_booking_outcome` |
| global | `end_call` |

### The gate (the crown jewel) - `/validate_lead`
- FastAPI service, HMAC multi-key auth, deployed behind Caddy (`/validator-function/*`).
- Input: close_rate_percent, weekly volume proxy, avg deal value, callback_number, timezone, company_name.
- Parsing: fuzzy first-number extraction, word-numbers, phone digit-extraction to E.164,
  money floor-rounded to 2 significant figures, timezone aliases.
- Verdict JSON -> Retell writes machine-truth boolean into dv via response_variables
  (**note:** Retell posts `{args:{...}}` when `args_at_root=false` - endpoint must unwrap).
- Edge ConfirmSlots->Booking requires `slot_verified=true`. No boolean, no booking. Ever.

### Custom endpoints are reusable across niches - build once:
1. time endpoint (`/today`) - parses Retell calendar context into YYYY-MM-DD
2. slot webhook - Cal.com availability for event type X
3. validator - the gate above

---

## 5. Knowledge bases (8)

call-context-kb · sales-language-kb · pain-points-kb · sales-psychology-kb · industry-kb ·
voice-ai-capabilities-kb · call-closing-kb · are-you-ai-kb

- Routing lives in main as one-liners (`##kb-slug##` markers).
- Craft sections (Loss Playback, Flip & Second Shot, Punch-Line Bridge) live in sales-psychology-kb
  as PATTERNS NEVER SCRIPTS. Retrieval-safe: no `<...>` wrappers, placeholders in prose form.
- Niche swap = rewrite industry-kb rows + pain-points-kb angles. Other 6 KBs stay.

---

## 6. Model config

gpt-5.2 · temperature 0.1 · model_high_priority false (validated: tier does not cause bypasses;
broken prompts do). Cheap tiers ramble more and obey less - pay for discipline.

---

## 7. Build & deploy SOP

1. `cp -r V7.5_lean <NewName>` ; edit the 3 niche files + 2 KBs.
2. `python3 tools/build_llm_json.py` (parity check must pass).
3. `python3 deploy_v68.py` (KB registry reuse/upsert enforced - never hand-create KBs).
4. Snapshot deployed payload into the folder (`DEPLOYED_llm_snapshot.json`) + note ids.
5. Acceptance ladder: first-12 regular personas async -> all designed outcomes correct, zero
   bypasses -> then 11 stress personas -> zero false commitments. Cancel all test bookings.
   Harness lives in `Dialux_SDR/testing/` (`runners/reg_one.py`, `runners/adv_one.py`,
   transcripts in `testing/json_logs/`).
6. Analyze per the three SOPs (CALL / SALES / HUMANIZED) before promoting.

## 8. Failure modes catalog (what we paid to learn)

| Symptom | Root cause | Fix |
|---|---|---|
| Agent verbally "books", promises callbacks/emails | Role-play gravity under frame-grabbing personas | CRITICAL CONSTRAINTS block + strong model |
| Sales upgrade breaks funnel | Craft written into state structure | Craft -> KB patterns only |
| Empty extract spam / latency | Capture mandate stated repeatedly | One extraction block per state |
| Fabricated fallback ("ignore the confirmation") | Lying failure script in prompts | Honest single retry -> another slot |
| Hallucinated PII passing gates | Model invents plausible data | NEVER-invent constraint + validator re-checks |
| Bypass epidemic after manual edits | Weakened extraction mandates in Intake/Discovery | Restore from deployed snapshot; edit via procedure |

## 9. Token budget target (o200k)

main <= 1100 · early states total <= 2000 · heavy states <= 3400 · customs schemas are sacred -
compress prose, never descriptions that encode behavior.

## 10. Self-hosted functions & runtime hygiene

- All custom tools are OUR services on MainVps (systemd user units), behind Caddy
  `https://slots.diallux-ai.site`: time :8002 `/time-function/*` · validator :8003
  `/validator-function/*` · slot webhook. Caddy routes = runtime injection via admin API
  (127.0.0.1:2019) - re-inject if Caddy restarts.
- Booking chain: create -> record_booking_uid -> validate_booking -> record_booking_outcome.
  Fallback doctrine: failed calendar tool = ONE honest line + offer another slot. No callbacks,
  no emails, no SMS promises.
- Known platform quirk ("the '' bug"): Retell extract_dynamic_variable tools fire with empty args;
  data actually rides the transition edge args. Accepted for now; cleanup candidate for early states.
