//! Protocol v2 and the table's gated, one-action planner, ported from jepa.js.
use crate::clock::PlannerClock;
use crate::features::{arr, encode, js_number, py_truthy, s, truthy, you, CardTables, Encoded};
use crate::own_deck::{OwnDeckContext, OwnDeckVariant};
use crate::{resource, rng::PyRandom};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet, VecDeque};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ModelRole {
    Raw,
    Evaluator,
}

/// Raw logits, not sigmoid values. The backend owns context caching and all tensor computation.
pub trait Model {
    fn predict_values(
        &mut self,
        role: ModelRole,
        encoded: &Encoded,
        horizon: &str,
    ) -> Result<Vec<f64>, String>;
    fn context_value(&mut self, role: ModelRole, encoded: &Encoded) -> Result<f64, String>;
    fn has_horizon(&self, _role: ModelRole, horizon: &str) -> bool {
        matches!(horizon, "1" | "4" | "s")
    }
}
pub trait Simulator {
    fn request(&mut self, request: Value) -> Result<Value, String>;
}
impl<F: FnMut(Value) -> Result<Value, String>> Simulator for F {
    fn request(&mut self, r: Value) -> Result<Value, String> {
        self(r)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct PlanConfig {
    pub roots: usize,
    pub follow: usize,
    pub follow2: usize,
    pub depth: usize,
    pub lines: usize,
    pub secs: f64,
    pub floor: f64,
    pub gate: f64,
}
impl Default for PlanConfig {
    fn default() -> Self {
        Self {
            roots: 16,
            follow: 6,
            follow2: 3,
            depth: 2,
            lines: 150,
            secs: 5.0,
            floor: 2500.0,
            gate: 0.04,
        }
    }
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub struct Config {
    pub name: String,
    pub score: String,
    pub mix: f64,
    pub window_horizon: String,
    pub follow_horizon: String,
    pub resource: Option<String>,
    pub plan: PlanConfig,
    pub own_deck: Option<OwnDeckVariant>,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            name: "jepa-tx-gate".into(),
            score: "plan".into(),
            mix: 0.0,
            window_horizon: "s".into(),
            follow_horizon: "s".into(),
            resource: Some("c-clock".into()),
            plan: PlanConfig::default(),
            own_deck: None,
        }
    }
}
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct Stats {
    pub windows: usize,
    pub planned: usize,
    pub gated: usize,
    pub lines: usize,
    pub leaves: usize,
    pub failed: usize,
    pub followed: usize,
    pub unplanned: usize,
    pub dropped: usize,
}
type FollowPlan = Vec<(String, String)>;
struct Line {
    taken: Vec<usize>,
    mine: FollowPlan,
    position: Value,
}
enum LineResult {
    Leaf(Line),
    Failed,
    Abort,
}
struct Last {
    key: String,
    best: Option<HashMap<usize, FollowPlan>>,
}

pub struct JepaBot {
    pub config: Config,
    pub tables: CardTables,
    pub stats: Stats,
    pub fail: Option<String>,
    pub plan: FollowPlan,
    pub own_deck: Option<OwnDeckContext>,
    rng: PyRandom,
    seen: HashMap<String, Vec<usize>>,
    last: Option<Last>,
}
pub fn canonical(v: &Value) -> String {
    match v {
        Value::Null => "null".into(),
        Value::Bool(b) => b.to_string(),
        Value::Number(n) => js_number(n.as_f64().unwrap_or(0.0)),
        Value::String(x) => serde_json::to_string(x).unwrap(),
        Value::Array(a) => format!(
            "[{}]",
            a.iter().map(canonical).collect::<Vec<_>>().join(",")
        ),
        Value::Object(o) => {
            let mut keys = o.keys().collect::<Vec<_>>();
            keys.sort();
            format!(
                "{{{}}}",
                keys.into_iter()
                    .map(|k| format!("{}:{}", serde_json::to_string(k).unwrap(), canonical(&o[k])))
                    .collect::<Vec<_>>()
                    .join(",")
            )
        }
    }
}
pub fn action_key(a: &Value) -> String {
    let arg = if a["arg"].is_number() || a["arg"].is_boolean() {
        a["arg"].clone()
    } else {
        Value::Null
    };
    canonical(&json!([
        a["kind"],
        a["label"],
        a["card"]["n"],
        a["card"]["zone"],
        a["card"]["ctl"],
        arg
    ]))
}
pub fn labels_key(acts: &[Value]) -> String {
    serde_json::to_string(&acts.iter().map(action_key).collect::<Vec<_>>()).unwrap()
}
fn is_button(a: &Value, label: &str) -> bool {
    s(a, "kind") == "button" && s(a, "label").to_lowercase() == label
}
fn sigmoid(v: f64) -> f64 {
    1.0 / (1.0 + (-v).exp())
}
fn order(scores: &[f64]) -> Vec<usize> {
    let mut out = (0..scores.len()).collect::<Vec<_>>();
    out.sort_by(|a, b| {
        scores[*b]
            .partial_cmp(&scores[*a])
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.cmp(b))
    });
    out
}
fn observation_key(msg: &Value) -> String {
    canonical(&json!([
        msg["prompt"],
        msg["state"],
        arr(msg, "actions")
            .iter()
            .map(|a| a["label"].clone())
            .collect::<Vec<_>>()
    ]))
}

