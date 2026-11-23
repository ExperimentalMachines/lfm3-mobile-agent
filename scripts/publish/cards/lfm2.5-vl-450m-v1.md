---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: LiquidAI/LFM2.5-VL-450M
pipeline_tag: image-text-to-text
library_name: transformers
language:
- en
datasets:
- experimentalmachines/MobileAgent-SFT-v1
tags:
- android
- gui-agent
- mobile-agent
- screenshot
- lora
---

# LFM2.5-VL-450M-MobileAgent-v1

[LiquidAI/LFM2.5-VL-450M](https://huggingface.co/LiquidAI/LFM2.5-VL-450M) fine-tuned on AndroidControl with a smaller recipe. Trained on the same data as LFM3-VL-2B v1 to compare base models; not part of the main line. The project's main model is [LFM3-VL-2B-MobileAgent-v4](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4).

| | |
|---|---|
| Base | LiquidAI/LFM2.5-VL-450M |
| Method / training | LoRA SFT (rank 16, alpha 32), lr 1e-4, one epoch: 1,875 steps × 32 rows of 48,000 AndroidControl rows + 12,000 general image-text replay rows (to protect general knowledge); merged (adapter in `lora_adapter/`) |
| Data | [MobileAgent-SFT-v1](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v1) (AndroidControl) + general replay rows |
| Phone format | 4-bit GGUF: [LFM2.5-VL-450M-MobileAgent-v1-GGUF](https://huggingface.co/experimentalmachines/LFM2.5-VL-450M-MobileAgent-v1-GGUF) |
| Status | Comparison model |

## Evaluation

| Benchmark | LFM2.5-VL-450M v1 | Base model |
|---|---|---|
| AndroidWorld seed 30 (116 tasks, development) | 2 | 0 |
| AndroidControl test, high- / low-level step accuracy | 0.536 / 0.862 | — |
| Terminal `complete` accuracy | 0.561 | — |
| MMStar / MMLU | 39.3% / 39.2% | — |
| Apple M5 GPU, median seconds per step | 1.14 | 2.21 |

- Too small for multi-step phone tasks at this recipe.

## Input and output

| Part | Format |
|---|---|
| Image | One screenshot per step at the processor's default size |
| User text | `Goal: …` / `Previous steps:` (last 8 steps as `n. <intent> -> <action JSON>`, or `None`) / `What is the next action?` |
| Output | `<think>short intent</think>` followed by one compact JSON action; coordinates are integers on a 0–1000 grid |
| Decoding | Thinking on, temperature 0 |

<details><summary>System prompt (v1–v3 format)</summary>

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

LFM Open License v1.0, inherited from [LiquidAI/LFM2.5-VL-450M](https://huggingface.co/LiquidAI/LFM2.5-VL-450M) ([LICENSE](LICENSE)).
