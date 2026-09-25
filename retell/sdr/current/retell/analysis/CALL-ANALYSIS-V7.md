# V7.0 CALL-ANALYSIS-SOP REPORT
Agent: agent_66df480ff8f240ee9e919d3b53 / llm_97474e866ccc2c89586c8f120ea2
Framework: docs/Testing_guidelines/CALL-ANALYSIS-SOP.md (all 8 categories)

## Test [0]: 0: (GK) Sam — scam-skeptic contractor — BOOKED 8PuBLbUYCXUTSXRV3oZGy5

### State Transitions
Intake → Discovery: ✅
Discovery → Closer: ✅
Closer → Offer: ✅
Offer → contact_details: ✅
contact_details → ConfirmSlots: ✅
ConfirmSlots → Booking: ✅
Booking → Closing: ✅

### Booking
create_livecall_booking: ✅ (uid: 8PuBLbUYCXUTSXRV3oZGy5)
validate_lead gate: true | end_call: ✅

### 1. Prompt Following
- Intake: ✅ required tools fired in order
- Discovery: ✅ required tools fired in order
- Closer: ✅ required tools fired in order
- Offer: ✅ required tools fired in order
- contact_details: ✅ required tools fired in order
- ConfirmSlots: ✅ required tools fired in order
- Booking: ✅ required tools fired in order
- Closing: ✅ required tools fired in order
- Filler-before-tool pattern observed: 1×

### 2. Nonsense/Hallucination
- JSON/tool leakage: 0
- Jay-callback offers (should be ZERO in V7): 0
- KB/playbook bleed into speech: 0

### 3. Redundancy
- Identical tool+args repeats: 3 [('extract_discovery_details', ''), ('extract_person_details', '')]
- Near-duplicate agent turns: 0

### 4. Repetition
- Sentences said >2×: none

### 5. Bugs
- Empty-string args passed: none
- dv slot_verified final: true | weekly/monthly leak: $21,000/$93,000
- tz enum violation: none

### 6. Tool Call Analysis
- Total invocations: 35 | validate_lead: 1× | unique: 30
- Order canonical: ✅

### 7. Conversation Flow
- Turns w/ stacked questions: 0/14 | user turns: 13

### 8. Logs & Metrics
Turns: 13 | Cost: 19.7¢ | Agent msgs: 14 | Tool calls: 35 | Transitions: 7

## Test [1]: 1: (GK) Priya — price-obsessed shopper — BOOKED 3miuGgFGu1EiZGVpWoSt5B

### State Transitions
Intake → Discovery: ✅
Discovery → Closer: ✅
Closer → Offer: ✅
Offer → contact_details: ✅
contact_details → ConfirmSlots: ✅
ConfirmSlots → Booking: ✅
Booking → Closing: ✅

### Booking
create_livecall_booking: ✅ (uid: 3miuGgFGu1EiZGVpWoSt5B)
validate_lead gate: true | end_call: ✅

### 1. Prompt Following
- Intake: ✅ required tools fired in order
- Discovery: ✅ required tools fired in order
- Closer: ✅ required tools fired in order
- Offer: ✅ required tools fired in order
- contact_details: ✅ required tools fired in order
- ConfirmSlots: ✅ required tools fired in order
- Booking: ✅ required tools fired in order
- Closing: ✅ required tools fired in order
- Filler-before-tool pattern observed: 1×

### 2. Nonsense/Hallucination
- JSON/tool leakage: 0
- Jay-callback offers (should be ZERO in V7): 0
- KB/playbook bleed into speech: 0

### 3. Redundancy
- Identical tool+args repeats: 1 [('extract_person_details', '')]
- Near-duplicate agent turns: 0

### 4. Repetition
- Sentences said >2×: none

### 5. Bugs
- Empty-string args passed: none
- dv slot_verified final: true | weekly/monthly leak: $2,100/$9,100
- tz enum violation: none

### 6. Tool Call Analysis
- Total invocations: 32 | validate_lead: 1× | unique: 30
- Order canonical: ✅

### 7. Conversation Flow
- Turns w/ stacked questions: 0/13 | user turns: 12

### 8. Logs & Metrics
Turns: 12 | Cost: 18.4¢ | Agent msgs: 13 | Tool calls: 32 | Transitions: 7

## Test [2]: 2: (GK) Boris — perpetually busy — BOOKED fyRe1zCxmVXozt3Re7aPse

### State Transitions
Intake → Discovery: ✅
Discovery → Closer: ✅
Closer → Offer: ✅
Offer → contact_details: ✅
contact_details → ConfirmSlots: ✅
ConfirmSlots → Booking: ✅

### Booking
create_livecall_booking: ✅ (uid: fyRe1zCxmVXozt3Re7aPse)
validate_lead gate: true | end_call: ✅

