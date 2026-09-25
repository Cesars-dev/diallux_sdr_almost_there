# 03 — CROSS-REFERENCE — audit (01) vs action plan (02)

Method: every audit finding (§F bugs/risks + §A claim corrections) checked for coverage in 02; every 02 change checked for audit support. Contradictions, gaps, redundancies listed with dispositions.

## 1. Audit findings → action-plan coverage

| Audit finding | Covered in 02? | Disposition |
|---|---|---|
| F1 round gate blocks tag-less states | ✅ T4.1 item 2 (live-branch `do_retrieve = bool(scope)`) | RESOLVED |
| F2 freed-state scope = 9-KB general union | ✅ T4.1 item 3 (pinned in tests, not assumed) | RESOLVED |
| F3 verbosity A/B confound | ✅ T1.4 (high arm `VERBOSITY_STATES_MEDIUM=""`) | RESOLVED |
| F4 flux STT drops Update events | ✅ T3.2 item 1-2 (new handler + `on_update` callback + once-per-turn session guard) | RESOLVED |
| F5 flux idle WS no keepalive | ✅ T5 item 2 (KeepAlive + maintainer + respawn) | RESOLVED |
| F6 adoption is callback-bound | ✅ T5 item 3 (adopt at WS level, recv loop binds to owning session) | RESOLVED |
| F7 semantic-dedupe hot-path cost | ✅ T4.2 item 3 ("?"-gate + non-empty window + stems embedded once) | RESOLVED |
| F8 `_frozen_chunks` fallback unimplementable under live mode | ✅ T3.2 item 4 (`_live_consumed` semantics) | RESOLVED |
| F9 serve_voice.sh refuses busy :8020 | ✅ T6 deploy recipe (explicit kill + pid file) | RESOLVED |
| F10 same-text rerun edge (`_live_msgs` text match) | ✅ T3.2 item 3 (turn-keyed seq) | RESOLVED |
| F11 docs/ledger drift (CALL_FACTS untracked, ITERATIONS missing 56-58, PT-57 gap) | ✅ T7 items 1-3 (git add, branch-closeout lines, PT-57 note) | RESOLVED |
| F12 round-sync breaks e2e ≤1100 gate by construction | ✅ T3.3 + T6 (per-variant gates; decision recorded pre-commit) | RESOLVED |
| A3 voice-ai-capabilities also on Offer | ✅ T1 evidence pack states the corrected map (no code change — map is data) | RESOLVED (documentation) |
| A17 GK_chat ≠ 7.8/7.9; no production V7.9 on disk | ✅ T1.1 corrected corpus (12 on-disk files; optional read-only pulls) | RESOLVED |
| A6 bg p50 123 vs plan's 131 | Both cited in report (ledger 123.2, spans median) | NOTED, immaterial |
| A19 38 vs 39 turns | Report cites ledger 38 (calls row) + report's 39 | NOTED, immaterial |

## 2. Action-plan changes → audit support

| 02 change | Audit support | Verdict |
|---|---|---|
| T0 worktree recipe (branch from db8e56f, venv symlink, .env copy) | §D: branch/worktree absent (clean), wt-iter58 .venv IS a symlink to the same target (existing practice), .env exists with required keys | SUPPORTED |
| T1.3 sweep corpus (iter58_gens_raw.txt + synthesized pairs) | §D: file exists (21,199 B); rephrase controls documented in iter58 report (0.54-0.57) | SUPPORTED |
| T1.5 turns 9→11 pin dump | §B1: `render_pinned_section` (rag.py:680); trace `daee4b00…` accessible (verified via API) | SUPPORTED |
| T3.2 Update-fire design | §B2: `_handle` structure (deepgram_stt.py:176-189); `_turn_state`/`_turn_dvs` maintained (session.py:588-591) — data needed mid-speech exists | SUPPORTED |
| T3.2 turn-keyed seq supersede | §B1: `spawn_live_retrieve`/`_consume_live_retrieve` signatures (1199/1245) — additive param + dict, no signature break | SUPPORTED |
| T3.3 round-sync variant | §B1: `_live_retrieve` callable directly (1091); cost measured (123-131 ms) | SUPPORTED |
| T4.1 empty `_RETRIEVAL_OFF` (keep attribute) | §A1: referenced at 971 (kb_slugs_for) + 1536 (gate) + tests; emptying is safer than deleting | SUPPORTED |
| T4.2 GraphState `question_stem_window` per-CALL | §B7: TypedDict additive; ingest reset list explicit (2247-2258) — omission = per-call persistence | SUPPORTED |
| T4.2 embed via store `embed_query` | §B1/rag.py:420-424: reused client exists; runtime holds `_kb_store` after resolve | SUPPORTED |
| T5 prewarm pool module + lifespan | §C5/C6: no startup hook exists today (clean addition); adoption signatures additive (`connect(ws=None)`) | SUPPORTED |
| T5 RAG stage = store singleton warm | §B7: `_SINGLETON` module-level (rag.py ~560); greeting path already proves the warm-embed pattern | SUPPORTED |
| T6 per-variant gates | §F12 | SUPPORTED |
| T7 closeout items | §A20/F11 + docs agent report (untracked files enumerated) | SUPPORTED |

## 3. Contradictions found (02 vs 01 vs original plan)

