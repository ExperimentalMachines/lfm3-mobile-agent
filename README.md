# LFM3-VL-2B Android agent

Post-training LiquidAI **LFM3-VL-2B** into a small, screenshot-only Android agent that runs on the phone, then
comparing it fairly with **GUI-Owl-1.5-2B** and **MAI-UI-2B**.

| | |
|---|---|
| Final model | **LFM3-VL-2B v4**: LoRA fine-tune, shipped as a 4-bit GGUF (1.30 GB with its image projector) |
| Main benchmark | AndroidWorld, 3 held-out seeds × 116 tasks, **preregistered** ([docs/PREREG_v4.md](docs/PREREG_v4.md)) |
| Other benchmarks | MobileWorld (105 tasks), AndroidControl (offline), speed on CPU, Apple M5 and a phone |
| Status | Complete (2026-11-19). Every result was independently re-checked by Codex ([docs/audits.md](docs/audits.md)) |

## Results at a glance

### AndroidWorld, held-out seeds (primary, preregistered)

Same harness for every model: 1 screenshot per step, 4-bit model via llama.cpp, same step budget, temperature 0.

| Model | Seed 7 | Seed 1234 | Seed 2026 | **Total / 348** |
|---|---|---|---|---|
| **LFM3-VL-2B v4 (ours)** | 18 | 17 | 19 | **54 (15.5%)** |
| GUI-Owl-1.5-2B | 16 | 13 | 18 | 47 (13.5%) |
| LFM3-VL-2B v1 (our first model) | 11 | 10 | 11 | 32 (9.2%) |

- **v4 vs GUI-Owl: +2.0 points, 95% CI [−4.5, +8.6], p = 0.60.** Non-inferior at the preregistered −6.9-point
  margin. Superiority is **not** shown.
- **v4 vs v1: +6.3 points, 95% CI [+1.1, +11.5], p = 0.02.**
- The non-inferiority result depends on the preregistered rule that re-runs an episode once if the emulator crashed
  before step 1. 113 of v4's seed-1234 episodes needed it after one emulator hung overnight. Counting them as
  failures instead gives −2.9 points (not non-inferior).
- Codex audit: **valid with caveats**. The caveats are device state carrying over between episodes (all models),
  one disputed v1 success, and limited power: about 57% to show non-inferiority if the models are truly equal.

### MobileWorld (secondary, descriptive; one run per model)

| Model | Successes / 105 |
|---|---|
| GUI-Owl-1.5-2B | **22 (21.0%)** |
| MAI-UI-2B | 11 (10.5%) |
| LFM3-VL-2B v4 | 6 (5.7%) |

- GUI-Owl is clearly better here: v4 − GUI-Owl = −15.2 points, exact McNemar p = 3.05 × 10⁻⁵.
- MAI-UI − v4 = +4.8 points (p = 0.18). MAI-UI's run had more environment failures; see [docs/results.md](docs/results.md#mobileworld).

### Speed (median seconds per step)

| Hardware | **v4** | GUI-Owl-1.5-2B | MAI-UI-2B |
|---|---|---|---|
| CPU, 8 threads (Intel Xeon, idle VM) | **6.4** | 58.0 | 58.2 |
| Apple M5 GPU, inside the AndroidWorld runs | **2.96** | 7.00 | 9.35 (8-bit) |
| Phone CPU (Snapdragon 8 Elite Extreme Gen 6), as evaluated | **~39** | ~1,100 | ~1,063 |

Why v4 is faster: it sends about a third as many prompt tokens per step (a smaller image) and its hybrid architecture
processes them about 3× faster on CPU.

### Development seed 30 (used to pick versions, so not evidence)

| v4 | MAI-UI-2B | GUI-Owl-1.5-2B | Qwen3.5-2B v1 | LFM3 v1 | LFM3 v3 | LFM3 v2 |
|---|---|---|---|---|---|---|
| 18 | **32** | 23 | 16 | 15 | 13 | 3 |

MAI-UI-2B (8-bit, 1 screenshot) scored highest on the development seed but was **not** run on the held-out seeds.

## Read next

| Document | Read it for |
|---|---|
| [docs/results.md](docs/results.md) | Every number, with its source file |
| [docs/evaluation.md](docs/evaluation.md) | How each benchmark was run and kept fair |
| [docs/models.md](docs/models.md) | Model versions v1–v4, training recipe, released artifacts |
| [docs/datasets.md](docs/datasets.md) | Training data, splits, contamination rule |
| [docs/PREREG_v4.md](docs/PREREG_v4.md) | The preregistration and every dated deviation (kept unedited) |
| [docs/audits.md](docs/audits.md) | Every Codex audit and its verdict |
| [docs/infrastructure.md](docs/infrastructure.md) | Where things ran, incidents and fixes |
| [docs/reproduce.md](docs/reproduce.md) | How to recompute every number |
| [docs/repository.md](docs/repository.md) | Repository layout, what moved, history notes |
| [docs/research/](docs/research/) | Literature reviews that shaped the plan |

## Repository layout

| Path | What it holds |
|---|---|
| [`analysis/`](analysis/) | Scripts that compute every reported number from `results/` |
| [`train/`](train/) | Training code: SFT, GRPO, prompt/action format |
| [`data/`](data/) | Dataset builders and fixed split files |
| [`eval/`](eval/) | Benchmark harnesses: AndroidControl, AndroidWorld, MobileWorld, general knowledge |
| [`scripts/`](scripts/) | Run orchestration, by purpose (AndroidWorld, MobileWorld, training, speed, publishing) |
| [`results/`](results/) | Raw results (episode files, predictions) and the summaries computed from them |
| [`logs/`](logs/) | Run logs kept as evidence (model servers, emulators, runs, Codex sessions) |
| [`docs/`](docs/) | Documentation |

## Rules this project kept

- **No AndroidWorld data in training:** no AndroidWorld tasks, variants, trajectories or checkers in any training set.
- **Fair harness:** same screenshot budget, step budget, quantisation and app list for the compared models.
- **Sealed held-out seeds:** results of seeds 7/1234/2026 were not read until every model had finished that seed.
- **Every deviation is dated** in [docs/PREREG_v4.md](docs/PREREG_v4.md), with what had and had not been seen at the time.
- **Exceptions count as failures**, unlike AndroidWorld's default.
