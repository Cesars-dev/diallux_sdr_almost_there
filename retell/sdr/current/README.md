# Dialux SDR — V7.9_slot_lock

> Production sales SDR agent ("Linda", 9-state Retell multi-prompt machine) **plus** a local
> experimental harness that runs the exact same agent on raw GPT-5.2 with real bookings —
> $0 platform fees, full Langfuse observability.

Two halves, one repo:

```
├── retell/   THE AGENT ARTIFACT (production source of truth)
│   ├── llm.json                  built payload — deployed to Retell agent_f305981ef7b5ce312c1c899bbf
│   ├── prompts/                  general + 9 state prompts (source of truth for the build)
│   ├── tools/                    per-state tool definitions (webhooks, extract tools, booking)
│   ├── edges/                    state transitions (become transition_to_<State> functions)
│   ├── Knowledge bases/          9 markdown KBs (sales craft, industry, capabilities…)
│   ├── versions/                 deploy lineage: every iteration snapshotted, never patched
│   ├── deploy_v68.py             build+deploy: new LLM + new agent per deploy, KB registry reuse
│   ├── STATE.md / README.md      live status + folder map
│   └── DEPLOYED_llm_snapshot.json the payload currently live on Retell
│
└── lab/      THE EXPERIMENTAL ZONE (everything we're doing outside Retell)
    ├── engine.py                 Retell-LLM runtime replica — same llm.json on raw OpenAI
    ├── run_ladder.py             5-persona acceptance ladder (sequential, Cal-verified)
    ├── server.py + demo.html     client-facing demo chat (books real calls)
    ├── langfuse_bridge.py        full-conversation tracing into self-hosted Langfuse
    ├── analysis/                 CALL-ANALYSIS-SOP reports
    ├── README.md                 deep technical documentation
    └── AGENTS.md                 ops manual — read before touching anything
```

**Endpoints contract (for outside agents):** [`ENDPOINTS.md`](ENDPOINTS.md) · **Start reading here:** [`lab/README.md`](lab/README.md) (mechanics) → [`lab/AGENTS.md`](lab/AGENTS.md) (operating rules).

## Why this exists

Retell moved new workspaces to prepaid credits; ours ran dry mid-validation. Instead of stopping,
the agent's brain (gpt-5.2 + this exact prompt/tool artifact) runs directly on OpenAI while the
booking pipeline stays 100% production: real Cal.com slot reservations, real bookings, real
deterministic gates. Result: the full acceptance ladder (4/4 booking personas, including the one
that failed twice on Retell's native booking tool) validated at **~$0.50/run**, LLM latency
**0.84s avg** with the measured reasoning config, and every call traced end-to-end in Langfuse.

## Status (2026-09-03)

- Deployed on Retell: `agent_f305981ef7b5ce312c1c899bbf` / `llm_cd0464ddca4fa415cc7190cb7f7b`
  (workspace awaiting credits — this repo keeps development moving without it)
- Local ladder: Maria ✅ Danny ✅ Susan ✅ Marcus ✅ (bookings Cal-accepted, canceled after tests)
- Booking architecture: slot-lock (freeze-2-offer via Cal reservations) + idempotent custom
  booking endpoint + enum-latched intent gate (`reschedule`/`cancel`)
