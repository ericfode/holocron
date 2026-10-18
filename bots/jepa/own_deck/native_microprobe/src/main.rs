//! Two actual, fully admitted card abilities in synthetic public microstates.
//! No game loop, search, optimizer, opponent, network, or hidden-card sampling.
use kessel::{model::{Card, CardId, Decision}, Action, Engine, Seat, State};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{env, fs, io::Write, path::{Path, PathBuf}, process::Command, time::Instant};

const SOURCE: &str = "/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source";
const REVISION: &str = "c7ee39554901278cee70f61fd8b26fb1920696b3";
const MAX_APPLY: usize = 12;
const EXPECTED_APPLY: usize = 8;
const MAX_SECONDS: u64 = 120;
// The loader requires its exact native Shield definition even for abilities
// that never create a Shield. This row remains unmodified and `unsupported`
// in compiler data; native admission owns the special token contract.
const SELECTED: [&str; 5] = ["ASH_011", "IBH_053", "ASH_019", "LOF_256", "TOKEN_SHIELD"];

fn source_preflight() -> Result<(), String> {
    let rev = Command::new("git").args(["-C", SOURCE, "rev-parse", "HEAD"])
        .output().map_err(|e| e.to_string())?;
    if !rev.status.success() || String::from_utf8_lossy(&rev.stdout).trim() != REVISION {
        return Err("pinned source revision mismatch".into());
    }
    let clean = Command::new("git").args(["-C", SOURCE, "diff", "--quiet", "HEAD", "--",
        "crates/kessel", "compiler/generated", "Cargo.toml", "Cargo.lock"])
        .status().map_err(|e| e.to_string())?;
    if !clean.success() { return Err("pinned Kessel execution inputs changed".into()); }
    Ok(())
}

fn add(e: &Engine, s: &mut State, seat: Seat, code: &str) -> CardId {
    let id = s.next_id;
    s.next_id += 1;
    let definition = e.definitions.iter().position(|d| d.code == code)
        .unwrap_or_else(|| panic!("whole card was not admitted: {code}")) as u16;
    *s.card_mut(id) = Card {
        present: true, def: definition, owner: seat, ..Card::default()
    };
    id
}

fn unit(e: &Engine, s: &mut State, seat: Seat, damage: u16) -> CardId {
    // LOF_256 is a 1/4 ground unit with no abilities, keywords or modifiers.
    let id = add(e, s, seat, "LOF_256");
    s.card_mut(id).damage = damage;
    s.card_mut(id).exhausted = true;
    s.player_mut(seat).ground.push(id).unwrap();
    s.arena_unit_order[0].push(id).unwrap();
    s.registration_order.push(id).unwrap();
    id
}

struct Fixture { state: State, source: CardId, resource: CardId, eligible: CardId, excluded: CardId }

fn fixture(e: &Engine, code: &str) -> Fixture {
    let mut s = State { hidden_history_exact: true, ..State::default() };
    for (seat, leader) in [(Seat::P1, code), (Seat::P2, "IBH_053")] {
        let base = add(e, &mut s, seat, "ASH_019");
        let leader = add(e, &mut s, seat, leader);
        s.player_mut(seat).base = base;
        s.player_mut(seat).leader = leader;
    }
    let source = s.player(Seat::P1).leader;
    // One total resource keeps deployment unavailable for both focal leaders.
    let resource = add(e, &mut s, Seat::P1, "LOF_256");
    s.player_mut(Seat::P1).resources.push(resource).unwrap();
    let high = unit(e, &mut s, Seat::P2, 2); // 2 remaining HP: legal Cad target.
    let low = unit(e, &mut s, Seat::P2, 3); // 1 remaining HP: illegal Cad target.
    let (eligible, excluded) = if code == "ASH_011" { (high, low) }
        else { (s.player(Seat::P2).base, high) };
    Fixture { state: s, source, resource, eligible, excluded }
}