| # | Contradiction | Resolution adopted |
|---|---|---|
| X1 | Original plan File Map: "on timeout → `_frozen_chunks` fallback" vs audit F8 (`_frozen_chunks` never maintained under live mode) | 02 T3.2 uses `_live_consumed` (last CONSUMED set). Semantics match the plan's INTENT ("never stale-prev") better than its letter. **Master plan must state this explicitly as a deviation.** |
| X2 | Original plan T1 command 1 (grep for GK_chat/get-chat/dialogue) vs audit A17 (wrong family) | 02 T1.1 replaces the corpus. **Deviation to state.** |
| X3 | Original plan T1 command 5 (A/B via OPENAI_VERBOSITY only) vs audit F3 | 02 T1.4 adds `VERBOSITY_STATES_MEDIUM=""` to the high arm. **Deviation to state.** |
| X4 | Original plan "kill `_RETRIEVAL_OFF` entirely" vs audit F1 (gate at 1535 also blocks) | 02 T4.1 changes BOTH sites. **Deviation (scope addition) to state.** |
| X5 | Original plan verification "kb_slugs_for(state) non-empty for ALL sales states" vs reality that freed states get the 9-KB UNION (not curated lists) | 02 pins the union explicitly. Consistent with owner's "all KBs at all times" intent — but the master plan must flag that contact_details rounds will now carry a WIDER delta (token cost) and that `rag_char_budget=1600` still caps rendered chars. |
| X6 | Original plan File Map names `tests/test_iter59_rag_freshency.py`-style file list but 02's T3.4 header had a typo risk (freshency/freshness) | Normalize to `test_iter59_rag_freshness.py` everywhere. |
| X7 | Original plan says branch "cut from engine/iter58-eot08-public-mic @ db8e56f" — verified identical to branch head | No conflict. |
| X8 | Plan's "await p50 ≤15 ms" gate vs round-sync variant where await is the full retrieve (~130 ms) | Per-variant gates (02 T3.3/T6). The variant DECISION is owner-recorded pre-commit per the plan's own resolved-decision table. |

## 4. Gaps found (neither 01 nor 02 covers → must enter master plan)

| # | Gap | Master-plan treatment |
|---|---|---|
| G1 | **Update-event payload semantics unverified**: the exact Deepgram flux `Update` message shape (does `TurnInfo.Update` carry `transcript`? is it partial-running or final-so-far?) is assumed from code comments only. | Master plan adds a T3.0 probe step: one logged live/synthetic call with a debug hook dumping raw Update msgs BEFORE finalizing the handler (or verify against Deepgram docs in T1.2's research pass). Implementation must not assume `is_final` semantics. |
| G2 | **Eager-EOT interplay**: with fire-at-first-Update, the EagerEOT fire (session.py:399) supersedes the Update-fired task (same state) ~1-3 s later with the full utterance — cancelling a possibly-landed task and restarting the embed. The once-per-turn Update guard must decide: keep the Update-fired task (partial utterance, lands early) vs re-fire at EagerEOT (full utterance, late). | Master plan specs: Update-fired task is NOT superseded by the EOT fire when it has already LANDED (consume prefers landed); EOT fire only when no Update fired (eager-off path). The partial-vs-full utterance quality tradeoff is part of the T5 evaluation. |
| G3 | **Prewarm vs `settings` mutation**: session.start mutates `self.settings.deepgram_eager_eot_threshold` (session.py:176-177) — pooled connections built from settings at startup could diverge from per-call mutated settings (URL params baked at connect). | Pool builds WS with the SAME .env-backed values; the mutation only defaults None→0.6 and .env pins 0.7 — pool and call agree. Master plan notes: if eager threshold is None at pool build AND mutated later, rebuild pool conn; simpler: pool builder reads the same effective value (0.7 from .env). |
| G4 | **`_live_consumed`/`question_stem_window` and checkpointing**: GraphState additions ride `MemorySaver` per call — no migration concern; but `question_stem_window` write-back must use plain overwrite (list), NOT an append-reducer, or ingest wouldn't be able to leave it alone. | Master plan pins: plain key (no Annotated reducer), write-back only from state_node updates. |
| G5 | **Semantic dedupe vs TTS fast-flush interplay**: a question fragment flushed early (fast-first-flush can cut at a comma BEFORE the "?" arrives) could bypass the "?"-gate and speak a stem that later completes as a duplicate question. | Master plan: the "?"-gate applies to SENTENCE-boundary flushes; fast-flush fragments are exempt (they join the exact-match window as today). Residual risk documented; the cross-turn catch still fires on the full sentence. Accepted tradeoff (matches iter42 fragment semantics). |
| G6 | **Owner prompt dependency for contact_details loop**: audit F-iter58-B (10-turn loop) is prompt/flow-side; engine fixes (KB-everywhere) give the model KB ammo but do NOT fix the re-ask behavior. | Master plan keeps this as an OWNER item (PT row) — engine scope excludes prompt edits. |
| G7 | **`agents` on-disk llm.json `states` list** confirms 9 states (Booking…contact_details) — plan text says "ALL sales states"; the pin must enumerate all 9. | Master plan pins the exact 9-state list. |

## 5. Redundancies

- R1: 02 T4.1 keeps `_RETRIEVAL_ALLOW` logic for the non-live branch — correct (iter48 revert path), not redundant.
- R2: The original plan's architecture block mentions "frozen-reuse fallback — never stale-prev" AND "`_frozen_chunks` fallback" in the File Map — superseded by the single `_live_consumed` design (X1). No double implementation.

## 6. Open items carried to PREFLIGHT

1. G1 Update-shape probe (needs docs/live verification before code finalization).
2. G2 Update-vs-EagerEOT supersede policy (spec'd; verify against `_consume_live_retrieve` ordering in preflight).
3. Confirm `embed_query` availability on the runtime's resolved store for the dedupe path (real store: yes, rag.py:420; hermetic tests: fake provides it — pin).
4. Confirm FastAPI lifespan is available in the pinned fastapi version (TestClient used in tests implies modern starlette — verify import `from contextlib import asynccontextmanager` + `FastAPI(lifespan=…)` works in the venv).
