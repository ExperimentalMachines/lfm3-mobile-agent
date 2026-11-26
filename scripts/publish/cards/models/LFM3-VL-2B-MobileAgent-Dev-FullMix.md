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
# LFM3-VL-2B-MobileAgent-Dev-FullMix

- **Name:** `LFM3-VL-2B-MobileAgent-Dev-FullMix` (formerly `LFM3-VL-2B-MobileAgent-v4.5-D`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Development checkpoint**: kept so results can be reproduced, **not recommended**. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead
- **Initialised from:** the base model
- **Recipe builds on:** [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent)
- **What was added:** one pass over all candidate sources, 24-step history, change notes

A 2B screenshot-only Android agent from round 7 of [LFM3 Mobile Agent](https://github.com/experimentalmachines/lfm3-mobile-agent):
one full pass over [MobileAgent-SFT-FullMix](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-FullMix)
(173,430 rows, about twice Main's data), with a **24-step text history** and **"[no visible change]" notes**.

**Status: not promoted.** It failed one check of the round's pre-registered offline gate: it says `status` two or more
steps before the end of AndroidControl episodes more often than Main (3.64% vs 2.74%; bar 3.24%). An exploratory
AndroidWorld run (outside the gate) is below. [LFM3-VL-2B-MobileAgent](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) remains
the evaluated model.

| | |
|---|---|
| Base | LiquidAI/LFM3-VL-2B @ `23387be` |
| Method | LoRA SFT (rank 64, alpha 128) on the language model, vision tower frozen; merged into the weights (adapter in `lora_adapter/`) |
| Training | 5,420 steps × 32 rows (one pass), lr 2e-4 cosine, no gradient checkpointing; one H100, 3.4 h |
| Data | [MobileAgent-SFT-FullMix](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-FullMix) @ `45331aaa`: all AndroidControl rows, uncapped GUI-Odyssey and AMEX (blank intents filled from Aguvis), MemGUI-3K, ScreenQA |
| Phone format | None published |

## Input and output

| Part | Format |
|---|---|
| Image | One screenshot per step, resized to at most 880 × 880 px of area |
| User text | `Goal: …` / `Installed apps: …` / `Previous steps:` (**last 24 steps**; ` [no visible change]` after a step whose next screenshot did not change) / `What is the next action?` |
| Output | `<think>short intent</think>` followed by one compact JSON action, on a 0–1000 grid |

Use the same history window and notes at run time (AndroidWorld harness: `--history_steps 24 --nochange_notes`).

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

## Offline evaluation

Transformers bf16, greedy. FullMix on its own prompt format; Main on its own (8-step) format, same evaluator.

| Metric | FullMix | Main | Gate bar |
|---|---|---|---|
| AndroidControl test, high-level step accuracy | **0.753** | 0.727 | ≥ 0.707 |
| `dev_answer` / `dev_complete` | 0.882 / **0.800** | 0.890 / 0.763 | ≥ 0.840 / ≥ 0.713 |
| AndroidControl: `status` ≥ 2 steps before the end | 3.64% | 2.74% | ≤ 3.24% (**fail**) |
| AndroidLens step accuracy at steps ≥ 10 | **0.471** | 0.367 | ≥ 0.367 |
| AndroidLens step accuracy, all steps | 0.507 | 0.414 | — |
| AndroidLens `complete` at the real last step | **57.6%** | 12.2% | — |
| MemGUI dev step accuracy | 0.697 | 0.421 | — |
| Validation loss (AndroidControl val, Main's format) | 0.252 | 0.306 | — |

- **Stronger almost everywhere offline,** most on long tasks and on stopping at the real end.
- **But it stops early more often:** on the same AndroidControl rows it says `status` where Main continues 114 times, the
  reverse 52 times (p < 0.0001). Early stopping is the main online failure of these models, so it was not run online
  as a confirmatory test.
- **Full record:** [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md) and
  [preregistration](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/preregistrations/round-07-full-mix-long-history.md).

## Exploratory AndroidWorld run (not part of the gate)

Seed 30, 116 tasks, 4-bit GGUF on a Mac emulator (owner-requested exception after the offline gate).

| | Main | **FullMix** |
|---|---|---|
| Successes | 18 | 21 (paired p = 0.61) |
| False completes | 25 | 27 |
| Share of steps spent waiting | 29.1% | 16.9% |

Its successor [Counterfactual](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual) targets the false completes.

## Limitations

- Research model, not promoted. Do not let it act unattended on a phone with real accounts, messages or payments.
- Not run on MobileWorld; AndroidWorld only as the exploratory run above.
- English goals, one screenshot per step, memory limited to the 24-step text history.

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