impl JepaBot {
    pub fn new(config: Config) -> Self {
        Self {
            config,
            tables: CardTables::default(),
            stats: Stats::default(),
            fail: None,
            plan: vec![],
            own_deck: None,
            rng: PyRandom::new(0),
            seen: HashMap::new(),
            last: None,
        }
    }
    pub fn new_game(&mut self, seed: u64) {
        self.rng = PyRandom::new(seed);
        self.seen.clear();
        self.plan.clear();
        self.fail = None;
        self.stats = Stats::default();
        self.last = None;
        self.own_deck = None;
    }
    pub fn hello(&mut self, msg: &Value) -> Value {
        self.tables = CardTables::from_cards(&msg["cards"]);
        self.new_game(msg["seed"].as_f64().unwrap_or(0.0).trunc().abs() as u64);
        self.own_deck = self
            .config
            .own_deck
            .map(|variant| OwnDeckContext::from_original(variant, &msg["deck"], &msg["cards"]));
        if self.config.score != "imagined"
            && arr(msg, "versions").iter().any(|v| v.as_f64() == Some(2.0))
        {
            json!({"t":"ready","v":2,"name":self.config.name,"sim":true})
        } else {
            json!({"t":"ready","v":1,"name":self.config.name})
        }
    }
    pub fn over(&self) -> Value {
        json!({"t":"ok"})
    }
    pub fn encode(&self, msg: &Value) -> Encoded {
        let mut encoded = encode(msg, &self.tables);
        encoded.own_deck = self.own_deck.clone();
        encoded
    }
    pub fn think<M: Model + ?Sized>(&self, msg: &Value, model: &mut M) -> Result<Vec<f64>, String> {
        let window = truthy(&msg["prompt"]["actionWindow"]);
        let follow =
            self.config.follow_horizon == "s" && !window && s(&msg["state"], "phase") == "action";
        let role = if window || follow {
            ModelRole::Evaluator
        } else {
            ModelRole::Raw
        };
        let encoded = self.encode(msg);
        let n = encoded.actions.n;
        let settled = model.has_horizon(role, "s");
        let mut values = |h: &str| -> Result<Vec<f64>, String> {
            let out = model.predict_values(role, &encoded, h)?;
            if out.len() != n {
                return Err(format!(
                    "model returned {} scores for {n} actions",
                    out.len()
                ));
            }
            Ok(out.into_iter().map(sigmoid).collect())
        };
        // Current paired checkpoints both support the settled horizon. Other backends may report its absence.
        if settled && ((self.config.window_horizon == "s" && window) || follow) {
            values("s")
        } else {
            let v1 = values("1")?;
            if self.config.mix != 0.0 {
                let v4 = values("4")?;
                Ok(v1
                    .iter()
                    .zip(v4)
                    .map(|(a, b)| (1.0 - self.config.mix) * a + self.config.mix * b)
                    .collect())
            } else {
                Ok(v1)
            }
        }
    }

