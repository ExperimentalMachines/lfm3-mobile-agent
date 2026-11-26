---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: LiquidAI/LFM3-VL-2B
pipeline_tag: image-text-to-text
library_name: transformers
language:
- en
tags:
- android
- gui-agent
- mobile-agent
- screenshot
- lora
---
# LFM3-VL-2B-MobileAgent-Dev-WaitRelabel

- **Name:** `LFM3-VL-2B-MobileAgent-Dev-WaitRelabel` (formerly `LFM3-VL-2B-MobileAgent-v4.1`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Development model**: kept so results can be reproduced, **not recommended**. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead
- **Initialised from:** the base model
- **Recipe builds on:** [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent)
- **What was added:** copied `wait` intents relabelled + recovery-history augmentation

A 2B screenshot-only Android agent: [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) fine-tuned to operate
a phone from one screenshot per step. A follow-up to Main aimed at Main's main failure: getting stuck in `wait` loops.

| | |
|---|---|
| Base | LiquidAI/LFM3-VL-2B @ `23387be` |
| Method | LoRA SFT (rank 64, alpha 128) on the language model, vision tower frozen; merged into the weights (adapter in `lora_adapter/`) |
| Training | 1,250 steps × 32 rows (0.43 epoch of 92,229 rows), lr 2e-4, one A100 — the same recipe, rows and row order as Main |
| Data | AndroidControl, GUI-Odyssey, AMEX, ScreenQA (Main's data with the text edits below) |
| Phone format | 4-bit GGUF: [LFM3-VL-2B-MobileAgent-Dev-WaitRelabel-GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-WaitRelabel-GGUF) |
| Status | Experimental; superseded by OwnHistory (12/116 vs Main's 18 on AndroidWorld seed 30) |

## What changed from Main (training text only)

| Edit | Rows | Why |
|---|---|---|
| `wait` relabel | 4,104 targets, 13,145 history lines | 94% of AndroidControl's `wait` rows repeat the previous step's intent ("Click on the search button" → `wait`), so Main learned "copy my last intent, then wait". Their intent is now "Wait for the screen to finish loading." |
| Recovery history | 5,244 rows | One extra history step (the last step repeated, or a wait); the human's next action stays the target |

## Input and output

| Part | Format |
|---|---|
| Image | One screenshot per step, resized to at most 880 × 880 px of area (about 720 image tokens) |
| User text | `Goal: …` / `Installed apps: …` / `Previous steps:` (last 8 steps as `n. <intent> -> <action JSON>`, or `None`) / `What is the next action?` |
| Output | `<think>short intent</think>` followed by one compact JSON action; coordinates are integers on a 0–1000 grid |
| Decoding | Thinking on, temperature 0 |

<details><summary>System prompt</summary>

```
You are a phone-use agent operating an Android phone to complete the user's goal.
Each turn you see the goal, the installed apps, your previous steps, and the current screenshot. Reply with ONE next action as JSON.
Coordinates are integers normalized to 0-1000 (x from left, y from top) of the screenshot.
Actions:
{"action_type":"click","point_2d":[x,y]}
{"action_type":"long_press","point_2d":[x,y]}
{"action_type":"input_text","text":"..."}  (types into the focused field)
{"action_type":"scroll","direction":"up|down|left|right"}  (down = reveal content below)
{"action_type":"open_app","app_name":"..."}  (app_name must be one of the installed apps)
{"action_type":"navigate_back"}
{"action_type":"navigate_home"}
{"action_type":"keyboard_enter"}
{"action_type":"wait"}
{"action_type":"answer","text":"..."}  (if the goal asks a question: the final reply, as short as possible and in the requested format; ends the task)
{"action_type":"status","goal_status":"complete|infeasible"}  (finish a goal that asks for no information; never use it instead of answering a question)
```
</details>

## Evaluation

Post-hoc follow-up (designed after reading Main's MobileWorld results). One run each, temperature 0, 4-bit GGUF;
exceptions count as failures.

| Benchmark | WaitRelabel | Main | Paired |
|---|---|---|---|
| AndroidWorld, seed 30 (116 tasks, development) | 12 (14 with loop guards) | 18 | +2 / −8 |
| AndroidControl test, high- / low-level step accuracy | 0.732 / 0.895 | 0.728 / 0.908 | — |
| MMStar / MMLU (general knowledge) | 55.6% / 51.1% | 52.9% / 50.4% | — |

- **Worse than Main online.** It was not selected for MobileWorld; its successor
  [OwnHistory](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory) (WaitRelabel + training on its own outputs)
  returned to 18/116 and scored 8/105 on MobileWorld (Main: 6/105).

## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step, no memory beyond the 8-step text history.
- Trained only on recorded demonstrations; it has never interacted with a live phone during training.

## Project

Code, data builders, benchmark harnesses and every result with its source: [experimentalmachines/lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent) (see [models](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/models.md) and [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md)).

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
