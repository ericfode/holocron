"""Small role-bound model for a synthetic typed-program factorial only.

Import, parsing, contract and parameter accounting use the standard library.
Only make_model constructs Torch modules, inside a separately sealed stage.
No selector truth, analytical outcome, card identity or title enters fields.
"""
import ast
import hashlib
import math
from pathlib import Path

SCHEMA = 'jepa-compositional-typed-model/1'
FIELD_NAMES = ('owner_any','owner_opponent','arena_ground','arena_space','cost_cap',
               'op_damage','op_heal','amount')
CANDIDATE_NAMES = ('owner_self','owner_opponent','arena_ground','arena_space',
                   'printed_cost','damage','hp','is_intended')
BIT_NAMES = ('owner_opponent','arena_space','cap_is_3','amount_is_3','op_heal')
FIELD_SCALES = (1.,1.,1.,1.,4.,1.,1.,3.)
CANDIDATE_SCALES = (1.,1.,1.,1.,4.,4.,10.,1.)


def require(ok, message):
    if not ok: raise ValueError(message)


def finite(value):
    require(type(value) in (int,float), 'finite numeric public field required')
    try: require(math.isfinite(value), 'finite numeric public field required')
    except OverflowError as error: raise ValueError('finite numeric public field required') from error
    return float(value)


def _keys(value, allowed):
    require(isinstance(value,dict) and not set(value)-set(allowed), 'unreviewed typed field')


def encode_program(raw):
    """Extract the eight fields from actual restricted IR, never code labels.

    The restricted task is one event, one unit target, cost<=cap, and one
    chosen-target damage/heal effect. Optionality concerns the collection
    protocol and is not an eligibility/outcome feature; no extra effects exist.
    """
    if 'abilities' in raw:
        abilities=raw['abilities']
        require(set(abilities)=={'card','unit','leader'} and not abilities['unit'] and
                not abilities['leader'] and len(abilities['card'])==1, 'one main event program required')
        raw=abilities['card'][0]
    _keys(raw,('trigger','title','contextTitle','promptTitle','costs','optional','targetResolver','effect'))
    require(raw.get('trigger')=='event' and raw.get('costs',[])==[], 'one event with no additional ability costs required')
    require('optional'not in raw or type(raw['optional'])is bool, 'strict optional boolean required')
    resolver=raw['targetResolver'];_keys(resolver,('owner','type','zone','arena','predicate'))
    owner,arena=resolver['owner'],resolver['arena']
    require(owner in ('any','opponent') and arena in ('ground','space') and
            resolver.get('type')=='unit' and resolver.get('zone')=='arena', 'restricted owner/unit/arena selector required')
    predicate=resolver['predicate'];_keys(predicate,('kind','op','left','right'))
    require(predicate.get('kind')=='binary' and predicate.get('op')=='<=' and
            predicate.get('left')==dict(kind='ref',path=['card','cost']), 'literal printed-cost <= predicate required')
    right=predicate['right'];_keys(right,('kind','value'))
    require(right.get('kind')=='const' and type(right.get('value'))is int and right['value']in(2,3), 'cap literal2/3 required')
    effect=raw['effect'];_keys(effect,('kind','target','amount'))
    op=effect['kind'];amount=effect['amount'];_keys(amount,('kind','value'))
    require(op in ('damage','heal') and effect.get('target')=='chosen' and
            amount.get('kind')=='const' and type(amount.get('value'))is int and amount['value']in(1,3),
            'chosen damage/heal literal1/3 required')
    return [float(owner=='any'),float(owner=='opponent'),float(arena=='ground'),float(arena=='space'),
            float(right['value']),float(op=='damage'),float(op=='heal'),float(amount['value'])]


def extract_program_bits(raw):
    f=encode_program(raw)
    return [int(f[1]),int(f[3]),int(f[4]==3),int(f[7]==3),int(f[6])]


program_fields=encode_program


def encode_candidate(record,intended_id,acting_owner='p1'):
    """Only a complete present public unit; unknown fields reject, never zero-fill."""
    require(acting_owner in ('p1','p2') and isinstance(intended_id,str) and intended_id,
            'known acting owner and pre-action intended identity required')
    require(record.get('present')is True and record.get('is_unit')is True and
            record.get('zone')in('ground','space'), 'present public arena unit required')
    known=record.get('known',{})
    require(all(known.get(k)is True for k in('identity','owner','printed_cost','damage','hp')),
            'complete identity/owner/cost/damage/HP public knowledge required')
    identity,owner=record.get('id'),record.get('owner')
    require(isinstance(identity,str)and identity and owner in('p1','p2'), 'public identity/owner malformed')
    cost,damage,hp=(finite(record.get(k))for k in('printed_cost','damage','hp'))
    require(cost in(2.,3.,4.)and hp==10. and 0<=damage<hp, 'candidate outside fixed cost2/3/4, HP10 live-unit contract')
    return [float(owner==acting_owner),float(owner!=acting_owner),float(record['zone']=='ground'),
            float(record['zone']=='space'),cost,damage,hp,float(identity==intended_id)]


