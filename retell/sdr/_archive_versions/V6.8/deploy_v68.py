#!/usr/bin/env python3
"""Deploy V6.7: KBs reference-only via registry (upsert only on sha change), then NEW LLM + chat agent.

Per docs/DEPLOYMENT-SOP.md:
- absolute .env path, key prefix sanity check
- KB add-source-before-delete ordering on upsert
- response_engine as object; llm_id from create-retell-llm response
"""
import hashlib
import io
import re
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/julio/projects/Retell_AI_MCP_connection"  # absolute — never ../..
REG_PATH = "/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/config/kb_registry.json"
# Agent display name = the folder this script lives in (snapshot name), sanitized
CHAT_AGENT_NAME = re.sub(r"[^\w.-]+", "_", os.path.basename(HERE))

KEY = None
for line in open(os.path.join(ROOT, ".env")):
    if line.strip().startswith("RETELL_API_KEY="):
        KEY = line.strip().split("=", 1)[1]
if not KEY or not KEY.startswith("key_"):
    sys.exit(f"FATAL: RETELL_API_KEY missing/odd in {ROOT}/.env")
print(f"key prefix OK: {KEY[:14]}...")


def api(method, path, data=None, form=None):
    headers = {"Authorization": f"Bearer {KEY}"}
    body = None
    if form is not None:
        boundary = "----v67deploy"
        buf = io.BytesIO()
        for k, v in form.items():
            buf.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        buf.write(f"--{boundary}--\r\n".encode())
        body = buf.getvalue()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"https://api.retellai.com/{path}", data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        print(f"API ERROR {e.code} {path}: {e.read().decode()[:400]}")
        sys.exit(1)


def resolve_kb(reg, slug, text):
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    entry = reg.get(slug)
    if entry and entry.get("sha256") == sha:
        return entry["kb_id"], "reused"
    if entry:
        kb_id = entry["kb_id"]
        det = api("GET", f"get-knowledge-base/{kb_id}")
        old_ids = {s["source_id"] for s in det.get("knowledge_base_sources", [])}
        ct, body = None, json.dumps([{"title": slug, "text": text}])
        # multipart add FIRST (never delete the last source)
        boundary = "----kbsrc"
        buf = io.BytesIO()
        buf.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"knowledge_base_texts\"\r\n\r\n{body}\r\n".encode())
        buf.write(f"--{boundary}--\r\n".encode())
        api("POST", f"add-knowledge-base-sources/{kb_id}", form={"ct": boundary, "body": buf.getvalue().decode()})
        new_ids = set()
        for _ in range(10):
            time.sleep(1.5)
            det = api("GET", f"get-knowledge-base/{kb_id}")
            new_ids = {s["source_id"] for s in det.get("knowledge_base_sources", [])}
            if new_ids - old_ids:
                break
        for sid in old_ids:
            api("DELETE", f"delete-knowledge-base-source/{kb_id}/source/{sid}")
        entry["sha256"] = sha
        return kb_id, "updated"
    ct, body = None, None
    payload = json.dumps({"knowledge_base_name": slug,
                          "knowledge_base_texts": [{"title": slug, "text": text}]})
    r = api("POST", "create-knowledge-base", data=json.loads(payload))
    kb_id = r.get("knowledge_base_id")
    reg[slug] = {"kb_id": kb_id, "sha256": sha}
    return kb_id, "created"


def main():
    llm = json.load(open(os.path.join(HERE, "llm.json")))

    print("== 1/3 KBs (registry reuse; upsert only on content change) ==")
    reg = json.load(open(REG_PATH))
    kb_dir = os.path.join(HERE, "Knowledge bases")
    slugs = sorted(f[:-3] for f in os.listdir(kb_dir) if f.endswith(".md"))
    ids = []
    for slug in slugs:
        text = open(os.path.join(kb_dir, slug + ".md"), "rb").read().decode("utf-8", "replace")
        kb_id, action = resolve_kb(reg, slug, text)
        ids.append(kb_id)
        print(f"  KB {slug}: {action}")
    json.dump(reg, open(REG_PATH, "w"), indent=2)

    print("== 2/3 NEW LLM ==")
    body = {
        "model": llm["model"],
        "model_high_priority": llm.get("model_high_priority", True),
        "model_temperature": llm.get("model_temperature"),
        "tool_call_strict_mode": llm.get("tool_call_strict_mode"),
        "general_prompt": llm["general_prompt"],
        "begin_message": llm["begin_message"],
        "start_speaker": llm.get("start_speaker"),
        "starting_state": llm["starting_state"],
        "states": llm["states"],
        "general_tools": llm["general_tools"],
        "default_dynamic_variables": llm["default_dynamic_variables"],
        "kb_config": llm["kb_config"],
        "knowledge_base_ids": ids,
    }
    r = api("POST", "create-retell-llm", body)
    llm_id = r["llm_id"]
    print(f"  LLM: {llm_id}")

    print("== 3/3 chat agent ==")
    r = api("POST", "create-chat-agent",
            {"agent_name": CHAT_AGENT_NAME,
             "response_engine": {"type": "retell-llm", "llm_id": llm_id, "version": 0}})
    print("\n=== DEPLOYED ===")
    print(json.dumps({"chat_agent_id": r["agent_id"], "llm_id": llm_id}, indent=2))


if __name__ == "__main__":
    main()
