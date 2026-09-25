# 02 ACTION PLAN — iter58: EOT 0.8 + PUBLIC Caddy voice endpoint

Written from 01_audit.md (all findings F1-F16 folded in). Exact diffs; nothing left
to interpretation at execution time. Branch: NEW `engine/iter58-eot08-public-mic`
cut from `4cfb7a5`; worktree `/tmp/opencode/wt-iter58`.

---

## T0 — Branch + worktree + env (no code yet)

```bash
cd /home/julio/projects/clean_diallux_SDR
git branch engine/iter58-eot08-public-mic 4cfb7a5
git worktree add /tmp/opencode/wt-iter58 engine/iter58-eot08-public-mic
ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter58/engine/.venv
cp /tmp/opencode/wt-iter56/engine/.env /tmp/opencode/wt-iter58/engine/.env   # real file, not symlink (A8)
```
Verify: `cd /tmp/opencode/wt-iter58/engine && .venv/bin/python -c "import fastembed; from fastembed import TextEmbedding" && git log --oneline -1` → `4cfb7a5`.

## T1 — Code edits (all in /tmp/opencode/wt-iter58/engine)

### Edit 1 — `diallux/app.py`

**1a. imports** (top block, after `import logging`): add
```python
import os
import secrets
import time
```

**1b. `/health`** — in the dict after `"eager_eot": s.deepgram_eager_eot,` add:
```python
        "eager_eot_threshold": s.deepgram_eager_eot_threshold,
```
(Fail-safe display. Note F7: after a call starts with env unset, session.py:177
mutates the shared lru_cached Settings to 0.6 — the field shows the EFFECTIVE value;
with env=0.8 no mutation fires.)

**1c. `/mic/ws`** — replace the opening of the handler (lines 146-151 today) with:
```python
@app.websocket("/mic/ws")
async def mic_ws(ws: WebSocket):
    # iter58: public-endpoint token gate — fail-closed. VOICE_TEST_TOKEN is
    # deliberately read from os.environ (serve_voice.sh exports all of .env),
    # NOT a Settings field: zero config.py edits, one variable only.
    await ws.accept()
    token = os.environ.get("VOICE_TEST_TOKEN", "")
    k = str(ws.query_params.get("k", ""))
    if not token or not secrets.compare_digest(k.encode(), token.encode()):
        log.warning("mic bridge rejected: %s", "token unset (fail-closed)" if not token
                    else "token mismatch")
        await ws.close(code=4401)
        return
    settings = get_settings()
    session: CallSession | None = None
    sid = uuid.uuid4().hex[:12]
    observe_ia = None
    if settings.metrics_enabled:
        from .observability import metrics
        observe_ia = metrics.MIC_CHUNK_INTERARRIVAL_MS
    last_chunk_t: float | None = None
```
(accept-then-close so browsers AND TestClient observe 4401 — verified shape, audit F6.
Never log `k` — no token leakage.)

**1d. receive loop** — the `audio` branch becomes:
```python
            audio = raw.get("bytes")
            if audio:
                now = time.perf_counter()
                if observe_ia is not None and last_chunk_t is not None:
                    observe_ia.observe((now - last_chunk_t) * 1000.0)
                last_chunk_t = now
                if session:
                    await session.on_media(base64.b64encode(audio).decode())
                continue
```

**1e. text dispatch** — insert BEFORE the `start` branch:
```python
            event = msg.get("event")
            if event == "probe":
                # iter58 RTT probe — direct reply is safe alongside the session
                # writer's PCM sends (verified empirically, audit F5).
                await ws.send_text(json.dumps({
                    "event": "probe_ack", "t": msg.get("t"),
                    "t_server_ms": round(time.perf_counter() * 1000, 1)}))
            elif event == "mic_stats":
                stats = msg.get("stats") or {}
                log.info("mic_stats %s: %s", sid, json.dumps(stats))
                if session is not None and session.tracer is not None:
                    session.tracer.span("mic_stats", metadata=stats)
            elif event == "start" and session is None:
                ...  # unchanged
```

### Edit 2 — `diallux/observability/metrics.py`

After `LLM_ROUND_S` (line 38) add:
```python
# iter58: browser-mic transport health — chunk inter-arrival at the server WS
# (page worklet sends 800 Int16 @16 kHz = 50 ms/message; starved bridge showed
# 73-198 ms on the 09-19 SSH-tunnel call).
MIC_CHUNK_INTERARRIVAL_MS = Histogram(
    "diallux_mic_chunk_interarrival_ms",
    "Browser-mic chunk inter-arrival at the server WS (nominal 50 ms)",
    buckets=(20, 30, 40, 50, 60, 70, 80, 100, 125, 150, 200, 300),
    registry=REGISTRY)
```

