# UK Address Handling — Knowledge Base

> This is a focused Knowledge Base for address understanding and readback. It teaches the agent (a) how UK addresses are structured so it can parse what the customer says, (b) how to write addresses in TTS-friendly format so ElevenLabs v2 reads them clearly, and (c) how to confirm ambiguous letters using common British words.
>
> Link this as a separate Knowledge Base in Retell alongside `uk-hvac-trade-kb`. Or merge the contents into the trade KB if you prefer one KB — both work.

---

## UK Address Structure

A UK address has up to 5 parts:

1. **House number or name** — e.g. "14", "14a", "Rose Cottage", "Flat 2"
2. **Line 1** — street name, e.g. "Victoria Terrace"
3. **Line 2** — often empty, sometimes a locality or flat
4. **City / town** — e.g. "Newcastle upon Tyne"
5. **Postcode** — e.g. "NE4 5AB"

The agent only needs three of these for booking: **house number/name, line 1 (street), city, and postcode**. The `lookup_address` webhook returns all of them. The agent's job is to **read them back in a TTS-friendly way** and confirm.

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

A full postcode covers ~15 addresses on average. That's why postcode alone is often not enough — the agent usually needs the house number too.

---

## How to Read a Postcode Aloud (TTS-Friendly)

**This is the critical section for ElevenLabs v2.**

If the agent writes a postcode like `NE4 5AB` in its response, ElevenLabs v2 will read it unpredictably — could be "knee four five ab", "north-east-four-five-ab", "nee-four-five-ab", or anything else.

**The fix: write each character separated by hyphens.** ElevenLabs v2 reads hyphenated single characters as individual letters.

### Rules for writing postcodes in spoken text

1. **Always separate characters with hyphens.** Write `N-E-4-5-A-B`, never `NE4 5AB`.
2. **Add the word "postcode" before it** so the customer knows what's coming: "So that's postcode N-E-4-5-A-B."
3. **Group as outward-inward** if it helps clarity: "N-E-4, then 5-A-B."
4. **Never write the postcode as a single token** in a response — TTS will mangle it.

### Examples of correct readback

**Customer says postcode is "NE4 5AB".**

The agent's response should contain:

> "So that's postcode N-E-4-5-A-B — right?"

Not:

> "So that's NE4 5AB — right?"  ❌ (TTS will mangle this)

**Customer says postcode is "SW1A 1AA".**

> "Postcode S-W-1-A-1-A-A — confirmed?"

**Customer says postcode is "M1 1AE".**

> "M-1-1-A-E — got it?"

### Why hyphens work

ElevenLabs v2 (and most TTS engines) treat a hyphenated sequence of single characters as an abbreviation to spell out. `N-E-4-5-A-B` is read as six distinct characters. `NE4 5AB` is read as a single token, and the engine guesses at pronunciation — usually wrong.

---

## How to Read a House Number or Name Aloud

### Plain number (most common)

Customer says "fourteen". Agent reads back: "number fourteen" or just "fourteen".

> "So that's 14 Victoria Terrace, postcode N-E-4-5-A-B — right?"

Write `14` as a digit. ElevenLabs v2 reads `14` as "fourteen" correctly.

### Number with letter suffix

Customer says "fourteen ay" (meaning 14a). Agent reads back:

> "So that's 14-A Victoria Terrace..."

Write as `14-A` with the hyphen. ElevenLabs reads it as "fourteen A". Writing `14a` without a hyphen risks "fourteen-uh" or "fourteen-ayy" unpredictably.

### House name

Customer says "Rose Cottage". Agent reads back the name verbatim:

> "So that's Rose Cottage, Victoria Terrace..."

No special TTS handling needed — names read fine.

### Flat or apartment

Customer says "Flat 2, 14 Victoria Terrace". Agent reads back:

> "So that's Flat 2, 14 Victoria Terrace..."

If the flat has a letter like "Flat 2A", write it as `Flat 2-A`.

---

## How to Read a Full Address Back

The `lookup_address` webhook returns a `formatted_for_readback` field. **The agent reads this verbatim**, but with one transformation:

**Insert hyphens in the postcode portion before reading.**

If the webhook returns:

```
"formatted_for_readback": "14 Victoria Terrace, Newcastle upon Tyne, NE4 5AB"
```

The agent speaks it as:

> "So that's 14 Victoria Terrace, Newcastle — postcode N-E-4-5-A-B — right?"

### Three transformations the agent applies

1. **City simplification.** If the city has "upon Tyne", "upon Avon", "on Sea" etc., the agent may drop the suffix for naturalness ("Newcastle" instead of "Newcastle upon Tyne"). Optional — only if it sounds more natural.

2. **Postcode hyphenation.** Always convert `XX## #XX` to `X-X-#-#-#-X-X` before speaking.

3. **"Postcode" prefix.** Always say "postcode" before spelling it out, so the customer knows what's coming.

### Example full readback patterns

> "So that's 14 Victoria Terrace, Newcastle — postcode N-E-4-5-A-B. Is that right?"

> "Right, so that's 27 Ashley Road, Sunderland — postcode S-R-3-1-X-X. Confirmed?"

> "Got it — Rose Cottage, Mill Lane, Hexham — postcode N-E-4-6-1-J-Q. Sound right?"

---

## Understanding the Customer When They Spell

Customers often spell postcodes aloud because UK postcodes are ambiguous over the phone (B/D/M/N/P/T all sound similar). The agent must understand both natural-language and spelled-out versions.

### Single-letter spelling

Customer might say:
- "en ee four five ay bee" → `NE4 5AB`
- "ess double-you one ay one double-ay" → `SW1A 1AA`
- "em one one ay ee" → `M1 1AE`

The agent treats sequences of letter-names as the spelling of the postcode.

