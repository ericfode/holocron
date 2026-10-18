"""Public metadata reservation only; caller owns a frozen, bounded stage.

No native outcome, numeric dataset, checkpoint or model is opened. Alias identity,
exact programs, numeric-abstracted full programs and selector exposure are separate
claims. Historical declarations include unexecuted proposals conservatively.
"""
import copy
import hashlib
import importlib
import json
import math
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent;TASK=HERE.parents[3];EXP=TASK/'experiments'
CATALOGUE=Path('/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/compiler/generated/cards.json')
RUNTIME=CATALOGUE.with_name('runtime-admission.json')
CATALOGUE_SHA='0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812'
RUNTIME_SHA='91553fdcd7862ebe473bfbbddaf4f17fdf37c2fc7fad7319bf2686d82122a957'
COVERAGE=EXP/'actual-corpus/coverage-v2/actual-corpus-coverage.json'
COVERAGE_SHA='dd3ec9dc77f1f888d070f7e8ed0ab20290c347c75c75f6fe01f5504ce43f0480'
TRAIN=('IBH_013','IBH_066','IBH_061','TWI_174','IBH_059');HELD=('JTL_075','TWI_170')
CODE=re.compile(r'^[A-Z]{3}_[0-9]{3}$')
EXPERIMENT_PLANS=('binding-transfer-fixture-validation-v1/prechange/closed-failure/native-plan-v3.json',
 'binding-transfer-fixture-validation-v1/prechange/native-collector/collection-plan.json','binding-transfer-v2/native-plan.json',
 'binding-transfer-v2/prelaunch-validated-source/native-collector/collection-plan.json','actual-corpus/native-plan.json',
 'ability-correction-v1/native-plan.json','literal-binding/native-plan-v2.json','literal-binding/native-plan.json',
 'compositional-typed-saved-v1/metadata-1/native-plan.json','public-input-binding-v1/native-plan.json',
 'grounded-contrast/core-programs.json','public-input-binding-v2/native-plan.json','native-effect-v2/native-plan.json',
 'transition-replication/core-programs.json','semantic-discrimination-repair-v1/native-plan.json',
 'compositional-typed-v1/metadata-1/native-plan.json','binding-transfer-v1/native-plan-v2.json','binding-transfer-v1/native-plan-v3.json',
 'binding-transfer-v1/prelaunch-26-root-6-source-v2/native-plan-v2.json','binding-transfer-v1/native-plan.json',
 'binding-transfer-v1/prelaunch-24-root-v1/native-plan.json','supported-transition/supported-transition-plan.json',
 'transition-replication/replication-plan.json')
LOCAL_PLANS=('binding-transfer-fixture-evidence','actual_corpus_native_collector','binding_transfer_native_collector',
 'literal_binding_native_collector','grounded_native_collector','native_effect_v2_collector',
 'public_input_binding_recovery_collector','transition_replication_collector','public_input_binding_collector')
MICROPROBE=HERE/'native_microprobe/src/main.rs'


def require(ok,message):
    if not ok:raise ValueError(message)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def pin(path):
    p=Path(path).resolve(strict=True);raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def source_paths():return[EXP/p for p in EXPERIMENT_PLANS]+[HERE/p/'collection-plan.json'for p in LOCAL_PLANS]+[MICROPROBE]
def semantic(value):
    if isinstance(value,dict):return{k:semantic(v)for k,v in value.items()if k!='present'}
    if isinstance(value,list):return[semantic(v)for v in value]
    return value
def exact_program_key(program):return digest(semantic(program))
def mechanism_family_key(program):
    """Abstract numeric amount/cap, never their presence or selector/control shape."""
    value=semantic(copy.deepcopy(program))
    for container,key in((value.get('effect',{}).get('amount',{}),'value'),(value.get('selector',{}).get('cost_cap',{}),'value')):
        if isinstance(container,dict)and container.get(key)is not None:
            require(type(container[key])in(int,float)and math.isfinite(container[key]),'numeric literal required');container[key]='<number>'
    return digest(value)
