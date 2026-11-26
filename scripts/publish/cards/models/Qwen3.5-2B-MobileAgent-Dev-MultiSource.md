---
license: apache-2.0
base_model: Qwen/Qwen3.5-2B
pipeline_tag: image-text-to-text
library_name: transformers
language:
- en
datasets:
- experimentalmachines/MobileAgent-SFT-MultiSource
tags:
- android
- gui-agent
- mobile-agent
- screenshot
- lora
---

# Qwen3.5-2B-MobileAgent-Dev-MultiSource

- **Name:** `Qwen3.5-2B-MobileAgent-Dev-MultiSource` (formerly `Qwen3.5-2B-MobileAgent-v2`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Development model**: kept so results can be reproduced, **not recommended**. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead
- **Initialised from:** the base model
- **What was added:** + GUI-Odyssey, AMEX, ScreenQA

[Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) fine-tuned with the recipe and data of LFM3-VL-2B-MobileAgent-Dev-MultiSource. Trained on the same data as LFM3-VL-2B AndroidControlOnly to compare base models; not part of the main line. The project's main model is [LFM3-VL-2B-MobileAgent](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent).

| | |
|---|---|
| Base | Qwen/Qwen3.5-2B |
| Method | LoRA SFT (rank 64, alpha 128) on the language model, vision tower frozen; merged into the weights (adapter in `lora_adapter/`) |
| Training | 1,250 steps × 32 rows, lr 2e-4 |
| Data | [MobileAgent-SFT-MultiSource](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-MultiSource) @ `42f7f763` (AndroidControl, GUI-Odyssey, AMEX, ScreenQA; 78,982 rows) |
| Phone format | 4-bit GGUF: [Qwen3.5-2B-MobileAgent-Dev-MultiSource-GGUF](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-Dev-MultiSource-GGUF) |
| Status | Comparison model; offline only |

## Evaluation (offline only; not run on AndroidWorld)

| Benchmark | Qwen3.5-2B MultiSource | LFM3-VL-2B MultiSource |
|---|---|---|
| AndroidControl test, high- / low-level step accuracy | 0.739 / 0.907 | 0.716 / 0.893 |
| Terminal `complete` accuracy | 0.750 | 0.732 |
| Dev splits: GUI-Odyssey / AMEX / ScreenQA answers | 0.724 / 0.739 / 0.756 | 0.644 / 0.735 / 0.764 |
| MMStar / MMLU | 54.0% / 56.0% | 54.6% / 50.9% |

- The MultiSource data mix later turned out to break the agent loop (LFM3 MultiSource: 3/116 on AndroidWorld), so this model was not
  run on AndroidWorld.

## Input and output

| Part | Format |
|---|---|
| Image | One screenshot per step, resized to at most 880 × 880 px of area (about 720 image tokens) |
| User text | `Goal: …` / `Previous steps:` (last 8 steps as `n. <intent> -> <action JSON>`, or `None`) / `What is the next action?` |
| Output | `<think>short intent</think>` followed by one compact JSON action; coordinates are integers on a 0–1000 grid |
| Decoding | Thinking on, temperature 0 |

<details><summary>System prompt (the earlier Dev models (AndroidControlOnly, MultiSource, FilledIntents) format)</summary>

```
You are a phone-use agent operating an Android phone to complete the user's goal.
Each turn you see the goal, your previous steps, and the current screenshot. Reply with ONE next action as JSON.
Coordinates are integers normalized to 0-1000 (x from left, y from top) of the screenshot.
Actions:
{"action_type":"click","point_2d":[x,y]}
{"action_type":"long_press","point_2d":[x,y]}
{"action_type":"input_text","text":"..."}  (types into the focused field)
{"action_type":"scroll","direction":"up|down|left|right"}  (down = reveal content below)
{"action_type":"open_app","app_name":"..."}
{"action_type":"navigate_back"}
{"action_type":"navigate_home"}
{"action_type":"keyboard_enter"}
{"action_type":"wait"}
{"action_type":"answer","text":"..."}  (reply to a question about the screen)
{"action_type":"status","goal_status":"complete|infeasible"}  (finish the task)
```
</details>

## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step, no memory beyond the 8-step text history.
- Trained only on recorded demonstrations; it has never interacted with a live phone during training.

## Project

Code, data builders, benchmark harnesses and every result with its source: [experimentalmachines/lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent) (see [models](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/models.md) and [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md)).

## License

Apache-2.0, inherited from [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) ([LICENSE](LICENSE)).
