#!/usr/bin/env python3
"""Build config-deployable llm.json from V6.6 source folders.

Folders are canonical:  prompts/ · tools/ · edges/
Output:                 llm.json (deploy payload — copy to MVP_agent/config/llm.json to deploy)

Top-level LLM settings (model, kb ids, dynamic variable seeds, ...) are carried
over from the existing llm.json untouched. Only general_prompt, begin_message,
general_tools, and each state's {state_prompt, tools, edges} are rebuilt from
the source folders.

Usage:
  python3 tools/build_llm_json.py            # build + validate, writes llm.json
  python3 tools/build_llm_json.py --check    # validate only, no write
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
STATES = ["Intake", "Discovery", "Closer", "Offer",
          "contact_details", "Booking", "Closing"]
TOKEN_CEILING = 2300  # user rule: main+state max ~2000, 2300 pushing it (warn-only)


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    check_only = "--check" in sys.argv
    llm_path = HERE / "llm.json"
    if not llm_path.exists():
        fail("llm.json not found — needed for top-level settings")
    old = json.loads(llm_path.read_text())

    new = {k: old[k] for k in old if k not in (
        "general_prompt", "begin_message", "general_tools", "states")}

    # --- prompts ---
    gp = (HERE / "prompts" / "general_prompt.md").read_text()
    bm = (HERE / "prompts" / "begin_message.txt").read_text().strip()
    gt = json.loads((HERE / "tools" / "general_tools.json").read_text())
    new["general_prompt"] = gp
    new["begin_message"] = bm
    new["general_tools"] = gt

    # --- states ---
    states = []
    for name in STATES:
        sp = HERE / "prompts" / "states" / f"{name}.md"
        tl = HERE / "tools" / f"{name}.tools.json"
        ed = HERE / "edges" / f"{name}.edges.json"
        for f in (sp, tl, ed):
            if not f.exists():
                fail(f"missing source file: {f}")
        states.append({
            "name": name,
            "state_prompt": sp.read_text(),
            "tools": json.loads(tl.read_text()),
            "edges": json.loads(ed.read_text()),
        })
    new["states"] = states

    # --- validation ---
    errors, warnings = [], []
    dv = set((new.get("default_dynamic_variables") or {}).keys())
    var_re = re.compile(r"\{\{(\w+)\}\}")
    kb_re = re.compile(r"##([\w-]+)-kb##")
    kb_files = {p.stem.replace(".md", ""): p for p in (HERE / "Knowledge bases").glob("*.md")}
    state_names = {s["name"] for s in states}

    for s in states:
        text = s["state_prompt"] + json.dumps(s["tools"]) + json.dumps(s["edges"])
        tok = (len(gp) + len(s["state_prompt"])) // 4
        if tok > TOKEN_CEILING:
            warnings.append(f"{s['name']}: main+state ~{tok} tokens > ceiling {TOKEN_CEILING} (runs hot)")
        else:
            print(f"  ok tokens: {s['name']:<16} main+state ~{tok}/2300")
        for v in var_re.findall(text):
            if v not in dv:
                warnings.append(f"{s['name']}: {{{{{v}}}}} not in default_dynamic_variables")
        for kb in kb_re.findall(text):
            if f"{kb}-kb" not in kb_files:
                errors.append(f"{s['name']}: KB marker ##{kb}-kb## has no file")
        for e in s["edges"]:
            if e.get("destination_state_name") not in state_names:
                errors.append(f"{s['name']}: edge -> unknown state {e.get('destination_state_name')}")
            req = e.get("parameters", {}).get("required", [])
            props = e.get("parameters", {}).get("properties", {})
            for r in req:
                if r not in props:
                    errors.append(f"{s['name']}: edge requires '{r}' not in properties")

    if warnings:
        for w in warnings:
            print(f"  warn: {w}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)

    if check_only:
        print("check OK (no write)")
        return

    llm_path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n")

    # parity proof: embedded == folder sources
    assert new["general_prompt"] == gp
    for s in states:
        assert s["state_prompt"] == (HERE / "prompts" / "states" / f"{s['name']}.md").read_text()
    print(f"built llm.json: {len(states)} states, parity verified")


if __name__ == "__main__":
    main()
