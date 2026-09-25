# 04 — MASTER PLAN — iter64 `industry-gate` (AIRTABLE-READY FOR EXECUTION)

Status: **AWAITING OWNER APPROVAL TO EXECUTE** (surgeon step-5 gate — user said STOP AT MASTER PLAN)
Supersedes: `plans/plan_v5_iter64_industry_gate.md` where the surgeon audit/cross-ref found flaws (AUD-1..AUD-7, PF-1 — see §7). A fresh agent can execute from THIS file alone.
Source docs: `archive/01_audit.md`, `archive/02_action_plan.md`, `archive/03_cross_reference.md` (same folder).

## 0. Identity

- Base: `2cb810f` = tip `engine/iter63-rag-fire-sim` (worktree `/tmp/opencode/wt-iter63` verified at that sha; baseline suite **425 passed** re-verified there 2026-09-22, 76.75 s).
- New branch: `engine/iter64-industry-gate` cut from `2cb810f`; worktree `/tmp/opencode/wt-iter64`.
- Goal: gate the shared `industry` KB OUT of all LIVE retrieval scopes until the vertical is KNOWN (pin resolved OR industry dv extracted) — kills the pre-pin wrong-vertical sweep (Susan t3/t4 plumbing, Marcus t5 dental→law, Maria t4 derm/cleaning/security, Danny t6 plumbing/MSP). Pin path, trigger path, kill-switch path byte-identical.
- Hard laws: NO touch of `diallux/media/*` (session.py, deepgram_stt.py, prewarm.py), prompts, `.env`, RAG settings (0.24/12/60/3/1600), `tests/llm2llm/harness.py`, `:8021` (pid 3834955, wt-iter62 — NO restart; iter62 mic gate surface), `:8020`, ports 8000–8003, live agent IDs. NO merges, NO tags. Commits only on the branch after gates green. `.env` never committed. Owner ASK at the end (LAW 0).

## 1. Exact code edits (all in `/tmp/opencode/wt-iter64/engine/`, line numbers verified @ `2cb810f`)

### E1 — `diallux/graph/builder.py` · `build_lanes` lines 1126–1135 — pre-pin gate inside the kill-switch block
```python
# BEFORE
        if pinned_tag:
            scope = [s for s in scope if s != "industry"]
        if getattr(self.settings, "rag_pin_industry", False):
            industry_norm = str((dvs or {}).get("industry") or "").strip().lower()
            if industry_norm:
                for kw, extra_kbs in _INDUSTRY_KB_TRIGGERS.items():
                    if kw in industry_norm:
                        for kb in extra_kbs:
                            if kb not in scope:
                                scope.append(kb)
# AFTER
        if pinned_tag:
            scope = [s for s in scope if s != "industry"]
        if getattr(self.settings, "rag_pin_industry", False):
            # iter64: pre-pin gate — the shared `industry` KB leaves the
            # scopes until the vertical is KNOWN (pin resolved or the
            # industry dv extracted); generic pre-pin turns cross-matched
            # every vertical's pain/ROI prose (iter63 battery: Susan t3/t4,
            # Marcus t3/t5, Maria t4, Danny t6). The pin block re-introduces
            # the vertical the moment it resolves.
            if not pinned_tag \
                    and not str((dvs or {}).get("industry") or "").strip():
                scope = [s for s in scope if s != "industry"]
            industry_norm = str((dvs or {}).get("industry") or "").strip().lower()
            if industry_norm:
                for kw, extra_kbs in _INDUSTRY_KB_TRIGGERS.items():
                    if kw in industry_norm:
                        for kb in extra_kbs:
                            if kb not in scope:
                                scope.append(kb)
```
Covers laneB (1165), middle-mode lane (1142), Closing anchor (1149); freed mechanical states via the `kb_slugs_for` general-union fallback. Multiquery laneA per-tag scopes (1158) never see `scope`. Trigger block untouched (fires only when the dv is non-empty — disjoint from the gate).

