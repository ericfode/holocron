//! Versioned exposed-IBH104 fresh-state diagnostic. No new program-transfer claim.
//! No engine expansion, hidden cards, full games, opponents, or synthetic labels.
use kessel::{model::{Card,CardId,Decision},Action,Engine,Seat,State};
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{env,fs,io::Write,path::{Path,PathBuf},process::Command,time::Instant};

const SOURCE:&str="/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source";
const REVISION:&str="c7ee39554901278cee70f61fd8b26fb1920696b3";
const MAX_APPLY:usize=32;
const MAX_SECONDS:u64=15;
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
    let physical_unit=(info.is("unit")||(info.is("leader")&&c.deployed))&&z!="discard"&&z!="absent";let damageable=physical_unit||info.is("base");
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
    for seat in [Seat::P1,Seat::P2]{
        if s.player(seat).deck.len!=0||seat==Seat::P2&&(s.player(seat).hand.len!=0||s.player(seat).resources.len!=0){return Err("hidden fixture piles must stay empty".into());}
    }
    if s.player(Seat::P1).hand.as_slice().iter().any(|id|*id!=refs[0]){return Err("own hand may contain only the declared source".into());}
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
        "abilitySelection":s.ability_selection.ids[..s.ability_selection.len as usize].iter().map(|id|cid(*id)).collect::<Vec<_>>(),
        "other_friendly_space_count":s.player(Seat::P1).space.as_slice().iter().filter(|id|**id!=refs[0]).count(),"other_friendly_fighter_count":other_fighter_count(e,s,refs,plan)?,"own_aspect_sources":{"base":e.definitions[s.card(s.player(Seat::P1).base).def as usize].code,"leader":e.definitions[s.card(s.player(Seat::P1).leader).def as usize].code},"state":wire,"projections":projections,"offeredActions":e.legal_actions(s),"terminal":s.is_terminal(),"settled":settled(s),
        "settlement":{"decision":format!("{:?}",s.decision),"ability_program":s.ability_program,"death_depth":s.death_depth,
            "death_pending":s.death_pending.len,"death_window":s.death_window.len,"pending_programs":s.pending_programs,
            "pending_triggers":s.pending_triggers,"after_attack_triggers":s.after_attack_triggers,
            "after_attack_programs":s.after_attack_programs,"event_group_active":s.event_group.active,"support_pending":s.support.pending}}))
}

