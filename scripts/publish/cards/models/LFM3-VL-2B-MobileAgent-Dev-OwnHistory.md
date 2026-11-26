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
# LFM3-VL-2B-MobileAgent-Dev-OwnHistory

- **Name:** `LFM3-VL-2B-MobileAgent-Dev-OwnHistory` (formerly `LFM3-VL-2B-MobileAgent-v4.2`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Development model**: kept so results can be reproduced, **not recommended**. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead
- **Initialised from:** the base model
- **Recipe builds on:** [`LFM3-VL-2B-MobileAgent-Dev-WaitRelabel`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-WaitRelabel)
- **What was added:** + the model's own replayed history on training episodes

A 2B screenshot-only Android agent: [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) fine-tuned to operate
a phone from one screenshot per step. WaitRelabel's data plus training on the model's own outputs, aimed at Main's `wait` loops.

| | |
|---|---|
| Base | LiquidAI/LFM3-VL-2B @ `23387be` |
| Method | LoRA SFT (rank 64, alpha 128) on the language model, vision tower frozen; merged into the weights (adapter in `lora_adapter/`) |
| Training | 1,250 steps × 32 rows (0.43 epoch of 92,229 rows), lr 2e-4, one A100 — the same recipe, rows and row order as Main |
| Data | AndroidControl, GUI-Odyssey, AMEX, ScreenQA (WaitRelabel's data with self-generated history, below) |
| Phone format | 4-bit GGUF: [LFM3-VL-2B-MobileAgent-Dev-OwnHistory-GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory-GGUF) |
| Status | Experimental; no better than Main on AndroidWorld, slightly ahead on MobileWorld (not significant) |

## What changed

| Edit | Why |
|---|---|
| WaitRelabel's edits: `wait` relabel and recovery history | 94% of AndroidControl's `wait` rows repeat the previous step's intent, which taught Main to loop |
| **Self-generated history** on 40% of training episodes | WaitRelabel replayed those episodes on their recorded screens with its own earlier outputs as history: steps it got right keep its own words, other steps get the human step. The training rows then carry this history, and the human's next action stays the target (semi-online patching as in UI-S1, arXiv 2509.11543, without RL) |
| **Own-mistake rows** | Where WaitRelabel wrongly chose `wait`, the row for that step shows that mistake (its own intent + `wait`) as the last history step; a wait leaves the screen unchanged, so screen and target still fit |

No environment, no teacher model and no benchmark data were used.

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

Post-hoc follow-up: designed after reading Main's MobileWorld results, so MobileWorld is a development benchmark here
(Main's 6/105 stays the held-out number). One run each, temperature 0, 4-bit GGUF; exceptions count as failures.

| Benchmark | OwnHistory | Main | Paired |
|---|---|---|---|
| AndroidWorld, seed 30 (116 tasks, development) | 18 | 18 | +6 / −6 |
| MobileWorld, 105 English GUI-only tasks | 8 | 6 | +3 / −1, exact McNemar p = 0.63 |
| AndroidControl test, high- / low-level step accuracy | 0.732 / 0.888 | 0.728 / 0.908 | — |
| MMStar / MMLU (general knowledge) | 55.7% / 50.3% | 52.9% / 50.4% | — |

- **Loops halved on MobileWorld:** `wait` fell from 21% to 5% of steps and repeated intents from 67% to 33%,
  but success barely moved. Neither difference from Main is significant.
- For comparison on the same MobileWorld tasks (our harness): GUI-Owl-1.5-2B 22/105, MAI-UI-2B 11/105.
- OwnHistory has not been run on the held-out AndroidWorld seeds (Main: 54/348).

## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step, no memory beyond the 8-step text history.
- Trained only on recorded demonstrations; it has never interacted with a live phone during training.

## Project

Code, data builders, benchmark harnesses and every result with its source: [experimentalmachines/lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent) (see [models](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/models.md) and [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md)).

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