fn offered_card(e: &Engine, s: &State, id: CardId) -> Result<Action, String> {
    e.legal_actions(s).into_iter().find(|a| a.id() == Some(id))
        .ok_or_else(|| format!("expected offered card c{} at {:?}", id - 1, s.decision))
}

fn has_card(e: &Engine, s: &State, id: CardId) -> bool {
    e.legal_actions(s).iter().any(|a| a.id() == Some(id))
}

fn capture(e: &Engine, s: &State) -> Value {
    json!({"decision":format!("{:?}",s.decision),"actor":s.actor(),
        "sourceInstance":if s.source==0 {Value::Null}else{json!(format!("c{}",s.source-1))},
        "abilityProgramPlusOne":s.ability_program,"abilityPc":s.ability_pc,
        "abilityCommitted":s.ability_committed,"state":e.snapshot(s),
        "offeredActions":e.legal_actions(s)})
}

struct Budget { started: Instant, calls: usize, trace_path: PathBuf }
impl Budget {
    fn trace(&self, row: &Value) -> Result<(), String> {
        let mut f = fs::OpenOptions::new().append(true).open(&self.trace_path)
            .map_err(|e| format!("partial trace open failed: {e}"))?;
        serde_json::to_writer(&mut f, row).map_err(|e| e.to_string())?;
        f.write_all(b"\n").and_then(|_|f.flush()).map_err(|e| e.to_string())
    }
    fn apply(&mut self, e: &Engine, s: &State, a: &Action) -> Result<State, String> {
        if self.calls >= MAX_APPLY || self.started.elapsed().as_secs() >= MAX_SECONDS {
            return Err("microprobe transition/time guard reached".into());
        }
        if !e.legal_actions(s).contains(a) { return Err("probe attempted an unoffered action".into()); }
        self.trace(&json!({"phase":"beforeApply","applyCall":self.calls+1,
            "before":capture(e,s),"offeredAction":a}))?;
        self.calls += 1;
        let result = e.apply(s, a);
        let row = match &result {
            Ok(after) => json!({"phase":"afterApply","applyCall":self.calls,"after":capture(e,after)}),
            Err(error) => json!({"phase":"applyError","applyCall":self.calls,"error":error}),
        };
        self.trace(&row)?;
        result
    }
}

