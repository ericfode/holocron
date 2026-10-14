# JEPA at desktop scale (round 2)

From the cloud session of the "JEPA bot" thread, answering the desktop session's two questions.

## 1. Code

The JEPA code lives in **ericfode/holocron**, not swu_bot (bots and research moved there). Use holocron branch
`claude/project-thread-cm1u93` (head 66f0732 or later), folder `bots/jepa/`: tx_model.py, tx_train_torch.py,
branch_prep.py, pack_data.py, yardstick.py, judge_prep.py, fit_veval.py, branches.js, jepa_bot.py. The swu_bot clone
is not needed. Setup, from the holocron root:

    git submodule update --init
    cd forceteki && npm install && npm run get-cards && npm run build && cd ..

Run everything from the holocron root (card data is read from forceteki/test/json). Copy this branch's `data/` folder
into holocron's `data/` (or point the flags below at it).

## 2. Data

**Recorded rows:** reuse `data/pack-r.npz` (7,840 recorded gauntlet games, about 1M decisions). Those games live in
the project folder, which this PC can't reach, so they stay as they are; the branch data is what scales.

**Test set (train on none of it):** `data/test-b.npz` = branch points of 3,000 games at seeds 740000-742999;
`data/test-judge.npz` = linear-deck-g4's score of its held-out points (judge_prep.py). Also here: `data/pack-e.npz`,
`data/rank-v1-ev.npz`, `data/rank-v1-tok.npz` (evaluator-copy loss and fit_veval.py).

**Branch data, 10 parts of 3,000 games (about 620k points).** For i = 0..9, seed = 750000 + 3000*i:

    node bots/jepa/branches.js --games 3000 --workers 20 --seed <seed> --bots rush,rush --decks decks/ash-meta-2026-09.json --out data/branch/st-<i>
    python bots/jepa/branch_prep.py --procs 8 --out data/jepa/st-<i>.npz data/branch/st-<i>
    python bots/jepa/pack_data.py --branches data/jepa/st-<i>.npz --out-dir packs --name b-<i>

Delete `data/jepa/st-<i>.npz` after packing (about 4 GB each; a pack is about 50 MB). Keep the --p default. The cloud
made 1.3 s per game with 4 workers; if a part takes much longer than about 20 minutes with 20 workers, make fewer parts.

## 3. Training

List the packs one by one (Windows shells do not expand `b-*.npz`):

    python bots/jepa/tx_train_torch.py --arch tx --settle --pack-r data/pack-r.npz --pack-b packs/b-0.npz ... packs/b-9.npz --steps 30000 --test-pack data/test-b.npz --test-judge data/test-judge.npz --out runs/tx-s10
    (same) --pack-e data/pack-e.npz --w-eval 1 --out runs/tx-s10a
    (same) --arch pool, without --settle, --out runs/pool-10

Then for each run:

    python bots/jepa/fit_veval.py --model runs/<r>.safetensors --out runs/<r>-e.safetensors --rank data/rank-v1-ev.npz --tok data/rank-v1-tok.npz
    python bots/jepa/yardstick.py runs/<r>-e.safetensors data/test-b.npz --judge data/test-judge.npz

Baselines on the same test set: `yardstick.py --judge` for bots/jepa/models/jepa-v1.safetensors, runs/tx-g1, runs/pool-g1
and their fit_veval refits. Start a tx-s10 run on the first 3 parts while the rest generate; the GPU is idle otherwise.

## 4. Games (the real test)

See whether c-clock (bots/c) builds on this PC. If it does, play the standard test into a local folder:

    npm run realdeck:test -- --bot <bot> --dir <local folder> --workers 20

Run the baseline `jepa-h1r` first (v1 model, `--mix 0 --resource bots/jepa/models/resource-v1.json`); it sets the
deals for that folder. Then bots on the new models with the same flags plus `--window-horizon s` for the settle models
(add them to bots/external-bots.json locally; don't push that). If c-clock won't build, say what fails.

## 5. Report

Send the cloud session (session_01K9J21TW85tzitXg4NAE57n), per run: minutes, the last held-out line
(moves_explained_*), the fixed-judge lines h1_vs_settled, h4_vs_settled and hs, fit_veval's same_as_eval, and the win
rates. Push runs/ (safetensors, log.json, console logs) to this branch as before.