fn attach_fixture(e:&Engine,s:&mut State,owner:Seat,code:&str,host:CardId)->Result<CardId,String>{
    if host==0||host>=s.next_id||!s.card(host).present{return Err("invalid fixture attachment host".into());}
    // Match native Engine::attach chronology: ordinary upgrades append at tail.
    // Validate the existing chain before allocating or changing any links.
    let mut tail=0;let mut current=s.card(host).upgrades;let mut seen=vec![];
    while current!=0{
        if current>=s.next_id||seen.contains(&current){return Err("invalid/cyclic fixture attachment chain".into());}
        let card=s.card(current);
        if !card.present||card.parent!=host{return Err("fixture attachment parent mismatch".into());}
        seen.push(current);tail=current;current=card.next_upgrade;
    }
    let id=add(e,s,owner,code);
    if tail==0{s.card_mut(host).upgrades=id;}else{s.card_mut(tail).next_upgrade=id;}
    s.card_mut(id).parent=host;s.card_mut(id).next_upgrade=0;
    s.registration_order.push(id)?;Ok(id)
}
fn fixture(e:&Engine,world:&Value,plan:&Value)->Result<(State,[CardId;8],Vec<CardId>),String>{
    let h=&plan["helpers"];let get=|name:&str|h[name].as_str().ok_or("helper code missing");
    let mut s=State{hidden_history_exact:true,..State::default()};
    for seat in [Seat::P1,Seat::P2]{let base=add(e,&mut s,seat,get("base")?);let leader=add(e,&mut s,seat,get("leader")?);s.player_mut(seat).base=base;s.player_mut(seat).leader=leader;}
    let mut refs=[0;8];refs[0]=add(e,&mut s,Seat::P1,world["source_code"].as_str().ok_or("source code missing")?);s.player_mut(Seat::P1).hand.push(refs[0])?;
    for slot in 1..6{
        let spec=&world["arena_cards"][SLOTS[slot]];
        let owner=match spec["owner"].as_str(){Some("p1")=>Seat::P1,Some("p2")=>Seat::P2,_=>return Err("public arena owner missing".into())};
        refs[slot]=unit(e,&mut s,owner,spec["code"].as_str().ok_or("public arena code missing")?);
        s.card_mut(refs[slot]).damage=u16::try_from(spec["damage"].as_u64().ok_or("public damage missing")?).map_err(|_|"damage out of range")?;
        s.card_mut(refs[slot]).exhausted=spec["exhausted"].as_bool().ok_or("public exhaustion missing")?;
    }
    refs[6]=s.player(Seat::P1).base;refs[7]=s.player(Seat::P2).base;
    s.card_mut(refs[6]).damage=u16::try_from(world["own_base_damage"].as_u64().ok_or("own base damage missing")?).map_err(|_|"base damage out of range")?;
    let ready=world["ready_resources"].as_u64().ok_or("resource count missing")?;
    if ready>12{return Err("ready resources exceed physical12".into());}
    for n in 0..12{let id=add(e,&mut s,Seat::P1,get("resource")?);s.card_mut(id).exhausted=n>=ready;s.player_mut(Seat::P1).resources.push(id)?;}
    Ok((s,refs,vec![]))
}
fn fixture_chronology(s:&State,host:CardId)->Result<Value,String>{
    let mut chain=vec![];let mut current=s.card(host).upgrades;
    while current!=0{
        if current>=s.next_id||chain.contains(&current){return Err("invalid/cyclic fixture attachment chain".into());}
        let card=s.card(current);
        if !card.present||card.parent!=host{return Err("fixture attachment parent mismatch".into());}
        chain.push(current);current=card.next_upgrade;
    }
    let registration:Vec<_>=s.registration_order.as_slice().iter().map(|id|*id as CardId).filter(|id|chain.contains(id)).collect();
    let host_index=s.registration_order.as_slice().iter().position(|id|*id as CardId==host).ok_or("fixture host registration missing")?;
    if registration!=chain||chain.iter().any(|id|s.registration_order.as_slice().iter().position(|v|*v as CardId==*id).map_or(true,|i|i<=host_index)){
        return Err("fixture attachment chronology differs from registration".into());
    }
    Ok(json!({"host":cid(host),"linkedUpgradeOrder":chain.into_iter().map(cid).collect::<Vec<_>>(),
        "registrationUpgradeOrder":registration.into_iter().map(cid).collect::<Vec<_>>(),"exact":true}))
}
fn validate_fixtures(e:&Engine,plan:&Value)->Result<Vec<Value>,String>{
    let worlds=plan["worlds"].as_array().ok_or("worlds missing")?;
    if worlds.len()!=8{return Err("fixture-only validation requires the frozen8-root plan".into());}
    let mut results=vec![];let mut ids=vec![];
    for world in worlds{
        let id=world["id"].as_u64().ok_or("world id missing")?;
        if id>=8||ids.contains(&id){return Err("duplicate/out-of-range fixture world id".into());}ids.push(id);
        let (s,refs,attachments)=fixture(e,world,plan)?;
        if !settled(&s){return Err("initial fixture must be settled".into());}
        let snapshot=e.snapshot(&s);let imported=e.load_state(&snapshot)?;
        if snapshot!=e.snapshot(&imported)||e.legal_actions(&s)!=e.legal_actions(&imported){return Err("public fixture snapshot/load mismatch".into());}
        for seat in [Seat::P1,Seat::P2]{
            if s.player(seat).deck.len!=0||(seat==Seat::P2&&(s.player(seat).hand.len!=0||s.player(seat).resources.len!=0)){return Err("hidden fixture piles must be empty".into());}
        }
        if s.player(Seat::P1).hand.as_slice()!=[refs[0]]{return Err("fixture own hand must contain only the declared source".into());}
        if (1..s.next_id).any(|id|s.card(id).present&&e.definitions[s.card(id).def as usize].code=="TOKEN_SHIELD"){
            return Err("constructor support token became a physical fixture card".into());
        }
        let mut chronology=vec![];let mut attachment_witnesses=vec![];
        for uid in attachments{
            let host=s.card(uid).parent;let mut query=s;query.source=uid;query.decision=Decision::UpgradeTarget;
            if offered(e,&query,host).is_none(){return Err("native public upgrade-target query rejects fixture host".into());}
            chronology.push(fixture_chronology(&s,host)?);
            attachment_witnesses.push(json!({"upgrade":cid(uid),"host":cid(host),"code":e.definitions[s.card(uid).def as usize].code,
                "offeredHost":offered(e,&query,host),"publicTargetQuery":capture(e,&query,&refs,plan,world)?}));
        }
        results.push(json!({"world_id":id,"card":world["source_code"],"publicSnapshotRoundtripExact":true,
            "legalActionsRoundtripExact":true,"attachmentChronology":chronology,"fixtureAttachmentWitnesses":attachment_witnesses,
            "before":capture(e,&s,&refs,plan,world)?,"applyCalls":0,"actionsApplied":0}));
    }
    Ok(results)
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
fn done_action(actions:&[Action])->Result<Action,String>{
    let done:Vec<_>=actions.iter().filter(|a|a.arg.as_ref().and_then(Value::as_str)==Some("done")&&a.label=="Done"&&a.id().is_none()).cloned().collect();
    if done.len()!=1{return Err("exact offered Done action missing/ambiguous".into());}Ok(done[0].clone())
}
fn decline_action(actions:&[Action])->Result<Option<Action>,String>{
    let choices:Vec<_>=actions.iter().filter(|a|a.id().is_none()&&a.arg.as_ref().and_then(Value::as_str)==Some("cancel")&&a.label=="Cancel").cloned().collect();
    if choices.len()>1{return Err("ambiguous native Cancel actions".into());}Ok(choices.first().cloned())
}
fn run_case(e:&Engine,b:&mut Budget,world:&Value,plan:&Value)->Result<Value,String>{
    let (mut s,refs,_)=fixture(e,world,plan)?;let start=b.calls;
    let code=world["source_code"].as_str().ok_or("source missing")?;b.context=format!("world-{}-{code}",world["id"]);
    let intended=world["intent_ref"].as_str().ok_or("frozen intent missing")?;let intended_index=SLOTS.iter().position(|v|*v==intended).ok_or("intent role unknown")?;
    let multiple=match world["selection_mode"].as_str(){Some("single-target")=>false,Some("exactly-one-upTo")=>true,_=>return Err("selection mode missing".into())};
    let mut refmap=serde_json::Map::new();for(name,id)in SLOTS.iter().zip(refs){refmap.insert((*name).into(),json!(cid(id)));}
    let mut row=json!({"card":code,"world_id":world["id"],"cohort":world["cohort"],"refs":refmap,
        "declared_intent":{"ref":intended,"id":cid(refs[intended_index]),"requires_target":true},"observation_refs":world["observation_refs"],
        "observation_mode":world["observation_mode"],"selection_mode":world["selection_mode"],"scenario":world["scenario"],"partition":world["partition"],"template_id":world["template_id"],"state_family":world["state_family"],
        "before":capture(e,&s,&refs,plan,world)?,"publicSnapshotRoundtripExact":true,"fixtureAttachmentWitnesses":[],
        "playAction":null,"steps":[],"targetPrompt":null,"targetAction":null,"selectionDoneAction":null,"selectionWitness":null,"declineAction":null,
        "intentOffered":null,"intentResolution":null,"terminalClassification":null,"final":null,"lastObserved":null,"final_source_parent":null,"engineError":null,"completion":"play-unavailable","applyCalls":0});
    let Some(play)=offered(e,&s,refs[0])else{row["lastObserved"]=row["before"].clone();b.trace(&json!({"phase":"contextComplete","context":b.context,"case":row}))?;return Ok(row);};
    row["playAction"]=json!(play);let mut next_action=Some((play,"play-own-hand"));let mut selected=false;let mut done=false;let mut declined=false;
    loop{
        if b.calls-start>=world["max_applies"].as_u64().ok_or("root apply bound missing")? as usize{row["completion"]=json!("per-root-apply-cap-unsettled");break;}
        let Some((action,stage))=next_action.take()else{break;};let before=capture(e,&s,&refs,plan,world)?;
        match b.apply(e,&s,&action,&refs,stage,plan,world){
            Err(error)if error.starts_with("NATIVE_APPLY_ERROR: ")=>{row["engineError"]=json!(error);row["completion"]=json!("native-error");break;},
            Err(error)=>return Err(error),
            Ok(after)=>{s=after;row["steps"].as_array_mut().unwrap().push(json!({"stage":stage,"before":before,"action":action,"after":capture(e,&s,&refs,plan,world)?}));}
        }
        if stage=="chosen-target"{selected=true;}if stage=="commit-one-selection"{done=true;}if stage=="decline-unoffered-target"{declined=true;}
        if settled(&s){row["final"]=capture(e,&s,&refs,plan,world)?;row["completion"]=json!("settled");break;}
        let actions=e.legal_actions(&s);
        if s.decision==Decision::AbilityTarget{
            if selected{
                if !multiple||done||s.ability_selection.len!=1||s.ability_selection.ids[0]!=refs[intended_index]||row["targetPrompt"]["abilityProgramPlusOne"]!=json!(s.ability_program)||row["targetPrompt"]["abilityPc"]!=json!(s.ability_pc){row["completion"]=json!("unreviewed-second-target-prompt");break;}
                row["selectionWitness"]=capture(e,&s,&refs,plan,world)?;
                match done_action(&actions){Ok(action)=>{row["selectionDoneAction"]=json!(action);next_action=Some((action,"commit-one-selection"));},Err(error)=>{row["completion"]=json!(error);break;}}
            }else{
                if !row["targetPrompt"].is_null(){row["completion"]=json!("unreviewed-second-target-prompt");break;}
                row["targetPrompt"]=capture(e,&s,&refs,plan,world)?;
                let choice=offered(e,&s,refs[intended_index]);row["intentOffered"]=json!(choice.is_some());
                if let Some(action)=choice{row["targetAction"]=json!(action);next_action=Some((action,"chosen-target"));}
                else{match decline_action(&actions){Ok(Some(action))=>{row["declineAction"]=json!(action);next_action=Some((action,"decline-unoffered-target"));},Ok(None)=>{row["completion"]=json!("unoffered-observation-only");break;},Err(error)=>{row["completion"]=json!(error);break;}}}
            }
        }else if s.decision==Decision::AbilityOptional{
            let choices:Vec<_>=actions.into_iter().filter(|a|a.arg.as_ref().and_then(Value::as_str)==Some("trigger")&&a.label=="Trigger"&&a.id().is_none()).collect();
            if choices.len()==1{next_action=Some((choices[0].clone(),"accept-optional-trigger"));}else{row["completion"]=json!("unrecognized-optional-menu");break;}
        }else if s.decision==Decision::AbilityNoEffect{
            let choices:Vec<_>=actions.into_iter().filter(|a|a.arg.as_ref().and_then(Value::as_u64)==Some(0)&&a.label=="Use it anyway"&&a.id().is_none()).collect();
            if choices.len()==1{next_action=Some((choices[0].clone(),"use-no-effect-anyway"));}else{row["completion"]=json!("unrecognized-no-effect-menu");break;}
        }else if s.decision==Decision::TriggerOrder&&actions.len()==1{next_action=Some((actions[0].clone(),"sole-trigger-order"));}
        else{row["completion"]=json!(format!("unreviewed-continuation-{:?}",s.decision));break;}
    }
    let committed=selected&&(!multiple||done);row["applyCalls"]=json!(b.calls-start);row["intendedTargetCommitted"]=json!(committed);
    row["intentResolution"]=if committed{json!("committed")}else if declined{json!("unoffered-declined")}else if row["completion"]=="unoffered-observation-only"{json!("unoffered-observation-only")}else{Value::Null};
    row["terminalClassification"]=if row["completion"]=="settled"&&committed{json!("settled-committed")}else if row["completion"]=="settled"&&declined{json!("settled-cancelled")}else if row["completion"]=="unoffered-observation-only"{json!("unoffered-prompt-only")}else{Value::Null};
    row["lastObserved"]=capture(e,&s,&refs,plan,world)?;
    row["final_source_parent"]=if s.card(refs[0]).parent==0{Value::Null}else{json!(cid(s.card(refs[0]).parent))};
    b.trace(&json!({"phase":"contextComplete","context":b.context,"applyCalls":b.calls,"case":row}))?;Ok(row)
}
fn run(validate_only:bool)->Result<Value,String>{
    source_preflight()?;let started=Instant::now();
    let plan_path=PathBuf::from(env::var("ABILITY_CORRECTION_PLAN").map_err(|_|"ABILITY_CORRECTION_PLAN required")?);
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
    let fixture_validation=validate_fixtures(&engine,&plan)?;
    // This branch returns before reading a native-trace path, creating an apply
    // journal, constructing Budget, or entering the action-producing run_case.
    if validate_only{
        let cases=fixture_validation;source_preflight()?;
        return Ok(json!({"schema":"jepa-ability-correction-fixture-validation/1","sourceRevision":REVISION,
            "collectionPlan":plan,"collectionPlanSha256":format!("{:x}",Sha256::digest(&bytes)),
            "selectedWholeCards":selected,"selectedCatalogueSha256":hash,"candidateOrder":SLOTS,
            "validationComplete":cases.len()==8,"cases":cases,"applyCalls":0,"engineApplyInvocations":0,
            "actionsApplied":0,"nativeJournalCreated":false,"neuralForwards":0,"optimizerUpdates":0,
            "elapsedSeconds":started.elapsed().as_secs_f64(),"noHiddenCardsOrDrawOrder":true,
            "scope":"Fixture construction, physical attachment legality/chronology and public snapshot/load validation only; no action outcomes or learned results."}));
    }
    let path=PathBuf::from(env::var("ABILITY_CORRECTION_NATIVE_TRACE").map_err(|_|"ABILITY_CORRECTION_NATIVE_TRACE required")?);
    let mut trace=fs::OpenOptions::new().write(true).create_new(true).open(&path).map_err(|e|e.to_string())?;
    serde_json::to_writer(&mut trace,&json!({"schema":"jepa-ability-correction-apply-journal/1","sourceRevision":REVISION,"selectedWholeCards":selected,"maxApplyCalls":MAX_APPLY,"planSha256":format!("{:x}",Sha256::digest(&bytes))})).map_err(|e|e.to_string())?;
    trace.write_all(b"\n").and_then(|_|trace.flush()).and_then(|_|trace.sync_all()).map_err(|e|e.to_string())?;drop(trace);
    let mut budget=Budget{started,calls:0,path,context:String::new()};let mut cases=vec![];
    for world in plan["worlds"].as_array().ok_or("worlds missing")?{
        let case=run_case(&engine,&mut budget,world,&plan)?;
        let complete=case["engineError"].is_null()&&((case["completion"]=="settled"&&(case["intentResolution"]=="committed"||case["intentResolution"]=="unoffered-declined"))||(case["completion"]=="unoffered-observation-only"&&case["intentOffered"]==false&&case["final"].is_null()));
        cases.push(case);if !complete{break;}
    }
    source_preflight()?;
    Ok(json!({"schema":"jepa-ability-correction-native/1","sourceRevision":REVISION,"selectedWholeCards":selected,"selectedCatalogueSha256":hash,
        "collectionPlan":plan,"collectionPlanSha256":format!("{:x}",Sha256::digest(&bytes)),"candidateOrder":SLOTS,"collectionComplete":cases.len()==8&&cases.iter().all(|c|c["engineError"].is_null()&&((c["completion"]=="settled"&&(c["intentResolution"]=="committed"||c["intentResolution"]=="unoffered-declined"))||(c["completion"]=="unoffered-observation-only"&&c["intentOffered"]==false&&c["final"].is_null()))),"fixtureValidation":fixture_validation,"cases":cases,"applyCalls":budget.calls,"maxApplyCalls":MAX_APPLY,
        "elapsedSeconds":started.elapsed().as_secs_f64(),"maxSeconds":MAX_SECONDS,"noHiddenCardsOrDrawOrder":true,"forcetekiOracleRun":false,
        "scope":"8 predeclared own-hand state-transfer diagnostic fixtures from one previously exposed complete actual-corpus card; exactly-one upTo controls, no multi-cardinality or competitive claim"}))
}
pub(crate) fn entry(require_validation:bool){let args:Vec<_>=env::args().collect();
    let validate_only=args.len()==3&&args[1]=="--validate-fixtures-only";
    if (!validate_only&&args.len()!=2)||(require_validation&&!validate_only){eprintln!("usage: ability-correction-native-collector --validate-fixtures-only NEW_RECEIPT.json");std::process::exit(2);}
    let output=if validate_only{args[2].clone()}else{args[1].clone()};
    match std::thread::Builder::new().stack_size(64*1024*1024).spawn(move||run(validate_only)).expect("collector worker").join(){
        Ok(Ok(receipt))=>{let mut file=fs::OpenOptions::new().write(true).create_new(true).open(&output).expect("new receipt");serde_json::to_writer_pretty(&mut file,&receipt).unwrap();file.write_all(b"\n").and_then(|_|file.flush()).and_then(|_|file.sync_all()).unwrap();println!("{}",json!({"ok":true,"receipt":output,"schema":receipt["schema"],"applyCalls":receipt["applyCalls"],"cases":receipt["cases"].as_array().unwrap().len()}));}
        Ok(Err(error))=>{eprintln!("collector: {error}");std::process::exit(1);},Err(_)=>{eprintln!("collector assertion failed");std::process::exit(1);}
    }
}
fn main(){entry(false);}
