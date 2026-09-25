# 03 CROSS-REFERENCE — `01_audit.md` ↔ `02_action_plan.md`

Method: every audit finding (F1–F10) checked for plan coverage; every plan step checked for audit backing; contradictions between the SOURCE documents (governing plan, execution report, iter65 plan) checked for resolution in the action plan.

## A. Audit findings → plan coverage

| Finding | Covered by | Verdict |
|---|---|---|
| F1 (HIGH) ledger import uses pre-PT-59 engine `live_sql.py` in plan+report | Phase B: root-SDK import command + SQL verification incl. kbs/pinned/lanes/zero_hit | COVERED |
| F2 (HIGH) "merge iter65 and iter66" proposal rests on empty-iter65 premise | Phase C merges iter66 ALONE; iter65 deferred to E2 | COVERED |
| F3 merge conflict = impossible (descendant) | C1 proof pack re-verifies merge-base == main tip at execution time | COVERED |
| F4 iter65 semantic re-preflight (prewarm structure, suite 427→439) | E2 (re-baseline + re-walk at iter65 kickoff) | COVERED |
| F5 dirty GIT_TREE.md + untracked docs | Phase 0 absorbs GIT_TREE.md; E5 owner menu for the untracked docs | COVERED |
| F6 remote/tracking-ref mismatch (live remote `dfc0926`, 208 behind local, linear); push topic OUT OF SCOPE per owner (local-commit closeout) | Reframed to Phase-D context (verified facts, FF-safe, ls-remote verify); E2 doc-fix sub-item dropped | COVERED (reframed) |
| F7 keys absent / provider cartesia / CALL_PREWARM unset | A0 owner-supplies block (worktree .env only) | COVERED |
| F8 :8020 busy; port must be verified free | A1 `ss -tln` guard + 8023 (verified free at audit) | COVERED |
| F9 stale branches + prunable worktrees | E3/E4 owner-say-so menu | COVERED |
| F10 main .env provider flip owner-gated | E1 | COVERED |

## B. Plan steps → audit backing

| Step | Backing | Verdict |
|---|---|---|
| Phase 0 docs commit | LAW 0 docs rule; precedent `3ac4ac6` (plan doc committed pre-approval); GIT_TREE.md refresh is accurate (audit §A) | SUPPORTED |
| A0 keys into worktree .env only | Audit §C2 (keys absent everywhere); governing plan Resolved Decision ("provider stays cartesia until owner flips after live pass") | SUPPORTED |
| A1 foreground uvicorn :8023, tunnel access | Audit §C3 (routes verified: /mic, /mic/ws; serve_voice.sh hardwired to busy :8020; port scan) | SUPPORTED |
| A2 LV-1..5 | Governing plan T7 line (verbatim) | SUPPORTED |
| A3 autopsy loop | AGENTS.md autopsy mandate; same-branch fix discipline | SUPPORTED |
| B root-SDK import | Audit §D (PT-59 `a4802fa` root vs pre-PT-59 engine copies, byte-identical trap) | SUPPORTED |
| C1–C4 merge/tag/suite/git-tree/ITERATIONS | Audit §A (FF-only proof), §E (ritual requirements); ladder precedent `40b3b40`; tag convention `engine/iterNN` @ branch head | SUPPORTED |
| D push | Audit §B4/E (linear remote, creds pattern, keyhound 286-FP baseline) | SUPPORTED |
| E1–E5 | Audit F4/F5/F6/F9/F10 | SUPPORTED |

## C. Contradictions found between SOURCE documents and their resolution

| # | Contradiction | Resolution (adopted in 02) |
|---|---|---|
| C-1 | Governing plan + report say import via `wt-iter66/engine` copy; iter65 plan (newest, owner decision) says ALL imports via root SDK, engine copy stays pre-PT-59 | Root SDK wins (newer owner decision; the other two texts simply predate it). Phase B. |
| C-2 | Report §Parallel-lane: "merge iter65 and iter66… both are main-tip descendants" — implies two merges | iter65 has ZERO commits (audit §A): nothing to merge. Phase C = iter66 only. The report's own caveat ("verify with git diff before merging") was the right instinct; the audit performed it: diff(iter65, iter66) == exactly the one iter66 commit. |
| C-3 | Report says wt-iter65 "@ 09bf87b" (work in flight); live state: iter65 @ 3ac4ac6, clean, PLAN ONLY | Branch was re-pointed to main tip per owner (recorded in iter65 plan §Compaction). No work exists; OFF-LIMITS stands. |
| C-4 | iter65 plan's suite baseline "427 passed" vs post-merge reality 439 | E2 re-baselines at iter65 kickoff. |
| C-5 | iter65 plan claims ladder "pushed (f5850e5..09bf87b)"; LIVE remote main = `dfc0926` (2026-09-08 era, 208 behind local — verified via token ls-remote) | Per owner 2026-09-22 the push topic is OUT OF SCOPE ("we are talking about local commits") — recorded as Phase-D context only; the closeout (merge/tag/docs) is fully local; no doc correction rides this procedure |
| C-6 | iter66 plan prescribes "foreground uvicorn"; serve_voice.sh (the "only legal launcher" per iter57) is detached + hardwired :8020 (busy) | Foreground direct uvicorn per the governing (newer) plan; serve_voice.sh's port-guard idea is preserved as the A1 `ss -tln` check. |
| C-7 | T7 needs browser access; no access method specified anywhere | A1: ssh tunnel (default, zero exposure) or Caddy route with MANDATORY token gate (public-endpoint-token-gate skill). |
| C-8 | Tag naming: report says `tag engine/iter66`; tags list has `engine/iter64` @ branch head | C3 tags `engine/iter66` at final branch head (6dc1ed8 or T7-fix head). |

## D. Gaps / redundancies check

- GAP: none found — every owner-gated item (keys, T7 go, merge word, push, hygiene) is explicit with its gate in 02.
- REDUNDANCY: none — Phases are strictly sequential with distinct gates; E-items are menu (opt-in), not auto-executed.
- OPEN ITEMS carried into 04: zero agent-resolvable; all remaining are owner gates by design (LAW 0).

## E. Preflight verdict

The action plan addresses every audit finding; every step is backed by verified box state; all eight source-document contradictions are resolved with the newer owner decision winning in each case. The plan is ready to consolidate into `04_master_plan.md`.
