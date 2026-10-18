"""Export the JEPA context cache and independent move graph, without training.

All tensor operations follow the verified transformer graph. Generated C gets
mechanical symbol prefixes only, so both programs can link into one executable.
"""
import argparse
import ctypes
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

from tinygrad import Tensor, dtypes
from tinygrad.helpers import Context
from tinygrad.nn.state import get_state_dict, safe_load
from tinygrad.uop.ops import Ops
from tinygrad.engine.jit import TinyJit
import extra.export_model as exporter
from extra.export_model import jit_model, compile_net, export_model_clang
from export_jepa import JepaForward, inputs, flat

ROOT = Path(__file__).resolve().parent
WASM = ROOT.parent
OUT = WASM / "generated"
CHECKPOINTS = WASM.parent / "models"
HORIZONS = ["1", "4", "s", "r:face", "r:trade", "r:hold", "r2:face", "r2:trade", "r2:hold"]


class Base(JepaForward):
    def __init__(self, checkpoint):
        self.w = {k:v.to("CPU").realize() for k,v in safe_load(str(checkpoint)).items()}
        self.t, self.dm, self.heads, self.layers = 24, 64, 4, 2

    def value(self, z, prefix="v"):
        return self.lin(prefix+"2", self.lin(prefix+"1", z).relu())


class ContextGraph(Base):
    def forward(self, state, ids, feats, mask):
        b,t,dm,h = 1,24,64,4
        c,hd = t+1,dm//h
        x = self.lin("sin", state).unsqueeze(1).cat(self.lin("tin", feats.cat(self.embed(ids), dim=-1)), dim=1)
        kval = Tensor.ones(b,1).cat(mask, dim=1)
        bias = ((kval-1.0)*1e9).reshape(b,1,1,c)
        cache=[]
        for i in range(self.layers):
            y=self.ln(f"b{i}.ln1",x)
            q=self.lin(f"b{i}.q",y).reshape(b,c,h,hd).transpose(1,2)
            k=self.lin(f"b{i}.k",y).reshape(b,c,h,hd).transpose(1,2)
            v=self.lin(f"b{i}.v",y).reshape(b,c,h,hd).transpose(1,2)
            cache += [k.contiguous(),v.contiguous()]
            att=((q@k.transpose(-2,-1))/math.sqrt(hd)+bias).softmax(-1)
            x=x+self.lin(f"b{i}.o",(att@v).transpose(1,2).reshape(b,c,dm))
            x=x+self.lin(f"b{i}.f2",self.lin(f"b{i}.f1",self.ln(f"b{i}.ln2",x)).relu())
        x=self.ln("lnf",x)
        m=kval.unsqueeze(-1)
        mean=(x*m).sum(1)/m.sum(1)
        z=self.lin("zo2",self.lin("zo1",x[:,0].cat(mean,state,dim=-1)).relu())
        return [z,*cache,self.value(z)]


class PredictGraph(Base):
    def __init__(self, checkpoint, batch):
        super().__init__(checkpoint)
        self.batch=batch

    def forward(self,z,k0,v0,k1,v1,mask,act,aid,horizon):
        b,k,dm,h,hd,c=1,self.batch,64,4,16,25
        x=self.lin("ain",act.cat(self.embed(aid),dim=-1))+self.w["hor"][horizon].reshape(1,1,dm)
        kval=Tensor.ones(1,1).cat(mask,Tensor.ones(1,1),dim=1)
        bias=((kval-1.0)*1e9).reshape(1,1,1,c+1)
        for i,(ck,cv) in enumerate(((k0,v0),(k1,v1))):
            y=self.ln(f"b{i}.ln1",x)
            q=self.lin(f"b{i}.q",y).reshape(b,k,h,hd).transpose(1,2)
            kk=self.lin(f"b{i}.k",y).reshape(b,k,h,hd).transpose(1,2)
            v=self.lin(f"b{i}.v",y).reshape(b,k,h,hd).transpose(1,2)
            scores=(q@ck.transpose(-2,-1)).cat((q*kk).sum(-1,keepdim=True),dim=-1)/math.sqrt(hd)
            att=(scores+bias).softmax(-1)
            a=att[...,:c]@cv+att[...,c:] * v
            x=x+self.lin(f"b{i}.o",a.transpose(1,2).reshape(b,k,dm))
            x=x+self.lin(f"b{i}.f2",self.lin(f"b{i}.f1",self.ln(f"b{i}.ln2",x)).relu())
        x=self.ln("lnf",x)
        zb=z.reshape(1,1,96).expand(1,k,96)
        pred=zb+self.lin("p2",self.lin("p1",zb.cat(x,dim=-1)).relu())
        return [pred,self.value(pred).reshape(k)]


