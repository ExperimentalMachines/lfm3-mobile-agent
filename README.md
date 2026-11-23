# LFM3-VL-2B Android agent

Post-training LiquidAI **LFM3-VL-2B** into a small, screenshot-only Android agent that runs on the phone, then
comparing it fairly with **GUI-Owl-1.5-2B** and **MAI-UI-2B**.

| | |
|---|---|
| Final model | **LFM3-VL-2B v4**: LoRA fine-tune, shipped as a 4-bit GGUF (1.30 GB with its image projector) |
| Main benchmark | AndroidWorld, 3 held-out seeds × 116 tasks, **preregistered** ([docs/PREREG_v4.md](docs/PREREG_v4.md)) |
| Other benchmarks | MobileWorld (105 tasks), AndroidControl (offline), speed on CPU, Apple M5 and a phone |
| Status | Complete (2026-11-19). The headline results were independently re-checked by Codex ([docs/audits.md](docs/audits.md)) |
| Follow-up | v4.1–v4.3 (2026-11-21 to 23, development benchmarks only): no reliable gain over v4, so **v4 stays the evaluated model** ([below](#follow-up-rounds-development-only)) |

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
- **v4's lead comes from templates whose goal text cannot change with the seed.** Seed 30 was used to pick v4. On
  the 78 templates whose goal text does change, v4 and GUI-Owl are level: 32 vs 33, CI [−8.2, +7.3], so
  non-inferiority is not shown on that subset.
- Codex audit: **valid with caveats**. The caveats:
  - device state carries over between episodes (all models);
  - two disputed checker successes, one v4 and one v1 (counting both as failures leaves the conclusion unchanged);
  - limited power: about 57% to show non-inferiority if the models are truly equal.

### MobileWorld (secondary, descriptive; one run per model)

| Model | Successes / 105 |
|---|---|
| GUI-Owl-1.5-2B | **22 (21.0%)** |
| MAI-UI-2B | 11 (10.5%) |
| LFM3-VL-2B v4 | 6 (5.7%) |

- GUI-Owl is clearly better here: v4 − GUI-Owl = −15.2 points, exact McNemar p = 3.05 × 10⁻⁵.
- MAI-UI − v4 = +4.8 points (p = 0.18). MAI-UI's run had more environment failures; see [docs/results.md](docs/results.md#mobileworld).

### Speed (median seconds per step; small pilot measurements)

| Hardware | **v4** | GUI-Owl-1.5-2B | MAI-UI-2B |
|---|---|---|---|
| CPU, 8 threads (Intel Xeon, idle VM); 4-bit; calls kept 14 / 4 / 4 | **6.4** | 58.0 | 58.2 |
| Apple M5 GPU, every step of the seed-30 runs (1,706–2,228 steps each) | **2.96** | 7.00 | 9.35 (8-bit) |
| Phone CPU (Snapdragon 8 Elite Extreme Gen 6), as evaluated; calls 10 / 2 / 2 | **~39** | ~1,100 | ~1,063 (8-bit) |

- In the CPU test v4 used about a third as many prompt tokens per step (a smaller image) and showed about 3× the
  prompt throughput. The tests compare whole pipelines and do not isolate the cause.
- At an equal 1,024-token image ceiling on the phone, GUI-Owl and MAI-UI take ~198 s and ~183 s; their accuracy
  at that ceiling was not measured.

### Development seed 30 (used to pick versions, so not evidence)

| v4 | MAI-UI-2B | GUI-Owl-1.5-2B | Qwen3.5-2B v1 | LFM3 v1 | LFM3 v3 | LFM3 v2 |
|---|---|---|---|---|---|---|
| 18 | **32** | 23 | 16 | 15 | 13 | 3 |

MAI-UI-2B (8-bit, 1 screenshot) scored highest on the development seed but was **not** run on the held-out seeds.

### Follow-up rounds (development only)

Rules fixed in advance in [docs/PREREG_v41.md](docs/PREREG_v41.md). No follow-up version was run on the held-out seeds.

| Version | What changed | Seed 30 / 116 | MobileWorld / 105 | Outcome |
|---|---|---|---|---|
| v4 | Reference | 18 | 6 | — |
| v4.1 | `wait` labels fixed + recovery-history augmentation | 12 | — | Worse (+2 / −8 vs v4) |
| v4.2 | v4.1 + the model's own replayed history (DAgger-style, offline) | 18 | 8 (p 0.63 vs v4) | Loops halved, success level; reference for round 5 |
| v4.3-dpo | v4.2 + DPO on all 4,163 of its own mistakes | not run | — | Failed offline (action types collapsed) |
| v4.3-dpo2 | v4.2 + DPO on 851 balanced stop / copied-intent mistakes | 21 | — | Failed online (+3 vs v4.2) |
| v4.3-sft | v4.2 + 500 more SFT steps on the same mix | 24 | — | Failed online (+6 vs v4.2; false `complete` 25 → 37) |

- Two passes of the same model (v4.2) differ on 9 tasks, so one seed-30 pass cannot detect gains smaller than about
  9 tasks. That was the pass bar.
- Details: [docs/results.md](docs/results.md#round-5-learning-from-own-mistakes-vs-more-training-pre-registered-2026-11-22),
  [docs/models.md](docs/models.md#versions-at-a-glance). All follow-up models are public on Hugging Face, marked experimental.

## Read next

| Document | Read it for |
|---|---|
| [docs/results.md](docs/results.md) | All results, each with its source file |
| [docs/evaluation.md](docs/evaluation.md) | How each benchmark was run and kept fair |
| [docs/models.md](docs/models.md) | Model versions v1–v4.3, training recipe, released artifacts |
| [docs/datasets.md](docs/datasets.md) | Training data, splits, contamination rule |
| [docs/PREREG_v4.md](docs/PREREG_v4.md) | The preregistration and every dated deviation (kept unedited) |
| [docs/PREREG_v41.md](docs/PREREG_v41.md) | Follow-up rounds v4.1–v4.3: plans, gates and dated log (append-only) |
| [docs/audits.md](docs/audits.md) | Every Codex audit and follow-up review, with its verdict |
| [docs/infrastructure.md](docs/infrastructure.md) | Where things ran, incidents and fixes |
| [docs/reproduce.md](docs/reproduce.md) | How to regenerate the result summaries, and what that covers |
| [docs/repository.md](docs/repository.md) | Repository layout, what moved, history notes |
| [docs/research/](docs/research/) | Literature reviews that shaped the plan |

## Repository layout

| Path | What it holds |
|---|---|
| [`analysis/`](analysis/) | Scripts that compute the result summaries from `results/` |
| [`train/`](train/) | Training code: SFT, GRPO, prompt/action format |
| [`data/`](data/) | Dataset builders and fixed split files |
| [`eval/`](eval/) | Benchmark harnesses: AndroidControl, AndroidWorld, MobileWorld, general knowledge |
| [`scripts/`](scripts/) | Run orchestration, by purpose (AndroidWorld, MobileWorld, training, speed, publishing) |
| [`results/`](results/) | Raw results (episode files, predictions) and the summaries computed from them |
| [`logs/`](logs/) | Run logs kept as evidence (model servers, emulators, runs, Codex sessions) |
| [`docs/`](docs/) | Documentation |

## Rules this project kept

- **No AndroidWorld data in training:** no AndroidWorld tasks, variants, trajectories or checkers in any training set.
- **Matched primary comparison:** v4 and GUI-Owl get one screenshot, the same tasks and step budget, 4-bit weights
  and the installed-app list. Image size and prompts differ ([details](docs/evaluation.md#fairness-at-a-glance)).
  MAI-UI runs at 8-bit; v1 gets no app list.
- **Sealed held-out seeds:** results of seeds 7/1234/2026 were not read until every model had finished that seed.
- **Every deviation is dated** in [docs/PREREG_v4.md](docs/PREREG_v4.md), with what had and had not been seen at the time.
- **Exceptions count as failures**, unlike AndroidWorld's default.
