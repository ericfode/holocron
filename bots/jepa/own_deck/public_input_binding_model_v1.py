"""Matched public-feature factorial for the effect-head research assay only.

No data collection, fitting, Torch import or forward occurs at import. The
production own-deck encoder is independent and unchanged. C adds generic BEFORE
arena aspect counts/printed aspects; R adds only the declared intended relation.
Neither channel evaluates a rule program, observes an offered action or reads a
future attachment. All four input cells use one allocated parameter graph.
"""
import hashlib
from pathlib import Path
SCHEMA = 'jepa-public-binding-model-inputs/1'
EFFECT_SOURCE_SHA = '90ef1c0c6e2a2626f0d54c1f031fea77a25ea80b9e6e351882cb7ddd38cbd765'
ARMS = ('C0R0','C1R0','C0R1','C1R1')
ASPECTS = ('vigilance','command','aggression','cunning','heroism','villainy')
LEGACY_CONTEXT_WIDTH = 18
LEGACY_CANDIDATE_WIDTH = 34
OWNER_FIELDS = (*('aspect_count_'+a for a in ASPECTS), 'known_aspects')
CONTEXT_EXTENSION = tuple(owner+'_'+field for owner in ('self','opponent') for field in OWNER_FIELDS)
CANDIDATE_CONTENT = (*('aspect_'+a for a in ASPECTS),'known_aspects')
CANDIDATE_RELATION = ('candidate_is_declared_intended_host_or_target','known_intended_relation')
CONTEXT_WIDTH = LEGACY_CONTEXT_WIDTH + len(CONTEXT_EXTENSION)  # 32
CANDIDATE_WIDTH = LEGACY_CANDIDATE_WIDTH + len(CANDIDATE_CONTENT) + len(CANDIDATE_RELATION)  # 43
RECORD_FIELDS = {'before','refs','declared_intent','observation_refs'}


def contract():
    return dict(schema=SCHEMA,arms=list(ARMS),context_width=CONTEXT_WIDTH,candidate_width=CANDIDATE_WIDTH,
        context_prefix_width=18,candidate_prefix_width=34,context_extension=list(CONTEXT_EXTENSION),
        candidate_content_extension=list(CANDIDATE_CONTENT),candidate_relation_extension=list(CANDIDATE_RELATION),
        aspect_vocabulary=list(ASPECTS),dtype='float32',
        metadata_scope='Printed-static reviewed fixtures only; no whole-game dynamic trait/aspect claim',
        count_units='Count distinct present pre-action arena unit instances matching each public predicate',
        normalization='One common C1R1 TRAIN-only transform; zero ablated channels AFTER normalization',
        graph='Shared old typed card16/context16/candidate16; source80→32→9 and branch80→32→7',
        upstream_effect_source_sha256=EFFECT_SOURCE_SHA,
        extra_input_parameters=368,own_deck='Separate production path unchanged; no deck input in this assay',
        unaddressed='No added Jedi/other trait eligibility; retained legacy trait bits remain unchanged',
        task_policy='A dataset has exactly one task; conditional-choose-candidate and actual-intent-endpoints cannot be mixed',
        relation_status='requires_target must be boolean: true enables known reference matching, false is neutral N/A [0,0]; missing is unknown [0,0], other types rejected. Never invent source as intended target.',
        empty_arena='Complete empty owner arena has zero counts/known1; incomplete arena has zero counts/known0',
        semantic_validated=False)


def _metadata(p, rows, family):
    if p is None or p.get('dynamic_'+family) is True: return None
    known_key='printed_'+family
    if known_key in p.get('known',{}) and p['known'][known_key] is not True: return None
    row = rows.get(p.get('code'))
    values = row.get('card',{}).get(family) if isinstance(row,dict) else None
    if not isinstance(values,list) or any(not isinstance(x,str) or not x.strip() for x in values): return None
    values = {x.strip().lower() for x in values}
    if family=='aspects' and not values.issubset(ASPECTS): return None
    witness = p.get('printed_'+family)
    if witness is not None:
        if not isinstance(witness,list) or any(not isinstance(x,str) for x in witness) or {x.strip().lower() for x in witness} != values: return None
    return values


def _reference(p, identity):
    return (isinstance(p,dict) and p.get('id') == identity and p.get('known',{}).get('identity') is True)


