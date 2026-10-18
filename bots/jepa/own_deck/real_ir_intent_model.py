"""One typed-intent bottleneck experiment; import is standard-library only.

Only make_model(torch, arm) constructs a model, inside ROOT's sealed worker.
The original model/source stay unchanged. Intent describes a card's nominal
effect; applying it to public state is learned separately, without a physics
oracle. This research module does not qualify a whole-card representation.
"""
import hashlib
import math
from pathlib import Path
from types import MethodType

import real_ir_transfer_model as M

SCHEMA = 'jepa-real-ir-intent-model/1'
IMPLEMENTATION_READY = True
ARMS = ('current', 'matched-aux-latent', 'factorized-intent')
BASE_SHA256 = 'c4383bd88b5a825d82544e02cd7dccd37a0cb533d58f958cf935a9d12a626f8b'
IDENTITY_CLASSES = ('damage', 'heal')
LITERAL_SCALE = 3.
NATIVE_LOSS_COEFFICIENTS = dict(eligibility=.5, endpoint=.5)
AUXILIARY_LOSS_COEFFICIENTS = dict(identity_cross_entropy=.25,
                                    literal_raw_smooth_l1=.25)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def parameter_shapes(arm):
    require(arm in ARMS, 'one fixed intent experiment arm required')
    result = dict(M.parameter_shapes('new-full'))
    if arm != 'current':
        result.update({
            'intent_identity.weight': (2, 8), 'intent_identity.bias': (2,),
            'intent_amount.weight': (1, 8), 'intent_amount.bias': (1,),
            'intent_lift.0.weight': (8, 3), 'intent_lift.0.bias': (8,),
        })
    return result


def base_pin():
    path = Path(M.__file__).resolve()
    raw = path.read_bytes()
    require(path == Path(__file__).resolve().with_name('real_ir_transfer_model.py')
            and hashlib.sha256(raw).hexdigest() == BASE_SHA256,
            'frozen original real-IR model source required')
    return dict(path=str(path), sha256=BASE_SHA256, bytes=len(raw))


def contract():
    return dict(schema=SCHEMA, implementation_ready=IMPLEMENTATION_READY,
        arms=list(ARMS), base_source=base_pin(),
        inputs=dict(program_fields=list(M.PROGRAM_FIELDS),
            candidate_fields=list(M.CANDIDATE_FIELDS),
            source_printed_fields=list(M.PRINTED_FIELDS)),
        parameters={arm: dict(allocated=sum(math.prod(s) for s in parameter_shapes(arm).values()),
            shapes={k: list(v) for k, v in parameter_shapes(arm).items()}) for arm in ARMS},
        outputs=dict(eligibility_logits=['R', 'Q'], signed_damage=['R', 'Q'],
            intent_identity_logits=['R', 2], intent_amount_native=['R'],
            card_effect=['R', 8], application_effect=['R', 8]),
        auxiliary_outputs='Only auxiliary arms expose the two intent outputs; current preserves the original output dictionary.',
        intent=dict(identity_classes=list(IDENTITY_CLASSES),
            encoder='Existing card-only effect(P13[10:13]/[1,1,3]) -> 8.',
            readouts='Learned identity8->2 and nominal literal8->1 in raw native amount units.',
            lift='Concatenate softmax(identity_logits) and predicted nominal literal/3; learned Linear3->8 then Tanh.',
            latent_control='Endpoint receives the original effect8; allocated lift is unused.',
            factorized='Endpoint receives only lifted predicted intent; no original effect8 bypass.'),
        preserved='Eligibility, endpoint, state, S10, HP and knownness inputs and original native masks remain unchanged.',
        hp_scope='HP remains in application. The original selector excludes HP; this does not introduce HP-dependent eligibility.',
        supervision=dict(native=dict(NATIVE_LOSS_COEFFICIENTS),
            auxiliary=dict(AUXILIARY_LOSS_COEFFICIENTS),
            labels='Identity and nominal amount are public TRAIN IR syntax labels, never clipped native delta. Unknowns stay masked.',
            shared='Both auxiliary arms have identical allocated parameters, initial state and auxiliary objective.'),
        initialization='Construct the original model first, then identity, amount and lift in fixed order; load all frozen original keys, clone/check the entire auxiliary initial state across the two auxiliary arms.',
        limits=['No deterministic sign, min, clipping or true-eligibility physics in the learned application.',
            'S10 remains an alternate source-profile shortcut; this is not exclusive causal mediation.',
            'Current has1458 parameters; both auxiliary arms have1517. Active gradient paths differ.',
            'Only a card-effect slot is represented; no whole-card or production qualification.'],
        semantic_validated=False, production_promotion=False)


def make_model(torch, arm):
    """Construct only within the sealed stage; no fitted statistics or I/O labels.

Current is the original object and original forward. Both auxiliary arms retain
all old flat parameter names and append the same six intent parameter names.
Their forward routes differ only at the effect input to the application head.
"""
    require(arm in ARMS, 'one fixed intent experiment arm required')
    base_pin()
    model = M.make_model(torch, 'new-full')
    if arm == 'current':
        return model
    nn = torch.nn
    model.intent_identity = nn.Linear(8, 2)
    model.intent_amount = nn.Linear(8, 1)
    model.intent_lift = nn.Sequential(nn.Linear(3, 8), nn.Tanh())

    def forward(self, program, candidates, printed):
        require(program.ndim == 2 and program.shape[1] == 13 and
                candidates.ndim == 3 and candidates.shape[2] == 17 and
                printed.ndim == 2 and printed.shape[1] == 10 and
                program.shape[0] == candidates.shape[0] == printed.shape[0],
                'exact original P13/C17/S10 common batch required')
        p = program / program.new_tensor(M.P_SCALE)
        c = candidates / candidates.new_tensor(M.C_SCALE)
        s = self.printed(printed / printed.new_tensor(M.S_SCALE))[:, None, :].expand(-1, c.shape[1], -1)
        pc = p[:, None, :].expand(-1, c.shape[1], -1)
        owner = self.owner(torch.cat((pc[..., :2], c[..., :2]), -1))
        kind = self.kind(torch.cat((pc[..., 2:5], c[..., [2, 4, 3]]), -1))
        zone = self.zone(torch.cat((pc[..., 5:8], c[..., 5:9]), -1))
        cap = self.cap(torch.cat((pc[..., 8:10], c[..., 9:12]), -1))
        eligibility = self.selector(torch.cat((owner, kind, zone, cap, s), -1)).squeeze(-1)

        # Card-only paths have no candidate, target state, source profile or ID.
        effect = self.effect(p[:, 10:13])
        identity_logits = self.intent_identity(effect)
        amount_native = self.intent_amount(effect).squeeze(-1)
        if arm == 'factorized-intent':
            decoded = torch.cat((torch.softmax(identity_logits, dim=-1),
                                 amount_native[:, None] / LITERAL_SCALE), -1)
            application_effect = self.intent_lift(decoded)
        else:
            # The matched control allocates the same lift but does not use it.
            application_effect = effect
        state = self.state(c[..., 12:16])
        effect_rows = application_effect[:, None, :].expand(-1, c.shape[1], -1)
        raw = self.endpoint(torch.cat((effect_rows, state, s), -1)).squeeze(-1)
        return dict(eligibility_logits=eligibility,
            signed_damage=raw * torch.sigmoid(eligibility) * candidates[..., 16],
            intent_identity_logits=identity_logits, intent_amount_native=amount_native,
            card_effect=effect, application_effect=application_effect)

    model.forward = MethodType(forward, model)
    return model