    fn rush_move(&mut self, r: &Value, target: &str, seen: &mut HashMap<String, usize>) -> usize {
        let acts = arr(r, "actions");
        let actor = s(r, "actor");
        let st = &r["state"];
        let opp = &st["players"][actor];
        let mine = &st["players"][target];
        let prompt = &r["prompt"];
        if truthy(&prompt["actionWindow"]) {
            let mut units = HashMap::new();
            for u in arr(opp, "ground").iter().chain(arr(opp, "space")) {
                units.insert(canonical(&u["id"]), u);
            }
            let ready = units.values().filter(|u| !truthy(&u["x"])).count();
            let key = canonical(&json!([
                st["round"],
                opp["handCount"],
                opp["res"]["ready"],
                mine["base"]["d"],
                ready
            ]));
            let count = seen.entry(key).or_default();
            *count += 1;
            let passes = acts
                .iter()
                .filter(|a| is_button(a, "pass"))
                .filter_map(|a| a["i"].as_u64().map(|i| i as usize))
                .collect::<Vec<_>>();
            if *count > 2 && !passes.is_empty() {
                return passes[0];
            }
            let leader = opp["leader"].get("id");
            let mut best = None;
            let mut best_p = 0.0;
            for a in acts {
                let c = &a["card"];
                if s(a, "kind") != "card" || !py_truthy(c) || s(c, "ctl") != actor {
                    continue;
                }
                let p = if s(c, "zone") == "hand" {
                    300.0 + self.tables.db.get(s(c, "s")).map_or(0.0, |i| i.cost)
                } else if let Some(u) = units.get(&canonical(&c["id"])) {
                    200.0 + numberish(&u["p"])
                } else if c.get("id") == leader {
                    100.0
                } else {
                    0.0
                };
                if p > best_p {
                    best = a["i"].as_u64().map(|i| i as usize);
                    best_p = p;
                }
            }
            return best.or_else(|| passes.first().copied()).unwrap_or(0);
        }
        let title = format!("{} {}", s(prompt, "title"), s(prompt, "promptTitle")).to_lowercase();
        if title.contains("attack") {
            let base = mine["base"].get("id");
            let cards = acts
                .iter()
                .filter(|a| s(a, "kind") == "card" && py_truthy(&a["card"]))
                .collect::<Vec<_>>();
            if let Some(a) = cards.iter().find(|a| a["card"].get("id") == base) {
                return a["i"].as_u64().unwrap_or(0) as usize;
            }
            let mut hp = HashMap::new();
            for u in arr(mine, "ground").iter().chain(arr(mine, "space")) {
                hp.insert(canonical(&u["id"]), numberish(&u["h"]) - numberish(&u["d"]));
            }
            let mut best = None;
            let mut value = 0.0;
            for a in cards {
                if let Some(v) = hp.get(&canonical(&a["card"]["id"])) {
                    if best.is_none() || *v < value {
                        best = a["i"].as_u64().map(|i| i as usize);
                        value = *v;
                    }
                }
            }
            if let Some(i) = best {
                return i;
            }
        }
        let keep = acts
            .iter()
            .filter(|a| !is_button(a, "cancel"))
            .filter_map(|a| a["i"].as_u64().map(|i| i as usize))
            .collect::<Vec<_>>();
        if keep.is_empty() {
            self.rng.below(acts.len())
        } else {
            self.rng.choice(&keep)
        }
    }
    pub fn settled(r: &Value) -> bool {
        truthy(&r["over"])
            || truthy(&r["prompt"]["actionWindow"])
            || s(&r["state"], "phase") != "action"
    }

