# JEPA training on a GPU (temporary transfer branch)

Code and data to train the transformer JEPA (`--arch tx`) and its pooled twin (`--arch pool`) with PyTorch.
This branch is temporary: it is deleted once the results are back. The code lives in `bots/jepa/` on holocron's
`claude/project-thread-cm1u93` branch.

1. Python 3.10 or newer, then a virtual environment next to this folder:
   `python -m venv .venv`, then `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate`.
2. `pip install numpy torch --index-url https://download.pytorch.org/whl/cu124` for an NVIDIA GPU
   (plain `pip install numpy torch` on a Mac). Check: `python -c "import torch; print(torch.cuda.is_available())"`.
3. Train both (each prints `device cuda`, a line every 100 steps, held-out checks every 500, then the value head and
   the move-ranking yardstick):
   - `python tx_train_torch.py --arch tx --pack-r data/pack-r.npz --pack-b data/pack-b.npz --out runs/tx-g1 --steps 5000`
   - `python tx_train_torch.py --arch pool --pack-r data/pack-r.npz --pack-b data/pack-b.npz --out runs/pool-g1 --steps 5000`
4. Commit `runs/*.safetensors`, `runs/*.log.json` and the console logs to this branch and push.
