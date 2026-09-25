#!/usr/bin/env python3
"""latency_pull.py — instant P50/P90 latency analysis over the SQLite call ledger.

Reads ledger.db (runs/calls/rounds/rag — see SQL_ANALYSIS_SOP.md) and prints
percentile tables per run: TTFT, LLM, cache, tokens, per-state, RAG. No LLM
needed to read the output. Percentile method matches scripts/latency.py
(nearest-rank over the sorted sample).

Usage:
  python3 scripts/latency_pull.py                                  # all runs
  python3 scripts/latency_pull.py --run happy-f --run battery-iter48
  python3 scripts/latency_pull.py --run battery-iter48 --state Discovery
  python3 scripts/latency_pull.py --run happy-f --json

Ledger default: research/surgeon/iter48-rag-truth/ledger.db (override --ledger).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def pct(vals: list[float], q: float) -> float | None:
    if not vals:
        return None
    v = sorted(vals)
    return round(v[min(int(q * len(v)), len(v) - 1)])


def f(x: float | None) -> str:
    return "—" if x is None else f"{x:,.0f}"


def rows(con: sqlite3.Connection, sql: str, args=()) -> list[dict]:
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute(sql, args)]


def run_report(con: sqlite3.Connection, run_id: str, state_filter: str | None) -> dict:
    con.row_factory = sqlite3.Row
    where, args = "WHERE run_id=?", [run_id]
    if state_filter:
        where += " AND state=?"
        args.append(state_filter)
    rounds_list = [dict(r) for r in con.execute(
        f"SELECT trace_id, ts, state, ttft_ms, cache_read, input, output, llm_ms "
        f"FROM rounds {where} ORDER BY trace_id, ts", args)]
    if not rounds_list:
        return {"run": run_id, "rounds": 0}

    # turn-1 = first round per trace (first TTFT-bearing round per call)
    first_by_trace: dict[str, dict] = {}
    for r in rounds_list:
        first_by_trace.setdefault(r["trace_id"], r)
    turn1 = list(first_by_trace.values())
    order = {t: i for i, t in enumerate(first_by_trace)}
    steady = [r for r in rounds_list if r["trace_id"] in order and r is not first_by_trace[r["trace_id"]]]

    ttft = [r["ttft_ms"] for r in rounds_list if r["ttft_ms"]]
    ttft_steady = [r["ttft_ms"] for r in steady if r["ttft_ms"]]
    ttft_t1 = [r["ttft_ms"] for r in turn1 if r["ttft_ms"]]
    llm = [r["llm_ms"] for r in rounds_list if r["llm_ms"]]
    cache0 = [r for r in rounds_list if (r["cache_read"] or 0) == 0]
    cache_hits = [r["cache_read"] for r in rounds_list if (r["cache_read"] or 0) > 0]
    inp = [r["input"] for r in rounds_list if r["input"]]
    outp = [r["output"] for r in rounds_list if r["output"]]

    by_state: dict[str, list] = {}
    for r in rounds_list:
        if r["ttft_ms"] is not None:
            by_state.setdefault(r["state"], []).append(r["ttft_ms"])

    rag_args = list(args)
    rags = [dict(r) for r in con.execute(
        f"SELECT ms, chunks, cosine FROM rag WHERE trace_id IN "
        f"(SELECT DISTINCT trace_id FROM rounds {where}) "
        f"AND ms IS NOT NULL", rag_args)]
    rag_ms = [r["ms"] for r in rags if r["ms"] is not None]
    rag_chunks = [r["chunks"] for r in rags if r["chunks"] is not None]
    rag_cos = [r["cosine"] for r in rags if r["cosine"] is not None]

    calls_meta = [dict(r) for r in con.execute(
        "SELECT trace_id, persona, outcome, turns, passed FROM calls WHERE run_id=?", (run_id,))]

    return {
        "run": run_id,
        "rounds": len(rounds_list),
        "ttft_p50": pct(ttft, .50), "ttft_p90": pct(ttft, .90),
        "ttft_steady_p50": pct(ttft_steady, .50), "ttft_steady_p90": pct(ttft_steady, .90),
        "turn1_ttfts": [(t["ttft_ms"], t["cache_read"]) for t in turn1],
        "turn1_p50": pct(ttft_t1, .50),
        "llm_p50": pct(llm, .50), "llm_p90": pct(llm, .90),
        "cache0_rounds": len(cache0),
        "cache_hit_p50": pct(cache_hits, .50),
        "input_p50": pct(inp, .50), "output_p50": pct(outp, .50),
        "states": {s: {"n": len(v), "p50": pct(v, .50), "p90": pct(v, .90)}
                   for s, v in sorted(by_state.items())},
        "rag_ms_p50": pct(rag_ms, .50), "rag_ms_p90": pct(rag_ms, .90),
        "rag_chunks_p50": pct(rag_chunks, .50),
        "rag_cosine_p50": round(sum(rag_cos) / len(rag_cos), 3) if rag_cos else None,
        "n_rag_spans": len(rags),
        "calls": calls_meta,
    }


def print_report(rep: dict) -> None:
    print(f"\n=== {rep['run']} ===")
    if rep.get("rounds", 0) == 0:
        print("  no rounds in ledger for this run/filter")
        return
    print(f"  rounds={rep['rounds']}  rag_spans={rep['n_rag_spans']}")
    print(f"  TTFT      p50={f(rep['ttft_p50'])}  p90={f(rep['ttft_p90'])}")
    print(f"  TTFT-steady(turn2+) p50={f(rep['ttft_steady_p50'])}  p90={f(rep['ttft_steady_p90'])}")
    t1s = ", ".join(f"{f(t)}/{int(c)}" for t, c in rep["turn1_ttfts"])
    print(f"  turn-1    p50={f(rep['turn1_p50'])}  (ttft/cache per call): {t1s}")
    print(f"  LLM-dur   p50={f(rep['llm_p50'])}  p90={f(rep['llm_p90'])}")
    print(f"  cache-0 rounds={rep['cache0_rounds']}  cache-hit p50={f(rep['cache_hit_p50'])}")
    print(f"  tokens    in p50={f(rep['input_p50'])}  out p50={f(rep['output_p50'])}")
    if rep["n_rag_spans"]:
        print(f"  RAG       ms p50={f(rep['rag_ms_p50'])} p90={f(rep['rag_ms_p90'])}  "
              f"chunks p50={rep['rag_chunks_p50']}  cos_avg={rep['rag_cosine_p50']}")
    print("  per-state TTFT (n / p50 / p90):")
    for s, v in rep["states"].items():
        print(f"    {s:18s} {v['n']:4d}  {f(v['p50'])}  {f(v['p90'])}")
    for c in rep["calls"]:
        flag = "" if c["passed"] in (1, "PASS", "pass", "true", "True") else "  <-- FAIL"
        print(f"    call {c['persona'] or c['trace_id'][:12]:18s} turns={c['turns']} "
              f"outcome={c['outcome']}{flag}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default="research/surgeon/iter48-rag-truth/ledger.db")
    ap.add_argument("--run", action="append", help="run_id to report (repeatable; default=all)")
    ap.add_argument("--state", help="filter rounds by state name")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    path = Path(a.ledger)
    if not path.exists():
        raise SystemExit(f"ledger not found: {path.resolve()}")
    con = sqlite3.connect(path)
    if a.run:
        runs = a.run
    else:
        runs = [r[0] for r in con.execute("SELECT run_id FROM runs ORDER BY imported_at")]
    if not runs:
        raise SystemExit("no runs in ledger")

    reports = [run_report(con, r, a.state) for r in runs]
    if a.json:
        print(json.dumps(reports, indent=2, default=str))
    else:
        for rep in reports:
            print_report(rep)


if __name__ == "__main__":
    main()
