# V7.8_reach_details — deploy lineage (new account, 2026-09-03)

| # | Folder | chat_agent_id | llm_id | Delta | Status |
|---|--------|---------------|--------|-------|--------|
| 01 | 01_baseline_e618dd12 | agent_e99648268be5045d8a49cc9e4e | llm_e618dd126405566695cb511267bc | V7.8 build as-is (fresh account, 9 KBs created once) | superseded |
| 02 | 02_endcall_rule_REJECTED_2987eab9 | agent_49906d46aa0d1c3f3a524ab5f1 | llm_2987eab94087b3058ec5eb09bf0b | invented "Do NOT end_call with transition" rule — REJECTED by owner | superseded, do not reuse |
| 03 | 03_bold_constraint_CURRENT_f402d94d | agent_da3959eac4b5f16ee40bbda233 | llm_f402d94db1842e53988b4839cd34 | existing CRITICAL CONSTRAINT bolded (** **), nothing else added | CURRENT |

Doctrine honored: new LLM + new chat agent per deploy (never patched), KBs reused via registry, no deletions — orphaned agents kept alive as rollback.
