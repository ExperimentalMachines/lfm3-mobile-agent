---
license: other
license_name: lfm1.0
base_model: LiquidAI/LFM3-VL-2B
tags: [android, gui-agent, screen-agent, phone, gguf]
---
# LFM3-VL-2B AndroidAgent v3

Screenshot-only Android phone agent: one screenshot + goal + short text history in, a one-sentence intent in
`<think>` and one JSON action out (click / long_press / input_text / scroll / open_app / navigate_back /
navigate_home / keyboard_enter / wait / answer / status), coordinates 0-1000. Built to run on phones
(llama.cpp GGUF, Q4_K_M).

* Merged weights: [alpharomercoma/LFM3-VL-2B-AndroidAgent-v3](https://huggingface.co/alpharomercoma/LFM3-VL-2B-AndroidAgent-v3) · Phone GGUF: [alpharomercoma/LFM3-VL-2B-AndroidAgent-v3-GGUF](https://huggingface.co/alpharomercoma/LFM3-VL-2B-AndroidAgent-v3-GGUF)
* Training data: [`alpharomercoma/AndroidAgent-SFT-v3`](https://huggingface.co/datasets/alpharomercoma/AndroidAgent-SFT-v3) @ `565ba76c4b`: the v2 mix (AndroidControl +
  GUI-Odyssey + AMEX + ScreenQA) with every blank training intent filled (6,106 tap/long-press intents written by
  Qwen3-VL-8B-Instruct from the screenshot with the tap point marked, 2,603 templated; 30 rows dropped; 78,952 rows).
  Actions, images and dev splits are unchanged from v2.
* Recipe (identical to v1 and v2, so they are equal-budget controls): LoRA r64/alpha128 on all language-model linear
  layers, lr 2e-4, 1,250 steps x 32 rows (about half an epoch), 774,400-pixel image budget. Vision tower frozen.

## Results

| Evaluation | v1 (AndroidControl only) | v2 (mix, blank intents) | **v3 (this model)** |
|---|---|---|---|
| AndroidControl test step SR, high-level | 0.715 | 0.716 | **0.723** |
| AndroidControl test step SR, low-level | 0.948 | 0.893 | 0.902 |
| AndroidControl terminal ('complete') | 0.792 | 0.732 | 0.725 |
| GUI-Odyssey held-out episodes | 0.269 | 0.644 | **0.662** |
| AMEX held-out episodes | 0.306 | 0.735 | **0.741** |
| ScreenQA validation (answer) | 0.000 | **0.764** | 0.724 |
| AndroidWorld, 116 tasks, seed 30, this GGUF, 1 screenshot/step (full successes) | 15/116 | 3/116 | 13/116 |
| General knowledge (forced-choice, paired vs base) | MMStar 57.1% (+5.0 pp vs base, p=3e-07); MMLU 49.5% (+0.6 pp vs base, p=0.68) | MMStar 54.6% (+2.5 pp vs base, p=0.018); MMLU 50.9% (+2.0 pp vs base, p=0.085) | MMStar 55.3% (+3.2 pp vs base, p=0.0022); MMLU 50.0% (+1.1 pp vs base, p=0.38) |

AndroidWorld, paired on identical task instances (exact McNemar):
* v3 vs v1: v1-only 6, v3-only 4 (p=0.75) - **no detectable difference**.
* v3 vs v2: v3-only 10, v2-only 0 (p=0.002) - v2's regression is fixed.
* v3 vs GUI-Owl-1.5-2B in the same harness and budget (1 screenshot, Q4_K_M, 23/116): GUI-Owl-only 18,
  v3-only 8 (p=0.076). GUI-Owl's published 67.9% uses its own harness (5 screenshots,
  full resolution, unquantized); the numbers are not comparable.

Known limitations (AndroidWorld failure analysis): v3 never emits `answer` (0 episodes),
so it fails the ~25 information-retrieval tasks; it declares `complete` on 38
failed tasks; it misnames some apps (e.g. "Marker" for Markor). AndroidWorld seed 30 was used to choose between
v1/v2/v3, so treat these scores as development-set numbers. Mean model latency 2.8 s/step (Apple M5, llama.cpp).
No AndroidWorld tasks, variants, trajectories or checkers were used in training.

Serving (llama.cpp): `llama-server -m LFM3-VL-2B-AndroidAgent-v3-Q4_K_M.gguf --mmproj mmproj-LFM3-VL-2B-Q8_0.gguf
-c 8192 --image-max-tokens 1024 --reasoning-format deepseek`. Prompt/action format: `train/agent_format.py` in the
lfm3-android project.

Derivative of LiquidAI/LFM3-VL-2B under its license (lfm1.0). The LoRA is language-model only; the vision projector
file is the base model's.

