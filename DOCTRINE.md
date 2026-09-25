# DOCTRINE.md — The Law of This Repo

> Not suggestions. If a rule here conflicts with convenience, convenience loses.
> Companion: STRUCTURE.md (architecture) · AGENTS.md (operations) · GIT_TREE.md (living map).

---

## ⚖️ LAW 0 — THE GIT CRYSTAL BALL (v2, refined 2026-09-08 by Julio)

**Git history is Julio's crystal ball. What matters is WHAT you're changing:**

1. **CODE = full discipline.** Any change to code, prompts, agent configs (`llm.json`,
   tools, edges), KBs, or `services/` → branch `engine/iterNN-<slug>` per an approved
   plan → commit on the branch → suite + battery → report → **ASK**.
   **NO merges of code branches without Julio's explicit say-so. Ever.**
   Green tests don't merge. Receipts don't merge. Only Julio's literal words merge.
2. **DOCS = straight to main.** Markdown only — README, AGENTS.md, DOCTRINE.md,
   GIT_TREE.md, STRUCTURE.md, MIGRATION_MAP.md, `plans/*`, `notes.md`, ITERATIONS.md,
   surgeon-report pointers → **commit + push directly to main, no branch, no ceremony.**
   "Nothing harmful" means: never put secrets, credentials, or evidence bulk in them
   (evidence stays in gitignored `research/` — that is not a docs exception).
3. **History surgery = say-so, always:** rebase, force-push, branch delete/rename,
   cherry-pick, history rewrite. **Tags** only ever accompany owner-approved merges.
4. Violations = revert on sight, no discussion.

---

## 1. The one rule that caused this restructure

**Iteration state lives in GIT, not in FOLDERS.** The old workspace carried ~15 copies
of the engine (9 snapshot folders, two same-named twins where the *typo* was live,
a state_machine copy, a Mac mirror) and ~28 version folders for the Retell line.
Folder-photocopies are how the typo-twin disaster happened: no diff, no blame, no
merge — just drift. That era is over.

```
THE ITERATION LOOP (mandatory, in order):

   plan ──► branch ──► iterate ──► test ──► report ──► commit ──► merge/abandon
   │         │           │          │         │           │
   plans/   engine/     ONE        suite +   research/   normal    merge = green
   plan_    iterNN-     VARIABLE   battery   surgeon/    commits    + receipts
   iterNN   <slug>      per iter   (SOPs)    iterNN.md   on branch  + docs
   _*.md    (engine/*)             ladder
```

- **plan:** every iteration starts as `plans/plan_<line>_iterNN_<slug>.md`
  (SOP: plans/SOP_NEW_PLAN.md). No plan, no branch.
- **branch:** `engine/iterNN-<slug>` — branched from `engine/main` (or from a parent
  iter branch when explicitly chained, e.g. iter31-c3 → c3b → c3c → c3d).
- **iterate:** ONE variable per iteration (a model swap, a gate, a prompt family, a
  cache architecture). If you're changing two things, that's two iterations.
- **test:** the acceptance ladder (first-13 regular + stress/curve + GK/breaker sets)
  per docs/Testing_guidelines/. Happy-path gate first — never stress a broken flow.
- **report:** surgeon report lands in `research/surgeon/<iterNN-slug>/NN_*.md`
  (evidence zone — never inside engine/ or retell/). Verdict + carry-forward queue.
- **commit:** normal commits on the iteration branch; message prefix `iterNN:`.
- **MERGE = OWNER GATE.** The loop ends at "everything green + report written + here's
  the one-paragraph summary". Then the agent ASKS. `git merge` happens ONLY when Julio
  says so. No autonomous merges, ever.
- **merge/abandon (on owner GO):** merge to `engine/main` only with green suite +
  battery receipts. Abandoned forks stay as branches with a one-line verdict in
  ITERATIONS.md §ledger. **No folder copies. No snapshots. Ever.**

**Glossary (the three git words people trip on):**
- **commit** — save a snapshot of your work on your branch. Invisible to main.
- **merge --no-ff** — bring the branch into main FORCING a visible merge commit, so the
  iteration stays a readable block in main's history (no fast-forward = no blended history).
- **tag** — a permanent name pinned to a commit (`engine/iter28`): the zero-cost
  replacement for folder snapshots. `git checkout engine/iter28` recreates that state forever.

## 2. Branch discipline — when to work where

| Situation | Action |
|---|---|
| Docs fix, typo, README, GIT_TREE refresh | commit **straight to `main`** + push — LAW 0 v2: docs are free |
| Any code/prompt/model/KB change | branch `iterNN-<slug>` first. No exceptions |
| Chained sub-experiments (like C3→C3d) | branch from the parent branch; merge the whole stack when the family is proven |
| Hotfix to a deployed artifact | new version folder in `retell/sdr/versions/` + MANIFEST entry + tag. **Never patch a deployed version in place** (Retell line is immutable-artifact) |
| "I want to try something weird" | still a branch. Cost is one `git switch -c` |
| Two experiments at once | two branches. If they must interact, that's a design smell — split or sequence them |

