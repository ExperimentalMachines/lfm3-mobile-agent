---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: LiquidAI/LFM3-VL-2B
pipeline_tag: image-text-to-text
library_name: transformers
language:
- en
datasets:
- experimentalmachines/MobileAgent-SFT-FilledIntents
tags:
- android
- gui-agent
- mobile-agent
- screenshot
- lora
---

# LFM3-VL-2B-MobileAgent-Dev-FilledIntents

- **Name:** `LFM3-VL-2B-MobileAgent-Dev-FilledIntents` (formerly `LFM3-VL-2B-MobileAgent-v3`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Development checkpoint**: kept so results can be reproduced, **not recommended**. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead
- **Initialised from:** the base model
- **Recipe builds on:** [`LFM3-VL-2B-MobileAgent-Dev-MultiSource`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MultiSource)
- **What was added:** the blank intents filled (templates + a teacher model)

MultiSource's mix with every blank intent filled, to test whether blank intents caused MultiSource's collapse.

| | |
|---|---|
| Base | LiquidAI/LFM3-VL-2B |
| Method | LoRA SFT (rank 64, alpha 128) on the language model, vision tower frozen; merged into the weights (adapter in `lora_adapter/`) |
| Training | 1,250 steps × 32 rows, lr 2e-4 (Modal H100) |
| Data | [MobileAgent-SFT-FilledIntents](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-FilledIntents) @ `565ba76c`: MultiSource with 6,106 intents written by Qwen3-VL-8B-Instruct, 2,603 from action templates, 30 rows dropped (78,952 rows) |
| Phone format | 4-bit GGUF: [LFM3-VL-2B-MobileAgent-Dev-FilledIntents-GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-FilledIntents-GGUF) |
| Status | **Superseded** by Main, whose data is built on FilledIntents' |

## Evaluation

| Benchmark | FilledIntents | MultiSource | AndroidControlOnly |
|---|---|---|---|
| AndroidWorld seed 30 (116 tasks, development) | 13 | 3 | 15 |
| AndroidControl test, high- / low-level step accuracy | 0.723 / 0.902 | 0.716 / 0.893 | 0.715 / 0.948 |
| Terminal `complete` accuracy | 0.725 | 0.732 | 0.792 |
| Dev splits: GUI-Odyssey / AMEX / ScreenQA answers | 0.662 / 0.741 / 0.724 | 0.644 / 0.735 / 0.764 | 0.269 / 0.306 / 0.000 |
| MMStar / MMLU | 55.3% / 50.0% | 54.6% / 50.9% | 57.1% / 49.5% |

- **Recovered from MultiSource** (FilledIntents-only 10 tasks, MultiSource-only 0, p = 0.002) but not above AndroidControlOnly (p = 0.75).
- Still never emits `answer` in AndroidWorld, although ScreenQA is in its data. Main fixed this with
  navigate-then-answer episodes and answer rules in the prompt.

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

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
