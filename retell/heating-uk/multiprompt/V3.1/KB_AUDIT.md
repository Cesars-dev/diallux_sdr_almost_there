# KB Audit — Local V3.1 KBs vs Live Retell KBs

> **Date:** 2026-08-02
> **Source of truth:** `1785629507189-kb-v31-live-comparison-plan.md`
> **Scope:** the 13 KBs linked to the deployed V3 LLM (`llm_ae461dfc248342f34b13d81108ec`).
> **Result: 13/13 verbatim (byte-exact). No reconciliation needed.**

---

## Summary

| Verbatim | Diverged | MISSING | Could not compare |
|---|---|---|---|
| **13** | **0** | **0** | **0** |

Every live KB matches its mapped local file byte-for-byte (confirmed with both a
whitespace-normalized diff and a raw byte comparison). **No KB was modified,
created, or deleted during this audit.**

---

## Full table (13/13)

| Live KB name | Live KB id | Local file | Verbatim? | Diff / notes |
|---|---|---|---|---|
| `uk-address-kb` | `knowledge_base_4452b7e7363019ef` | `uk_address_kb.md` | ✅ yes | byte-exact |
| `v2-call-closing-kb` | `knowledge_base_9c5e47f73a7b1f39` | `call_closing_kb.md` | ✅ yes | byte-exact |
| `uk-hvac-trade-kb` | `knowledge_base_0d0f17655163dc37` | `uk-hvac-trade-kb.md` | ✅ yes | byte-exact (see note below) |
| `v2-fees-kb` | `knowledge_base_02c945a272e218ab` | `kb_v2_fee_rules.md` | ✅ yes | byte-exact |
| `v2-diagnostic-restraint-kb` | `knowledge_base_888f4640f99ab157` | `kb_v2_diagnostic_restraint.md` | ✅ yes | byte-exact |
| `v2-company-kb` | `knowledge_base_3001ab3f9bb38d42` | `kb_v2_company_briefing.md` | ✅ yes | byte-exact |
| `name-spelling-kb` | `knowledge_base_04eb73eab0376404` | `name_spelling_kb.md` | ✅ yes | byte-exact |
| `v2-sample-phrases-kb` | `knowledge_base_3c4cade180c03212` | `kb_v2_sample_phrases.md` | ✅ yes | byte-exact |
| `v2-knowledge-boundary-kb` | `knowledge_base_e193e310d593a364` | `kb_v2_knowledge_boundary.md` | ✅ yes | byte-exact |
| `v2-interaction-kb` | `knowledge_base_0a1e3377f2b26885` | `kb_v2_interaction_rules.md` | ✅ yes | byte-exact |
| `v2-gas-mention-kb` | `knowledge_base_9eac8bc973b8b0cb` | `kb_v2_emergency_gas.md` | ✅ yes | byte-exact |
| `uk-names-kb` | `knowledge_base_daa6ad09e303ed86` | `uk_names_kb.md` | ✅ yes | byte-exact |
| `day-logic-kb` | `knowledge_base_eb5d02e827b7e56a` | `day_logic_kb.md` | ✅ yes | byte-exact |

---

## Needs your decision

**None.** All 13 used KBs are verbatim — no decision required.

### `uk-hvac-trade-kb` provenance (resolved)

The plan flagged that the live KB might have been uploaded from the older
`uk_hvac_symptom_kb.md`. This turned out **not** to be the case:

- Live `uk-hvac-trade-kb` vs `uk-hvac-trade-kb.md` → **byte-exact match**
- Live `uk-hvac-trade-kb` vs `uk_hvac_symptom_kb.md` → **differs** (12748 vs 6958 chars)

So `uk-hvac-trade-kb.md` is confirmed as the canonical source of the live KB.
The `uk_hvac_symptom_kb.md` file is **obsolete** (superseded by
`uk-hvac-trade-kb.md`), as the plan anticipated.

---

## Not used (flagged, not removed)

- **`uk_hvac_symptom_kb.md`** — was in `V3.1/Knowledge bases/` but **not** referenced by
  any V3.1 prompt and not in `build_v3_llm.py`. Confirmed superseded by
  `uk-hvac-trade-kb.md`. **Archived 2026-08-02** to `multiprompt/_archive/uk_hvac_symptom_kb.md`
  (per user decision). Not deleted.

---

## Notes / edge cases

- KB content was stored as a single `knowledge_base_texts` block (`title` == KB name,
  text = full file content), served via CloudFront `content_url`. The diff compared the
  downloaded text against the local file; both the whitespace-normalized comparison and a
  raw byte comparison passed.
- All 13 expected names were found in `list-knowledge-bases`; **no MISSING KBs**.
  (`list-knowledge-bases` returned 17 KBs total; the other 4 — Sales Psychology
  Methodology, Pain Points Framework, Industry-Specific Knowledge, Voice AI Capabilites —
  are unrelated to the heating agent and out of scope.)

## Validation

- Mapping complete: 13/13 used KBs mapped to a local file; exactly one extra file
  (`uk_hvac_symptom_kb.md`) flagged.
- Report table has exactly 13 rows (one per used KB).
- Spot-checked `uk-address-kb`, `name-spelling-kb`, `uk-hvac-trade-kb`,
  `v2-interaction-kb` at raw byte level — all byte-exact, confirming the diff method is not a false pass.
- No KB or file was created, edited, or deleted during this audit.
