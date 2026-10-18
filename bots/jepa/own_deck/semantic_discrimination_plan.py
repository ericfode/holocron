"""Public/source-only preparation for the fixed 33-root semantic assay.

No engine application, model forward, optimizer, fitted transform or ledger
initialization. Hypotheses are admission expectations, never native labels.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import effect_identifiability_fit as E

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]/'experiments/semantic-discrimination-v1'
KESSEL=Path('/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source')
REVISION='c7ee39554901278cee70f61fd8b26fb1920696b3'
SCHEMA='jepa-semantic-discrimination-plan/1'
CODES=('LAW_045','ASH_071','LOF_077','JTL_078','LAW_133','JTL_140','ASH_081','IBH_104')
TRAIN=CODES[:6]
HELD=CODES[6:]
ROLES=('source','own_helper','opponent_helper','anchor_a','anchor_b','auxiliary','own_base','opponent_base')
HELPERS=dict(base='ASH_019',leader='IBH_053',resource='LOF_256',own_false='ASH_056',own_true='SEC_094',
    cheap_ground='SEC_028',expensive_ground='LOF_112',cheap_space='TWI_253',expensive_space='TWI_111',auxiliary='TWI_253')
TEMPLATES=dict(LAW_045='conditional-ground-damage',ASH_071='simultaneous-self-and-enemy-space-damage',
    LOF_077='cost-bounded-nonleader-defeat',JTL_078='vehicle-nonleader-defeat',LAW_133='unit-defeat-then-own-base-heal',
    JTL_140='bounded-multi-target-unit-damage',ASH_081='chosen-unit-or-base-heal',IBH_104='enemy-cost-bounded-multi-target-defeat')


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()
def pin(path):
    p=Path(path).resolve();raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def require(value,message):
    if not value:raise ValueError(message)


def scenario_cards(scenario):
    """Every arena instance has one represented public candidate role."""
    unit=lambda code,owner,damage=0:dict(code=code,owner=owner,damage=damage,exhausted=False)
    if scenario==0:
        anchors=dict(anchor_a=unit(HELPERS['cheap_ground'],'p1',1),anchor_b=unit(HELPERS['expensive_space'],'p2',1))
        helpers=dict(own_helper=unit(HELPERS['own_false'],'p1'),opponent_helper=unit(HELPERS['own_true'],'p2'))
    elif scenario==1:
        anchors=dict(anchor_a=unit(HELPERS['expensive_ground'],'p2',4),anchor_b=unit(HELPERS['cheap_space'],'p1',1))
        helpers=dict(own_helper=unit(HELPERS['own_true'],'p1'),opponent_helper=unit(HELPERS['own_false'],'p2'))
    else:raise ValueError('two frozen scenario families only')
    return dict(**helpers,**anchors,auxiliary=unit(HELPERS['auxiliary'],'p2'))


def worlds():
    result=[]
    for code in CODES:
        for scenario in(0,1):
            for intent in('anchor_a','anchor_b'):
                partition=('train'if scenario==0 else'state_held')if code in TRAIN else('family_held'if scenario==0 else'joint')
                result.append(dict(id=len(result),source_code=code,scenario=scenario,state_family=scenario,intent_ref=intent,
                    requires_target=True,observation_refs=list(ROLES),observation_mode='actual-action-endpoints',partition=partition,
                    template_id=TEMPLATES[code],cohort='paired-program-semantics',max_applies=4,ready_resources=12,
                    own_base_damage=3 if scenario==0 else 1,opponent_base_damage=0,arena_cards=scenario_cards(scenario),
                    selection_mode='exactly-one-upTo'if code in('JTL_140','IBH_104')else'single-target',
                    auxiliary_cap_root=False,primary_pair_excluded=False))
    auxiliary=copy.deepcopy(next(w for w in result if w['source_code']=='LAW_133'and w['scenario']==0 and w['intent_ref']=='anchor_a'))
    auxiliary.update(id=32,own_base_damage=1,auxiliary_cap_root=True,primary_pair_excluded=True)
    result.append(auxiliary)
    return result


def frontend_audit(rows):
    W=E.prior();records={}
    for code in CODES:
        document,audit=E.canonical_document(rows[code]);tokens=W.tokens(document)
        program={k:document[k]for k in('abilities','keywordValues','attachCondition')}
        records[code]=dict(normalized_document=document,canonical_document_sha256=digest(document),normalized_program_group=digest(program),
            semantic_tokens=len(tokens),max_path=max(len(p)for p,_,_ in tokens),cleanup_audit=audit)
    require(len({v['canonical_document_sha256']for v in records.values()})==8,'whole-card equivalent groups require a different frozen split')
    require(not({records[c]['normalized_program_group']for c in TRAIN}&{records[c]['normalized_program_group']for c in HELD}),'program-equivalent groups cross TRAIN/held')
    return dict(schema='jepa-semantic-discrimination-frontend/1',max_tokens=512,max_path=32,width=16,cards=records,
        held_public_syntax_allocated_before_labels=True,held_training_updates=False,truncation=False,
        semantic_validated=False)


def build_plan(catalog,admission,coverage):
    rows={r['setCode']:r for r in catalog['cards']};admitted={r['setCode']:r for r in admission['runtimeAdmittedCards']}
    inventory={c['canonical_id']:c for c in coverage['runtime_admitted_card_inventory']}
    require(set(CODES)<=set(inventory),'source must belong to actual 115-card inventory')
    selected=sorted(set(CODES)|set(HELPERS.values())|{'TOKEN_SHIELD'})
    require(set(selected)-{'TOKEN_SHIELD'}<=set(admitted),'complete normal source/helper native admission required')
    copies={c:int(inventory[c]['main_copies'])for c in CODES};require(sum(copies.values())==50,'actual eight-source copy count changed')
    identities={c:str(rows[c]['card']['id'])for c in CODES}
    require(len(set(identities.values()))==8,'canonical source identities cross split')
    aliases={c:copy.deepcopy(rows[c]['card'].get('setCodes'))for c in CODES}
    for code in CODES:
        require(admitted[code]['implementation']=='sourceIr'and rows[code]==inventory[code]['whole_catalog_row'],'source must retain its exact complete actual-corpus row')
    for name in('cheap_ground','expensive_ground','cheap_space','expensive_space','auxiliary'):
        r=rows[HELPERS[name]];m=r['card'];require(not any(r['abilities'].values())and not r['keywordValues']and not m['unique'],'plain complete endpoint helper required')
        require(m['arena']==('space'if 'space'in name or name=='auxiliary'else'ground'),'helper arena differs')
    require(rows[HELPERS['cheap_ground']]['card']['cost']==rows[HELPERS['cheap_space']]['card']['cost']==2,'cheap threshold profile differs')
    require(rows[HELPERS['expensive_ground']]['card']['cost']==rows[HELPERS['expensive_space']]['card']['cost']==3,'expensive threshold profile differs')
    require(all('vehicle'not in rows[HELPERS[k]]['card']['traits']for k in('cheap_ground','expensive_ground'))and all('vehicle'in rows[HELPERS[k]]['card']['traits']for k in('cheap_space','expensive_space')),'opposed ground/Vehicle selectors differ')
    ws=worlds()
    for w in ws:
        for role,card in w['arena_cards'].items():require(0<=card['damage']<rows[card['code']]['card']['hp'],'initial dead/invalid public fixture: '+role)
    parts={p:[w['id']for w in ws if w['partition']==p]for p in('train','state_held','family_held','joint')}
    require({k:len(v)for k,v in parts.items()}==dict(train=13,state_held=12,family_held=4,joint=4),'frozen33-root split differs')
    pairs=[dict(id=f's{scenario}-{intent}',left_card='IBH_104',right_card='LOF_077',left_root=28+scenario*2+q,right_root=8+scenario*2+q,
        anchor_a='anchor_a',anchor_b='anchor_b',head='target_allowed',expected_D=-2 if scenario==0 else 2,
        nesting='Two intents repeat one public scenario; two scenario families, not four independent worlds.')for scenario in(0,1)for q,intent in enumerate(('anchor_a','anchor_b'))]
    front=frontend_audit(rows)
    return dict(schema=SCHEMA,status='prepared-no-execution',source_revision=REVISION,codes=list(CODES),train_codes=list(TRAIN),heldout_codes=list(HELD),
        cards=[dict(code=c,raw_card=copy.deepcopy(rows[c]),raw_row_sha256=digest(rows[c]),canonical_card_id=identities[c],aliases=aliases[c],
            actual_main_copies=copies[c],declaration_count=inventory[c]['declaration_count'],template_id=TEMPLATES[c],family_id=TEMPLATES[c],
            normalized_program_group=front['cards'][c]['normalized_program_group'])for c in CODES],actual_source_copies=50,
        worlds=ws,helpers=copy.deepcopy(HELPERS),candidate_order=list(ROLES),selected_whole_cards=selected,
        selected_whole_rows={c:copy.deepcopy(rows[c])for c in selected},selected_row_hashes={c:digest(rows[c])for c in selected},
        selected_row_pins={c:dict(sha256=digest(rows[c]),bytes=len(encoded(rows[c])))for c in selected},
        split=dict(root_partitions=parts,train_codes=list(TRAIN),heldout_codes=list(HELD),grouping='All source aliases and exact program-equivalent groups stay together; source0 row is excluded from primary target scoring.'),
        frontend_admission=front,primary_pairs=pairs,expected_cases=33,main_cases=32,auxiliary_cases=[32],max_applies_per_case=4,
        collector_max_engine_applies=128,collector_max_seconds=45,native_build_max_seconds=10,max_rss_bytes=1024**3,cpu_workers=1,
        structural_apply_estimate=dict(single_target_roots=25,upTo_roots=8,single_target_stage_bound=3,upTo_stage_bound=4,total_stage_bound=107,
            caveat='Prelabel dispatcher-stage bound; no action outcomes inferred. Global128 and per-root4 hard stops remain authoritative.'),
        raw_abi=dict(schema='jepa-semantic-discrimination-native/1',journal_schema='jepa-semantic-discrimination-apply-journal/1',
            terminal_classes=['settled-committed','settled-cancelled','unoffered-prompt-only'],
            unavailable='Only an actually reached native target prompt provides membership. No Cancel means observation-only, no target substitution; all future masks unknown.',
            selection='Exactly one offered target then native Done for upTo. No two/three-target or target-set representation claim.'),
        public_binding_contract=dict(task='actual-intent-endpoints',context_width=32,candidate_width=43,legacy_prefix=[18,34],source_width=9,target_width=7),
        primary_scope=dict(eligibility='IBH104 versus LOF077 native offer differences across fixed paired public scenarios.',healing='ASH081 signed surviving damage changes; LAW133 TRAIN own-base heal3 and auxiliary cap1 are measured, not parser labels.',
            source_self='Diagnostic only; no primary source-row scoring or candidate pooling.',death='Removed known only after actual successful committed effect; numeric counters after departure unknown.',
            LAW_true5='Scenario1-only conditional true5 is diagnostic OOD, not positively exercised TRAIN magnitude coverage.'),
        primary_spec=dict(anchors=['anchor_a','anchor_b'],source_self_excluded=True,
            masks={'ASH_081':['target_damage_delta'],'IBH_104':['target_allowed','target_removed']},
            eligibility_pairs=pairs,public_input_match='Require raw and common-TRAIN-scaled X32 plus consumed non-source candidate43 equality within each IBH104/LOF077 pair. Source candidate0 printed cost differs and is not pooled or primary.',
            rank_pairs=[dict(id='ASH081-s1-magnitude',left_root=26,right_root=27,anchors=['anchor_a','anchor_b'],head='target_damage_delta',utility_sign=-1.,requires_both_committed=True,
                require_complete_masks=True,require_nontie_native_utility=True)],rank_direction_accuracy_threshold=.75,
            rank_scope='One nested state pair: negative sum of the two actually observed damage deltas measures healing magnitude regardless of allegiance, not strategic value. World0 ties are excluded upfront. No unexecuted futures imputed.'),
        privacy='Empty decks and opposing hand; own known source only in hand; all five public arena instances represented. No after/menu/parent/hidden identities enter input features.',
        neural_forwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,semantic_validated=False,root_go_required=True)


def prepare_plan():
    """Metadata-only; coordinator calls this inside its reserved stage."""
    gen=KESSEL/'compiler/generated';coverage=HERE.parents[3]/'experiments/actual-corpus/coverage-v2/actual-corpus-coverage.json'
    value=build_plan(json.loads((gen/'cards.json').read_text()),json.loads((gen/'runtime-admission.json').read_text()),json.loads(coverage.read_text()))
    value['source_pins']=[pin(p)for p in(Path(__file__),HERE/'test_semantic_discrimination_plan.py',HERE/'effect_identifiability_fit.py',HERE/'whole_card_encoder.py',coverage,*[gen/n for n in('cards.json','runtime-admission.json','manifest.json','inputs.json','diagnostics.json')])]
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'native-plan.json');a=parser.parse_args()
    require(not a.out.exists(),'preserve prior prepared plans; versioned outputs only')
    value=prepare_plan()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x')as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(plan=pin(a.out),roots=33,source_copies=50,native_applies=0,neural_forwards=0,numerical_fits=0)))


if __name__=='__main__':main()