### 1. Prompt Following
- Intake: ✅ required tools fired in order
- Discovery: ✅ required tools fired in order
- Closer: ✅ required tools fired in order
- Offer: ✅ required tools fired in order
- contact_details: ✅ required tools fired in order
- ConfirmSlots: ✅ required tools fired in order
- Booking: ✅ required tools fired in order
- Filler-before-tool pattern observed: 2×

### 2. Nonsense/Hallucination
- JSON/tool leakage: 0
- Jay-callback offers (should be ZERO in V7): 0
- KB/playbook bleed into speech: 0

### 3. Redundancy
- Identical tool+args repeats: 7 [('extract_discovery_details', ''), ('extract_person_details', '')]
- Near-duplicate agent turns: 1

### 4. Repetition
- Sentences said >2×: none

### 5. Bugs
- Empty-string args passed: none
- dv slot_verified final: true | weekly/monthly leak: $10,000/$43,000
- tz enum violation: none

### 6. Tool Call Analysis
- Total invocations: 40 | validate_lead: 1× | unique: 29
- Order canonical: ✅

### 7. Conversation Flow
- Turns w/ stacked questions: 0/12 | user turns: 10

### 8. Logs & Metrics
Turns: 10 | Cost: 17.1¢ | Agent msgs: 12 | Tool calls: 40 | Transitions: 6

## Test [3]: 3: (GK) Bianca — burned-before — BOOKED vxVHfhnVRe9kgZZpsDPuWC

### State Transitions
Intake → Discovery: ✅
Discovery → Closer: ✅
Closer → Offer: ✅
Offer → contact_details: ✅
contact_details → ConfirmSlots: ✅
ConfirmSlots → Booking: ✅
Booking → Closing: ✅

### Booking
create_livecall_booking: ✅ (uid: vxVHfhnVRe9kgZZpsDPuWC)
validate_lead gate: true | end_call: ✅

### 1. Prompt Following
- Intake: ✅ required tools fired in order
- Discovery: ✅ required tools fired in order
- Closer: ✅ n/a (no required tools)
- Offer: ✅ required tools fired in order
- contact_details: ✅ n/a (no required tools)
- ConfirmSlots: ✅ required tools fired in order
- Booking: ✅ required tools fired in order
- Closing: ✅ required tools fired in order
- Filler-before-tool pattern observed: 1×

### 2. Nonsense/Hallucination
- JSON/tool leakage: 0
- Jay-callback offers (should be ZERO in V7): 0
- KB/playbook bleed into speech: 0

### 3. Redundancy
- Identical tool+args repeats: 6 [('extract_discovery_details', ''), ('extract_closer_details', '')]
- Near-duplicate agent turns: 0

### 4. Repetition
- Sentences said >2×: none

### 5. Bugs
- Empty-string args passed: none
- dv slot_verified final: true | weekly/monthly leak: $2,500/$11,000
- tz enum violation: none

### 6. Tool Call Analysis
- Total invocations: 41 | validate_lead: 1× | unique: 30
- Order canonical: ✅

### 7. Conversation Flow
- Turns w/ stacked questions: 0/20 | user turns: 19

### 8. Logs & Metrics
Turns: 19 | Cost: 27.5¢ | Agent msgs: 20 | Tool calls: 41 | Transitions: 7

## Test [4]: 4: (GK) Dave — status-quo defender — BOOKED 5HcfTqCNy3sNHGGixTFEDx

### State Transitions
Intake → Discovery: ✅
Discovery → Closer: ✅
Closer → Offer: ✅
Offer → contact_details: ✅
contact_details → ConfirmSlots: ✅
ConfirmSlots → Booking: ✅
Booking → Closing: ✅

### Booking
create_livecall_booking: ✅ (uid: 5HcfTqCNy3sNHGGixTFEDx)
validate_lead gate: true | end_call: ✅

### 1. Prompt Following
- Intake: ✅ required tools fired in order
- Discovery: ✅ required tools fired in order
- Closer: ✅ required tools fired in order
- Offer: ✅ required tools fired in order
- contact_details: ✅ required tools fired in order
- ConfirmSlots: ✅ required tools fired in order
- Booking: ✅ required tools fired in order
- Closing: ✅ required tools fired in order
- Filler-before-tool pattern observed: 2×

### 2. Nonsense/Hallucination
- JSON/tool leakage: 0
- Jay-callback offers (should be ZERO in V7): 0
- KB/playbook bleed into speech: 0

### 3. Redundancy
- Identical tool+args repeats: 4 [('extract_discovery_details', ''), ('extract_leak_inputs', '')]
- Near-duplicate agent turns: 0

### 4. Repetition
- Sentences said >2×: none

### 5. Bugs
- Empty-string args passed: none
- dv slot_verified final: true | weekly/monthly leak: $8,200/$35,000
- tz enum violation: none

