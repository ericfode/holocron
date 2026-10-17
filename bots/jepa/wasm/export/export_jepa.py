"""Bounded inference/export experiment; no optimizer, training, or checkpoint writes.

Run with the pinned tinygrad source on PYTHONPATH and DEV=CPU:CLANGJIT.
The graph follows Holocron tx_train_torch.run_tx and the pinned checkpoint shapes.
"""
import argparse
import ctypes
import json
import math
from pathlib import Path

from tinygrad import Tensor, dtypes
from tinygrad.nn.state import safe_load
from extra.export_model import jit_model, compile_net, export_model_clang
from tinygrad.helpers import Context
from tinygrad.nn.state import get_state_dict
from tinygrad.uop.ops import Ops
import extra.export_model as exporter
from tinygrad.renderer.cstyle import ClangJITRenderer

# The native CPU C renderer uses `long` for i64; WASM's C ABI has 32-bit long.
# Keep intermediate integer arithmetic (including modulo lowering) explicitly 64-bit.
# This changes type spelling only, not tensor operations or checkpoint values.
ClangJITRenderer.type_map = {**ClangJITRenderer.type_map, dtypes.int64: 'long long', dtypes.uint64: 'unsigned long long'}


class JepaForward:
    def __init__(self, checkpoint, actions, horizons=(0, 1, 2)):
        self.w = {k: v.to('CPU').realize() for k, v in safe_load(str(checkpoint)).items()}
        self.actions, self.horizons = actions, tuple(horizons)
        self.t, self.dm, self.heads, self.layers = 24, 64, 4, 2
        c, hz = 1 + self.t, len(self.horizons)
        s = c + hz * actions
        # Exporter's WASM path retains named model tensors as weights; register constants too.
        self.structural_mask = Tensor([[0.0 if j < c or (i == j and i >= c) else -1e9
                                       for j in range(s)] for i in range(s)]).reshape(1, 1, s, s).realize()
        self.selected_horizons = Tensor(self.horizons, dtype=dtypes.int32).realize()

    def lin(self, name, x):
        return x @ self.w[name + '.w'] + self.w[name + '.b']

    def ln(self, name, x):
        mu = x.mean(-1, keepdim=True)
        variance = ((x - mu) ** 2).mean(-1, keepdim=True)
        return (x - mu) * (variance + 1e-5).rsqrt() * self.w[name + '.g'] + self.w[name + '.b']

    def embed(self, ids):
        return self.w['emb_a'][ids % 64] + self.w['emb_b'][ids // 64] + self.w['emb_c'][(ids * 7 + 3) % 61]

    def forward(self, state, ids, feats, mask, act, aid):
        b, t, k, dm, h = 1, self.t, self.actions, self.dm, self.heads
        hz, hd, c = len(self.horizons), dm // h, t + 1
        x = self.lin('sin', state).unsqueeze(1).cat(self.lin('tin', feats.cat(self.embed(ids), dim=-1)), dim=1)
        av = self.lin('ain', act.cat(self.embed(aid), dim=-1))
        av = (av.unsqueeze(2) + self.w['hor'][self.selected_horizons].reshape(1, 1, hz, dm)).reshape(b, hz * k, dm)
        x = x.cat(av, dim=1)
        kval = Tensor.ones(b, 1).cat(mask, Tensor.ones(b, hz * k), dim=1)
        s = c + hz * k
        bias = ((kval - 1.0) * 1e9).reshape(b, 1, 1, s) + self.structural_mask
        for i in range(self.layers):
            y = self.ln(f'b{i}.ln1', x)
            q = self.lin(f'b{i}.q', y).reshape(b, s, h, hd).transpose(1, 2)
            kk = self.lin(f'b{i}.k', y).reshape(b, s, h, hd).transpose(1, 2)
            v = self.lin(f'b{i}.v', y).reshape(b, s, h, hd).transpose(1, 2)
            att = ((q @ kk.transpose(-2, -1)) / math.sqrt(hd) + bias).softmax(-1)
            x = x + self.lin(f'b{i}.o', (att @ v).transpose(1, 2).reshape(b, s, dm))
            x = x + self.lin(f'b{i}.f2', self.lin(f'b{i}.f1', self.ln(f'b{i}.ln2', x)).relu())
        x = self.ln('lnf', x)
        kv = kval[:, :c].unsqueeze(-1)
        mean = (x[:, :c] * kv).sum(1) / kv.sum(1)
        z = self.lin('zo2', self.lin('zo1', x[:, 0].cat(mean, state, dim=-1)).relu())
        ao = x[:, c:].reshape(b, k, hz, dm)
        zb = z.reshape(b, 1, 1, 96).expand(b, k, hz, 96)
        predicted = zb + self.lin('p2', self.lin('p1', zb.cat(ao, dim=-1)).relu())
        logits = self.lin('v2', self.lin('v1', predicted).relu()).reshape(k, hz)
        return z, predicted, logits


def inputs(encoded, k):
    tokens, actions = encoded['tokens'], encoded['actions']
    used = min(tokens['n'], 24)
    ids = tokens['ids'][:used] + [0] * (24 - used)
    feats = tokens['feats'][:used * 21] + [0.0] * ((24 - used) * 21)
    return (Tensor(encoded['state']).reshape(1, 73), Tensor(ids, dtype=dtypes.int32).reshape(1, 24),
            Tensor(feats).reshape(1, 24, 21), Tensor([1.0] * used + [0.0] * (24 - used)).reshape(1, 24),
            Tensor(actions['rows']).reshape(1, k, 62), Tensor(actions['ids'], dtype=dtypes.int32).reshape(1, k))


def flat(x):
    if isinstance(x, list):
        return [y for v in x for y in flat(v)]
    return [x]


def export_portable(model, inp):
    # This local April snapshot predates upstream's tuple-key fix in export_model.
    # Match compile_net's exact buffer key, as the current upstream exporter does.
    with Context(JIT=2):
        linear, outputs = jit_model(model, *inp)
    # A memory-planned LINEAR sequence can repeat an identical CALL after scratch
    # has changed. A graph toposort deduplicates those calls and changes the model.
    # This verified export boundary accepts flat kernel schedules only.
    def ordered_kernel_calls(program):
        for call in program.src:
            assert call.op is Ops.CALL and call.src[0].op in {Ops.SINK, Ops.PROGRAM}
            yield call
    old_traversal = exporter.iter_kernel_calls
    try:
        exporter.iter_kernel_calls = ordered_kernel_calls
        functions, statements, bufs, saved = compile_net(linear, outputs)
    finally:
        exporter.iter_kernel_calls = old_traversal
    state = get_state_dict(model)
    names = {(id(b.base), b.offset, b.size, x.dtype): name
             for name, x in state.items() if (b := x.uop.base.realized) is not None}
    named = {n: names[key] for n, (_, _, key) in bufs.items() if key in names}
    missing = set(saved) - set(named)
    assert not missing, f'export would lose nonzero constants/weights: {missing}'
    assert len(named) > 50, 'checkpoint weights were not bound'
    assert all(not gs or math.prod(gs) == 1 for _, _, gs, _ in statements), 'export must be single-threaded'
    c, js = export_model_clang(functions, statements, bufs, saved,
                               [f'input{i}' for i in range(len(inp))],
                               [f'output{i}' for i in range(len(outputs))], names, wasm=True)
    return c, js, state, named


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reference', type=Path, default=Path(__file__).resolve().parent.parent / 'tests/fixtures/runtime-reference.json')
    ap.add_argument('--models', type=Path, default=Path(__file__).resolve().parents[2] / 'models')
    ap.add_argument('--export', type=Path)
    args = ap.parse_args()
    reference = json.loads(args.reference.read_text())
    reports = []
    for name, checkpoint in [('model', 'tx-t10.safetensors'), ('windowModel', 'tx-t10-e.safetensors')]:
        for case in reference['vectors']:
            k = case['encoded']['actions']['n']
            model = JepaForward(args.models / checkpoint, k)
            inp = inputs(case['encoded'], k)
            z, pred, logits = model.forward(*inp)
            z, pred, logits = [flat(v.tolist()) for v in (z, pred, logits)]
            expected = case['networks'][name]
            hz = ('1', '4', 's')
            ep = [v for a in range(k) for h in hz for v in expected['predictions'][h].get('latent',[])[a * 96:(a + 1) * 96]]
            el = [expected['predictions'][h]['logits'][a] for a in range(k) for h in hz]
            diff = lambda a, b: max((abs(x - y) for x, y in zip(a, b)),default=0.)
            row = dict(model=name, case=case['name'], z_error=diff(z, expected['context'].get('z',[])),
                       latent_error=diff(pred, ep), logit_error=diff(logits, el))
            print(json.dumps(row), flush=True)
            reports.append(row)
            if args.export and name == 'model' and case['name'] == 'window-p1':
                c, js, state, named = export_portable(model, inp)
                args.export.mkdir(parents=True, exist_ok=True)
                (args.export / 'jepa.c').write_text(c)
                (args.export / 'jepa-wrapper.js').write_text(js)
                # Record pointer names; no generated tensor code is hand-edited.
                (args.export / 'state.json').write_text(json.dumps({n: {'shape': v.shape, 'dtype': str(v.dtype)} for n, v in state.items()}))
                (args.export / 'bindings.json').write_text(json.dumps(named))
                for idx, binding_name in enumerate(named.values()):
                    (args.export / f'weight-{idx}.bin').write_bytes(state[binding_name].data().tobytes())
    assert max(max(r['z_error'], r['latent_error'], r['logit_error']) for r in reports) < 1e-5


if __name__ == '__main__':
    main()