def export_graph(graph, inp, prefix, output_shapes):
    # Realize the output tuple together: the upstream helper realizes outputs
    # one by one and needlessly recomputes the encoder for exported cache views.
    @TinyJit
    def together(*x):
        out=graph.forward(*x)
        Tensor.realize(*out)
        return out
    with Context(JIT=2,CPU_COUNT=1):
        for _ in range(2): out=together(*inp)
    program=together.captured.linear
    outputs=[x.uop.base.realized for x in out]
    def ordered(program):
        for call in program.src:
            assert call.op is Ops.CALL and call.src[0].op in {Ops.SINK,Ops.PROGRAM}
            yield call
    old=exporter.iter_kernel_calls
    try:
        exporter.iter_kernel_calls=ordered
        functions,statements,bufs,saved=compile_net(program,outputs)
    finally:
        exporter.iter_kernel_calls=old
    state=get_state_dict(graph)
    names={(id(b.base),b.offset,b.size,x.dtype):name for name,x in state.items() if (b:=x.uop.base.realized) is not None}
    named={n:names[key] for n,(_,_,key) in bufs.items() if key in names}
    assert set(saved)<=set(named),(set(saved)-set(named))
    assert all(not gs or math.prod(gs)==1 for _,_,gs,_ in statements)
    c,js=export_model_clang(functions,statements,bufs,saved,[f"input{i}" for i in range(len(inp))],
                           [f"output{i}" for i in range(len(outputs))],names,wasm=True)
    # Isolate external C names mechanically; arithmetic and kernel bodies stay generated.
    symbols=set(functions)|{n for n in bufs if n.startswith("buf_")}|{"net","set_buf","bufs"}
    pattern=re.compile(r"\b("+"|".join(sorted(map(re.escape,symbols),key=len,reverse=True))+r")\b")
    c=pattern.sub(lambda m:prefix+"_"+m.group(0),c)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/f"{prefix}.c").write_text(c)
    (OUT/f"{prefix}.js").write_text(js)
    bindings=[{"index":i,"name":name,"bytes":bufs[n][0]} for i,(n,name) in enumerate(named.items())]
    meta={"prefix":prefix,"net":prefix+"_net","set_buf":prefix+"_set_buf","bindings":bindings,
          "inputs":[{"shape":list(x.shape),"dtype":"i32" if x.dtype==dtypes.int else "f32","bytes":bufs[f'input{i}'][0]} for i,x in enumerate(inp)],
          "outputs":[{"shape":shape,"bytes":bufs[f'output{i}'][0]} for i,shape in enumerate(output_shapes)],
          "calls":len(statements),"unique_kernels":len(functions),"scratch_bytes":sum(size for name,(size,_,_) in bufs.items() if name not in named and name.startswith("buf_"))}
    (OUT/f"{prefix}.json").write_text(json.dumps(meta,indent=2))
    print(json.dumps({"export":prefix,"calls":len(statements),"bindings":len(bindings),"scratch_bytes":meta['scratch_bytes']}),flush=True)
    return meta


def make_predict_inputs(ctx, e, start, batch, horizon):
    count=min(batch,e["actions"]["n"]-start)
    acts=e["actions"]["rows"][start*62:(start+count)*62]+[0.]*(62*(batch-count))
    aids=e["actions"]["ids"][start:start+count]+[0]*(batch-count)
    m=inputs(e,e["actions"]["n"])[3]
    return (*ctx[:5],m,Tensor(acts).reshape(1,batch,62),Tensor(aids,dtype=dtypes.int32).reshape(1,batch),Tensor([horizon],dtype=dtypes.int32))


