# 04 — MASTER PLAN — iter62 lane restore (AIRTABLE-READY FOR EXECUTION)

Status: **AWAITING OWNER APPROVAL TO EXECUTE** (surgeon step-5 gate)
Supersedes: `plans/plan_v5_iter62_lane_restore.md` where 01-audit/03-cross-ref found flaws (AUD-01..05, NEW-1..6). A fresh agent can execute from THIS file alone.
Source docs: `archive/01_audit.md`, `archive/02_action_plan.md`, `archive/03_cross_reference.md` (same folder).

## 0. Identity

- Base: `6c986e8` = tip `engine/iter61-prewarm-staleness` (clean worktree `/tmp/opencode/wt-iter61`; `:8021` pid 1983323 runs it).
- New branch: `engine/iter62-lane-restore` cut from `6c986e8`; worktree `/tmp/opencode/wt-iter62`.
- Goal: restore two-lane retrieval (Lane A pinned-shape at first Update + Lane B utterance at EagerEOT) by DELETING the coordination machinery that breaks it; add solar alias; fix the `record_reach_details` empty-callback dead end. Mic behavior byte-stable when retrieval lands in time.
- Hard laws: NO edits to `tests/llm2llm/harness.py`, `session.py`, prompts, `.env`, prewarm.py, deepgram_stt.py. NO merges, NO `:8020`/ports 8000-8003, `.env` never committed. Commits only on the branch after suite green. Owner mic re-test gates everything.

## 1. Exact code edits (all in `/tmp/opencode/wt-iter62/engine/`)

### E1 — `diallux/graph/builder.py` · `ingest` line 2663 — keep the turn transcript
```python
# BEFORE
                "user_text": "",
# AFTER
                # iter62: keep the turn transcript — state_node consumes
                # state["user_text"]; the next turn's payload overwrites it.
                "user_text": state.get("user_text", ""),
```

### E2 — `diallux/graph/builder.py` · `state_node` live branch lines 1872-1873 — single source of truth
Target the occurrence inside `if live and do_retrieve:` (line 1871) — an identical two-liner exists at 1901-1902 (non-live revert path) that must NOT be touched.
```python
# BEFORE
                    user_msg = next((m["content"] for m in reversed(history)
                                     if m.get("role") == "user"), "")
# AFTER
                    # iter62 — the session-provided transcript is the single
                    # source of truth; history re-extraction diverged under
                    # eager/barge-in and triggered empty respawns (25/67
                    # blind rounds on call cc22e0a0185e).
                    user_msg = (state.get("user_text") or "").strip()
```

### E3 — `diallux/graph/builder.py` · `_consume_hybrid` lines 1525-1530 — stash honesty (NEW-1)
```python
# BEFORE
            r = stash["res"]
            return (r["delta"], r["kbs"], r["ms"], r["chunks"],
                    r["lane_qs"], False, 0.0)
# AFTER
            r = stash["res"]
            # iter62: same empty-set honesty on same-turn reuse rounds.
            return (r["delta"], r["kbs"], r["ms"], r["chunks"],
                    r["lane_qs"], not r["chunks"], 0.0)
```

### E4 — `diallux/graph/builder.py` · `_consume_hybrid` lines 1540-1550 — delete respawn, KEEP mismatch reject
```python
# BEFORE
        # lane B: bounded await on the in-flight single-query embed; respawn
        # when missing (speech-window fire skipped / eager-off turn).
        res_b = None
        if task_b is None or task_b.cancelled() \
                or self._live_msgs.get(key_b) != msg:
            # iter60 AUD-4: a DONE laneB from an earlier turn/visit has no
            # seq/msg freshness check — reject on msg mismatch and respawn
            # with the CURRENT round's utterance (same kill as the task
            # path's msg-match).
            self.spawn_live_retrieve(state_name, dvs, msg, lane="laneB")
            task_b = self._live_tasks.get(key_b)
# AFTER
        # lane B: bounded await on the in-flight single-query embed.
        # iter62: NO respawn — the fire lives in the session layer
        # (Update/EagerEOT/EOT). Missing, cancelled, or fired for a
        # DIFFERENT utterance (iter60 AUD-4 mismatch) = CLEAN FAIL this
        # round; the next fire supersedes (owner: no late-restart injection).
        res_b = None
        if task_b is None or task_b.cancelled() \
                or self._live_msgs.get(key_b) != msg:
            task_b = None
```

