"""Separate initialization-only recovery; preserve every v1 scientific byte/value."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TASK=HERE.parents[3]
ROOT=TASK/"experiments/public-input-binding-v2"
V1_PLAN=TASK/"experiments/public-input-binding-v1/native-plan.json"
V1_PLAN_SHA256="0888fd95b7c3499f533dd2cff5e4e6585519293557dcf48d2e43e57941c67128"
CATALOG=Path("/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/compiler/generated/cards.json")
TOKEN="TOKEN_SHIELD"
TOKEN_ROW_SHA256="677c6916b4cce150b411c83708dcc1af953204fde4191e3a3039891a91a758be"
CATALOG_KEYS={"selected_whole_cards","selected_whole_rows","selected_row_hashes","selected_row_pins"}


def encoded(value):return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()
def pin(path):
    p=Path(path).resolve();b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))


def assert_recovery_invariants(v1,v2):
    for key,value in v1.items():
        if key not in CATALOG_KEYS and v2.get(key)!=value:raise ValueError("v1 scientific value changed: "+key)
    if set(v2)-set(v1)!={"recovery"}:raise ValueError("unreviewed recovery metadata addition")
    if v2["selected_whole_cards"]!=sorted([*v1["selected_whole_cards"],TOKEN]):
        raise ValueError("only mandatory Shield constructor support may be added")
    for key in ("selected_whole_rows","selected_row_hashes","selected_row_pins"):
        if set(v2[key])-set(v1[key])!={TOKEN}:raise ValueError("catalogue support key set differs")
        for code,value in v1[key].items():
            if v2[key].get(code)!=value:raise ValueError("v1 whole row/pin changed: "+code)
    row=v2["selected_whole_rows"][TOKEN]
    if digest(row)!=TOKEN_ROW_SHA256 or row["status"]!="unsupported"or row["card"]["types"]!=["token","upgrade"]:
        raise ValueError("mandatory support must retain the exact original unsupported native token row")
    if v2["selected_row_hashes"][TOKEN]!=TOKEN_ROW_SHA256 or v2["selected_row_pins"][TOKEN]!=dict(sha256=TOKEN_ROW_SHA256,bytes=len(encoded(row))):
        raise ValueError("Shield support deep byte pin differs")


def build_plan(v1,catalog):
    if TOKEN in v1["selected_whole_cards"]:raise ValueError("v1 already contains Shield; recovery premise differs")
    row=next((r for r in catalog["cards"]if r["setCode"]==TOKEN),None)
    if row is None:raise ValueError("mandatory Shield constructor support row absent")
    if digest(row)!=TOKEN_ROW_SHA256:raise ValueError("exact reviewed Shield support row changed")
    result=copy.deepcopy(v1);result["selected_whole_cards"]=sorted([*v1["selected_whole_cards"],TOKEN])
    result["selected_whole_rows"][TOKEN]=copy.deepcopy(row);result["selected_row_hashes"][TOKEN]=TOKEN_ROW_SHA256
    result["selected_row_pins"][TOKEN]=dict(sha256=TOKEN_ROW_SHA256,bytes=len(encoded(row)))
    result["recovery"]=dict(schema="public-input-binding-initialization-recovery/1",scope="Only mandatory catalogue constructor support; no source/world/query/target/hypothesis/predictor/verifier change.",
        v1_plan_sha256=V1_PLAN_SHA256,v1_scientific_values_sha256=digest({k:v for k,v in v1.items()if k not in CATALOG_KEYS}),
        added_constructor_support=[TOKEN],support_is_experimental_card=False,support_preserves_unsupported_status=True,
        expected_physical_shield_instances=0,v1_failure_and_charged_quota_preserved=True,root_go_required=True)
    assert_recovery_invariants(v1,result);return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--out-dir",type=Path,default=ROOT);args=ap.parse_args()
    if pin(V1_PLAN)["sha256"]!=V1_PLAN_SHA256:raise ValueError("immutable v1 plan byte pin differs")
    v1=json.loads(V1_PLAN.read_text())
    expected_catalog=next(p for p in v1["source_pins"]if p["path"]==str(CATALOG))
    if pin(CATALOG)!=expected_catalog:raise ValueError("original full generated catalogue pin differs")
    catalog=json.loads(CATALOG.read_text());result=build_plan(v1,catalog)
    args.out_dir.mkdir(parents=True,exist_ok=True);out=args.out_dir/"native-plan.json";raw=json.dumps(result,indent=2)+"\n"
    if out.exists()and out.read_text()!=raw:raise FileExistsError("preserve recovery plan; no silent replacement")
    if not out.exists():out.write_text(raw)
    print(json.dumps(dict(plan=pin(out),added_support=[TOKEN],scientific_values_unchanged=True,native_applies=0,neural_forwards=0)))


if __name__=="__main__":main()
