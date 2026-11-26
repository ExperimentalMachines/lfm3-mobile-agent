---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory
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
# LFM3-VL-2B-MobileAgent-Dev-ContinuedSFT

- **Name:** `LFM3-VL-2B-MobileAgent-Dev-ContinuedSFT` (formerly `LFM3-VL-2B-MobileAgent-v4.3-sft`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Development model**: kept so results can be reproduced, **not recommended**. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead
- **Initialised from:** [`LFM3-VL-2B-MobileAgent-Dev-OwnHistory`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory)
- **Recipe builds on:** [`LFM3-VL-2B-MobileAgent-Dev-OwnHistory`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory)
- **What was added:** 500 more SFT steps on the same mix

Round 5: [OwnHistory](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory) trained **longer on the same data mix** (the "more epochs" test). Tests whether more training on the same mix helps.

| | |
|---|---|
| Start | OwnHistory (merged weights) |
| Method | 500 more SFT steps × 32 rows (16,000 rows, ≈0.17 epoch; cut from 800 for credits before any result) sampled from OwnHistory's own training data (about 43% already seen), warm-up → constant → linear decay (last 15%), lr 1e-4; new language-only LoRA r64/α128 merged into the weights (adapter in `lora_adapter/`); vision tower and projector frozen |
| Data | OwnHistory's training data, unchanged (AndroidControl, GUI-Odyssey, AMEX, ScreenQA with WaitRelabel / OwnHistory edits) |
| Phone format | 4-bit GGUF: [LFM3-VL-2B-MobileAgent-Dev-ContinuedSFT-GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-ContinuedSFT-GGUF) |
| Status | **Failed its online gate (round 5); use Main (the main model) or OwnHistory.** AndroidWorld seed 30: 24/116, the best LFM3 count so far, but +6 over OwnHistory is below the pre-declared noise yardstick (+9), and it ended with a false `complete` more often (37 vs 22–25). A lead worth re-testing, not a validated improvement |

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

Pre-registered round 5 (gates fixed on 2026-11-22 before training). Offline gate passed, online gate failed.

| Offline (gate) | OwnHistory | ContinuedSFT | Threshold |
|---|---|---|---|
| Parse rate | 1.000 | 1.000 | ≥ 0.99 |
| AndroidControl test, high-level step accuracy | 0.732 | 0.736 | ≥ 0.712 |
| AndroidControl terminal `complete` accuracy | 0.738 | 0.757 | ≥ 0.70 |
| Dev `answer` / dev `complete` | 0.868 / 0.812 | 0.860 / 0.875 | ≥ 0.848 / — |
| Validation loss (AndroidControl val, final; each repo's `training_logs/log_history.json`) | 0.340 | 0.334 | — |

| AndroidWorld seed 30 (116 tasks, development) | OwnHistory | ContinuedSFT | Threshold |
|---|---|---|---|
| Successes | 18 (replicate: 19) | **24** | net gain ≥ 9 over OwnHistory → **+6, fail** |
| False `complete` (ended "done", checker says no) | 25 (replicate: 22) | **37** | ≤ 15 with ≥ 16 successes → **fail** |

- The gain has the same size against Main (+6, p = 0.15) and the OwnHistory replicate (+5, p = 0.23), but is not significant.
- It ends more tasks by declaring them done (56 vs 37–38; paired p = 0.03 vs OwnHistory); the share of those that are right is unchanged (0.34).

## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step, no memory beyond the 8-step text history.
- Declares tasks done too early more often than OwnHistory; not evaluated on MobileWorld or sealed seeds.

## Project

Code, data builders, benchmark harnesses and every result with its source: [experimentalmachines/lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent) (see [models](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/models.md) and [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md)).

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
