# Retell Testing API — Research Notes (from Tech Tomlet video)

> Source: "How I Build AND Test Voice Agents with Claude Code (Retell AI)" by Tech Tomlet, published 2026-03-21. URL: https://www.youtube.com/watch?v=U3vJIOlFKBA
>
> **Important caveat:** This file documents what's described in the video transcript. The actual Retell API endpoints, parameters, and SDK calls are NOT in the transcript — Mark keeps those in his free Voice AI Starter Kit (Google Drive folder linked below). Before implementing any of this, verify against Retell's official docs or Mark's Starter Kit.

---

## The Big Idea

Retell quietly released a testing API that completes the development loop. Combined with Claude Code, you can:

1. Build the agent (Claude Code writes the prompt, configures tools, deploys via API)
2. Test the agent programmatically (no dashboard needed)
3. Find issues automatically
4. Fix the prompt
5. Redeploy and retest
6. Repeat until rock solid

This is the missing piece. Before this, you could build with Claude Code but you had to manually test in the Retell dashboard. Now the whole loop is automated.

---

## Three Testing Methods (ranked by quality)

### 1. Chat-Based Testing (Best)

- Clone the voice agent to a chat agent via API
- Claude Code tests it directly, turn-by-turn, with full context of how the agent was built
- Delete the chat agent after testing
- Same LLM brain, same prompt — only the interface changes
- **Why it's best:** Claude has the full context of the agent's design, so it knows where to probe for weak points. A context-unaware LLM (used in batch testing) misses subtleties.

### 2. Batch Simulation Testing (Wide Net)

- Spin up N parallel scenarios (10, 50, 100+)
- Each scenario is a different caller persona / situation
- Get pass/fail rates across the board
- Good for finding broad patterns of failure
- **Why it's weaker:** The LLM grading the responses doesn't have the agent's context, so it can miss nuanced failures or grade incorrectly.

### 3. Python Scripts (Edge Cases)

- For specific, surgical tests
- Less preferred — Claude direct testing is better when you have the time

---

## The Bullseye Framework

```
Build → Test → Find issues → Fix prompt → Redeploy → Retest → Repeat
```

Mark's analogy: Claude Code used to be like an archer who could shoot and hit the bullseye but couldn't see where the arrow landed. Now with testing, it can see where it landed and recalibrate.

The recalibration loop:
1. Test reveals an issue (e.g., "agent skipped greeting when caller opened with a pricing question")
2. Claude Code applies a prompt fix based on its trained knowledge of how to fix that class of issue
3. Retest the specific scenario
4. If passes, run regression on ALL scenarios to make sure nothing else broke

---

## The 10-Reps Rule (Critical)

**A single passing test means nothing.** LLMs are probabilistic — a fix that works once might fail 3 out of 10 times.

- **Minimum for confidence:** 10 regenerations of the same test, all must pass
- **Mark's SOP default:** 3 reps (to save tokens) — explicitly acknowledges this is a compromise
- **For surgical fixes:** Manually tell Claude Code to run 10 reps on the specific issue

This is the single most important testing principle in the video. Without it, you ship fixes that look good but fail in production.

### Why Retell's API limits this

Mark mentions (around 11:31): "Retell AI doesn't expose this debug functionality as an API to regenerate the answer 10 times." So you can't regenerate at a specific turn — you have to rerun the entire chat. Mark asks Retell to expose this in the future.

**Workaround:** Run the full chat conversation 10 times instead of regenerating at a specific turn. More tokens, but works.

---

## The Testing SOP (5 steps, from Mark's Starter Kit)

1. **Build** the voice agent with Claude Code
2. **Test** using chat-based testing directly from Claude Code (text-based)
3. **Fix** the prompt, redeploy, iterate
4. **Retest** until ironed out
5. **Clean up** — delete temporary chat agents

### The Chat Agent Workaround

Retell doesn't expose direct chat testing on voice agents. The workaround:
1. Clone the voice agent via API
2. Convert the clone to a chat agent (same LLM, same prompt)
3. Test via chat API
4. Take the latest, greatest version and apply it back to the voice agent
5. Delete the chat agent

Mark hopes Retell opens this up directly in the future, but for now it works.

---

## Workflow Walkthrough (from the video)

### Phase 1: Scenario Inventory (Wide Array Testing)

- Claude Code spins up multiple sub-agents
- Each tests a different scenario
- Goal: find any broad areas of failure
- Example: 16 scenarios, 14 passed, 2 issues found

### Phase 2: Issue Analysis

For each failure, Claude Code gives:
- The specific scenario that failed
- What went wrong (e.g., "agent skipped greeting name collection when caller opened with a pricing question")
- The full transcript of the failed conversation

Example issues found in the video:
- "Price shopper labor rate leak" — agent went straight to objection handling without asking "who am I speaking with"
- "Hallucination on custom work" — agent got stuck in a loop
- "DOT inspection" — took 3 asks before agent acknowledged they offer DOT inspections

### Phase 3: Surgical Fix

- Pick one issue
- Tell Claude Code to test it directly (no Python scripts) for surgical precision
- Run 3 reps to confirm the issue is reproducible
- Apply prompt fix
- Redeploy
- Run 10 reps to confirm the fix is rock solid

