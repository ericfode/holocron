//! Whole existing definitions, native action menus, independent public branches.
//! No engine expansion, hidden cards, full games, opponents, or synthetic labels.
use kessel::{model::{Card,CardId,Decision},Action,Engine,Seat,State};
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{env,fs,io::Write,path::{Path,PathBuf},process::Command,time::Instant};

const SOURCE:&str="/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source";
const REVISION:&str="c7ee39554901278cee70f61fd8b26fb1920696b3";
const MAX_APPLY:usize=2048;
const MAX_SECONDS:u64=180;
const SLOTS:[&str;8]=["own_base","opponent_base","friendly_ground","enemy_ground","enemy_space","friendly_imperial","friendly_creature","source"];
const TARGETS:[&str;11]=["source_use","target_allowed","cost_resource","damage_delta","source_exhausted_after","target_exhausted_delta","shield_delta","xp_delta","target_defeated","followup_source_offered","terminal"];

fn source_preflight()->Result<(),String>{
    let revision=Command::new("git").args(["-C",SOURCE,"rev-parse","HEAD"]).output().map_err(|e|e.to_string())?;
    if !revision.status.success()||String::from_utf8_lossy(&revision.stdout).trim()!=REVISION{return Err("pinned source revision mismatch".into());}
    let clean=Command::new("git").args(["-C",SOURCE,"diff","--quiet","HEAD","--","crates/kessel","compiler/generated","Cargo.toml","Cargo.lock"]).status().map_err(|e|e.to_string())?;
    if !clean.success(){return Err("pinned Kessel source changed".into());} Ok(())
}
fn cid(id:CardId)->String{format!("c{}",id-1)}
fn add(e:&Engine,s:&mut State,seat:Seat,code:&str)->CardId{
    let def=e.definitions.iter().position(|d|d.code==code).unwrap_or_else(||panic!("whole definition not admitted: {code}")) as u16;
    let id=s.next_id;s.next_id+=1;*s.card_mut(id)=Card{present:true,def,owner:seat,..Card::default()};id
}
fn unit(e:&Engine,s:&mut State,seat:Seat,code:&str)->CardId{
    let id=add(e,s,seat,code);
    let space=e.definitions[s.card(id).def as usize].info.arena.as_deref()==Some("space");
    if space{s.player_mut(seat).space.push(id).unwrap();}else{s.player_mut(seat).ground.push(id).unwrap();}
    s.arena_unit_order[usize::from(space)].push(id).unwrap();s.registration_order.push(id).unwrap();id
}
fn zone(s:&State,id:CardId)->&'static str{
    for seat in [Seat::P1,Seat::P2]{let p=s.player(seat);
        if p.base==id{return "base";}if p.ground.contains(id){return "ground";}if p.space.contains(id){return "space";}
        if p.leader==id{return "leader";}if p.discard.contains(id){return "discard";}if p.resources.contains(id){return "resource";}
    } "absent"
}
fn native_card<'a>(wire:&'a Value,id:CardId)->Option<&'a Value>{
    let name=cid(id);
    for seat in ["p1","p2"]{let p=&wire["players"][seat];for z in ["base","leader"]{if p[z]["id"]==name{return Some(&p[z]);}}
        for z in ["ground","space","discard","resources"]{if let Some(cards)=p[z].as_array(){for c in cards{if c["id"]==name{return Some(c);}}}}
    }None
}
fn token_count(s:&State,mut id:CardId)->Result<i64,String>{
    let mut count=0;while id!=0{if id>=s.next_id||count>=i64::from(s.next_id){return Err("native token list out of bounds".into());}count+=1;id=s.card(id).next_token;}Ok(count)
}
fn settled(s:&State)->bool{
    s.is_terminal()||(s.decision==Decision::Window&&s.ability_program==0&&s.death_depth==0
        &&s.death_pending.len==0&&s.death_window.len==0&&s.pending_programs==0
        &&s.pending_triggers==0&&s.after_attack_triggers==0&&s.after_attack_programs==0
        &&!s.event_group.active&&!s.support.pending)
}
fn projection(e:&Engine,s:&State,wire:&Value,id:CardId)->Result<Value,String>{
    let c=s.card(id);let info=&e.definitions[c.def as usize].info;let z=zone(s,id);
    let card=native_card(wire,id);let hp=card.and_then(|v|v["hp"].as_i64()).or(info.hp.map(i64::from));
    let power=card.and_then(|v|v["power"].as_i64()).or(info.power.map(i64::from));
    Ok(json!({"id":cid(id),"code":if c.present{json!(e.definitions[c.def as usize].code)}else{Value::Null},"zone":z,"owner":if c.present{json!(c.owner.as_str())}else{Value::Null},
        "present":c.present,"in_arena":z=="ground"||z=="space","attackable":["ground","space","base"].contains(&z),
        "is_unit":info.is("unit")||(info.is("leader")&&c.deployed),"is_base":info.is("base"),
        "damage":c.damage,"exhausted":c.exhausted,"hp":if c.present{hp.unwrap_or(0)}else{0},"power":if c.present{power.unwrap_or(0)}else{0},
        "shield_count":token_count(s,c.shield)?,"xp_count":token_count(s,c.experience)?,
        "known":{"identity":c.present,"owner":c.present,"damage":c.present,"exhausted":c.present,"hp":c.present&&hp.is_some(),"power":c.present&&power.is_some(),"shield_count":true,"xp_count":true}}))
}
fn capture(e:&Engine,s:&State,refs:&[CardId;8])->Result<Value,String>{
    let wire=e.snapshot(s);let mut projections=serde_json::Map::new();
    for (slot,id) in SLOTS.iter().zip(refs){projections.insert((*slot).into(),projection(e,s,&wire,*id)?);}
    Ok(json!({"decision":format!("{:?}",s.decision),"actor":s.actor(),"sourceInstance":if s.source==0{Value::Null}else{json!(cid(s.source))},
        "abilityProgramPlusOne":s.ability_program,"abilityPc":s.ability_pc,"abilityCommitted":s.ability_committed,
        "state":wire,"projections":projections,"offeredActions":e.legal_actions(s),"terminal":s.is_terminal(),"settled":settled(s),
        "settlement":{"decision":format!("{:?}",s.decision),"ability_program":s.ability_program,"death_depth":s.death_depth,
            "death_pending":s.death_pending.len,"death_window":s.death_window.len,"pending_programs":s.pending_programs,
            "pending_triggers":s.pending_triggers,"after_attack_triggers":s.after_attack_triggers,
            "after_attack_programs":s.after_attack_programs,"event_group_active":s.event_group.active,"support_pending":s.support.pending}}))
}
struct Fixture{state:State,refs:[CardId;8]}
fn fixture(e:&Engine,program:&Value,context:&Value,plan:&Value)->Result<Fixture,String>{
    let code=program["code"].as_str().ok_or("code missing")?;let leader=program["side"]=="leader";
    let mut s=State{hidden_history_exact:true,..State::default()};
    for seat in [Seat::P1,Seat::P2]{let base=add(e,&mut s,seat,plan["helpers"]["base"].as_str().unwrap());let l=add(e,&mut s,seat,if seat==Seat::P1&&leader{code}else{"IBH_053"});s.player_mut(seat).base=base;s.player_mut(seat).leader=l;}
    let mut refs=[0;8];refs[0]=s.player(Seat::P1).base;refs[1]=s.player(Seat::P2).base;
    refs[2]=unit(e,&mut s,Seat::P1,plan["helpers"]["ground"].as_str().unwrap());
    refs[3]=unit(e,&mut s,Seat::P2,plan["helpers"]["ground"].as_str().unwrap());
    refs[4]=unit(e,&mut s,Seat::P2,plan["helpers"]["space"].as_str().unwrap());
    refs[5]=unit(e,&mut s,Seat::P1,plan["helpers"]["imperial"].as_str().unwrap());
    refs[6]=unit(e,&mut s,Seat::P1,plan["helpers"]["creature"].as_str().unwrap());
    refs[7]=if leader{s.player(Seat::P1).leader}else{unit(e,&mut s,Seat::P1,code)};
    let ready=context["ready_resources"].as_u64().ok_or("resource count missing")?;
    for n in 0..3{let id=add(e,&mut s,Seat::P1,plan["helpers"]["ground"].as_str().unwrap());s.card_mut(id).exhausted=n>=ready;s.player_mut(Seat::P1).resources.push(id).unwrap();}
    s.card_mut(refs[7]).exhausted=context["source_exhausted"].as_bool().ok_or("source status missing")?;
    for (name,fields) in context["overrides"].as_object().ok_or("context overrides missing")?{
        let index=SLOTS.iter().position(|s|*s==name).ok_or("unknown override slot")?;
        if let Some(value)=fields["damage"].as_u64(){s.card_mut(refs[index]).damage=u16::try_from(value).map_err(|e|e.to_string())?;}
        if let Some(value)=fields["exhausted"].as_bool(){s.card_mut(refs[index]).exhausted=value;}
    }
    Ok(Fixture{state:s,refs})
}
fn offered(e:&Engine,s:&State,id:CardId)->Option<Action>{e.legal_actions(s).into_iter().find(|a|a.id()==Some(id))}
fn cancellation(e:&Engine,s:&State)->Option<Action>{e.legal_actions(s).into_iter().find(|a|a.label=="Cancel"||a.arg.as_ref().and_then(Value::as_str)==Some("cancel"))}
fn ready_resources(s:&State)->i64{s.player(Seat::P1).resources.as_slice().iter().filter(|id|!s.card(**id).exhausted).count() as i64}
struct Budget{started:Instant,calls:usize,path:PathBuf,context:String}
impl Budget{
    fn trace(&self,row:&Value)->Result<(),String>{let mut f=fs::OpenOptions::new().append(true).open(&self.path).map_err(|e|e.to_string())?;serde_json::to_writer(&mut f,row).map_err(|e|e.to_string())?;f.write_all(b"\n").and_then(|_|f.flush()).and_then(|_|f.sync_all()).map_err(|e|e.to_string())}
    fn check(&self)->Result<(),String>{if self.calls>=MAX_APPLY||self.started.elapsed().as_secs()>=MAX_SECONDS{return Err("grounded native apply/time quota reached".into());}Ok(())}
    fn apply(&mut self,e:&Engine,s:&State,a:&Action,refs:&[CardId;8],branch:&str)->Result<State,String>{
        self.check()?;if !e.legal_actions(s).contains(a){return Err("attempted unoffered native action".into());}
        self.trace(&json!({"phase":"beforeApply","applyCall":self.calls+1,"context":self.context,"branch":branch,"before":capture(e,s,refs)?,"offeredAction":a}))?;
        self.calls+=1;let result=e.apply(s,a);
        let row=match &result{Ok(t)=>json!({"phase":"afterApply","applyCall":self.calls,"context":self.context,"branch":branch,"after":capture(e,t,refs)?}),Err(error)=>json!({"phase":"applyError","applyCall":self.calls,"context":self.context,"branch":branch,"error":error})};self.trace(&row)?;result.map_err(|error|format!("NATIVE_APPLY_ERROR: {error}"))
    }
}
fn run_case(e:&Engine,b:&mut Budget,program:&Value,context:&Value,plan:&Value)->Result<Value,String>{
    let f=fixture(e,program,context,plan)?;let s=f.state;let refs=f.refs;
    let code=program["code"].as_str().unwrap();b.context=format!("{code}-family-{}",context["id"]);
    let imported=e.load_state(&e.snapshot(&s))?;
    if e.snapshot(&s)!=e.snapshot(&imported)||e.legal_actions(&s)!=e.legal_actions(&imported){return Err("public fixture roundtrip changed state or legal actions".into());}
    let mut ref_map=serde_json::Map::new();for (slot,id) in SLOTS.iter().zip(refs){ref_map.insert((*slot).into(),json!(cid(id)));}
    let before=capture(e,&s,&refs)?;
    let mut row=json!({"card":code,"abilityPath":["abilities",program["side"],program["index"]],"context_family":context["id"],"context_group":format!("family-{}",context["id"]),"identity_partition":program["partition"],"state_partition":context["partition"],
        "refs":ref_map,"before":before,"sourceAction":null,"sourceOpened":null,"menuAction":null,"postActivation":null,"activationCompletion":"not-offered","targetPrompt":null,"cancelAction":null,"cancelled":null,"queries":[],"source_use":false,"source_use_known":true});
    let mut target_prompt=None;let mut available=false;
    if let Some(source_action)=offered(e,&s,refs[7]){
        let mut opened=b.apply(e,&s,&source_action,&refs,"source-card")?;row["sourceAction"]=json!(source_action);row["sourceOpened"]=capture(e,&opened,&refs)?;
        if opened.decision==Decision::AbilityMenu{
            let choices:Vec<_>=e.legal_actions(&opened).into_iter().filter(|a|a.label!="Attack"&&a.label!="Cancel").collect();
            if choices.len()>1{return Err("selected whole-card active side has ambiguous available actions".into());}
            if let Some(action)=choices.first(){if action.arg.as_ref().and_then(Value::as_u64)!=Some(0){return Err("sole existing unit menu action has unexpected index".into());}
                let next=b.apply(e,&opened,action,&refs,"sole-ability-menu")?;row["menuAction"]=json!(action);opened=next;available=true;
            }
        }else if opened.decision==Decision::AbilityTarget||opened.decision==Decision::AbilityNoEffect
            ||(program["side"]=="leader"&&settled(&opened)&&!opened.card(refs[7]).deployed){available=true;}
        row["postActivation"]=capture(e,&opened,&refs)?;
        if available&&!settled(&opened)&&(opened.source!=refs[7]||opened.ability_program==0){return Err("actual selected ability did not bind expected source program".into());}
        if available&&opened.decision==Decision::AbilityTarget{row["targetPrompt"]=capture(e,&opened,&refs)?;target_prompt=Some(opened);row["activationCompletion"]=json!("target-prompt");}
        else{row["activationCompletion"]=json!(if available&&settled(&opened){"finished-without-target"}else if available{"pending-without-target"}else{"attack-only"});}
        if let Some(cancel)=cancellation(e,&opened){let cancelled=b.apply(e,&opened,&cancel,&refs,"cancel-independent-branch")?;row["cancelAction"]=json!(cancel);row["cancelled"]=capture(e,&cancelled,&refs)?;
            if e.snapshot(&cancelled)!=e.snapshot(&s)||e.legal_actions(&cancelled)!=e.legal_actions(&s){return Err("native cancellation did not restore root".into());}
        }else if !available{return Err(format!("unrecognized source/attack path without cancellation at {:?}",opened.decision));}
    }
    row["source_use"]=json!(available);let mut queries=vec![];let mut followed=false;let mut errors=0;
    for (slot,id) in SLOTS.iter().zip(refs){
        let mut target_values=serde_json::Map::new();let mut masks=serde_json::Map::new();for name in TARGETS{target_values.insert(name.into(),json!(0));masks.insert(name.into(),json!(false));}
        target_values.insert("source_use".into(),json!(available as u8));masks.insert("source_use".into(),json!(true));
        let mut query=json!({"chosen_ref":slot,"chosen_id":cid(id),"targetAction":null,"after":null,"followupPass":null,"following":null,"targets":target_values,"target_mask":masks,"engineError":null});
        if let Some(prompt)=target_prompt{
            query["target_mask"]["target_allowed"]=json!(true);
            if let Some(action)=offered(e,&prompt,id){
                query["targets"]["target_allowed"]=json!(1);query["targetAction"]=json!(action);b.check()?;
                match b.apply(e,&prompt,&action,&refs,&format!("commit-{slot}-independent")){
                    Err(error) if error.starts_with("NATIVE_APPLY_ERROR: ")=>{query["engineError"]=json!(error);errors+=1;}
                    Err(error)=>return Err(error),
                    Ok(after)=>{
                        let captured=capture(e,&after,&refs)?;
                        query["after"]=captured.clone();
                        if !settled(&after){
                            query["pendingOutcome"]=json!("Native apply returned an unresolved continuation; final outcome labels remain unknown.");
                            queries.push(query);continue;
                        }
                        query["targets"]["cost_resource"]=json!(ready_resources(&s)-ready_resources(&after));
                        query["targets"]["source_exhausted_after"]=json!(after.card(refs[7]).exhausted as u8);
                        query["targets"]["terminal"]=json!(after.is_terminal() as u8);
                        let was_attackable=before["projections"][slot]["attackable"].as_bool().unwrap();
                        let after_zone=zone(&after,id);let defeated=was_attackable&&(after_zone=="discard"||!after.card(id).present);
                        query["targets"]["target_defeated"]=json!(defeated as u8);
                        for name in ["cost_resource","source_exhausted_after","terminal","target_defeated"]{query["target_mask"][name]=json!(true);}
                        if was_attackable&&["ground","space","base"].contains(&after_zone)&&after_zone==zone(&s,id){
                            for (name,field) in [("damage_delta","damage"),("target_exhausted_delta","exhausted"),("shield_delta","shield_count"),("xp_delta","xp_count")]{
                                let pre=&before["projections"][slot][field];let post=&captured["projections"][slot][field];
                                let a=pre.as_i64().or_else(||pre.as_bool().map(i64::from)).ok_or("native projection prevalue missing")?;
                                let z=post.as_i64().or_else(||post.as_bool().map(i64::from)).ok_or("native projection postvalue missing")?;
                                query["targets"][name]=json!(z-a);query["target_mask"][name]=json!(true);
                            }
                        }
                        query["after"]=captured;
                        if !followed&&!after.is_terminal(){
                            if let Some(pass)=e.legal_actions(&after).into_iter().find(|a|a.kind=="button"&&a.arg.as_ref().and_then(Value::as_str)==Some("pass")){
                                let following=b.apply(e,&after,&pass,&refs,&format!("followup-{slot}-only-once"))?;followed=true;
                                query["followupPass"]=json!(pass);query["following"]=capture(e,&following,&refs)?;
                                // A window card alone can be an attack, so never label it ability reuse.
                                // Observed absence proves no source affordance; presence stays unknown here.
                                if following.active==Seat::P1&&following.decision==Decision::Window&&!following.regroup
                                    &&settled(&following)&&!following.is_terminal()&&offered(e,&following,refs[7]).is_none(){
                                    query["targets"]["followup_source_offered"]=json!(0);query["target_mask"]["followup_source_offered"]=json!(true);
                                }
                            }
                        }
                    }
                }
            }
        }
        queries.push(query);
    }
    row["queries"]=json!(queries);row["engine_error_branches"]=json!(errors);
    b.trace(&json!({"phase":"contextComplete","context":b.context,"applyCalls":b.calls,"case":row}))?;Ok(row)
}
fn run()->Result<Value,String>{
    source_preflight()?;let started=Instant::now();
    let plan_path=PathBuf::from(env::var("GROUNDED_COLLECTION_PLAN").map_err(|_|"GROUNDED_COLLECTION_PLAN required")?);
    let plan_bytes=fs::read(&plan_path).map_err(|e|e.to_string())?;let plan:Value=serde_json::from_slice(&plan_bytes).map_err(|e|e.to_string())?;
    let mut catalogue=kessel::catalogue_io::load_catalogue_value(&Path::new(SOURCE).join("compiler/generated"))?;
    let full=catalogue["cards"].as_array().ok_or("catalogue cards missing")?;let mut provenance=vec![];let mut selected=vec![];
    for program in plan["programs"].as_array().ok_or("program plan missing")?{
        let code=program["code"].as_str().unwrap();let side=program["side"].as_str().unwrap();let index=program["index"].as_u64().unwrap() as usize;
        let raw=full.iter().find(|r|r["setCode"]==code).ok_or("whole source card missing")?;
        let abilities=raw["abilities"][side].as_array().ok_or("active side missing")?;
        if abilities.len()!=1||index!=0||abilities[index]["trigger"]!="action"||raw["sourceHash"]!=program["source_hash"]||abilities[index]!=program["raw_ability"]{return Err("frozen actual active-side action binding changed".into());}
        selected.push(code.to_string());provenance.push(json!({"card":code,"sourceHash":raw["sourceHash"],"sourcePath":raw["sourcePath"],"abilityPath":["abilities",side,index],"actualUnmodifiedAbility":abilities[index]}));
    }
    for code in plan["helpers"].as_object().unwrap().values().chain(plan["required_native_tokens"].as_array().unwrap().iter()) {selected.push(code.as_str().unwrap().to_string());}
    selected.sort();selected.dedup();
    catalogue["cards"].as_array_mut().unwrap().retain(|r|r["setCode"].as_str().is_some_and(|code|selected.iter().any(|x|x==code)));
    let selected_hash=format!("{:x}",Sha256::digest(serde_json::to_vec(&catalogue).unwrap()));
    let engine=Engine::from_catalogue_value(&catalogue)?;
    for code in &selected{if !engine.definitions.iter().any(|d|d.code==*code){return Err(format!("whole selected definition not admitted: {code}"));}}
    let path=PathBuf::from(env::var("GROUNDED_NATIVE_TRACE").map_err(|_|"GROUNDED_NATIVE_TRACE required")?);
    let mut file=fs::OpenOptions::new().write(true).create_new(true).open(&path).map_err(|e|e.to_string())?;
    serde_json::to_writer(&mut file,&json!({"schema":"grounded-native-apply-journal/1","sourceRevision":REVISION,"selectedWholeCards":selected,"maxApplyCalls":MAX_APPLY,"planSha256":format!("{:x}",Sha256::digest(&plan_bytes))})).map_err(|e|e.to_string())?;
    file.write_all(b"\n").and_then(|_|file.flush()).and_then(|_|file.sync_all()).map_err(|e|e.to_string())?;drop(file);
    let mut budget=Budget{started,calls:0,path,context:String::new()};let mut cases=vec![];
    for context in plan["contexts"].as_array().unwrap(){for program in plan["programs"].as_array().unwrap(){cases.push(run_case(&engine,&mut budget,program,context,&plan)?);}}
    source_preflight()?;
    let engine_errors:usize=cases.iter().map(|case|case["engine_error_branches"].as_u64().unwrap_or(0) as usize).sum();
    Ok(json!({"schema":"jepa-grounded-native-transitions/1","sourceRevision":REVISION,"selectedWholeCards":selected,"selectedCatalogueSha256":selected_hash,"provenance":provenance,"native_engine_error_branches":engine_errors,
        "collectionPlan":plan,"collectionPlanSha256":format!("{:x}",Sha256::digest(&plan_bytes)),"candidateOrder":SLOTS,"targetNames":TARGETS,"cases":cases,
        "applyCalls":budget.calls,"maxApplyCalls":MAX_APPLY,"elapsedSeconds":started.elapsed().as_secs_f64(),"maxSeconds":MAX_SECONDS,
        "actualCardAbilitiesInSyntheticPublicStates":true,"noHiddenCardsOrDrawOrder":true,"forcetekiOracleRun":false,
        "scope":"existing whole native-admitted cards only; independent offered candidate commits, no game/opponent or coverage expansion"}))
}
fn main(){let args:Vec<_>=env::args().collect();if args.len()!=2{eprintln!("usage: grounded-native-collector NEW_RECEIPT.json");std::process::exit(2);}
    match std::thread::Builder::new().stack_size(64*1024*1024).spawn(run).expect("collector worker").join(){
        Ok(Ok(receipt))=>{let mut file=fs::OpenOptions::new().write(true).create_new(true).open(&args[1]).expect("new receipt");serde_json::to_writer_pretty(&mut file,&receipt).unwrap();file.write_all(b"\n").and_then(|_|file.flush()).and_then(|_|file.sync_all()).unwrap();println!("{}",json!({"ok":true,"receipt":args[1],"applyCalls":receipt["applyCalls"],"contexts":receipt["cases"].as_array().unwrap().len()}));}
        Ok(Err(error))=>{eprintln!("collector: {error}");std::process::exit(1);}
        Err(_)=>{eprintln!("collector assertion failed");std::process::exit(1);}
    }
}