def _arena(before, projections, refs):
    """Deduplicate public instances; never inspect private hand/deck contents."""
    units = {}; complete = True
    for role,p in projections.items():
        if p is None: continue
        if not _reference(p,refs.get(role)): raise ValueError('public physical reference mismatch')
        if p.get('known',{}).get('owner') is not True or p.get('owner') not in ('p1','p2'):
            complete = False; continue
        if p.get('is_unit') is not True or p.get('zone') not in ('ground','space') or p.get('present') is not True: continue
        key=p['id']; value=(p['owner'],p['zone'],p.get('code'),p.get('printed_aspects'))
        if key in units and units[key][0] != value: raise ValueError('duplicate public instance disagrees')
        units[key]=(value,p)
    try:
        raw_ids=set()
        for seat in ('p1','p2'):
            player=before['state']['players'][seat]
            for zone in ('ground','space'):
                if not isinstance(player[zone],list): raise ValueError('public arena list required')
                raw_ids.update(u['id'] for u in player[zone])
        complete &= raw_ids == set(units)
    except (KeyError,TypeError): complete=False
    return [units[k][1] for k in sorted(units)],complete


def project_record(record, candidate_order, rows):
    """Only explicit before/refs/intent are read; IDs resolve equality, not features."""
    if set(record) != RECORD_FIELDS: raise ValueError('strict before-only public record required')
    before,refs=record['before'],record['refs']; projections=before['projections']
    source=projections.get('source')
    if not _reference(source,refs.get('source')) or source.get('known',{}).get('owner') is not True or source.get('owner') not in ('p1','p2'):
        raise ValueError('known own source identity/owner required')
    own=source['owner'];opponent='p2' if own=='p1' else 'p1'
    for p in projections.values():
        if p is not None and p.get('zone') in ('deck','hand') and not (p.get('id')==source['id'] and p.get('owner')==own and p.get('zone')=='hand'):
            raise ValueError('only the acting own-hand source and public observations are allowed')
    arena,complete=_arena(before,projections,refs);context=[]
    for owner in (own,opponent):
        units=[p for p in arena if p['owner']==owner]
        aspects=[_metadata(p,rows,'aspects') for p in units]
        known_aspects=complete and all(v is not None for v in aspects)
        context.extend(sum(a in v for v in aspects) if known_aspects else 0 for a in ASPECTS)
        context.append(float(known_aspects))
    intent=record['declared_intent'];intended=refs.get(intent.get('ref'))
    target_requirement=intent.get('requires_target')
    if 'requires_target' in intent and type(target_requirement) is not bool: raise ValueError('requires_target must be a strict boolean when supplied')
    intended_known=(target_requirement is True and intended is not None and intent.get('id')==intended and _reference(projections.get(intent.get('ref')),intended))
    candidates=[]
    for role in candidate_order:
        p=projections.get(role);identity=refs.get(role);aspects=_metadata(p,rows,'aspects')
        if p is not None and not _reference(p,identity): raise ValueError('candidate reference mismatch')
        relation_known=p is not None and intended_known and _reference(p,identity)
        candidates.append([*(float(a in aspects) if aspects is not None else 0. for a in ASPECTS),
            float(aspects is not None),
            float(identity==intended) if relation_known else 0.,float(relation_known)])
    return context,candidates


def _validate_manifest(manifest):
    spec=manifest.get('public_binding_contract',{})
    if spec.get('schema')!=SCHEMA or spec.get('task') not in ('conditional-choose-candidate','actual-intent-endpoints'):
        raise ValueError('one explicit versioned task required')
    if spec.get('aspect_vocabulary')!=list(ASPECTS) or spec.get('metadata_mode')!='printed-static-fixture-only':
        raise ValueError('prelabel fixed metadata vocabulary/scope required')
    if not isinstance(manifest.get('public_catalog_rows'),dict): raise ValueError('full pinned public catalog rows required')
    return spec


def mask_extensions(x,c,input_arm):
    """Apply AFTER the one common TRAIN normalization; no arm-specific fitting."""
    if input_arm not in ARMS: raise ValueError('unknown factorial input cell')
    x=x.copy();c=c.copy()
    if input_arm[1]=='0':
        x[...,18:]=0;c[...,34:34+len(CANDIDATE_CONTENT)]=0
    if input_arm[3]=='0': c[...,34+len(CANDIDATE_CONTENT):]=0
    return x,c


mask_scaled_inputs = mask_extensions


def parameter_counts(symbols,n_train):
    if len(symbols['type'])!=7 or type(n_train) is not int or n_train<1:
        raise ValueError('same seven-type encoder and positive training table required')
    encoder=2560+16*(len(symbols['path'])+len(symbols['value']));identity=16*(n_train+1)
    allocated=9568+identity+16*(len(symbols['path'])+len(symbols['value']))
    controls=('rich-typed','rich-id-only','rich-untrained-typed')
    return dict(allocated=allocated,encoder=encoder,identity=identity,input_parameter_delta=368,
        trainable={arm:allocated-(encoder if arm!='rich-typed' else 0)-(0 if arm=='rich-id-only' else identity) for arm in controls})


