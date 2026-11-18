# LFM3 Android agent — run log

Every training run, evaluation, benchmark and speed measurement of the **lfm3-android** project: post-training
LiquidAI **LFM3-VL-2B** into an on-device, screenshot-only Android agent and comparing it fairly with
**GUI-Owl-1.5-2B** (and **MAI-UI-2B**) on AndroidWorld and MobileWorld.

Numbers in the tables are generated from the working repository's result files by
[`data/build_runs_registry.py`](data/build_runs_registry.py) (machine-readable copy: [`data/runs.json`](data/runs.json));
nothing is typed in by hand. Snapshot: lfm3-android @ c0a6abb, 2026-11-18 14:19.

## Headline (AndroidWorld, 116 tasks, development seed 30, same harness for every model)

| model | successes /116 | answer tasks /25 | action tasks /91 | median s/step (M5) |
|---|---|---|---|---|
| **LFM3-VL-2B v4 (frozen final)** | **18** | 6 | 12 | 2.96 |
| GUI-Owl-1.5-2B (matched: 1 screenshot, Q4_K_M) | 23 | 10 | 13 | 7.0 |
| Qwen3.5-2B v1 | 16 | 0 | 16 | 4.2 |
| LFM3-VL-2B v1 | 15 | 0 | 15 | 2.66 |
| LFM3-VL-2B v3 | 13 | 0 | 13 | 2.61 |
| LFM3-VL-2B v2 | 3 | 0 | 3 | 2.61 |
| Qwen3.5-0.8B v1 | 12 | 0 | 12 | 2.0 |
| LFM2.5-VL-450M v1 | 2 | 0 | 2 | 1.14 |


* **v4 is the frozen "LFM3 final"**: it passed the pre-registered development gate ([PREREG](docs/PREREG_v4.md),
  [gate output](results/v4_gate_seed30.txt)); Codex's independent re-audit: **FREEZE OK**
  ([report](audits/v4_seed30_audit__report.md)).
* v4 fixed the "never answers" failure (0 → 6 answer-task successes) but is still behind GUI-Owl-1.5-2B in the matched
  harness (18 vs 23, exact McNemar p = 0.33 on one seed; GUI-Owl's seed-30 run did not receive the installed-app list
  v4 gets — the sealed runs give both models the list).
* Seed 30 was used to choose between versions: these are **development** numbers. The pre-registered comparison uses
  sealed seeds 7 / 1234 / 2026 ([status](EVALUATIONS.md#sealed-held-out-runs)); no sealed outcome is reported here.
* Speed: on an 8-thread CPU, one agent step takes **6.4 s for v4 vs ~58 s for GUI-Owl-1.5-2B and MAI-UI-2B**
  ([SPEED](SPEED.md)).

## Contents

| file | what |
|---|---|
| [RUNS.md](RUNS.md) | every training run (data revision, recipe, compute, losses, checkpoints) and what each version changed |
| [EVALUATIONS.md](EVALUATIONS.md) | offline evals (AndroidControl, dev splits, retention), AndroidWorld, sealed-run status, MobileWorld, gate and promotion decisions |
| [SPEED.md](SPEED.md) | per-step latency of v4, GUI-Owl-1.5-2B and MAI-UI-2B on identical inputs (CPU) and in real runs (Apple M5) |
| [INFRASTRUCTURE.md](INFRASTRUCTURE.md) | compute used (Colab, Modal, AWS, GCP, Mac), costs, incidents and fixes |
| [AUDITS.md](AUDITS.md) | every Codex adversarial audit with its verdict (full reports in `audits/`) |
| [TIMELINE.md](TIMELINE.md) | every commit of the working repo, in order |
| [docs/](docs/) | pre-registration, evaluation protocol, datasets and splits, GUI-Owl lessons, data plans |
| [research/](research/) | literature reviews that shaped the plan |
| [results/](results/) | gate output, promotion record, export manifests, speed results, MobileWorld snapshot |

## Models and datasets (Hugging Face, private unless noted)

| artifact | repo |
|---|---|
| v4 merged / GGUF | `experimentalmachines/LFM3-VL-2B-AndroidAgent-v4`, `…-v4-GGUF` |
| v4-RL merged / GGUF (not promoted) | `experimentalmachines/LFM3-VL-2B-AndroidAgent-v4-RL`, `…-v4-RL-GGUF` |
| v3, v2 merged + GGUF | `alpharomercoma/LFM3-VL-2B-AndroidAgent-v3(-GGUF)`, `…-v2(-GGUF)` |
| v1 merged + GGUF | `experimentalmachines/LFM3-VL-2B-AndroidControl(-GGUF)` |
| training data | `alpharomercoma/AndroidAgent-SFT-v4` @ 3375539, `…-SFT-v3` @ 565ba76c, `experimentalmachines/AndroidAgent-SFT-v2` (**public**, superseded), `experimentalmachines/AndroidControl-screen-agent-sft` |
| RL state pool | `alpharomercoma/AndroidAgent-RL-v4` @ 9ba36d90 |

Contamination rule for every LFM3 version: no AndroidWorld tasks, variants, trajectories or checkers in training data.
