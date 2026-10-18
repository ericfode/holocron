//! Whole existing definitions, native action menus, independent public branches.
//! No engine expansion, hidden cards, full games, opponents, or synthetic labels.
use kessel::{model::{Card,CardId,Decision},Action,Engine,Seat,State};
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{env,fs,io::Write,path::{Path,PathBuf},process::Command,time::Instant};

const SOURCE:&str="/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source";
const REVISION:&str="c7ee39554901278cee70f61fd8b26fb1920696b3";
const MAX_APPLY:usize=48;
const MAX_SECONDS:u64=30;
const SLOTS:[&str;8]=["source","own_helper","opponent_helper","anchor_a","anchor_b","auxiliary","own_base","opponent_base"];

fn source_preflight()->Result<(),String>{
    let revision=Command::new("git").env("GIT_OPTIONAL_LOCKS","0").args(["-C",SOURCE,"rev-parse","HEAD"]).output().map_err(|e|e.to_string())?;
    if !revision.status.success()||String::from_utf8_lossy(&revision.stdout).trim()!=REVISION{return Err("pinned source revision mismatch".into());}
    let clean=Command::new("git").env("GIT_OPTIONAL_LOCKS","0").args(["-C",SOURCE,"diff","--quiet","HEAD","--","crates/kessel","compiler/generated","Cargo.toml","Cargo.lock"]).status().map_err(|e|e.to_string())?;
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
        if p.leader==id{return "leader";}if p.hand.contains(id){return "hand";}if p.discard.contains(id){return "discard";}if p.resources.contains(id){return "resource";}
    } if s.card(id).present&&s.card(id).parent!=0{return "upgrade";} "absent"
}
fn native_card<'a>(wire:&'a Value,id:CardId)->Option<&'a Value>{
    let name=cid(id);
    for seat in ["p1","p2"]{let p=&wire["players"][seat];for z in ["base","leader"]{if p[z]["id"]==name{return Some(&p[z]);}}
        for z in ["ground","space","discard","resources","hand"]{if let Some(cards)=p[z].as_array(){for c in cards{if c["id"]==name{return Some(c);}}}}
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
    let physical_unit=info.is("unit")||(info.is("leader")&&c.deployed);let damageable=physical_unit||info.is("base");
    let card=native_card(wire,id);let hp=card.and_then(|v|v["hp"].as_i64()).or(info.hp.map(i64::from));
    let power=card.and_then(|v|v["power"].as_i64()).or(info.power.map(i64::from));
    Ok(json!({"id":cid(id),"code":if c.present{json!(e.definitions[c.def as usize].code)}else{Value::Null},"zone":z,"owner":if c.present{json!(c.owner.as_str())}else{Value::Null},
        "present":c.present,"in_arena":z=="ground"||z=="space","attackable":(["ground","space","base"].contains(&z)),
        "is_unit":info.is("unit")||(info.is("leader")&&c.deployed),"is_base":info.is("base"),
        "damage":if info.is("upgrade"){0}else{c.damage},"exhausted":if info.is("upgrade"){false}else{c.exhausted},"hp":if c.present&&!info.is("upgrade"){hp.unwrap_or(0)}else{0},"power":if c.present&&!info.is("upgrade"){power.unwrap_or(0)}else{0},
        "shield_count":token_count(s,c.shield)?,"xp_count":token_count(s,c.experience)?,
        "known":{"identity":c.present,"owner":c.present,"damage":c.present&&damageable,"exhausted":c.present&&physical_unit,"hp":c.present&&hp.is_some()&&damageable,"power":c.present&&power.is_some()&&physical_unit,"shield_count":c.present&&physical_unit,"xp_count":c.present&&physical_unit}}))
}
fn public_printed_has_trait(plan:&Value,code:&str,name:&str)->Result<bool,String>{
    // These fixtures contain no trait-changing effects. Read the complete public
    // pinned row keyed by the ACTUAL runtime definition code, not private fields.
    let row=plan.get("selected_whole_rows").and_then(|v|v.get(code)).ok_or("public whole-card trait row missing")?;
    let traits=row.get("card").and_then(|v|v.get("traits")).and_then(Value::as_array).ok_or("public printed traits missing")?;
    if traits.iter().any(|v|!v.is_string()){return Err("public printed traits malformed".into());}
    Ok(traits.iter().any(|v|v.as_str()==Some(name)))
}
fn other_fighter_count(e:&Engine,s:&State,refs:&[CardId;8],plan:&Value)->Result<usize,String>{
    let mut count=0;
    for &id in s.player(Seat::P1).ground.as_slice().iter().chain(s.player(Seat::P1).space.as_slice()){
        if id==refs[0]{continue;}
        let code=e.definitions[s.card(id).def as usize].code.as_str();
        if public_printed_has_trait(plan,code,"fighter")?{count+=1;}
    }
    Ok(count)
}
fn capture(e:&Engine,s:&State,refs:&[CardId;8],plan:&Value,world:&Value)->Result<Value,String>{
    let wire=e.snapshot(s);let mut projections=serde_json::Map::new();
    let intent=world["intent_ref"].as_str().ok_or("intent role missing")?;
    let intended=refs[SLOTS.iter().position(|r|*r==intent).ok_or("unknown intent role")?];
    let observations=world["observation_refs"].as_array().ok_or("observation roles missing")?;
    for (slot,id) in SLOTS.iter().zip(refs){
        if *id==0{projections.insert((*slot).into(),Value::Null);continue;}
        let mut p=projection(e,s,&wire,*id)?;
        let code=e.definitions[s.card(*id).def as usize].code.as_str();
        let printed=&plan["selected_whole_rows"][code]["card"];
        p["printed_traits"]=printed["traits"].clone();p["printed_aspects"]=printed["aspects"].clone();
        p["printed_types"]=printed["types"].clone();p["printed_cost"]=printed["cost"].clone();p["printed_unique"]=printed["unique"].clone();p["printed_keywords"]=printed["keywords"].clone();
        p["printed_keyword_values"]=plan["selected_whole_rows"][code]["keywordValues"].clone();
        p["known"]["printed_traits"]=json!(printed["traits"].is_array());p["known"]["printed_aspects"]=json!(printed["aspects"].is_array());
        p["known"]["printed_types"]=json!(printed["types"].is_array());p["known"]["printed_cost"]=json!(printed["cost"].is_number());
        p["known"]["printed_unique"]=json!(printed["unique"].is_boolean());p["known"]["printed_keywords"]=json!(printed["keywords"].is_array());
        p["role_matches"]=json!({"source":*id==refs[0],"intended":world["requires_target"]==true&&*id==intended,
            "observation_anchor_a":observations.first().and_then(Value::as_str)==Some(*slot),
            "observation_anchor_b":observations.get(1).and_then(Value::as_str)==Some(*slot)});
        projections.insert((*slot).into(),p);
    }
    Ok(json!({"decision":format!("{:?}",s.decision),"actor":s.actor(),"sourceInstance":if s.source==0{Value::Null}else{json!(cid(s.source))},
        "abilityProgramPlusOne":s.ability_program,"abilityPc":s.ability_pc,"abilityCommitted":s.ability_committed,
        "other_friendly_space_count":s.player(Seat::P1).space.as_slice().iter().filter(|id|**id!=refs[0]).count(),"other_friendly_fighter_count":other_fighter_count(e,s,refs,plan)?,"own_aspect_sources":{"base":e.definitions[s.card(s.player(Seat::P1).base).def as usize].code,"leader":e.definitions[s.card(s.player(Seat::P1).leader).def as usize].code},"state":wire,"projections":projections,"offeredActions":e.legal_actions(s),"terminal":s.is_terminal(),"settled":settled(s),
        "settlement":{"decision":format!("{:?}",s.decision),"ability_program":s.ability_program,"death_depth":s.death_depth,
            "death_pending":s.death_pending.len,"death_window":s.death_window.len,"pending_programs":s.pending_programs,
            "pending_triggers":s.pending_triggers,"after_attack_triggers":s.after_attack_triggers,
            "after_attack_programs":s.after_attack_programs,"event_group_active":s.event_group.active,"support_pending":s.support.pending}}))
}

