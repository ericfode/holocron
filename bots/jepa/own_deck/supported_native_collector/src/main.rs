//! Supported-only transition collection: two complete existing leader definitions.
//! No game loop, search, optimizer, opponent, network, or hidden-card sampling.
use kessel::{model::{Card, CardId, Decision}, Action, Engine, Seat, State};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{env, fs, io::Write, path::{Path, PathBuf}, process::Command, time::Instant};

const SOURCE: &str = "/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source";
const REVISION: &str = "c7ee39554901278cee70f61fd8b26fb1920696b3";
const MAX_APPLY: usize = 64;
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

fn cid(id: CardId) -> String { format!("c{}", id - 1) }

struct Fixture {
    state: State, source: CardId, resource: CardId, chosen: CardId,
    own_base: CardId, opponent_base: CardId, first_unit: CardId, second_unit: CardId,
}

fn fixture(e: &Engine, code: &str, family: usize) -> Fixture {
    let mut s = State { hidden_history_exact: true, ..State::default() };
    for (seat, leader) in [(Seat::P1, code), (Seat::P2, "IBH_053")] {
        let base = add(e, &mut s, seat, "ASH_019");
        let leader = add(e, &mut s, seat, leader);
        s.player_mut(seat).base = base;
        s.player_mut(seat).leader = leader;
    }
    let source = s.player(Seat::P1).leader;
    let own_base = s.player(Seat::P1).base;
    let opponent_base = s.player(Seat::P2).base;
    let resource = add(e, &mut s, Seat::P1, "LOF_256");
    s.player_mut(Seat::P1).resources.push(resource).unwrap();
    s.card_mut(resource).exhausted = family == 1 || family == 6;
    s.card_mut(source).exhausted = family == 2 || family == 7;
    let first_unit = unit(e, &mut s, if family == 4 || family == 7 { Seat::P1 } else { Seat::P2 },
        if family == 3 || family == 6 { 3 } else if family == 4 { 0 } else if family == 7 { 1 } else { 2 });
    let second_unit = unit(e, &mut s, Seat::P2, if family == 3 || family == 6 { 2 } else { 3 });
    if family == 4 { s.card_mut(own_base).damage = 29; }
    if family == 5 { s.card_mut(opponent_base).damage = 29; }
    if family == 7 { s.card_mut(own_base).damage = 2; }
    let chosen = if code == "ASH_011" || family == 3 || family == 6 { first_unit }
        else if family == 4 || family == 7 { own_base } else { opponent_base };
    Fixture { state: s, source, resource, chosen, own_base, opponent_base, first_unit, second_unit }
}

fn offered_card(e: &Engine, s: &State, id: CardId) -> Option<Action> {
    e.legal_actions(s).into_iter().find(|a| a.id() == Some(id))
}

fn capture(e: &Engine, s: &State) -> Value {
    json!({"decision":format!("{:?}",s.decision),"actor":s.actor(),
        "sourceInstance":if s.source==0 {Value::Null}else{json!(cid(s.source))},
        "abilityProgramPlusOne":s.ability_program,"abilityPc":s.ability_pc,
        "abilityCommitted":s.ability_committed,"state":e.snapshot(s),
        "offeredActions":e.legal_actions(s),"terminal":s.is_terminal()})
}

struct Budget { started: Instant, calls: usize, trace_path: PathBuf, context: String }
impl Budget {
    fn trace(&self, row: &Value) -> Result<(), String> {
        let mut f = fs::OpenOptions::new().append(true).open(&self.trace_path).map_err(|e|e.to_string())?;
        serde_json::to_writer(&mut f,row).map_err(|e|e.to_string())?;
        f.write_all(b"\n").and_then(|_|f.flush()).and_then(|_|f.sync_all()).map_err(|e|e.to_string())
    }
    fn apply(&mut self, e: &Engine, s: &State, a: &Action, branch: &str) -> Result<State, String> {
        if self.calls >= MAX_APPLY || self.started.elapsed().as_secs() >= MAX_SECONDS {
            return Err("supported transition/time guard reached".into());
        }
        if !e.legal_actions(s).contains(a) { return Err("attempted unoffered action".into()); }
        self.trace(&json!({"phase":"beforeApply","applyCall":self.calls+1,"context":self.context,
            "branch":branch,"before":capture(e,s),"offeredAction":a}))?;
        self.calls += 1;
        let result=e.apply(s,a);
        let row=match &result {
            Ok(after)=>json!({"phase":"afterApply","applyCall":self.calls,"context":self.context,"branch":branch,"after":capture(e,after)}),
            Err(error)=>json!({"phase":"applyError","applyCall":self.calls,"context":self.context,"branch":branch,"error":error}),
        };
        self.trace(&row)?;
        result
    }
}

fn ready_resources(s: &State) -> i64 {
    s.player(Seat::P1).resources.iter().filter(|id| !s.card(**id).exhausted).count() as i64
}