def raw_template(value,abstract=True):
    """Display title only is removed; every other raw key/list/order is retained."""
    if isinstance(value,dict):return{k:raw_template(v,abstract)for k,v in value.items()if k!='title'}
    if isinstance(value,list):return[raw_template(v,abstract)for v in value]
    if abstract and type(value)in(int,float):require(math.isfinite(value),'finite public literal required');return'<number>'
    return value
def numeric_raw_program_key(ability):return digest(raw_template(ability))
def selector_key(ability):
    """Explicit developmental overlap, not a full-program equivalence claim."""
    resolver=ability.get('targetResolver');effect=ability.get('effect',{})
    if not isinstance(resolver,dict)or not isinstance(effect,dict)or effect.get('kind')not in('damage','heal')or effect.get('target')!='chosen':return None
    value=dict(owner='any',type='any',zone=None,arena=None,predicate=None,optional=False,mode=None,count=None)
    value.update({k:v for k,v in resolver.items()if k not in('promptTitle','promptTitleParts')})
    return digest(dict(selector=raw_template(value),operator=effect['kind'],destination='chosen'))


def alias_index(rows):
    index={};identities={}
    for row in rows:
        code=row['setCode'];require(isinstance(code,str)and bool(code),'primary identifier required')
        require(type(row.get('id'))in(str,int)and bool(str(row['id'])),'canonical source identity required');sid=str(row['id']);names={code}
        card=row['card'];require(isinstance(card,dict),'card metadata required');printings=card.get('setCodes',[])
        require(isinstance(printings,list),'printing aliases must be a list when present')
        for alias in printings:
            require(isinstance(alias,dict)and isinstance(alias.get('set'),str)and re.fullmatch(r'[A-Z]{3}',alias['set'])is not None,'valid printing set required')
            require(type(alias.get('number'))is int and 0<=alias['number']<=999,'numeric printing number required');names.add(f"{alias['set']}_{alias['number']:03d}")
        require(sid not in identities,'duplicate canonical source identity');identities[sid]=dict(code=code,aliases=sorted(names))
        for name in names:require(name not in index or index[name]==code,'ambiguous printing alias');index[name]=code
    return index,identities
def strings(value):
    if isinstance(value,str):return{value}if CODE.fullmatch(value)else set()
    if isinstance(value,list):return set().union(*(strings(v)for v in value))if value else set()
    if isinstance(value,dict):return set().union(*(strings(v)for v in value.values()))if value else set()
    return set()
def plan_exposure(plan):
    sources=set();selected=set();embedded=[]
    for key in('codes','train_codes','heldout_codes','held_codes'):sources|=strings(plan.get(key,[]))
    for key in('cards','programs'):
        records=plan.get(key,[])
        if isinstance(records,dict):sources|={k for k in records if CODE.fullmatch(k)};records=list(records.values())
        for r in records:
            if not isinstance(r,dict):continue
            code=r.get('code',r.get('card',r.get('set_code')))
            if isinstance(code,str)and CODE.fullmatch(code):sources.add(code)
            if isinstance(r.get('raw_card'),dict):embedded.append(r['raw_card'])
    sources|={w['source_code']for w in plan.get('worlds',[])if CODE.fullmatch(str(w.get('source_code','')))}
    for key in('selected_whole_cards','selectedWholeCards','complete_runtime_definition_codes'):selected|=strings(plan.get(key,[]))
    embedded+=list(plan.get('selected_whole_rows',{}).values());selected|=strings(plan.get('helpers',{}))
    selected|={k for k in plan.get('selected_whole_rows',{})if CODE.fullmatch(k)}
    return sources,selected-sources,embedded


