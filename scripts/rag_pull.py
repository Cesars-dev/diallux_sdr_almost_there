#!/usr/bin/env python3
"""rag_pull.py — RAG-ANALYSIS SOP read-side SDK (stdlib only).

Companion to docs/Testing_guidelines/RAG-ANALYSIS-SOP.md. Reads the SQLite
ledger (`runs/calls/rag`), optionally joins the Langfuse rag-span enrichment
(kbs/pinned/lanes — fields the ledger import does not carry, cached by the
engine-side fetcher), and prints the per-call RAG evidence tables + gates.

Usage (main repo, python3):
  python3 scripts/rag_pull.py --run <run_id>                 # per-call summary
  python3 scripts/rag_pull.py --run <run_id> --rounds        # per-round table
  python3 scripts/rag_pull.py --run <run_id> --rounds --state Discovery
  python3 scripts/rag_pull.py --run <run_id> --zero          # zero-hit/degraded rounds only
  python3 scripts/rag_pull.py --run <run_id> --pin           # pin-block coverage table
  python3 scripts/rag_pull.py --run <run_id> --gates         # RAG gate line vs thresholds

Enrichment sidecar (kbs/pinned/lanes per rag span) is JSON at
  research/surgeon/iter63-rag-fire-sim/rag_span_enrichment_<run>.json
Produced by the engine-side collector (see SOP §3); without it the SDK still
works from the ledger alone (degraded/zero flags only).

Gates (iter61/62 calibration):
  degraded% <= 10 on chat sim (mic gate is per LATENCY-PERCENTILE-SOP)
  query-empty rate = 0
  await p50 <= 80 ms (hybrid consume cap is 60)
  pin coverage: >0 once industry dv known
"""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "research", "surgeon", "iter48-rag-truth", "ledger.db")
ENRICH_DIR = os.path.join(ROOT, "research", "surgeon", "iter63-rag-fire-sim")


