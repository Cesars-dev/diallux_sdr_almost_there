#!/usr/bin/env python3
"""Langfuse bridge (SDK v4) for the SDR simulator — persistent tracing of every
LLM generation and tool call. Fail-safe: if Langfuse is down, tracing is skipped
and the ladder still runs.

Config: LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST
(self-hosted v3 stack on this VPS at http://localhost:3001).
"""
import os
import uuid

LEASING_ENV = "/home/julio/projects/leasing_tenant_scorer/.env"


def _lf_keys():
    env = dict(os.environ)
    if "LANGFUSE_PUBLIC_KEY" in env:
        return (env.get("LANGFUSE_PUBLIC_KEY"), env.get("LANGFUSE_SECRET_KEY"),
                env.get("LANGFUSE_HOST", "http://localhost:3001"))
    vals = {}
    for line in open(LEASING_ENV):
        line = line.strip()
        if line.startswith("LANGFUSE_") and "=" in line:
            k, _, v = line.partition("=")
            vals[k.strip()] = v.strip()
    return (vals.get("LANGFUSE_PUBLIC_KEY"), vals.get("LANGFUSE_SECRET_KEY"),
            vals.get("LANGFUSE_HOST", "http://localhost:3001"))


class Tracer:
    def __init__(self, session_name="sdr-chat", metadata=None, enabled=True):
        self.enabled = enabled
        self.root = None
        self.lf = None
        self.session_id = f"{session_name}-{uuid.uuid4().hex[:8]}"
        self._meta = metadata or {}
        if not enabled:
            return
        try:
            from langfuse import Langfuse, propagate_attributes
            pk, sk, host = _lf_keys()
            self.lf = Langfuse(public_key=pk, secret_key=sk, host=host)
            with propagate_attributes(session_id=self.session_id, trace_name=session_name):
                self.root = self.lf.start_observation(
                    name=session_name,
                    as_type="agent",
                    metadata={"session_id": self.session_id, **self._meta},
                )
        except Exception as exc:
            print(f"[langfuse] disabled ({type(exc).__name__}: {exc})")
            self.enabled = False

    def start_llm(self, state, model, messages):
        if not self.root:
            return None
        try:
            return self.root.start_observation(
                name=f"llm:{state}",
                as_type="generation",
                model=model,
                input=messages,
                metadata={"state": state},
            )
        except Exception as exc:
            print(f"[langfuse] gen open skipped: {type(exc).__name__}: {exc}")
            return None

    def finish_llm(self, obs, *, output, latency_s, usage=None, tool_calls=None):
        if not obs:
            return
        try:
            usage_details = None
            if usage:
                usage_details = {"input": usage.get("input", 0),
                                 "output": usage.get("output", 0),
                                 "total": usage.get("total", 0)}
            obs.update(
                output={"text": output, "tool_calls": tool_calls or []},
                metadata={"latency_s": round(latency_s, 3)},
                usage_details=usage_details,
            )
            obs.end()
        except Exception as exc:
            print(f"[langfuse] gen close skipped: {type(exc).__name__}: {exc}")

    def start_tool(self, name, input_data, state):
        if not self.root:
            return None
        try:
            return self.root.start_observation(
                name=f"tool:{name}",
                as_type="tool",
                input=input_data,
                metadata={"state": state},
            )
        except Exception as exc:
            print(f"[langfuse] tool open skipped: {type(exc).__name__}: {exc}")
            return None

    def finish_tool(self, obs, output_data, latency_s):
        if not obs:
            return
        try:
            obs.update(output=output_data, metadata={"latency_s": round(latency_s, 3)})
            obs.end()
        except Exception as exc:
            print(f"[langfuse] tool close skipped: {type(exc).__name__}: {exc}")

    def flush(self):
        if not self.lf:
            return
        try:
            self.lf.flush()
        except Exception:
            pass

    def finish(self, output=None):
        """Close the root observation, storing the FULL conversation transcript."""
        if not self.root:
            return
        try:
            if output is not None:
                self.root.update(input={"session_id": self.session_id,
                                        **(self._meta or {})},
                                 output=output)
            self.root.end()
            self.flush()
        except Exception as exc:
            print(f"[langfuse] finish skipped: {type(exc).__name__}: {exc}")
