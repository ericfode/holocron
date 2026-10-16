//! Card data, from the `cards` of a game's `hello`: the engine's card JSON (one object per card, as in
//! `forceteki/test/json/Card/<name>.json`) for both decks and the tokens.
//!
//! The `decide` messages name cards by set code, title and internal name but carry no stats, so a policy that wants
//! costs, aspects or keywords looks them up here. The bot reads no card files. Missing data is not an error: lookups
//! return None and policies fall back to rules.

use serde::Deserialize;
use serde_json::Value;
use std::collections::HashMap;

#[derive(Debug, Deserialize, Default, Clone)]
#[serde(rename_all = "camelCase")]
#[allow(dead_code)] // the full stat line, for policies to come
pub struct CardInfo {
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub internal_name: String,
    #[serde(default)]
    pub cost: Option<i32>,
    #[serde(default)]
    pub power: Option<i32>,
    #[serde(default)]
    pub hp: Option<i32>,
    #[serde(default)]
    pub upgrade_power: Option<i32>,
    #[serde(default)]
    pub upgrade_hp: Option<i32>,
    #[serde(default)]
    pub text: Option<String>,
    #[serde(default)]
    pub deploy_box: Option<String>,
    #[serde(default)]
    pub epic_action: Option<String>,
    #[serde(default)]
    pub unique: bool,
    #[serde(default)]
    pub arena: Option<String>,
    #[serde(default)]
    aspects: Option<Vec<String>>,
    #[serde(default)]
    keywords: Option<Vec<String>>,
    #[serde(default)]
    types: Option<Vec<String>>,
    #[serde(default)]
    set_id: Option<SetId>,
    /// Every printing (alternate art, reprints), `set_id` among them.
    #[serde(default)]
    set_codes: Option<Vec<SetId>>,
}

#[derive(Debug, Deserialize, Default, Clone)]
struct SetId {
    #[serde(default)]
    set: String,
    #[serde(default)]
    number: Option<u32>,
}

impl CardInfo {
    pub fn aspects(&self) -> &[String] {
        self.aspects.as_deref().unwrap_or(&[])
    }

    pub fn has_keyword(&self, k: &str) -> bool {
        self.keywords.as_deref().unwrap_or(&[]).iter().any(|x| x == k)
    }

    pub fn is(&self, t: &str) -> bool {
        self.types.as_deref().unwrap_or(&[]).iter().any(|x| x == t)
    }

    pub fn cost(&self) -> i32 {
        self.cost.unwrap_or(0)
    }

    pub fn text_lower(&self) -> String {
        self.text.as_deref().unwrap_or("").to_lowercase()
    }
}

#[derive(Default)]
pub struct CardDb {
    by_name: HashMap<String, CardInfo>,
    /// "SOR_010" -> internal name
    by_set: HashMap<String, String>,
    /// title -> internal name (first one wins; titles repeat across versions of a character)
    by_title: HashMap<String, String>,
}

impl CardDb {
    /// From card JSON objects (hello's `cards`), in their order; one that does not parse as a card is skipped, so one odd
    /// card costs only itself.
    pub fn from_values<'a>(cards: impl IntoIterator<Item = &'a Value>) -> CardDb {
        let mut db = CardDb::default();
        for v in cards {
            if let Ok(card) = CardInfo::deserialize(v) {
                db.insert(card);
            }
        }
        db
    }

    pub fn insert(&mut self, card: CardInfo) {
        let code = |s: &SetId| s.number.filter(|_| !s.set.is_empty()).map(|n| format!("{}_{:03}", s.set, n));
        if let Some(c) = card.set_id.as_ref().and_then(code) {
            self.by_set.insert(c, card.internal_name.clone());
        }
        // other printings never take a code that is some card's own set_id
        for c in card.set_codes.iter().flatten().filter_map(code) {
            self.by_set.entry(c).or_insert_with(|| card.internal_name.clone());
        }
        self.by_title.entry(card.title.clone()).or_insert_with(|| card.internal_name.clone());
        self.by_name.insert(card.internal_name.clone(), card);
    }

    pub fn len(&self) -> usize {
        self.by_name.len()
    }

    pub fn by_name(&self, internal_name: &str) -> Option<&CardInfo> {
        self.by_name.get(internal_name)
    }

    pub fn by_set_code(&self, code: &str) -> Option<&CardInfo> {
        self.by_set.get(code).and_then(|n| self.by_name.get(n))
    }

    pub fn by_title(&self, title: &str) -> Option<&CardInfo> {
        self.by_title.get(title).and_then(|n| self.by_name.get(n))
    }

    /// Best effort: action label (internal name), then set code, then title.
    pub fn find(&self, label: Option<&str>, set_code: Option<&str>, title: Option<&str>) -> Option<&CardInfo> {
        label
            .and_then(|l| self.by_name(l))
            .or_else(|| set_code.and_then(|s| self.by_set_code(s)))
            .or_else(|| title.and_then(|t| self.by_title(t)))
    }
}

