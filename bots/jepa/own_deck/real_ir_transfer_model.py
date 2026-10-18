"""Three fixed real-IR research arms. Import and contracts are stdlib only.

Only ``make_model(torch, arm)`` constructs a neural module; the sealed fit
worker calls it after its guard starts. No identity, title or code is a field.
The OLD comparator shares inputs, not graph or parameter count, with NEW.
"""
import math

ARMS = ('new-full', 'old-late-fusion', 'new-printed-only')
PROGRAM_FIELDS = ('owner_allowed_self', 'owner_allowed_opponent', 'target_unit_allowed',
    'target_leader_unit_allowed', 'target_base_allowed', 'zone_ground_allowed',
    'zone_space_allowed', 'zone_base_allowed', 'cost_cap_present', 'cost_cap',
    'op_damage', 'op_heal', 'amount')
CANDIDATE_FIELDS = ('owner_self', 'owner_opponent', 'is_unit', 'is_base', 'is_leader',
    'zone_ground', 'zone_space', 'zone_base', 'attackable', 'printed_cost', 'cost_known',
    'cost_applicable', 'damage', 'damage_known', 'hp', 'hp_known', 'is_intended')
PRINTED_FIELDS = ('cost', 'cost_known', 'hp', 'hp_known', 'power', 'power_known',
                  'unique', 'is_event', 'is_unit', 'is_base')
P_SCALE = (1.,)*9 + (4., 1., 1., 3.)
C_SCALE = (1.,)*9 + (4., 1., 1., 4., 1., 10., 1., 1.)
S_SCALE = (4., 1., 10., 1., 10., 1., 1., 1., 1., 1.)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def parameter_shapes(arm):
    require(arm in ARMS, 'fixed arm required')
    if arm == 'old-late-fusion':
        return {'paths.weight': (23, 16), 'values.weight': (16, 1), 'values.bias': (16,),
            'candidate.0.weight': (16, 17), 'candidate.0.bias': (16,),
            'readout.0.weight': (16, 48), 'readout.0.bias': (16,),
            'readout.2.weight': (2, 16), 'readout.2.bias': (2,)}
    result = {}
    for name, width in (('owner', 4), ('kind', 6), ('zone', 7), ('cap', 5),
                        ('printed', 10), ('effect', 3), ('state', 4)):
        result[name + '.0.weight'] = (8, width); result[name + '.0.bias'] = (8,)
    for name, width in (('selector', 40), ('endpoint', 24)):
        result.update({name + '.0.weight': (16, width), name + '.0.bias': (16,),
                       name + '.2.weight': (1, 16), name + '.2.bias': (1,)})
    return result


def contract():
    return dict(schema='jepa-real-ir-transfer-model/1', arms=list(ARMS),
        program_fields=list(PROGRAM_FIELDS), candidate_fields=list(CANDIDATE_FIELDS),
        source_printed_fields=list(PRINTED_FIELDS),
        scales=dict(program=list(P_SCALE), candidate=list(C_SCALE), printed=list(S_SCALE)),
        parameters={a: dict(allocated=sum(math.prod(s) for s in parameter_shapes(a).values()),
            shapes={k: list(v) for k, v in parameter_shapes(a).items()}) for a in ARMS},
        semantic_gate='NEW full versus printed-only has identical shape/initial state; gate all13 semantic fields to0 only.',
        comparator='OLD path/value nonlinear mean pool then own-candidate late fusion, identical P13/C17/S10 inputs; different graph and parameter count.',
        eligibility='NEW owner/kind/zone/cost binders and S10; no intent/operator/amount or candidate damage/HP in eligibility.',
        endpoint='NEW effect/amount and public damage/HP binders plus S10; raw signed output × predicted eligibility × intended equality.',
        metadata_scope='Exactly numeric S10 control, not all printed rules/traits/aspects.',
        semantic_validated=False)


def make_model(torch, arm):
    require(arm in ARMS, 'fixed arm required')
    nn = torch.nn
    def block(width, output=8):
        return nn.Sequential(nn.Linear(width, output), nn.Tanh())
    class RoleBound(nn.Module):
        def __init__(self):
            super().__init__()
            self.owner=block(4); self.kind=block(6); self.zone=block(7); self.cap=block(5)
            self.printed=block(10); self.effect=block(3); self.state=block(4)
            self.selector=nn.Sequential(nn.Linear(40,16),nn.Tanh(),nn.Linear(16,1))
            self.endpoint=nn.Sequential(nn.Linear(24,16),nn.Tanh(),nn.Linear(16,1))
        def forward(self, program, candidates, printed):
            validate(program,candidates,printed)
            p=program / program.new_tensor(P_SCALE)
            if arm == 'new-printed-only':
                p=p*0.
            c=candidates / candidates.new_tensor(C_SCALE)
            s=self.printed(printed / printed.new_tensor(S_SCALE))[:,None,:].expand(-1,c.shape[1],-1)
            p=p[:,None,:].expand(-1,c.shape[1],-1)
            owner=self.owner(torch.cat((p[...,:2],c[...,:2]),-1))
            # Candidate columns have unit/base/leader, while P has unit/leader/base.
            kind=self.kind(torch.cat((p[...,2:5],c[...,[2,4,3]]),-1))
            zone=self.zone(torch.cat((p[...,5:8],c[...,5:9]),-1))
            cap=self.cap(torch.cat((p[...,8:10],c[...,9:12]),-1))
            eligibility=self.selector(torch.cat((owner,kind,zone,cap,s),-1)).squeeze(-1)
            effect=self.effect(p[...,10:13]); state=self.state(c[...,12:16])
            raw=self.endpoint(torch.cat((effect,state,s),-1)).squeeze(-1)
            return dict(eligibility_logits=eligibility,
                signed_damage=raw*torch.sigmoid(eligibility)*candidates[...,16])
    class LateFusion(nn.Module):
        def __init__(self):
            super().__init__()
            self.paths=nn.Embedding(23,16); self.values=nn.Linear(1,16)
            self.candidate=block(17,16)
            self.readout=nn.Sequential(nn.Linear(48,16),nn.Tanh(),nn.Linear(16,2))
        def forward(self, program, candidates, printed):
            validate(program,candidates,printed)
            fields=torch.cat((program/program.new_tensor(P_SCALE),printed/printed.new_tensor(S_SCALE)),-1)
            tokens=torch.tanh(self.paths.weight[None,:,:]+self.values(fields[...,None]))
            p=tokens.mean(1)[:,None,:].expand(-1,candidates.shape[1],-1)
            c=self.candidate(candidates/candidates.new_tensor(C_SCALE))
            out=self.readout(torch.cat((p,c,p*c),-1)); eligibility=out[...,0]
            return dict(eligibility_logits=eligibility,
                signed_damage=out[...,1]*torch.sigmoid(eligibility)*candidates[...,16])
    def validate(p,c,s):
        require(p.ndim==2 and p.shape[1]==13 and c.ndim==3 and c.shape[2]==17 and
                s.ndim==2 and s.shape[1]==10 and p.shape[0]==c.shape[0]==s.shape[0],
                'exact P13/C17/S10 common batch required')
    return LateFusion() if arm == 'old-late-fusion' else RoleBound()
