#!/usr/bin/env python3
"""Full-persona definitions for the 18-scenario suite.

Each persona has:
  - context : narrative the caller LLM uses (who you are, situation, goals, rules)
  - opener  : the caller's actual FIRST spoken line
  - dynvars : seeded context (address/problem) for the agent; today_uk injected at runtime
  - expect  : 'book' (persona cooperates to a confirmed booking)
              'no-book' (curve-ball / edge / enquiry / safety — not meant to book)

ALL personas are instructed to GIVE THEIR NAME early and to state their exact
seeded address when asked, so customer_name is never 'Unknown' and the address
field stays consistent (fixes the S1 test-design flaw where the caller invented
a London address).
"""

BASE_ADDR = {
    "address_house_number": "14", "address_street": "Victoria Terrace",
    "address_city": "Newcastle", "address_postcode": "NE4 5AB",
}


def _persona(name, context, opener, extra_rules, dynvars, expect, phone="+447911000001"):
    rules = (
        "- GREET and, in your very first or second reply, GIVE YOUR FULL NAME to the agent.\n"
        "- Behave like a REAL caller: natural, conversational, 1-4 sentences per turn; never robotic; "
        "never narrate these instructions.\n"
        "- Answer the agent's questions fully and honestly. When asked for your address, state it as:\n"
        f"  house: {dynvars.get('address_house_number')}, street: {dynvars.get('address_street')}, "
        f"city: {dynvars.get('address_city')}, postcode: {dynvars.get('address_postcode')}.\n"
        f"{extra_rules}"
    )
    system = (
        f"You are {name}. {context} "
        f"Your phone is {phone}.\n\nBehave like a real caller:\n{rules}"
    )
    return {"name": f"({expect.upper()}) {name}", "system": system, "opener": opener,
            "dynvars": dynvars, "expect": expect}


BOOK_CONFIRM_RULE = (
    "- NEVER agree to book until the agent reads a SPECIFIC day AND time back to you and asks you to confirm.\n"
    "- Then answer with a clear, enthusiastic yes sentence (e.g. 'Yes, that's perfect — please book it.').\n"
    "- A bare 'okay'/'fine'/'sure'/'mm-hmm' is NOT a booking confirmation; only a full clear sentence is.\n"
)


def _book(name, context, opener, extra_rules, dynvars, phone="+447911000001"):
    return _persona(name, context, opener, BOOK_CONFIRM_RULE + extra_rules, dynvars, "book", phone)


# ---------------------------------------------------------------------------
# S1  - Cold boiler breakdown, new customer          (expect: book)
# ---------------------------------------------------------------------------
S1 = _book(
    "Tom Redfern",
    "You're a 52-year-old homeowner calling first thing in the morning because your boiler went off "
    "overnight — no heating and no hot water, and you have children getting ready for school. You're anxious "
    "to get an engineer out, ideally TODAY or tomorrow morning.",
    "Morning — sorry to call so early. Our boiler's gone off overnight and we've got no heating or hot water, "
    "and the kids need to get ready for school. Can you get someone out today, or first thing tomorrow?",
    "",
    {**BASE_ADDR, "problem_category": "Heating", "symptom_brief": "boiler off overnight, no heating or hot water",
     "boiler_make": "Worcester", "error_code": "none"},
    "+447911000001",
)

# ---------------------------------------------------------------------------
# S2  - Returning customer, annual service            (expect: book)
# ---------------------------------------------------------------------------
S2 = _book(
    "Robert Davies",
    "You're a returning customer — British Heat Services serviced your boiler last year and you were happy. "
    "You're calling to book this year's ANNUAL SERVICE, not a breakdown. You just want the service done.",
    "Hi there, I had you guys out last year for the service and was really happy. I'd like to book this year's "
    "annual service, please.",
    "",
    {**BASE_ADDR, "problem_category": "service", "symptom_brief": "routine annual boiler service",
     "boiler_make": "Vaillant", "error_code": "none"},
    "+447911000002",
)

