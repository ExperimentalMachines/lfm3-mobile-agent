---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: experimentalmachines/LFM3-VL-2B-MobileAgent
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
# LFM3-VL-2B-MobileAgent-Dev-MemGUIContinuedSFT

- **Name:** `LFM3-VL-2B-MobileAgent-Dev-MemGUIContinuedSFT` (formerly `LFM3-VL-2B-MobileAgent-v4.4-C`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Development model**: kept so results can be reproduced, **not recommended**. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead
- **Initialised from:** [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent)
- **Recipe builds on:** [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent)
- **What was added:** 500 more steps on 50% MemGUI / 50% main-model rows

A 2B screenshot-only Android agent from round 6 of [LFM3 Mobile Agent](https://github.com/experimentalmachines/lfm3-mobile-agent): Main continued for 500 steps on 50% MemGUI rows and 50% Main rows.

**Status: not promoted.** It failed the round's pre-registered offline gate on one check (late-step early stops on
AndroidControl) and was not run online. [LFM3-VL-2B-MobileAgent](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent)
remains the evaluated model.

| | |
|---|---|
| Base | [experimentalmachines/LFM3-VL-2B-MobileAgent](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) |
| Method | LoRA SFT (rank 64, alpha 128) on Main's merged weights, vision tower frozen; merged (adapter in `lora_adapter/`) |
| Training | 500 steps × 32 rows, lr 1e-4 warm-up / stable / short decay, one A100 |
| Data | [MobileAgent-SFT](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT) @ `3375539` + [MobileAgent-SFT-MemGUI](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-MemGUI) @ `2b481ae3` (MemGUI-3K rows, filtered: no AndroidWorld, MobileWorld or AndroidLab apps) |
| Phone format | 4-bit GGUF: [LFM3-VL-2B-MobileAgent-Dev-MemGUIContinuedSFT-GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MemGUIContinuedSFT-GGUF) (Q4_K_M + vision projector) |

## Input and output

The same as Main:

| Part | Format |
|---|---|
| Image | One screenshot per step, resized to at most 880 × 880 px of area |
| User text | `Goal: …` / `Installed apps: …` / `Previous steps:` (last 8 steps) / `What is the next action?` |
| Output | `<think>short intent</think>` followed by one compact JSON action, on a 0–1000 grid |

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

- **Setup:** Transformers bf16, greedy, the same pre-rendered splits for Main and the candidates.
- **AndroidLens English** (172 long episodes, evaluation only) is a static test with ground-truth history.

| Metric | MemGUIContinuedSFT | Main | Gate bar |
|---|---|---|---|
| AndroidControl test, high-level step accuracy | 0.724 | 0.727 | ≥ 0.707 |
| `dev_answer` / `dev_complete` | 0.875 / 0.788 | 0.890 / 0.763 | ≥ 0.840 / ≥ 0.713 |
| AndroidControl steps ≥ 4: predicted `status` | 9.8% | 9.0% | ≤ 6.0% |
| AndroidLens step accuracy at steps ≥ 10 | 0.413 | 0.367 | ≥ 0.347 |
| AndroidLens step accuracy, all steps | 0.444 | 0.414 | — |
| AndroidLens `complete` at the real last step | 47.7% | 12.2% | — |
| MemGUI dev step accuracy | 0.698 | 0.421 | — |

- **What improved:** long-task accuracy and stopping at the real end of long tasks.
- **What did not:** early stops on AndroidControl's late steps, which the round targeted. About half of those are one
  step before the end, where the human demonstrations add a final scroll or wait.
- **Full record:** [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md) and
  [preregistration](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/preregistrations/round-06-long-trajectories.md).

## Limitations

- Research model, not promoted. Do not let it act unattended on a phone with real accounts, messages or payments.
- Not run on AndroidWorld or MobileWorld.
- English goals, one screenshot per step, no memory beyond the 8-step text history.

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