### E5 — `diallux/graph/builder.py` · `_consume_hybrid` lines 1587-1592 — fail clean (delete stale fallback)
```python
# BEFORE
        if not landed:
            fallback = self._live_consumed_res.get(state_name) \
                or self._live_prev.get(state_name) or {}
            return (fallback.get("delta", ""), fallback.get("kbs", []),
                    fallback.get("ms", 0.0), fallback.get("chunks", []),
                    fallback.get("lane_qs", []), True, await_ms)
# AFTER
        if not landed:
            # iter62 — owner decision: a late/failed retrieval is a CLEAN
            # FAIL; stale-prev injection feeds the model chunks that make
            # no sense at the wrong moment. Next fire supersedes.
            return ("", [], 0.0, [], [], True, await_ms)
```

### E6 — `diallux/graph/builder.py` · `_consume_hybrid` final return line 1616 — landed-empty is degraded
```python
# BEFORE
        return (delta, kbs, ms, merged, lane_qs, False, await_ms)
# AFTER
        # iter62: chunks=0 is an HONEST degraded round (was hard-coded False;
        # 38/67 spans hid behind that on the iter61 call).
        return (delta, kbs, ms, merged, lane_qs, not merged, await_ms)
```

### E7 — `diallux/graph/builder.py` · eot/speech-window consume return lines 1494-1495 — same empty-set rule
```python
# BEFORE
            return (res["delta"], res["kbs"], res["ms"], res["chunks"],
                    res["lane_qs"], False, await_ms)
# AFTER
            # iter62: same empty-set rule — 0 chunks is never "healthy".
            return (res["delta"], res["kbs"], res["ms"], res["chunks"],
                    res["lane_qs"], not res["chunks"], await_ms)
```
(The eot-path inline respawn 1471-1473 and fallback 1500-1503 stay — revert path, untouched.)

### E8 — `diallux/graph/builder.py` · LIVE rag span emitter line 1891 — zero_hit
```python
# BEFORE
                            "degraded": degraded, "await_ms": await_ms,
# AFTER
                            "degraded": degraded,
                            "zero_hit": (len(merged) == 0),
                            "await_ms": await_ms,
```

### E9 — `diallux/graph/builder.py` · FREEZE rag span emitter line 2064 — zero_hit (parity)
```python
# BEFORE
                            "state": state_name, "ms": rag_ms, "kbs": rag_kbs,
                            "chunks": len(chunks), "query": query[:200],
# AFTER
                            "state": state_name, "ms": rag_ms, "kbs": rag_kbs,
                            "chunks": len(chunks), "query": query[:200],
                            "zero_hit": (len(chunks) == 0),
```
(Uses `chunks` — `merged` does not exist on this path. AUD-05.)

### E10 — `diallux/graph/builder.py` · `_PIN_ALIASES` after line 134 — solar alias
```python
    ("roofing", "Residential Roofing & Solar Installers"),
    ("solar", "Residential Roofing & Solar Installers"),   # iter62: dv
    # "solar company" fell to embed-fallback < 0.24 and cached a per-dv
    # miss for the whole call (pinned="" on all 67 spans, cc22e0a0185e)
```
(Position inside the literal is moot — the `sorted(..., key=-len(alias))` wrapper orders it. Resolver `hits` is a set of TAGS → roofing+solar stays a single hit.)

