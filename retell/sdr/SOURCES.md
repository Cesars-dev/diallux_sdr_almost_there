# SOURCES — provenance & snapshot info

Everything in this folder was fetched from the **live Retell account** on **2026-08-04**.

> **Working policy: we don't even look at production.** The production agent/LLM/KBs listed below were snapshotted **once** to seed this folder and are now out of scope. All iteration runs on the **local clone** (see `deploy_chat_clone.py` + README "Current local clone") — tweak, redeploy, and test from local files. Do not read, reference, or modify the production IDs.

## Live production asset (READ-ONLY — DO NOT TOUCH)

| Asset | ID | Version | Notes |
|-------|----|---------|-------|
| Voice agent | `agent_4b577c7e169b069deae991b11d` | 36 (base 35) | "Dialux AI", channel `voice`, **LIVE** — phone +1 (213) 600-1723 |
| Retell LLM | `llm_187271736e1a805fa07737692b84` | 36 | gpt-5.4, multi-prompt (4 states) |
| Webhook | — | — | `https://newn8n.dialux-ai.site/webhook/719e4c00-0208-46ea-b84c-f43e6a86673a` |

## Linked knowledge bases (4)

| KB name | KB ID | Source file (cloudfront) |
|---------|-------|--------------------------|
| Sales Psychology Methodology | `knowledge_base_15cc6c993c6023c6` | `c511a595.md` |
| Pain Points Framework | `knowledge_base_2907e916fab4baab` | `5670cba2.md` |
| Industry-Specific Knowledge | `knowledge_base_06fd054f525c0171` | `5b670c64.md` |
| Voice AI Capabilities | `knowledge_base_aab195d8ef57063f` | `46cd92b3.md` |

## How each file maps to the API

| Folder file | API call |
|-------------|----------|
| `config/agent.json` | `GET https://api.retellai.com/get-agent/agent_4b577c7e169b069deae991b11d` |
| `config/llm.json` | `GET https://api.retellai.com/get-retell-llm/llm_187271736e1a805fa07737692b84` |
| `prompts/general_prompt.md` | `llm.json.general_prompt` |
| `prompts/begin_message.txt` | `llm.json.begin_message` |
| `prompts/states/*.md` | `llm.json.states[].state_prompt` |
| `JSON/general_tools.json` | `llm.json.general_tools` |
| `JSON/states/*.tools.json` | `llm.json.states[].tools` |
| `JSON/states/*.edges.json` | `llm.json.states[].edges` (incl. transition `parameters` schema) |
| `Knowledge bases/*.md` | source `file_url` from `GET /get-knowledge-base/{kb_id}` |

## API key

ReteLL API key lives in `Retell_AI_MCP_connection/.env` (`RETELL_API_KEY`) — **never commit**. To re-fetch or for build tooling, export it from there.

## Local clone (deployed 2026-08-04, from local files)

| Asset | ID |
|-------|----|
| Chat agent `Diallux_recheck` (channel: chat) | `agent_d4e6edb48d468c47c7ed985337` |
| Cloned LLM (gpt-5.4) | `llm_c66214a24c8aa208540dc73ff8e3` |
| KB — Sales Psychology Methodology | `knowledge_base_c9de57c0cba92030` |
| KB — Pain Points Framework | `knowledge_base_2ae669af31f3b055` |
| KB — Industry-Specific Knowledge | `knowledge_base_68af8951b7313eeb` |
| KB — Voice AI Capabilities | `knowledge_base_fcdbf1846c63f2a3` |

## Important constraints

- This agent is a **voice** agent — it cannot be driven by `create-chat-completion` directly. To chat-test, bind a **chat agent** to the (new) LLM. To test voice, clone and use audio/web-call.
- Retell caches LLM behaviour; **never PATCH the live LLM** — always create a new LLM for iterations (project build policy).
- These files are a **snapshot**, not a live link. If the live config changes, re-fetch to refresh.