fn run_case(e: &Engine, budget: &mut Budget, code: &str) -> Result<Value, String> {
    let f = fixture(e, code);
    let s = f.state;
    // Validate the public fixture through the real import boundary. No transition.
    let imported = e.load_state(&e.snapshot(&s))?;
    assert_eq!(e.snapshot(&s), e.snapshot(&imported));
    assert_eq!(e.legal_actions(&s), e.legal_actions(&imported));
    assert!(has_card(e, &s, f.source));
    let mut exhausted = s;
    exhausted.card_mut(f.source).exhausted = true;
    assert!(!has_card(e, &exhausted, f.source));
    let mut no_ready_resource = s;
    no_ready_resource.card_mut(f.resource).exhausted = true;
    if code == "IBH_053" { assert!(!has_card(e, &no_ready_resource, f.source)); }
    else { assert!(has_card(e, &no_ready_resource, f.source)); }

    let source_action = offered_card(e, &s, f.source)?;
    let prompt = budget.apply(e, &s, &source_action)?;
    assert_eq!(prompt.decision, Decision::AbilityTarget);
    assert_eq!(prompt.source, f.source);
    // The complete actual card has exactly one leader ability, asserted from
    // its catalogue below. Its runtime-local numeric program ID stays opaque.
    assert!(prompt.ability_program > 0);
    assert!(!prompt.ability_committed);
    assert!(!prompt.card(f.source).exhausted);
    assert!(!prompt.card(f.resource).exhausted);
    assert!(has_card(e, &prompt, f.eligible));
    assert!(!has_card(e, &prompt, f.excluded));
    if code == "ASH_011" {
        assert!(!has_card(e, &prompt, s.player(Seat::P1).base));
        assert!(!has_card(e, &prompt, s.player(Seat::P2).base));
    } else {
        assert!(has_card(e, &prompt, s.player(Seat::P1).base));
    }
    // Cancel is an actual offered tuple and must preserve both costs and state.
    let cancel = e.legal_actions(&prompt).into_iter().find(|a|
        a.kind == "button" && a.arg.as_ref().and_then(Value::as_str) == Some("cancel"))
        .ok_or("expected precommit Cancel")?;
    let cancelled = budget.apply(e, &prompt, &cancel)?;
    assert_eq!(e.snapshot(&cancelled), e.snapshot(&s));
    assert_eq!(e.legal_actions(&cancelled), e.legal_actions(&s));

    let target_action = offered_card(e, &prompt, f.eligible)?;
    let after = budget.apply(e, &prompt, &target_action)?;
    assert_eq!(after.decision, Decision::Window);
    assert_eq!(after.active, Seat::P2);
    assert_eq!(after.card(f.eligible).damage, s.card(f.eligible).damage + 1);
    assert!(after.card(f.source).exhausted);
    assert_eq!(after.card(f.resource).exhausted, code == "IBH_053");
    // One offered pass returns priority, making inability to reuse observable.
    let pass = e.legal_actions(&after).into_iter().find(|a|
        a.kind == "button" && a.arg.as_ref().and_then(Value::as_str) == Some("pass"))
        .ok_or("expected offered Pass")?;
    let following = budget.apply(e, &after, &pass)?;
    assert_eq!(following.decision, Decision::Window);
    assert_eq!(following.active, Seat::P1);
    assert!(!has_card(e, &following, f.source));
    assert!(!following.is_terminal());
    let mut ready_again = following;
    ready_again.card_mut(f.source).exhausted = false;
    if code == "IBH_053" {
        assert!(!has_card(e, &ready_again, f.source)); // paid resource still exhausted.
    } else { assert!(has_card(e, &ready_again, f.source)); }

    Ok(json!({"card":code,"abilityPath":["abilities","leader",0],
        "before":capture(e,&s),"sourceAction":source_action,
        "targetPrompt":capture(e,&prompt),"cancelAction":cancel,
        "cancelled":capture(e,&cancelled),"targetAction":target_action,
        "after":capture(e,&after),"followupPass":pass,"following":capture(e,&following),
        "predeterminedAssertionsPassed":["public fixture import roundtrip","source exhausted blocks action",
            "resource boundary matches literal cost","source click defers costs until target commitment",
            "eligible target offered and excluded target absent","cancel preserves state and legal actions",
            "chosen target takes exactly one damage","source exhausts and resource paid iff literal cost",
            "opponent offered pass returns priority","same leader cannot reuse ability"]}))
}