### Edit 3 — `diallux/static/mic/index.html`

**3a. HTML** — after the `.status` div (line 36) add:
```html
    <div class="sub" id="netstats" style="margin-bottom:14px">net: —</div>
```

**3b. JS anchors** — after the `let ws = null, ...` line (61) add:
```js
  const $net = document.getElementById('netstats');
  const T0 = performance.now();
  let wsOpenAt = null, firstAudioAt = null, rttSamples = [], probeTimer = null;
```

**3c. WS URL** — replace lines 102-103:
```js
      const k = new URLSearchParams(location.search).get('k') || '';
      const proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
      ws = new WebSocket(proto + location.host + '/mic/ws' + (k ? '?k=' + encodeURIComponent(k) : ''));
```

**3d. ws.onopen** — start the 2 s probe:
```js
      ws.onopen = () => {
        wsOpenAt = performance.now();
        log('ws open → start'); ws.send(JSON.stringify({ event: 'start' }));
        probeTimer = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN)
            ws.send(JSON.stringify({ event: 'probe', t: Date.now() }));
        }, 2000);
      };
```

**3e. ws.onmessage** — first-audio timeline + probe_ack RTT:
```js
      ws.onmessage = (e) => {
        if (e.data instanceof ArrayBuffer) {
          if (firstAudioAt === null && wsOpenAt !== null) {
            firstAudioAt = performance.now();
            const stats = {
              page_open_to_ws_open_ms: Math.round(wsOpenAt - T0),
              ws_open_to_first_audio_ms: Math.round(firstAudioAt - wsOpenAt),
              page_open_to_first_audio_ms: Math.round(firstAudioAt - T0)
            };
            console.log('mic_stats', stats);
            log('first audio: page→ws ' + stats.page_open_to_ws_open_ms +
                ' ms · ws→audio ' + stats.ws_open_to_first_audio_ms + ' ms');
            ws.send(JSON.stringify({ event: 'mic_stats', stats }));
          }
          playChunk(new Int16Array(e.data));
        } else if (e.data) {
          try {
            const m = JSON.parse(e.data);
            if (m.event === 'probe_ack') {
              const rtt = Date.now() - m.t;
              rttSamples.push(rtt);
              if (rttSamples.length > 5) rttSamples.shift();
              $net.textContent = 'RTT ' + rtt + ' ms · last5 [' + rttSamples.join(', ') + ']';
            }
          } catch (err) { /* non-JSON control frame */ }
        }
      };
```

**3f. ws.onclose** — surface 4401 + stop the probe:
```js
      ws.onclose = (e) => {
        clearInterval(probeTimer);
        const code = e && e.code ? ' (' + e.code + ')' : '';
        log('ws closed' + code);
        if (e && e.code === 4401) setStatus('rejected: bad/missing token (4401)', 'err');
        endCallUI('call ended');
      };
```

**3g. endCallUI** — add `clearInterval(probeTimer);` first line.

### Edit 4 — `tests/test_units.py` (F1 fix — the plan's File Map missed this)

Replace `test_mic_page_serves_and_ws_handshakes` (lines 290-303) with:
```python
def test_mic_page_serves_and_ws_handshakes(monkeypatch):
    """iter21: GET /mic serves the bridge page; WS /mic/ws handshakes and stays
    silent (no Deepgram/Cartesia connects) until the client sends start.
    iter58: token gate armed deterministically (setenv + matching k) so the pin
    holds with VOICE_TEST_TOKEN present in .env or the shell env."""
    from fastapi.testclient import TestClient
    from diallux.app import app

    client = TestClient(app)
    r = client.get("/mic")
    assert r.status_code == 200
    assert "getUserMedia" in r.text
    assert "/mic/ws" in r.text
    monkeypatch.setenv("VOICE_TEST_TOKEN", "t1")
    with client.websocket_connect("/mic/ws?k=t1") as ws:
        ws.send_text(json.dumps({"event": "noop"}))   # ignored: no session yet
        ws.send_text("not json")                      # ignored: JSONDecodeError path
```

### Edit 5 — `tests/test_iter58_mic_probe.py` (NEW — 4 pins)

