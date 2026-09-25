#!/usr/bin/env python3
"""Local Retell-LLM replica for V7.9_slot_lock — runs the EXACT deployed prompts/tools
against OpenAI directly, wired to the LIVE VPS endpoints (slots checker, book-livecall,
validator gates). $0 to Retell.

Faithful to the deployed agent:
- system = general_prompt + state_prompt ({{dv}} + ##kb## substitution)
- tools per state + general_tools + edges as transition_to_<State> functions
- extract_dynamic_variable tools write dvs
- custom tools: HMAC-signed POST/GET to slots.diallux-ai.site, response_variables → dvs
- begin_message spoken first (start_speaker: agent)
"""
import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path

import requests
from openai import OpenAI

from langfuse_bridge import Tracer

LAB = Path(__file__).resolve().parent               # .../V7.9_slot_lock/lab
HERE = LAB.parent / "retell"                        # .../V7.9_slot_lock/retell (agent artifact)
ROOT = LAB.parent.parent.parent                    # Retell_AI_MCP_connection/

MODEL_CANDIDATES = ["gpt-5.2", "gpt-5", "gpt-4.1"]
MAX_TOOL_ROUNDS = 12


def load_root_key(name):
    for line in open(ROOT / ".env"):
        if line.strip().startswith(name + "="):
            return line.strip().split("=", 1)[1]
    raise SystemExit(f"missing {name} in {ROOT}/.env")


class R:
    """Minimal response wrapper so custom-tool handling matches the service tests."""

    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