def assemble(rows,runtime_codes,plans,coverage,adapter,micro_sources=(),micro_helpers=()):
    """Pure metadata logic, also exercised on synthetic rows by stdlib tests."""
    lookup={r['setCode']:r for r in rows};aliases,identities=alias_index(rows);source_use={};helper_use={};prior_rows=[];token_helpers={}
    def add(mapping,code,path):
        if code in aliases:mapping.setdefault(aliases[code],set()).add(path)
    for path,plan in plans:
        sources,helpers,embedded=plan_exposure(plan);prior_rows.extend((path,r)for r in embedded)
        for token in re.findall(r'"(TOKEN_[A-Z_]+)"',json.dumps({k:plan.get(k)for k in('helpers','selected_whole_cards','complete_runtime_definition_codes')})):token_helpers.setdefault(token,set()).add(path)
        for c in sources:add(source_use,c,path)
        for c in helpers:add(helper_use,c,path)
    for c in micro_sources:add(source_use,c,'earliest-native-microprobe-source')
    for c in micro_helpers:add(helper_use,c,'earliest-native-microprobe-source')
    for c in set(source_use)|set(helper_use):prior_rows.append(('canonical-source/helper-full-row:'+c,lookup[c]))
    programs=[];seen=set();synthetic=set()
    for origin,row in prior_rows:
        if not isinstance(row,dict)or not isinstance(row.get('abilities'),dict):continue
        key=(origin,digest(row))
        if key in seen:continue
        seen.add(key);record=adapter.adapt_row(row);program=record.get('canonical_program')
        if str(row.get('setCode','')).startswith('SYN'):synthetic.add(row['setCode'])
        for side,values in row['abilities'].items():
            for i,ability in enumerate(values):programs.append(dict(origin=origin,code=row.get('setCode'),side=side,index=i,raw_key=numeric_raw_program_key(ability),selector_key=selector_key(ability),
                mechanism_key=mechanism_family_key(program)if program and record['program_adapter_supported']else None))
    candidates=[];train_groups=set();held_groups=set()
    for code in TRAIN+HELD:
        require(code in lookup and code in runtime_codes,'candidate absent from pinned native admission');row=lookup[code];sid=str(row['id']);adapted=adapter.adapt_row(row)
        require(adapted['full_card_supported']is True and adapted['canonical_program']['form']=='chosen-constant','whole real candidate adapter admission failed')
        require(code not in source_use and code not in helper_use,'candidate/alias previously source/helper selected')
        p=adapted['canonical_program'];family=mechanism_family_key(p);ability=row['abilities']['card'][0];rawkey=numeric_raw_program_key(ability)
        raw_overlap=[r for r in programs if r['raw_key']==rawkey];mechanism_overlap=[r for r in programs if r['mechanism_key']==family]
        partition='train'if code in TRAIN else'held';(train_groups if partition=='train'else held_groups).add(family)
        if partition=='held':require(not raw_overlap and not mechanism_overlap,'held full program family has prior source exposure')
        decks=[d for d in coverage['decks']if any(str(c['source_id'])==sid for c in d['main_cards'])]
        candidates.append(dict(code=code,source_id=sid,aliases=identities[sid]['aliases'],partition=partition,whole_row_sha256=digest(row),
            source_hash=row.get('sourceHash'),source_path=row.get('sourcePath'),canonical_program=p,exact_program_key=exact_program_key(p),adapter_family_key=adapted['family_key'],mechanism_family_key=family,numeric_raw_program_key=rawkey,
            prior_raw_full_program_overlaps=raw_overlap,prior_adapter_full_program_overlaps=mechanism_overlap,
            prior_selector_operator_overlaps=[r for r in programs if r['selector_key']is not None and r['selector_key']==selector_key(ability)],
            corpus_copies=sum(c['copies']for d in decks for c in d['main_cards']if str(c['source_id'])==sid),source_deck_indices=[d['source_index']for d in decks]))
        require(adapted['family_key']==exact_program_key(p),'adapter exact-family contract changed')
    require(not(train_groups&held_groups)and len(train_groups)==3 and len(held_groups)==2,'whole numeric-abstracted groups must remain partitioned3/2')
    selected={r['source_id']for r in candidates};deck_coverage=[]
    for d in coverage['decks']:
        cards=[dict(canonical_id=c['canonical_id'],source_id=c['source_id'],copies=c['copies'],proposed_bank_member=str(c['source_id'])in selected)for c in d['main_cards']]
        known=sum(c['copies']for c in cards if c['proposed_bank_member']);total=sum(c['copies']for c in cards)
        require(total==d['total_main_copies'],'no card copies may be dropped');deck_coverage.append(dict(source_index=d['source_index'],family_id=d['family_id'],split=d['split'],total_main_copies=total,proposed_known_copies=known,proposed_unknown_copies=total-known,main_cards=cards))
    exposed=[dict(code=c,source_id=str(lookup[c]['id']),aliases=identities[str(lookup[c]['id'])]['aliases'],source_files=sorted(source_use.get(c,[])),helper_files=sorted(helper_use.get(c,[])))for c in sorted(set(source_use)|set(helper_use))]
    return dict(schema='jepa-real-ir-reservation/1',status='metadata-reserved-no-outcomes',train_codes=list(TRAIN),held_codes=list(HELD),candidates=candidates,prior_declaration_exposure=exposed,
        prior_program_records=programs,prior_synthetic_codes=sorted(synthetic),token_helpers=[dict(code=k,source_files=sorted(v))for k,v in sorted(token_helpers.items())],mechanism_groups=dict(train=sorted(train_groups),held=sorted(held_groups)),deck_coverage=deck_coverage,
        freshness='No selected source/helper or full-program-group overlap within the pinned saved-plan census, including proposals. Entire catalogue IR was previously metadata/parser inspected.',
        held_scope='Two operator-specific event templates share one held any-unit-or-base selector form relative to this TRAIN set. Selector/operator developmental exposure is separately listed; no new primitive claim.',
        semantic_validated=False,native_conformance_verified=False,native_calls=0,neural_calls=0,optimizer_updates=0)


