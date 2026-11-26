---
license: other
license_name: mixed-apache-2.0-cc-by-4.0
license_link: LICENSE.md
pretty_name: MobileAgent-SFT-MultiSource
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
    path: data/train-*
  - split: dev_odyssey
    path: data/dev_odyssey-*
  - split: dev_amex
    path: data/dev_amex-*
  - split: dev_screenqa
    path: data/dev_screenqa-*
dataset_info:
  features:
  - name: images
    list: image
  - name: messages
    list:
    - name: role
      dtype: string
    - name: content
      dtype: string
    - name: reasoning_content
      dtype: string
  - name: source
    dtype: string
  - name: split
    dtype: string
  - name: episode_id
    dtype: string
  - name: step_idx
    dtype: int32
  - name: gt_action
    dtype: string
  - name: is_terminal
    dtype: bool
  - name: orig_w
    dtype: int32
  - name: orig_h
    dtype: int32
  - name: img_sha
    dtype: string
  splits:
  - name: train
    num_bytes: 7650322238
    num_examples: 78982
  - name: dev_odyssey
    num_bytes: 103966755
    num_examples: 1000
  - name: dev_amex
    num_bytes: 49948861
    num_examples: 468
  - name: dev_screenqa
    num_bytes: 47725361
    num_examples: 500
  download_size: 7746047195
  dataset_size: 7851963215
---

# MobileAgent-SFT-MultiSource

- **Name:** `MobileAgent-SFT-MultiSource` (formerly `MobileAgent-SFT-v2`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Trains:** [`LFM3-VL-2B-MobileAgent-Dev-MultiSource`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MultiSource), [`Qwen3.5-2B-MobileAgent-Dev-MultiSource`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-Dev-MultiSource)

Training data of [LFM3-VL-2B-MobileAgent-Dev-MultiSource](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MultiSource) and [Qwen3.5-2B-MobileAgent-Dev-MultiSource](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-Dev-MultiSource).

AndroidControl 55,936 rows (incl. 5,998 terminal) · GUI-Odyssey 9,979 · AMEX 7,072 · ScreenQA 5,995 (78,982 train rows) + screen-disjoint dev splits for GUI-Odyssey, AMEX and ScreenQA. **Superseded:** 8,739 rows have a blank intent, which broke the agent loop (FilledIntents fixes them).

| | |
|---|---|
| Built by | [`data/sft_multisource.py`](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/data/sft_multisource.py) |
| Revision used for training | `42f7f763` (pin it: later commits only changed this card) |

Each row is one step: `images` (the screenshot), `messages` (system prompt, user text with goal and 8-step history, target reply `<think>intent</think>{action JSON}`), plus the ground-truth action and provenance fields.

## Sources and licenses

| Source | License | Use here |
|---|---|---|
| [AndroidControl](https://github.com/google-research/google-research/tree/master/android_control) (Google Research) | Apache-2.0 | Official train / validation / test episodes |
| [GUI-Odyssey](https://huggingface.co/datasets/OpenGVLab/GUI-Odyssey) | CC BY 4.0 | MultiSource+ |
| [AMEX](https://huggingface.co/datasets/Yuxiang007/AMEX) | CC BY 4.0 | MultiSource+ |
| [ScreenQA](https://github.com/google-research-datasets/screen_qa) | CC BY 4.0 | MultiSource+: question-answer rows |
| Text written by [Qwen/Qwen3-VL-8B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) | Apache-2.0 (model) | FilledIntents intents, Main questions and answers |

No AndroidWorld tasks, variants, trajectories or checkers; training episodes that name any of the 14 AndroidWorld-specific apps are dropped (a heuristic filter, see the project's [datasets notes](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/datasets.md)).
