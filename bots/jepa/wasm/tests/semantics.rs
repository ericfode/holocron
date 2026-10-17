//! Golden helper semantics from the pinned JavaScript implementation. No model or simulator is loaded.
use jepa_controller::{
    features::{encode, hash_id, CardTables},
    resource::choose_clock,
    rng::PyRandom,
    Config, Encoded, JepaBot, Model, ModelRole, Simulator,
};
use serde_json::Value;

fn fixture() -> Value {
    serde_json::from_str(include_str!("fixtures/semantics.json")).unwrap()
}

fn assert_bits(name: &str, actual: &[f32], expected: &Value) {
    let expected = expected.as_array().unwrap();
    assert_eq!(actual.len(), expected.len(), "{name}: length");
    for (i, (actual, expected)) in actual.iter().zip(expected).enumerate() {
        let expected = expected.as_u64().unwrap() as u32;
        assert_eq!(
            actual.to_bits(),
            expected,
            "{name}[{i}]: actual {actual:?}, expected {:?}",
            f32::from_bits(expected)
        );
    }
}

fn assert_ids(name: &str, actual: &[i32], expected: &Value) {
    let expected: Vec<i32> = serde_json::from_value(expected.clone()).unwrap();
    assert_eq!(actual, expected, "{name}");
}

#[test]
fn feature_vectors_match_javascript_float32_bits() {
    let fixture = fixture();
    for case in fixture["features"].as_array().unwrap() {
        let name = case["name"].as_str().unwrap();
        let msg: Value = serde_json::from_str(case["msg_json"].as_str().unwrap()).unwrap();
        let cards = case.get("cards").unwrap_or(&fixture["cards"]);
        let encoded = encode(&msg, &CardTables::from_cards(cards));
        let expected = &case["expected"];
        assert_bits(&format!("{name}.state"), &encoded.state, &expected["state"]);
        assert_bits(
            &format!("{name}.actions.rows"),
            &encoded.actions.rows,
            &expected["actions"]["rows"],
        );
        assert_ids(
            &format!("{name}.actions.ids"),
            &encoded.actions.ids,
            &expected["actions"]["ids"],
        );
        assert_eq!(
            encoded.actions.n,
            expected["actions"]["n"].as_u64().unwrap() as usize,
            "{name}.actions.n"
        );
        assert_bits(
            &format!("{name}.tokens.feats"),
            &encoded.tokens.feats,
            &expected["tokens"]["feats"],
        );
        assert_ids(
            &format!("{name}.tokens.ids"),
            &encoded.tokens.ids,
            &expected["tokens"]["ids"],
        );
        assert_eq!(
            encoded.tokens.n,
            expected["tokens"]["n"].as_u64().unwrap() as usize,
            "{name}.tokens.n"
        );
    }
}

#[test]
fn resource_policy_matches_reference_thresholds_aspect_multiplicity_and_action_ids() {
    let fixture = fixture();
    for case in fixture["resource"].as_array().unwrap() {
        let cards = case.get("cards").unwrap_or(&fixture["cards"]);
        let expected = case["expected"].as_u64().map(|n| n as usize);
        assert_eq!(
            choose_clock(&case["msg"], &CardTables::from_cards(cards)),
            expected,
            "{}",
            case["name"]
        );
    }
}

#[test]
fn card_and_label_hashes_use_utf8_fnv_low_bits() {
    for case in fixture()["hashes"].as_array().unwrap() {
        assert_eq!(
            hash_id(case["input"].as_str().unwrap()),
            case["expected"].as_i64().unwrap() as i32,
            "{}",
            case["input"]
        );
    }
}

#[test]
fn python_randrange_matches_reference_including_rejection_and_twist() {
    for case in fixture()["rng"].as_array().unwrap() {
        let seed = case["seed"].as_u64().unwrap();
        let mut rng = PyRandom::new(seed);
        for (i, draw) in case["draws"].as_array().unwrap().iter().enumerate() {
            let n = draw["n"].as_u64().unwrap() as usize;
            assert_eq!(
                rng.below(n),
                draw["expected"].as_u64().unwrap() as usize,
                "seed {seed}, draw {i}, bound {n}"
            );
        }
    }
}

struct FixedModel {
    flat: bool,
    calls: usize,
}

impl Model for FixedModel {
    fn predict_values(
        &mut self,
        role: ModelRole,
        encoded: &Encoded,
        horizon: &str,
    ) -> Result<Vec<f64>, String> {
        // Every scenario is an action window or action-phase follow-up. They must use the evaluator head at s.
        assert!(matches!(role, ModelRole::Evaluator));
        assert_eq!(horizon, "s");
        self.calls += 1;
        let follow = encoded.actions.rows.get(1) == Some(&1.0);
        Ok((0..encoded.actions.n)
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

    fn context_value(&mut self, role: ModelRole, _encoded: &Encoded) -> Result<f64, String> {
        assert!(
            matches!(role, ModelRole::Raw),
            "real settled boards use the outcome-trained raw head"
        );
        Ok(2.0)
    }
}

struct ReplaySimulator<'a> {
    transcript: &'a [Value],
    cursor: usize,
}

impl Simulator for ReplaySimulator<'_> {
    fn request(&mut self, request: Value) -> Result<Value, String> {
        let row = self
            .transcript
            .get(self.cursor)
            .ok_or_else(|| format!("unexpected simulator request {request}"))?;
        if request != row["request"] {
            return Err(format!(
                "simulator request {}: got {request}, expected {}",
                self.cursor, row["request"]
            ));
        }
        self.cursor += 1;
        Ok(row["reply"].clone())
    }
}

