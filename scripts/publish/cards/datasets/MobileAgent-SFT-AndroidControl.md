---
license: apache-2.0
pretty_name: MobileAgent-SFT-AndroidControl
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
    path: data/train/*.parquet
  - split: validation
    path: data/val/*.parquet
  - split: test
    path: data/test/*.parquet
---

# MobileAgent-SFT-AndroidControl

- **Name:** `MobileAgent-SFT-AndroidControl` (formerly `MobileAgent-SFT-v1`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Trains:** [`LFM3-VL-2B-MobileAgent-Dev-AndroidControlOnly`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-AndroidControlOnly), [`Qwen3.5-2B-MobileAgent-Dev-AndroidControlOnly`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-Dev-AndroidControlOnly)

Training data of [LFM3-VL-2B-MobileAgent-Dev-AndroidControlOnly](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-AndroidControlOnly) and the comparison fine-tunes
([Qwen3.5-2B AndroidControlOnly](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-Dev-AndroidControlOnly), [Qwen3.5-0.8B AndroidControlOnly](https://huggingface.co/experimentalmachines/Qwen3.5-0.8B-MobileAgent-Dev-AndroidControlOnly),
[LFM2.5-VL-450M AndroidControlOnly](https://huggingface.co/experimentalmachines/LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly)). The project's AndroidControl evaluations read its `test` split.

| | |
|---|---|
| Source | AndroidControl (Google Research), re-split with the official `splits.json` (a common Hub mirror's random split leaks 1,238 test episodes) |
| Train | 99,216 rows: high-level steps + ~15% low-level copies + one synthetic `status: complete` step on each episode's final screen |
| Validation / test | Official validation and test episodes (test: high- and low-level rows, used for the offline AndroidControl numbers) |
| Built by | [`data/sft_androidcontrol.py`](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/data/sft_androidcontrol.py); statistics per build machine in `stats/` |
| License | Apache-2.0, as AndroidControl |

Each row is one step: `images` (the screenshot), `messages` (system prompt, user text with goal and 8-step history, target reply `<think>intent</think>{action JSON}`), plus the ground-truth action and provenance fields.

No AndroidWorld tasks, variants, trajectories or checkers; training episodes that name any of the 14 AndroidWorld-specific apps are dropped (a heuristic filter, see the project's [datasets notes](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/datasets.md)).
