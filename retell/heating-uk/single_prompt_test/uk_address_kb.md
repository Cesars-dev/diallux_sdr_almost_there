# UK Address Handling — Knowledge Base

> Teaches the agent UK address structure, TTS-friendly postcode formatting for ElevenLabs v2, phonetic alphabet parsing, and confirmation patterns. Address is captured conversationally by the prompt — this KB provides the rules for formatting and understanding what the customer says.

---

## UK Address Structure

A UK address has up to 5 parts:

1. **House number or name** — e.g. "14", "14a", "Rose Cottage", "Flat 2"
2. **Line 1** — street name, e.g. "Victoria Terrace"
3. **Line 2** — often empty, sometimes a locality or flat
4. **City / town** — e.g. "Newcastle upon Tyne"
5. **Postcode** — e.g. "NE4 5AB"

The agent needs **house number/name, street, city, and postcode** for booking. Capture these from the customer conversationally.

---

## UK Postcode Format

A UK postcode has two halves separated by a space:

- **Outward code** (2–4 characters): area + district. Letters + digits, e.g. "NE4", "SW1A", "M1", "B33".
- **Inward code** (always 3 characters): sector + unit. Digit + 2 letters, e.g. "5AB", "1AA", "8BD".

Examples:
- `NE4 5AB` — Newcastle, district 4, sector 5, unit AB
- `SW1A 1AA` — Buckingham Palace
- `M1 1AE` — central Manchester
- `B33 8TH` — Birmingham

The first 1–2 letters indicate the area:
- `NE` = Newcastle / North East
- `SW` = South West London
- `M` = Manchester
- `B` = Birmingham
- `L` = Liverpool
- `G` = Glasgow
- `EH` = Edinburgh
- `CF` = Cardiff
- `BT` = Belfast
- `BS` = Bristol
- `LS` = Leeds
- `S` = Sheffield
- `PL` = Plymouth
- `EX` = Exeter

A full postcode covers ~15 addresses on average. The agent usually needs the house number too.

---

## How to Read a Postcode Aloud (TTS-Friendly)

**Critical for ElevenLabs v2.** If you write a postcode like `NE4 5AB`, ElevenLabs v2 will read it unpredictably.

**The fix: write each character separated by hyphens.** `N-E-4-5-A-B` is read clearly as individual letters.

### Rules

1. **Always separate characters with hyphens.** Write `N-E-4-5-A-B`, never `NE4 5AB`.
2. **Add the word "postcode" before it** so the customer knows what's coming.
3. **Never write a postcode as a single token** in a response.

### Examples

> "So that's postcode N-E-4-5-A-B — right?"
> "Postcode S-W-1-A-1-A-A — confirmed?"
> "M-1-1-A-E — got it?"

---

## How to Read a House Number or Name Aloud

- **Plain number:** Write `14` as a digit — ElevenLabs reads it as "fourteen" correctly.
- **Number with letter suffix:** Write `14-A` with hyphen — ElevenLabs reads it as "fourteen A". Writing `14a` risks mangled pronunciation.
- **House name:** Read it verbatim, no special handling needed.
- **Flat or apartment:** "Flat 2, 14 Victoria Terrace". If "Flat 2A", write as `Flat 2-A`.

---

## How to Read a Full Address Back

The agent reads back the address it captured from the customer, with the postcode hyphenated:

> "So that's 14 Victoria Terrace, Newcastle — postcode N-E-4-5-A-B — right?"

### Three formatting rules

1. **City simplification** — drop "upon Tyne", "upon Avon", etc. for naturalness ("Newcastle" not "Newcastle upon Tyne"). Optional.
2. **Postcode hyphenation** — always convert `XX## #XX` to `X-X-#-#-#-X-X`.
3. **"Postcode" prefix** — always say "postcode" before spelling it out.

### Example readback patterns

> "So that's 14 Victoria Terrace, Newcastle — postcode N-E-4-5-A-B. Is that right?"
> "Right, so that's 27 Ashley Road, Sunderland — postcode S-R-3-1-X-X. Confirmed?"
> "Got it — Rose Cottage, Mill Lane, Hexham — postcode N-E-4-6-1-J-Q. Sound right?"

---