def check_tinygrad(reference):
    reports=[]
    for role,file in (("model","tx-t10.safetensors"),("windowModel","tx-t10-e.safetensors")):
        context=ContextGraph(CHECKPOINTS/file)
        predict=PredictGraph(CHECKPOINTS/file,4)
        for case in reference["vectors"]:
            e=case["encoded"]; expected=case["networks"][role]
            ctx=[x.realize() for x in context.forward(*inputs(e,e['actions']['n'])[:4])]
            ce=max((abs(x-y) for x,y in zip(flat(ctx[0].tolist()),expected['context'].get('z',[]))),default=0.)
            ve=abs(flat(ctx[5].tolist())[0]-expected['context']['valueLogit'])
            err=0.
            for hi,h in enumerate(HORIZONS):
                for start in range(0,e['actions']['n'],4):
                    pred,logit=predict.forward(*make_predict_inputs(ctx,e,start,4,hi))
                    n=min(4,e['actions']['n']-start)
                    ep=expected['predictions'][h].get('latent',[])[start*96:(start+n)*96]
                    el=expected['predictions'][h]['logits'][start:start+n]
                    err=max(err,max((abs(x-y) for x,y in zip(flat(pred.tolist())[:n*96],ep)),default=0.),max(abs(x-y) for x,y in zip(flat(logit.tolist())[:n],el)))
            row={"backend":"tinygrad-cached","role":role,"case":case['name'],"context_error":ce,"context_value_error":ve,"prediction_error":err}
            print(json.dumps(row),flush=True); reports.append(row)
    assert max(max(x['context_error'],x['context_value_error'],x['prediction_error']) for x in reports)<1e-5
    return reports


def build_native(meta):
    prefix=meta['prefix']
    subprocess.run(['clang','-dynamiclib','-O2','-ffp-contract=off','-fno-common',str(OUT/f'{prefix}.c'),'-o',str(OUT/f'{prefix}.dylib')],check=True)


def checkpoint_blobs(path):
    import struct
    blob=path.read_bytes(); n=struct.unpack_from('<Q',blob)[0]; header=json.loads(blob[8:8+n])
    return {k:blob[8+n+v['data_offsets'][0]:8+n+v['data_offsets'][1]] for k,v in header.items() if k!='__metadata__'}


