---
license: other
license_name: mixed-apache-2.0-cc-by-4.0
license_link: LICENSE.md
pretty_name: MobileAgent-SFT-v4
task_categories:
- image-text-to-text
language:
- en
tags:
- android
- gui-agent
- mobile-agent
- screenshot
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*.parquet
  - split: dev_odyssey
    path: data/dev_odyssey-*.parquet
  - split: dev_amex
    path: data/dev_amex-*.parquet
  - split: dev_screenqa
    path: data/dev_screenqa-*.parquet
  - split: dev_answer
    path: data/dev_answer-*.parquet
  - split: dev_complete
    path: data/dev_complete-*.parquet
---

# MobileAgent-SFT-v4

Training data of [LFM3-VL-2B-MobileAgent-v4](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4); v4.1 and v4.2 rebuild their data from it deterministically (code in the project repo).

v3 rewritten to the v4 prompt (answer-vs-complete rules + installed-app list) + 2,386 navigate-then-answer copies of AndroidControl train episodes (11,156 rows; question and answer by Qwen3-VL-8B-Instruct from the final screen, confirmed by a second call and a strict typed check) + 1,233 shortened ScreenQA answers: 92,229 train rows. `dev_answer` / `dev_complete`: 136 held-out, screen-disjoint episodes (question / original action version) used by v4's gate.

| | |
|---|---|
| Built by | [`data/v4_build_parquet.py`](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/data/v4_build_parquet.py) |
| Revision used for training | `3375539` (pin it: later commits only changed this card) |

Each row is one step: `images` (the screenshot), `messages` (system prompt, user text with goal and 8-step history, target reply `<think>intent</think>{action JSON}`), plus the ground-truth action and provenance fields.

## Sources and licenses

| Source | License | Use here |
|---|---|---|
| [AndroidControl](https://github.com/google-research/google-research/tree/master/android_control) (Google Research) | Apache-2.0 | Official train / validation / test episodes |
| [GUI-Odyssey](https://huggingface.co/datasets/OpenGVLab/GUI-Odyssey) | CC BY 4.0 | v2+ |
| [AMEX](https://huggingface.co/datasets/Yuxiang007/AMEX) | CC BY 4.0 | v2+ |
| [ScreenQA](https://github.com/google-research-datasets/screen_qa) | CC BY 4.0 | v2+: question-answer rows |
| Text written by [Qwen/Qwen3-VL-8B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) | Apache-2.0 (model) | v3 intents, v4 questions and answers |

No AndroidWorld tasks, variants, trajectories or checkers; training episodes that name any of the 14 AndroidWorld-specific apps are dropped (a heuristic filter, see the project's [datasets notes](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/datasets.md)).