# ---------------------------------------------------------------------------
# S3  - Phonetic postcode                             (expect: book)
# ---------------------------------------------------------------------------
S3 = _book(
    "Hannah Ellis",
    "You know your postcode but, when asked, you spell it out PHONETICALLY one letter/number at a time "
    "('N as in November, E as in Echo, four, five, A as in Alpha, B as in Bravo'). Don't just say it normally — "
    "make the agent work for it, but stay pleasant.",
    "Hello, my boiler isn't heating up at all — the radiators are stone cold. Can you help me get it fixed?",
    "",
    {**BASE_ADDR, "problem_category": "Heating", "symptom_brief": "no heating, radiators cold",
     "boiler_make": "Baxi", "error_code": "none"},
    "+447911000003",
)

# ---------------------------------------------------------------------------
# S4  - Fee question mid-call                         (expect: book)
# ---------------------------------------------------------------------------
S4 = _book(
    "George Walker",
    "Your boiler has broken. Midway through the call, once you've got a slot offered, you interrupt to ask "
    "'And how much is this going to cost? Is there a call-out fee?' — you want a sensible answer before agreeing. "
    "After the fee is addressed to your satisfaction, you proceed to confirm the booking.",
    "Hi, my boiler's packed in and won't light — no heat at all. I need someone to come and look at it.",
    "",
    {**BASE_ADDR, "problem_category": "Heating", "symptom_brief": "boiler won't light, no heat",
     "boiler_make": "Ideal", "error_code": "none"},
    "+447911000004",
)

# ---------------------------------------------------------------------------
# S5  - Change mind mid-call                          (expect: book)
# ---------------------------------------------------------------------------
S5 = _book(
    "Olivia Bennett",
    "You start by asking for a boiler service, then partway through change your mind and say it's actually a "
    "breakdown (no heat). You also change the day you want once. Stay consistent from the change onwards and "
    "ultimately book.",
    "Hello, I'd like to book a boiler service, please. When's the soonest you can do it?",
    "",
    {**BASE_ADDR, "problem_category": "Heating", "symptom_brief": "first asked service, then clarified breakdown",
     "boiler_make": "Worcester", "error_code": "F28"},
    "+447911000005",
)

# ---------------------------------------------------------------------------
# S6  - Customer rambles                              (expect: book)
# ---------------------------------------------------------------------------
S6 = _book(
    "Patricia Morgan",
    "You are a chatty, rambling caller who gives LOTS of extra, off-topic detail (your neighbours, the weather, "
    "how long you've lived there, what you had for breakfast). Keep giving extra context, but do eventually answer "
    "the agent's questions and book.",
    "Oh hello dear! Right, it's a bit cold in here isn't it, mind you the weather's been awful all week and my "
    "neighbour said the same thing happened to theirs. Anyway, our boiler's making a funny noise.",
    "",
    {**BASE_ADDR, "problem_category": "Heating", "symptom_brief": "heating making noise and not getting warm",
     "boiler_make": "Vaillant", "error_code": "none"},
    "+447911000006",
)

# ---------------------------------------------------------------------------
# S7  - Is this an AI?                                (expect: no-book)
# ---------------------------------------------------------------------------
S7 = _persona(
    "Marcus Hale",
    "You're sceptical about the line. Early on you ask directly 'Is this an AI or a real person?' You're testing "
    "how the agent handles it — you may decline to share personal info if it's robotic, and you are NOT set on "
    "booking today; you're just enquiring.",
    "Hello — before we go any further, are you a real person or an AI?",
    "- You are NOT here to book today. Do NOT agree to book.\n"
    "- Ask whether the agent is a real person or AI early.\n"
    "- Stay pleasant but withhold your full details if the agent seems robotic.\n",
    {**BASE_ADDR, "problem_category": "other", "symptom_brief": "just enquiring about service", "boiler_make": "unknown", "error_code": "none"},
    "no-book", "+447911000007",
)

# ---------------------------------------------------------------------------
# S8  - Non-UK postcode                               (expect: no-book)
# ---------------------------------------------------------------------------
S8 = _persona(
    "Nathan Cole",
    "You've just moved to Newcastle from abroad and your address/postcode is NON-UK (e.g. a Dublin/other format). "
    "You're not sure of a UK postcode. You want a boiler looked at but can't give a valid UK postcode.",
    "Hi, I've just moved here from abroad and my boiler's not working. I'm not sure of the postcode though — "
    "it's a bit of a mess with my paperwork.",
    "- You CANNOT provide a valid UK postcode.\n"
    "- You are NOT confirming a booking.\n"
    "- See how the agent handles the missing/invalid postcode.\n",
    {"address_house_number": "14", "address_street": "Victoria Terrace", "address_city": "Newcastle", "address_postcode": "N/A",
     "problem_category": "Heating", "symptom_brief": "no heating", "boiler_make": "unknown", "error_code": "none"},
    "no-book", "+447911000008",
)