fn run() -> Result<Value, String> {
    source_preflight()?;
    let started = Instant::now();
    let mut catalogue = kessel::catalogue_io::load_catalogue_value(&Path::new(SOURCE).join("compiler/generated"))?;
    let full = catalogue["cards"].as_array().ok_or("catalogue missing cards")?;
    let required = [
        ("ASH_011", "c8deebf53ed30519ed4b4abe6b274f1c460997a55b209174e28125f3cec7752f"),
        ("IBH_053", "93cdf6459ac9de34369a172aec6a2729cb608c749f6a0bd847ccea8656987c41")
    ];
    let mut provenance = vec![];
    for (code, hash) in required {
        let entry = full.iter().find(|c| c["setCode"] == code).ok_or("missing actual card")?;
        assert_eq!(entry["sourceHash"], hash);
        let leader = entry["abilities"]["leader"].as_array().ok_or("leader side missing")?;
        assert_eq!(leader.len(), 1);
        assert_eq!(leader[0]["trigger"], "action");
        provenance.push(json!({"card":code,"sourceHash":hash,"sourcePath":entry["sourcePath"],
            "abilityPath":["abilities","leader",0],"actualUnmodifiedAbility":entry["abilities"]["leader"][0]}));
    }
    let shield = full.iter().find(|c| c["setCode"] == "TOKEN_SHIELD").ok_or("canonical Shield row missing")?;
    assert_eq!(shield["sourceHash"], "39f1c6699c36ba309a8fe8e053f9b94ddbb8877991767b6664fcd88d447be91f");
    assert_eq!(shield["status"], "unsupported");
    catalogue["cards"].as_array_mut().unwrap().retain(|c|
        c["setCode"].as_str().is_some_and(|v| SELECTED.contains(&v)));
    // Every selected card remains complete, including both leader sides.
    let catalogue_sha = format!("{:x}",Sha256::digest(serde_json::to_vec(&catalogue).unwrap()));
    let engine = Engine::from_catalogue_value(&catalogue)?;
    for code in SELECTED { assert!(engine.definitions.iter().any(|d|d.code==code),"whole card rejected: {code}"); }
    let trace_path = PathBuf::from(env::var("TYPED_IR_TRACE").map_err(|_|"TYPED_IR_TRACE must name a new partial-trace path")?);
    let mut trace = fs::OpenOptions::new().write(true).create_new(true).open(&trace_path).map_err(|e|e.to_string())?;
    serde_json::to_writer(&mut trace,&json!({"schema":"typed-ir-native-partial-trace/1",
        "sourceRevision":REVISION,"selectedWholeCards":SELECTED,"maxApplyCalls":MAX_APPLY,
        "syntheticPublicStatesOnly":true})).map_err(|e|e.to_string())?;
    trace.write_all(b"\n").and_then(|_|trace.flush()).map_err(|e|e.to_string())?;
    drop(trace);
    let mut budget = Budget { started, calls: 0, trace_path };
    let cases = [run_case(&engine,&mut budget,"ASH_011")?,run_case(&engine,&mut budget,"IBH_053")?];
    assert_eq!(budget.calls, EXPECTED_APPLY);
    source_preflight()?;
    Ok(json!({"schema":"jepa-typed-ir-native-microprobe/1","sourceRevision":REVISION,
        "selectedCatalogueSha256":catalogue_sha,"selectedWholeCards":SELECTED,
        "actualCardAbilitiesInSyntheticPublicStates":true,"forcetekiOracleRun":false,
        "noHiddenCardsOrDrawOrder":true,"applyCalls":budget.calls,"maxApplyCalls":MAX_APPLY,
        "elapsedSeconds":started.elapsed().as_secs_f64(),"maxSeconds":MAX_SECONDS,
        "excludedActualCards":{"IBH_001":"whole-card runtime admission rejects unit-side numCardsFunc",
            "SHD_002":"whole-card runtime admission rejects unit-side systemPropertiesFactory"},
        "provenance":provenance,"cases":cases}))
}

fn main() {
    // The final receipt opens only after all assertions pass. Partial JSONL
    // transition evidence is appended before/after every real apply call.
    let outcome = std::thread::Builder::new().stack_size(64*1024*1024).spawn(run)
        .expect("microprobe thread").join();
    match outcome {
        Ok(Ok(receipt)) => {
            let args: Vec<_> = std::env::args().collect();
            if args.len() != 2 { eprintln!("usage: typed-ir-microprobe NEW_RECEIPT.json");std::process::exit(2); }
            let mut f = fs::OpenOptions::new().write(true).create_new(true).open(&args[1]).expect("new receipt path");
            serde_json::to_writer_pretty(&mut f,&receipt).unwrap();f.write_all(b"\n").unwrap();
            println!("{}",json!({"ok":true,"receipt":args[1],"applyCalls":EXPECTED_APPLY}));
        }
        Ok(Err(error)) => { eprintln!("microprobe: {error}");std::process::exit(1); }
        Err(_) => { eprintln!("microprobe assertion failed");std::process::exit(1); }
    }
}