### E11 — `diallux/graph/tools.py` · `ToolExecutor.execute` after the `query_livecall_slots` block (line 157), before `if self.tracer:` — need_digits recovery
```python
        # iter62 (FIND-29 family): record_reach_details(true) with NO
        # callback_number is a guaranteed dead end on mic transport (no
        # caller-ID to seed) — the webhook answers ok/"seeded stands" and
        # the ConfirmSlots gate then blocks with no scripted recovery.
        # Hand the model the next step HERE; the webhook's dvs_patch
        # (phone_confirmed) stands. Non-empty callback_number or a NO
        # answer = byte-identical to today.
        if name == "record_reach_details" \
                and (args or {}).get("is_calling_best_number") is True \
                and not str((dvs or {}).get("callback_number") or "").strip():
            resp = dict(outcome.response or {})
            resp["status"] = "need_digits"
            resp["instruction"] = ("Ask: What's the best number to reach you? "
                                   "Then call set_callback_number with the "
                                   "exact digits they spoke.")
            outcome["response"] = resp
```
Accepted interactions (03 §3): overrides `already_captured` on a repeat identical call (better guidance); overrides a failed-webhook body too (the ask-digits step is correct regardless).

## 2. Existing-test rewrites (2 — documented deviation from the source plan's "zero edits"; count-neutral)

### R1 — `tests/test_iter60_audit_fixes.py` · `test_hybrid_stale_laneb_respawned_with_current_msg` (lines 132-166)
Keep name + setup (turn-1 Booking laneB fire/land/consume; turn-2 Intake laneA+laneB fires). Replace the final consume block + assertions:
```python
        # iter62: the respawn is DELETED (fail-clean) — the stale DONE
        # laneB (fired for an earlier utterance) is REJECTED on msg
        # mismatch, NOTHING re-fires, and the round fails CLEAN.
        _d2, _k2, _ms2, _c2, lq2, deg2, _aw2 = await rt._consume_live_retrieve(
            "Booking", {}, "and what about the warranty", store)
        assert deg2 is True
        assert lq2 == [] and _c2 == [] and _d2 == ""
        assert len(store.lane_calls) == 3   # turn-1 laneB + turn-2 laneA/laneB — NO 4th fire
```

### R2 — `tests/test_iter59_rag_freshness.py` · `test_hybrid_lane_b_only_when_lane_a_absent` (lines 391-405)
```python
def test_hybrid_lane_b_only_when_lane_a_absent():
    """iter62: an eager-off turn (no laneB fire) has NOTHING to consume —
    the round FAILS CLEAN (inline respawn deleted; fires are session-owned;
    chat surfaces show this exact shape — documented, not a regression)."""
    store = LanesStore(sets=[[[_chunk(3, "pain-points", "laneB only", 0.8)]]])
    rt = CallRuntime(_settings(rag_fire_mode="hybrid"), _LLM_JSON,
                     tracer=None, llm=None,
                     http_client=mock_client(), kb_store=store)

    async def go():
        d, k, ms, ch, lq, deg, aw = await rt._consume_live_retrieve(
            "Intake", {}, "spawning lane b inline", store)
        assert deg is True and d == "" and k == [] and ch == []
        assert store.lane_calls == []          # nothing fired inline
        await rt.aclose()

    _run(go())
```

## 3. New pins file `tests/test_iter62_lane_restore.py` (9 pins; crib `_t4_settings`/`LanesStore`/`_chunk`/`mock_client` from test_iter49_rag_parity, `_run` pattern from test_iter59)