### E2 — `diallux/graph/builder.py` · `_retrieve_raw` laneB lines 1198–1204 — same gate, reuse `industry`
```python
# BEFORE
            if len(msg) >= int(getattr(self.settings, "rag_min_query_chars", 0)):
                industry = str(dvs.get("industry") or "").strip()
                q = f"{msg} (their industry: {industry})" if industry else msg
                scope = [s for s in self.kb_slugs_for(state_name)
                         if not (pinned_tag and s == "industry")]
                lanes.append({"query": q, "scope": scope})
                owned.append(set())       # lane B owns nothing: quota applies
# AFTER
            if len(msg) >= int(getattr(self.settings, "rag_min_query_chars", 0)):
                industry = str(dvs.get("industry") or "").strip()
                q = f"{msg} (their industry: {industry})" if industry else msg
                scope = [s for s in self.kb_slugs_for(state_name)
                         if not (pinned_tag and s == "industry")]
                # iter64: pre-pin gate — same rule as build_lanes; pinned
                # and dv-known rounds are byte-identical to iter63.
                if getattr(self.settings, "rag_pin_industry", False) \
                        and not pinned_tag and not industry:
                    scope = [s for s in scope if s != "industry"]
                lanes.append({"query": q, "scope": scope})
                owned.append(set())       # lane B owns nothing: quota applies
```

### E3 — `scripts/rag_replay.py` lines 89–98 — mirror the gate in the replay SDK (PF-1, REQUIRED for the T8 verdict)
Without this, the replay reconstructs pre-pin pools WITH industry in scope → false "wrong-vertical still present" verdicts on a correct fix.
```python
# BEFORE
            pinned_tag = o.get("pinned") or ""
            scope = [s for s in rt.kb_slugs_for(state) if s != "industry"] \
                if pinned_tag else rt.kb_slugs_for(state)
            norm = (industry or "").strip().lower()
# AFTER
            pinned_tag = o.get("pinned") or ""
            scope = [s for s in rt.kb_slugs_for(state) if s != "industry"] \
                if pinned_tag else rt.kb_slugs_for(state)
            # iter64: mirror the engine's pre-pin gate — industry leaves the
            # reconstructed scope until pinned OR the industry dv was known
            # (parsed from the laneB query anchor below/above).
            if not pinned_tag and not (industry or "").strip():
                scope = [s for s in scope if s != "industry"]
            norm = (industry or "").strip().lower()
```
(The `_INDUSTRY_KB_TRIGGERS` append at 95–98 stays after it — trigger only fires when `norm` non-empty, disjoint.) Script only — NOT collected by pytest; suite count unaffected.

## 2. Existing-test rewrites — `tests/test_iter49_rag_parity.py` (4 assertions, 2 functions; count-neutral; documented deviation — the plan's "zero test edits / 425 passes untouched" was FALSE, AUD-1)

### R1a — line 263, in `test_build_lanes_lane_a_query_format_and_scope`
```python
# BEFORE
    assert lanes[-1]["scope"] == rt.kb_slugs_for("Intake")
# AFTER
    # iter64: pre-pin (no industry dv, no pin) — industry gated out of scope
    assert "industry" not in lanes[-1]["scope"]
    assert lanes[-1]["scope"] == \
        [s for s in rt.kb_slugs_for("Intake") if s != "industry"]
```
### R1b — line 304, in `test_build_lanes_caps_off_states_and_multiquery_off` — same pattern, `"Discovery"`
### R1c — line 311 — same pattern, `"Booking"` (`blanes[0]`, general-union fallback scope)
### R1d — line 320 — same pattern, `"Intake"`, `rt2` (middle mode)
Nothing else in either function changes.

## 3. New pins file `tests/test_iter64_industry_gate.py` (2 pins; crib `_t4_settings` from `tests/test_iter52_industry_pin.py` — it pins `rag_pin_industry=True` via setdefault, ambient-env-proof; `_chunk`/`LanesStore` from `tests/test_iter49_rag_parity.py`; `_FakeKBStore` shape from test_iter52)

1. **`test_industry_absent_pre_pin`** — helper `_s64(**kw)` = `_t4_settings` clone.
   `_GateStore`: records every `retrieve_lanes(lanes)` call AND serves scripted chunks FILTERED by `lane["scope"]` (chunk's kb must be in the lane's scope) — proves the served set, not just the scope (AUD-4). Script: `_chunk(1, "industry", "dental pain prose", 0.5)` + `_chunk(2, "sales-language", "generic ammo", 0.4)`.
   - (a) default settings, `rt.build_lanes("Discovery", {}, "how much does this cost exactly")` → laneB (last lane): `"industry" not in lane["scope"]` AND scope == `[s for s in rt.kb_slugs_for("Discovery") if s != "industry"]`; laneA per-tag lanes unchanged.
   - (b) `await rt._retrieve_raw("Discovery", {}, "how much does this cost exactly", store, lane="laneB")` → recorded lane scope excludes `"industry"`; served results contain ZERO `kb == "industry"` chunks (the scope filter dropped chunk 1) and DO contain the sales-language chunk.
   - (c) kill switch: `CallRuntime(_s64(rag_pin_industry=False), …)` → `build_lanes("Discovery", {}, msg)` laneB scope KEEPS `"industry"` (byte-exact iter49 — AUD-2 pin).