class SDREngine:
    def __init__(self, persona_dynvars=None, retell_key=None, log_prefix="sim"):
        self.llm = json.loads((HERE / "llm.json").read_text())
        self.dvs = dict(self.llm["default_dynamic_variables"])
        self.dvs.update(persona_dynvars or {})
        self.states = {s["name"]: s for s in self.llm["states"]}
        self.state = self.llm["starting_state"]
        self.history = []
        self.ended = False
        self.trace = []
        self.log_prefix = log_prefix
        self.tracer = Tracer(
            session_name="sdr-sim",
            metadata={"agent": "V7.9_slot_lock", "llm_model": self.llm.get("model"),
                      "engine": "local-simulator"},
            enabled=os.environ.get("LANGFUSE_ENABLED", "1") == "1",
        )
        self.retell_key = retell_key or load_root_key("RETELL_API_KEY")
        self.kb_cache = {}
        self._client = OpenAI(api_key=load_root_key("OPENAI_API_KEY"))
        self.model = MODEL_CANDIDATES[0]
        # first agent utterance (start_speaker: agent)
        self.history.append({"role": "assistant", "content": self.llm["begin_message"]})

    # ---------------- substitution ----------------
    @staticmethod
    def _openai_schema(params):
        """Recursively convert Retell schemas (type 'enum' + 'choices') to OpenAI JSON Schema."""
        if isinstance(params, list):
            return [SDREngine._openai_schema(p) for p in params]
        if not isinstance(params, dict):
            return params
        out = {}
        if params.get("type") == "enum" and params.get("choices"):
            out["type"] = "string"
            out["enum"] = params["choices"]
        else:
            for k, v in params.items():
                if k == "choices":
                    continue
                out[k] = SDREngine._openai_schema(v)
        return out

    def subst(self, text):
        def kb(m):
            slug = m.group(1)
            if slug not in self.kb_cache:
                p = HERE / "Knowledge bases" / f"{slug}.md"
                self.kb_cache[slug] = p.read_text() if p.exists() else f"[KB {slug} MISSING]"
            return self.kb_cache[slug]

        text = re.sub(r"##([\w-]+)-kb##", kb, text)
        return re.sub(
            r"\{\{(\w+)\}\}",
            lambda m: str(self.dvs.get(m.group(1), m.group(0))),
            text,
        )

    # ---------------- tools ----------------
    def _tools_for_state(self):
        out = []
        for t in list(self.states[self.state]["tools"]) + list(self.llm["general_tools"]):
            ttype = t.get("type")
            if ttype == "extract_dynamic_variable":
                props = {}
                req = []
                for v in t.get("variables", []):
                    prop = {"type": v.get("type", "string"), "description": self.subst(v.get("description", ""))}
                    if v.get("choices"):
                        prop["type"] = "string"
                        prop["enum"] = v["choices"]
                    props[v["name"]] = prop
                    req.append(v["name"])
                out.append({"type": "function", "function": {
                    "name": t["name"],
                    "description": self.subst(t.get("description", "")),
                    "parameters": {"type": "object", "properties": props, "required": req},
                }})
            elif ttype in ("custom", "book_appointment_cal"):
                params = t.get("parameters") or {"type": "object", "properties": {}}
                if "properties" in params:
                    params = self._openai_schema(json.loads(self.subst(json.dumps(params))))
                out.append({"type": "function", "function": {
                    "name": t["name"],
                    "description": self.subst(t.get("description", "")),
                    "parameters": params,
                }})
        for e in self.states[self.state]["edges"]:
            out.append({"type": "function", "function": {
                "name": f"transition_to_{e['destination_state_name']}",
                "description": self.subst(e.get("description", "")),
                "parameters": e.get("parameters", {"type": "object", "properties": {}}),
            }})
        return out

    def _signed_request(self, url, method, payload):
        raw = json.dumps(payload).encode()
        ts = str(int(time.time() * 1000))
        digest = hmac.new(self.retell_key.encode(), raw + ts.encode(), hashlib.sha256).hexdigest()
        try:
            resp = requests.request(
                method, url, data=raw if method == "POST" else None,
                params=payload if method == "GET" else None,
                headers={"Content-Type": "application/json",
                         "X-Retell-Signature": f"v={ts},d={digest}"},
                timeout=20,
            )
            try:
                return R(resp.status_code, resp.json())
            except ValueError:
                return R(resp.status_code, {})
        except requests.RequestException as exc:
            return R(599, {"ok": False, "error": "request_failed", "message": str(exc)[:200]})

    def _exec_custom(self, t, args):
        url = t["url"]
        method = t.get("method", "POST")
        if t.get("query_params"):
            url = url + "?" + "&".join(f"{k}={v}" for k, v in t["query_params"].items())
        payload = args if t.get("args_at_root") else {"args": args}
        resp = self._signed_request(url, method, payload)
        try:
            body = resp.json()
        except Exception:
            body = {}
        for resp_key, dv_name in (t.get("response_variables") or {}).items():
            if isinstance(body, dict) and resp_key in body and body[resp_key] not in (None, ""):
                self.dvs[dv_name] = body[resp_key]
        self.trace.append({"tool": t["name"], "args": args, "http": resp.status_code, "resp": body})
        return body

    def _exec(self, name, args):
        t0 = time.time()
        state0 = self.state
        tool_obs = self.tracer.start_tool(name, args, state0)
        result = self._exec_inner(name, args)
        self.tracer.finish_tool(tool_obs, result, time.time() - t0)
        return result

    def _exec_inner(self, name, args):
        # Repeat-call guard: identical tool+args twice in a row → nudge forward
        # (stochastic loop guard; prompts untouched).
        key = (name, json.dumps(args, sort_keys=True))
        if getattr(self, "_last_call", None) == key:
            self.trace.append({"tool": name, "duplicate_guard": True})
            return {
                "status": "already_captured",
                "message": ("Values are already stored as dynamic variables. Do NOT call this "
                            "tool again — proceed to the next step in the flow."),
            }
        self._last_call = key
        for t in list(self.states[self.state]["tools"]) + list(self.llm["general_tools"]):
            if t.get("name") != name:
                continue
            if t.get("type") == "extract_dynamic_variable":
                wrote = {}
                for v in t.get("variables", []):
                    val = args.get(v["name"])
                    if val not in (None, ""):
                        self.dvs[v["name"]] = val
                        wrote[v["name"]] = val
                self.trace.append({"tool": name, "wrote": wrote})
                return {"status": "ok", "written": wrote}
            return self._exec_custom(t, args)
        if name.startswith("transition_to_"):
            dest = name[len("transition_to_"):]
            self.state = dest
            self.trace.append({"tool": name, "to": dest})
            return {"status": "ok", "state": dest}
        if name == "end_call":
            self.ended = True
            self.trace.append({"tool": name})
            return {"status": "call_ended"}
        return {"status": "unknown_tool", "name": name}

    # ---------------- turn ----------------
    def system_message(self):
        return self.subst(
            self.llm["general_prompt"] + "\n\n" + self.states[self.state]["state_prompt"]
        )

    def chat(self, user_text):
        self.history.append({"role": "user", "content": user_text})
        self.timings = getattr(self, "timings", [])
        for _ in range(MAX_TOOL_ROUNDS):
            t0 = time.time()
            state0 = self.state
            gen_obs = self.tracer.start_llm(state0, self.model, self.history[-6:])
            # gpt-5.2 fast config: NO temperature, NO reasoning_effort — both are
            # measured latency killers (default ≈1.0s; temperature+reasoning hit 87s).
            kwargs = dict(
                model=self.model,
                messages=[{"role": "system", "content": self.system_message()}] + self.history,
                tools=self._tools_for_state(),
                tool_choice="auto",
            )
            if os.environ.get("TEMPERATURE"):
                kwargs["temperature"] = float(os.environ["TEMPERATURE"])
            effort = os.environ.get("REASONING_EFFORT", "")
            if effort and effort != "default":
                kwargs["reasoning_effort"] = effort
            try:
                resp = self._client.chat.completions.create(**kwargs)
            except Exception as exc:
                if "reasoning_effort" in kwargs and "reasoning" in str(exc).lower():
                    kwargs.pop("reasoning_effort")
                    resp = self._client.chat.completions.create(**kwargs)
                else:
                    raise
            llm_s = time.time() - t0
            msg = resp.choices[0].message
            usage = None
            if getattr(resp, "usage", None):
                usage = {"input": resp.usage.prompt_tokens,
                         "output": resp.usage.completion_tokens,
                         "total": resp.usage.total_tokens,
                         "unit": "TOKENS"}
            tcs = [{"name": tc.function.name, "args": tc.function.arguments}
                   for tc in (msg.tool_calls or [])]
            self.tracer.finish_llm(gen_obs, output=msg.content or "",
                                   latency_s=llm_s, usage=usage, tool_calls=tcs)
            if msg.tool_calls:
                t1 = time.time()
                self.history.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = self._exec(tc.function.name, args)
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result)[:4000],
                    })
                self.timings.append({"state": self.state, "llm_s": round(llm_s, 2),
                                     "tools_s": round(time.time() - t1, 2),
                                     "calls": [tc.function.name for tc in msg.tool_calls]})
                if self.ended:
                    return msg.content or ""
                continue
            self.timings.append({"state": self.state, "llm_s": round(llm_s, 2),
                                 "tools_s": 0, "calls": ["<speak>"]})
            self.history.append({"role": "assistant", "content": msg.content or ""})
            self.tracer.flush()
            return msg.content or ""
        self.tracer.flush()
        return ""

    def dump_transcript(self):
        return {
            "state": self.state, "ended": self.ended,
            "dvs": self.dvs, "trace": self.trace, "history": self.history,
        }

    def full_transcript(self):
        """Complete human-readable conversation + tool trace + final dvs (for Langfuse)."""
        convo = [
            {"role": m["role"], "content": m.get("content") or "",
             "tool_calls": [tc["function"]["name"] for tc in m.get("tool_calls", [])] or None}
            for m in self.history if m["role"] in ("user", "assistant", "tool")
        ]
        return {
            "conversation": convo,
            "tool_trace": self.trace,
            "final_state": self.state,
            "ended": self.ended,
            "dynamic_variables": self.dvs,
        }

    def finish(self):
        """Persist the FULL conversation to Langfuse and close the trace."""
        try:
            self.tracer.finish(output=self.full_transcript())
        except Exception:
            pass
