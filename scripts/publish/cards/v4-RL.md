---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: experimentalmachines/LFM3-VL-2B-MobileAgent-v4
base_model_relation: finetune
pipeline_tag: image-text-to-text
library_name: transformers
language:
- en
datasets:
- experimentalmachines/MobileAgent-RL-v4
tags:
- android
- gui-agent
- mobile-agent
- screenshot
- lora
---

# LFM3-VL-2B-MobileAgent-v4-RL

v4 plus 200 steps of GRPO reinforcement learning on static screenshots. Not promoted.

| | |
|---|---|
| Start | [LFM3-VL-2B-MobileAgent-v4](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4) |
| Method | GRPO (TRL) on static screenshots, 4 samples per state, KL β 0.001, LoRA rank 16, lr 1e-5; merged |
| Training | 200 steps, 0.95 h on one A100; mean reward over the first / last 20 steps 0.714 → 0.765 |
| Data | [MobileAgent-RL-v4](https://huggingface.co/datasets/experimentalmachines/MobileAgent-RL-v4) @ `9ba36d90`: 2,000 states (700 answer, 500 complete, 300 other, 500 click) |
| Phone format | 4-bit GGUF: [LFM3-VL-2B-MobileAgent-v4-RL-GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4-RL-GGUF) |
| Status | **Not promoted:** failed the promotion rule fixed before training ended; not run on AndroidWorld |

## Evaluation (offline promotion rule)

| Check | Rule | v4 | v4-RL | Result |
|---|---|---|---|---|
| Strict answer match, 136 held-out questions | ≥ v4 + 0.05 | 0.868 | 0.890 | fail |
| AndroidControl test, high-level step accuracy | ≥ v4 − 0.02 | 0.728 | 0.667 | fail |
| False answers on 80 action-goal controls | ≤ 0.03 | 0.00 | 0.00 | pass |

- **Diagnosis:** on average 66% of the sampled groups per step had zero reward variance, and 60% of states were
  terminal screens, so little learning signal reached ordinary actions.
- Tokenizer files are v4's (the GRPO trainer had saved a left-padding setting); see `v4rl_local_export_manifest.json`.

## Input and output

| Part | Format |
|---|---|
| Image | One screenshot per step, resized to at most 880 × 880 px of area (about 720 image tokens) |
| User text | `Goal: …` / `Installed apps: …` / `Previous steps:` (last 8 steps as `n. <intent> -> <action JSON>`, or `None`) / `What is the next action?` |
| Output | `<think>short intent</think>` followed by one compact JSON action; coordinates are integers on a 0–1000 grid |
| Decoding | Thinking on, temperature 0 |

<details><summary>System prompt (v4 format)</summary>

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

## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step, no memory beyond the 8-step text history.
- Trained only on recorded demonstrations; it has never interacted with a live phone during training.

## Project

Code, data builders, benchmark harnesses and every result with its source: [experimentalmachines/lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent) (see [models](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/models.md) and [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md)).

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
