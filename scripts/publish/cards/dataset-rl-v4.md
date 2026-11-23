---
license: other
license_name: mixed-apache-2.0-cc-by-4.0
license_link: LICENSE.md
pretty_name: MobileAgent-RL-v4
task_categories:
- image-text-to-text
language:
- en
tags:
- android
- gui-agent
- mobile-agent
- screenshot
dataset_info:
  features:
  - name: image
    dtype: image
  - name: prompt
    list:
    - name: role
      dtype: string
    - name: content
      dtype: string
  - name: gt_action
    dtype: string
  - name: kind
    dtype: string
  - name: episode_id
    dtype: string
  splits:
  - name: train
    num_bytes: 205845529
    num_examples: 2000
  download_size: 202604003
  dataset_size: 205845529
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
---

# MobileAgent-RL-v4

Training data of [LFM3-VL-2B-MobileAgent-v4-RL](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4-RL).

2,000 single-step states from v4's training data for GRPO on static screenshots: 700 answer, 500 complete, 300 other actions, 500 clicks. Columns: `image`, `prompt` (chat messages), `gt_action`, `kind`, `episode_id`.

| | |
|---|---|
| Built by | [`data/v4_rl_pool.py`](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/data/v4_rl_pool.py) |
| Revision used for training | `9ba36d90` (pin it: later commits only changed this card) |


## Sources and licenses

| Source | License | Use here |
|---|---|---|
| [AndroidControl](https://github.com/google-research/google-research/tree/master/android_control) (Google Research) | Apache-2.0 | Official train / validation / test episodes |
| [GUI-Odyssey](https://huggingface.co/datasets/OpenGVLab/GUI-Odyssey) | CC BY 4.0 | v2+ |
| [AMEX](https://huggingface.co/datasets/Yuxiang007/AMEX) | CC BY 4.0 | v2+ |
| [ScreenQA](https://github.com/google-research-datasets/screen_qa) | CC BY 4.0 | v2+: question-answer rows |
| Text written by [Qwen/Qwen3-VL-8B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) | Apache-2.0 (model) | v3 intents, v4 questions and answers |

No AndroidWorld tasks, variants, trajectories or checkers; training episodes that name any of the 14 AndroidWorld-specific apps are dropped (a heuristic filter, see the project's [datasets notes](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/datasets.md)).
