"""sop_mechanicals.py — CALL/HUMANIZED-SOP mechanical checks, one-shot.

Stdlib only. Input: one or more harness json_log files (tests/llm2llm/json_logs/).
Emits the per-call mechanical block (R1-R5 for HUMANIZED + CALL auto-checks) and,
with --rows-out, a ready sop-import JSON (HUMANIZED R1-R5 rows per call).

Usage:
  python3 scripts/sop_mechanicals.py /path/to/worktree/engine/tests/llm2llm/json_logs/*.json
  python3 scripts/sop_mechanicals.py --rows-out sop_rows.json <json_log...>

One block per call:
  header (persona/turns/pass/booked/ended/gate_rej/p50) · R1 robotic regex ·
  R3 tool-talk · R4 brackets · R5.1 bloat · R5.4 filler stack · R5.5 verbatim ·
  R5.7 mirroring · repeated-question scan (CALL redundancy/repetition).
"""
import glob
import json
import re
import sys

R1 = re.compile(r"I completely understand|I hear you|Certainly,|I'd be happy to|I understand how", re.I)
R3 = re.compile(r"validate_lead|slot_verified|dynamic variables|extract_|query_livecall|transition_to|record_reach|callback_number")
R4 = re.compile(r"\[OPTION|\{\{|<their |{{dv")
ACK = re.compile(r"\b(got it|makes sense|that makes sense|absolutely|totally fair|fair enough|understood)\b", re.I)