def parameter_metadata(n_train_identities=16):
    require(type(n_train_identities)is int and 1<=n_train_identities<=32, 'bounded TRAIN identity table required')
    shapes={'owner.0.weight':[8,4],'owner.0.bias':[8],'arena.0.weight':[8,4],'arena.0.bias':[8],
        'cost.0.weight':[8,2],'cost.0.bias':[8],'effect.0.weight':[8,3],'effect.0.bias':[8],
        'state.0.weight':[8,2],'state.0.bias':[8],'identity.weight':[n_train_identities+1,8],
        'selector.0.weight':[16,32],'selector.0.bias':[16],'selector.2.weight':[1,16],'selector.2.bias':[1],
        'endpoint.0.weight':[16,24],'endpoint.0.bias':[16],'endpoint.2.weight':[1,16],'endpoint.2.bias':[1]}
    count=sum(math.prod(shape)for shape in shapes.values())
    require(count<=5000,'fixed new-model parameter ceiling exceeded')
    return dict(allocated=count,trainable=count,named_weight_shapes=shapes,identity_parameters=8*(n_train_identities+1),
        identity_gate='0/1 changes no allocated/trainable tensor shapes; inactive gradient paths differ',
        held_identity='One UNK0 row; no separate held-ID allocation or identity in semantic fields')


def source_fingerprint():
    source=Path(__file__).read_bytes()
    tree=ast.parse(source);functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in
                                    ('encode_program','encode_candidate','make_model')]
    return dict(sha256=hashlib.sha256(source).hexdigest(),bytes=len(source),
                contract_ast_sha256=hashlib.sha256(ast.dump(ast.Module(body=functions,type_ignores=[]),include_attributes=False).encode()).hexdigest())


def contract(n_train_identities=16):
    return dict(schema=SCHEMA,fields=dict(shape=['R',8],dtype='float32',columns=list(FIELD_NAMES),scales=list(FIELD_SCALES)),
        candidates=dict(shape=['R','Q',8],dtype='float32',columns=list(CANDIDATE_NAMES),scales=list(CANDIDATE_SCALES)),
        identity_indices=dict(shape=['R'],dtype='int64',minimum=0,maximum=n_train_identities,held=0),
        outputs=dict(eligibility_logits=['R','Q'],signed_damage=['R','Q']),
        widths=dict(role=8,hidden=16),parameters=parameter_metadata(n_train_identities),
        dependencies=dict(eligibility=['owner requirement/public owner','arena requirement/public arena','cost cap/public cost','optional identity'],
            endpoint=['operator','amount','public damage/HP','optional identity','predicted eligibility','declared intended equality']),
        routing='eligibility excludes intent/operator/amount/damage/HP; endpoint=raw_signed_output*sigmoid(eligibility_logits)*is_intended',
        input_policy='Raw natural units. Fixed physics scales applied internally; no fitted public transform or selector/outcome truth input.',
        scope='Synthetic event factorial only; this is an encoding plus causal-routing comparison, not production integration.',
        semantic_validated=False)


def make_model(torch,n_train_identities=16,identity_enabled=False):
    """Construct only inside the root-authorized sealed numerical stage."""
    parameter_metadata(n_train_identities)
    require(type(identity_enabled)is bool,'identity gate must be a fixed boolean')
    nn=torch.nn
    class CompositionalTyped(nn.Module):
        def __init__(self):
            super().__init__();self.identity_enabled=identity_enabled
            def binder(width):return nn.Sequential(nn.Linear(width,8),nn.Tanh())
            self.owner=binder(4);self.arena=binder(4);self.cost=binder(2)
            self.effect=binder(3);self.state=binder(2)
            self.identity=nn.Embedding(n_train_identities+1,8,padding_idx=0)
            self.selector=nn.Sequential(nn.Linear(32,16),nn.Tanh(),nn.Linear(16,1))
            self.endpoint=nn.Sequential(nn.Linear(24,16),nn.Tanh(),nn.Linear(16,1))

        def forward(self,fields,candidates,identity_indices=None):
            require(fields.ndim==2 and fields.shape[1]==8 and candidates.ndim==3 and
                    candidates.shape[0]==fields.shape[0]and candidates.shape[2]==8,'exact fields/candidates tensor shapes required')
            if identity_indices is None:
                identity_indices=torch.zeros(len(fields),dtype=torch.long,device=fields.device)
            require(identity_indices.shape==(len(fields),),'one identity index per row required')
            q=candidates.shape[1];f=fields[:,None,:].expand(-1,q,-1)
            identity=self.identity(identity_indices)[:,None,:].expand(-1,q,-1)*float(self.identity_enabled)
            owner=self.owner(torch.cat((f[...,:2],candidates[...,:2]),-1))
            arena=self.arena(torch.cat((f[...,2:4],candidates[...,2:4]),-1))
            cost=self.cost(torch.stack((f[...,4]/4.,candidates[...,4]/4.),-1))
            eligibility=self.selector(torch.cat((owner,arena,cost,identity),-1)).squeeze(-1)
            effect=self.effect(torch.cat((f[...,5:7],f[...,7:8]/3.),-1))
            state=self.state(torch.stack((candidates[...,5]/4.,candidates[...,6]/10.),-1))
            raw=self.endpoint(torch.cat((effect,state,identity),-1)).squeeze(-1)
            endpoint=raw*torch.sigmoid(eligibility)*candidates[...,7]
            return dict(eligibility_logits=eligibility,signed_damage=endpoint)
    return CompositionalTyped()