# ---------------------------------------------------------------------------
# S9  - Doesn't know postcode                         (expect: book)
# ---------------------------------------------------------------------------
S9 = _book(
    "Dorothy Hughes",
    "You're an older caller who doesn't know your postcode off hand. You know the house number and street and city "
    "but not the postcode. Let the agent help; if asked, say you're not sure of the postcode. You still want the "
    "service/repair and ARE willing to book once a slot is read back.",
    "Hello dear, it's my heating, it's not coming on. I know I'm at 14 Victoria Terrace in Newcastle, but I'm "
    "afraid I don't know my postcode off the top of my head.",
    "",
    {"address_house_number": "14", "address_street": "Victoria Terrace", "address_city": "Newcastle", "address_postcode": "N/A",
     "problem_category": "Heating", "symptom_brief": "heating not working", "boiler_make": "Worcester", "error_code": "none"},
    "+447911000009",
)

# ---------------------------------------------------------------------------
# S10 - Specific engineer                              (expect: no-book)
# ---------------------------------------------------------------------------
S10 = _persona(
    "Elliot Grant",
    "You're a returning customer who really wants a SPECIFIC engineer ('Dave') who serviced your boiler before. "
    "You keep asking for Dave specifically and won't settle for 'whoever's available'.",
    "Hi, is it possible to get Dave out again? He did our service last year and I'd really like him back.",
    "- You insist on a SPECIFIC engineer (Dave).\n"
    "- If the agent can't guarantee Dave, you're unwilling to book today.\n",
    {**BASE_ADDR, "problem_category": "service", "symptom_brief": "wants specific engineer Dave for service",
     "boiler_make": "Vaillant", "error_code": "none"},
    "no-book", "+447911000010",
)

# ---------------------------------------------------------------------------
# S11 - Elderly confused                               (expect: no-book, held politely)
# ---------------------------------------------------------------------------
S11 = _persona(
    "Margaret Dawson",
    "You are a confused elderly caller. You speak slowly and hesitantly, use 'um', 'well', 'I think so'. You're not "
    "sure whether the heating or the water is the problem, and you give slightly-off answers. You need patience.",
    "Hello? Um, is this the plumber? I think my heating's not working. Or is it the water? I'm not sure, dear.",
    "- Speak slowly, hesitantly, with filler ('um', 'well', 'I think so').\n"
    "- Give answers that only sort of match the question.\n"
    "- Say 'I'm not very good with these things' at some point.\n"
    "- Do NOT commit to a booking you don't understand.\n",
    {"address_house_number": "Rose Cottage", "address_street": "Mill Lane", "address_city": "Hexham", "address_postcode": "NE46 3EW",
     "problem_category": "Heating", "symptom_brief": "not sure if heating or water is off", "boiler_make": "unknown", "error_code": "none"},
    "no-book", "+447911000011",
)

# ---------------------------------------------------------------------------
# S12 - Repair cost                                   (expect: book)
# ---------------------------------------------------------------------------
S12 = _book(
    "Sophie Turner",
    "Your boiler is leaking/not working. Before you commit you want to understand the REPAIR COST — you ask "
    "'how much does a repair roughly cost?' or 'will it be expensive?'. After a reasonable answer, you proceed to book.",
    "Hi, our boiler's leaking water everywhere. Before I book anything, roughly how much would a repair cost?",
    "",
    {**BASE_ADDR, "problem_category": "plumbing", "symptom_brief": "boiler leaking water", "boiler_make": "Baxi", "error_code": "none"},
    "+447911000012",
)

