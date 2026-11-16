---
license: other
base_model: LiquidAI/LFM3-VL-2B
tags: [android, gui-agent, mobile, on-device, vision-language, gguf]
---

# LFM3-VL-2B-AndroidControl

Screenshot-only ("pixel") Android phone agent, fine-tuned from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) for on-device automation.
One screenshot (+ goal + short text history) in → one JSON action out. Built to run on phones (llama.cpp GGUF).

* Merged weights: [experimentalmachines/LFM3-VL-2B-AndroidControl](https://huggingface.co/experimentalmachines/LFM3-VL-2B-AndroidControl) · Phone GGUF: [experimentalmachines/LFM3-VL-2B-AndroidControl-GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-AndroidControl-GGUF)
* Recipe: LoRA r64/α128 on all language-model linears (vision + projector frozen), lr 2e-4 cosine, 1,250 steps × 32 (40k rows), bf16
* Data: AndroidControl (Google) **official train split only**, re-split by the official `splits.json` (the common HF mirror's
  random split leaks 1,238 test episodes — avoided); AndroidWorld-app episodes filtered out; synthetic `status: complete` step on each
  episode's final screen. Dataset: `experimentalmachines/AndroidControl-screen-agent-sft` (private).

## Results
| Benchmark | Score |
|---|---|
| AndroidControl test, high-level | step SR **0.715**, episode SR 0.283 |
| AndroidControl test, low-level | step SR **0.948**, episode SR 0.783 |
| 'task complete' (terminal) accuracy | 0.792 |
| MMSTAR (forced-choice, paired vs base) | 52.1% → 57.1% (+5.0 pp, McNemar p=0.00) |
| MMLU (forced-choice, paired vs base) | 48.9% → 49.5% (+0.6 pp, McNemar p=0.68) |

Offline history is teacher-forced (human step instructions), as in AndroidControl-Curated; closed-loop AndroidWorld is harder.

## Prompt / action format
System prompt and user text exactly as in `train/agent_format.py`; screenshot resized with Qwen2-VL-style `smart_resize`
(factor 32, ≤ 774,400 px → ~720 image tokens for a 1080×2400 phone). Output:

```
<think>one-sentence intent</think>{"action_type":"click","point_2d":[x,y]}
```
Coordinates are integers on a 0–1000 grid. Actions: click, long_press, input_text, scroll(up/down/left/right; down = reveal content
below), open_app, navigate_back, navigate_home, keyboard_enter, wait, answer, status(complete/infeasible).

<details><summary>System prompt</summary>

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

## On-device usage (llama.cpp)
```bash
llama-server -m LFM3-VL-2B-AndroidControl-Q4_K_M.gguf --mmproj mmproj-LFM3-VL-2B-Q8_0.gguf -c 8192 --image-max-tokens 1024 --reasoning-format deepseek
```
The vision tower and projector are unchanged by fine-tuning (LoRA on the language model only), so the base model's mmproj is used.

## License
LFM Open License v1.0 (inherited from LiquidAI/LFM3-VL-2B). Training data: AndroidControl (see its terms).
