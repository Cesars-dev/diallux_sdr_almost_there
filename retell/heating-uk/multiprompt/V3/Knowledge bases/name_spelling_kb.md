# Name Spelling Knowledge Base

> Retrieved automatically when a customer's name does NOT have a 100% match in `##uk-names-kb##`. The agent follows this KB to confirm spelling using TTS-friendly hyphenation.

---

## When to Use This KB

1. Customer says their name.
2. Agent retrieves `##uk-names-kb##` and checks for a 100% match.
3. If 100% match → use the name. Done.
4. If NO match → follow the rules in this KB.

---

## The 3-Path Name Confirmation Flow

### Path 1: 100% Match in `##uk-names-kb##`

Use the name as-is. Mirror back naturally:
<Right, [NAME] — lovely.>

No spelling confirmation needed. Move on.

### Path 2: No Match — Agent Spells It Back for Confirmation

If the spoken name doesn't match the KB, the agent spells it back hyphenated for TTS, then asks for confirmation:

<Just to make sure I've got that — is it [HYPHENATED-SPELLING]?>

Examples:
- Customer says "Mirikit" → <Just to make sure I've got that — is it M-I-R-I-K-I-T?>
- Customer says "Loughlin" → <Just to make sure I've got that — is it L-O-U-G-H-L-I-N?>
- Customer says "Xochitl" → <Just to make sure I've got that — is it X-O-C-H-I-T-L?>

#### Customer Confirms

If the customer says "yes", "that's right", "correct", "perfect", or any other acknowledgement:
→ Use the name. Move on.

#### Customer Corrects

If the customer says "no, it's actually..." or gives a different spelling:
→ Ask the customer to spell it: <Could you spell that for me?>
→ When the customer spells it, confirm back hyphenated: <Got it — [HYPHENATED-SPELLING]. Right?>
→ Wait for confirmation, then use it.

### Path 3: Customer Spells It Themselves

If the customer spells their name without being asked (common for unusual names):

1. Listen to the spelling.
2. Confirm back hyphenated: <Got it — [HYPHENATED-SPELLING]. Right?>
3. Wait for confirmation.
4. If confirmed → use it.
5. If customer corrects → re-confirm with the correction.

---

## TTS Hyphenation Rules for Names

### Rule 1: Hyphenate Every Character

Write each character separated by hyphens. ElevenLabs v2 reads hyphenated single characters as individual letters.

- **MIRIKIT** → `M-I-R-I-K-I-T`
- **LOUGHLIN** → `L-O-U-G-H-L-I-N`
- **XOCHITL** → `X-O-C-H-I-T-L`

Never write the name as a single token like `MIRIKIT` — ElevenLabs v2 will mangle it.

### Rule 2: Use Uppercase

Write the letters in uppercase. This signals "spell it out" to the TTS engine more reliably than lowercase.

### Rule 3: Say "is it" Before the Spelling

Always preface the hyphenated spelling with "is it" or "got it":
<Just to make sure I've got that — is it M-I-R-I-K-I-T?>
<Got it — L-O-U-G-H-L-I-N. Right?>

This signals to the customer (and the TTS) that a spelling is coming.

### Rule 4: Handle Double Letters

If a name has double letters (e.g. "Annabelle"), spell each letter individually:
- `A-N-N-A-B-E-L-L-E` (not `A-NN-A-B-E-LL-E`)

### Rule 5: Handle Hyphenated Names

If the customer has a hyphenated name (e.g. "Mary-Jane"), treat as two parts:
<Is it M-A-R-Y, hyphen, J-A-N-E?>

Or simply ask: <Is that Mary-Jane, with a hyphen?>

---

## Phonetic Alphabet for Ambiguous Letters

If the customer is spelling their name and the agent isn't sure about a letter (B vs D, M vs N, P vs T), use phonetic clarification:

| Letter | British phonetic words |
|---|---|
| A | Apple, Andrew |
| B | Bicycle, Bob |
| C | Charlie, Catherine |
| D | David, Dog |
| E | Edward, Elephant |
| F | Freddie, Father |
| G | George, Gee |
| H | Harry, Henry |
| I | Isaac, Indigo |
| J | John, Jack |
| K | King, Katie |
| L | Liverpool, Larry |
| M | Mother, Mary |
| N | Newcastle, Nellie |
| O | Oliver, Oscar |
| P | Peter, Paul |
| Q | Queen, Quentin |
| R | Robert, Roger |
| S | Sugar, Samuel |
| T | Thomas, Terry |
| U | Uncle, Ursula |
| V | Victor, Victoria |
| W | William, Wendy |
| X | X-ray, Xavier |
| Y | Yellow, Yvonne |
| Z | Zebra, Zach |

Example:
<Just so I've got it — is that N for Newcastle, A for Apple, D for David, I for Isaac, A for Apple?>

---

## When NOT to Use This KB

- If the name has a 100% match in `##uk-names-kb##` → use Path 1, don't spell.
- If the customer is clearly giving a common name and you understood it → use Path 1.
- If the customer asks "do you need me to spell it?" → say <No, I've got it — [NAME].> if you're confident, OR <Yes please, just to make sure.> if you're not.

---

## Critical Rules

- Always hyphenate name spellings in spoken responses — `M-I-R-I-K-I-T`, never `MIRIKIT`
- Use uppercase letters
- Say "is it" or "got it" before the spelling
- Spell each letter individually, including doubles (A-N-N-A, not A-NN-A)
- If unsure about a letter, use phonetic clarification
- Never write a name as a single token in a spoken response — TTS will mangle it