fn attach_fixture(e:&Engine,s:&mut State,owner:Seat,code:&str,host:CardId)->CardId{
    let id=add(e,s,owner,code);let old=s.card(host).upgrades;
    s.card_mut(id).parent=host;s.card_mut(id).next_upgrade=old;s.card_mut(host).upgrades=id;
    s.registration_order.push(id).unwrap();id
}
fn fixture(e:&Engine,world:&Value,plan:&Value)->Result<(State,[CardId;8],Vec<CardId>),String>{
    let h=&plan["helpers"];let get=|name:&str|h[name].as_str().unwrap();let mut s=State{hidden_history_exact:true,..State::default()};
    for seat in [Seat::P1,Seat::P2]{let base=add(e,&mut s,seat,get("base"));let leader=add(e,&mut s,seat,get("leader"));s.player_mut(seat).base=base;s.player_mut(seat).leader=leader;}
    let mut refs=[0;8];refs[0]=add(e,&mut s,Seat::P1,world["source_code"].as_str().ok_or("source definition missing")?);s.player_mut(Seat::P1).hand.push(refs[0])?;
    let mut attachments=vec![];
    match world["cohort"].as_str(){
        Some("own-aspect-condition")=>{
            refs[1]=unit(e,&mut s,Seat::P1,world["own_helper"].as_str().ok_or("own helper missing")?);
            refs[2]=unit(e,&mut s,Seat::P2,world["opponent_helper"].as_str().ok_or("opponent helper missing")?);
            refs[3]=unit(e,&mut s,Seat::P2,get("victim"));s.card_mut(refs[3]).damage=world["victim_damage"].as_u64().ok_or("victim damage missing")? as u16;
            refs[4]=unit(e,&mut s,Seat::P2,get("unused_anchor"));
            for code in h["victim_upgrades"].as_array().ok_or("victim upgrades missing")?{
                attachments.push(attach_fixture(e,&mut s,Seat::P2,code.as_str().ok_or("victim upgrade code missing")?,refs[3]));
            }
        },
        Some("simultaneous-damage")=>{
            for slot in [3,4]{refs[slot]=unit(e,&mut s,Seat::P2,get("damage_space"));s.card_mut(refs[slot]).damage=world["anchor_damage"].as_u64().ok_or("anchor damage missing")? as u16;}
        },
        Some("friendly-space-aura")=>{
            let own=world["own_anchor"].as_str().ok_or("own anchor missing")?;
            if own!="anchor_a"&&own!="anchor_b"{return Err("invalid own aura anchor".into());}
            for slot in [3,4]{let owner=if SLOTS[slot]==own{Seat::P1}else{Seat::P2};refs[slot]=unit(e,&mut s,owner,get("aura_space"));s.card_mut(refs[slot]).damage=world["anchor_damage"].as_u64().ok_or("anchor damage missing")? as u16;}
        },
        Some("attachment-parent-binding")=>{
            for slot in [3,4]{refs[slot]=unit(e,&mut s,Seat::P1,get("host"));s.card_mut(refs[slot]).damage=world["anchor_damage"].as_u64().ok_or("anchor damage missing")? as u16;}
        },_=>return Err("unreviewed fixture cohort".into())
    }
    refs[6]=s.player(Seat::P1).base;refs[7]=s.player(Seat::P2).base;
    for n in 0..12{let id=add(e,&mut s,Seat::P1,get("resource"));s.card_mut(id).exhausted=n>=world["ready_resources"].as_u64().unwrap();s.player_mut(Seat::P1).resources.push(id)?;}
    Ok((s,refs,attachments))
}
fn offered(e:&Engine,s:&State,id:CardId)->Option<Action>{e.legal_actions(s).into_iter().find(|a|a.id()==Some(id))}
struct Budget{started:Instant,calls:usize,path:PathBuf,context:String}
impl Budget{
    fn trace(&self,row:&Value)->Result<(),String>{let mut f=fs::OpenOptions::new().append(true).open(&self.path).map_err(|e|e.to_string())?;serde_json::to_writer(&mut f,row).map_err(|e|e.to_string())?;f.write_all(b"\n").and_then(|_|f.flush()).and_then(|_|f.sync_all()).map_err(|e|e.to_string())}
    fn apply(&mut self,e:&Engine,s:&State,a:&Action,refs:&[CardId;8],branch:&str,plan:&Value,world:&Value)->Result<State,String>{
        if self.calls>=MAX_APPLY||self.started.elapsed().as_secs()>=MAX_SECONDS{return Err("native global quota reached".into());}
        if !e.legal_actions(s).contains(a){return Err("unoffered native action rejected before apply".into());}
        self.trace(&json!({"phase":"beforeApply","applyCall":self.calls+1,"context":self.context,"branch":branch,"before":capture(e,s,refs,plan,world)?,"offeredAction":a}))?;
        self.calls+=1;let result=e.apply(s,a);
        let row=match &result{Ok(t)=>json!({"phase":"afterApply","applyCall":self.calls,"context":self.context,"branch":branch,"after":capture(e,t,refs,plan,world)?}),Err(error)=>json!({"phase":"applyError","applyCall":self.calls,"context":self.context,"branch":branch,"error":error})};
        self.trace(&row)?;result.map_err(|error|format!("NATIVE_APPLY_ERROR: {error}"))
    }
}
fn run_case(e:&Engine,b:&mut Budget,world:&Value,plan:&Value)->Result<Value,String>{
    let (mut s,refs,attachments)=fixture(e,world,plan)?;let start=b.calls;
    let code=world["source_code"].as_str().unwrap();b.context=format!("world-{}-{code}",world["id"]);
    let imported=e.load_state(&e.snapshot(&s))?;
    if e.snapshot(&s)!=e.snapshot(&imported)||e.legal_actions(&s)!=e.legal_actions(&imported){return Err("public fixture snapshot/load mismatch".into());}
    let mut attachment_witnesses=vec![];
    for uid in attachments{
        let host=s.card(uid).parent;let mut query=s;query.source=uid;query.decision=Decision::UpgradeTarget;
        if offered(e,&query,host).is_none(){return Err("native public upgrade-target query rejects fixture host".into());}
        attachment_witnesses.push(json!({"upgrade":cid(uid),"host":cid(host),"code":e.definitions[s.card(uid).def as usize].code,"publicTargetQuery":capture(e,&query,&refs,plan,world)?,"offeredHost":offered(e,&query,host)}));
    }
    let intended=world["intent_ref"].as_str().ok_or("frozen intent missing")?;let intended_index=SLOTS.iter().position(|v|*v==intended).ok_or("intent role unknown")?;
    let mut refmap=serde_json::Map::new();for(name,id)in SLOTS.iter().zip(refs){refmap.insert((*name).into(),if id==0{Value::Null}else{json!(cid(id))});}
    let mut row=json!({"card":code,"world_id":world["id"],"cohort":world["cohort"],"refs":refmap,
        "declared_intent":{"ref":intended,"id":cid(refs[intended_index]),"requires_target":world["requires_target"]},"observation_refs":world["observation_refs"],
        "observation_mode":world["observation_mode"],"partition":world["partition"],"template_id":world["template_id"],"state_family":world["state_family"],
        "before":capture(e,&s,&refs,plan,world)?,"publicSnapshotRoundtripExact":true,"fixtureAttachmentWitnesses":attachment_witnesses,
        "playAction":null,"steps":[],"targetPrompt":null,"targetAction":null,"final":null,"lastObserved":null,"final_source_parent":null,"engineError":null,"completion":"play-unavailable","applyCalls":0});
    let Some(play)=offered(e,&s,refs[0])else{row["lastObserved"]=row["before"].clone();b.trace(&json!({"phase":"contextComplete","context":b.context,"case":row}))?;return Ok(row);};
    row["playAction"]=json!(play);let mut next_action=Some((play,"play-own-hand"));let mut committed_target=false;
    loop{
        if b.calls-start>=world["max_applies"].as_u64().ok_or("root apply bound missing")? as usize{row["completion"]=json!("per-root-apply-cap-unsettled");break;}
        let Some((action,stage))=next_action.take()else{break;};let before=capture(e,&s,&refs,plan,world)?;
        match b.apply(e,&s,&action,&refs,stage,plan,world){
            Err(error)if error.starts_with("NATIVE_APPLY_ERROR: ")=>{row["engineError"]=json!(error);row["completion"]=json!("native-error");break;},
            Err(error)=>return Err(error),
            Ok(after)=>{s=after;row["steps"].as_array_mut().unwrap().push(json!({"stage":stage,"before":before,"action":action,"after":capture(e,&s,&refs,plan,world)?}));}
        }
        if settled(&s){row["final"]=capture(e,&s,&refs,plan,world)?;row["completion"]=json!("settled");break;}
        let actions=e.legal_actions(&s);
        if s.decision==Decision::AbilityTarget||s.decision==Decision::UpgradeTarget{
            if !row["targetPrompt"].is_null(){row["completion"]=json!("unreviewed-second-target-prompt");break;}
            row["targetPrompt"]=capture(e,&s,&refs,plan,world)?;
            if let Some(action)=offered(e,&s,refs[intended_index]){row["targetAction"]=json!(action);committed_target=true;next_action=Some((action,if s.decision==Decision::UpgradeTarget{"attach-intended-host"}else{"chosen-target"}));}
            else if let Some(action)=actions.into_iter().find(|a|a.arg.as_ref().and_then(Value::as_str)==Some("passAbility")||a.arg.as_ref().and_then(Value::as_str)==Some("cancel")||a.label=="Cancel"){next_action=Some((action,"decline-unoffered-target"));}
            else{row["completion"]=json!("intended-target-unoffered-no-reviewed-decline");break;}
        }else if s.decision==Decision::AbilityOptional{
            if let Some(action)=actions.into_iter().find(|a|a.arg.as_ref().and_then(Value::as_str)==Some("trigger")){next_action=Some((action,"accept-optional-trigger"));}else{row["completion"]=json!("unrecognized-optional-menu");break;}
        }else if s.decision==Decision::AbilityNoEffect{
            if let Some(action)=actions.into_iter().find(|a|a.arg.as_ref().and_then(Value::as_u64)==Some(0)){next_action=Some((action,"use-no-effect-anyway"));}else{row["completion"]=json!("unrecognized-no-effect-menu");break;}
        }else if s.decision==Decision::TriggerOrder&&actions.len()==1{next_action=Some((actions[0].clone(),"sole-trigger-order"));}
        else{row["completion"]=json!(format!("unreviewed-continuation-{:?}",s.decision));break;}
    }
    row["applyCalls"]=json!(b.calls-start);row["intendedTargetCommitted"]=json!(committed_target);row["lastObserved"]=capture(e,&s,&refs,plan,world)?;
    row["final_source_parent"]=if s.card(refs[0]).parent==0{Value::Null}else{json!(cid(s.card(refs[0]).parent))};
    b.trace(&json!({"phase":"contextComplete","context":b.context,"applyCalls":b.calls,"case":row}))?;Ok(row)
}
fn run()->Result<Value,String>{
    source_preflight()?;let started=Instant::now();
    let plan_path=PathBuf::from(env::var("BINDING_TRANSFER_COLLECTION_PLAN").map_err(|_|"BINDING_TRANSFER_COLLECTION_PLAN required")?);
    let bytes=fs::read(&plan_path).map_err(|e|e.to_string())?;let plan:Value=serde_json::from_slice(&bytes).map_err(|e|e.to_string())?;
    let mut catalog=kessel::catalogue_io::load_catalogue_value(&Path::new(SOURCE).join("compiler/generated"))?;
    let selected:Vec<String>=plan["selected_whole_cards"].as_array().ok_or("selected rows missing")?.iter().map(|v|v.as_str().unwrap().to_string()).collect();
    for code in &selected{
        let row=catalog["cards"].as_array().unwrap().iter().find(|r|r["setCode"]==*code).ok_or("whole card absent")?;
        // Diagnostic-shard fields are added by the loader and preserved in the
        // actual engine catalogue; every compiler cards-shard field is exact.
        let expected=&plan["selected_whole_rows"][code];
        for (key,value)in expected.as_object().ok_or("expected whole card row missing")?{if row[key]!=*value{return Err(format!("whole definition changed {code}.{key}"));}}
    }
    catalog["cards"].as_array_mut().unwrap().retain(|r|r["setCode"].as_str().is_some_and(|c|selected.iter().any(|x|x==c)));
    let hash=format!("{:x}",Sha256::digest(serde_json::to_vec(&catalog).unwrap()));let engine=Engine::from_catalogue_value(&catalog)?;
    for code in &selected{if !engine.definitions.iter().any(|d|d.code==*code){return Err(format!("complete selected card not admitted: {code}"));}}
    let path=PathBuf::from(env::var("BINDING_TRANSFER_NATIVE_TRACE").map_err(|_|"BINDING_TRANSFER_NATIVE_TRACE required")?);
    let mut trace=fs::OpenOptions::new().write(true).create_new(true).open(&path).map_err(|e|e.to_string())?;
    serde_json::to_writer(&mut trace,&json!({"schema":"jepa-binding-transfer-apply-journal/1","sourceRevision":REVISION,"selectedWholeCards":selected,"maxApplyCalls":MAX_APPLY,"planSha256":format!("{:x}",Sha256::digest(&bytes))})).map_err(|e|e.to_string())?;
    trace.write_all(b"\n").and_then(|_|trace.flush()).and_then(|_|trace.sync_all()).map_err(|e|e.to_string())?;drop(trace);
    let mut budget=Budget{started,calls:0,path,context:String::new()};let mut cases=vec![];
    for world in plan["worlds"].as_array().ok_or("worlds missing")?{
        let case=run_case(&engine,&mut budget,world,&plan)?;
        let complete=case["completion"]=="settled"&&case["engineError"].is_null()&&(world["requires_target"]!=true||case["intendedTargetCommitted"]==true);
        cases.push(case);if !complete{break;}
    }
    source_preflight()?;
    Ok(json!({"schema":"jepa-binding-transfer-native/1","sourceRevision":REVISION,"selectedWholeCards":selected,"selectedCatalogueSha256":hash,
        "collectionPlan":plan,"collectionPlanSha256":format!("{:x}",Sha256::digest(&bytes)),"candidateOrder":SLOTS,"collectionComplete":cases.len()==26&&cases.iter().all(|c|c["completion"]=="settled"&&c["engineError"].is_null()&&(c["declared_intent"]["requires_target"]!=true||c["intendedTargetCommitted"]==true)),"cases":cases,"applyCalls":budget.calls,"maxApplyCalls":MAX_APPLY,
        "elapsedSeconds":started.elapsed().as_secs_f64(),"maxSeconds":MAX_SECONDS,"noHiddenCardsOrDrawOrder":true,"forcetekiOracleRun":false,
        "scope":"26 actual-endpoint fixtures from seven complete actual-corpus sources; four TRAIN templates/two held parent-stat program variants, no broad semantic or competitive claim"}))
}
fn main(){let args:Vec<_>=env::args().collect();if args.len()!=2{eprintln!("usage: binding-transfer-native-collector NEW_RECEIPT.json");std::process::exit(2);}
    match std::thread::Builder::new().stack_size(64*1024*1024).spawn(run).expect("collector worker").join(){
        Ok(Ok(receipt))=>{let mut file=fs::OpenOptions::new().write(true).create_new(true).open(&args[1]).expect("new receipt");serde_json::to_writer_pretty(&mut file,&receipt).unwrap();file.write_all(b"\n").and_then(|_|file.flush()).and_then(|_|file.sync_all()).unwrap();println!("{}",json!({"ok":true,"receipt":args[1],"applyCalls":receipt["applyCalls"],"cases":receipt["cases"].as_array().unwrap().len()}));}
        Ok(Err(error))=>{eprintln!("collector: {error}");std::process::exit(1);},Err(_)=>{eprintln!("collector assertion failed");std::process::exit(1);}
    }
}