2. **`test_industry_returns_on_pin`** — `_PinStore` = `_FakeKBStore` shape (async `retrieve`/`vertical_of`/`pinned_by_tag` + call recorders) + `retrieve_lanes` recording lanes and serving scripted chunks; `pinned_by_tag("Dental Practices")` → 2 chunks; utterance ≥ 12 chars (`rag_min_query_chars`).
   - (a) pinned: `dvs = {"industry": "dental practice"}` (alias hit, no embed) → `await rt._retrieve_raw("Discovery", dvs, "we miss calls constantly", store, lane="laneB")` returns `pinned_tag == "Dental Practices"`; `rt._pinned_industry["chunks"]` len 2; recorded laneB scope EXCLUDES industry (existing pinned drop); `store.pin_calls == ["Dental Practices"]`.
   - (b) dv present, pin UNRESOLVED: `dvs = {"industry": "car dealership"}` (no alias, `retrieve_rows=[]` → resolver None) → `pinned_tag == ""` AND recorded laneB scope KEEPS `"industry"` (gate inactive: dv non-empty — iter63 behavior preserved).
   - (c) render re-entry: `_render_from_raw(lane_results, owned, merged, ms, lane_qs, pinned_tag, pin)` with the returned pieces → `kbs` includes `"industry"` (pin block) — the vertical is never lost.

## 4. Execution order (compile-check after each edit; suite after §2 and after §3)

**T1 — worktree + baseline**
```bash
cd /home/julio/projects/clean_diallux_SDR && git worktree add -b engine/iter64-industry-gate /tmp/opencode/wt-iter64 2cb810f
ln -sfn /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter64/engine/.venv
cp -p /tmp/opencode/wt-iter63/engine/.env /tmp/opencode/wt-iter64/engine/.env
cd /tmp/opencode/wt-iter64/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3
```
GATE: `git log --oneline -1` == `2cb810f`; suite == **425 passed** (verified 425 on this exact sha 2026-09-22; any other count → STOP and reconcile).

**T2 — apply E1, E2, E3** → `.venv/bin/python -m py_compile diallux/graph/builder.py scripts/rag_replay.py`; `git diff 2cb810f --stat` shows ONLY `engine/diallux/graph/builder.py` + `engine/scripts/rag_replay.py` (+ §2/§3 files when done).

**T3 — apply R1a–R1d** → `.venv/bin/python -m pytest tests/test_iter49_rag_parity.py -o addopts="" -q` → all passed.

**T4 — suite gate (fix + rewrites, no new pins)** → **425 passed, 0 failed** (count-neutral).

**T5 — write the 2-pin file** → `pytest tests/test_iter64_industry_gate.py -o addopts="" -q` → 2 passed.

**T6 — suite gate final** → **427 passed, 0 failed**. (If an existing test fails: STOP, diagnose, fix forward per its semantics — never weaken a pin; record in the report.)

**T7 — battery (OWNER TOKEN GO REQUIRED FIRST — spends OPENAI_API_KEY)**
```bash
set -a && . ./.env && set +a && export RAG_FIRE_MODE=hybrid && date +%H:%M
.venv/bin/python tests/llm2llm/harness.py --personas happy --rag --rag-fire-sim --langfuse --max-turns 48
.venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --rag-fire-sim --langfuse --max-turns 48
date +%H:%M
```
GATE: 6/6 PASS, booked/ended, mock slots only. If a real Cal.com booking appears → cancel immediately (event 3801235 is REAL).

