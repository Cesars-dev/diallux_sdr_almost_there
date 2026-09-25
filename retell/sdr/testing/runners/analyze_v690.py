import json, re, os

BASE = "/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/V6.8/"
PERSONA = {}
for i in range(13):
    for line in open(f"/tmp/opencode/p{i}.log"):
        if line.startswith("START"):
            PERSONA[line.split("chat_")[1].split(".json")[0] if "chat_" in line else None] = None

# map persona names via logs (START line precedes; saved line has chat id)
order = []
for i in range(13):
    start = saved = None
    for line in open(f"/tmp/opencode/p{i}.log"):
        if line.startswith("START"): start = line.strip()
        if "saved:" in line: saved = line.strip().split("saved: ")[1].split("/")[-1]
    order.append((start, saved))

for start, saved in sorted(order, key=lambda x: x[0]):
    f = "/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/V6.8/tools/json_logs/" + saved.split("/")[-1]
    d = json.load(open(f))
    dv = d["collected_dynamic_variables"]
    msgs = d["message_with_tool_calls"]
    vl_calls, edge_fabrications = [], []
    booking_uid = None
    last_sv_result = None
    for m in msgs:
        if not isinstance(m, dict): continue
        if m.get("role") == "tool_call_invocation" and m.get("name") == "validate_lead":
            try: args = json.loads(m.get("arguments", "{}"))
            except: args = {}
            vl_calls.append(args)
        if m.get("role") == "tool_call_result" and "slot_verified" in str(m.get("content", "")):
            try:
                r = json.loads(m["content"])
                last_sv_result = r
            except: pass
        if m.get("role") == "tool_call_invocation" and m.get("name") == "transition_to_Booking":
            try:
                ea = json.loads(m.get("arguments", "{}"))
                sv_dv_true = str(dv.get("slot_verified")).lower() == "true"
                if bool(ea.get("slot_verified")) != sv_dv_true:
                    edge_fabrications.append((ea.get("slot_verified"), dv.get("slot_verified")))
            except: pass
        if m.get("name") == "record_booking_uid" and m.get("role") == "tool_call_result":
            mm = re.search(r'"booking_uid":"([^"]+)"', str(m.get("content","")))
            if mm: booking_uid = mm.group(1)
    name = (start or "?").replace("START ", "")
    print(f"\n### {name}")
    print(f"  file: {saved}")
    print(f"  validate_lead calls: {len(vl_calls)} | final server verdict: {last_sv_result['slot_verified'] if last_sv_result else 'N/A'}")
    probs = [p.get('field') for p in (last_sv_result or {}).get('problems', [])]
    acts = len((last_sv_result or {}).get('actions', []))
    print(f"  problems on final call: {probs} | ask-lines attached: {acts}")
    bad_args = []
    for a in vl_calls:
        if a.get("callback_number") == "calling_number": bad_args.append("calling_number")
        if not a.get("selected_time"): bad_args.append("no selected_time")
    print(f"  dirty arg payloads: {bad_args if bad_args else 'none'}")
    print(f"  dv slot_verified: {dv.get('slot_verified')} | leaks: {dv.get('weekly_leak')} / {dv.get('monthly_leak')}")
    print(f"  EDGE FABRICATION (edge arg != dv): {edge_fabrications if edge_fabrications else 'NONE'}")
    print(f"  booking_uid: {booking_uid or '-'}")