#[cfg(test)]
pub fn test_card(name: &str, json: &str) -> CardInfo {
    let mut c: CardInfo = serde_json::from_str(json).unwrap();
    c.internal_name = name.into();
    c
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    #[test]
    fn finds_a_card_by_any_printing() {
        let mut db = CardDb::default();
        db.insert(test_card(
            "tauntaun-mount",
            r#"{"title":"Tauntaun Mount","setId":{"set":"IBH","number":15},
                "setCodes":[{"set":"IBH","number":15},{"set":"IBH","number":28},{"set":"SOR","number":7}]}"#,
        ));
        // SOR_007 is another card's own number: its set_id wins whatever the load order
        db.insert(test_card("other", r#"{"title":"Other","setId":{"set":"SOR","number":7}}"#));
        assert_eq!(db.by_set_code("IBH_028").map(|c| c.title.as_str()), Some("Tauntaun Mount"));
        assert_eq!(db.by_set_code("IBH_015").map(|c| c.title.as_str()), Some("Tauntaun Mount"));
        assert_eq!(db.by_set_code("SOR_007").map(|c| c.title.as_str()), Some("Other"));
    }

    #[test]
    fn from_values_skips_what_does_not_parse() {
        let cards: Vec<Value> = serde_json::from_str(
            r#"[{"title":"Tauntaun Mount","internalName":"tauntaun-mount","setId":{"set":"IBH","number":15},
                 "setCodes":[{"set":"IBH","number":15},{"set":"IBH","number":28}]},
                {"title":"Broken","internalName":"broken","unique":null}, 7, "wampa",
                {"title":"Shield","internalName":"shield","setId":{"set":"SOR"},"types":["token","upgrade"]}]"#,
        )
        .unwrap();
        let db = CardDb::from_values(&cards);
        assert_eq!(db.len(), 2);
        assert_eq!(db.by_set_code("IBH_028").map(|c| c.internal_name.as_str()), Some("tauntaun-mount"));
        assert_eq!(db.find(None, None, Some("Shield")).map(|c| c.internal_name.as_str()), Some("shield"));
        assert!(db.by_name("broken").is_none());
    }

    /// Every card file of the engine's card data (`$SWU_CARD_JSON` or forceteki/test/json at the repo root), sorted by
    /// name; None when there is none.
    fn card_files() -> Option<Vec<String>> {
        let dir = std::env::var_os("SWU_CARD_JSON")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| Path::new(env!("CARGO_MANIFEST_DIR")).join("../../forceteki/test/json"))
            .join("Card");
        let mut paths: Vec<_> = std::fs::read_dir(dir).ok()?.flatten().map(|e| e.path()).collect();
        paths.sort();
        Some(paths.iter().filter_map(|p| std::fs::read_to_string(p).ok()).collect())
    }

    #[test]
    fn from_values_looks_up_like_the_card_files() {
        let Some(texts) = card_files() else {
            eprintln!("skipped: no forceteki/test/json (npm run get-cards in forceteki)");
            return;
        };
        // the files as the bot used to read them, card by card, and the same cards as hello's JSON values
        let mut files = CardDb::default();
        for t in &texts {
            if let Ok(card) = serde_json::from_str::<CardInfo>(t) {
                files.insert(card);
            }
        }
        let values: Vec<Value> = texts.iter().filter_map(|t| serde_json::from_str(t).ok()).collect();
        let db = CardDb::from_values(&values);
        assert!(files.len() > 2000, "{} cards", files.len());
        assert_eq!(db.len(), files.len());
        let name = |c: Option<&CardInfo>| c.map(|c| (c.internal_name.clone(), c.title.clone(), c.cost, c.power, c.hp, c.text.clone()));
        for (n, c) in &files.by_name {
            assert_eq!(name(db.by_name(n)), name(Some(c)));
            assert_eq!(db.by_name(n).map(|d| (d.aspects().to_vec(), d.is("unit"), d.has_keyword("sentinel"))), Some((c.aspects().to_vec(), c.is("unit"), c.has_keyword("sentinel"))));
        }
        assert_eq!(db.by_set.len(), files.by_set.len());
        for code in files.by_set.keys() {
            assert_eq!(name(db.by_set_code(code)), name(files.by_set_code(code)), "{code}");
        }
        for title in files.by_title.keys() {
            assert_eq!(name(db.by_title(title)), name(files.by_title(title)), "{title}");
        }
    }
}
