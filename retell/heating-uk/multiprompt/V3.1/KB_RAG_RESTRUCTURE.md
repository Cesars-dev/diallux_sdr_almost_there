# KB RAG Restructure — Deep Analysis & Plan (V3.1 / Natural Speech)

> **Type:** Assessment only. Nothing below has been applied — no prompt, KB, or config changes.
> **Purpose:** Make the 13 KBs semantically RAG-friendly (≥90% chunk-retrieval accuracy) and
> harmonize them with the **light** Natural Speech main prompt (765 tokens) so prompt + KBs work
> as one retrieval system — the way the Dialux SDR does.
> **Cross-references:** `Iterations/Natural Speech/multiprompt_mvp_main_v3_natural_speech.md`
> (the main prompt we will keep tweaking) · `build_v3_llm.py:183` (`kb_config: top_k 3, filter 0.6`)
> · the 6 state prompts under `prompts/`.

---

## 1. Executive summary

The SDR retrieves flawlessly because of **three properties** the HVAC KBs mostly lack:

1. **One KB = one topic** (Industry KB has 19 industries, one `##` each).
2. **One chunk = one retrievable unit, titled with the customer's own words** ("roofing" → "Roofing" chunk).
3. **The prompt actively directs which KB to query, when.**

The HVAC problem is concentrated in **two files**: `uk-hvac-trade-kb.md` (five topics crammed into
one KB → top_k 3 pulls unrelated chunks) and `uk_names_kb.md` (26 name-groups under one heading →
"Marcus" query can miss the M chunk). Everything else is already RAG-reasonable.

**Fix (concept):** split the mega-KB into topic-scoped KBs; promote each retrievable unit to its
own `##` chunk titled with the caller's language; align KB names with the prompt markers; keep the
main prompt light. Result: the Natural Speech main stays at ~765 tokens, every "when to use this KB"
pointer resolves to a focused KB, and symptom/name lookups hit their chunk ~90% of the time.

---

## 2. Why the SDR wins (the RAG principles we copy)

| Principle | SDR implementation | HVAC today |
|---|---|---|
| One KB = one topic | Industry / Pain / Sales-Psych / Capabilities = 4 KBs | `uk-hvac-trade-kb` = vocab + brands + services + symptoms + regulatory + safety in ONE file |
| Chunk = query-named unit | `## Residential Roofing` chunk; query "roofing" hits it | `### No Hot Water` is an H3 buried under a shared `## Symptom Categories` |
| Chunk self-contained | pain + solution + ROI together | symptom's approved phrase/questions/do-not-say ARE together (good) but compete with 8 sibling symptoms + 5 other topics for top_k 3 |
| Prompt directs retrieval | "when {{industry}} known → find matching KB" | main has trigger pointers; but triage points at the mega-KB "for everything" |
| Filter/scope reliability | small focused KBs → 0.6 filter rarely drops the right chunk | big mixed KB → 0.6 filter + top_k 3 → wrong-topic chunks crowd out the right one |

**Root cause of <90% retrieval:** retrieval precision is set by chunk granularity and topic
separation, not by total tokens. The SDR has *more* tokens per KB but *sharper* chunks.

---

## 3. Current KB inventory + RAG-readiness score

Retrieval config: `top_k: 3`, `filter_score: 0.6` (global, all KBs).

| KB (file) | ~tokens | Topic(s) | Referenced from | RAG-ready? |
|---|---|---|---|---|
| uk-hvac-trade-kb.md | 2,967 | vocab, brands, 7 services, 9 symptoms, regulatory, safety, vulnerable, out-of-hours | triage | ❌ MEGA-KB — split needed |
| uk_address_kb.md | 3,428 | address structure, postcode, readback, spelling, field mapping | address | 🟡 good H2s, but big; top_k 3 can miss field-mapping vs readback chunks |
| uk_names_kb.md | 2,867 | 26 letter-groups under one H2 | greeter | ❌ semantic retrieval is wrong tool / granularity — promote letters to H2 |
| day_logic_kb.md | 1,619 | day-of-week, bank holidays, slot format | slot_selection | 🟡 procedural; chunk per rule-set needed |
| name_spelling_kb.md | 1,357 | 3-path spelling flow, phonetic alphabet | greeter, triage | 🟡 decision-tree; must stay ONE cohesive chunk |
| call_closing_kb.md | 970 | 4-step close, examples | main, triage, slot, booking | ✅ procedural, fine |
| kb_v2_interaction_rules.md | 331 | mirroring, off-script | main | ✅ small, fine |
| kb_v2_emergency_gas.md | ~200 | gas mention script | main (marker: `v2-gas-mention-kb` — NAME MISMATCH) | ✅ content fine; ❌ name misaligned |
| kb_v2_diagnostic_restraint.md | 204 | refusal phrase | triage | ✅ small, fine |
| kb_v2_knowledge_boundary.md | 125 | "engineer will look" fallback | (implicit) | ✅ small, fine |
| kb_v2_sample_phrases.md | 166 | acknowledgment phrases | main | ✅ small, fine |
| kb_v2_fee_rules.md | 96 | call-out fee | main, slot_selection | ✅ small, fine |
| kb_v2_company_briefing.md | 73 | company facts | main, greeter | ✅ small, fine |

