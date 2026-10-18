//! Synthetic elementary IR in the unchanged pinned native runtime.
//! No actual-card, compiler-conformance, hidden-information or strength claim.
use kessel::{model::{Card,CardId,Decision},Action,Engine,Seat,State};
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{env,fs,io::Write,path::{Path,PathBuf},process::Command,time::Instant};

const SOURCE:&str="/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source";
const REVISION:&str="c7ee39554901278cee70f61fd8b26fb1920696b3";
const MAX_APPLY:usize=512;
const MAX_SECONDS:u64=30;
type Refs=Vec<(String,CardId)>;

fn source_preflight()->Result<(),String>{
    let revision=Command::new("git").env("GIT_OPTIONAL_LOCKS","0").args(["-C",SOURCE,"rev-parse","HEAD"]).output().map_err(|e|e.to_string())?;
    if !revision.status.success()||String::from_utf8_lossy(&revision.stdout).trim()!=REVISION{return Err("pinned source revision mismatch".into());}
    let clean=Command::new("git").env("GIT_OPTIONAL_LOCKS","0").args(["-C",SOURCE,"diff","--quiet","HEAD","--","crates/kessel","compiler/generated","Cargo.toml","Cargo.lock"]).status().map_err(|e|e.to_string())?;
    if !clean.success(){return Err("pinned native source changed".into());}Ok(())
}
fn cid(id:CardId)->String{format!("c{}",id-1)}
fn find(refs:&Refs,role:&str)->Result<CardId,String>{refs.iter().find(|(r,_)|r==role).map(|(_,id)|*id).ok_or_else(||format!("missing physical role {role}"))}
fn add(e:&Engine,s:&mut State,owner:Seat,code:&str)->Result<CardId,String>{
    let def=e.definitions.iter().position(|d|d.code==code).ok_or_else(||format!("definition not admitted {code}"))? as u16;
    if s.next_id as usize>=kessel::model::MAX_CARDS{return Err("physical card capacity".into());}
    let id=s.next_id;s.next_id+=1;*s.card_mut(id)=Card{present:true,def,owner,..Card::default()};Ok(id)
}
fn unit(e:&Engine,s:&mut State,owner:Seat,code:&str)->Result<CardId,String>{
    let id=add(e,s,owner,code)?;let space=e.definitions[s.card(id).def as usize].info.arena.as_deref()==Some("space");
    if space{s.player_mut(owner).space.push(id)?;}else{s.player_mut(owner).ground.push(id)?;}
    s.arena_unit_order[usize::from(space)].push(id)?;s.registration_order.push(id)?;Ok(id)
}
fn zone(s:&State,id:CardId)->&'static str{
    for owner in [Seat::P1,Seat::P2]{let p=s.player(owner);
        if p.base==id{return "base";}if p.leader==id{return "leader";}if p.ground.contains(id){return "ground";}if p.space.contains(id){return "space";}
        if p.hand.contains(id){return "hand";}if p.resources.contains(id){return "resource";}if p.discard.contains(id){return "discard";}
    }if s.card(id).present&&s.card(id).parent!=0{return "upgrade";}"absent"
}
fn native_card<'a>(wire:&'a Value,id:CardId)->Option<&'a Value>{
    let name=cid(id);for owner in ["p1","p2"]{let p=&wire["players"][owner];
        for z in ["base","leader"]{if p[z]["id"]==name{return Some(&p[z]);}}
        for z in ["ground","space","hand","resources","discard"]{if let Some(cards)=p[z].as_array(){for c in cards{if c["id"]==name{return Some(c);}}}}
    }None
}
fn token_count(s:&State,mut id:CardId)->Result<usize,String>{
    let mut seen=vec![];while id!=0{if id>=s.next_id||seen.contains(&id){return Err("invalid token chain".into());}seen.push(id);id=s.card(id).next_token;}Ok(seen.len())
}
fn settled(s:&State)->bool{
    s.is_terminal()||(s.decision==Decision::Window&&s.ability_program==0&&s.death_depth==0&&s.death_pending.len==0&&s.death_window.len==0
        &&s.pending_programs==0&&s.pending_triggers==0&&s.after_attack_triggers==0&&s.after_attack_programs==0&&!s.event_group.active&&!s.support.pending)
}
fn projection(e:&Engine,s:&State,wire:&Value,id:CardId,plan:&Value)->Result<Value,String>{
    let c=s.card(id);let d=&e.definitions[c.def as usize];let z=zone(s,id);let unit=d.info.is("unit")&&["ground","space"].contains(&z);let base=d.info.is("base");
    let card=native_card(wire,id);let hp=card.and_then(|v|v["hp"].as_i64()).or(d.info.hp.map(i64::from));let power=card.and_then(|v|v["power"].as_i64()).or(d.info.power.map(i64::from));
    let printed=&plan["selected_whole_rows"][d.code.as_str()]["card"];
    if !printed.is_object(){return Err("missing complete public definition row".into());}
    Ok(json!({"id":cid(id),"code":d.code,"owner":c.owner.as_str(),"zone":z,"present":c.present,"in_arena":unit,"attackable":unit||base,
        "is_unit":d.info.is("unit"),"is_base":base,"damage":c.damage,"hp":hp.unwrap_or(0),"power":power.unwrap_or(0),"exhausted":c.exhausted,
        "shield_count":token_count(s,c.shield)?,"xp_count":token_count(s,c.experience)?,"printed_cost":printed["cost"],"printed_traits":printed["traits"],
        "printed_aspects":printed["aspects"],"printed_types":printed["types"],"printed_unique":printed["unique"],
        "known":{"identity":c.present,"owner":c.present,"damage":c.present&&(unit||base),"hp":c.present&&(unit||base)&&hp.is_some(),
            "power":c.present&&unit&&power.is_some(),"exhausted":c.present&&unit,"shield_count":c.present&&unit,"xp_count":c.present&&unit,
            "printed_cost":printed["cost"].is_number(),"printed_traits":printed["traits"].is_array(),"printed_aspects":printed["aspects"].is_array()}}))
}
fn privacy(s:&State,refs:&Refs)->Result<(),String>{
    let source=find(refs,"source")?;
    for owner in [Seat::P1,Seat::P2]{let p=s.player(owner);
        if p.deck.len!=0||(owner==Seat::P2&&(p.hand.len!=0||p.resources.len!=0)){return Err("private fixture piles must stay empty".into());}
    }
    if s.player(Seat::P1).hand.as_slice().iter().any(|id|*id!=source){return Err("own hand contains an undeclared source".into());}Ok(())
}
fn capture(e:&Engine,s:&State,refs:&Refs,plan:&Value)->Result<Value,String>{
    privacy(s,refs)?;let wire=e.snapshot(s);let mut projections=serde_json::Map::new();
    for(role,id)in refs{projections.insert(role.clone(),projection(e,s,&wire,*id,plan)?);}
    Ok(json!({"state":wire,"projections":projections,"offeredActions":e.legal_actions(s),"decision":format!("{:?}",s.decision),"actor":s.actor(),
        "sourceInstance":if s.source==0{Value::Null}else{json!(cid(s.source))},"abilityProgramPlusOne":s.ability_program,"abilityPc":s.ability_pc,
        "abilityCommitted":s.ability_committed,"terminal":s.is_terminal(),"settled":settled(s),
        "settlement":{"decision":format!("{:?}",s.decision),"ability_program":s.ability_program,"death_depth":s.death_depth,
            "death_pending":s.death_pending.len,"death_window":s.death_window.len,"pending_programs":s.pending_programs,"pending_triggers":s.pending_triggers,
            "after_attack_triggers":s.after_attack_triggers,"after_attack_programs":s.after_attack_programs,"event_group_active":s.event_group.active,"support_pending":s.support.pending}}))
}
fn fixture(e:&Engine,world:&Value,plan:&Value)->Result<(State,Refs),String>{
    let mut s=State{hidden_history_exact:true,..State::default()};let h=&plan["helpers"];
    for owner in [Seat::P1,Seat::P2]{let base=add(e,&mut s,owner,h["base"].as_str().ok_or("base code")?)?;let leader=add(e,&mut s,owner,h["leader"].as_str().ok_or("leader code")?)?;
        s.player_mut(owner).base=base;s.player_mut(owner).leader=leader;}
    let source=add(e,&mut s,Seat::P1,world["source_code"].as_str().ok_or("source code")?)?;s.player_mut(Seat::P1).hand.push(source)?;
    let mut refs=vec![("source".into(),source)];
    let roles=plan["candidate_order"].as_array().ok_or("candidate order")?;if roles.len()!=16{return Err("exact sixteen candidate units required".into());}
    for role in roles{let role=role.as_str().ok_or("role string")?;let spec=&world["arena_cards"][role];
        let owner=match spec["owner"].as_str(){Some("p1")=>Seat::P1,Some("p2")=>Seat::P2,_=>return Err("unit owner".into())};
        let id=unit(e,&mut s,owner,spec["code"].as_str().ok_or("unit code")?)?;
        let damage=spec["damage"].as_u64().ok_or("unit damage")?;if damage>=10{return Err("initial dead synthetic unit".into());}
        s.card_mut(id).damage=damage as u16;s.card_mut(id).exhausted=spec["exhausted"].as_bool().ok_or("unit exhaustion")?;
        refs.push((role.into(),id));
    }
    refs.push(("own_base".into(),s.player(Seat::P1).base));refs.push(("opponent_base".into(),s.player(Seat::P2).base));
    let ready=world["ready_resources"].as_u64().ok_or("resource count")?;if ready!=4{return Err("fixed four funded resources required".into());}
    for _ in 0..ready{let id=add(e,&mut s,Seat::P1,h["resource"].as_str().ok_or("resource code")?)?;s.player_mut(Seat::P1).resources.push(id)?;}
    privacy(&s,&refs)?;Ok((s,refs))
}
fn offered(e:&Engine,s:&State,id:CardId)->Result<Option<Action>,String>{
    let actions:Vec<_>=e.legal_actions(s).into_iter().filter(|a|a.id()==Some(id)).collect();
    if actions.len()>1{return Err("ambiguous offered card action".into());}Ok(actions.first().cloned())
}
fn validate_fixtures(e:&Engine,plan:&Value)->Result<Vec<Value>,String>{
    let worlds=plan["worlds"].as_array().ok_or("worlds")?;if worlds.len()!=128{return Err("exact128 roots required".into());}
    let programs=plan["programs"].as_array().ok_or("programs")?;if programs.len()!=32{return Err("exact32 programs required".into());}
    for (i,p)in programs.iter().enumerate(){if p["index"].as_u64()!=Some(i as u64)||!e.definitions.iter().any(|d|d.code==p["code"].as_str().unwrap_or("")){return Err("synthetic program rejected or misindexed".into());}}
    let mut proofs=vec![];
    for (i,w)in worlds.iter().enumerate(){if w["id"].as_u64()!=Some(i as u64)||w["max_applies"]!=4{return Err("world ID/per-root bound".into());}
        let(s,refs)=fixture(e,w,plan)?;if !settled(&s){return Err("initial fixture is not settled".into());}
        let snapshot=e.snapshot(&s);let loaded=e.load_state(&snapshot)?;
        if snapshot!=e.snapshot(&loaded)||e.legal_actions(&s)!=e.legal_actions(&loaded){return Err("public fixture snapshot/load mismatch".into());}
        if offered(e,&s,find(&refs,"source")?)?.is_none(){return Err("funded source play unavailable".into());}
        for(_,id)in &refs{if s.card(*id).shield!=0||s.card(*id).experience!=0||s.card(*id).upgrades!=0{return Err("unplanned physical attachment/token".into());}}
        let before=capture(e,&s,&refs,plan)?;
        proofs.push(json!({"world_id":i,"card":w["source_code"],"publicSnapshotRoundtripExact":true,"legalActionsRoundtripExact":true,
            "allProgramsAdmitted":true,"before":before,"applyCalls":0,"actionsApplied":0}));
    }Ok(proofs)
}
struct Budget{started:Instant,calls:usize,path:PathBuf,context:String}
impl Budget{
    fn trace(&self,row:&Value)->Result<(),String>{let mut f=fs::OpenOptions::new().append(true).open(&self.path).map_err(|e|e.to_string())?;
        serde_json::to_writer(&mut f,row).map_err(|e|e.to_string())?;f.write_all(b"\n").and_then(|_|f.flush()).and_then(|_|f.sync_all()).map_err(|e|e.to_string())}
    fn apply(&mut self,e:&Engine,s:&State,a:&Action,refs:&Refs,plan:&Value,stage:&str)->Result<State,String>{
        if self.calls>=MAX_APPLY||self.started.elapsed().as_secs()>=MAX_SECONDS{return Err("native global quota reached".into());}
        if !e.legal_actions(s).contains(a){return Err("unoffered action rejected before apply".into());}
        self.trace(&json!({"phase":"beforeApply","applyCall":self.calls+1,"context":self.context,"branch":stage,"before":capture(e,s,refs,plan)?,"offeredAction":a}))?;
        self.calls+=1;let result=e.apply(s,a);
        self.trace(&match &result{Ok(t)=>json!({"phase":"afterApply","applyCall":self.calls,"context":self.context,"branch":stage,"after":capture(e,t,refs,plan)?}),
            Err(error)=>json!({"phase":"applyError","applyCall":self.calls,"context":self.context,"branch":stage,"error":error})})?;
        result.map_err(|error|format!("NATIVE_APPLY_ERROR: {error}"))
    }
}
fn run_case(e:&Engine,b:&mut Budget,world:&Value,plan:&Value)->Result<Value,String>{
    let(mut s,refs)=fixture(e,world,plan)?;let start=b.calls;let code=world["source_code"].as_str().ok_or("source code")?;
    b.context=format!("world-{}-{code}",world["id"]);let intent=world["intent_ref"].as_str().ok_or("intent")?;let intended=find(&refs,intent)?;
    let source=find(&refs,"source")?;let play=offered(e,&s,source)?.ok_or("funded source action unavailable")?;
    let refmap=refs.iter().map(|(role,id)|(role.clone(),json!(cid(*id)))).collect::<serde_json::Map<_,_>>();
    let mut row=json!({"world_id":world["id"],"card":code,"program_index":world["program_index"],"root_variant":world["root_variant"],"partition":world["partition"],
        "refs":refmap,"declared_intent":{"ref":intent,"id":cid(intended),"requires_target":true},"observation_refs":plan["candidate_order"],
        "before":capture(e,&s,&refs,plan)?,"publicSnapshotRoundtripExact":true,"playAction":play,"targetPrompt":null,"targetAction":null,"declineAction":null,
        "steps":[],"final":null,"intentOffered":null,"engineError":null,"completion":null,"intentResolution":null,"terminalClassification":null});
    let mut next=Some((play,"play-own-hand"));let mut selected=false;let mut declined=false;
    while let Some((action,stage))=next.take(){
        if b.calls-start>=4{row["completion"]=json!("per-root-apply-cap-unsettled");break;}
        let before=capture(e,&s,&refs,plan)?;
        match b.apply(e,&s,&action,&refs,plan,stage){
            Ok(t)=>{s=t;row["steps"].as_array_mut().unwrap().push(json!({"stage":stage,"before":before,"action":action,"after":capture(e,&s,&refs,plan)?}));},
            Err(error)if error.starts_with("NATIVE_APPLY_ERROR: ")=>{row["engineError"]=json!(error);row["completion"]=json!("native-error");break;},
            Err(error)=>return Err(error),
        }
        if stage=="chosen-target"{selected=true;}if stage=="decline-unoffered-target"{declined=true;}
        if settled(&s){row["final"]=capture(e,&s,&refs,plan)?;row["completion"]=json!("settled");break;}
        if s.decision!=Decision::AbilityTarget||!row["targetPrompt"].is_null()||selected||declined{
            row["completion"]=json!(format!("unreviewed-continuation-{:?}",s.decision));break;
        }
        row["targetPrompt"]=capture(e,&s,&refs,plan)?;
        if let Some(choice)=offered(e,&s,intended)?{row["intentOffered"]=json!(true);row["targetAction"]=json!(choice);next=Some((choice,"chosen-target"));}
        else{
            row["intentOffered"]=json!(false);
            let cancel:Vec<_>=e.legal_actions(&s).into_iter().filter(|a|a.id().is_none()&&a.arg.as_ref().and_then(Value::as_str)==Some("cancel")&&a.label=="Cancel").collect();
            if cancel.len()>1{return Err("ambiguous actual Cancel".into());}
            if let Some(action)=cancel.first(){row["declineAction"]=json!(action);next=Some((action.clone(),"decline-unoffered-target"));}
            else{row["completion"]=json!("unoffered-observation-only");break;}
        }
    }
    row["applyCalls"]=json!(b.calls-start);row["intendedTargetCommitted"]=json!(selected);
    row["intentResolution"]=if selected{json!("committed")}else if declined{json!("unoffered-declined")}else if row["completion"]=="unoffered-observation-only"{json!("unoffered-observation-only")}else{Value::Null};
    row["terminalClassification"]=if row["completion"]=="settled"&&selected{json!("settled-committed")}else if row["completion"]=="settled"&&declined{json!("settled-cancelled")}else if row["completion"]=="unoffered-observation-only"{json!("unoffered-prompt-only")}else{Value::Null};
    row["lastObserved"]=capture(e,&s,&refs,plan)?;b.trace(&json!({"phase":"contextComplete","context":b.context,"case":row,"applyCalls":b.calls}))?;Ok(row)
}
fn complete(case:&Value)->bool{
    case["engineError"].is_null()&&((case["completion"]=="settled"&&(case["intentResolution"]=="committed"||case["intentResolution"]=="unoffered-declined"))
        ||(case["completion"]=="unoffered-observation-only"&&case["intentOffered"]==false&&case["final"].is_null()))
}
fn run(plan_path:&Path,journal_path:&Path)->Result<Value,String>{
    source_preflight()?;let started=Instant::now();let plan_bytes=fs::read(plan_path).map_err(|e|e.to_string())?;let plan:Value=serde_json::from_slice(&plan_bytes).map_err(|e|e.to_string())?;
    if plan["schema"]!="jepa-compositional-typed-plan/1"||plan["synthetic"]!=true||plan["collector_max_engine_applies"]!=512{return Err("frozen synthetic plan contract".into());}
    let mut catalogue=kessel::catalogue_io::load_catalogue_value(&Path::new(SOURCE).join("compiler/generated"))?;
    for code in ["ASH_019","IBH_053","LOF_256","TOKEN_SHIELD"]{
        let actual=catalogue["cards"].as_array().ok_or("catalogue cards")?.iter().find(|r|r["setCode"]==code).ok_or("pinned support row missing")?;
        let expected=&plan["selected_whole_rows"][code];
        for(key,value)in expected.as_object().ok_or("expected support row")?{if actual[key]!=*value{return Err(format!("support definition changed {code}.{key}"));}}
    }
    let selected=plan["selected_whole_cards"].as_array().ok_or("selected definition list")?;
    let mut entries=vec![];for code in selected{let code=code.as_str().ok_or("selected code")?;let row=&plan["selected_whole_rows"][code];
        if row["setCode"]!=code{return Err("selected row/code mismatch".into());}entries.push(row.clone());}
    catalogue["cards"]=json!(entries);let catalogue_hash=format!("{:x}",Sha256::digest(serde_json::to_vec(&catalogue).map_err(|e|e.to_string())?));
    let engine=Engine::from_catalogue_value(&catalogue)?;
    for code in selected{if !engine.definitions.iter().any(|d|d.code==code.as_str().unwrap_or("")){return Err(format!("complete definition was rejected: {code}"));}}
    // All128 construction/serialization/admission checks occur before the first
    // apply, inside this same native invocation and its monotonic wall budget.
    let validation=validate_fixtures(&engine,&plan)?;
    let mut journal=fs::OpenOptions::new().write(true).create_new(true).open(journal_path).map_err(|e|e.to_string())?;
    serde_json::to_writer(&mut journal,&json!({"schema":"jepa-compositional-typed-apply-journal/1","sourceRevision":REVISION,"maxApplyCalls":MAX_APPLY,
        "expectedCases":128,"planSha256":format!("{:x}",Sha256::digest(&plan_bytes))})).map_err(|e|e.to_string())?;
    journal.write_all(b"\n").and_then(|_|journal.flush()).and_then(|_|journal.sync_all()).map_err(|e|e.to_string())?;drop(journal);
    let mut budget=Budget{started,calls:0,path:journal_path.into(),context:String::new()};let mut cases=vec![];
    for world in plan["worlds"].as_array().ok_or("worlds")?{let case=run_case(&engine,&mut budget,world,&plan)?;let ok=complete(&case);cases.push(case);if !ok{break;}}
    source_preflight()?;
    Ok(json!({"schema":"jepa-compositional-typed-native/1","synthetic":true,"sourceRevision":REVISION,
        "collectionPlan":plan,"collectionPlanSha256":format!("{:x}",Sha256::digest(&plan_bytes)),"selectedCatalogueSha256":catalogue_hash,
        "candidateOrder":plan["candidate_order"],"programs":plan["programs"],"selectedWholeCards":plan["selected_whole_cards"],
        "fixtureValidation":validation,"cases":cases,"collectionComplete":cases.len()==128&&cases.iter().all(complete),
        "applyCalls":budget.calls,"maxApplyCalls":MAX_APPLY,"maxSeconds":MAX_SECONDS,"elapsedSeconds":started.elapsed().as_secs_f64(),
        "noHiddenCardsOrDrawOrder":true,"compilerConversionRun":false,"engineSourceChanged":false,"actualCardCoverageClaim":false}))
}
fn main(){
    let args:Vec<_>=env::args().collect();if args.len()!=4{eprintln!("usage: compositional-typed-native-collector PLAN NEW_RECEIPT NEW_JOURNAL");std::process::exit(2);}
    let plan=PathBuf::from(&args[1]);let output=PathBuf::from(&args[2]);let journal=PathBuf::from(&args[3]);
    if output.exists()||journal.exists(){eprintln!("exclusive new receipt/journal required");std::process::exit(2);}
    match std::thread::Builder::new().stack_size(64*1024*1024).spawn(move||run(&plan,&journal)).expect("collector worker").join(){
        Ok(Ok(receipt))=>{let mut file=fs::OpenOptions::new().write(true).create_new(true).open(output).expect("new native receipt");
            serde_json::to_writer_pretty(&mut file,&receipt).unwrap();file.write_all(b"\n").and_then(|_|file.flush()).and_then(|_|file.sync_all()).unwrap();
            println!("{}",json!({"collectionComplete":receipt["collectionComplete"],"applyCalls":receipt["applyCalls"],"cases":receipt["cases"].as_array().unwrap().len()}));},
        Ok(Err(error))=>{eprintln!("collector: {error}");std::process::exit(1);},Err(_)=>{eprintln!("collector panic");std::process::exit(1);}
    }
}