1. **`test_ingest_keeps_user_text_across_rounds`** — full-graph (FakeLLM 1 speech round, `kb_store=None`): astream turn with `user_text="how much do you guys charge for HVAC"` → final state `state["user_text"] == "how much..."` (was `""`), history has exactly ONE user msg; second astream turn SAME text → still ONE user msg (idempotent guard) and `user_text` unchanged.
2. **`test_consume_uses_session_transcript_not_history`** — hybrid rt + LanesStore(1 chunk set); `spawn_live_retrieve("Intake", {}, "how much do you guys charge", lane="laneB")`; await task; `_consume_live_retrieve("Intake", {}, "how much do you guys charge", store)` → `lane_qs` contains the transcript, `degraded is False`, `store.lane_calls` length 1 (NO respawn).
3. **`test_lane_a_shape_refer_tags_owned`** — `build_lanes("Offer", {"monthly_leak": "60,000"}, "")` → lanes are exactly the Offer refer-tag lanes: query contains tag.what + `"$60,000 a month"`, scope `== [tag.kb]`, owned `== {tag.kb}`; `build_lanes("contact_details", {...}, "")` → NO lane-A lanes (that state has no refer-tags; lane A comes only from tags).
4. **`test_zero_chunks_is_degraded`** — hybrid, both lanes land, LanesStore returns empty chunk lists → consume: `degraded is True`, `chunks == []`.
5. **`test_span_zero_hit_field`** — spy tracer (`class _SpanSpy: spans=[]; span(name, output=None, **kw)` appended); two one-turn graph runs (chunk store vs empty store) → captured `"rag"` span output has `zero_hit` True/False matching emptiness.
6. **`test_await_miss_fails_clean`** — hybrid; round 1 lands + consumes (stash `_live_consumed_res` populated); then `rag_live_await_ms=5`, slow LanesStore (`delay=2.0`), new laneB fire for a NEW msg → consume: `degraded is True`, `delta == ""`, `chunks == []` — the PREVIOUS set is NOT returned (fail clean, not `_live_consumed_res`).
7. **`test_solar_alias_resolves_vertical`** — fake store recording `retrieve` calls: `_resolve_industry_tag("solar company", store)` == `"Residential Roofing & Solar Installers"` with ZERO retrieve calls (alias path); `_ensure_pinned_industry({"industry": "solar company"}, store)` with `pinned_by_tag` → 3 chunks caches `{"tag": ..., "chunks": 3}` (settings `rag_pin_industry=True`).
8. **`test_lane_drive_no_llm`** — hybrid rt + LanesStore (laneA set + laneB set): `spawn_live_retrieve(laneA, "")`, await; `spawn_live_retrieve(laneB, "how much do you guys charge")`, await; consume with the same msg → merged chunks from BOTH lanes render, `degraded is False`, span-relevant `lane_qs` non-empty (the chat-surface logic check; zero harness edits).
9. **`test_record_reach_details_need_digits_recovery`** — `ToolExecutor(SETTINGS, LLM_JSON, http_client=mock_client())`:
   (a) dvs `{"callback_number": ""}` → `execute("record_reach_details", {"is_calling_best_number": True}, dvs, "contact_details")` → `response["status"] == "need_digits"`, `"set_callback_number" in response["instruction"]`, `dvs_patch["phone_confirmed"] is True`;
   (b) dvs `{"callback_number": "+13125551234"}` → `response["status"] == "ok"` and NO `instruction` key (byte-identical);
   (c) `{"is_calling_best_number": False}` + empty dvs → `response["status"] == "ok"` (untouched).

## 4. Execution order (compile-check after each edit; suite after §3)

**T1 — worktree + baseline**
```bash
cd /home/julio/projects/clean_diallux_SDR && git worktree add -b engine/iter62-lane-restore /tmp/opencode/wt-iter62 6c986e8
ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter62/engine/.venv
cp -p /tmp/opencode/wt-iter61/engine/.env /tmp/opencode/wt-iter62/engine/.env
cd /tmp/opencode/wt-iter62/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3
```
GATE: `git log --oneline -1` == `6c986e8`; suite == **413 passed**. (If the count differs from 413, STOP and reconcile before any edit.)

**T2-T6 — apply E1..E11** (builder.py E1-E10, tools.py E11), `py_compile` each file, then **R1+R2** rewrites, then the **9-pin file**.

**T7 — suite**
```bash
cd /tmp/opencode/wt-iter62/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3
```
GATE: **422 passed, 0 failed** (413 + 9 new; R1/R2 count-neutral). If any OTHER existing test fails (an eot-path empty-set assertion AUD-11 did not find), fix forward per its semantics — empty ⇒ degraded — and record it in the fix report; never weaken a pin to pass.