### 6. Tool Call Analysis
- Total invocations: 39 | validate_lead: 1× | unique: 30
- Order canonical: ✅

### 7. Conversation Flow
- Turns w/ stacked questions: 0/19 | user turns: 17

### 8. Logs & Metrics
Turns: 17 | Cost: 26.2¢ | Agent msgs: 19 | Tool calls: 39 | Transitions: 7

## Test [6]: 6: (BRK) Jamie — prompt-injection brat — NO-BOOK

### State Transitions
Intake → Discovery: ✅
Discovery → Closer: ✅
Closer → Offer: ✅

### Booking
create_livecall_booking: — (uid: none)
validate_lead gate: None | end_call: ✅

### 1. Prompt Following
- Intake: ✅ required tools fired in order
- Discovery: ✅ required tools fired in order
- Closer: ⚠️ partial: missing ['extract_leak_inputs', 'calculate_monthly_leak']
- Offer: ⚠️ partial: missing ['extract_offer_details', 'offer_completed']
- Filler-before-tool pattern observed: 0×

### 2. Nonsense/Hallucination
- JSON/tool leakage: 0
- Jay-callback offers (should be ZERO in V7): 0
- KB/playbook bleed into speech: 0

### 3. Redundancy
- Identical tool+args repeats: 1 [('extract_discovery_details', '')]
- Near-duplicate agent turns: 0

### 4. Repetition
- Sentences said >2×: none

### 5. Bugs
- Empty-string args passed: none
- dv slot_verified final: None | weekly/monthly leak: None/
- tz enum violation: none

### 6. Tool Call Analysis
- Total invocations: 12 | validate_lead: 0× | unique: 10
- Order canonical: ✅

### 7. Conversation Flow
- Turns w/ stacked questions: 0/17 | user turns: 17

### 8. Logs & Metrics
Turns: 17 | Cost: 23.6¢ | Agent msgs: 17 | Tool calls: 12 | Transitions: 3

## Test [7]: 7: (BRK) Rita — tangent rambler — NO-BOOK

### State Transitions
(no transitions — early exit)

### Booking
create_livecall_booking: — (uid: none)
validate_lead gate: None | end_call: ✅

### 1. Prompt Following
- Intake: ⚠️ partial: missing ['extract_intake_details', 'intake_completed']
- Filler-before-tool pattern observed: 0×

### 2. Nonsense/Hallucination
- JSON/tool leakage: 0
- Jay-callback offers (should be ZERO in V7): 0
- KB/playbook bleed into speech: 0

### 3. Redundancy
- Identical tool+args repeats: 0
- Near-duplicate agent turns: 0

### 4. Repetition
- Sentences said >2×: none

### 5. Bugs
- Empty-string args passed: none
- dv slot_verified final: None | weekly/monthly leak: None/None
- tz enum violation: none

### 6. Tool Call Analysis
- Total invocations: 1 | validate_lead: 0× | unique: 1
- Order canonical: ✅

### 7. Conversation Flow
- Turns w/ stacked questions: 0/11 | user turns: 11

### 8. Logs & Metrics
Turns: 11 | Cost: 15.8¢ | Agent msgs: 11 | Tool calls: 1 | Transitions: 0

## Test [8]: 8: (BRK) Nick — contradiction machine — BOOKED cEmzkcgrWNyv4nsiq9BVYX

### State Transitions
Intake → Discovery: ✅
Discovery → Closer: ✅
Closer → Offer: ✅
Offer → contact_details: ✅
contact_details → ConfirmSlots: ✅
ConfirmSlots → Booking: ✅
Booking → Closing: ✅

### Booking
create_livecall_booking: ✅ (uid: cEmzkcgrWNyv4nsiq9BVYX)
validate_lead gate: true | end_call: ✅

### 1. Prompt Following
- Intake: ✅ required tools fired in order
- Discovery: ✅ required tools fired in order
- Closer: ✅ required tools fired in order
- Offer: ✅ required tools fired in order
- contact_details: ✅ n/a (no required tools)
- ConfirmSlots: ✅ required tools fired in order
- Booking: ✅ required tools fired in order
- Closing: ✅ required tools fired in order
- Filler-before-tool pattern observed: 1×

### 2. Nonsense/Hallucination
- JSON/tool leakage: 0
- Jay-callback offers (should be ZERO in V7): 0
- KB/playbook bleed into speech: 0

### 3. Redundancy
- Identical tool+args repeats: 5 [('extract_discovery_details', ''), ('extract_leak_inputs', '')]
- Near-duplicate agent turns: 0

### 4. Repetition
- Sentences said >2×: none

### 5. Bugs
- Empty-string args passed: none
- dv slot_verified final: true | weekly/monthly leak: $250,000/$1,000,000
- tz enum violation: none

