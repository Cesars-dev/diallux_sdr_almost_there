# 01 AUDIT — iter57 voice closeout (plan `plans/plan_v5_iter57_voice_closeout_launcher.md`)

Date: 2026-09-19 · Auditor: agent · Every claim below was traced against the real box.

## 1. What EXISTS — verified facts

### 1.1 Worktree / branch state
| Claim | Verified | Evidence |
|---|---|---|
| Worktree `/tmp/opencode/wt-iter56` exists, clean @ `abde308` | ✅ | `git log --oneline -1` → `abde308 iter56 C2: observability fields…`; `git status --porcelain` → empty |
| Branch is `engine/iter56-state-delta-payload` | ✅ | `git branch --show-current` |
| `.venv` is a symlink → main venv | ✅ | `lrwxrwxrwx … .venv -> /home/julio/projects/clean_diallux_SDR/engine/.venv` |
| `.env` present in worktree (1372 B, Sep 18) | ✅ | `ls -la` |
| `.env` keys: OPENAI, RAG_* (incl. `RAG_EMBEDDING_MODEL`), RETELL, LANGFUSE, DEEPGRAM, CARTESIA, HTTP_PORT… | ✅ | key dump (names only) |

### 1.2 The launcher trap (root cause of the RAG-dead call) — CONFIRMED LIVE
- `/tmp/opencode/wt-iter56/engine/.venv/bin/uvicorn` line 1: `#!/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/dialux-langgraph-production-v5/.venv/bin/python3` — **the shebang trap is real**.
- That old venv's `pyvenv.cfg`: `include-system-site-packages = false`, home=/usr, py3.12.3.
- Old venv `import fastembed` → `fastembed.__file__ = None` (**namespace-stub false positive — reproduced**).
- Old venv `from fastembed import TextEmbedding` → `ImportError: cannot import name 'TextEmbedding' from 'fastembed' (unknown location)` — **reproduced**.
- Main venv: `fastembed 0.8.0` at `/home/julio/projects/clean_diallux_SDR/engine/.venv/lib/python3.12/site-packages/fastembed/__init__.py`; `TextEmbedding` import **OK**.
- `python -m uvicorn` in main venv: uvicorn **0.52.4** imports fine → the mandated launcher (`nohup .venv/bin/python -m uvicorn diallux.app:app …`) is sound.

### 1.3 Code surfaces the plan touches
| Surface | Exists | Detail |
|---|---|---|
| `diallux/app.py` `/health` | ✅ | `app.py:34-47` — returns 8 fixed fields (`ok, version, stt_mode, llm, tts, rag_mode, checkpoint, eager_eot, langfuse`). **No test asserts exact health keys** (grep `health` in `tests/test_units.py` → 0 hits) → adding 2 fail-safe fields is low-risk. App is 174 lines; imports are stdlib + fastapi + internal only (no fastembed import at module top — good; the embedder field must import lazily/fail-safe) |
| Greeting warm fire (voice-only) | ✅ | `media/session.py` ~195-215: `warm_rag` + full `warm_prompt_cache` + lite warm fire unconditionally (iter43/46/49 comments) |
| Eager RAG prefire on EOT (voice) | ✅ | `media/session.py` ~360-375: `spawn_live_retrieve(...)` best-effort, never raises |
| `micbridge-*` trace naming | ✅ | `session.py:137-139` — browser transport traces as `micbridge-<call_sid>` |
| `retrieve_lanes(lanes)` | ✅ | `diallux/rag.py:372` — lanes = `[{"query","scope"}]`, batched embed + concurrent pgvector; returns per-lane chunk lists; never raises |
| `get_kb_store(settings)` | ✅ | `diallux/rag.py:531` → `KBStore | None` |
| `Runtime._resolve_kb_store` | ✅ | `graph/builder.py:684` — latch only after success |
| Embedder | ✅ | `config.py:222` default `snowflake/snowflake-arctic-embed-m`; `_ensure_embed_fn` at `rag.py:287` |

### 1.4 Tooling on disk
| Tool | Status |
|---|---|
| `scripts/fake_twilio_call.py` | ✅ `--url/--input/--output` exactly as plan's fallback command |
| `scripts/lf.py` | ✅ `health/traces/show/gens/tools/usage/costs` — plan's T3 pulls supported |
| `scripts/live_sql.py` | ✅ `import --window --run --commit --db` — plan's ledger command valid |
| `scripts/hitl_ping.py` | ✅ exists; fail-safe (never blocks) |
| `scripts/voice_preflight.py` | ❌ does not exist yet (correct — plan creates it, File Map says NEW) |
| Ledger `research/surgeon/iter48-rag-truth/ledger.db` | ✅ 618 KB, Sep 18 11:25 |
| Surgeon folder `research/surgeon/iter56-state-delta-payload/` | ✅ has `01_report.md` + `02_sop_audit.md`; `03_voice_report.md` not yet (plan creates) |

