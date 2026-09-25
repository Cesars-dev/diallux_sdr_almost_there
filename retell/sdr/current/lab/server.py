#!/usr/bin/env python3
"""Client demo — browser chat with the Dialux SDR (V7.9 engine, real bookings).

Serve:  python3 server.py          → http://127.0.0.1:8010
Expose: ssh -L 8010:localhost:8010 <vps>   then open http://localhost:8010
"""
import json
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from engine import SDREngine

app = FastAPI(title="Dialux SDR demo")
SESSIONS = {}
LOCK = threading.Lock()
PAGE = Path(__file__).parent / "demo.html"


class Msg(BaseModel):
    session_id: str | None = None
    message: str


def get_engine(session_id):
    with LOCK:
        if session_id not in SESSIONS:
            SESSIONS[session_id] = SDREngine(log_prefix="demo")
        return SESSIONS[session_id]


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE.read_text()


@app.post("/chat")
def chat(m: Msg):
    sid = m.session_id or uuid.uuid4().hex[:12]
    eng = get_engine(sid)
    reply = eng.chat(m.message)
    uid = eng.dvs.get("booking_uid") or ""
    return JSONResponse({
        "session_id": sid,
        "reply": reply,
        "state": eng.state,
        "ended": eng.ended,
        "booked": bool(uid),
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8010, log_level="warning")