def mechanicals(path):
    d = json.load(open(path))
    t = d["transcript"]
    r1 = [(x["turn"], m.group(0)) for x in t for m in [R1.search(x["agent"] or "")] if m]
    r3 = [(x["turn"], m.group(0)) for x in t for m in [R3.search(x["agent"] or "")] if m]
    r4 = [(x["turn"], m.group(0)) for x in t for m in [R4.search(x["agent"] or "")] if m]
    bloat = [x["turn"] for x in t
             if len((x["agent"] or "").split()) > 40
             and len((x["caller"] or "").split()) <= 5]
    stack = [x["turn"] for x in t if len(ACK.findall(x["agent"] or "")) >= 2]
    sents = {}
    for x in t:
        for s in re.split(r"(?<=[.!?]) ", x["agent"] or ""):
            s = s.strip()
            if len(s.split()) >= 6:
                sents.setdefault(s, []).append(x["turn"])
    verbatim = {s: v for s, v in sents.items() if len(v) > 1}
    cmed = sorted(len((x["caller"] or "").split()) for x in t)[len(t) // 2]
    amed = sorted(len((x["agent"] or "").split()) for x in t)[len(t) // 2]
    mirror = "FAIL" if cmed <= 6 and amed > 25 else "OK"
    return {
        "file": path, "persona": d["persona"], "turns": d["turns"],
        "pass": d["pass"], "booked": d["booked"], "ended": d["ended"],
        "gate_rejections": d["gate_rejections"], "p50_ms": d.get("p50_ms"),
        "R1": r1, "R3": r3, "R4": r4,
        "R5.1": bloat, "R5.4": stack,
        "R5.5": [{"sentence": s[:80], "turns": v} for s, v in verbatim.items()],
        "R5.7": {"caller_med": cmed, "agent_med": amed, "verdict": mirror},
    }


def humanized_verdict(m):
    hard = len(m["R5.5"])
    graded = len(m["R5.1"]) + len(m["R5.4"]) + len(m["R5.7"] == "FAIL" and [1] or [])
    hits = len(m["R1"]) + len(m["R3"]) + len(m["R4"]) + graded
    if hard or hits >= 3:
        return "FAIL" if (hard or len(m["R4"]) >= 3) else "FAIL"
    if hits:
        return "PARTIAL"
    return "PASS"


def main():
    args = sys.argv[1:]
    rows_out = None
    if "--rows-out" in args:
        i = args.index("--rows-out")
        rows_out = args[i + 1]
        args = args[:i] + args[i + 2:]
    paths = []
    for a in args:
        paths.extend(glob.glob(a))
    out_rows = []
    for p in paths:
        m = mechanicals(p)
        print(f"== {m['persona'][:40]} turns={m['turns']} pass={m['pass']} booked={m['booked']} gate_rej={m['gate_rejections']} p50={m['p50_ms']}")
        print(f"   R1 robotic: {len(m['R1'])} {m['R1'][:3]}")
        print(f"   R3 tool-talk: {len(m['R3'])} {m['R3'][:3]}")
        print(f"   R4 brackets: {len(m['R4'])} {m['R4'][:2]}")
        print(f"   R5.1 bloat: {m['R5.1']}")
        print(f"   R5.4 filler-stack: {m['stack' if False else 'R5.4'] if False else m['R5.4']}")
        print(f"   R5.5 verbatim: {len(m['R5.5'])} {[v['sentence'][:60] for v in m['R5.5'][:2]] if m['R5.5'] else ''}")
        for v in m["R5.5"][:2]:
            print(f"      - {v['sentence'][:70]} turns={v['turns']}")
        print(f"   R5.7 mirror: {m['R5.7']}")
        print(f"   HUMANIZED verdict: {humanized_verdict(m)}")
        if rows_out:
            rows = []
            rows.append({"run_id": "", "trace_id": None, "sop": "HUMANIZED",
                         "category": "R1", "scope": "full call",
                         "verdict": "PARTIAL" if m["R1"] else "PASS",
                         "rule": "R1", "failure_reason": "robotic filler" if m["R1"] else "",
                         "failure_assessment": "minor polish" if m["R1"] else "",
                         "evidence": "; ".join(f"t{t}: {w}" for t, w in m["R1"][:3]),
                         "source": m["file"]})
            for cat in ("R2", "R3", "R4"):
                hits = m.get(cat, [])
                rows.append({"run_id": "", "trace_id": None, "sop": "HUMANIZED",
                             "category": cat, "scope": "full call",
                             "verdict": "PARTIAL" if hits else "PASS", "rule": cat,
                             "failure_reason": f"{len(hits)} hits" if hits else "",
                             "failure_assessment": "polish" if hits else "",
                             "evidence": str(hits[:3]), "source": m["file"]})
            for sub in ("R5.1", "R5.4"):
                hits = m[sub]
                if hits:
                    rows.append({"run_id": "", "trace_id": None, "sop": "HUMANIZED",
                                 "category": "R5", "scope": f"t{hits[0]}" if hits else "",
                                 "verdict": "PARTIAL", "rule": sub,
                                 "failure_reason": sub, "failure_assessment": "graded",
                                 "evidence": str(hits[:4]), "source": m["file"]})
            for v in m["R5.5"]:
                rows.append({"run_id": "", "trace_id": None, "sop": "HUMANIZED",
                             "category": "R5", "scope": f"t{v['turns']}",
                             "verdict": "FAIL", "rule": "R5.5",
                             "failure_reason": "verbatim sentence repeat (hard flag)",
                             "failure_assessment": "verbatim = template/concat, never accidental",
                             "evidence": f"{v['sentence'][:80]} turns={v['turns']}", "source": m["file"]})
            if m["R5.7"] == "FAIL":
                rows.append({"run_id": "", "trace_id": None, "sop": "HUMANIZED",
                             "category": "R5", "scope": "full call", "verdict": "FAIL",
                             "rule": "R5.7", "failure_reason": "no mirroring",
                             "failure_assessment": "energy/length adaptation failure",
                              "evidence": f"caller_med={m['R5.7']['caller_med']}w agent_med={m['R5.7']['agent_med']}w",
                              "source": m["file"]})
            out_rows.extend(rows)        # iter65 T5: accumulate ACROSS calls
    if rows_out:
        json.dump(out_rows, open(rows_out, "w"), indent=1)
        print(f"rows -> {rows_out} ({len(out_rows)})")


if __name__ == "__main__":
    main()
