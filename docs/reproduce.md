# Reproduce

## Recompute every reported number (minutes, no GPU)

```bash
git clone git@github.com:alpharomercoma/lfm3-android-runs.git && cd lfm3-android-runs
bash analysis/reproduce.sh          # needs Python 3.10+ with numpy; PY=... to pick the interpreter
```

The script re-runs every script in [`analysis/`](../analysis/) and checks each output against the committed version.

| Covered | Not covered |
|---|---|
| Every summary in `results/`, from episode files, request logs, predictions and per-run metric files | Re-scoring raw AndroidControl / general-knowledge predictions into those metric files (use the `eval/` scorers) |
| AndroidWorld analyses without an AndroidWorld install (task metadata is pinned in `data/meta/`) | Training logs, dataset statistics, and the numbers typed into the docs |

| What is regenerated | From |
|---|---|
| AndroidWorld held-out and seed-30 scores, tests, sensitivity, M5 speed | Episode files (`*.pkl.gz`) in `results/androidworld_sealed/` and `results/androidworld/` |
| v4 gate, v4-RL promotion, offline tables | Prediction and metric files in `results/v4_dev/`, `results/v4rl_dev/`, `results/androidcontrol/`, `results/general/` |
| Speed (CPU, phones) | Raw request logs in `results/speed/`, `results/qdc/`, `results/devstream/` |
| MobileWorld | **Skipped** unless `results/mobileworld/traj_r2/` exists: the 8.6 GB of raw trajectories are not in git; the per-task summaries are |

The episode files are Python pickles written by this project's own AndroidWorld harness. Load them only from this
repository.

## Re-run the experiments

These need hardware and accounts the analysis does not:

| Experiment | Needs | Entry point |
|---|---|---|
| Training (SFT) | One GPU (peak use ~11.5 GB; runs used Colab A100 / L4 / G4 and Modal A100 / H100); Hugging Face access to the datasets | [`train/sft_vlm.py`](../train/sft_vlm.py); job configs in [`scripts/training/jobs/`](../scripts/training/jobs/) |
| AndroidControl offline eval | GPU | [`eval/androidcontrol/generate.py`](../eval/androidcontrol/generate.py) → [`score.py`](../eval/androidcontrol/score.py) |
| AndroidWorld | AndroidWorld @ `55ddaf5` cloned to `android_world/` + the two patches in `eval/androidworld/`; Android SDK emulator (API 33); llama.cpp | [`scripts/androidworld/local_sealed_aw_v3.sh`](../scripts/androidworld/local_sealed_aw_v3.sh) `<arm> <seed> <console port> <grpc port> <server port>` |
| MobileWorld | A Linux host with KVM; MobileWorld @ `a026188`; a GPU host for the model server | [`scripts/mobileworld/`](../scripts/mobileworld/) |
| Speed | llama.cpp `cd959bae9` (b12110); the GGUF files | [`scripts/speed/bench_speed.sh`](../scripts/speed/bench_speed.sh) |

Model files (GGUF) live in the Hugging Face repositories listed in [models.md](models.md#released-artifacts).
Local paths in the scripts (`models/`, `tools/`, `android_world/`) are git-ignored.

## Python environments used

| Environment | Used for |
|---|---|
| Python 3 + numpy | Everything in `analysis/` |
| `.venv-aw` (Python 3.11 + AndroidWorld's requirements) | AndroidWorld runs |
| Colab / Modal images pinned in [`scripts/training/colab_bootstrap.py`](../scripts/training/colab_bootstrap.py) and [`scripts/training/modal_app.py`](../scripts/training/modal_app.py) | Training and offline evals (torch 2.14.1, transformers 5.20.2, TRL 1.16.0, PEFT 0.21.2) |