**T8 — ledger + replay verdict**
```bash
set -a && . ./.env && set +a && .venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run chat-iter64-sim --branch engine/iter64-industry-gate --commit <sha>
cd /home/julio/projects/clean_diallux_SDR && python3 scripts/rag_pull.py --run chat-iter64-sim --gates
cd /tmp/opencode/wt-iter64/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/rag_replay.py --run chat-iter64-sim --out /tmp/opencode/iter64_rag_truth.jsonl
```
Plus Langfuse sidecar `research/surgeon/iter64-industry-gate/rag_span_enrichment_chat-iter64-sim.json` (pattern: iter63 sidecar). GATE: (a) rag_pull gates PASS (served_rate ≥ 95%, await p50 ≤ 80); (b) replay: **zero wrong-vertical industry chunks in pools/served on pre-pin rounds** (the iter63 defect list — Susan t3/t4, Marcus t3/t5, Maria t4, Danny t6 — pools clean); (c) pin rounds byte-unchanged (pin coverage ≈ 84%, pin-only rounds still serve the vertical block).

**T9 — report + commit + ASK**
1. Write `research/surgeon/iter64-industry-gate/01_iteration_report.md`: gates table, before/after wrong-vertical table (cite `research/surgeon/iter63-rag-fire-sim/06_others_rag_per_turn.md`), per-SOP one-table pass, the 4-assertion rewrite note, the E3 replay-mirror note.
2. Commit (branch only):
```bash
cd /tmp/opencode/wt-iter64 && git add engine/diallux/graph/builder.py engine/scripts/rag_replay.py engine/tests/test_iter49_rag_parity.py engine/tests/test_iter64_industry_gate.py && git commit -m "iter64: pre-pin industry scope gate — wrong-vertical sweep eliminated (2-line fix + replay mirror + 4 assertion updates + 2 pins)"
```
3. Telegram ASK (`hitl_ping.py` — source video_strategy `.env` then engine `.env`): suite 427/0, gates table, before/after wrong-vertical, run `chat-iter64-sim`, report path — **merge decision = owner (STOP POINT)**.

## 5. Known accepted consequences (do NOT "fix" during execution)

- Freeze/prefetch/drift family (`rag_live_retrieve=False` revert path: state_node non-live branch, `_stage_rag`, warm gate) keeps `industry` pre-pin — dormant under defaults; the evidence and the fix are live-path only (AUD-3).
- Kill switch off (`rag_pin_industry=False`) = byte-exact iter49 scopes — the gate is inside the switch (AUD-2).
- Pre-pin probing rounds (~4–6) lose vertical ammo by design; generic sales KBs serve them; the vertical re-enters via the pin block 1 turn after extraction (measured `await_ms=0`).
- Stale pin on cleared dv (AUD-6): existing pinned drop still applies; unchanged from iter52.
- Freed mechanical states (Booking etc.) also lose pre-pin industry (same general-union scope) — intended, same risk family.
- Ledger `chunks=0` labels (PT-59) not used for verdicts; replay SDK (E3-mirrored) + Langfuse pin truth are the verdict source.

## 6. Out of scope (owner decisions, unchanged)

iter62 mic gate + merge (owner call pending) · iter63 merge (owner STOP POINT) · RAG settings tuning (0.24/12/60) · PT-59 ledger kbs/pinned columns · FIND-8 concat-echo fix · chat lane firing default-on · pain-amplification KB.

## 7. Flaw ledger (source plan → resolution; full detail in archive/01-03)

| # | Flaw in `plans/plan_v5_iter64_industry_gate.md` | Resolution here |
|---|---|---|
| AUD-1 | "existing 425 suite still passes" pre-pins — FALSE (4 assertions break: test_iter49:263/304/311/320) | §2 R1a–d rewrites + reordered gates (T4=425 → T6=427) |
| AUD-2 | Fix snippet ungated on `rag_pin_industry` (breaks iter52 kill-switch contract) | E1/E2 gate inside the switch; pin 1(c) pins it |
| AUD-3 | Freeze/drift family not mentioned | §5 documented consequence |
| AUD-4 | Pin-1 "served set" unprovable with scope-agnostic LanesStore | `_GateStore` scope-filtering fake (§3.1) |
| AUD-5 | Duplicate industry derivation in laneB | E2 reuses the var |
| AUD-6 | Stale-pin-on-cleared-dv edge | §5 documented, no change |
| AUD-7 | Pin-2 store interface gap | `_PinStore` spec (§3.2) |
| PF-1 | rag_replay.py reconstructs the OLD scope → T8 verdict would false-fail | E3 mirrors the gate (§1) |

**STOP — the next action (T1) runs ONLY on the owner's explicit go.**