```python
"""iter58 T1 — public-mic instrumentation pins (measurement + token gate).

  1. /health carries eager_eot_threshold (the iteration's ONE variable, visible)
  2. /mic/ws fail-closed: env unset OR wrong k → close 4401
  3. correct k: probe → probe_ack (client t echoed, t_server_ms present)
  4. mic chunk inter-arrival histogram observed on /metrics after 2 binary frames
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from starlette.websockets import WebSocketDisconnect


def test_health_carries_eager_eot_threshold():
    from fastapi.testclient import TestClient
    from diallux.app import app

    r = TestClient(app).get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "eager_eot_threshold" in data
    assert data["eager_eot_threshold"] is None or \
        isinstance(data["eager_eot_threshold"], float)


def test_mic_ws_token_gate_fail_closed(monkeypatch):
    from fastapi.testclient import TestClient
    from diallux.app import app

    client = TestClient(app)
    monkeypatch.delenv("VOICE_TEST_TOKEN", raising=False)   # F10: never inherit
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/mic/ws") as ws:
            ws.receive_text()
    assert exc.value.code == 4401

    monkeypatch.setenv("VOICE_TEST_TOKEN", "t1")
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/mic/ws?k=wrong") as ws:
            ws.receive_text()
    assert exc.value.code == 4401


def test_mic_ws_probe_ack(monkeypatch):
    from fastapi.testclient import TestClient
    from diallux.app import app

    monkeypatch.setenv("VOICE_TEST_TOKEN", "t1")
    client = TestClient(app)
    with client.websocket_connect("/mic/ws?k=t1") as ws:
        ws.send_text(json.dumps({"event": "probe", "t": 12345}))
        ack = json.loads(ws.receive_text())
        assert ack["event"] == "probe_ack"
        assert ack["t"] == 12345
        assert isinstance(ack["t_server_ms"], (int, float))


def test_mic_interarrival_metric_observed(monkeypatch):
    from fastapi.testclient import TestClient
    from diallux.app import app

    monkeypatch.setenv("VOICE_TEST_TOKEN", "t1")
    client = TestClient(app)
    with client.websocket_connect("/mic/ws?k=t1") as ws:
        ws.send_bytes(b"\x00" * 1600)     # 50 ms of silence
        ws.send_bytes(b"\x00" * 1600)
    body = client.get("/metrics").text
    assert "diallux_mic_chunk_interarrival_ms_bucket" in body
    # exactly one delta from two frames; the only binary sender in the suite
    assert "diallux_mic_chunk_interarrival_ms_count 1" in body
```

### T1 run order
1. Apply Edits 1-5.
2. `cd /tmp/opencode/wt-iter58/engine && .venv/bin/python -m pytest tests -o addopts="" -q`
   → **exact gate: 367 passed** (363 + 4 new; Edit 4 modifies an existing pin, adds none). Any other count = STOP.
3. Commit: `iter58 T1: mic token gate (4401) + probe RTT + chunk inter-arrival metric + /health eager_eot_threshold + client first-audio timeline`.

## T2 — Caddy public endpoint (ops)

Primary (needs DNS — owner ASK):
```bash
mkdir -p /tmp/caddy
cp /etc/caddy/Caddyfile /tmp/caddy/voicetest-candidate-caddyfile
cat >> /tmp/caddy/voicetest-candidate-caddyfile <<'EOF'

voicetest.diallux-ai.site {
	reverse_proxy 127.0.0.1:8020 {
		flush_interval -1
	}
}
EOF
/usr/bin/caddy validate --config /tmp/caddy/voicetest-candidate-caddyfile --adapter caddyfile
```
Validated already in audit (A12) — re-validate after the copy. Then **OWNER** runs
`sudo /usr/local/bin/caddy-apply /tmp/caddy/voicetest-candidate-caddyfile`
(F2: sudo denied at my permission layer; owner runs it or adds an opencode
permission rule `bash +sudo /usr/local/bin/caddy-apply*` first).
Verify: `curl -s https://voicetest.diallux-ai.site/health` → 200 JSON (only after DNS +
apply); from the Mac (no tunnel): page loads, WS connects with `?k=`.

Fallback if DNS stays blocked (owner picks at go — F3): replace the `flores` block in the
candidate with (F11 — valid Caddy syntax, `handle_path` strips the `/voice` prefix so the
engine needs ZERO path changes):
```
flores.diallux-ai.site {
	handle_path /voice/* {
		reverse_proxy 127.0.0.1:8020 {
			flush_interval -1
		}
	}
	handle {
		reverse_proxy localhost:8000
	}
}
```
plus ONE JS line in Edit 3c: `'/mic/ws'` → `'/voice/mic/ws'` (page URL becomes
`https://flores.diallux-ai.site/voice/mic?k=…`). Decide BEFORE T1 commit so the branch
carries the right page.

