# NEXT_STEPS — the live queue (one item at a time)

> Updated: 2026-09-17 (later) — iter54-assessment session.
> Previous queue (HVAC V3 polish, 2026-08-01) → `plans/archive/NEXT_STEPS_hvac-2026-08-01.md`.

> **NAMING CONVENTION (owner decision 2026-09-17 — applies going forward):**
> `iter<N>` = a CODE iteration (branch + commits + battery). A PLAN is a plan — it does
> not own an iter number. Historical drift to keep straight when reading old docs:
> iter43 = real branch, ABANDONED (`engine/iter43-eot-cache-askgate`, tag `iter43-failed`);
> iter44 = real branch (`engine/iter44-cache-floor`); plan FILES named `plan_iter43_*` /
> `plan_iter44_*` are their plans (missing the `v5_` prefix — cosmetic). `mvp-finally`
> was deliberately NOT iterNN-numbered ("iterations = commits"). iter55 follows the
> convention: one iter = one plan = one branch. (Formal note rides
> `engine/ITERATIONS.md` on the next branch closeout — do not hand-edit it on main,
> the iter52 branch carries its newest version.)

## NOW

> Updated: 2026-09-23 (iter67 Twilio lane session — T1–T5 done, phone endpoint LIVE).

0. **RESUME `plans/plan_v5_iter67_twilio_resume_t6_t7.md` — iter67 Twilio lane is LIVE on the VPS** (`https://twilio.diallux-ai.site`, systemd :8026, signature gate on, suite 434). Next: T6 repoint `+18885958927` → the engine (owner say-so: "repoint") → T7 owner-ears call + ledger + report. Branch `engine/iter67-twilio-live-lane` @ `0394a3b` pending merge (T8, after iter66 merges first).
1. **EXECUTE `plans/plan_v5_iter55_tts_era_turn1_ammo.md`** (owner GO pending):
   production-era truth + turn-1 "ammo locked" landing. Finds in one session:
   (a) the live :8000 engine runs **iter40-era code — the cache machine never
   shipped** (verified: zero `prompt_prewarm`/`first_turn_lite` in the deployed
   config); (b) warm-completion time is measured NOWHERE (zero spans) — T0 adds
   warm + greeting spans; (c) owner gates are HARD: first 3-4 turns TTFT ≤900 ms,
   worst case TTFT ≤1,100 / hear ≤1,400 ms; (d) sequence: T0 spans → warm p90
   table → O5 (tail shrink) → turn-1 full-round probe (`FIRST_TURN_LITE=false`)
   → fallback "one moment, taking notes" ONLY if misses remain (default OFF).
   Supersedes `plan_v5_iter54_turn1_cache_landing.md` (its O1-O5 menu collapsed:
   O3/O4 dead under the 1,100/1,400 gates; O1 direction owner-confirmed, gated on T0).
2. **Julio — merge ASK: `engine/iter52-industry-pin` @ `a36bdd7`** (ONE clean commit:
   iter52 feature + docs + LAW 0 v3 + Mike Rourke persona; suite 333 green ×2 modes;
   battery-iter52 4/4 + plumber A/B PASS). Branch verified conflict-free vs main
   (`merge-tree` exit 0). Standing ASK since 2026-09-16. (iter55 cuts from this branch's
   HEAD `054af7b` regardless — merge order is owner's call.)
3. **HITL — owner decisions iter55 needs (no agent answer exists):**
   - Real-path test level: browser mic-bridge battery only, or + one REAL Twilio test
     call (test number + webhook change; production agents untouched).
   - "One moment, taking notes" filler copy approval (T6, only if misses remain).
   - Turn-1 EOT wait ceiling: keep 500 ms or raise (decide AFTER T0 warm numbers).
   - warm_rag / KB-resolve keep-drop-reorder at call start (owner directive: NO KB
     loads before/at the lite turn; physics check: warm_rag is async but feeds the
     turn-2 first heavy round's embed — measure with T1 greeting span, then decide).
   - **Cutover authorization** — the endgame ASK: the deployed :8000 has never run the
     cache machine; the lab evidence is meaningless to production until it ships.
4. *Previous top item:* ~~Julio — Phase B engine-owned state machine~~ (still parked,
   `phaseB-wip` stash — superseded in priority by the ASKs above).

## NEXT (owner-gated — nothing happens without Julio's word)

- **Services cutover to the fork's engine** — the item behind ALL the latency work:
  the deployed engine is iter40-era, so every lab gain (lite head, warms, await split,
  RAG lanes, industry pin) is invisible to real callers until cutover.
  MIGRATION_MAP.md checklist; real-path validation rides iter55 T2.
- ~~**Merge iter29 → iter30 → iter31-c3d stack into `engine/main`**~~ STALE
  (superseded 2026-09-16: main @ `4559a33` = the MVP merge of `engine/mvp-finally`
  cut from `engine/iter49c-engine-finish` — that stack is already in main).
- ~~**Cut iter32**~~ STALE (superseded by iters 33-52; the "gen-p50 ≤1.2s prefix work"
  it carried landed via the iter43-48 cache work; Pedro over-book guard + Phase B
  remain parked, re-triaged on their own merits).
- **iter53 hygiene plan** (`plans/plan_v5_iter53_git_hygiene_rag_next.md`, parked at
  ref label `engine/docs-archive/fec12dd-plan53`) — docs-only, T1–T7 unexecuted,
  independent of iter55; schedule = owner's call.

## OWNER GitHub actions (agent cannot)

- [ ] Delete stray repo `Cesars-dev/scope-test-nonexistent` (empty; token lacks delete scope)
- [ ] Rotate the V7.9 PAT burned in the ORIGINAL repo's `.git/config` (see PENDING_TASKS security ledger)