**Hard finding:** 8 of 13 KBs are already fine *because they're small* (≤1,000 tokens → likely
1–3 chunks, retrieval is effectively whole-file). The failures live in the **three big KBs** and
the **one naming mismatch**.

---

## 4. Root causes (ranked)

1. **Mega-KB topic collision** (`uk-hvac-trade-kb`): a single query must compete across 5 topics for
   the same 3 chunks. "No hot water" can return [brand] + [service type] + [safety note] — zero useful.
2. **Symptom granularity**: 9 symptoms are `###` under one `## Symptom Categories`. If Retell chunks
   at H2, all 9 collapse into one overloaded chunk (retrieval returns everything or nothing). If it
   chunks at H3, they compete with 5 other topics for top_k 3.
3. **Names are not semantic**: `uk_names_kb` is a lookup table, not prose. Semantic retrieval of a
   *name* is the wrong mechanism unless each letter-group is its own chunk the query can land on.
4. **Chunk titles ≠ customer language**: target chunks are headed by internal labels
   ("Symptom Category", "Service Types") instead of the words the caller actually says
   ("no hot water", "radiator cold").
5. **Marker↔file name mismatch**: main prompt says `##v2-gas-mention-kb##`; the file is
   `kb_v2_emergency_gas.md`. Fragile hygiene (also contradicts the "drop 'emergency' vocabulary" rule).
6. **Passive retrieval**: several KBs say "populates automatically" — no state prompt tells the model
   *what query* to form, so retrieval is uncontrolled.

---

## 5. ASCII diagram — current vs target

```
CURRENT — mega-KB + flat name list:

  uk-hvac-trade-kb (2,967 tok)  ── ONE FILE, FIVE TOPICS ──
  ┌──────────────────────────────────────────────────────┐
  │ vocab │ brands │ services │ symptoms (9×H3 under 1H2) │ regulatory/safety │
  └──────────────────────────────────────────────────────┘
  query "no hot water"  → top_k 3 → [brand] [service] [safety]  ✗ symptom missed

  uk_names_kb (2,867 tok)  ── 26 ×H3 letter groups under ONE H2 ──
  query "Marcus" → top_k 3 → [A/B] [C/D] [E/F]  ✗ M missed


TARGET — topic-scoped KBs, one queryable `##` chunk each:

  uk-hvac-trade-kb  ──split 5-way──►
     service-types-kb      (7 ×H2, titled "Annual Boiler Service"…)
     symptom-questions-kb  (9 ×H2, titled "No Hot Water"… self-contained)
     boiler-brands-kb      (H2 per letter, or keep 1 small chunk)
     safety-regulatory-kb  (Gas Safe / CO / CP12 / BUS / vulnerable / hours)
     vocabulary            → already in main prompt (UK trade vocab block)

  uk_names_kb  ──promote──►  letter groups to H2 → one chunk per letter
     query "Marcus" → lands on "M" chunk ✓

  PROMPT (unchanged size):
     main = voice + "when to use each KB" triggers (765 tok)
     triage = "query ##symptom-questions-kb## for the symptom;
              query ##boiler-brands-kb## for the brand"
     (pointer edits only — zero token growth)

  RETRIEVAL FLOW (per trigger):
     "no hot water" ──► symptom-questions-kb ──► "No Hot Water" H2 chunk ──► 90%+ ✓
     "Marcus"       ──► uk-names-kb          ──► "M" H2 chunk          ──► 90%+ ✓