**T8 — restart :8021 + mic gate** (only restart surface; never `:8020`/8000-8003)
```bash
kill $(cat /tmp/opencode/voice_8021.pid) 2>/dev/null; sleep 2
ss -ltn | grep 8021 && kill -9 $(ss -ltnp | grep 8021 | grep -oP 'pid=\K[0-9]+' | head -1) 2>/dev/null; sleep 1
cd /tmp/opencode/wt-iter62/engine && git log --oneline -1
set -a && . ./.env && set +a
RAG_FIRE_MODE=hybrid CALL_PREWARM=true setsid nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8021 >> /tmp/opencode/voice_server_8021.log 2>&1 &
sleep 6
ss -ltnp | grep 8021 | grep -oP 'pid=\K[0-9]+' | head -1 > /tmp/opencode/voice_8021.pid
curl -sf http://127.0.0.1:8021/health && .venv/bin/python scripts/voice_preflight.py --url http://127.0.0.1:8021 2>&1 | tail -2
```
Then Telegram the owner the SAME mic URL (`https://flores.diallux-ai.site/voice60/mic?k=$VOICE_TEST_TOKEN`): "iter62 mic regression test ready — same URL, raise a pricing objection somewhere in the call." Pull: `.venv/bin/python scripts/mic_events.py --sid <new-sid> --langfuse`.
MIC GATE (all must hold): e2e p50 within ±25% of 1188 ms; eager_final_match 100%; zero STT/TTS errors/drops; greeting full; TTL respawns normal; `zero_hit=True` count on rag-eligible turns STRICTLY < 38/67; objection-turn span `query` NON-EMPTY (contains the utterance); `pinned` non-empty once industry known.

**T9 — ledger + report + commit + ASK**
1. Ledger (venv python, NO sqlite3 CLI): `scripts/live_sql.py import --window "HH:MM-HH:MM" --run mic-iter62 --branch engine/iter62-lane-restore --commit <sha>` from the worktree with `.env` sourced; flip **FIND-30** → `fixed-in-iter62 verified-live` (before: 38/67 zero-hit + empty objection queries; after: re-test counts); append **FIND-29 fix-note** (need_digits recovery + iter62 sha; gate/prompt half stays parked for the owner's string edit).
2. Write `research/surgeon/iter62-lane-restore/01_fix_report.md`: per fix — before (cite `research/surgeon/iter61-prewarm-staleness/03_kb_retrieval_deep_dive.md` §7) / after (file:line + pin) / mic gate table / the chat-`--rag` expected fail-clean note (degraded=true, zero_hit=true on chat = the semantics working, NOT a regression).
3. Commit (branch only):
```bash
cd /tmp/opencode/wt-iter62 && git add engine/diallux engine/tests && git commit -m "iter62: lane restore — session-transcript single source (kill empty respawn), fail-clean await, honest zero_hit, solar pin alias, record_reach_details need_digits"
```
4. ASK owner (`hitl_ping.py`): suite <N> passed, mic gate status, retrieval delta, FIND-30 flipped, report path — **merge decision = owner (STOP POINT)**.

## 5. Known accepted consequences (do not "fix" during execution)
- Chat `--rag` runs: no session fires → hybrid consume fail-cleans → spans `degraded=true, zero_hit=true` (owner-deferred chat firing).
- AUD-3 stash identical-msg cross-turn reuse: benign (same query ⇒ same retrieval).
- E11 overrides `already_captured`/failed-webhook bodies on (YES ∧ empty callback): intentional (better guidance than walking into the gate dead-end).
- eot-mode spans now degrade on 0 chunks (E7): the revert path gets the same honesty; AUD-11 found no existing pin contradicted.
- `_live_consumed_res` write at 1610 stays (readers gone in hybrid; eot/speech-window still use it).

## 6. Out of scope (owner decisions, unchanged)
FIND-29 calendar seed + gate ordering (parked) · FIND-31/32 (parked) · pain-amplification KB (owner HITL) · `rag_filter_score`/`rag_min_query_chars` tuning (owner-calibrated, UNTOUCHED) · chat lane firing / `--rag-fire-sim` (deferred) · merges/tags/`git-tree.sh` (LAW 0, STOP POINT) · contact_details.md line-31 string edit (owner applies; agent proposes in the fix report: "YES branch: if `{{callback_number}}` is empty, ask for the digits first — the tool will confirm with need_digits").