**Size tiers — how much process a change deserves:**

| Tier | Change | Process |
|---|---|---|
| **0 — trivial** | docs, README/AGENTS/GIT_TREE edits, typos, comments, plan files | commit **straight to main** + push. No branch, no ceremony (LAW 0 v2) |
| **1 — iteration** | any code / prompt / model / KB / config change | FULL loop + owner GO before merge |
| **2 — deploy** | anything that touches `retell/sdr/current/`, `services/`, agent IDs, or systemd | full loop + owner GO + explicit cutover plan (MIGRATION_MAP checklist) |

**Never:** commit on a branch you didn't name after a plan; keep two iterations mixed
in one branch; delete a branch without a verdict note in ITERATIONS.md.

## 3. Merge rules

0. **LAW 0 — OWNER GATE: NO merge of a CODE branch without Julio's explicit say-so. A
   plain "merge it" from Julio counts; nothing else does.** (Docs never need merges —
   they go straight to main per LAW 0 v2.) Everything below are preconditions — not
   permissions, not triggers.
1. **Green suite + battery receipts or no merge.** The pytest suite
   (`engine/.venv/bin/python -m pytest engine/tests -q`, expect the current count)
   must pass, and the battery verdict must be in the surgeon report.
2. **Squash vs preserve:** default is MERGE COMMIT (`--no-ff`) so the iteration's
   commit trail stays visible as a block on main. Never rebase published history.
3. **After every merge:** run `scripts/git-tree.sh` to regenerate GIT_TREE.md, and
   update ITERATIONS.md §ledger (one line: iterNN — verdict — branch — tag).
   **GIT_TREE.md must never be more than one iteration stale.**
4. **Conflicts:** the iter branch rebases onto the latest main; main never chases branches.
5. **Tags:** every merged iteration gets `engine/iterNN` tag at the merge commit.
   Snap-era history (pre-iter21) lives as `engine/snap-*` branches — treat them as
   read-only archaeology; never branch new work from them.

## 4. Zones — what lives where (and never crosses)

| Zone | Path | Rate of change | Git? |
|---|---|---|---|
| The product | `engine/` | daily | yes (engine/* refs = its history) |
| Deployed artifacts | `retell/sdr/current/` + `versions/` | per deploy | yes, tagged, read-only lineage |
| UK agent line | `retell/heating-uk/` | weekly | yes |
| Live infra | `services/` | per deploy window | yes (independent deployables) |
| Reference docs | `docs/` | monthly | yes |
| Process | `plans/` | per iteration | yes (live files + archive/) |
| Evidence | `research/` | write-once | **gitignored** (transcripts, surgeon reports, batteries, dumps) |
| Cold dead weight | `_cold_archive/` | never | **gitignored tarballs only** |
| Secrets | `*/.env` | as needed | **gitignored, never committed, never in remotes/URLs** |

**Hard boundaries:** nothing from `research/` ever enters `engine/` or `retell/`;
nothing in `_cold_archive/` is ever resurrected without an explicit plan + Julio's OK
(each resurrection = a fresh branch + MANIFEST note); `.env` files never leave disk
they live on (engine has its own; services have their own; root has none).

## 5. Security law

1. **No tokens in URLs. Ever.** (The V7.9 repo shipped a PAT inside its remote URL —
   that class of mistake is why this section exists.) Auth goes through credential
   helpers or headers at push time.
2. `scripts/keyhound` (secret-scan) runs before every push. A push that fails it
   doesn't get forced — it gets fixed.
3. `.env`, `*.db`, `*.db-*`, OAuth JSONs, `slots.db*` are gitignored by default (see
   .gitignore). Adding a new secret type = adding the ignore pattern FIRST.
4. Known-contaminated history (the PAT) is documented in MIGRATION_MAP.md; rotation
   is an owner action, tracked in plans/PENDING_TASKS.md until done.

## 6. Systemd / live-service cutover law

The ORIGINAL workspace (`/home/julio/projects/Retell_AI_MCP_connection/`) still serves
:8000–8003. This repo does NOT touch it. Cutover happens only as an explicit plan:
repoint the 3 systemd units' WorkingDirectory/ExecStart to `services/*` here, restart,
verify via `scripts/bridge.py`, then freeze the original. Until that day: **no service
in this repo binds a live port.**

## 7. The freshness contract

Any agent (human or AI) opening this repo must be able to answer, in under 60 seconds,
from the root files alone:
1. What is the current state? → README.md §status + AGENTS.md
2. Where does X live? → GIT_TREE.md + MIGRATION_MAP.md
3. How do I run/test/deploy? → AGENTS.md runbooks
4. What's the history of iteration NN? → `engine/*` branch + ITERATIONS.md + research/surgeon/

If any of those four takes longer, the docs are broken — fixing them is priority zero.
