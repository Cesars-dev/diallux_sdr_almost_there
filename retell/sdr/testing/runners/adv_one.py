import sys, importlib.util
spec = importlib.util.spec_from_file_location('s', '/tmp/opencode/adversarial_suite.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
h = m.h
idx = int(sys.argv[1])
if idx == 5: sys.exit(0)  # Larry deprecated
p = m.PERSONAS[idx]
print(f"START {idx}: {p['name']}", flush=True)
r = h.run_scenario(p)
print(f"DONE idx={idx} | {p['name']} | booking={r['booking']} end={r['end']} cost={r['cost']}c", flush=True)