fn run_case(e: &Engine, budget: &mut Budget, code: &str, family: usize) -> Result<Value,String> {
    let f=fixture(e,code,family);
    let s=f.state;
    budget.context=format!("{code}-family-{family}");
    let imported=e.load_state(&e.snapshot(&s))?;
    if e.snapshot(&s)!=e.snapshot(&imported) || e.legal_actions(&s)!=e.legal_actions(&imported) {
        return Err("public fixture import changed state or legal actions".into());
    }
    let mut row=json!({"card":code,"abilityPath":["abilities","leader",0],"context_family":family,
        "context_group":format!("family-{family}"),"partition":if family<5 {"train"}else{"val"},
        "refs":{"source":cid(f.source),"resource":cid(f.resource),"chosen":cid(f.chosen),
            "own_base":cid(f.own_base),"opponent_base":cid(f.opponent_base),"first_unit":cid(f.first_unit),"second_unit":cid(f.second_unit)},
        "before":capture(e,&s),"sourceAction":null,"targetPrompt":null,"cancelAction":null,"cancelled":null,
        "targetAction":null,"after":null,"followupPass":null,"following":null,
        "targets":{"source_use":0,"target_allowed":0,"cost_resource":0,"damage_delta":0,"source_exhausted_after":0,"followup_source_offered":0,"terminal":0},
        "target_mask":{"source_use":true,"target_allowed":false,"cost_resource":false,"damage_delta":false,"source_exhausted_after":false,"followup_source_offered":false,"terminal":false},
        "label_origin":"native public Engine legal_actions and actual apply counters only; masked values are placeholders"});
    if let Some(source_action)=offered_card(e,&s,f.source) {
        row["targets"]["source_use"]=json!(1);
        row["sourceAction"]=json!(source_action);
        let prompt=budget.apply(e,&s,&source_action,"source")?;
        if prompt.decision!=Decision::AbilityTarget || prompt.source!=f.source || prompt.ability_program==0 {
            return Err("existing leader action did not bind its actual target program".into());
        }
        row["targetPrompt"]=capture(e,&prompt);
        row["target_mask"]["target_allowed"]=json!(true);
        row["targets"]["target_allowed"]=json!(offered_card(e,&prompt,f.chosen).is_some() as u8);
        row["candidate_target_masks"]=json!({"own_base":offered_card(e,&prompt,f.own_base).is_some(),
            "opponent_base":offered_card(e,&prompt,f.opponent_base).is_some(),
            "first_unit":offered_card(e,&prompt,f.first_unit).is_some(),"second_unit":offered_card(e,&prompt,f.second_unit).is_some()});
        let cancel=e.legal_actions(&prompt).into_iter().find(|a|a.kind=="button"&&a.arg.as_ref().and_then(Value::as_str)==Some("cancel"))
            .ok_or("expected existing precommit cancellation action")?;
        let cancelled=budget.apply(e,&prompt,&cancel,"cancel-independent-branch")?;
        row["cancelAction"]=json!(cancel);
        row["cancelled"]=capture(e,&cancelled);
        if e.snapshot(&cancelled)!=e.snapshot(&s) || e.legal_actions(&cancelled)!=e.legal_actions(&s) {
            return Err("precommit cancellation changed fixture or legal actions".into());
        }
        if let Some(target_action)=offered_card(e,&prompt,f.chosen) {
            // Commit from the untouched prompt, never from the cancelled branch.
            let after=budget.apply(e,&prompt,&target_action,"commit-independent-branch")?;
            row["targetAction"]=json!(target_action);
            row["after"]=capture(e,&after);
            row["targets"]["cost_resource"]=json!(ready_resources(&s)-ready_resources(&after));
            row["targets"]["damage_delta"]=json!(i64::from(after.card(f.chosen).damage)-i64::from(s.card(f.chosen).damage));
            row["targets"]["source_exhausted_after"]=json!(after.card(f.source).exhausted as u8);
            row["targets"]["terminal"]=json!(after.is_terminal() as u8);
            for name in ["cost_resource","damage_delta","source_exhausted_after","terminal"] { row["target_mask"][name]=json!(true); }
            if !after.is_terminal() {
                if let Some(pass)=e.legal_actions(&after).into_iter().find(|a|a.kind=="button"&&a.arg.as_ref().and_then(Value::as_str)==Some("pass")) {
                    let following=budget.apply(e,&after,&pass,"followup-offered-pass")?;
                    row["followupPass"]=json!(pass);
                    row["following"]=capture(e,&following);
                    if following.active==Seat::P1 {
                        row["target_mask"]["followup_source_offered"]=json!(true);
                        row["targets"]["followup_source_offered"]=json!(offered_card(e,&following,f.source).is_some() as u8);
                    }
                }
            }
        }
    }
    budget.trace(&json!({"phase":"contextComplete","context":budget.context,"applyCalls":budget.calls,"case":row}))?;
    Ok(row)
}

