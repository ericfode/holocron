"""One endpoint-HP input projection over the unchanged PR45 NEW model.

No Torch import or model construction at import. The caller must construct and
use models only inside its sealed numerical stage. This is an effect-decoder
dependency correction, not a new whole-card encoder or deterministic interpreter.
"""
import hashlib
from pathlib import Path

import real_ir_transfer_model as M

SCHEMA='jepa-real-ir-hp-projection-model/1'
ARMS=('baseline','effect-hp-invariant')
BASE_SHA256='c4383bd88b5a825d82544e02cd7dccd37a0cb533d58f958cf935a9d12a626f8b'


def base_pin():
    path=Path(M.__file__).resolve()
    M.require(path==Path(__file__).resolve().with_name('real_ir_transfer_model.py'),'exact sibling base-model source required')
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    M.require(digest==BASE_SHA256,'frozen PR45 model source changed')
    return dict(path=str(path),sha256=digest,bytes=len(raw))


def project_endpoint_state(_module,inputs):
    """Pre-hook: clone [R,Q,4], zero HP column2; retain every other value."""
    M.require(isinstance(inputs,tuple)and len(inputs)==1,'one endpoint-state input required')
    value=inputs[0];shape=getattr(value,'shape',())
    M.require(len(shape)==3 and shape[-1]==4,'endpoint state must be [R,Q,4]')
    projected=value.clone()
    projected[...,2]=0.
    return(projected,)


def contract():
    base=M.contract()
    return dict(schema=SCHEMA,arms=list(ARMS),base_source=base_pin(),base_arm='new-full',
        program_fields=base['program_fields'],candidate_fields=base['candidate_fields'],
        source_printed_fields=base['source_printed_fields'],scales=base['scales'],
        parameters=base['parameters']['new-full'],added_parameters=0,
        projection=dict(module='state',hook='register_forward_pre_hook',input_shape=['R','Q',4],
            input_columns=['scaled_damage','damage_known','scaled_hp','hp_known'],zero_columns=[2],
            originating_candidate_column=14,physical_scale=10.,original_input_mutated=False),
        unchanged=['HP knownness','S10 printed input/embedding','eligibility path','operator and literal amount',
            'intended equality','parameter names/shapes/count','random initialization draws','optimizer interface'],
        active_path_limit='HP input-weight example gradients are suppressed; allocated weights remain and the same optimizer may apply weight decay.',
        card_effect_api=dict(module='effect',input='scaled P13[...,10:13]',input_fields=['op_damage','op_heal','amount'],
            output_width=8,dependencies='Card program only; already present in PR45. No extra effect forward is performed by this wrapper.'),
        scope='Single endpoint input-dependency projection; no new card embedding, analytical selector, sign rule, clipping rule or full-card support.',
        semantic_validated=False)


def make_model(torch,arm):
    """Return the original model directly, with one pre-hook in the corrected arm."""
    M.require(arm in ARMS,'fixed HP-projection arm required');base_pin()
    model=M.make_model(torch,'new-full')
    if arm=='effect-hp-invariant':
        model.state.register_forward_pre_hook(project_endpoint_state)
    return model
