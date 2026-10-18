//! Own-list-only, order-independent deck context. This module never reads a live
//! observation, an opponent list, an instance ID, or a draw-order field.
use crate::features::hash_id;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};

pub const VERSION: u32 = 1;
pub const ROWS: usize = 2;
pub const METADATA_DIM: usize = 50;
pub const IDENTITY_DIM: usize = 64 + 32 + 61;
pub const ROW_DIM: usize = METADATA_DIM + IDENTITY_DIM;
pub const KEYWORDS: [&str; 10] = [
    "sentinel",
    "overwhelm",
    "raid",
    "restore",
    "saboteur",
    "shielded",
    "ambush",
    "grit",
    "bounty",
    "smuggle",
];
pub const ASPECTS: [&str; 6] = [
    "vigilance",
    "command",
    "aggression",
    "cunning",
    "heroism",
    "villainy",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum OwnDeckVariant {
    Neutral,
    Original,
    /// The legacy constructor leaves row 1 unknown; opt-in RemainingLedger can
    /// provide provenance-gated counts without changing the original row.
    OriginalPlusRemaining,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OwnDeckContext {
    pub version: u32,
    pub variant: OwnDeckVariant,
    /// Two row-major rows, each [50 metadata coordinates, 64/32/61 identity factors].
    pub features: Vec<f32>,
}

#[derive(Debug, Clone, PartialEq)]
struct Metadata {
    cost: f64,
    power: f64,
    hp: f64,
    types: Vec<String>,
    aspects: Vec<String>,
    keywords: Vec<String>,
    traits: Vec<String>,
    space: bool,
}

fn normalized_list(v: &Value, name: &str, unique: bool) -> Option<Vec<String>> {
    let mut out = v
        .get(name)?
        .as_array()?
        .iter()
        .map(|x| {
            let s = x.as_str()?.trim().to_lowercase();
            (!s.is_empty()).then_some(s)
        })
        .collect::<Option<Vec<_>>>()?;
    out.sort();
    if unique {
        out.dedup();
    }
    Some(out)
}

fn number(v: &Value, name: &str) -> Option<f64> {
    v.get(name)?
        .as_f64()
        .filter(|n| n.is_finite() && n.abs() <= f32::MAX as f64 / 128.0)
}

impl Metadata {
    fn read(v: &Value) -> Option<Self> {
        let types = normalized_list(v, "types", true)?;
        if types.is_empty()
            || types.iter().any(|t| {
                ["leader", "base", "token"]
                    .iter()
                    .any(|kind| t.contains(kind))
            })
        {
            return None;
        }
        let cost = number(v, "cost").filter(|n| *n >= 0.0)?;
        let unit = types.iter().any(|t| t.contains("unit"));
        let optional_stat = |name| match v.get(name) {
            Some(_) => number(v, name),
            None if !unit => Some(0.0),
            _ => None,
        };
        let mut power = optional_stat("power")?;
        let mut hp = optional_stat("hp")?;
        if types.iter().any(|t| t.contains("upgrade")) && power == 0.0 {
            power = if v.get("upgradePower").is_some() {
                number(v, "upgradePower")?
            } else {
                0.0
            };
            hp = if v.get("upgradeHp").is_some() {
                number(v, "upgradeHp")?
            } else {
                0.0
            };
        }
        Some(Self {
            cost,
            power,
            hp,
            types,
            aspects: normalized_list(v, "aspects", false)?,
            keywords: normalized_list(v, "keywords", true)?,
            traits: normalized_list(v, "traits", true)?,
            space: v.get("arena").and_then(Value::as_str) == Some("space"),
        })
    }
}

/// Normalize a printed set code, never an instance ID or a deck position.
pub fn normalize_code(code: &str) -> Option<String> {
    let code = code.trim().to_ascii_uppercase();
    let (set, digits) = code.split_once('_')?;
    if set.is_empty()
        || !set.bytes().all(|c| c.is_ascii_alphanumeric())
        || digits.is_empty()
        || !digits.bytes().all(|c| c.is_ascii_digit())
    {
        return None;
    }
    let digits = digits.trim_start_matches('0');
    let digits = if digits.is_empty() { "0" } else { digits };
    Some(format!("{set}_{digits:0>3}"))
}

fn set_code(v: &Value) -> Option<String> {
    let set = v.get("set")?.as_str()?;
    let n = v.get("number")?.as_u64()?;
    normalize_code(&format!("{set}_{n}"))
}

fn cards_lookup(cards: &Value) -> BTreeMap<String, (String, Option<Metadata>)> {
    let mut records: BTreeMap<String, Option<Metadata>> = BTreeMap::new();
    let mut aliases: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for card in cards.as_array().map(Vec::as_slice).unwrap_or(&[]) {
        let mut codes: BTreeSet<String> = card
            .get("setCodes")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .filter_map(set_code)
            .collect();
        let preferred = card.get("setId").and_then(set_code);
        if let Some(code) = &preferred {
            codes.insert(code.clone());
        }
        let Some(canonical) = preferred.or_else(|| codes.first().cloned()) else {
            continue;
        };
        let metadata = Metadata::read(card);
        records
            .entry(canonical.clone())
            .and_modify(|old| {
                if *old != metadata {
                    *old = None;
                }
            })
            .or_insert(metadata);
        for code in codes {
            aliases.entry(code).or_default().insert(canonical.clone());
        }
    }
    aliases
        .into_iter()
        .map(|(alias, names)| {
            if names.len() == 1 {
                let name = names.into_iter().next().unwrap();
                let metadata = records.get(&name).cloned().flatten();
                (alias, (name, metadata))
            } else {
                // An ambiguous alias retains only its normalized identity, with unknown metadata.
                (alias.clone(), (alias, None))
            }
        })
        .collect()
}

impl OwnDeckContext {
    pub fn neutral() -> Self {
        let mut features = vec![0.0; ROWS * ROW_DIM];
        features[0] = 1.0;
        features[ROW_DIM + 1] = 1.0;
        Self {
            version: VERSION,
            variant: OwnDeckVariant::Neutral,
            features,
        }
    }

    /// Read only an own SWUDB list and the public printed-card catalog. Callers
    /// must pass hello.deck, never the complete hello or simulator snapshot.
    pub fn from_original(variant: OwnDeckVariant, deck: &Value, cards: &Value) -> Self {
        let mut out = Self::neutral();
        out.variant = variant;
        if variant == OwnDeckVariant::Neutral {
            return out;
        }
        out.features[2] = 1.0;
        if variant == OwnDeckVariant::OriginalPlusRemaining {
            // Explicitly enabled but unknown. This is not a valid depletion ablation.
            out.features[ROW_DIM + 2] = 1.0;
        }
        let lookup = cards_lookup(cards);
        let mut entries: BTreeMap<String, (u128, Option<Metadata>)> = BTreeMap::new();
        let mut malformed = 0_u64;
        let mut structurally_valid = true;
        let Some(list) = deck.get("deck").and_then(Value::as_array) else {
            out.features[49] = 1.0 / 60.0;
            return out;
        };
        for entry in list {
            let code = entry
                .get("id")
                .and_then(Value::as_str)
                .and_then(normalize_code);
            let count = entry
                .get("count")
                .and_then(Value::as_u64)
                .filter(|n| *n > 0 && *n <= 9_007_199_254_740_991);
            let (Some(code), Some(count)) = (code, count) else {
                malformed += 1;
                structurally_valid = false;
                continue;
            };
            let (canonical, metadata) = lookup.get(&code).cloned().unwrap_or((code, None));
            let old = entries.entry(canonical).or_insert((0, metadata.clone()));
            if old.1 != metadata {
                old.1 = None;
            }
            old.0 += u128::from(count);
        }
        // Invalidate a whole overflowing group after summing, so malformed
        // duplicate entries remain invariant under split/merge and permutation.
        entries.retain(|_, (count, _)| {
            if *count > 9_007_199_254_740_991 {
                malformed += 1;
                structurally_valid = false;
                false
            } else {
                true
            }
        });
        let total: f64 = entries.values().fold(0.0, |sum, (n, _)| sum + *n as f64);
        let unknown: f64 = entries
            .values()
            .filter(|(_, m)| m.is_none())
            .map(|(n, _)| *n as f64)
            .fold(0.0, |sum, count| sum + count);
        let mut row = [0.0_f64; ROW_DIM];
        row[0] = 1.0;
        row[2] = 1.0;
        row[3] = f64::from(structurally_valid && unknown == 0.0);
        row[4] = total / 60.0;
        row[5] = unknown / 60.0;
        row[6] = entries.len() as f64 / 60.0;
        row[7] = if total > 0.0 {
            (total - unknown) / total
        } else {
            f64::from(structurally_valid)
        };
        row[49] = malformed as f64 / 60.0;
        for (code, (count, metadata)) in entries {
            let count = count as f64;
            let id = hash_id(&format!("card:{code}")) as usize;
            row[50 + id % 64] += count / 60.0;
            row[114 + id / 64] += count / 60.0;
            row[146 + (id * 7 + 3) % 61] += count / 60.0;
            let Some(m) = metadata else { continue };
            let weight = count / total;
            row[8] += weight * m.cost / 10.0;
            row[9] += weight * m.power / 10.0;
            row[10] += weight * m.hp / 10.0;
            let has = |kind: &str| m.types.iter().any(|t| t.contains(kind));
            row[11] += weight * f64::from(has("unit"));
            row[12] += weight * f64::from(has("event"));
            row[13] += weight * f64::from(has("upgrade"));
            row[14] += weight * f64::from(has("unit") && !m.space);
            row[15] += weight * f64::from(has("unit") && m.space);
            row[16 + (m.cost.floor() as usize).min(8)] += weight;
            for (i, keyword) in KEYWORDS.iter().enumerate() {
                row[25 + i] += weight * f64::from(m.keywords.iter().any(|s| s == keyword));
            }
            for aspect in m.aspects {
                if let Some(i) = ASPECTS.iter().position(|s| *s == aspect) {
                    row[35 + i] += weight;
                }
            }
            for trait_ in m.traits {
                row[41 + hash_id(&trait_) as usize % 8] += weight;
            }
        }
        out.features[..ROW_DIM].copy_from_slice(&row.map(|v| v as f32));
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn cards() -> Value {
        json!([
            {"setId":{"set":"SOR","number":42},"setCodes":[{"set":"SOR","number":42},{"set":"JTL","number":20}],
             "cost":2,"power":3,"hp":4,"types":["unit"],"arena":"ground","aspects":["command","command"],"keywords":["raid"],"traits":["Rebel","Trooper"]},
            {"setId":{"set":"SOR","number":43},"setCodes":[{"set":"SOR","number":43}],
             "cost":8,"types":["event"],"aspects":["cunning"],"keywords":[],"traits":[]}
        ])
    }

    #[test]
    fn aliases_duplicate_counts_and_permutation_are_identical() {
        let a = json!({"deck":[{"id":" jtl_20 ","count":1},{"id":"SOR_042","count":2},{"id":"SOR_043","count":1}]});
        let b = json!({"deck":[{"id":"SOR_43","count":1},{"id":"SOR_42","count":3}]});
        let x = OwnDeckContext::from_original(OwnDeckVariant::Original, &a, &cards());
        let y = OwnDeckContext::from_original(OwnDeckVariant::Original, &b, &cards());
        assert_eq!(x, y);
        assert_eq!(x.features.len(), 414);
        assert_eq!(x.features[3], 1.0);
        assert_eq!(x.features[4], 4.0 / 60.0);
        assert_eq!(x.features[6], 2.0 / 60.0);
        assert_eq!(x.features[18], 0.75);
        assert_eq!(x.features[24], 0.25);
        assert_eq!(x.features[36], 1.5); // Double command is preserved.
        for (start, len) in [(50, 64), (114, 32), (146, 61)] {
            let sum: f32 = x.features[start..start + len].iter().sum();
            assert!((sum - 4.0 / 60.0).abs() < 1e-7);
        }
    }

    #[test]
    fn overflowing_canonical_groups_are_unknown_in_any_entry_order() {
        let mut entries = vec![
            json!({"id":"SOR_042","count":9_007_199_254_740_991_u64}),
            json!({"id":"JTL_020","count":1}),
            json!({"id":"SOR_043","count":3}),
        ];
        let a = OwnDeckContext::from_original(
            OwnDeckVariant::Original,
            &json!({"deck":entries}),
            &cards(),
        );
        entries.reverse();
        let b = OwnDeckContext::from_original(
            OwnDeckVariant::Original,
            &json!({"deck":entries}),
            &cards(),
        );
        assert_eq!(a, b);
        assert_eq!(
            (a.features[3], a.features[4], a.features[49]),
            (0.0, 3.0 / 60.0, 1.0 / 60.0)
        );
    }

    #[test]
    fn saved_cross_language_contract_vectors_match_bits() {
        let fixture: Value =
            serde_json::from_str(include_str!("../fixtures/own-deck-contract.json")).unwrap();
        for case in fixture["cases"].as_array().unwrap() {
            let variant = serde_json::from_value(case["variant"].clone()).unwrap();
            let context = OwnDeckContext::from_original(
                variant,
                &case["hello"]["deck"],
                &case["hello"]["cards"],
            );
            let bits: Vec<u32> = context.features.iter().map(|x| x.to_bits()).collect();
            let expected: Vec<u32> = serde_json::from_value(case["expected_bits"].clone()).unwrap();
            assert_eq!(bits, expected, "{}", case["name"]);
        }
    }

    #[test]
    fn unknown_metadata_is_explicit_and_missing_differs_from_known_empty() {
        let missing =
            OwnDeckContext::from_original(OwnDeckVariant::Original, &Value::Null, &cards());
        let empty =
            OwnDeckContext::from_original(OwnDeckVariant::Original, &json!({"deck":[]}), &cards());
        assert_eq!(
            (missing.features[3], missing.features[49]),
            (0.0, 1.0 / 60.0)
        );
        assert_eq!(
            (empty.features[3], empty.features[7], empty.features[49]),
            (1.0, 1.0, 0.0)
        );
        let x = OwnDeckContext::from_original(
            OwnDeckVariant::Original,
            &json!({"deck":[{"id":"SOR_999","count":2},{"id":"SOR_042","count":-1}]}),
            &cards(),
        );
        assert_eq!(x.features[3], 0.0);
        assert_eq!(x.features[5], 2.0 / 60.0);
        assert_eq!(x.features[49], 1.0 / 60.0);
        assert!(x.features.iter().all(|n| n.is_finite()));
    }

    #[test]
    fn neutral_and_remaining_unknown_never_derive_depletion() {
        let deck = json!({"deck":[{"id":"SOR_042","count":3}],"opponent":{"deck":[{"id":"SOR_043","count":50}]},"drawOrder":["SOR_043"]});
        let neutral = OwnDeckContext::from_original(OwnDeckVariant::Neutral, &deck, &cards());
        assert_eq!(neutral, OwnDeckContext::neutral());
        let x =
            OwnDeckContext::from_original(OwnDeckVariant::OriginalPlusRemaining, &deck, &cards());
        let rem = &x.features[ROW_DIM..];
        assert_eq!((rem[1], rem[2], rem[3]), (1.0, 1.0, 0.0));
        assert!(rem[4..].iter().all(|n| *n == 0.0));
        let clean = OwnDeckContext::from_original(
            OwnDeckVariant::OriginalPlusRemaining,
            &json!({"deck":[{"id":"SOR_042","count":3}]}),
            &cards(),
        );
        assert_eq!(x, clean);
    }

    #[test]
    fn malformed_metadata_and_ambiguous_aliases_fail_to_unknown() {
        let mut bad = cards();
        bad[0].as_object_mut().unwrap().remove("traits");
        let deck = json!({"deck":[{"id":"SOR_042","count":3}]});
        let x = OwnDeckContext::from_original(OwnDeckVariant::Original, &deck, &bad);
        assert_eq!((x.features[3], x.features[5]), (0.0, 3.0 / 60.0));
        assert!(x.features[8..49].iter().all(|v| *v == 0.0));
        let mut collision = cards();
        collision[1]["setCodes"] = json!([{"set":"SOR","number":42}]);
        let a = OwnDeckContext::from_original(OwnDeckVariant::Original, &deck, &collision);
        collision.as_array_mut().unwrap().reverse();
        let b = OwnDeckContext::from_original(OwnDeckVariant::Original, &deck, &collision);
        assert_eq!(a, b);
        assert_eq!(a.features[3], 0.0);
    }

    #[test]
    fn unsupported_main_types_and_overlarge_stats_are_unknown_and_finite() {
        let deck = json!({"deck":[{"id":"SOR_042","count":3}]});
        for replacement in [
            json!({"cost":1e200}),
            json!({"types":["leader","unit"]}),
            json!({"types":["token","unit"]}),
        ] {
            let mut data = cards();
            for (key, value) in replacement.as_object().unwrap() {
                data[0][key] = value.clone();
            }
            let x = OwnDeckContext::from_original(OwnDeckVariant::Original, &deck, &data);
            assert_eq!(x.features[3], 0.0);
            assert_eq!(x.features[5], 3.0 / 60.0);
            assert!(x.features.iter().all(|n| n.is_finite()));
        }
    }

    #[test]
    fn controller_retains_only_own_list_and_resets_at_hello() {
        use crate::{Config, JepaBot};
        let mut config = Config::default();
        config.own_deck = Some(OwnDeckVariant::OriginalPlusRemaining);
        let mut bot = JepaBot::new(config);
        let hello = json!({"versions":[2],"deck":{"deck":[{"id":"SOR_042","count":3}]},"cards":cards(),
            "opponent":{"deck":[{"id":"SOR_043","count":999}]},"drawOrder":["SOR_043"]});
        bot.hello(&hello);
        let original = bot.own_deck.clone();
        let mut changed = hello.clone();
        changed["opponent"] = json!({"secretHand":["SOR_042"]});
        changed["drawOrder"] = json!(["SOR_042"]);
        changed["state"] = json!({"privateDeck":["SOR_043"]});
        bot.hello(&changed);
        assert_eq!(bot.own_deck, original);
        let crowded = json!({"you":"p1","state":{"players":{"p1":{"ground":vec![json!({"s":"SOR_042"});40]}}}});
        let encoded = bot.encode(&crowded);
        assert_eq!(encoded.tokens.n, 32);
        assert_eq!(encoded.own_deck, original);
        assert_eq!(bot.encode(&json!({"state":{"players":{"p1":{"deck":1,"discard":[{"s":"SOR_042"}],"resources":[{"s":"SOR_042"}]}}}})).own_deck, original);
        bot.hello(&json!({"versions":[2],"cards":cards()}));
        assert_eq!(bot.own_deck.as_ref().unwrap().features[3], 0.0);
        assert_ne!(bot.own_deck, original);
        bot.new_game(0);
        assert!(bot.own_deck.is_none());
        let mut legacy = JepaBot::new(Config::default());
        legacy.hello(&hello);
        let e = legacy.encode(&crowded);
        assert!(e.own_deck.is_none());
        assert!(serde_json::to_value(e).unwrap().get("own_deck").is_none());
    }

    struct ContextAssertingModel {
        expected: OwnDeckContext,
        flat: bool,
        policy_calls: usize,
        leaf_calls: usize,
    }
    impl crate::Model for ContextAssertingModel {
        fn predict_values(
            &mut self,
            _: crate::ModelRole,
            e: &crate::Encoded,
            _: &str,
        ) -> Result<Vec<f64>, String> {
            assert_eq!(e.own_deck.as_ref(), Some(&self.expected));
            self.policy_calls += 1;
            let follow = e.actions.rows.get(1) == Some(&1.0);
            Ok((0..e.actions.n)
                .map(|i| {
                    if self.flat {
                        1.0
                    } else if follow {
                        [2.0, 1.0, 10.0].get(i).copied().unwrap_or(i as f64)
                    } else {
                        i as f64
                    }
                })
                .collect())
        }
        fn context_value(
            &mut self,
            _: crate::ModelRole,
            e: &crate::Encoded,
        ) -> Result<f64, String> {
            assert_eq!(e.own_deck.as_ref(), Some(&self.expected));
            self.leaf_calls += 1;
            Ok(2.0)
        }
    }

    #[test]
    fn policy_followups_and_simulated_leaves_all_receive_frozen_original_context() {
        use crate::{Config, JepaBot};
        let fixtures: Value =
            serde_json::from_str(include_str!("../../tests/fixtures/planning.json")).unwrap();
        let mut leaves = 0;
        for case in fixtures["cases"].as_array().unwrap() {
            let mut config: Config = serde_json::from_value(case["config"].clone()).unwrap();
            config.own_deck = Some(OwnDeckVariant::OriginalPlusRemaining);
            let mut bot = JepaBot::new(config);
            let mut hello = case["hello"].clone();
            hello["deck"] = json!({"deck":[{"id":"SOR_042","count":3}]});
            hello["cards"]
                .as_array_mut()
                .unwrap()
                .extend(cards().as_array().unwrap().clone());
            bot.hello(&hello);
            let mut model = ContextAssertingModel {
                expected: bot.own_deck.clone().unwrap(),
                flat: case["flat"].as_bool().unwrap(),
                policy_calls: 0,
                leaf_calls: 0,
            };
            let transcript = case["transcript"].as_array().unwrap();
            let mut cursor = 0;
            let mut sim = |request: Value| -> Result<Value, String> {
                let row = transcript
                    .get(cursor)
                    .ok_or_else(|| format!("unexpected simulator request {request}"))?;
                assert_eq!(request, row["request"]);
                cursor += 1;
                Ok(row["reply"].clone())
            };
            for (input, expected) in case["inputs"]
                .as_array()
                .unwrap()
                .iter()
                .zip(case["replies"].as_array().unwrap())
            {
                assert_eq!(bot.decide(input, &mut model, &mut sim).unwrap(), *expected);
            }
            assert_eq!(cursor, transcript.len());
            assert!(model.policy_calls > 0);
            leaves += model.leaf_calls;
        }
        assert!(
            leaves > 0,
            "fixture must exercise the simulated-leaf inference path"
        );
    }
}
