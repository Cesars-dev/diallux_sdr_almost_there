# 03 CROSS-REFERENCE — iter58 plan vs audit vs action plan

Method: every load-bearing claim of `plans/plan_v5_iter58_eot08_public_mic.md` checked
against 01_audit.md findings; every change of 02_action_plan.md checked against the audit.
Contradictions/gaps/redundancies are numbered and resolved.

| # | Item | Plan says | Audit found | Resolution in 02 |
|---|---|---|---|---|
| X1 | File Map completeness | 4 engine files (app.py, index.html, metrics.py, new test file) | **F1: `tests/test_units.py:290-303` breaks** under the token gate (connects with no `k`, expects live handshake) | Edit 4 fixes the existing pin (deterministic setenv + `?k=`). File Map corrected. |
| X2 | Suite gate | "363 + N new pins (exact count from the pins written)" | Baseline 363 re-verified today (A1) | Exact gate pinned: **367** (363 + 4 new; Edit 4 modifies, adds none). Any other count = STOP. |
| X3 | session.py edit | "NO behavior change — threshold comes from env" | VERIFIED (E-claims): `DEEPGRAM_EAGER_EOT_THRESHOLD` → `Settings` → Deepgram URL param (deepgram_stt.py:82-83); no edit needed | No edit. ✓ |
| X4 | Token gate shape | "read query param k, compare VOICE_TEST_TOKEN env — mismatch or unset → await ws.close(code=4401)" | F6: accept-then-close is the observable shape (browser + TestClient); compare_digest for constant-time; never log `k` | Edit 1c implements exactly that. ✓ |
| X5 | Probe reply concurrency | "immediate server reply" (unspecified transport safety) | F5: writer task is the sole WS sender today; concurrent-send safety TESTED — safe under websockets 16.1.1 | Edit 1e sends directly; evidence cited. ✓ |
| X6 | caddy-apply | BLOCKED: "owner runs the apply" | F2: still true AT MY LAYER (opencode permission deny on `sudo *`) even with OS passwordless sudo granted | Owner runs it; alternative (permission rule `bash +sudo /usr/local/bin/caddy-apply*`) documented in 04 ASK. |
| X7 | DNS | BLOCKED: needs A record `voicetest` → 46.62.233.228 | A3: **still NXDOMAIN today** | Go-gate ASK: DNS record OR flores fallback. T2-alt block written (valid syntax). |
| X8 | Fallback "3-line JS prefix patch" | loose wording | F11: Caddy side needs `handle_path /voice/*` + `handle` wrapper (plan's inline-append wording is not valid Caddy); JS side is ONE line | Exact fallback block + 1-line JS change specified. |
| X9 | T3 restart | `kill $(cat pid); sleep 2; serve_voice.sh` | F14: launcher REFUSES busy port; race if old server lingers | Port-free check between kill and launch. ✓ |
| X10 | Inter-arrival measurement point | "observed from the mic WS receive loop" | F8: correct — `on_media` has no timestamps; app.py:157 is the transport boundary; browser-only (Twilio path excluded) | Edit 1d observes in `/mic/ws` loop, gated by `metrics_enabled`. ✓ |
| X11 | VOICE_TEST_TOKEN | owner sets in wt-iter58 `.env` | A7/F4: absent everywhere today; `serve_voice.sh` exports all `.env` → reaches `os.environ` | T3 sequence: token BEFORE restart (else fail-closed locks the owner out). ✓ |
| X12 | import_call.py T4 command | flags `--log --sid --branch --commit --port --model --trace --worktree` | A14: argparse matches exactly | Carried verbatim. ✓ |
| X13 | Telegram ping | export form + fires BEFORE every owner ask | A15: hitl_ping exits 0 always; success = stdout `hitl_ping: sent` (iter57 B10 lesson) | T4/T5 ping commands + stdout check. ✓ |
| X14 | Reference baselines (73-198 ms/chunk, EOT median 2203/4≤1s, first-5 e2e, TTFT 618-1182) | quoted from the 09-19 call analysis | Historical call-log facts (not re-derivable from code) — carried as-is for T4 comparison | Kept as gates' baselines. ✓ |
| X15 | "/health gains eager_eot_threshold (fail-safe)" | display-only field | F7: lru_cached Settings + session.py:176-177 mutation → field shows EFFECTIVE value | Implemented fail-safe; semantics documented. ✓ |
| X16 | Plan status "awaits owner go" + "stop at master plan" (this session) | — | — | Circle halts at 04; execution only on owner GO. |
| X17 | Untracked docs (plan file, CALL_FACTS.md, tasks/) | plan assumes CALL_FACTS.md is "tracked" | A13/F13: untracked on main; main ahead 5/behind 5 origin | One docs commit at T5 (LAW 0), owner-informed; NO push/pull this iter. |
| X18 | 4401 pin duplication risk | — | Edit 4 (test_units) arms the token but does NOT re-assert 4401; the new file owns the 4401 pins | No redundancy. ✓ |
| X19 | `count 1` determinism in the metrics pin | — | Only binary sender in the suite is the new test (grep-verified: test_units mic test sends text only); file order test_iter58_* < test_units_* | Exact assertion safe. ✓ |
| X20 | Plan's Langfuse :3001 commands | `lf.py health|traces|show` | LANGFUSE_HOST=http://localhost:3001 in .env (A7) — not exercised live in the circle | Used as-is at T4/T5; non-blocking. |
| X21 | Plan "Branch cut from 4cfb7a5 carries iter57's preflight + serve_voice.sh + /health fields" | — | VERIFIED (A5/A6 + files read at 4cfb7a5); running :8020 server = same diallux code | T0 cut is safe; T3 replaces pid 1741047 (F15: NOT a do-not-touch stale pid). ✓ |
| X22 | Old plan meta "363 passed" (iter57 state) | — | Re-confirmed 363 in 66.55 s today | Baseline anchored. ✓ |

**Verdict:** the plan was sound; the circle caught ONE breaking omission (X1), ONE
syntax-level correction (X8), ONE environment truth the owner's sudo offer cannot
change (X6), and tightened the suite gate (X2). No unresolved contradictions between
01, 02, and the plan. Open items are exclusively owner decisions (DNS, token, apply mode,
GO) — carried into 04.