def build_reservation(catalogue=CATALOGUE,runtime=RUNTIME,coverage=COVERAGE,paths=None,adapter=None):
    """Read-only metadata audit; no output/ledger writes. Run only under root GO."""
    paths=source_paths()if paths is None else list(paths);adapter=importlib.import_module('real_ir_adapter')if adapter is None else adapter
    inputs=[Path(catalogue),Path(runtime),Path(coverage),*paths,Path(__file__),Path(adapter.__file__),
        EXP/'grounded-contrast/inventory.json',EXP/'compositional-actual-admission-v1/audit-1/admission-report.json',HERE/'TRANSFER_ATTRIBUTION_DESIGN_REVIEW.md']
    pins=[pin(p)for p in dict.fromkeys(inputs)]
    for p,expected in((catalogue,CATALOGUE_SHA),(runtime,RUNTIME_SHA),(coverage,COVERAGE_SHA)):require(pin(p)['sha256']==expected,'wrong snapshot; do not mix newer main catalogue')
    cat=json.loads(Path(catalogue).read_text());run=json.loads(Path(runtime).read_text());cov=json.loads(Path(coverage).read_text())
    require(len(cat['cards'])==2458 and run['runtimeAdmittedCount']==1178,'exact2458/1178 source universe required')
    plans=[];micro=None
    for path in paths:
        if Path(path).suffix=='.rs':
            text=Path(path).read_text();match=re.search(r'const SELECTED:.*?= \[(.*?)\];',text);require(match is not None,'earliest selected-card declaration missing');micro=set(re.findall(r'"([A-Z]+_[0-9]+)"',match.group(1)))
        else:plans.append((str(Path(path).resolve()),json.loads(Path(path).read_text())))
    require(micro is not None and {'ASH_011','IBH_053'}<=micro,'earliest source/helper evidence required')
    result=assemble(cat['cards'],{r['setCode']for r in run['runtimeAdmittedCards']},plans,cov,adapter,('ASH_011','IBH_053'),micro-{'ASH_011','IBH_053'})
    require(len(result['prior_synthetic_codes'])==32,'all32 historical synthetic programs must be included')
    require(len(result['deck_coverage'])==27 and sum(d['total_main_copies']for d in result['deck_coverage'])==1432,'exact27/1432 corpus retained')
    for p in pins:require(pin(p['path'])==p,'metadata source changed during reservation')
    result.update(input_pins=pins,snapshot=dict(catalogue_rows=2458,runtime_admitted=1178,game_conformance=run['gameConformance']),
        static_discovery=dict(entire_catalogue_previously_parser_inspected=True,source=pin(EXP/'compositional-actual-admission-v1/audit-1/admission-report.json')))
    return result