### 6. Tool Call Analysis
- Total invocations: 41 | validate_lead: 1× | unique: 30
- Order canonical: ✅

### 7. Conversation Flow
- Turns w/ stacked questions: 0/21 | user turns: 19

### 8. Logs & Metrics
Turns: 19 | Cost: 28.8¢ | Agent msgs: 21 | Tool calls: 41 | Transitions: 7

## Test [9]: 9: (BRK) Suzy — monosyllable wall — NO-BOOK

### State Transitions
(no transitions — early exit)

### Booking
create_livecall_booking: — (uid: none)
validate_lead gate: None | end_call: ✅

### 1. Prompt Following
- Intake: ⚠️ partial: missing ['extract_intake_details', 'intake_completed']
- Filler-before-tool pattern observed: 0×

### 2. Nonsense/Hallucination
- JSON/tool leakage: 0
- Jay-callback offers (should be ZERO in V7): 0
- KB/playbook bleed into speech: 0

### 3. Redundancy
- Identical tool+args repeats: 0
- Near-duplicate agent turns: 0

### 4. Repetition
- Sentences said >2×: none

### 5. Bugs
- Empty-string args passed: none
- dv slot_verified final: None | weekly/monthly leak: None/None
- tz enum violation: none

### 6. Tool Call Analysis
- Total invocations: 1 | validate_lead: 0× | unique: 1
- Order canonical: ✅

### 7. Conversation Flow
- Turns w/ stacked questions: 0/5 | user turns: 5

### 8. Logs & Metrics
Turns: 5 | Cost: 8¢ | Agent msgs: 5 | Tool calls: 1 | Transitions: 0

## Test [10]: 10: (BRK) Alan — mid-call explosion — NO-BOOK

### State Transitions
(no transitions — early exit)

### Booking
create_livecall_booking: — (uid: none)
validate_lead gate: None | end_call: ✅

### 1. Prompt Following
- Intake: ⚠️ partial: missing ['extract_intake_details', 'intake_completed']
- Filler-before-tool pattern observed: 0×

### 2. Nonsense/Hallucination
- JSON/tool leakage: 0
- Jay-callback offers (should be ZERO in V7): 0
- KB/playbook bleed into speech: 0

### 3. Redundancy
- Identical tool+args repeats: 0
- Near-duplicate agent turns: 0

### 4. Repetition
- Sentences said >2×: none

### 5. Bugs
- Empty-string args passed: none
- dv slot_verified final: None | weekly/monthly leak: None/None
- tz enum violation: none

### 6. Tool Call Analysis
- Total invocations: 1 | validate_lead: 0× | unique: 1
- Order canonical: ✅

### 7. Conversation Flow
- Turns w/ stacked questions: 0/3 | user turns: 3

### 8. Logs & Metrics
Turns: 3 | Cost: 5.4¢ | Agent msgs: 3 | Tool calls: 1 | Transitions: 0

## Test [11]: 11: (BRK) Wendy — agreement waffler — BOOKED ktKg6oYfeDG33whQwK4ch5

### State Transitions
Intake → Discovery: ✅
Discovery → Closer: ✅
Closer → Offer: ✅
Offer → contact_details: ✅
contact_details → ConfirmSlots: ✅
ConfirmSlots → Booking: ✅
Booking → Closing: ✅

### Booking
create_livecall_booking: ✅ (uid: ktKg6oYfeDG33whQwK4ch5)
validate_lead gate: true | end_call: ✅

### 1. Prompt Following
- Intake: ✅ required tools fired in order
- Discovery: ✅ required tools fired in order
- Closer: ✅ required tools fired in order
- Offer: ✅ required tools fired in order
- contact_details: ✅ required tools fired in order
- ConfirmSlots: ✅ required tools fired in order
- Booking: ✅ required tools fired in order
- Closing: ✅ required tools fired in order
- Filler-before-tool pattern observed: 1×

### 2. Nonsense/Hallucination
- JSON/tool leakage: 0
- Jay-callback offers (should be ZERO in V7): 0
- KB/playbook bleed into speech: 0

### 3. Redundancy
- Identical tool+args repeats: 3 [('extract_discovery_details', ''), ('extract_leak_inputs', '')]
- Near-duplicate agent turns: 0

### 4. Repetition
- Sentences said >2×: none

### 5. Bugs
- Empty-string args passed: none
- dv slot_verified final: true | weekly/monthly leak: $7,500/$32,000
- tz enum violation: none

### 6. Tool Call Analysis
- Total invocations: 37 | validate_lead: 1× | unique: 30
- Order canonical: ✅

### 7. Conversation Flow
- Turns w/ stacked questions: 0/17 | user turns: 16

### 8. Logs & Metrics
Turns: 16 | Cost: 23.6¢ | Agent msgs: 17 | Tool calls: 37 | Transitions: 7