def _load_enrich(run):
    # iter64: sidecars live in their iteration's evidence folder
    # (research/surgeon/iterNN-slug/) — glob instead of one hardcoded dir.
    import glob
    hits = glob.glob(os.path.join(
        ROOT, "research", "surgeon", "*", f"rag_span_enrichment_{run}.json"))
    path = hits[0] if hits else os.path.join(
        ENRICH_DIR, f"rag_span_enrichment_{run}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _calls(con, run):
    return con.execute(
        "SELECT trace_id, trace_name, persona, turns, passed FROM calls "
        "WHERE run_id=? ORDER BY ts", (run,)).fetchall()


def _rag_rows(con, run, tid=None):
    cols = ("kind, state, ms, chunks, query, mode, degraded, await_ms, "
            "kbs, pinned, lanes, zero_hit")
    if tid:
        rows = list(reversed(con.execute(
            f"SELECT trace_id, {cols} "
            "FROM rag WHERE run_id=? AND trace_id=? ORDER BY id", (run, tid)).fetchall()))
    else:
        rows = list(reversed(con.execute(
            f"SELECT trace_id, {cols} "
            "FROM rag WHERE run_id=? ORDER BY id", (run,)).fetchall()))
    return rows


def _match_enrich(enrich, tid, row):
    """PT-59 (iter64): the ledger rag table now carries kbs/pinned/lanes/
    zero_hit natively — the sidecar is only a fallback for pre-iter64 rows."""
    if row["kbs"] is not None or row["pinned"] is not None:
        return {"kbs": (row["kbs"] or "").split(",") if row["kbs"] else [],
                "pinned": row["pinned"] or "",
                "zero_hit": row["zero_hit"]}
    spans = enrich.get(tid) or []
    for s in spans:
        if s.get("state") == row["state"] and (s.get("query") or "") == (row["query"] or ""):
            return s
    return None


def summary(con, run, enrich):
    calls = _calls(con, run)
    print(f"run={run} calls={len(calls)}")
    print(f"{'persona':30s} rag lands zero_hit q_empty pin_rounds pin_tags await_p50")
    tot = {"rounds": 0, "land": 0, "zero": 0, "qempty": 0, "pin": 0}
    for c in calls:
        rows = _rag_rows(con, run, c["trace_id"])
        if not rows:
            continue
        aws = sorted((r["await_ms"] or 0) for r in rows)
        p50 = aws[len(aws) // 2]
        land = sum(1 for r in rows if not r["degraded"])
        zero = sum(1 for r in rows if (r["zero_hit"] if r["zero_hit"] is not None
                                      else (r["chunks"] or 0) == 0))
        qempty = sum(1 for r in rows if not r["query"])
        pins, tags = 0, set()
        for r in rows:
            s = _match_enrich(enrich, c["trace_id"], r) or {}
            if s.get("pinned"):
                pins += 1
                tags.add(s["pinned"])
        no_pin = len(rows) - pins
        print(f"{(c['persona'] or c['trace_name'])[:30]:30s} {len(rows):5d} {land:5d} "
              f"{zero:5d} {qempty:7d} {pins:5d} {','.join(sorted(tags))[:40]:40s} {p50:6.1f}")
    rows = _rag_rows(con, run)
    land = sum(1 for r in rows if not r["degraded"])
    zero = sum(1 for r in rows if (r["zero_hit"] if r["zero_hit"] is not None
                                      else (r["chunks"] or 0) == 0))
    qempty = sum(1 for r in rows if not r["query"])
    pins = 0
    for r in rows:
        s = _match_enrich(enrich, r["trace_id"], r) or {}
        if s.get("pinned"):
            pins += 1
    n = len(rows)
    if n:
        print(f"TOTAL rounds={n} land={land} ({100 * land / n:.0f}%) zero_hit={zero} "
              f"({100 * zero / n:.0f}%) q_empty={qempty} pin_rounds={pins} "
              f"({100 * pins / n:.0f}%)")


def rounds(con, run, enrich, state=None, only_zero=False):
    for c in _calls(con, run):
        rows = _rag_rows(con, run, c["trace_id"])
        name = c["persona"] or c["trace_name"]
        for i, r in enumerate(rows, 1):
            if state and r["state"] != state:
                continue
            if only_zero and (r["chunks"] or 0) != 0:
                continue
            s = _match_enrich(enrich, c["trace_id"], r) or {}
            q = (r["query"] or "")[:70]
            kbs = ",".join(s.get("kbs") or [])[:40]
            pin = s.get("pinned") or "-"
            print(f"[{i:3d}] {r['state']:15s} ch={r['chunks'] or 0} degr={r['degraded']} "
                  f"aw={r['await_ms'] or 0:>6} pin={pin[:28]:28s} kbs={kbs:40s} q={q[:70]}")
            if not r["chunks"] and r["query"]:
                pass


def pin_table(con, run, enrich):
    for c in _calls(con, run):
        rows = _rag_rows(con, run, c["trace_id"])
        tags, pin_only, no_pin = {}, 0, 0
        for r in rows:
            s = _match_enrich(enrich, c["trace_id"], r) or {}
            if s.get("pinned"):
                tags[s["pinned"]] = tags.get(s["pinned"], 0) + 1
                if (r["chunks"] or 0) == 0:
                    pass
        pins = [r for r in rows if (_match_enrich(enrich, c["trace_id"], r) or {}).get("pinned")]
        pin_only = sum(1 for r in rows
                       if (_match_enrich(enrich, c["trace_id"], r) or {}).get("pinned")
                       and (r["chunks"] or 0) == 0)
        print(f"{(c['persona'] or c['trace_name'])[:30]:30s} rounds={len(rows)} "
              f"pin_rounds={len(rows) - no_pin if False else sum(1 for r in rows if (_match_enrich(enrich, c['trace_id'], r) or {}).get('pinned'))} "
              f"pin_only_no_vector={pin_only} tags={tags}")


def gates(con, run, enrich):
    rows = _rag_rows(con, run)
    n = len(rows)
    if not n:
        print("no rag rows")
        return
    land = sum(1 for r in rows if not r["degraded"])
    zero = sum(1 for r in rows if (r["zero_hit"] if r["zero_hit"] is not None
                                      else (r["chunks"] or 0) == 0))
    qempty = sum(1 for r in rows if not r["query"])
    pins = sum(1 for r in rows if (_match_enrich(enrich, r["trace_id"], r) or {}).get("pinned"))
    aws = sorted((r["await_ms"] or 0) for r in rows)
    p50 = aws[len(aws) // 2]
    served = sum(1 for r in rows
                 if (r["chunks"] or 0) > 0
                 or (_match_enrich(enrich, r["trace_id"], r) or {}).get("pinned"))
    print(f"GATES run={run}")
    print(f"  rounds            = {n}")
    print(f"  served_rate       = {served}/{n} = {100 * served / n:.0f}%  (chunked OR pin-block; TRUE knowledge-delivery rate)")
    print(f"  land_rate         = {100 * land / n:.0f}%  (span-degraded flag; inflated by pin-only rounds) {'PASS' if land / n >= 0.90 else 'FAIL'}")
    print(f"  degraded_rate     = {100 * (n - land) / n:.0f}%  (gate <= 10%) {'PASS' if (n - land) / n <= 0.10 else 'FAIL'}")
    print(f"  query_empty_rate  = {qempty}/{n} = {100 * qempty / n:.1f}%  (gate = 0%) {'PASS' if qempty == 0 else 'FAIL'}")
    print(f"  zero_hit_rate     = {100 * zero / n:.0f}%  (honest-empty; investigate KB gaps if > 15%)")
    print(f"  await_p50_ms      = {p50}  (gate <= 80) {'PASS' if p50 <= 80 else 'FAIL'}")
    print(f"  pin_coverage      = {100 * pins / n:.0f}%  (once industry known; >0 required)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", required=True)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--rounds", action="store_true", help="per-round detail")
    ap.add_argument("--state", help="filter rounds by state")
    ap.add_argument("--zero", action="store_true", help="only zero-chunk rounds")
    ap.add_argument("--pin", action="store_true", help="pin coverage table")
    ap.add_argument("--gates", action="store_true", help="gate line only")
    a = ap.parse_args()
    con = sqlite3.connect(a.db)
    con.row_factory = sqlite3.Row
    enrich = _load_enrich(a.run)
    if a.rounds:
        rounds(con, a.run, enrich, a.state, getattr(a, "zero", False))
    elif a.pin:
        pin_table(con, a.run, enrich)
    elif a.gates:
        gates(con, a.run, enrich)
    else:
        summary(con, a.run, enrich)
        gates(con, a.run, enrich)


if __name__ == "__main__":
    main()