class NativeGraph:
    def __init__(self,meta):
        self.meta=meta; self.lib=ctypes.CDLL(str((OUT/f"{meta['prefix']}.dylib").resolve()))
        self.bind=getattr(self.lib,meta['set_buf']); self.bind.argtypes=[ctypes.c_size_t,ctypes.c_void_p]
        self.net=getattr(self.lib,meta['net']); self.net.argtypes=[ctypes.c_void_p]*(len(meta['inputs'])+len(meta['outputs'])); self.net.restype=None
    def load(self,path):
        blobs=checkpoint_blobs(path); self.keep=[]
        for b in self.meta['bindings']:
            assert b['name'].startswith('w.')
            data=ctypes.create_string_buffer(blobs[b['name'][2:]]); self.keep.append(data); self.bind(b['index'],ctypes.cast(data,ctypes.c_void_p))
    def __call__(self,values):
        ins=[((ctypes.c_int32 if m['dtype']=='i32' else ctypes.c_float)*len(v))(*v) for m,v in zip(self.meta['inputs'],values)]
        outs=[(ctypes.c_float*(m['bytes']//4))() for m in self.meta['outputs']]
        self.net(*outs,*ins)
        return [list(x) for x in outs]


def native_input_values(e):
    t=min(e['tokens']['n'],24)
    return [e['state'],e['tokens']['ids'][:t]+[0]*(24-t),e['tokens']['feats'][:21*t]+[0.]*(21*(24-t)),[1.]*t+[0.]*(24-t)]


def check_native(reference,cm,pm):
    ctxgraph,prgraph=NativeGraph(cm),NativeGraph(pm); reports=[]
    for role,file in (("model","tx-t10.safetensors"),("windowModel","tx-t10-e.safetensors")):
        ctxgraph.load(CHECKPOINTS/file); prgraph.load(CHECKPOINTS/file)
        for case in reference['vectors']:
            e=case['encoded']; expected=case['networks'][role]; vals=native_input_values(e); ctx=ctxgraph(vals)
            ce=max((abs(x-y) for x,y in zip(ctx[0],expected['context'].get('z',[]))),default=0.); ve=abs(ctx[5][0]-expected['context']['valueLogit']); pe=0.
            for hi,h in enumerate(HORIZONS):
                for start in range(0,e['actions']['n'],4):
                    n=min(4,e['actions']['n']-start)
                    acts=e['actions']['rows'][start*62:(start+n)*62]+[0.]*(62*(4-n)); aids=e['actions']['ids'][start:start+n]+[0]*(4-n)
                    pred,logit=prgraph([*ctx[:5],vals[3],acts,aids,[hi]])
                    ep=expected['predictions'][h].get('latent',[])[start*96:(start+n)*96]; el=expected['predictions'][h]['logits'][start:start+n]
                    pe=max(pe,max((abs(x-y) for x,y in zip(pred[:n*96],ep)),default=0.),max(abs(x-y) for x,y in zip(logit[:n],el)))
            row={"backend":"native-c-cached","role":role,"case":case['name'],"context_error":ce,"context_value_error":ve,"prediction_error":pe}
            print(json.dumps(row),flush=True); reports.append(row)
    assert max(max(x['context_error'],x['context_value_error'],x['prediction_error']) for x in reports)<1e-5
    return reports


def main():
    global OUT, CHECKPOINTS
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--models',type=Path,default=CHECKPOINTS)
    ap.add_argument('--reference',type=Path,default=WASM/'tests/fixtures/runtime-reference.json')
    ap.add_argument('--out',type=Path,default=OUT)
    ap.add_argument('--tinygrad-check',action='store_true')
    ap.add_argument('--export',action='store_true',help='export using the first reference observation')
    ap.add_argument('--export-only',action='store_true',help='export fixed shapes using synthetic inputs; no reference needed')
    ap.add_argument('--build-native',action='store_true',help='compile native C shared libraries with local clang')
    ap.add_argument('--native-check',action='store_true')
    a=ap.parse_args(); OUT=a.out.resolve(); CHECKPOINTS=a.models.resolve(); reports=[]
    if not any((a.export,a.export_only,a.tinygrad_check,a.native_check,a.build_native)):
        ap.error('choose --export-only, --export, --tinygrad-check, --build-native or --native-check')
    reference=json.loads(a.reference.read_text()) if (a.export or a.tinygrad_check or a.native_check) else None
    if a.tinygrad_check: reports+=check_tinygrad(reference)
    if a.export or a.export_only:
        # Inputs become real argument buffers. Their values do not specialize any
        # branch: candidate count and context length are the only fixed shapes.
        e=reference['vectors'][0]['encoded'] if a.export else {
            'state':[0.]*73,'tokens':{'n':11,'ids':[0]*11,'feats':[0.]*(11*21)},
            'actions':{'n':4,'ids':[0]*4,'rows':[0.]*(4*62)}}
        cg=ContextGraph(CHECKPOINTS/'tx-t10.safetensors'); cinp=inputs(e,e['actions']['n'])[:4]; ctx=[x.realize() for x in cg.forward(*cinp)]
        cm=export_graph(cg,cinp,'jepa_context',[[1,96],[1,4,25,16],[1,4,25,16],[1,4,25,16],[1,4,25,16],[1,1]])
        pg=PredictGraph(CHECKPOINTS/'tx-t10.safetensors',4); pinp=make_predict_inputs(ctx,e,0,4,0)
        pm=export_graph(pg,pinp,'jepa_predict4',[[1,4,96],[4]])
        manifest={"format":"jepa-cached/1","token_limit":24,"horizons":HORIZONS,"context":cm,"predict4":pm,
                  "checkpoints":{f:hashlib.sha256((CHECKPOINTS/f).read_bytes()).hexdigest() for f in ('tx-t10.safetensors','tx-t10-e.safetensors')}}
        (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
        (OUT/'jepa_cached.h').write_text('''/* Generated ABI; checkpoint tensors retain their original values. */
#include <stddef.h>
/* K/V arrays use contiguous [head=4][context=25][width=16]. */
void jepa_context_set_buf(size_t index, void *ptr);
void jepa_context_net(float *z96, float *k0_1600, float *v0_1600,
    float *k1_1600, float *v1_1600, float *value1,
    float *state73, int *ids24, float *feats504, float *mask24);
void jepa_predict4_set_buf(size_t index, void *ptr);
void jepa_predict4_net(float *latent384, float *logits4,
    float *z96, float *k0_1600, float *v0_1600, float *k1_1600, float *v1_1600,
    float *mask24, float *actions248, int *action_ids4, int *horizon1);
''')
    if a.build_native:
        manifest=json.loads((OUT/'manifest.json').read_text())
        build_native(manifest['context']); build_native(manifest['predict4'])
    if a.native_check:
        manifest=json.loads((OUT/'manifest.json').read_text()); reports+=check_native(reference,manifest['context'],manifest['predict4'])
    if reports: (OUT/'verification.json').write_text(json.dumps(reports,indent=2))


if __name__=='__main__': main()