### Phase 4: Regression Test

- Rerun ALL scenarios on the fixed prompt
- Make sure nothing else broke
- Claude Code gives a regression scorecard (X passed, Y failed)

### Phase 5: Repeat

- Go through every failed scenario
- Fix each one
- Run 10 reps each
- Optional: "throw everything at the agent" — 50+ scenarios, batch + chat + Python, let it run for 5–7 hours

---

## Dynamic Variables in Testing

If your agent uses dynamic variables passed at the start of the call (e.g., `{{customer_name}}`, `{{caller_phone_number}}`), Claude Code can simulate those via API:

1. Tell Claude Code: "Here are my dynamic variables. Notice exactly how my server sends them to Retell AI."
2. Claude Code injects them at the start of the test call via API
3. Test proceeds as normal

Critical for agents whose success depends on dynamic variables being used correctly.

---

## Knowledge Base Adherence Testing

Specific use case: test whether the agent answers questions correctly using the linked KB.

- Spin up 10 batch testing agents
- Success criteria: "did the agent answer the question correctly per the KB?"
- Run them, get pass/fail rates
- Pull transcripts for failures
- Have Claude Code analyze why they failed

Mark uses this to verify KB retrieval is working as expected.

---

## Token Cost Warning

Mark explicitly calls this out: "We are using quite a few tokens here. So if you're not on the higher echelons of these plans, you might hit your limits pretty quick."

Rough math: 16 scenarios × 3 reps × regression runs × 10-rep surgical fixes = easily 100+ test calls per iteration cycle. On Claude Code's higher plans, this is fine. On lower plans, you'll hit limits.

---

## What's Missing from the Transcript

The video describes the workflow but doesn't include:

- The actual Retell API endpoints for:
  - Creating a chat agent from a voice agent
  - Sending chat messages to a chat agent
  - Retrieving chat transcripts
  - Deleting chat agents
  - Triggering batch simulation tests
  - Retrieving batch test results
- The exact JSON shape of success criteria
- The Python script templates
- The default settings JSON
- The prompt-fix ruleset Claude Code uses

**All of these live in Mark's free Voice AI Starter Kit:**
https://drive.google.com/drive/folders/1oH4eVQ5CYqexn4nvipNKlSuQZDQx7KuF

---

## How This Applies to Our HVAC Demo

This testing framework is exactly what we need to take the HVAC agent from "sounds good in the playground" to "won't embarrass you in front of a paying customer."

### Specifically for our use case:

1. **Build** the agent using `single_prompt_v2.md` + the two KBs
2. **Scenario inventory** — write 15-20 HVAC-specific scenarios:
   - Cold boiler breakdown, new customer
   - Returning customer, annual service
   - Customer spells postcode phonetically
   - Customer asks about the fee mid-booking
   - Customer changes their mind mid-call
   - Customer rambles about boiler history
   - Customer asks "is this an AI?"
   - Customer gives a non-UK postcode
   - Customer doesn't know their postcode
   - Customer wants a specific engineer
   - Customer is elderly and confused
   - Customer asks about repair cost
   - Customer mentions gas smell (should redirect)
   - Customer mentions headache (should NOT redirect)
   - Customer gives house name instead of number
   - Customer picks the first slot offered
   - Customer rejects 2 slot offers
   - Customer tries to book a heat pump quote
3. **Run chat-based testing** via Claude Code, 3 reps each
4. **Find issues** — likely candidates:
   - Postcode hyphenation rule breaks under pressure
   - Agent skips name capture when caller opens with pricing
   - Agent offers more than 2 slots at once
   - Agent forgets to confirm address before booking
   - Agent quotes fee proactively when it shouldn't
5. **Surgical fixes** — 10 reps each on the specific failures
6. **Regression test** — rerun all 18 scenarios on the fixed prompt
7. **Ship to demo** only when 10/10 reps pass on every scenario

### Cost-benefit for our £3-4k sale

- 18 scenarios × 3 reps × ~2-3 iteration cycles = ~150-200 test calls
- At Claude Code's token cost, probably £20-50 in inference
- Time: 2-4 hours of Claude Code running
- ROI: turns a "probably works" demo into a "won't embarrass you" demo

For a £3-4k sale, £30-50 in testing tokens is a no-brainer.

---

## Action Items

1. **Download Mark's Starter Kit** from the Google Drive link above
2. **Verify against Retell's official docs** — the testing API may have evolved since March 2026
3. **Write the HVAC-specific test scenarios** (15-20 cases)
4. **Run the testing SOP** against `single_prompt_v2.md` before the demo
5. **Document the actual API endpoints** we use (separate file) once verified

---

## Sources

- Video: https://www.youtube.com/watch?v=U3vJIOlFKBA
- Mark's Voice AI Starter Kit: https://drive.google.com/drive/folders/1oH4eVQ5CYqexn4nvipNKlSuQZDQx7KuF
- Retell AI docs (testing section — to verify): https://docs.retellai.com/
- Retell AI testing video by Mark (mentioned in transcript): watch his earlier Retell AI testing video for batch testing details
