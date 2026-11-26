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
# LFM3-VL-2B-MobileAgent-Dev-DPOStopMistakes

- **Name:** `LFM3-VL-2B-MobileAgent-Dev-DPOStopMistakes` (formerly `LFM3-VL-2B-MobileAgent-v4.3-dpo2`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Development model**: kept so results can be reproduced, **not recommended**. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead
- **Initialised from:** [`LFM3-VL-2B-MobileAgent-Dev-OwnHistory`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory)
- **Recipe builds on:** [`LFM3-VL-2B-MobileAgent-Dev-OwnHistory`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory)
- **What was added:** DPO on 851 balanced stop / copied-intent mistakes

Round 5 (post-hoc fix of the DPOAllMistakes model): [OwnHistory](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory) trained to prefer the human step over **its own mistakes**. Learns from its own attempts: the contrast between its own wrong step and the right step at the same screen.

| | |
|---|---|
| Start | OwnHistory (merged weights) |
| Method | Step-level DPO (β 0.1, lr 1e-5) + 1.0 × SFT on the preferred step; new language-only LoRA r64/α128 merged into the weights (adapter in `lora_adapter/`); vision tower and projector frozen |
| Data | OwnHistory decoded its own training rows greedily; where it stopped too early, missed a stop, or copied its previous intent, the pair is human step (preferred) vs its own step (rejected): 851 balanced pairs (DPOAllMistakes used all 4,163 mistakes and collapsed whole action types). No environment, teacher model or benchmark data |
| Phone format | 4-bit GGUF: [LFM3-VL-2B-MobileAgent-Dev-DPOStopMistakes-GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-DPOStopMistakes-GGUF) |
| Status | **Failed its online gate (round 5); use Main (the main model) or OwnHistory.** AndroidWorld seed 30: 21/116 vs OwnHistory's 18, a +3 gain that is inside run-to-run noise (two identical OwnHistory runs differ on 9 tasks), and it did not reduce false `complete`s (28 vs 22–25). Kept public as a documented negative result |

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

| Offline (gate) | OwnHistory | DPOStopMistakes | Threshold |
|---|---|---|---|
| Parse rate | 1.000 | 1.000 | ≥ 0.99 |
| AndroidControl test, high-level step accuracy | 0.732 | 0.728 | ≥ 0.712 |
| AndroidControl terminal `complete` accuracy | 0.738 | **0.785** | ≥ 0.70 |
| Dev `answer` / dev `complete` | 0.868 / 0.812 | 0.875 / 0.838 | ≥ 0.848 / — |

| AndroidWorld seed 30 (116 tasks, development) | OwnHistory | DPOStopMistakes | Threshold |
|---|---|---|---|
| Successes | 18 (replicate: 19) | 21 | net gain ≥ 9 over OwnHistory → **+3, fail** |
| False `complete` (ended "done", checker says no) | 25 (replicate: 22) | **28** | ≤ 15 with ≥ 16 successes → **fail** |

- The offline gain at the last step did not show up online: on the AndroidWorld emulator its stopping is indistinguishable from OwnHistory's (false `complete` 26 vs 25 on the tasks neither run crashed, p = 1.0).
- Its +3 is noise-level: paired McNemar p = 0.55; against the identical OwnHistory replicate it is +2 (p = 0.69).

## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step, no memory beyond the 8-step text history.
- Not better than OwnHistory on AndroidWorld; not evaluated on MobileWorld or sealed seeds.

## Project

Code, data builders, benchmark harnesses and every result with its source: [experimentalmachines/lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent) (see [models](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/models.md) and [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md)).

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
