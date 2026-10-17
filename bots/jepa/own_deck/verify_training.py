"""Run the bounded training/model contract checks and save compact evidence.

Uses already available NumPy/PyTorch. No installs, downloads, game execution or
real-data training. Exactly one synthetic supplemental-only update occurs in
test_torch_matches_numpy_and_updates_only_extra_tensors.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
import test_own_deck


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=Path(__file__).with_name("training-verification.json"))
    args=p.parse_args()
    torch.set_num_threads(1)
    files=[ROOT/"models/tx-t10.safetensors", ROOT/"models/tx-t10-e.safetensors", ROOT/"wasm/generated-own-deck/deck-init.safetensors"]
    before={str(path.relative_to(ROOT)):sha(path) for path in files}
    suite=unittest.defaultTestLoader.loadTestsFromModule(test_own_deck)
    start=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    elapsed=time.monotonic()-start
    after={str(path.relative_to(ROOT)):sha(path) for path in files}
    sources=[ROOT/"own_deck.py",ROOT/"own_deck_model.py",ROOT/"test_own_deck.py",ROOT/"tx_model.py",ROOT/"wasm/export/export_own_deck.py",Path(__file__).resolve()]
    report={"schema":"own-deck-training-verification/1","status":"PASS" if result.wasSuccessful() and not result.skipped and before==after else "FAIL", "testsRun":result.testsRun,"skips":result.skipped,
            "cpuThreads":1,"elapsedSeconds":round(elapsed,4),"syntheticOptimizerUpdates":1,
            "optimizer":"SGD, lr=0.0001, supplemental tensors only", "supplementalParameters":4416,
            "checks":["22 Rust/Python cases: 9,108 f32 coordinates bit-identical", "factorized counts equal copy-weighted shared embeddings", "all 24 live cards remain alongside 2 deck slots", "legacy fixture logits unchanged within 0.00001", "state/action/value and cached predictions retain original-deck context", "PyTorch versus NumPy z/pred/value parity", "finite nonzero gradients for all 3 supplemental tensors", "base tensors unchanged after synthetic update", "post-update full and supplemental-only checkpoint round-trips"],
            "python":platform.python_version(),"numpy":np.__version__,"torch":torch.__version__,"device":"cpu",
            "sourceSha256":{str(path.relative_to(ROOT)):sha(path) for path in sources},
            "inputSha256":{str(path.relative_to(ROOT)):sha(path) for path in [ROOT/"wasm/controller/fixtures/own-deck-contract.json",ROOT/"wasm/tests/fixtures/runtime-reference.json",ROOT/"wasm/tests/fixtures/own-deck-runtime-reference.json"]},
            "immutableBefore":before,"immutableAfter":after,
            "limitations":["Synthetic update proves gradient and serialization wiring only; no strength claim.","Remaining row has no observation ledger and is explicitly unknown."]}
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    if report["status"]!="PASS":
        raise SystemExit(1)


if __name__=="__main__": main()
