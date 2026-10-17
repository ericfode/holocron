//! The current table bot's c-clock resourcing rule (not a learned policy).
use crate::features::{arr, f, s, you, CardTables};
use serde_json::Value;

pub fn my_aspects(msg: &Value, t: &CardTables) -> Vec<String> {
    let me = &msg["state"]["players"][you(msg)];
    ["leader", "base"]
        .iter()
        .filter_map(|k| t.meta.get(s(&me[k], "s")))
        .flat_map(|m| m.aspects.clone())
        .collect()
}
pub fn off_aspect(code: &str, t: &CardTables, aspects: &[String]) -> usize {
    let mut have = aspects.to_vec();
    let mut off = 0;
    if let Some(m) = t.meta.get(code) {
        for a in &m.aspects {
            if let Some(k) = have.iter().position(|x| x == a) {
                have.remove(k);
            } else {
                off += 1;
            }
        }
    }
    off
}
pub fn max_select(prompt: &Value) -> usize {
    // JS takes the last run of ASCII decimal digits in the prompt title.
    let title = s(prompt, "title");
    let mut last = None;
    let mut n = 0_usize;
    let mut active = false;
    for b in title.bytes() {
        if b.is_ascii_digit() {
            n = if active {
                n.saturating_mul(10).saturating_add((b - b'0') as usize)
            } else {
                (b - b'0') as usize
            };
            active = true;
        } else if active {
            last = Some(n);
            active = false;
        }
    }
    if active {
        last = Some(n);
    }
    last.unwrap_or(1)
}
pub fn clock_keep(code: &str, t: &CardTables, aspects: &[String], total: f64) -> f64 {
    let Some(m) = t.meta.get(code) else {
        return 1.0;
    };
    let pen = 2.0 * off_aspect(code, t, aspects) as f64;
    let mut v = 3.0 - 0.6 * (m.cost + pen - (total + 2.0)).max(0.0) - (0.8 * pen) / 2.0;
    if m.types.iter().any(|x| x == "unit") {
        v += 1.0 + 0.05 * (m.power + m.hp);
    }
    if m.types.iter().any(|x| x == "upgrade") {
        v -= 0.3;
    }
    v
}
pub fn choose_clock(msg: &Value, t: &CardTables) -> Option<usize> {
    let prompt = &msg["prompt"];
    if s(prompt, "type") != "resource" {
        return None;
    }
    let you = you(msg);
    let mut cards = Vec::new();
    let mut done = None;
    for a in arr(msg, "actions") {
        let c = &a["card"];
        let id = a["i"].as_u64().map(|i| i as usize);
        if s(a, "kind") == "card"
            && s(c, "zone") == "hand"
            && s(c, "ctl") == you
            && !s(c, "s").is_empty()
        {
            if let Some(id) = id {
                cards.push((id, s(c, "s")));
            }
        } else if s(a, "kind") == "button" {
            done = id;
        }
    }
    let me = &msg["state"]["players"][you];
    let total = f(&me["res"], "total");
    let hand = f(me, "handCount");
    let aspects = my_aspects(msg, t);
    let mut want = max_select(prompt);
    if s(&msg["state"], "phase") == "regroup" {
        let big = arr(me, "hand").iter().any(|c| {
            !s(c, "s").is_empty()
                && t.meta.get(s(c, "s")).map_or(3.0, |m| {
                    m.cost + 2.0 * off_aspect(s(c, "s"), t, &aspects) as f64
                }) > total
        });
        if !(total < 6.0 || (total < 9.0 && hand >= 3.0) || (big && hand >= 2.0)) {
            want = 0;
        }
    }
    if arr(prompt, "selected").len() >= want && done.is_some() {
        return done;
    }
    let mut best = None;
    let mut score = f64::INFINITY;
    for (id, code) in cards {
        let v = clock_keep(code, t, &aspects, total);
        if best.is_none() || v < score {
            best = Some(id);
            score = v;
        }
    }
    best.or(done)
}