### Phonetic alphabet (NATO or British variants)

Customers often use words to clarify letters:

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

When a customer says "N for Newcastle, E for Edward, four, five, A for Apple, B for Bob", the agent parses this as `NE4 5AB`.

### When the agent isn't sure

If the agent cannot confidently parse a spelled-out postcode, it must ask for confirmation using its own phonetic clarification:

> "Just so I've got it — N for Newcastle, E for Edward, four, five, A for Apple, B for Bob — is that right?"

This is the only time the agent uses phonetic alphabet itself. Otherwise, it just spells out letters with hyphens.

---

## Common UK Place Names — Tricky Pronunciations

UK place names often don't sound how they're spelled. ElevenLabs v2 handles most of these correctly because they're in its training data, but the agent should be aware of the patterns in case the customer uses the spelled version.

| Written | Spoken | Notes |
|---|---|---|
| Newcastle upon Tyne | "Newcastle upon Tyne" or just "Newcastle" | |
| Stoke-on-Trent | "Stoke on Trent" | |
| Stratford-upon-Avon | "Stratford upon Avon" | |
| Kingston upon Thames | "Kingston upon Thames" | |
| Leicester | "Lester" | NOT "lie-cess-ter" |
| Worcester | "Wooster" | NOT "war-cess-ter" |
| Gloucester | "Gloster" | NOT "glow-cess-ter" |
| Edinburgh | "Edinburra" | Scottish — roll the r slightly |
| Glasgow | "Glesga" (local) or "Glasgow" | |
| Dundee | "Dundee" | |
| Aberdeen | "Aberdeen" | |
| Llanelli | "Thlan-ethli" | Welsh — the Ll is a voiceless lateral |
| Wrexham | "Reks-am" | |
| Hawick | "Hoik" | Scottish Borders — surprising |
| Milngavie | "Mull-guy" | Near Glasgow |
| Frome | "Froom" | Somerset |
| Bury | "Berry" | Greater Manchester / Lancashire |
| Bury St Edmunds | "Berry St Edmunds" | Suffolk |
| Belvoir | "Beaver" | Belvoir Castle |
| Cholmondeley | "Chumley" | Cheshire |
| Mousehole | "Mowz-el" | Cornwall |
| Woolfardisworthy | "Woolsery" | Devon |
| Pontypridd | "Pontypreeth" | Wales |

For the agent's purposes: the customer will say the spoken form, and the webhook returns the written form. The agent reads back the spoken form (which it can infer from the written form for major cities; for unusual villages, just use what the customer said).

---

## Confirmation Patterns

The agent confirms the address in two situations:

### 1. After `lookup_address` returns a single match

Read the address back (with hyphenated postcode) and ask for explicit confirmation.

Patterns (vary, never verbatim every call):

- "So that's 14 Victoria Terrace, Newcastle — postcode N-E-4-5-A-B. Right?"
- "Right, so that's 27 Ashley Road, Sunderland — S-R-3-1-X-X. Confirmed?"
- "Got it — Rose Cottage, Mill Lane, Hexham — N-E-4-6-1-J-Q. Sound right?"

Wait for the customer to say yes. If they say no or correct anything, re-call `lookup_address` with the correction.

### 2. When the customer spelled it out and the agent wants to verify before calling the tool

If the customer spelled a postcode and the agent is even slightly unsure, confirm using phonetic clarification before calling `lookup_address`:

> "Just so I've got it — N for Newcastle, E for Edward, four, five, A for Apple, B for Bob — is that right?"

Then call `lookup_address`.

---

## Edge Cases

### Customer doesn't know the postcode

> "No problem — what's the first line of the address and the city? I'll find it from there."

Then call `lookup_address` with just the postcode field empty (if your webhook supports reverse lookup by street + city) — or ask for the postcode specifically as it's needed for engineer routing.

For the demo, if the customer doesn't know the postcode, fall back to: "I'll text you a quick link — just tap it and your phone will share your address with us."

### Customer gives a partial postcode ("NE4")

> "I need the full postcode to find you — should be something like N-E-4-something-something. Could you check?"

### Customer gives a non-UK postcode ("90210")

> "That looks like a US zip code — we cover the UK only. Are you in the UK?"

### Customer is in a new build not yet on Royal Mail's database

`lookup_address` will return 0 matches. Agent falls back to SMS link.

### Customer gives a business name instead of an address

> "Got it — what's the postcode for the business? I'll find it that way."

---

## What the Agent Never Does

- **Writes a postcode as a single token in a spoken response.** Always hyphenate.
- **Reads the `uprn` field aloud.** It's a 12-digit internal ID for CRM use only.
- **Assembles the address from `line1`, `line2`, `city`, `postcode` fields itself.** Use `formatted_for_readback` from the webhook.
- **Confirms an address the customer did not verbally agree to.** Wait for explicit "yes" / "that's right" / "correct" before proceeding.
- **Skips the postcode readback.** The postcode is the most error-prone field — it must always be confirmed.
- **Uses Americanisms.** "Zip code", "apartment", "street address" — all forbidden. Use "postcode", "flat", "address".

---

## Address Field Mapping — Variable Extraction

When the customer gives their address, split it into the correct dynamic variable:

| Customer gives | Store in |
|---|---|
| House number or property name | address_house_number |
| Street name only | address_street |
| City or town | address_city |
| Postcode | address_postcode |

Example — "14 Victoria Terrace, Newcastle, NE4 5AB":
- 14 → address_house_number
- Victoria Terrace → address_street
- Newcastle → address_city
- NE4 5AB → address_postcode

Never put the street in address_house_number. Never put the number in address_street. If they give a combined value like "14 Victoria Terrace" in one phrase, split at the first space: first word → address_house_number, rest → address_street.
