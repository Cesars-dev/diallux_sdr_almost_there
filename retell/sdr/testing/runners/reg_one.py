import sys, importlib.util
spec = importlib.util.spec_from_file_location('h', '/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/testing/test_llm_to_llm.py')
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
idx = int(sys.argv[1]); p = h.PERSONAS[idx]
print(f"START {idx}: {p['name']}", flush=True)
r = h.run_scenario(p)
print(f"DONE idx={idx} | {p['name']} | booking={r['booking']} end={r['end']} cost={r['cost']}c", flush=True)