```

---

## 6. The restructure plan (per KB)

### 6.1 Split `uk-hvac-trade-kb.md` (2,967) → 4 topic KBs
| New KB | Chunks | Chunk titles = customer words |
|---|---|---|
| `symptom-questions-kb` | 9 ×H2 | "No Hot Water", "Banging / Kettling Noise", "Cold Radiators", "Pressure Dropping", "Error Code", "Not Firing", "Leak", "Controls", "No Heating" — each self-contained (approved phrase + questions + do-not-say + "book as breakdown") |
| `service-types-kb` | 7 ×H2 | "Boiler Breakdown", "Annual Boiler Service", "CP12", "New Boiler Quote", "Heat Pump", "Radiator / Pressure", "Thermostat / Controls" |
| `boiler-brands-kb` | 1–2 chunks | brand list + "capture in boiler_make" |
| `safety-regulatory-kb` | H2 per rule-set | Gas Safe Register · 0800 111 999 · CO symptoms · CP12 · BUS grant · vulnerable cues · out-of-hours |

Vocab stays **in the main prompt** (already done — 765-token main has the UK terms block).

### 6.2 Fix `uk_names_kb.md` (2,867)
Promote the 26 letter groups from `###` → `##` (one chunk per letter). A "Marcus" query then lands
on the `## M` chunk, making the 100%-match check reliable. (Alternative: move names to a lookup
tool — out of scope for this doc.)

### 6.3 Tune `uk_address_kb.md` (3,428)
Already has clean H2s; the risk is top_k 3 across 15+ chunks. Split by retrieval intent into
`uk-postcode-kb` (format + readback), `uk-address-readback-kb`, `uk-address-field-mapping-kb` so
each state query targets a small KB instead of one crowded one.

### 6.4 Keep-as-is (verified fine)
`day_logic_kb` (ensure each rule-set is its own `##` — mostly already), `name_spelling_kb`
(keep 3-path flow as ONE chunk: it is a decision tree, not a lookup), `call_closing_kb`,
all `kb_v2_*` small KBs.

### 6.5 Rename for hygiene
`kb_v2_emergency_gas.md` → `kb_v2_gas_mention.md` to match the main-prompt marker
`##v2-gas-mention-kb##` (and drop "emergency" from the name, consistent with the language rule).

---

## 7. What we change in the prompts (minimal — main stays ~765 tokens)

| File | Change | Token impact |
|---|---|---|
| Natural Speech main | (none required for KB split; markers stay as-is) | 0 |
| triage | repoint `##uk-hvac-trade-kb##` → `##symptom-questions-kb##` + `##boiler-brands-kb##` for their specific steps | ~0 (same-length pointer swap) |
| address | (after 6.3) repoint to the split address KBs per step | ~0 |
| main (optional) | if we later want the model to *form the query* explicitly, add "query the KB for the exact symptom the caller described" — ~15 tokens max | +15 max |

**Design rule going forward (harmonization):**
- **Main prompt = voice + global triggers** (phrasing, off-script, fees, gas, company, closing) — already the Natural Speech shape.
- **State prompts = flow + topic triggers** (symptom KB, brand KB, address KB, day-logic KB).
- **KBs = one topic each, one `##` chunk per queryable unit, chunk titles in caller language.**
- This is exactly the SDR pattern: prompt points, KB delivers.

---

## 8. What we are NOT changing (and why)

- **The voice coaching** in the Natural Speech main — it's the part that makes Tom sound human; untouched.
- **The JSON tools / edge schemas** — this is a retrieval-layer restructure; tool behaviour is unaffected.
- **kb_config numbers** (`top_k 3, filter 0.6`) — with focused KBs these become reliable; no tuning needed first pass. Re-visit only if a specific lookup still misses.
- **Total KB token budget** — the split re-organises ~2,967 tokens into 4 KBs; no content bloat.

---

## 9. Acceptance criteria (how we know retrieval hit 90%)

1. LLM-to-LLM runs where a caller says "no hot water but heating works" → the agent uses the
   **"No Hot Water"** approved phrase verbatim (proves the right symptom chunk was retrieved).
2. Caller says a rare name (e.g., "Siobhan") → agent proceeds through the **M/N/S spelling path**,
   not a generic retry (proves the name chunk landed).
3. Caller says "smell of gas" → agent uses the gas script + 0800 111 999 (proves the gas KB was
   retrieved via the corrected marker).
4. Every state prompt's KB pointer resolves to a KB that exists with that exact name.
5. Main prompt stays ≤ ~800 tokens after all edits.

---

## 10. Suggested execution order (future, not done)

1. Split `uk-hvac-trade-kb.md` → 4 KBs (6.1). 2. Promote name letters to H2 (6.2).
3. Split/retarget `uk_address_kb` (6.3). 4. Rename gas KB (6.5). 5. Repoint triage/address
   prompt markers (Section 7). 6. Rebuild as a NEW LLM (never patch), re-run happy-path +
   symptom/name/gas probe scenarios, measure against Section 9.