    fn plan_line<M: Model + ?Sized, S: Simulator + ?Sized>(
        &mut self,
        msg: &Value,
        model: &mut M,
        sim: &mut S,
        path: &[usize],
        queue: &mut VecDeque<Vec<usize>>,
    ) -> Result<LineResult, String> {
        let me = you(msg);
        let mut r = sim.request(json!({"t":"sim","op":"begin","deal":0}))?;
        if truthy(&r["error"]) || arr(&r, "actions").len() != arr(msg, "actions").len() {
            self.fail = Some(format!(
                "begin: {}",
                r["error"].as_str().unwrap_or("actions differ")
            ));
            return Ok(LineResult::Abort);
        }
        let mut taken = Vec::new();
        let mut mine = Vec::new();
        let mut guard: HashMap<String, Vec<usize>> = HashMap::new();
        let mut seen = HashMap::new();
        let mut depth = 0;
        for step in 0..80 {
            if truthy(&r["error"]) {
                self.fail = Some(format!("act: {}", s(&r, "error")));
                return Ok(LineResult::Failed);
            }
            if r["ms"]
                .as_f64()
                .is_some_and(|ms| ms < self.config.plan.floor)
            {
                self.fail = Some("time".into());
                return Ok(LineResult::Abort);
            }
            if step > 0 && Self::settled(&r) {
                return Ok(LineResult::Leaf(Line {
                    taken,
                    mine,
                    position: r,
                }));
            }
            let acts = arr(&r, "actions");
            if acts.is_empty() {
                self.fail = Some("no actions".into());
                return Ok(LineResult::Failed);
            }
            let actor = s(&r, "actor");
            let key = if actor == me && acts.len() > 1 {
                Some(canonical(&json!([
                    r["prompt"],
                    r["state"],
                    acts.iter().map(|a| a["label"].clone()).collect::<Vec<_>>()
                ])))
            } else {
                None
            };
            let j = if step < path.len() {
                let j = path[step];
                if step > 0 {
                    if let Some(k) = &key {
                        guard.entry(k.clone()).or_default().push(j);
                        depth += 1;
                    }
                }
                j
            } else if actor != me {
                self.rush_move(&r, me, &mut seen)
            } else if acts.len() == 1 {
                0
            } else {
                let pos = json!({"you":me,"prompt":r["prompt"],"state":r["state"],"actions":acts});
                let ranks = order(&self.think(&pos, model)?);
                let cancels = acts
                    .iter()
                    .enumerate()
                    .filter(|(_, a)| is_button(a, "cancel"))
                    .map(|(i, _)| i)
                    .collect::<HashSet<_>>();
                let ranks = ranks
                    .iter()
                    .filter(|i| !cancels.contains(*i))
                    .chain(ranks.iter().filter(|i| cancels.contains(*i)))
                    .copied()
                    .collect::<Vec<_>>();
                let tried = guard.entry(key.clone().unwrap()).or_default();
                let j = if tried.is_empty() && depth < self.config.plan.depth {
                    let width = if depth == 0 {
                        self.config.plan.follow
                    } else {
                        self.config.plan.follow2
                    };
                    let mut opts = ranks
                        .iter()
                        .filter(|i| !cancels.contains(*i))
                        .take(width)
                        .copied()
                        .collect::<Vec<_>>();
                    if opts.is_empty() {
                        opts = ranks.iter().take(1).copied().collect();
                    }
                    for alt in opts.iter().skip(1) {
                        let mut next = taken.clone();
                        next.push(*alt);
                        queue.push_back(next);
                    }
                    opts[0]
                } else {
                    let best = ranks[0];
                    if tried.len() >= 2 && tried.contains(&best) {
                        ranks
                            .iter()
                            .find(|i| !tried.contains(i))
                            .copied()
                            .unwrap_or_else(|| self.rng.below(acts.len()))
                    } else {
                        best
                    }
                };
                tried.push(j);
                depth += 1;
                j
            };
            if actor == me && step > 0 && acts.len() > 1 {
                let a = acts.get(j).ok_or("planner chose an unavailable action")?;
                mine.push((labels_key(acts), action_key(a)));
            }
            taken.push(j);
            r = sim.request(json!({"t":"sim","op":"act","i":j}))?;
        }
        self.fail = Some("step cap".into());
        Ok(LineResult::Failed)
    }

    fn plan_moves<M: Model + ?Sized, S: Simulator + ?Sized>(
        &mut self,
        msg: &Value,
        model: &mut M,
        sim: &mut S,
        imagined: &[f64],
    ) -> Result<Option<(Vec<f64>, HashMap<usize, FollowPlan>)>, String> {
        let acts = arr(msg, "actions");
        let me = you(msg);
        let mut roots = order(imagined)
            .into_iter()
            .take(self.config.plan.roots)
            .collect::<Vec<_>>();
        for (i, a) in acts.iter().enumerate() {
            if is_button(a, "pass") && !roots.contains(&i) {
                roots.push(i);
            }
        }
        let mut queue = roots.into_iter().map(|i| vec![i]).collect::<VecDeque<_>>();
        let start = PlannerClock::now()?;
        let mut leaves = Vec::new();
        let mut lines = 0;
        while !queue.is_empty()
            && lines < self.config.plan.lines
            && start.elapsed_seconds()? < self.config.plan.secs
        {
            let path = queue.pop_front().unwrap();
            let res = self.plan_line(msg, model, sim, &path, &mut queue)?;
            lines += 1;
            match res {
                LineResult::Abort => break,
                LineResult::Failed => self.stats.failed += 1,
                LineResult::Leaf(line) => leaves.push(line),
            }
        }
        sim.request(json!({"t":"sim","op":"end"}))?;
        self.stats.lines += lines;
        self.stats.leaves += leaves.len();
        if leaves.is_empty() {
            return Ok(None);
        }
        let mut scores = vec![-1.0; acts.len()];
        let mut best = HashMap::new();
        let same = canonical(&msg["state"]);
        for line in leaves {
            let r = &line.position;
            let value = if truthy(&r["over"]) {
                let winner = &r["over"]["winner"];
                if winner.as_str() == Some(me) {
                    1.0
                } else if winner.is_null() || winner.as_str() == Some("draw") {
                    0.5
                } else {
                    0.0
                }
            } else if s(r, "actor") == me
                && truthy(&r["prompt"]["actionWindow"])
                && canonical(&r["state"]) == same
            {
                0.0
            } else {
                let pos = if s(r, "actor") == me {
                    json!({"you":me,"prompt":r["prompt"],"state":r["state"],"actions":r["actions"]})
                } else {
                    json!({"you":me,"prompt":{"type":"actionWindow","actionWindow":true,"selectCardMode":null,"selected":[]},"state":r["state"],"actions":acts})
                };
                sigmoid(model.context_value(ModelRole::Raw, &self.encode(&pos))?)
            };
            let root = line.taken[0];
            if value > scores[root] {
                scores[root] = value;
                best.insert(root, line.mine);
            }
        }
        Ok(Some((scores, best)))
    }

