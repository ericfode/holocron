use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

pub const STATE_DIM: usize = 73;
pub const ACTION_DIM: usize = 62;
pub const TOKEN_DIM: usize = 21;
pub const MAX_TOKENS: usize = 32;
const PROMPTS: [&str; 10] = [
    "actionWindow",
    "resource",
    "initiative",
    "triggerWindow",
    "optionalTrigger",
    "distributeAmongTargets",
    "displayCards",
    "number",
    "mulligan",
    "other",
];
const KINDS: [&str; 6] = [
    "button",
    "card",
    "option",
    "displayCard",
    "perCardButton",
    "distribute",
];
const BUTTONS: [&str; 12] = [
    "pass", "cancel", "done", "keep", "mulligan", "0", "1", "yes", "no", "claim", "skip", "other",
];
const ZONES: [&str; 8] = [
    "hand",
    "groundArena",
    "spaceArena",
    "base",
    "discard",
    "resource",
    "leader",
    "other",
];
const KEYWORDS: [&str; 10] = [
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

pub fn arr<'a>(v: &'a Value, k: &str) -> &'a [Value] {
    v[k].as_array().map(Vec::as_slice).unwrap_or(&[])
}
pub fn f(v: &Value, k: &str) -> f64 {
    v[k].as_f64().unwrap_or(0.0)
}
pub fn s<'a>(v: &'a Value, k: &str) -> &'a str {
    v[k].as_str().unwrap_or("")
}
pub fn bit(b: bool) -> f64 {
    if b {
        1.0
    } else {
        0.0
    }
}
pub fn you(msg: &Value) -> &str {
    let y = s(msg, "you");
    if y.is_empty() {
        "p1"
    } else {
        y
    }
}
pub fn opponent(you: &str) -> &str {
    if you == "p1" {
        "p2"
    } else {
        "p1"
    }
}
pub fn truthy(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::Number(n) => n.as_f64().is_some_and(|x| x != 0.0),
        Value::String(s) => !s.is_empty(),
        _ => true,
    }
}
pub fn py_truthy(v: &Value) -> bool {
    match v {
        Value::Array(a) => !a.is_empty(),
        Value::Object(o) => !o.is_empty(),
        _ => truthy(v),
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CardInfo {
    pub cost: f64,
    pub power: f64,
    pub hp: f64,
    pub unit: bool,
    pub event: bool,
    pub upgrade: bool,
    pub leader: bool,
    pub base: bool,
    pub token: bool,
    pub space: bool,
    pub keywords: u16,
}
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CardMeta {
    pub cost: f64,
    pub power: f64,
    pub hp: f64,
    pub types: Vec<String>,
    pub aspects: Vec<String>,
    pub space: bool,
}
#[derive(Debug, Clone, Default)]
pub struct CardTables {
    pub db: HashMap<String, CardInfo>,
    pub meta: HashMap<String, CardMeta>,
}
fn strings(v: &Value, k: &str) -> Vec<String> {
    arr(v, k)
        .iter()
        .filter_map(Value::as_str)
        .map(str::to_lowercase)
        .collect()
}
impl CardTables {
    pub fn from_cards(cards: &Value) -> Self {
        let mut out = Self::default();
        for v in cards.as_array().map(Vec::as_slice).unwrap_or(&[]) {
            if !v.is_object() {
                continue;
            }
            let types = strings(v, "types");
            let kws = strings(v, "keywords");
            let has = |t: &str| types.iter().any(|x| x.contains(t));
            let mut i = CardInfo {
                cost: f(v, "cost"),
                power: f(v, "power"),
                hp: f(v, "hp"),
                unit: has("unit"),
                event: has("event"),
                upgrade: has("upgrade"),
                leader: has("leader"),
                base: has("base"),
                token: has("token"),
                space: s(v, "arena") == "space",
                keywords: 0,
            };
            for (b, k) in KEYWORDS.iter().enumerate() {
                if kws.iter().any(|x| x == k) {
                    i.keywords |= 1 << b;
                }
            }
            if i.upgrade && i.power == 0.0 {
                i.power = f(v, "upgradePower");
                i.hp = f(v, "upgradeHp");
            }
            let m = CardMeta {
                cost: f(v, "cost"),
                power: f(v, "power"),
                hp: f(v, "hp"),
                types,
                aspects: strings(v, "aspects"),
                space: s(v, "arena") == "space",
            };
            let mut codes = arr(v, "setCodes").to_vec();
            if truthy(&v["setId"]) {
                codes.push(v["setId"].clone());
            }
            for c in codes {
                if let (Some(set), Some(n)) = (c["set"].as_str(), c["number"].as_f64()) {
                    if n.fract() == 0.0 && n.is_finite() {
                        let text = js_number(n);
                        let code = format!("{set}_{text:0>3}");
                        out.db.insert(code.clone(), i.clone());
                        out.meta.insert(code, m.clone());
                    }
                }
            }
        }
        out
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Actions {
    pub rows: Vec<f32>,
    pub ids: Vec<i32>,
    pub n: usize,
}
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Tokens {
    pub ids: Vec<i32>,
    pub feats: Vec<f32>,
    pub n: usize,
}
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Encoded {
    pub state: Vec<f32>,
    pub actions: Actions,
    pub tokens: Tokens,
}

pub fn hash_id(text: &str) -> i32 {
    let mut h = 0x84222325_u32;
    for b in text.as_bytes() {
        h = (h ^ u32::from(*b)).wrapping_mul(0x1b3);
    }
    (h % 2048) as i32
}

fn side_features(side: &Value, out: &mut Vec<f64>) {
    let base = &side["base"];
    let hp = f(base, "hp").max(1.0);
    let left = (f(base, "hp") - f(base, "d")).max(0.0);
    let mut hp_left = 0.0;
    let mut exhausted = 0.0;
    let mut ready_power = 0.0;
    let mut sentinels = 0.0;
    let mut shields = 0.0;
    let mut ups = 0.0;
    for u in arr(side, "ground").iter().chain(arr(side, "space")) {
        hp_left += (f(u, "h") - f(u, "d")).max(0.0);
        if f(u, "x") > 0.0 {
            exhausted += 1.0;
        } else {
            ready_power += f(u, "p");
        }
        sentinels += f(u, "sn");
        for up in arr(u, "u") {
            if up.is_object() && s(up, "n") == "Shield" {
                shields += 1.0;
            } else {
                ups += 1.0;
            }
        }
    }
    let res = &side["res"];
    let leader = &side["leader"];
    let power = |z| arr(side, z).iter().fold(0.0, |total, u| total + f(u, "p"));
    out.extend([
        left / 30.0,
        left / hp,
        bit(left <= 10.0),
        f(res, "ready") / 10.0,
        f(res, "total") / 10.0,
        f(side, "handCount") / 10.0,
        f(side, "deck") / 50.0,
        arr(side, "discard").len() as f64 / 30.0,
        arr(side, "ground").len() as f64 / 6.0,
        arr(side, "space").len() as f64 / 6.0,
        power("ground") / 20.0,
        power("space") / 20.0,
        hp_left / 30.0,
        exhausted / 6.0,
        ready_power / 20.0,
        sentinels / 3.0,
        shields / 3.0,
        ups / 3.0,
        f(leader, "dep"),
        f(leader, "x"),
    ]);
}

pub fn encode_state(msg: &Value, t: &CardTables) -> Vec<f32> {
    let you = you(msg);
    let opp = opponent(you);
    let state = &msg["state"];
    let me = &state["players"][you];
    let them = &state["players"][opp];
    let prompt = &msg["prompt"];
    let mut out = Vec::with_capacity(STATE_DIM);
    side_features(me, &mut out);
    side_features(them, &mut out);
    let ready = f(&me["res"], "ready");
    let mut cost = 0.0;
    let mut units = 0.0;
    let mut events = 0.0;
    let mut upgrades = 0.0;
    let mut playable = 0.0;
    let mut power = 0.0;
    let mut min_cost = 99.0_f64;
    let hand = arr(me, "hand");
    for c in hand {
        if let Some(i) = t.db.get(s(c, "s")) {
            cost += i.cost;
            units += bit(i.unit);
            events += bit(i.event);
            upgrades += bit(i.upgrade);
            playable += bit(i.cost <= ready);
            min_cost = min_cost.min(i.cost);
            power += i.power;
        }
    }
    out.extend([
        cost / 30.0,
        units / 5.0,
        events / 5.0,
        upgrades / 5.0,
        playable / 5.0,
        if hand.is_empty() {
            1.0
        } else {
            min_cost.min(10.0) / 10.0
        },
        power / 20.0,
        hand.len() as f64 / 10.0,
    ]);
    out.push(f(state, "round") / 20.0);
    for phase in ["setup", "action", "regroup"] {
        out.push(bit(s(state, "phase") == phase));
    }
    out.extend([
        bit(s(state, "initiative") == you),
        bit(s(state, "initiative") == opp),
        bit(state["initiative"].is_null()),
    ]);
    let pt = if s(prompt, "title").to_lowercase().contains("mulligan") {
        8
    } else {
        PROMPTS
            .iter()
            .position(|p| *p == s(prompt, "type"))
            .unwrap_or(9)
    };
    for k in 0..PROMPTS.len() {
        out.push(bit(k == pt));
    }
    out.push(bit(prompt["actionWindow"] == Value::Bool(true)));
    out.extend([
        bit(s(prompt, "selectCardMode") == "single"),
        bit(s(prompt, "selectCardMode") == "multiple"),
        bit(prompt["selectCardMode"].is_null()),
    ]);
    out.push(arr(prompt, "selected").len() as f64 / 5.0);
    out.push(arr(msg, "actions").len().min(30) as f64 / 30.0);
    out.push(out[0] - out[20]);
    out.push(out[12] - out[32] + out[10] + out[11] - out[30] - out[31]);
    assert_eq!(out.len(), STATE_DIM);
    out.into_iter().map(|x| x as f32).collect()
}

/// ECMAScript's decimal/exponent thresholds, using Rust's shortest round-trip significant digits.
pub fn js_number(n: f64) -> String {
    if n == 0.0 {
        return "0".into();
    }
    if !n.is_finite() {
        return if n.is_nan() {
            "nan"
        } else if n > 0.0 {
            "inf"
        } else {
            "-inf"
        }
        .into();
    }
    let sign = if n < 0.0 { "-" } else { "" };
    let text = n.abs().to_string();
    let (mant, exp) = text
        .split_once(['e', 'E'])
        .map(|(a, b)| (a, b.parse::<i32>().unwrap()))
        .unwrap_or((&text, 0));
    let decimal = mant.find('.').unwrap_or(mant.len()) as i32 + exp;
    let mut digits = mant.replace('.', "");
    let leading = digits.bytes().take_while(|b| *b == b'0').count();
    digits.drain(..leading);
    let decimal = decimal - leading as i32;
    while digits.len() > 1 && digits.ends_with('0') {
        digits.pop();
    }
    if n.abs() >= 1e21 || n.abs() < 1e-6 {
        let e = decimal - 1;
        let mut body = digits[..1].to_string();
        if digits.len() > 1 {
            body.push('.');
            body.push_str(&digits[1..]);
        }
        format!("{sign}{body}e{}{e}", if e >= 0 { "+" } else { "" })
    } else if decimal <= 0 {
        format!("{sign}0.{}{digits}", "0".repeat((-decimal) as usize))
    } else if decimal as usize >= digits.len() {
        format!(
            "{sign}{digits}{}",
            "0".repeat(decimal as usize - digits.len())
        )
    } else {
        format!(
            "{sign}{}.{}",
            &digits[..decimal as usize],
            &digits[decimal as usize..]
        )
    }
}
pub fn arg_text(v: &Value) -> String {
    match v {
        Value::String(x) => x.to_lowercase(),
        Value::Number(x) => js_number(x.as_f64().unwrap_or(0.0)),
        _ => String::new(),
    }
}
pub fn py_float(t: &str) -> Option<f64> {
    let bytes = t.trim().as_bytes();
    let mut clean = String::new();
    for (i, b) in bytes.iter().enumerate() {
        if *b == b'_'
            && i > 0
            && i + 1 < bytes.len()
            && bytes[i - 1].is_ascii_digit()
            && bytes[i + 1].is_ascii_digit()
        {
            continue;
        }
        clean.push(*b as char);
    }
    let lower = clean.to_lowercase();
    if matches!(lower.as_str(), "inf" | "+inf" | "infinity" | "+infinity") {
        return Some(f64::INFINITY);
    }
    if matches!(lower.as_str(), "-inf" | "-infinity") {
        return Some(f64::NEG_INFINITY);
    }
    if matches!(lower.as_str(), "nan" | "+nan" | "-nan") {
        return Some(f64::NAN);
    }
    if clean.is_empty()
        || !clean
            .bytes()
            .all(|b| b.is_ascii_digit() || b"+-.eE".contains(&b))
    {
        return None;
    }
    clean.parse::<f64>().ok()
}

pub fn encode_actions(msg: &Value, t: &CardTables) -> Actions {
    let you = you(msg);
    let opp = opponent(you);
    let me = &msg["state"]["players"][you];
    let them = &msg["state"]["players"][opp];
    let ready = f(&me["res"], "ready");
    let mut board = HashMap::new();
    for (side, mine) in [(me, true), (them, false)] {
        for u in arr(side, "ground").iter().chain(arr(side, "space")) {
            if let Some(id) = u["id"].as_str() {
                board.insert(id, (u, mine));
            }
        }
    }
    let acts = arr(msg, "actions");
    let mut rows = Vec::with_capacity(acts.len() * ACTION_DIM);
    let mut ids = Vec::with_capacity(acts.len());
    for a in acts {
        let mut r = [0.0_f64; ACTION_DIM];
        let mut o = 0;
        let kind = s(a, "kind");
        if let Some(k) = KINDS.iter().position(|x| *x == kind) {
            r[o + k] = 1.0;
        }
        o += KINDS.len();
        let label = s(a, "label").to_lowercase();
        let arg = arg_text(&a["arg"]);
        if kind == "button" || kind == "perCardButton" {
            let b = BUTTONS
                .iter()
                .position(|bt| {
                    arg == *bt || label == *bt || (bt.len() > 2 && label.starts_with(bt))
                })
                .unwrap_or(BUTTONS.len() - 1);
            r[o + b] = 1.0;
        }
        o += BUTTONS.len();
        let card = a["card"].as_object().map(|_| &a["card"]);
        if let Some(c) = card {
            let z = ZONES.iter().position(|z| *z == s(c, "zone")).unwrap_or(7);
            r[o + z] = 1.0;
        }
        o += ZONES.len();
        if let Some(c) = card {
            r[o] = bit(s(c, "ctl") == you);
            r[o + 1] = bit(s(c, "ctl") == opp);
        }
        o += 2;
        if let Some(i) = card.and_then(|c| t.db.get(s(c, "s"))) {
            r[o..o + 11].copy_from_slice(&[
                i.cost / 10.0,
                i.power / 10.0,
                i.hp / 10.0,
                bit(i.unit),
                bit(i.event),
                bit(i.upgrade),
                bit(i.leader),
                bit(i.base),
                bit(i.token),
                bit(i.space),
                bit(i.cost <= ready),
            ]);
            for b in 0..10 {
                r[o + 11 + b] = f64::from((i.keywords >> b) & 1);
            }
        }
        o += 21;
        let cid = card
            .and_then(|c| c["id"].as_str())
            .or_else(|| a["cardUuid"].as_str());
        if let Some((u, mine)) = cid.and_then(|id| board.get(id)) {
            r[o..o + 7].copy_from_slice(&[
                1.0,
                bit(*mine),
                f(u, "p") / 10.0,
                (f(u, "h") - f(u, "d")).max(0.0) / 10.0,
                f(u, "x"),
                f(u, "sn"),
                arr(u, "u").len() as f64 / 3.0,
            ]);
        }
        o += 7;
        if a["distribute"].is_object() {
            r[o] = f(&a["distribute"], "amount") / 10.0;
            r[o + 1] = arr(&a["distribute"], "targets").len() as f64 / 10.0;
        }
        if kind == "option" {
            if let Some(x) = py_float(&arg) {
                r[o + 2] = x / 10.0;
            }
        }
        r[o + 3] = bit(s(&msg["prompt"], "selectCardMode") == "multiple" && kind == "card");
        o += 4;
        r[o] = bit(cid.is_some() && cid == them["base"]["id"].as_str());
        r[o + 1] = bit(cid.is_some() && cid == me["base"]["id"].as_str());
        let key = if let Some(code) = card.and_then(|c| c["s"].as_str()) {
            format!("card:{code}")
        } else {
            format!("{kind}:{}", if arg.is_empty() { &label } else { &arg })
        };
        ids.push(hash_id(&key));
        rows.extend(r.into_iter().map(|x| x as f32));
    }
    Actions {
        rows,
        ids,
        n: acts.len(),
    }
}

pub fn encode_tokens(msg: &Value, t: &CardTables) -> Tokens {
    let you = you(msg);
    let me = &msg["state"]["players"][you];
    let them = &msg["state"]["players"][opponent(you)];
    let ready = f(&me["res"], "ready");
    let mut items = vec![
        (5, &me["leader"]),
        (6, &them["leader"]),
        (7, &me["base"]),
        (8, &them["base"]),
    ];
    for (slot, cards) in [
        (1, arr(me, "ground")),
        (2, arr(me, "space")),
        (3, arr(them, "ground")),
        (4, arr(them, "space")),
        (0, arr(me, "hand")),
    ] {
        for c in cards {
            items.push((slot, c));
        }
    }
    let used: Vec<_> = items
        .into_iter()
        .filter(|(_, c)| c.is_object())
        .take(MAX_TOKENS)
        .collect();
    let mut ids = Vec::with_capacity(used.len());
    let mut feats = Vec::with_capacity(used.len() * TOKEN_DIM);
    for (slot, c) in &used {
        let code = s(c, "s");
        let i = t.db.get(code);
        ids.push(hash_id(&format!("card:{code}")));
        let mut row = [0.0_f64; TOKEN_DIM];
        row[*slot] = 1.0;
        let hp = if c.get("h").is_some() {
            f(c, "h")
        } else {
            f(c, "hp")
        };
        row[9..].copy_from_slice(&[
            f(c, "p") / 10.0,
            (hp - f(c, "d")).max(0.0) / 10.0,
            f(c, "x"),
            f(c, "sn"),
            arr(c, "u").len() as f64 / 3.0,
            f(c, "dep"),
            i.map_or(0.0, |i| i.cost / 10.0),
            i.map_or(0.0, |i| bit(i.unit)),
            i.map_or(0.0, |i| bit(i.event)),
            i.map_or(0.0, |i| bit(i.upgrade)),
            i.map_or(0.0, |i| bit(i.cost <= ready)),
            i.map_or(0.0, |i| bit(i.space)),
        ]);
        feats.extend(row.into_iter().map(|x| x as f32));
    }
    Tokens {
        ids,
        feats,
        n: used.len(),
    }
}

pub fn encode(msg: &Value, t: &CardTables) -> Encoded {
    Encoded {
        state: encode_state(msg, t),
        actions: encode_actions(msg, t),
        tokens: encode_tokens(msg, t),
    }
}
