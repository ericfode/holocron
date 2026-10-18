# Real-IR adapter coverage

The explicit adapter serializes **152/1,178 runtime-admitted whole rows** in the
pinned Kessel snapshot. In the saved 27-deck main-card corpus, it covers **9/251
identities and 47/1,432 copies**. These are input-contract coverage results.
They do not establish native game conformance, learned prediction transfer, or
useful card/deck vectors. At this coverage closure, the report records no
native-verified or learned-vector identities and keeps `semantic_validated=false`.
Saved provenance/count verification replays the same adapter; representative
fixtures and native-source peer review check the represented grammar.

The snapshot is Kessel `c7ee39554901278cee70f61fd8b26fb1920696b3`: 2,458
catalogue rows, of which 1,178 are runtime-admitted. Catalogue SHA256 is
`0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812`;
runtime-admission SHA256 is
`91553fdcd7862ebe473bfbbddaf4f17fdf37c2fc7fad7319bf2686d82122a957`.
This is the same snapshot used by the [previous strict admission audit](COMPOSITIONAL_ACTUAL_ADMISSION_RESULTS.md).

That frozen candidate rejected every whole row. Its six first-rejection
categories were:

| First rejection | Catalogue | Admitted | Boundary |
|---|---:|---:|---|
| One main event program required | 842 | 487 | Empty profiles, other sides and multiple programs did not fit the event-only form. |
| Unreviewed typed field | 659 | 199 | Extra ability/selector/effect fields could not be discarded. |
| Event without extra costs required | 727 | 389 | Other triggers or additional ability costs were outside its grammar. |
| Missing explicit arena | 111 | 61 | Native selectors may have no arena restriction; ground cannot be imputed. |
| Missing target resolver | 118 | 41 | Self, composed or other targeting forms cannot acquire an invented chosen resolver. |
| Missing cost predicate | 1 | 1 | No predicate means no cost cap, rather than an invented cap2/3. |

These partitions report the first failure only. The new adapter fully represents
140 rows from the first category, five from the trigger/cost category and seven
from the missing-arena category. All remaining rows still fail the complete-row
support gate. This is a declared grammar extension, not evidence that relaxing
one old check makes an arbitrary card supported.

The [adapter](real_ir_adapter.py) preserves the complete raw row, its canonical
whole-row hash, all ability sides, printed metadata and provenance. Null printed
HP/power remain unknown, never numeric zero. Canonical programs retain trigger,
owner, target kind, zone, arena, optionality, literal amount and a separate
cost-cap presence/value pair. Native defaults are explicit. Keywords, unknown
capabilities/fields, attachment conditions, continuations and other unrepresented
rules produce JSON-path markers and prevent `full_card_supported=true`.
`profile_serialized` and `program_adapter_supported` are weaker, separate flags.
The exact program key retains amount/cap/trigger; it is not a holdout-family key.

The [17 selected fixtures](real_ir_adapter_fixtures.json) include the seven simple
events, three complete `whenPlayed` units and three plain units, plus multi-side,
conditional, simultaneous and attachment rejections. Twelve focused tests also
check defaults, unknown capabilities, impossible selector overlaps, strict
booleans and immutable raw rows. Healthy healing targets remain eligible at an
opened native target prompt; the adapter does not invent outcome labels.

| Fully represented form | Admitted rows | Corpus identities | Corpus copies |
|---|---:|---:|---:|
| Keywordless plain unit/base profile | 140 | 8 | 46 |
| One chosen constant `whenPlayed` damage/heal program | 5 | 1 | 1 |
| One chosen constant event damage/heal program | 7 | 0 | 0 |
| Total | 152 | 9 | 47 |

The eight plain corpus identities are ASH201, JTL095, JTL212, LAW175, LOF093,
LOF192, SEC028 and SEC080. The sole covered `whenPlayed` corpus identity is
ASH081. The other **1,385 copies remain outside full support**. Profile-only or
partially serialized programs do not increase these whole-card totals.

The separate prelabel reservation selects TRAIN IBH013/066 (unit healing),
IBH061/TWI174 (unit damage) and IBH059 (base damage). Held JTL075/SOR074 and
TWI170/SHD178 are alias-grouped unit-or-base healing/damage events. All seven
have **zero main-card copies in these 27 decks**. The two operator-specific held
templates share one held selector form; they are not broad family evidence.
The entire catalogue was already parser-inspected. The saved reservation also
discloses prior trigger-agnostic selector/operator exposure, including ASH081
healing. Numeric-abstracted full-program reservations therefore do not imply new
primitives or wholly unexposed healing mechanics.

Coverage froze source commit `c44be0871cad71e5026e75e7a5f2fcac4f5b5733`.
V1 stopped before initialization on a printing-alias preflight check and charged
zero. V2 failed before outcomes on a synthetic-inventory assertion and retains
its full **10-second** charge. The separately linked V3 coverage and verification
completed, charging **1.873552499921061 seconds**. Combined new charged time is
**11.873552499921061 seconds**, within the shared 20-second ceiling. At coverage
closure, carry is **807 charged native applications /279.90387191576883 charged
seconds /unknown historical observed native count**. No failures were credited
or reset. These coverage stages added zero native calls, neural forwards,
backwards, updates, numerical fits, paid jobs or recorded spend. The saved
$100 ceiling/$25 reserve persists; this is not an account-wide billing claim.

Subsequent native verification covers the seven selected event sources and their
fixture helpers, not all 152 adapted definitions. Prediction-transfer results
belong in the separate [prediction-transfer report](REAL_IR_TRANSFER_RESULTS.md), with its
own native labels, controls, gates and accounting. This report makes no transfer
or production-integration claim.

Saved evidence is under task7 `experiments/real-ir-coverage-v1/`, `v2/` and `v3/`:

- V3 coverage report: `6bdc20c620d0079717f31754e3f67f14e65e5423f35b5f3ea99d1bfaf41bab3d`.
- Holdout reservation: `d46bb580b0b1884d6988875eb20038bd405f91f2995821e8c717da2aa05f8486`.
- Saved provenance/count verification: `188627f0057196376ee0024e1ebeb9b0151c4ad4b5b3fc191299c10fe7d07e28`.
- V3 closure: `1093798e8076060c2d9390c6c580f087b5e8befaa15f5bb7c0125b68f8acc5ff`.
- Adapter source: `9ac935090a518786d5f88c58311ef3339bb51388b28a3a895aa49c41dd25bec2`.