def consumed_input_hashes(x,c,representation_signatures,selected):
    """Hash actual normalized/masked forward inputs; no labels/offer masks enter."""
    import numpy as np
    x=np.asarray(x);c=np.asarray(c);selected=np.asarray(selected)
    if x.dtype!=np.float32 or c.dtype!=np.float32 or x.shape!=(len(c),32) or c.ndim!=3 or c.shape[-1]!=43 or len(representation_signatures)!=len(x) or selected.shape!=(len(x),) or selected.dtype.kind not in 'iu':
        raise ValueError('exact consumed forward tensors/signatures required')
    if not np.isfinite(x).all() or not np.isfinite(c).all() or (selected<0).any() or (selected>=c.shape[1]).any():
        raise ValueError('finite inputs and valid declared before-intent indices required')
    def key(signature,global_features,candidate_features):
        if not isinstance(signature,str) or not signature: raise ValueError('explicit typed-tensor or TRAIN-ID/UNK signature required')
        prefix=signature.encode();return hashlib.sha256(len(prefix).to_bytes(8,'little')+prefix+global_features.tobytes()+candidate_features.tobytes()).hexdigest()
    return [dict(source=key(signature,x[i],c[i,selected[i]]),candidate=[key(signature,x[i],row) for row in c[i]]) for i,signature in enumerate(representation_signatures)]


def project_arrays(arrays,manifest,input_arm='C1R1',scalers=None):
    """Return flat x/c; caller fits a single TRAIN transform on raw C1R1 only."""
    import numpy as np
    _validate_manifest(manifest)
    x=np.asarray(arrays['context_features']);c=np.asarray(arrays['candidate_features'])
    if x.dtype!=np.float32 or c.dtype!=np.float32 or x.ndim!=2 or c.ndim!=3 or x.shape[0]!=c.shape[0] or x.shape[1]!=18 or c.shape[2]!=34:
        raise ValueError('unchanged float32 legacy18/34 inputs required')
    records=manifest['public_before_records'];order=manifest['candidate_order']
    if len(records)!=len(x) or len(order)!=c.shape[1] or len(order)!=len(set(order)): raise ValueError('public record/candidate alignment differs')
    extension=[project_record(r,order,manifest['public_catalog_rows']) for r in records]
    xe=np.asarray([r[0] for r in extension],np.float32).reshape(len(x),len(CONTEXT_EXTENSION))
    ce=np.asarray([r[1] for r in extension],np.float32).reshape(len(x),c.shape[1],CANDIDATE_WIDTH-34)
    x=np.concatenate((x,xe),axis=-1);c=np.concatenate((c,ce),axis=-1)
    if not np.isfinite(x).all() or not np.isfinite(c).all(): raise ValueError('nonfinite public input')
    if scalers is not None:
        output=[]
        for values,key in ((x,'context_features'),(c,'candidate_features')):
            center=np.asarray(scalers[key]['center'],np.float32);scale=np.asarray(scalers[key]['scale'],np.float32)
            if center.shape!=(values.shape[-1],) or scale.shape!=center.shape or not np.isfinite(center).all() or not np.isfinite(scale).all() or (scale<=0).any():
                raise ValueError('one complete finite common input transform required')
            output.append((values-center)/scale)
        x,c=output
    elif input_arm!='C1R1':
        raise ValueError('ablations require the common TRAIN normalization before masking')
    return mask_extensions(x,c,input_arm)


def make_model(torch,symbols,n_cards,n_train):
    """Construct only when separately authorized; E.forward itself is unchanged."""
    import effect_identifiability_fit as E
    if hashlib.sha256(Path(E.__file__).read_bytes()).hexdigest()!=EFFECT_SOURCE_SHA: raise ValueError('audited old graph source changed')
    model=E.make_model(torch,symbols,n_cards,n_train)
    model.context[0]=torch.nn.Linear(CONTEXT_WIDTH,16)
    model.candidate[0]=torch.nn.Linear(CANDIDATE_WIDTH,16)
    return model


def configure_arm(model,representation_control='rich-typed'):
    if representation_control not in ('rich-typed','rich-id-only','rich-untrained-typed'): raise ValueError('unknown matched representation control')
    import effect_identifiability_fit as E
    if hashlib.sha256(Path(E.__file__).read_bytes()).hexdigest()!=EFFECT_SOURCE_SHA: raise ValueError('audited old graph source changed')
    E.configure_arm(model,representation_control)
