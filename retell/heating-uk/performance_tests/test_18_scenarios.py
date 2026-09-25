#!/usr/bin/env python3
"""18-scenario runner: full-persona LLM-to-LLM over the V3.1 build.

Reuses the proven conversation loop from test_real_happy_path.py but loads
personas from personas/18/hvac_18_personas.py, injects today_uk at run time,
and writes an outcomes file. No source/config changes.

Usage:
  export RETELL_API_KEY=key_...
  export CHAT_AGENT_ID=<new agent_id>
  python3 test_18_scenarios.py               # run all 18
  python3 test_18_scenarios.py "S1" "S4"     # run a subset (by name or index)
"""

import importlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_real_happy_path import _today_uk, retell, run_scenario

personas = importlib.import_module("personas.18.hvac_18_personas")

RESULTS_PATH = "/home/julio/projects/Retell_AI_MCP_connection/data/18_scenario_results.json"


def resolve(sel):
    # Match "S1".."S18" or "1".."18" by index
    m = sel.strip().upper()
    if m.startswith("S") and m[1:].isdigit():
        idx = int(m[1:]) - 1
        if 0 <= idx < len(personas.SCENARIOS):
            return personas.SCENARIOS[idx]
    if m.isdigit():
        idx = int(m) - 1
        if 0 <= idx < len(personas.SCENARIOS):
            return personas.SCENARIOS[idx]
    # Match by first token (e.g. "(BOOK) Tom Redfern" -> "TOM")
    first = m.split("(", 1)[-1].split(")")[0].strip().split()[0]
    for s in personas.SCENARIOS:
        if first in s["name"].upper():
            return s
    raise SystemExit(f"Unknown selector: {sel}")


def main():
    if not os.environ.get("RETELL_API_KEY"):
        print("Set RETELL_API_KEY"); sys.exit(1)
    from test_real_happy_path import CHAT_AGENT
    print(f"Running against chat agent: {CHAT_AGENT}")

    sels = sys.argv[1:] or [s["name"] for s in personas.SCENARIOS]
    picks = [resolve(sel) for sel in sels]

    # Load any existing results so multiple invocations accumulate (not overwrite).
    results = []
    try:
        with open(RESULTS_PATH) as f:
            results = json.load(f)
    except Exception:
        results = []

    for sc in picks:
        sc = dict(sc)
        sc["dynvars"] = dict(sc["dynvars"])
        sc["dynvars"]["today_uk"] = _today_uk()  # inject fresh date
        r = run_scenario(sc)
        if r:
            r["expect"] = sc["expect"]
            results.append(r)
            with open(RESULTS_PATH, "w") as f:
                json.dump(results, f, indent=2)
    print(f"\n=== written {len(results)} total result(s) to {RESULTS_PATH} ===")


if __name__ == "__main__":
    main()