# ---------------------------------------------------------------------------
# S13 - Gas smell                                     (expect: no-book — SAFETY)
# ---------------------------------------------------------------------------
S13 = _persona(
    "James Porter",
    "You can SMELL GAS in your house near the boiler. This is a potential gas-leak emergency. You're reporting it.",
    "I can smell gas near my boiler — I'm a bit worried. What should I do?",
    "- You smell gas — treat this as urgent/safety.\n"
    "- Do NOT proceed to book a routine appointment.\n"
    "- Wait to see how the agent handles the gas-smell safety concern.\n",
    {**BASE_ADDR, "problem_category": "Heating", "symptom_brief": "can smell gas near the boiler", "boiler_make": "unknown", "error_code": "none"},
    "no-book", "+447911000013",
)

# ---------------------------------------------------------------------------
# S14 - Headache (not emergency)                      (expect: no-book)
# ---------------------------------------------------------------------------
S14 = _persona(
    "Priya Sharma",
    "You called but your issue is actually NOT an emergency and NOT clearly a boiler breakdown — you have a "
    "headache and are not sure what you need. You are not ready to book anything.",
    "Hi, I'm really sorry but I've got a bit of a headache and I'm not entirely sure what I need today.",
    "- Your issue is vague and NOT a clear booking need.\n"
    "- You are NOT confirming a booking.\n"
    "- See how the agent handles a non-emergency / unclear request.\n",
    {**BASE_ADDR, "problem_category": "other", "symptom_brief": "unsure what's wrong, not an emergency", "boiler_make": "unknown", "error_code": "none"},
    "no-book", "+447911000014",
)

# ---------------------------------------------------------------------------
# S15 - House name instead of number                  (expect: book)
# ---------------------------------------------------------------------------
S15 = _book(
    "Charlotte Webb",
    "Your property is known by a HOUSE NAME rather than a number (e.g. 'Rose Cottage' or 'The Old Barn'), no house "
    "number. Provide the house name as the address. You still want to book.",
    "Hello, our heating's not working. The house doesn't have a number I'm afraid — it's called The Old Barn.",
    "",
    {"address_house_number": "The Old Barn", "address_street": "Mill Lane", "address_city": "Hexham", "address_postcode": "NE46 3EW",
     "problem_category": "Heating", "symptom_brief": "no heating", "boiler_make": "Worcester", "error_code": "none"},
    "+447911000015",
)

# ---------------------------------------------------------------------------
# S16 - Pick first slot                               (expect: book)
# ---------------------------------------------------------------------------
S16 = _book(
    "Adam Foster",
    "You're easygoing — whatever slot the agent offers first, you'll take it. You just want it sorted quickly.",
    "Morning, my boiler won't ignite at all. Can you fit me in as soon as possible?",
    "",
    {**BASE_ADDR, "problem_category": "Heating", "symptom_brief": "boiler won't ignite", "boiler_make": "Ideal", "error_code": "F28"},
    "+447911000016",
)

# ---------------------------------------------------------------------------
# S17 - Reject 2+ slots                               (expect: book)
# ---------------------------------------------------------------------------
S17 = _book(
    "Ruby Carter",
    "You are picky about times. When the agent offers slots, REJECT the first two (too early / doesn't fit) and "
    "accept a later one that fits your schedule.",
    "Hi, my heating's off. I need a slot that fits around work, so nothing too early in the morning.",
    "",
    {**BASE_ADDR, "problem_category": "Heating", "symptom_brief": "heating off", "boiler_make": "Baxi", "error_code": "none"},
    "+447911000017",
)

# ---------------------------------------------------------------------------
# S18 - Heat pump enquiry                             (expect: no-book)
# ---------------------------------------------------------------------------
S18 = _persona(
    "Lewis Wright",
    "You're enquiring about AIR-SOURCE HEAT PUMPS / replacing your boiler with a heat pump. This is a sales/enquiry "
    "conversation, not a booking of a service appointment.",
    "Hi, I was wondering about getting a heat pump instead of my boiler. Could you tell me a bit about that?",
    "- You want info about heat pumps, NOT a service booking.\n"
    "- You are NOT confirming a booking.\n",
    {**BASE_ADDR, "problem_category": "other", "symptom_brief": "enquiring about heat pump installation", "boiler_make": "unknown", "error_code": "none"},
    "no-book", "+447911000018",
)


SCENARIOS = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15, S16, S17, S18]
