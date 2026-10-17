"""Export the opt-in original-deck context graph; never overwrite legacy kernels.

New supplemental weights are deterministic untrained engineering scaffolding.
The supplied baseline checkpoints remain byte-identical. No optimizer runs here.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
WASM = ROOT.parent
sys.path.insert(0, str(WASM.parent))
import model as M
import own_deck as O
import own_deck_model as D
import tx_model as X
import export_cached as C
from export_jepa import inputs, flat
from tinygrad import Tensor, dtypes
from tinygrad.nn.state import safe_load


class OwnBase(C.Base):
    def __init__(self, checkpoint, supplemental):
        super().__init__(checkpoint)
        self.w.update({k: v.to("CPU").realize() for k, v in safe_load(str(supplemental)).items()})


class ContextGraph(OwnBase):
    def forward(self, state, ids, feats, mask, deck):
        b,t,dm,h,c,hd = 1,24,64,4,27,16
        identity = deck[..., 50:114] @ self.w["emb_a"] + deck[..., 114:146] @ self.w["emb_b"] + deck[..., 146:207] @ self.w["emb_c"]
        dt = self.lin("din", deck[..., :50].cat(identity, dim=-1)) + self.w["drole"].reshape(1,2,64)
        x = self.lin("sin", state).unsqueeze(1).cat(self.lin("tin", feats.cat(self.embed(ids), dim=-1)), dt, dim=1)
        kval = Tensor.ones(b,1).cat(mask, Tensor.ones(b,2), dim=1)
        bias = ((kval-1)*1e9).reshape(b,1,1,c)
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


class PredictGraph(OwnBase):
    def forward(self,z,k0,v0,k1,v1,mask,act,aid,horizon):
        b,k,dm,h,hd,c = 1,4,64,4,16,27
        x=self.lin("ain",act.cat(self.embed(aid),dim=-1))+self.w["hor"][horizon].reshape(1,1,dm)
        kval=Tensor.ones(1,1).cat(mask,Tensor.ones(1,1),dim=1)
        bias=((kval-1)*1e9).reshape(1,1,1,c+1)
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


def fixture_hello():
    return {"deck":{"deck":[{"id":"SOR_042","count":3},{"id":"SOR_043","count":2}]}, "cards":[
        {"setId":{"set":"SOR","number":42},"setCodes":[{"set":"JTL","number":20}],"cost":2,"power":3,"hp":4,"types":["unit"],"arena":"ground","aspects":["command","command"],"keywords":["raid"],"traits":["Rebel","Trooper"]},
        {"setId":{"set":"SOR","number":43},"setCodes":[],"cost":8,"types":["event"],"aspects":["cunning"],"keywords":[],"traits":[]}]}


def numpy_inputs(encoded):
    import numpy as np
    used=min(encoded["tokens"]["n"],24)
    return (np.asarray(encoded["state"],np.float32).reshape(1,73),
            np.asarray(encoded["tokens"]["ids"][:used]+[0]*(24-used),np.int64).reshape(1,24),
            np.asarray(encoded["tokens"]["feats"][:21*used]+[0.]*(21*(24-used)),np.float32).reshape(1,24,21),
            np.asarray([1.]*used+[0.]*(24-used),np.float32).reshape(1,24))


def write_reference(path, baseline, models, supplemental):
    import numpy as np
    reference=json.loads(baseline.read_text())
    vectors=[]
    for variant in O.VARIANTS:
        # All seven bounded fixtures include a crowded 32-card case and seven actions.
        for source in reference["vectors"]:
            e=copy.deepcopy(source["encoded"])
            e["own_deck"]=O.encode_hello(fixture_hello(),variant)
            ni=numpy_inputs(e)
            n=e["actions"]["n"]
            act=np.asarray(e["actions"]["rows"],np.float32).reshape(1,n,62)
            aid=np.asarray(e["actions"]["ids"],np.int64).reshape(1,n)
            networks={}
            for role,file in (("model","tx-t10.safetensors"),("windowModel","tx-t10-e.safetensors")):
                w,meta=D.load_extended(models/file,supplemental)
                net=D.NumpyOwnDeckTx(w,meta)
                z,pred=net.forward(*ni,act,aid,own_deck=e["own_deck"])
                networks[role]={"context":{"valueLogit":float(net.value(z)[0])},
                    "predictions":{str(h):{"logits":net.value(pred[0,:,hi]).tolist()} for hi,h in enumerate(net.horizons)}}
            vectors.append({"name":variant+"/"+source["name"],"encoded":e,"networks":networks})
    output={"schema":"swu-jepa-own-deck-parity/1","ownDeckHello":fixture_hello(),"provenance":{"engineeringOnly":True,"supplementalSha256":hashlib.sha256(supplemental.read_bytes()).hexdigest(),"baselineReferenceSha256":hashlib.sha256(baseline.read_bytes()).hexdigest(),"checkpoints":{role:{"file":file,"sha256":hashlib.sha256((models/file).read_bytes()).hexdigest()} for role,file in (("model","tx-t10.safetensors"),("windowModel","tx-t10-e.safetensors"))}},"vectors":vectors}
    path.write_text(json.dumps(output,separators=(",",":"))+"\n")
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--models",type=Path,default=WASM.parent/"models")
    p.add_argument("--out",type=Path,default=WASM/"generated-own-deck")
    p.add_argument("--reference",type=Path,default=WASM/"tests/fixtures/runtime-reference.json")
    p.add_argument("--write-reference",type=Path,default=WASM/"tests/fixtures/own-deck-runtime-reference.json")
    p.add_argument("--export",action="store_true")
    p.add_argument("--build-native",action="store_true")
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    C.OUT=args.out.resolve()
    supplemental=args.out/"deck-init.safetensors"
    if not supplemental.exists():
        M.save_safetensors(supplemental,D.supplement(),{"format":D.FORMAT,"own_deck_version":1,"seed":17,"engineering_only":1})
    # Validate the supplement even when already present.
    D.load_extended(args.models/"tx-t10.safetensors",supplemental)
    ref=write_reference(args.write_reference,args.reference,args.models,supplemental)
    if args.export:
        e=ref["vectors"][7]["encoded"] # original/window-p1
        cg=ContextGraph(args.models/"tx-t10.safetensors",supplemental)
        ci=(*inputs(e,e["actions"]["n"])[:4],Tensor(e["own_deck"]["features"]).reshape(1,2,207))
        ctx=[x.realize() for x in cg.forward(*ci)]
        cm=C.export_graph(cg,ci,"jepa_context",[[1,96],*[ [1,4,27,16] for _ in range(4) ],[1,1]])
        pg=PredictGraph(args.models/"tx-t10.safetensors",supplemental)
        pi=(*ctx[:5],ci[3].cat(Tensor.ones(1,2),dim=1),*inputs(e,4)[4:],Tensor([0],dtype=dtypes.int32))
        pm=C.export_graph(pg,pi,"jepa_predict4",[[1,4,96],[4]])
        manifest={"format":"jepa-cached-own-deck/1","engineering_only":True,"token_limit":24,"deck_tokens":2,"deck_input_dim":207,"context_tokens":27,"horizons":C.HORIZONS,"context":cm,"predict4":pm,
            "supplemental":{"file":supplemental.name,"sha256":hashlib.sha256(supplemental.read_bytes()).hexdigest(),"keys":list(D.supplemental_shapes())},
            "checkpoints":{file:hashlib.sha256((args.models/file).read_bytes()).hexdigest() for file in ("tx-t10.safetensors","tx-t10-e.safetensors")}}
        (args.out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
        (args.out/"jepa_cached.h").write_text('''/* Opt-in own-deck v1; legacy ABI is unchanged in generated/. */
#include <stddef.h>
/* K/V contiguous [head=4][context=27][width=16]. Deck rows [2][207]. */
void jepa_context_set_buf(size_t index, void *ptr);
void jepa_context_net(float *z96, float *k0_1728, float *v0_1728,
    float *k1_1728, float *v1_1728, float *value1,
    float *state73, int *ids24, float *feats504, float *mask24, float *deck414);
void jepa_predict4_set_buf(size_t index, void *ptr);
void jepa_predict4_net(float *latent384, float *logits4,
    float *z96, float *k0_1728, float *v0_1728, float *k1_1728, float *v1_1728,
    float *mask26, float *actions248, int *action_ids4, int *horizon1);
''')
    if args.build_native:
        manifest=json.loads((args.out/"manifest.json").read_text())
        C.build_native(manifest["context"])
        C.build_native(manifest["predict4"])


if __name__=="__main__":
    main()
