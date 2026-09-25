# 03 CROSS-REFERENCE — audit (01) vs action plan (02)

Question 1: Does the plan address every issue the audit found?
Question 2: Does the audit support every change the plan proposes?

## Audit findings → action plan coverage

| Audit flaw | Addressed in 02? | How | Status |
|---|---|---|---|
| F1 hitl_ping env: worktree `.env` has no TELEGRAM keys; bare run silently skips | T2.1 + T4.3 | Mandatory export form before every ping; verify stdout `hitl_ping: sent` | ✅ resolved |
| F2 `import fastembed` = namespace-stub false positive | T1.1 Check A + T1.2 | Health asserts `TextEmbedding` result, not bare import; preflight re-runs a real retrieve probe | ✅ resolved |
| F3 /health embedder field must be lazy + fail-safe; no module-top fastembed import | T1.2 | Lazy import inside try/except in handler; `ok` stays True on failure | ✅ resolved |
| F4 suite count gate (pytest.ini addopts=-q; expect 361→363) | T1.4 step 1 | `-o addopts=""` + explicit 363 gate + STOP on drift | ✅ resolved |
| F5 preflight `--url` ambiguity (server-side vs in-process probe) | T1.1 Check A/B | Split explicitly: Check A = HTTP /health client; Check B = in-process retrieve probe in the SAME main-venv env the server runs | ✅ resolved |
| F6 booking cancel risk (PT-56 anomaly, real event 3801235) | T4.1 | List-then-cancel only this session's uids; blocked item if key scope unknown | ✅ resolved (owner dependency stands) |

## Plan (original iter57 plan) → action plan coverage

| Plan task | Covered | Notes |
|---|---|---|
| T1 relaunch + self-check | T1.1-T1.4 | Exact launcher command carried verbatim; `.venv/bin/uvicorn` forbidden |
| T2 voice call | T2 | Mic primary, fake_twilio fallback — same order |
| T3 trace/gates/ledger | T3 | Import from MAIN checkout (AGENTS.md trap) — preserved |
| T4 closeout + ASK | T4 | Merge gate = hold for Julio |

## Gaps / contradictions found

| # | Issue | Verdict |
|---|---|---|
| G1 | Original plan File Map says test pin goes in `tests/test_units.py` "or a new tiny file". 02 chose the new file (`test_voice_preflight.py`) — fine, but T1.4's expected count must reflect exactly 2 new pins. | Consistent (363). Must re-check pin count at preflight stage. |
| G2 | Original plan preflight verification says "prints ≥1 chunk" — 02's Check B runs the probe **in-process** in the main venv, while the server runs the same env; but in-process ≠ server-process. A server-side embedder failure with a green in-process probe is possible only if env differs — same `.venv` symlink + same `.env` makes this near-impossible; Check A's `embedder: ok` already covers the server process itself (it proves TextEmbedding imports **inside the server process**). Combined A+B = full coverage. | Resolved — no contradiction |
| G3 | Audit said `ok stays True` on embedder import-fail (fail-safe design); original plan says "fail-safe, never raises" — consistent. But: could a green `ok: True` + `embedder: import-failed` be missed by an operator? Preflight Check A asserts `embedder == "ok"` → red. Covered. | Resolved |
| G4 | Ledger import window placeholder `<HH:MM-HH:MM>` must be filled from the actual call time — noted in T3.3. | Fine |
| G5 | 02 T1.2 adds `import sys` at module top of app.py — audit confirmed app.py has no `sys` import today (checked imports at lines 11-24: base64, json, logging, uuid, pathlib, fastapi, internal). Non-conflicting. | Fine |
| G6 | No contradiction between "docs ride the branch" (T4.2, iter56 pattern) and LAW 0 "md files → main". iter56 established the branch-rides-docs pattern for evidence files; PENDING_TASKS.md/ITERATIONS.md commits on the branch match the original plan's Deploy Rules. Keep as plan says (branch), flag at ASK. | Accepted, flagged |

## Verdict
No unresolved contradictions. All 6 audit flaws addressed. All 4 plan tasks mapped. → Proceed to preflight/master plan (04), which re-verifies the two code edits (app.py health shape, preflight imports) against real signatures before execution.
