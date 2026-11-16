---
pretty_name: OpenMobile-Data-v2
language:
- en
- zh
task_categories:
- image-text-to-text
tags:
- mobile
- gui-agent
- multimodal
- emulator
- simulator
size_categories:
- 100K<n<1M
configs:
- config_name: sft
  data_files:
  - split: train
    path:
    - emulator/train.json
    - simulator/gui-only/train.json
    - simulator/hybrid/train.json
- config_name: rl
  data_files:
  - split: train
    path: RL/task.jsonl
---

## Paper

This dataset is introduced in our paper:

[OpenMobile-2: Building Versatile Mobile Agents with Scalable Environments and App-Native Tools](https://huggingface.co/papers/2610.14157)

# OpenMobile-Data-v2

Two parts. SFT is one decision step per example: the model reads the remaining screenshots and the conversation history, then writes a `Thought:` followed by one tool call. Coordinates belong in the tool arguments. The screen space in the prompt is **999×999**. RL is one task per line, with the instruction, the initial state, and the check for success.

SFT has **11,643** trajectories and **118,582** steps, about **59.2 GB**. Trajectory folders contain only `screenshot_step{K}.png`. RL has **2,475** tasks in one JSONL file.

## Splits

| Split | File | Trajectories | Steps | Tools |
| --- | --- | ---: | ---: | --- |
| Emulator | `emulator/train.json` | 7,725 | 83,631 | `mobile_use` only. 3,202 cross-app, 4,523 single-app |
| Simulator, GUI-only | `simulator/gui-only/train.json` | 2,144 | 22,857 | `mobile_use` only |
| Simulator, hybrid | `simulator/hybrid/train.json` | 1,774 | 12,094 | `mobile_use`, plus extra app tools listed in the current tool message |

`dataset_info.json` registers these files as `emulator_qwen35_last3_noloop_notitle_nocoord_think_thought`, `mobilegym_qwen35_last3_noloop_notitle_nocoord_think_thought`, and `gui_mcp_qwen35_last3_noloop_notitle_nocoord_think_thought`.

## Record format

Each `train.json` is a list of objects with `id`, `messages`, and `images`.

- `images` holds at most the last three screenshots, oldest first. Paths are relative to that JSON file.
- Earlier screenshots are replaced in the text by `This screenshot has been collapsed.` The remaining `<image>` placeholders line up with `images`.
- History `assistant` turns are marked `"loss": false`. Supervise the last `assistant` turn.
- Hybrid `tool` messages may include a foreground-app tool catalog. Those tools are valid only while that app stays in front.

## RL tasks

`RL/tasks.jsonl` is one JSON object per line. Each line has `task`, `init`, and `verify` together.

- `task.instruction` is the user goal. `task.apps` lists the apps involved.
- `init` is the starting state, including `assertion_initials`.
- `verify` is the success check: `assertions` and optional `extra_checks`.

## Use with ms-swift

Download the full repository so the screenshot paths resolve. The dataset viewer table stores those paths as strings and does not replace this download.

```bash
hf download OpenMobile-2/OpenMobile-Data-v2 --repo-type dataset --local-dir OpenMobile-Data-v2

swift sft \
  --custom_dataset_info OpenMobile-Data-v2/dataset_info.json \
  --dataset emulator_qwen35_last3_noloop_notitle_nocoord_think_thought \
            mobilegym_qwen35_last3_noloop_notitle_nocoord_think_thought \
            gui_mcp_qwen35_last3_noloop_notitle_nocoord_think_thought
```

Adjust `model`, batch size, and output paths for your local [ms-swift](https://github.com/modelscope/ms-swift) setup and hardware.
