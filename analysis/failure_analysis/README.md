# Failure analysis (2026-11-22)

Read-only scripts behind [our_failures.md](../../docs/research/notes/training-scale-and-own-attempt-learning/our_failures.md).
They read `results/androidworld/`, `results/mobileworld/` (local, git-ignored trajectories), training logs and server logs.

| Script | What it computes |
|---|---|
| `aw_features.py` | Per-episode features for AndroidWorld runs (intent repeats, waits, no-change taps, ending). Run first: `.venv-aw/bin/python -I analysis/failure_analysis/aw_features.py <out>/aw_features.json` |
| `aw_taxonomy.py`, `aw_taxonomy_lib.py` | Main failure cause per episode, counts per version (writes `aw_taxonomy.json` next to the features file) |
| `aw_paired.py`, `aw_details.py`, `aw_more.py`, `aw_fresh.py`, `fresh2.py` | Paired per-task changes between versions, GUI-Owl-only tasks, detail tables |
| `mw_compare.py`, `mw_tails.py` | MobileWorld v4 vs GUI-Owl: first divergent step, final loops |
| `train_curves.py`, `offline.py`, `ac_preds.py` | Training-loss curves, offline metrics vs online success, AndroidControl premature `status` |
| `latency.py` | Prompt vs decode time per step from llama-server logs |

Write outputs outside the repo (e.g. a temp folder); they are not tracked.