#[test]
fn controller_matches_reference_gate_search_followup_and_loop_guard() {
    let fixtures: Value = serde_json::from_str(include_str!("fixtures/planning.json")).unwrap();
    for case in fixtures["cases"].as_array().unwrap() {
        let name = case["name"].as_str().unwrap();
        let config: Config = serde_json::from_value(case["config"].clone()).unwrap();
        let mut bot = JepaBot::new(config);
        assert_eq!(bot.hello(&case["hello"]), case["ready"], "{name}: ready");
        let mut model = FixedModel {
            flat: case["flat"].as_bool().unwrap(),
            calls: 0,
        };
        let transcript = case["transcript"].as_array().unwrap();
        let mut sim = ReplaySimulator {
            transcript,
            cursor: 0,
        };
        for (i, (input, reply)) in case["inputs"]
            .as_array()
            .unwrap()
            .iter()
            .zip(case["replies"].as_array().unwrap())
            .enumerate()
        {
            assert_eq!(
                bot.decide(input, &mut model, &mut sim)
                    .unwrap_or_else(|e| panic!("{name}, decision {i}: {e}")),
                *reply,
                "{name}, decision {i}"
            );
        }
        assert_eq!(
            sim.cursor,
            transcript.len(),
            "{name}: all simulator messages consumed"
        );
        assert_eq!(
            serde_json::to_value(&bot.stats).unwrap(),
            case["stats"],
            "{name}: statistics"
        );
        assert_eq!(
            serde_json::to_value(&bot.fail).unwrap(),
            case["fail"],
            "{name}: failure reason"
        );
        assert!(model.calls > 0, "{name}: invoked deterministic model");
        assert_eq!(bot.over(), serde_json::json!({ "t": "ok" }));
    }
}

struct RoutingModel {
    calls: Vec<(ModelRole, String)>,
}
impl Model for RoutingModel {
    fn predict_values(
        &mut self,
        role: ModelRole,
        encoded: &Encoded,
        horizon: &str,
    ) -> Result<Vec<f64>, String> {
        self.calls.push((role, horizon.to_owned()));
        let logit = match horizon {
            "1" => -1.0,
            "4" => 1.0,
            "s" => 2.0,
            _ => return Err("unexpected horizon".into()),
        };
        Ok(vec![logit; encoded.actions.n])
    }
    fn context_value(&mut self, _role: ModelRole, _encoded: &Encoded) -> Result<f64, String> {
        panic!("think does not simulate")
    }
}

#[test]
fn prompt_phase_selects_the_reference_head_and_horizon() {
    let fixture = fixture();
    let cases = &fixture["features"];
    let cards = CardTables::from_cards(&fixture["cards"]);
    for (name, expected_role, expected_horizon) in [
        ("window-p1", ModelRole::Evaluator, "s"),
        ("window-p2", ModelRole::Evaluator, "s"),
        ("followup-p1", ModelRole::Evaluator, "s"),
        ("resource-p1", ModelRole::Raw, "1"),
        ("resource-stop-p2", ModelRole::Raw, "1"),
    ] {
        let case = cases
            .as_array()
            .unwrap()
            .iter()
            .find(|c| c["name"] == name)
            .unwrap();
        let msg: Value = serde_json::from_str(case["msg_json"].as_str().unwrap()).unwrap();
        let mut bot = JepaBot::new(Config::default());
        bot.tables = cards.clone();
        let mut model = RoutingModel { calls: vec![] };
        bot.think(&msg, &mut model).unwrap();
        assert_eq!(
            model.calls,
            vec![(expected_role, expected_horizon.into())],
            "{name}"
        );
    }
    let msg: Value = serde_json::from_str(cases[0]["msg_json"].as_str().unwrap()).unwrap();
    let mut config = Config::default();
    config.mix = 0.25;
    config.window_horizon = "1".into();
    let mut bot = JepaBot::new(config);
    bot.tables = cards;
    let mut model = RoutingModel { calls: vec![] };
    let scores = bot.think(&msg, &mut model).unwrap();
    assert_eq!(
        model.calls,
        vec![
            (ModelRole::Evaluator, "1".into()),
            (ModelRole::Evaluator, "4".into())
        ]
    );
    let expected = 0.75 / (1.0 + 1.0_f64.exp()) + 0.25 / (1.0 + (-1.0_f64).exp());
    assert!(scores.iter().all(|v| (v - expected).abs() < 1e-12));
}

#[test]
fn protocol_negotiation_and_trivial_decisions_keep_reference_behavior() {
    let mut bot = JepaBot::new(Config::default());
    assert_eq!(
        bot.hello(&serde_json::json!({"versions":[2],"seed":0})),
        serde_json::json!({"t":"ready","v":2,"name":"jepa-tx-gate","sim":true})
    );
    assert_eq!(
        bot.hello(&serde_json::json!({"versions":[1],"seed":0})),
        serde_json::json!({"t":"ready","v":1,"name":"jepa-tx-gate"})
    );
    let mut config = Config::default();
    config.score = "imagined".into();
    let mut imagined = JepaBot::new(config);
    // Preserves the reference's v1 response for imagined mode, even when hello offers only v2.
    assert_eq!(imagined.hello(&serde_json::json!({"versions":[2]}))["v"], 1);
    let mut model = RoutingModel { calls: vec![] };
    let mut sim =
        |_request| -> Result<Value, String> { panic!("a trivial decision cannot simulate") };
    for actions in [
        serde_json::json!([]),
        serde_json::json!([{"i":0,"kind":"button","label":"Done"}]),
    ] {
        assert_eq!(
            bot.decide(
                &serde_json::json!({"actions":actions}),
                &mut model,
                &mut sim
            )
            .unwrap(),
            serde_json::json!({"t":"act","i":0})
        );
    }
    assert!(model.calls.is_empty());
}