    fn follow_plan(&mut self, msg: &Value) -> Option<usize> {
        if self.plan.is_empty() {
            return None;
        }
        let acts = arr(msg, "actions");
        let sig = labels_key(acts);
        if let Some(k) = self.plan.iter().position(|(want, _)| *want == sig) {
            let choice = self.plan[k].1.clone();
            self.plan = self.plan[k + 1..].to_vec();
            return acts.iter().position(|a| action_key(a) == choice);
        }
        self.plan.clear();
        self.stats.dropped += 1;
        None
    }
    pub fn decide<M: Model + ?Sized, S: Simulator + ?Sized>(
        &mut self,
        msg: &Value,
        model: &mut M,
        sim: &mut S,
    ) -> Result<Value, String> {
        Ok(json!({"t":"act","i":self.pick(msg,model,sim)?}))
    }
    pub fn pick<M: Model + ?Sized, S: Simulator + ?Sized>(
        &mut self,
        msg: &Value,
        model: &mut M,
        sim: &mut S,
    ) -> Result<usize, String> {
        self.last = None;
        let acts = arr(msg, "actions");
        let n = acts.len();
        if n <= 1 {
            return Ok(0);
        }
        if !matches!(self.config.score.as_str(), "plan" | "imagined") {
            return Err(format!("score {} is not ported", self.config.score));
        }
        let mut scores = self.think(msg, model)?;
        if let Some(policy) = &self.config.resource {
            if policy == "c-clock" {
                if let Some(j) = resource::choose_clock(msg, &self.tables) {
                    return Ok(j);
                }
            } else {
                return Err(format!(
                    "resource policy {policy} is not the table c-clock rule"
                ));
            }
        }
        self.fail = None;
        let window = truthy(&msg["prompt"]["actionWindow"]);
        let mut best = None;
        if self.config.score == "plan" {
            if window {
                self.plan.clear();
                self.stats.windows += 1;
                let max = scores.iter().copied().fold(f64::NEG_INFINITY, f64::max);
                let min = scores.iter().copied().fold(f64::INFINITY, f64::min);
                if max - min < self.config.plan.gate {
                    self.stats.gated += 1;
                } else if truthy(&msg["sim"]) {
                    if let Some((planned, plans)) = self.plan_moves(msg, model, sim, &scores)? {
                        scores = planned;
                        best = Some(plans);
                        self.stats.planned += 1;
                    }
                }
            } else if let Some(j) = self.follow_plan(msg) {
                self.stats.followed += 1;
                return Ok(j);
            } else {
                self.stats.unplanned += 1;
            }
        }
        let key = observation_key(msg);
        let tried = self.seen.entry(key.clone()).or_default();
        let ranked = order(&scores);
        let mut pick = ranked[0];
        if tried.len() >= 2 && tried.contains(&pick) {
            pick = ranked
                .iter()
                .find(|i| !tried.contains(i))
                .copied()
                .unwrap_or_else(|| self.rng.below(n));
        }
        tried.push(pick);
        if let Some(plans) = &best {
            self.plan = plans.get(&pick).cloned().unwrap_or_default();
        }
        self.last = Some(Last { key, best });
        Ok(pick)
    }
    pub fn adopt(&mut self, i: usize) {
        if let Some(last) = &self.last {
            if let Some(tried) = self.seen.get_mut(&last.key) {
                if let Some(x) = tried.last_mut() {
                    *x = i;
                }
            }
            if let Some(best) = &last.best {
                self.plan = best.get(&i).cloned().unwrap_or_default();
            }
        }
    }
}

fn numberish(v: &Value) -> f64 {
    match v {
        Value::Number(n) => n.as_f64().unwrap_or(0.0),
        Value::Bool(b) => {
            if *b {
                1.0
            } else {
                0.0
            }
        }
        Value::String(s) => s.trim().parse().unwrap_or(0.0),
        _ => 0.0,
    }
}
