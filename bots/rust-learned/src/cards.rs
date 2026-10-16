//! Printed card stats by set code ("SOR_042"), from the engine's card JSON (one object per card). In play the table
//! comes from each game's `hello` (`cards`: both decks and the tokens); the offline commands (train, explain, ...)
//! read the card folder (forceteki/test/json/Card).

use serde_json::Value;
use std::collections::HashMap;
use std::path::Path;

#[derive(Clone, Debug, Default)]
pub struct CardInfo {
    pub cost: f32,
    pub power: f32,
    pub hp: f32,
    pub unit: bool,
    pub event: bool,
    pub upgrade: bool,
    pub leader: bool,
    pub base: bool,
    pub token: bool,
    pub space: bool,
    pub keywords: u32,
}

#[derive(Default)]
pub struct CardDb {
    by_code: HashMap<String, CardInfo>,
}

impl CardDb {
    /// Reads every card file in `dir` (the `Card/` folder or its parent). Missing data gives an empty table:
    /// the model still plays, it just loses the printed-stat features.
    pub fn load(dir: &Path) -> CardDb {
        let dir = if dir.join("Card").is_dir() { dir.join("Card") } else { dir.to_path_buf() };
        let mut db = CardDb::default();
        let Ok(entries) = std::fs::read_dir(&dir) else {
            eprintln!("swu-learned: no card data at {}", dir.display());
            return db;
        };
        for e in entries.flatten() {
            let Ok(text) = std::fs::read_to_string(e.path()) else { continue };
            let Ok(v) = serde_json::from_str::<Value>(&text) else { continue };
            db.add(&v);
        }
        eprintln!("swu-learned: {} card codes from {}", db.by_code.len(), dir.display());
        db
    }

    /// From card JSON objects (hello's `cards`); anything but a card object adds nothing.
    pub fn from_values<'a>(cards: impl IntoIterator<Item = &'a Value>) -> CardDb {
        let mut db = CardDb::default();
        for v in cards {
            if v.is_object() {
                db.add(v);
            }
        }
        db
    }

    /// One card: its stats under every set code it is printed with.
    fn add(&mut self, v: &Value) {
        let num = |k: &str| v.get(k).and_then(|x| x.as_f64()).unwrap_or(0.0) as f32;
        let strs = |k: &str| -> Vec<String> {
            v.get(k)
                .and_then(|x| x.as_array())
                .map(|a| a.iter().filter_map(|s| s.as_str().map(str::to_lowercase)).collect())
                .unwrap_or_default()
        };
        let types = strs("types");
        let kws = strs("keywords");
        let has = |t: &str| types.iter().any(|x| x.contains(t));
        let mut info = CardInfo {
            cost: num("cost"),
            power: num("power"),
            hp: num("hp"),
            unit: has("unit"),
            event: has("event"),
            upgrade: has("upgrade"),
            leader: has("leader"),
            base: has("base"),
            token: has("token"),
            space: v.get("arena").and_then(|a| a.as_str()) == Some("space"),
            keywords: 0,
        };
        for (bit, k) in KEYWORDS.iter().enumerate() {
            if kws.iter().any(|x| x == k) {
                info.keywords |= 1 << bit;
            }
        }
        if info.upgrade && info.power == 0.0 {
            info.power = num("upgradePower");
            info.hp = num("upgradeHp");
        }
        let codes = v.get("setCodes").and_then(|x| x.as_array()).cloned().unwrap_or_default();
        let mut all = codes;
        if let Some(id) = v.get("setId") {
            all.push(id.clone());
        }
        for c in all {
            let (Some(set), Some(n)) = (c.get("set").and_then(|s| s.as_str()), c.get("number").and_then(|n| n.as_u64())) else {
                continue;
            };
            self.by_code.insert(format!("{set}_{n:03}"), info.clone());
        }
    }

    pub fn get(&self, code: Option<&str>) -> Option<&CardInfo> {
        code.and_then(|c| self.by_code.get(c))
    }

    pub fn len(&self) -> usize {
        self.by_code.len()
    }
}

/// Keywords that get their own feature bit.
pub const KEYWORDS: [&str; 10] =
    ["sentinel", "overwhelm", "raid", "restore", "saboteur", "shielded", "ambush", "grit", "bounty", "smuggle"];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn from_values_reads_cards_like_the_files() {
        let cards: Vec<Value> = serde_json::from_str(
            r#"[{"title":"Wampa","cost":4,"power":4,"hp":5,"types":["unit"],"keywords":["Overwhelm"],"arena":"ground",
                 "setId":{"set":"SOR","number":38},"setCodes":[{"set":"SOR","number":38},{"set":"SOR","number":291}]},
                {"title":"Shield","types":["token","upgrade"],"upgradePower":0,"upgradeHp":0,"setId":{"set":"SOR"}}, 7]"#,
        )
        .unwrap();
        let db = CardDb::from_values(&cards);
        assert_eq!(db.len(), 2);
        let w = db.get(Some("SOR_291")).unwrap();
        assert_eq!((w.cost, w.power, w.hp, w.unit, w.space, w.keywords), (4.0, 4.0, 5.0, true, false, 1 << 1));
        // the same codes and stats as reading the engine's card files, when they are here
        let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../forceteki/test/json/Card");
        let Ok(entries) = std::fs::read_dir(&dir) else {
            eprintln!("skipped: no {}", dir.display());
            return;
        };
        let values: Vec<Value> =
            entries.flatten().filter_map(|e| serde_json::from_str(&std::fs::read_to_string(e.path()).ok()?).ok()).collect();
        let files = CardDb::load(&dir);
        let hello = CardDb::from_values(&values);
        assert!(files.len() > 2000);
        assert_eq!(hello.len(), files.len());
        for (code, c) in &files.by_code {
            let h = hello.get(Some(code)).unwrap();
            assert_eq!((h.cost, h.power, h.hp, h.keywords, h.unit, h.upgrade), (c.cost, c.power, c.hp, c.keywords, c.unit, c.upgrade), "{code}");
        }
    }
}
