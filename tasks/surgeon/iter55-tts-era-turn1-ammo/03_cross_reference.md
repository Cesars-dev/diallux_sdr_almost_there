# 03 — CROSS-REFERENCE — audit (01) vs action plan (02)

Method: every audit finding (F-01…F-09) checked for plan coverage; every planned change checked for audit support; contradictions resolved or escalated.

## Matrix — audit finding → plan resolution

| Finding | Resolved by | Status |
|---|---|---|
| F-01 Rourke breaks SOP-order pin (332/333) | Commit 0 (reposition into happy block) | ✓ covered |
| F-02 config.py duplicate V2 block | Logged in audit §C; deliberately NOT fixed (scope discipline) | ✓ documented, deferred |
| F-03 `43d83d0815c9` unresolvable | T2 Option A step: re-resolve before use | ✓ covered |
| F-04 :8005 > :8000 raw means (population mismatch) | Guard note in audit D2; T2 same-path A/B is the only valid comparison | ✓ guarded |
| F-05 Langfuse ingest quiet | Benign (no runs since yesterday); T0 live verification will re-confirm | ✓ noted |
| F-06 greeting stamps turn-0 clock | 1d design: dedicated `_greet` anchors, never the clock | ✓ covered |
| F-07 T3-as-written FALSE (shared `_warm_llm` cap) | Commit 2: split knob `prewarm_lite_max_completion_tokens` + lite twin; sweep touches lite only | ✓ covered — **plan delta vs source plan** |
| F-08 `warm()` swallows failures → done-callback blind | 1b: un-swallow (all 3 callers verified inside try/except) + 1c diag | ✓ covered |
| F-09 4th await outcome `no_task` | 1c taxonomy: landed/timeout/already_done/no_task (+task_error) | ✓ covered |

## Contradictions found (source plan vs code — resolved)

| # | Source-plan claim | Code reality | Resolution in 02 |
|---|---|---|---|
| CR-1 | T3: "sweep only touches the lite warm by reading `_warm`'s lite branch" | The cap lives on the shared `_warm_llm` twin (llm.py:205-211), NOT the lite branch; both shapes capped by one knob | Commit 2 prerequisite (F-07). T3 gate rewritten to require Commit 2 first |
| CR-2 | "Suite check expect 333 passed" at branch point | 332 passed + 1 failed (Rourke, F-01) | Commit 0 restores; suite gate for T0 = 333 + new pins |
| CR-3 | File Map: llm.py gets warm timestamps; tracer.py gets span helpers | Timestamps belong in builder (fired_at + done-callback); `Tracer.span` already exists and suffices | 02 assigns: llm.py = un-swallow only (1b); tracer.py = UNCHANGED; builder.py = spans/timestamps (1c). Cleaner, fewer files |
| CR-4 | T0 verification: "one mic-bridge session + one harness call" | Greeting span is voice-only by construction (chat has no audio; harness window = known sleep) | 1f protocol states this explicitly; chat verification checks warm/await spans only |
| CR-5 | Plan BLOCKED table lists `prewarm_entry_wait_eot_ms` raise as post-T0 owner decision | Code confirms entry-ack path has NO wait knob at all (`pass`, builder.py:1382) — raising the EOT cap only affects lite/full rounds | Preserved as owner decision; action plan adds the failure-tree ping (T4) so the decision is data-fed |
| CR-6 | Plan warm-span shape "warm:<shape>" | Keyed spans `warm:lite:<state>` / `warm:<state>` match `_latest_warm` keys exactly (SQL/join-friendly) | 02 uses `warm:{key}` naming; documented |

## Gaps found (plan → audit support check)

| # | Planned change | Audit support | Status |
|---|---|---|---|
| G-1 | `warm_observability` flag default True | "No behavior change" holds: spans are fail-safe side-effects; flag False = exact pre-T0 span surface (pinned in test 5) | ✓ |
| G-2 | Done-callback emits spans | `asyncio.Task.add_done_callback` runs in the event loop; tracer.span is sync + fail-safe (tracer.py:143-153) — no await needed | ✓ verified |
| G-3 | `_greeting_drain` follow-up task | Mirrors existing `_late_turn_report` pattern (session.py:541-556) — proven in production | ✓ |
| G-4 | Telegram ping helper | Creds + pattern verified on file (audit D3); engine `.env` gitignored; fail-safe contract matches tracer | ✓ |
| G-5 | T1 cold-probe letters a/b, ≥3.5 h idle | Matches plan's pinned cold-probe discipline (probe mechanics section) | ✓ |
| G-6 | Ledger import from MAIN checkout | Trap documented in plan + AGENTS.md; T1 step 4 restates | ✓ |

## Redundancies / scope checks
- No commit touches more than one concern: C0 fixtures, C1 observability, C2 split knob, C3 (conditional) fallback authoring. One variable per probe preserved (T3 sweeps ONE env; T4 flips ONE env).
- Tracer.py drops out of the T0 file map entirely (CR-3) — 4 engine files touched instead of 5.
- warm_rag instrumentation deliberately OUT of scope (greeting span covers the session-start runway question the owner asked; warm_rag is async off critical path — its keep/drop is the T1-fed HITL row, not a T0 measurement).

## Open items NONE
All findings resolved or explicitly deferred with owner visibility (F-02). Master plan (04) is airtight to write.