fn run() -> Result<Value,String> {
    source_preflight()?;
    let started=Instant::now();
    let mut catalogue=kessel::catalogue_io::load_catalogue_value(&Path::new(SOURCE).join("compiler/generated"))?;
    let full=catalogue["cards"].as_array().ok_or("catalogue missing cards")?;
    let mut programs=serde_json::Map::new();
    let mut provenance=vec![];
    for (code,hash) in [("ASH_011","c8deebf53ed30519ed4b4abe6b274f1c460997a55b209174e28125f3cec7752f"),
        ("IBH_053","93cdf6459ac9de34369a172aec6a2729cb608c749f6a0bd847ccea8656987c41")] {
        let entry=full.iter().find(|c|c["setCode"]==code).ok_or("missing existing definition")?;
        if entry["sourceHash"]!=hash || entry["abilities"]["leader"].as_array().map(|v|v.len())!=Some(1) {
            return Err("existing actual whole-card ability binding changed".into());
        }
        programs.insert(code.into(),json!({"ability_path":["abilities","leader",0],"source_hash":hash,
            "source_path":entry["sourcePath"],"program":entry["abilities"]["leader"][0]}));
        provenance.push(json!({"card":code,"sourceHash":hash,"sourcePath":entry["sourcePath"],
            "abilityPath":["abilities","leader",0],"actualUnmodifiedAbility":entry["abilities"]["leader"][0]}));
    }
    let shield=full.iter().find(|c|c["setCode"]=="TOKEN_SHIELD").ok_or("canonical Shield row missing")?;
    if shield["sourceHash"]!="39f1c6699c36ba309a8fe8e053f9b94ddbb8877991767b6664fcd88d447be91f" || shield["status"]!="unsupported" {
        return Err("reviewed exact native token row changed".into());
    }
    catalogue["cards"].as_array_mut().unwrap().retain(|c|c["setCode"].as_str().is_some_and(|v|SELECTED.contains(&v)));
    let catalogue_sha=format!("{:x}",Sha256::digest(serde_json::to_vec(&catalogue).unwrap()));
    let engine=Engine::from_catalogue_value(&catalogue)?;
    for code in SELECTED { if !engine.definitions.iter().any(|d|d.code==code) { return Err(format!("whole card rejected: {code}")); } }
    let trace_path=PathBuf::from(env::var("SUPPORTED_NATIVE_TRACE").map_err(|_|"SUPPORTED_NATIVE_TRACE required")?);
    let mut trace=fs::OpenOptions::new().write(true).create_new(true).open(&trace_path).map_err(|e|e.to_string())?;
    serde_json::to_writer(&mut trace,&json!({"schema":"supported-native-apply-journal/1","sourceRevision":REVISION,
        "selectedWholeCards":SELECTED,"maxApplyCalls":MAX_APPLY,"contextCount":16})).map_err(|e|e.to_string())?;
    trace.write_all(b"\n").and_then(|_|trace.flush()).and_then(|_|trace.sync_all()).map_err(|e|e.to_string())?;
    drop(trace);
    let mut budget=Budget { started,calls:0,trace_path,context:String::new() };
    let mut cases=vec![];
    for family in 0..8 { for code in ["ASH_011","IBH_053"] { cases.push(run_case(&engine,&mut budget,code,family)?); } }
    source_preflight()?;
    Ok(json!({"schema":"jepa-supported-native-transitions/1","sourceRevision":REVISION,
        "selectedCatalogueSha256":catalogue_sha,"selectedWholeCards":SELECTED,"programs":programs,"provenance":provenance,
        "actualCardAbilitiesInSyntheticPublicStates":true,"forcetekiOracleRun":false,"noHiddenCardsOrDrawOrder":true,
        "applyCalls":budget.calls,"maxApplyCalls":MAX_APPLY,"elapsedSeconds":started.elapsed().as_secs_f64(),
        "contextSplit":{"train_families":[0,1,2,3,4],"val_families":[5,6,7],"heldout_card_ids":false,"all_branches_grouped_across_cards":true},
        "limitations":["Only two already bound whole-card leader abilities; held-out contexts, no unseen-card generalization.",
            "Synthetic public microstates, native supported semantics only; no Forceteki oracle, full game, opponent, policy or playing-strength evidence.",
            "Only synthetic boundary-context generalization; friendly-base terminal-positive train and enemy-base terminal-positive validation are predeclared."],"cases":cases}))
}

fn main() {
    let args:Vec<_>=env::args().collect();
    if args.len()!=2 { eprintln!("usage: supported-native-collector NEW_RECEIPT.json");std::process::exit(2); }
    let outcome=std::thread::Builder::new().stack_size(64*1024*1024).spawn(run).expect("collector worker").join();
    match outcome {
        Ok(Ok(receipt))=>{
            let mut file=fs::OpenOptions::new().write(true).create_new(true).open(&args[1]).expect("new receipt path");
            serde_json::to_writer_pretty(&mut file,&receipt).unwrap();
            file.write_all(b"\n").and_then(|_|file.flush()).and_then(|_|file.sync_all()).unwrap();
            println!("{}",json!({"ok":true,"receipt":args[1],"applyCalls":receipt["applyCalls"],"contexts":16}));
        }
        Ok(Err(error))=>{eprintln!("collector: {error}");std::process::exit(1);}
        Err(_)=>{eprintln!("collector assertion failed");std::process::exit(1);}
    }
}

