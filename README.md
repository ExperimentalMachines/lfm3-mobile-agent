# LFM3 Mobile Agent

A small Android agent that works from screenshots alone: LiquidAI **LFM3-VL-2B**, fine-tuned to operate a phone from
one screenshot per step, small enough to run on the phone (4-bit GGUF, llama.cpp). It is compared fairly with
**GUI-Owl-1.5-2B** and **MAI-UI-2B**.

This repository is the whole project: training code, dataset builders, benchmark harnesses, every result with its raw
files, and the preregistered rules each decision followed.

| | |
|---|---|
| **Main model** | **v4**: [weights](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4), [phone GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4-GGUF) (1.30 GB with its image projector). The version tested on the sealed held-out benchmark |
| **Newest model** | **v4.6-E**: [weights](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.6-E), [phone GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.6-E-GGUF). Barely waits and is sharper offline, but repeats taps more. Held-out AndroidWorld: 52 / 348 vs v4's 54 (not worse, not better), with more false "done" calls (75 vs 71), so it did not replace v4 |
| **Now** | E on MobileWorld ([rule](docs/PREREG_v46.md)); round 11, E trained further on multi-part tasks it should finish, training on an L4 ([plan](docs/PREREG_v49.md)) |
| Everything published | [LFM3 Mobile Agent collection](https://huggingface.co/collections/experimentalmachines/lfm3-mobile-agent-6b03a79f8e23b8dde16e8326): every model, GGUF and training dataset, public |
| License | Code: Apache-2.0. Models and data: their sources' licenses ([below](#license)) |

---

## Use the model

```bash
# llama.cpp (https://github.com/ggml-org/llama.cpp); the same flags as in our evaluations
hf download experimentalmachines/LFM3-VL-2B-MobileAgent-v4-GGUF --local-dir lfm3-mobile-agent-v4
llama-server -m lfm3-mobile-agent-v4/LFM3-VL-2B-MobileAgent-v4-Q4_K_M.gguf \
  --mmproj lfm3-mobile-agent-v4/mmproj-LFM3-VL-2B-Q8_0.gguf \
  -c 8192 --image-max-tokens 1024 --reasoning-format deepseek
```

| Piece | Where |
|---|---|
| Prompt and action format | [`train/agent_format.py`](train/agent_format.py) (`build_messages(..., prompt_version="v4", apps=[...])`, `parse_action`); also on the [model card](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4) |
| Agent loop on an emulator or phone (AndroidWorld) | [`eval/androidworld/lfm_agent.py`](eval/androidworld/lfm_agent.py), run by [`eval/androidworld/run_aw.py`](eval/androidworld/run_aw.py) |
| Agent for MobileWorld | [`eval/mobileworld/lfm3_mw_agent.py`](eval/mobileworld/lfm3_mw_agent.py) |
| On the phone's GPU (LiteRT-LM) | [`LFM3-VL-2B-MobileAgent-v4-LiteRT`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4-LiteRT) (one int8 file, about 3.5 s per model call on a Snapdragon reference phone) and the Android app [ExperimentalMachines/mobile-agent](https://github.com/ExperimentalMachines/mobile-agent) |
| Newer model (v4.6-E) | Same command with the [v4.6-E GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.6-E-GGUF); it expects a 24-step history with "[no visible change]" notes (see its card) |
| Limits | Research model: do not let it act unattended on a phone with real accounts, messages or payments |

---

## Results at a glance

### Main result: AndroidWorld, held-out (preregistered)

116 tasks × 3 sealed seeds; every model gets one screenshot per step, 4-bit weights, the same tasks and step budget.

| Model | Successes / 348 | |
|---|---|---|
| **LFM3-VL-2B v4 (ours)** | **54 (15.5%)** | |
| GUI-Owl-1.5-2B | 47 (13.5%) | v4 − GUI-Owl = +2.0 points, 95% CI [−4.5, +8.6]: **non-inferior** (not worse by more than the preregistered 6.9-point margin), not shown better |
| LFM3-VL-2B v1 (our first model) | 32 (9.2%) | v4 − v1 = +6.3 points, CI [+1.1, +11.5]: better |
| LFM3-VL-2B v4.6-E (newest; run later, post-hoc) | 52 (14.9%) | E − v4 = −0.6 points, CI [−5.4, +4.2]: not worse, but 75 false "done" calls vs v4's 71, so v4 stays ([rule](docs/PREREG_v46.md)) |

- **The non-inferiority verdict is fragile.** It relies on the preregistered re-run of episodes whose emulator crashed before
  step 1 (113 of v4's seed-1234 episodes, after one emulator hung overnight). On the 78 templates whose goal text changes with the seed,
  v4 and GUI-Owl are level (32 vs 33).
- An independent audit judged the result **valid with caveats** ([audits](docs/audits.md)).

### Other benchmarks

| Benchmark | v4 | GUI-Owl-1.5-2B | MAI-UI-2B |
|---|---|---|---|
| MobileWorld, 105 tasks (one run each) | 6 | **22** | 11 |
| Speed, Apple M5, median s/step | **2.96** | 7.00 | 9.35 (8-bit) |
| Speed, phone CPU (Snapdragon 8 Elite Extreme Gen 6), s/step as evaluated | **~39** | ~1,100 | ~1,063 (8-bit) |

- **On MobileWorld v4 is clearly behind** GUI-Owl (−15 points, p < 0.001).
- **v4 is the fastest by far.** It sends fewer prompt tokens per step (a smaller image): about a third as many on CPU
  and phone, about 60% on the M5. The tests compare whole pipelines and do not isolate the cause.

Every number, caveat and source file: **[docs/results.md](docs/results.md)**.

---

## Since v4: development rounds

Each round fixed its rules in advance: a dated plan, an offline gate, then (only on a pass) one run on AndroidWorld's
development seed 30. One seed-30 pass cannot detect differences smaller than about 9 tasks. **No version has beaten
v4 by that margin, so v4 remains the main model.**

| Date | Round | Version | What it tried | Seed 30 / 116 | False "done" | Outcome |
|---|---|---|---|---|---|---|
| 11-19 | — | **v4** | Reference | 18 | 25 | Main model |
| 11-21 | — | v4.1 | Fix copied `wait` labels; recovery histories | 12 | — | Worse |
| 11-22 | — | v4.2 | + its own replayed histories (offline DAgger) | 18 | 25 | Loops halved on MobileWorld (8 / 105) |
| 11-22 | 5 | v4.3-dpo, -dpo2, -sft | Penalise its own mistakes (DPO); or train longer | —, 21, 24 | —, 28, 37 | Failed (noise, or more false "done") |
| 11-23 | 6 | v4.4-A, B, C | Long, self-correcting trajectories (MemGUI) | — | — | Failed offline gate |
| 11-24 | 7 | v4.5-D | All the data once, 24-step memory | 21* | 27 | Failed offline gate (stops too early) |
| 11-25 | 8 | **v4.6-E** | Teach it to judge "done" from the screen, not its history | 19* | 24 | Failed offline gate narrowly; waits 29% → 3.5% of steps. Held-out: 52 / 348 (v4 54), not promoted |
| 11-25 | 9 | (v4.7 data) | Remove useless waits | — | — | Not trained: E already met the wait bars set for it |
| 11-25 | 10 | E-DPO | Penalise E's premature stops and reward its missed stops, on judge-checked examples | — | — | Failed offline gate (unchanged from E) |
| 11-25 | 11 | E-T | E + 747 checked "multi-part task finished" examples | training | | |

\* Exploratory run by the owner's decision after a failed offline gate.

**What the rounds taught us**

- **Stopping is the main weakness.** Every version tested ends 22–37 of 116 episodes with a false "done". About half of
  E's are multi-part tasks stopped part-way.
- **Offline gains do not transfer reliably.** D and E beat v4 clearly offline (AndroidControl 0.727 → 0.75–0.76; long
  tasks 0.37 → 0.46–0.47), yet succeed at about as many AndroidWorld tasks.
- **Waits were fixable with data:** E spends 3.5% of its steps waiting (v4: 29%). Repeated taps rose, though
  (runs of the same tap: v4 6, E 23).
- **Human "done" labels are noisy.** 16–25% of GUI-Odyssey's recorded final steps looked not done in the first
  reviews, and about half under the owner's strict definition of done. Round 10 calibrated a judge to that definition
  (the by-eye labels it was checked against were made by the coding assistant, itself a Claude model).
- **Penalising own mistakes did not help** at our scale (rounds 5 and 10).

Every round in detail: **[docs/rounds.md](docs/rounds.md)**.

---

## Documentation

| Read | For |
|---|---|
| **[Results](docs/results.md)** | The main study: AndroidWorld held-out, MobileWorld, speed, offline scores, with every caveat and source |
| **[Development rounds](docs/rounds.md)** | Every round since v4: idea, gate, result, decision, lessons |
| **[Models](docs/models.md)** | Versions, training recipe, training runs, what is published where |
| [Datasets](docs/datasets.md) | Training data per version, splits, the contamination rule |
| [Evaluation](docs/evaluation.md) | How each benchmark was run and kept fair |
| [Reproduce](docs/reproduce.md) | Regenerate the result summaries; re-run the experiments |
| **Records** | |
| [Preregistrations](docs/PREREG_v4.md) | The rules each round fixed in advance, with dated logs: [v4](docs/PREREG_v4.md) · [v4.1–v4.3](docs/PREREG_v41.md) · [v4.4](docs/PREREG_v44.md) · [v4.5](docs/PREREG_v45.md) · [v4.6](docs/PREREG_v46.md) · [v4.7](docs/PREREG_v47.md) · [v4.8](docs/PREREG_v48.md) · [v4.9](docs/PREREG_v49.md) |
| [Audits](docs/audits.md) | Independent reviews and their verdicts |
| [Infrastructure](docs/infrastructure.md) | Where things ran, costs, incidents |
| [Repository notes](docs/repository.md) | Layout details, tags, secrets policy, history rewrites |
| [Research](docs/research/) | Literature reviews that shaped the plan |

---

## Repository layout

| Path | What it holds |
|---|---|
| [`train/`](train/) | Training code: SFT, DPO, GRPO, prompt and action format |
| [`data/`](data/) | Dataset builders and fixed split files |
| [`eval/`](eval/) | Benchmark harnesses: AndroidControl, AndroidWorld, MobileWorld, general knowledge |
| [`analysis/`](analysis/) | Scripts that compute the result summaries from `results/` |
| [`scripts/`](scripts/) | Run orchestration by purpose: training, AndroidWorld, MobileWorld, speed, publishing |
| [`results/`](results/) | Raw results (episodes, predictions) and the summaries computed from them |
| [`logs/`](logs/) | Run logs kept as evidence |
| [`docs/`](docs/) | Documentation |

---

## Rules this project kept

- **No benchmark data in training:** nothing from AndroidWorld, MobileWorld or AndroidLab (their tasks, trajectories,
  checkers or benchmark-specific apps) in any training set.
- **Matched comparison:** v4 and GUI-Owl get one screenshot, the same tasks and step budget, 4-bit weights and the
  installed-app list. Image size and prompts differ ([details](docs/evaluation.md#fairness-at-a-glance)).
- **Sealed held-out seeds:** results of seeds 7 / 1234 / 2026 were not read until every model had finished that seed.
- **Rules before results:** every round's plan and gate were committed before training; deviations are dated.
- **Exceptions count as failures**, unlike AndroidWorld's default.

---

## License

| Part | License |
|---|---|
| Code and documentation | Apache-2.0 ([LICENSE](LICENSE)) |
| LFM3-VL-2B and LFM2.5-VL-450M fine-tunes | LFM Open License v1.0, inherited from the LiquidAI base models |
| Qwen3.5 fine-tunes | Apache-2.0, inherited from the Qwen base models |
| Training datasets | Per source: AndroidControl Apache-2.0; GUI-Odyssey, AMEX, ScreenQA CC BY 4.0; MemGUI-3K Apache-2.0 (see each dataset card) |
| Third-party code | `eval/androidworld/maiui_ref/` (MAI-UI reference agent) and `eval/androidworld/*.patch` (AndroidWorld, android_env): Apache-2.0, as their sources |