### 1.5 Ports
- **:8020 FREE** (plan says down — verified).
- **:8000-:8003 LIVE** (python/uvicorn pids) — production untouched; the plan's deploy rules already forbid touching them.

## 2. Flaws / risks found (goes into cross-reference)

| # | Flaw | Severity | Resolution |
|---|---|---|---|
| F1 | Plan meta line 41 says TELEGRAM creds come "via `hitl_ping` fallback to video_strategy/.env" — **false as written**: `hitl_ping.py` only loads `engine/.env` (ROOT/`.env`) and the worktree `.env` has **no TELEGRAM keys**; a bare run prints "not configured — skipping" and exits 0 silently. | Medium (silent no-op) | Action plan must use the plan §47 export form (`export $(grep -E "^TELEGRAM_(BOT_TOKEN\|CHAT_ID)=" /home/julio/projects/video_strategy/.env \| xargs)`) before every hitl_ping call — never a bare invocation. Ping failure must be verified by stdout `hitl_ping: sent`. |
| F2 | `import fastembed` success is a false positive (namespace stub) — the health `embedder` field MUST NOT use a bare import check; it must verify `TextEmbedding` (as plan already decided) AND the preflight must run a real `retrieve_lanes` probe (plan already decided). | Confirmed in audit — decision already correct in plan | Carry into action plan verbatim; preflight exit-1 gate on TextEmbedding import + ≥1 chunk. |
| F3 | `/health` embedder field in `app.py`: `diallux.app` does not import fastembed at module top; a naive top-level import would poison app import in the OLD interpreter too (if someone ever mislaunches again). Field must be fail-safe (try/except, lazy) — plan says fail-safe, never raises. | Low (design constraint) | Action plan: lazy import inside try/except in the handler; on any failure report `embedder: "import-failed"` + `ok` stays True. |
| F4 | pytest `addopts = -q` in `pytest.ini` — plan's suite command passes `-o addopts=""` (correct) plus `-q`. Expected count 361 (from plan compaction); verify at T1 time and treat any count ≠ 361 as a stop-and-explain, not a proceed. | Low | Gate in action plan. |
| F5 | The preflight probe needs a `retrieve_lanes` call on the LIVE server (per plan: `--url http://127.0.0.1:8020`) — the script is a CLIENT of /health, but a `retrieve_lanes` probe can also run in-process. Plan wording: "prints chunk count" + `--url` arg. Ambiguity: does the probe run server-side (curl /health) or client-side? Resolution for action plan: preflight = two checks in one script: (a) check /health JSON fields (python_venv tail + embedder ok) via HTTP; (b) run ONE local in-process retrieve probe (main venv interpreter = same env the server runs in) against the pgvector store and print chunk count. Exit 1 on any failure. | Medium (ambiguity) | Resolved in action plan T1 spec. |
| F6 | Booking cleanup: chat battery bookings are mocked; the :8020 voice path books REAL slots on Cal event 3801235. PT-56 anomaly means a cancel by uid may hit the wrong record; owner may need to supply the Cal API key scope. Blocked-item stands. | Known / external | T4: cancel only bookings created this session; list-then-cancel by event window; if key scope unknown → ask owner (already a BLOCKED item). |

## 3. MISSING (things that must be created — matches plan File Map)
1. `scripts/voice_preflight.py` (NEW)
2. `/health` fields `python_venv` + `embedder` in `diallux/app.py` (E)
3. Test pin (new tiny `tests/test_voice_preflight.py` or test_units addition) (N/E)
4. `research/surgeon/iter56-state-delta-payload/03_voice_report.md` (N)
5. ITERATIONS.md iter56 ledger line (E, on branch)
6. `plans/PENDING_TASKS.md` PT-53/PT-55 flips + PT-45 note + PT-57 (E)

## 4. Verdict
Plan claims are **factually accurate** — every load-bearing statement reproduced live (shebang, stub, ports, worktree, tooling). One wording flaw (F1) and one ambiguity (F5) to resolve in the action plan. No code touched.
