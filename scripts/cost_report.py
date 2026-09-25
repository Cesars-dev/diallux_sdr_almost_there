#!/usr/bin/env python3
"""cost_report.py — spend on the Langfuse traces behind the SQLite call ledger.

Answers:
  * TOTAL spent across all Langfuse traces (all days).
  * Per-RUN cost for every run in the ledger (run_id -> traces via `calls`).
  * Per-MODEL breakdown (from Langfuse metrics/daily usage).

COST PROVENANCE (read this):
  The number is **Langfuse's computed cost** = provider-returned token usage
  (`usageDetails`) x Langfuse's own per-model price table (`inputPrice`, `outputPrice`,
  `usagePricingTierName`). It is **NOT** a provider-returned dollar amount — OpenAI's
  chat API returns tokens, not cost, and there is no per-call cost field in the
  response. So treat these as estimates from Langfuse's price table:
    - models with no price configured contribute **$0** (e.g. gpt-5.6-luna) and are
      reported as `unpriced`;
    - cached input tokens are currently charged at the full input price (no cache
      discount applied by the local calculation), so cached-heavy runs read high.

Usage:
  cd /home/julio/projects/clean_diallux_SDR
  set -a; . /tmp/opencode/wt-iter44/.env; set +a     # LANGFUSE_* keys
  python3 scripts/cost_report.py                      # total + per-run + per-model
  python3 scripts/cost_report.py --run battery-iter48
  python3 scripts/cost_report.py --hours 48 --json
  python3 scripts/cost_report.py --days 2026-09-10:2026-09-12

Env/ledger defaults:
  LANGFUSE_* from the environment, else the first .env found in
  ROOT/.env, ROOT/engine/.env, /tmp/opencode/wt-*/.env (override with --env-file).
  Ledger: research/surgeon/iter48-rag-truth/ledger.db (override --ledger).
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import math
import os
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER_DEFAULT = ROOT / "research" / "surgeon" / "iter48-rag-truth" / "ledger.db"

ENV_CANDIDATES = [
    ROOT / ".env",
    ROOT / "engine" / ".env",
    *sorted(glob.glob("/tmp/opencode/wt-*/.env")),
]
LF_KEYS = ("LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")


def _parse_env(path: Path) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def lf_env(env_file: str = "") -> tuple[str, str, str]:
    if all(os.environ.get(k) for k in LF_KEYS):
        return (os.environ["LANGFUSE_HOST"].rstrip("/"),
                os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_SECRET_KEY"])
    candidates = ([Path(env_file)] if env_file else []) + ENV_CANDIDATES
    for p in candidates:
        if p.is_file():
            e = _parse_env(p)
            if all(e.get(k) for k in LF_KEYS):
                return e["LANGFUSE_HOST"].rstrip("/"), e["LANGFUSE_PUBLIC_KEY"], e["LANGFUSE_SECRET_KEY"]
    sys.exit("LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY not found (env vars or --env-file); "
             "try: set -a; . /tmp/opencode/wt-iter44/.env; set +a")


class LF:
    def __init__(self, host: str, pk: str, sk: str):
        self.host = host
        self.auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()

    def get(self, path: str, **params) -> dict:
        url = f"{self.host}{path}"
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
        req = urllib.request.Request(url, headers={"Authorization": "Basic " + self.auth})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)

    def paginate(self, path: str, cap: int = 200, **params) -> list[dict]:
        out, page = [], 1
        while page <= cap:
            d = self.get(path, page=page, limit=params.pop("limit", 100), **params)
            data = d.get("data", [])
            out.extend(data)
            meta = d.get("meta", {})
            if page >= meta.get("totalPages", 1) or not data:
                break
            page += 1
        return out


def trace_cost(lf: LF, trace_id: str) -> tuple[float, int, int, dict]:
    """(cost_usd, n_generations, n_unpriced, model_costs) for one trace."""
    obs = lf.paginate("/api/public/observations", traceId=trace_id)
    ngen, unpriced, costs = 0, 0, []
    model_costs: dict[str, float] = {}
    for o in obs:
        if (o.get("type") or "").upper() != "GENERATION":
            continue
        ngen += 1
        c = o.get("calculatedTotalCost")
        if c is None:
            cd = o.get("costDetails") or {}
            c = cd.get("total")
        if (c is None or c == 0) and o.get("model"):
            unpriced += 1
        c = float(c or 0.0)
        costs.append(c)
        model_costs[o.get("model") or "(none)"] = \
            model_costs.get(o.get("model") or "(none)", 0.0) + c
    total = math.fsum(costs)  # math.fsum = exact float summation for money
    return total, ngen, unpriced, model_costs


def load_ledger(path: Path, run_filter: list[str]) -> list[dict]:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    q = ("SELECT c.trace_id, c.run_id, c.persona, r.window, r.session, "
         "COALESCE(s.branch,'') AS branch, COALESCE(s.commit_sha,'') AS commit_sha "
         "FROM calls c LEFT JOIN runs r ON r.run_id=c.run_id "
         "LEFT JOIN sessions s ON s.session=r.session WHERE 1=1")
    args: list = []
    if run_filter:
        q += " AND c.run_id IN (%s)" % ",".join("?" * len(run_filter))
        args += run_filter
    q += " ORDER BY c.run_id, c.persona"
    return [dict(r) for r in con.execute(q, args)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", default=str(LEDGER_DEFAULT))
    ap.add_argument("--run", action="append", help="limit to run_id(s); default all")
    ap.add_argument("--hours", type=float, default=0, help="only daily rows within N hours")
    ap.add_argument("--days", help="date range YYYY-MM-DD:YYYY-MM-DD (inclusive)")
    ap.add_argument("--env-file", default="")
    ap.add_argument("--model", help="restrict per-run breakdown to a model (e.g. gpt-5.4)")
    ap.add_argument("--by-day", action="store_true", help="print per-day cost (all runs) by model")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    host, pk, sk = lf_env(a.env_file)
    lf = LF(host, pk, sk)

    # ---- daily cost (fast, covers ALL traces) + per-model ----
    daily = lf.paginate("/api/public/metrics/daily", limit=100)
    if a.days:
        lo, hi = a.days.split(":")
        daily = [r for r in daily if lo <= r["date"] <= hi]
    elif a.hours:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=a.hours)).date().isoformat()
        daily = [r for r in daily if r["date"] >= cutoff]
    daily_total = math.fsum(float(r.get("totalCost") or 0) for r in daily)
    total_traces = sum(int(r.get("countTraces") or 0) for r in daily)

    model_agg: dict[str, dict] = {}
    for r in daily:
        for u in r.get("usage", []):
            m = u.get("model") or "(none)"
            e = model_agg.setdefault(m, {"gens": 0, "in": 0, "out": 0, "cost": 0.0})
            e["gens"] += int(u.get("countObservations") or 0)
            e["in"] += int(u.get("inputUsage") or 0)
            e["out"] += int(u.get("outputUsage") or 0)
            e["cost"] += float(u.get("totalCost") or 0)

    # ---- per-run cost (ledger-scoped: run_id -> trace_id -> generations) ----
    calls = load_ledger(Path(a.ledger), a.run or [])
    runs: dict[str, dict] = {}
    trace_totals: list[tuple[str, float, int, int]] = []
    for c in calls:
        cost, ngen, unpriced, mc = trace_cost(lf, c["trace_id"])
        trace_totals.append((c["trace_id"], cost, ngen, unpriced))
        e = runs.setdefault(c["run_id"], {
            "run_id": c["run_id"], "session": c["session"] or "", "branch": c["branch"],
            "commit_sha": c["commit_sha"], "window": c["window"] or "",
            "calls": 0, "cost": 0.0, "unpriced_gens": 0, "models": {},
        })
        e["calls"] += 1
        e["cost"] += cost
        e["unpriced_gens"] += unpriced
        for m, v in mc.items():
            e["models"][m] = e["models"].get(m, 0.0) + v
    for e in runs.values():
        e["cost_per_call"] = (e["cost"] / e["calls"]) if e["calls"] else 0.0
    ledger_total = math.fsum(e["cost"] for e in runs.values())
    ledger_traces = len(trace_totals)

    if a.json:
        print(json.dumps({
            "langfuse_total_cost": daily_total,
            "langfuse_traces": total_traces,
            "by_model": model_agg,
            "by_run": sorted(runs.values(), key=lambda r: -r["cost"]),
            "ledger_attributed_cost": ledger_total,
            "ledger_traces": ledger_traces,
            "unattributed_cost": daily_total - ledger_total,
            "note": "Langfuse-computed cost (tokens x Langfuse price table); NOT provider-returned USD.",
        }, indent=2, default=str))
        return 0

    f = lambda x: f"${x:,.4f}" if abs(x) < 1 else f"${x:,.2f}"
    print(f"\n=== TOTAL SPENT (Langfuse, all traces) ===  {f(daily_total)}   "
          f"traces={total_traces}")
    print("  (Langfuse-computed = provider tokens x Langfuse price table; NOT provider USD)")
    if daily:
        print(f"  window: {daily[-1]['date']} .. {daily[0]['date']}  ({len(daily)} days)")
    print("\n=== BY MODEL ===")
    print(f"  {'model':16s} {'gens':>7s} {'in':>12s} {'out':>10s} {'cost':>12s}")
    for m, e in sorted(model_agg.items(), key=lambda kv: -kv[1]["cost"]):
        if a.model and m != a.model:
            continue
        tag = "  <-- UNPRICED ($0)" if e["cost"] == 0 and m != "(none)" and e["gens"] else ""
        print(f"  {m:16s} {e['gens']:>7d} {e['in']:>12,} {e['out']:>10,} {f(e['cost']):>12s}{tag}")

    if a.model or a.by_day:
        models = sorted({(u.get("model") or "(none)") for r in daily for u in r.get("usage", [])
                         if u.get("totalCost")})
        if a.model:
            models = [m for m in models if m == a.model]
        print("\n=== BY DAY (all traces; each date ~ a session/battery) ===")
        print(f"  {'date':11s} {'traces':>6s} " + "".join(f"{m[:10]:>11s}" for m in models)
              + f" {'day total':>11s}")
        for r in sorted(daily, key=lambda r: r["date"]):
            cells = []
            for m in models:
                c = math.fsum(float(u.get("totalCost") or 0) for u in r.get("usage", [])
                              if (u.get("model") or "(none)") == m)
                cells.append(f"{f(c):>11s}")
            print(f"  {r['date']:11s} {int(r.get('countTraces') or 0):>6d} " + "".join(cells)
                  + f" {f(float(r.get('totalCost') or 0)):>11s}")

    print("\n=== BY RUN (ledger-attributed) ===")
    hdr = f"  {'run_id':16s} {'calls':>5s} {'cost':>11s} {'$/call':>9s}"
    if a.model:
        hdr += f" {a.model:>11s}"
    hdr += f"  {'session':24s} branch@commit"
    print(hdr)
    key = (lambda r: -r["models"].get(a.model, 0.0)) if a.model else (lambda r: -r["cost"])
    for r in sorted(runs.values(), key=key):
        un = f" (+{r['unpriced_gens']} unpriced gens)" if r["unpriced_gens"] else ""
        sc = f"{r['branch']}@{r['commit_sha']}" if r["branch"] else "-"
        line = (f"  {r['run_id']:16s} {r['calls']:>5d} {f(r['cost']):>11s} "
                f"{f(r['cost_per_call']):>9s}")
        if a.model:
            line += f" {f(r['models'].get(a.model, 0.0)):>11s}"
        line += f"  {r['session']:24s} {sc}{un}"
        print(line)
    print(f"\n  ledger-attributed total = {f(ledger_total)} over {ledger_traces} traces")
    print(f"  unattributed (runs not imported into the ledger) = {f(daily_total - ledger_total)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
