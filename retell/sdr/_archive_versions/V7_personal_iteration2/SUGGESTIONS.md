# V6.6 — FINDINGS & QUEUED FIXES (SUGGESTIONS)

> Created: 2026-08-23, post 4-persona happy-path gauntlet.
> All items here are OUT of the deployed V6.6 scope — nothing applied without explicit approval.
> Test evidence: `6.1 iterations/MVP_agent/tools/json_logs/BOOK_chat_{3793f892,50ea57ec,404349c9,d1933bbe}*.json`
> Deployed build: `agent_df7d1aa32ead7256ce65885610` / `llm_6adc5ef97e7affe7d0daa387ccfa`

---

## P0 — correctness bugs (server-side fixes, no prompt surgery)

### 1. `""` penetrates edge `required:` gates — CONFIRMED LIVE (Susan run)
`first_name=""`, `last_name=""` yet `transition_to_Booking` fired; agent improvised
booking name "Cornerstone Owner" and a real Cal.com booking was created under it.
Retell treats empty string as populated for edge requirements.
**Fix options (decide one):**
- a) Strip `""` seeds from `default_dynamic_variables` for all edge-gated vars (keep seeds
  only for vars interpolated into spoken prompts).
- b) Booking webhook rejects bookings whose `name` is empty/generic placeholder
  (`{ok:false, reason:"missing_name", say:"Sorry — what name should I put this under?"}`).
- c) Both. (Recommended.)

### 2. Extractor wrote a KB taxonomy label into `{{industry}}` (Marcus run)
Stored `"Private Clinics (Urgent Care, Physical Therapy, Chiropractic)"` for a personal-injury
law firm — an industry-kb section title, not the prospect's words.
**Fix:** tighten `extract_discovery_details.industry` description: "the prospect's OWN words,
2-4 words max, plain trade name (e.g. 'law firm', 'dental practice'). Never a category list,
never KB phrasing."

### 3. Dynamic-variable blindness → redundant tool spam (all 4 runs)
The LLM cannot READ current variable values — it can only populate/inject them. Evidence:
34 tool invocations per ~12-turn call; `extract_contact_details` ×2-3 with identical payloads,
`extract_booking_details` ×2-3 (once pre-booking with `confirmed:false`),
`extract_leak_inputs` ×3, `calculate_monthly_leak` ×2, `extract_contact_timezone` ×3.
Every "CHECK {{var}} — if set skip" instruction is unfalsifiable for the model.
**Fix direction:** accept redundancy as harmless-but-costly OR move gating reads server-side
(webhooks know their own state). Do NOT add more "check first" prose — it cannot work.

---

## P1 — naturalness (robotic tail) — all 4 runs, concentrated in Booking/Closing

| Symptom | Evidence | Fix (prompt edit, small) |
|---|---|---|
| Double-echo of day/time/zone | "Perfect, I'll lock in tomorrow at 1:45 PM Central…" THEN "You're all set for tomorrow at 1:45 PM Central — I've locked in…" | Result step becomes short human ack: <Done — you're booked.> No second restatement |
| Cal.com feature recital | "You'll get a text in a moment with the confirmation details — you can add it to your calendar or reschedule…" ×4 near-verbatim | One casual clause max: <Text's on its way.> Kill the feature list |
| Timezone repeated after confirm | "tomorrow at 11:30am Central", "Monday at 3:30 in the afternoon Eastern" in EVERY line | Zone spoken ONCE at confirmation, then dropped |
| "with Jay" injected by agent in 4/4 booking lines | "I'll lock in 11:30am Central for you with Jay" | Remove from templates; Jay surfaces only when prospect asks who |
| Opener monotony | "Got it" = #1 opener in all 4 calls (Danny ×6); Got/Perfect/Nice rotation | Add explicit banned-opener streak rule: never open two consecutive replies with the same word |
| Identical closing question | "Is there anything else I can help you with before we hop off?" word-identical ×3 | Give 3 interchangeable variants in Closing.md; require paraphrase |

Note: Discovery/Closer speech scored natural (mirrors, contractions, pauses land).
Do NOT touch those prompts for tone.

---

## P2 — process / ops

- **4 real bookings await cancellation** on Cal.com event `3801235`
  (uids: `gJAAt5yp5YRwbVzC28wXJ3`, `1c87ryw8iUM829D7zWBMD1`, `fZcrkDF3g9trguXoAQyAFT`,
  `dCMVRG8sQjhDHN9dCR8smV`). Cancel endpoint returned BadRequest with v2 `2026-02-25`;
  needs correct endpoint/version check against `docs/api/cal.com` before next test cycle.
- Maria + Marcus: timezone captured via city inference WITHOUT the yes/no confirm ritual.
  Consider one line in contact_details §5: "Even when you're sure, confirm once."
- Harness improvement (queued): offline rules engine (`verify_run.py`) asserting
  slots-honesty, E.164 phones, tz-confirm-before-book, end_call gating, transition liveness.
- `working_agent/README.md` references dead agent id `agent_74b34a77…` (404 on new account);
  live V6.5 is `agent_514a7af07acf4a407c76f486ce`. Root docs disagree — consolidate.
- Old duplicate chat agents + the deprecated `Linda AI V2 enhanced` builds: cleanup pass
  (PT-26 lineage) once V6.6 declared good.

## Deployed-artifact registry (this session)

| Build | Agent | LLM |
|---|---|---|
| V6.5 (live, documented) | `agent_514a7af07acf4a407c76f486ce` | `llm_1b72cf559f873043eb5130815dcc` |
| V6.6 rev1 | `agent_b753bd8f45a5a455c0d890a1d4` | `llm_c95be9b4328d8d7cd7df7d66c1b4` |
| **V6.6 rev2 (current, tested 4/4)** | `agent_df7d1aa32ead7256ce65885610` | `llm_6adc5ef97e7affe7d0daa387ccfa` |