## T3 — EOT threshold 0.6 → 0.8 + restart (the ONE behavior variable)

```bash
cd /tmp/opencode/wt-iter58/engine
sed -i 's/^DEEPGRAM_EAGER_EOT_THRESHOLD=.*/DEEPGRAM_EAGER_EOT_THRESHOLD=0.8/' .env
grep DEEPGRAM_EAGER_EOT .env            # → true + 0.8
# owner sets the token first (F4): VOICE_TEST_TOKEN=<secret> appended to .env
kill $(cat /tmp/opencode/voice_8020.pid) 2>/dev/null; sleep 2
ss -tln | grep -q "127.0.0.1:8020 " && echo "STOP: port still busy" || bash scripts/serve_voice.sh
curl -s http://127.0.0.1:8020/health | .venv/bin/python -c \
  "import sys,json; d=json.load(sys.stdin); print(d['eager_eot_threshold'], d['embedder'])"
```
Gate: last launcher line `VOICE SERVER READY … RAG PROVEN`; /health shows `0.8` + `ok`;
`grep -c "No module named" /tmp/opencode/voice_server_8020.log` on the new launch section = 0.

## T4 — Owner live call over the PUBLIC URL (no SSH)

1. Telegram ping (form per A15, require `hitl_ping: sent`):
   `export $(grep -E "^TELEGRAM_(BOT_TOKEN|CHAT_ID)=" /home/julio/projects/video_strategy/.env | xargs) && .venv/bin/python scripts/hitl_ping.py "iter58: :8020 up (EOT 0.8, token gate, RTT probe). Public URL ready: https://voicetest.diallux-ai.site/mic?k=<TOKEN> — no tunnel. ~10 min full intake→booking call when you're ready."`
2. Owner runs the call. Agent live-watches `tail -f /tmp/opencode/voice_server_8020.log`
   (chunks flowing, `mic_stats` line, zero `retrieve_lanes failed`).
3. Extraction: `/metrics` snapshot (inter-arrival buckets → p90), page RTT (owner
   screenshots console or netstats), `turn N report` / `head_start_ms` from the log,
   `StartOfTurn → eot adopted` deltas, first-5-turns e2e; import:
   `.venv/bin/python ../research/surgeon/call-facts/import_call.py --log /tmp/opencode/voice_server_8020.log --sid <sid> --branch engine/iter58-eot08-public-mic --commit <sha> --port 8020 --model gpt-5.4 --trace <id> --worktree /tmp/opencode/wt-iter58`
4. Gates: inter-arrival p90 ≤ 65 ms/chunk (vs 73-198 starved); ZERO EOT-adopts < 800 ms
   (was 4 ≤ 1 s at 0.6); eager adoption ≥ 80%; turn-1 cache ≥ 1664; TTFT p50 ≤ 900 ms.
5. Cancel ALL Cal test bookings (event 3801235 is REAL).

## T5 — Report + closeout + ASK

1. `research/surgeon/iter58-eot08-public-mic/01_report.md` — before/after table
   (transport rate, EOT delays, first-5 e2e, client RTT, first-audio timeline) with
   SQL/log citations.
2. `docs/CALL_FACTS.md` +1 row; `facts` rows into `call_facts.db` (no sqlite3 CLI —
   venv python).
3. `plans/PENDING_TASKS.md`: PT-58 (threshold adopt/flip), PT-59 (transport verdict).
4. Commit docs (LAW 0: docs → main; also the untracked plan/CALL_FACTS/tasks files —
   F13, one docs commit, owner-informed).
5. Telegram closeout ping, then **ASK JULIO**: (a) keep 0.8? (b) merge branch?
   (c) keep `voicetest` endpoint for Twilio cutover prep? (d) iter57 owed closeout
   (ledger import voice-iter56, ITERATIONS.md line, PT flips) — F16.

## Rollbacks
- Threshold: `sed` back to 0.6 + restart (seconds).
- Token gate: remove VOICE_TEST_TOKEN from .env → endpoint fail-closed (shut, not open).
- Code: branch is additive; `git checkout 4cfb7a5 -- <file>` per file, or abandon branch.
- Caddy: owner re-runs caddy-apply with the backup `/etc/caddy/backups/` copy.
