# Existing runtime-admitted activated programs

Inventory only: no native actions or training executed.

| Card | Source | Printed source | Cost | Target | Effect | Native token dependency |
| --- | --- | --- | --- | --- | --- | --- |
| ASH_011 | leader/0 | ground 4/7; underworld,bounty hunter | exhaustSelf | any/unit/anyAttackable/* + exact predicate | damage 1 -> chosen | none |
| HMW_170 | card/0 | ground 4/7; rebel,official | exhaustSelf | any/unit/anyAttackable/* + exact predicate | ready -> chosen | none |
| IBH_016 | card/0 | ground 0/5; weapon | exhaustSelf | any/any/arena/space | damage 3 -> chosen | none |
| IBH_053 | leader/0 | ground 3/8; force,imperial,sith | resources:1, exhaustSelf | any/any/base/* | damage 1 -> chosen | none |
| LOF_004 | leader/0 | ground 3/6; force,jedi,rebel,spectre | resources:1, exhaustSelf | any/any/anyAttackable/* + exact predicate | giveShield 1 -> chosen | TOKEN_SHIELD |
| LOF_134 | card/0 | space 4/3; separatist,droid,vehicle,transport | exhaustSelf | any/unit/arena/ground | damage 2 -> chosen | none |
| SHD_196 | card/0 | ground 0/5; force | exhaustSelf | opponent/any/arena/* | exhaust -> chosen | none |
| SOR_007 | leader/0 | ground 2/7; imperial,official | resources:1, exhaustSelf | any/any/anyAttackable/* + exact predicate | giveExperience 1 -> chosen | TOKEN_EXPERIENCE |
| SOR_011 | leader/0 | ground 3/6; force,imperial,inquisitor | exhaustSelf | self/unit/anyAttackable/* + exact predicate | sequence[damage 2 -> chosen; ready -> chosen] | none |
| SOR_094 | card/0 | ground 1/2; rebel,official | exhaustSelf | self/any/anyAttackable/* + exact predicate | giveExperience 1 -> chosen | TOKEN_EXPERIENCE |
| TWI_056 | card/0 | ground 0/4; republic,official | exhaustSelf, resources:2 | any/any/anyAttackable/* | heal 2 -> chosen | none |
| TWI_157 | card/0 | ground 0/4; separatist,official | resources:2, exhaustSelf | any/base/anyAttackable/* | damage 2 -> chosen | none |

Whole catalog: 41 actions, 40 cards, 41 normalized program groups.

Exact costs, predicates, ordered effects, additional keys, all-side ability counts, aliases and source/data hashes are preserved in inventory.json.