## Understanding the Customer When They Spell

Customers often spell postcodes because UK postcodes are ambiguous over the phone (B/D/M/N/P/T sound similar).

### Single-letter spelling

- "en ee four five ay bee" → `NE4 5AB`
- "ess double-you one ay one double-ay" → `SW1A 1AA`
- "em one one ay ee" → `M1 1AE`

### Phonetic alphabet (NATO or British variants)

| Letter | Common British phonetic words |
|---|---|
| A | Apple, Alpha, Andrew |
| B | Bicycle, Bravo, Bob |
| C | Charlie, Cat, Catherine |
| D | David, Delta, Dog |
| E | Elephant, Echo, Edward |
| F | Freddie, Foxtrot, Father |
| G | George, Golf, Gee |
| H | Harry, Hotel, Henry |
| I | India, Indigo, Isaac |
| J | John, Juliet, Jack |
| K | King, Kilo, Katie |
| L | Liverpool, Lima, Larry |
| M | Mother, Mike, Mary |
| N | Newcastle, November, Nellie |
| O | Orange, Oscar, Oliver |
| P | Peter, Papa, Paul |
| Q | Queen, Quebec, Quentin |
| R | Robert, Romeo, Roger |
| S | Sugar, Sierra, Samuel |
| T | Thomas, Tango, Terry |
| U | Uncle, Uniform, Ursula |
| V | Victor, Victoria |
| W | William, Whisky, Wendy |
| X | X-ray, Xavier |
| Y | Yellow, Yankee, Yvonne |
| Z | Zebra, Zulu, Zach |

When a customer says "N for Newcastle, E for Edward, four, five, A for Apple, B for Bob", parse this as `NE4 5AB`.

### When not sure

If unsure, confirm using phonetic clarification:

> "Just so I've got it — N for Newcastle, E for Edward, four, five, A for Apple, B for Bob — is that right?"

---

## Common UK Place Names — Tricky Pronunciations

| Written | Spoken | Notes |
|---|---|---|
| Newcastle upon Tyne | "Newcastle upon Tyne" or just "Newcastle" | |
| Stoke-on-Trent | "Stoke on Trent" | |
| Leicester | "Lester" | NOT "lie-cess-ter" |
| Worcester | "Wooster" | NOT "war-cess-ter" |
| Gloucester | "Gloster" | NOT "glow-cess-ter" |
| Edinburgh | "Edinburra" | Scottish |
| Glasgow | "Glasgow" | |
| Bury | "Berry" | |
| Belvoir | "Beaver" | |
| Cholmondeley | "Chumley" | |
| Mousehole | "Mowz-el" | Cornwall |
| Woolfardisworthy | "Woolsery" | Devon |
| Pontypridd | "Pontypreeth" | Wales |

The customer will say the spoken form. Read it back the same way they said it.

---

## Confirmation Patterns

After capturing the full address from the customer (postcode + house number), read it back and confirm:

> "So that's 14 Victoria Terrace, Newcastle — postcode N-E-4-5-A-B. Right?"
> "Right, so that's 27 Ashley Road, Sunderland — S-R-3-1-X-X. Confirmed?"
> "Got it — Rose Cottage, Mill Lane, Hexham — N-E-4-6-1-J-Q. Sound right?"

Wait for explicit confirmation. If they correct anything, re-confirm.

---

## Edge Cases

### Customer doesn't know the postcode
> "No problem — what's the first line of the address and the city?"

For the demo, if they still can't provide it: "I'll text you a quick link — just tap it and your phone will share your address with us."

### Customer gives a partial postcode ("NE4")
> "I need the full postcode to find you — could you check?"

### Customer gives a non-UK postcode
> "That looks like a US zip code — we cover the UK only. Are you in the UK?"

### Customer gives a business name
> "Got it — what's the postcode for the business?"

---

## What the Agent Never Does

- **Writes a postcode as a single token in a spoken response.** Always hyphenate.
- **Confirms an address the customer did not verbally agree to.** Wait for explicit confirmation.
- **Skips the postcode readback.** The postcode is the most error-prone field.
- **Uses Americanisms.** "Zip code", "apartment", "street address" — forbidden. Use "postcode", "flat", "address".
