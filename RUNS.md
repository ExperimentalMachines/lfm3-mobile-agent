# Training runs

All LFM3-VL-2B versions use the same recipe and budget so that data/prompt changes are the only variable: LoRA r64 /
α128 on the language model only (vision tower untouched), lr 2e-4, 1,250 optimizer steps × 32 rows (batch 8 × grad-accum 4),
pixel budget 880×880, one screenshot + text history per step, output `<think>intent</think>` + one JSON action.
Checkpoints were pushed to the hub every 50 steps so a lost VM could resume.

| run | training data @ revision | steps | rows/step | lr | LoRA r | train rows | epochs seen | train loss | eval loss | wall h | peak GPU GB | checkpoint repo | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LFM3-VL-2B v1 (AndroidControl) | experimentalmachines/AndroidControl-screen-agent-sft@train | 1250 | 32 | 0.0002 | 64 | 99216 | 0.403 | 0.2846 | 0.2875 | 1.14 | 11.0 | experimentalmachines/LFM3-VL-2B-AndroidControl-LoRA-ckpt | Modal; a first attempt reached step 200 (results/training/lfm3vl2b/train_log.jsonl), this is the resumed run |
| LFM2.5-VL-450M v1 (AndroidControl) | experimentalmachines/AndroidControl-screen-agent-sft@train | 1 epoch (1875 steps) | 32 | 0.0001 | 16 | 60000 | 1.0 | 0.4689 | 0.375 | 0.96 | 8.5 | experimentalmachines/LFM2.5-VL-450M-AndroidControl-LoRA-ckpt | Modal |
| Qwen3.5-2B v1 (AndroidControl) | experimentalmachines/AndroidControl-screen-agent-sft@train | 1250 | 32 | 0.0002 | 64 | 99216 | 0.403 | 0.2393 | 0.2396 | 0.86 | 10.8 | experimentalmachines/Qwen3.5-2B-AndroidControl-LoRA-ckpt |  |
| Qwen3.5-0.8B v1 (AndroidControl) | experimentalmachines/AndroidControl-screen-agent-sft@train | 1 epoch (1875 steps) | 32 | 0.0001 | 16 | 60000 | 1.0 | 0.3811 | 0.2756 | 0.6 | 8.3 | experimentalmachines/Qwen3.5-0.8B-AndroidControl-LoRA-ckpt |  |
| LFM3-VL-2B v2 (AC + GUI-Odyssey + AMEX + ScreenQA) | experimentalmachines/AndroidAgent-SFT-v2@train#42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a | 1250 | 32 | 0.0002 | 64 | 78982 | 0.507 | 0.2048 | 0.2994 | 1.63 | 10.2 | alpharomercoma/LFM3-VL-2B-AndroidAgent-v2-LoRA-ckpt |  |
| Qwen3.5-2B v2 (same mix) | experimentalmachines/AndroidAgent-SFT-v2@train#42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a | 1250 | 32 | 0.0002 | 64 | 78982 | 0.507 | 0.1684 | 0.2501 | 1.61 | 10.0 | alpharomercoma/Qwen3.5-2B-AndroidAgent-v2-LoRA-ckpt |  |
| LFM3-VL-2B v3 (v2 mix, every intent filled) | alpharomercoma/AndroidAgent-SFT-v3@train#565ba76c4b10b6733549151f0fece1f70bc33b9c | 1250 | 32 | 0.0002 | 64 | 78952 | 0.507 | 0.3849 | 0.2999 | 1.23 | 11.0 | alpharomercoma/LFM3-VL-2B-AndroidAgent-v3-LoRA-ckpt | Modal |
| LFM3-VL-2B v4 (v4b data: v3 + navigate-then-answer + app list) | alpharomercoma/AndroidAgent-SFT-v4@train#337553984ee970a767dceb21adc6343f3d613602 | 1250 | 32 | 0.0002 | 64 | 92229 | 0.434 | 0.3363 | 0.306 | 1.99 | 11.5 | alpharomercoma/LFM3-VL-2B-AndroidAgent-v4b-LoRA-ckpt | Colab A100; VM lost at step 353 and resumed from the step-350 hub checkpoint: wall h = the resumed segment (steps 351-1250) |
| LFM3-VL-2B v4-RL (static-screenshot GRPO from v4) | alpharomercoma/AndroidAgent-RL-v4@9ba36d90 (2,000 states: 700 answer, 500 complete, 300 other, 500 click) | 200 |  | 1e-05 | 16 | 2000 |  |  |  | 0.95 | 13.4 | alpharomercoma/LFM3-VL-2B-AndroidAgent-v4-RL-ckpt | GRPO (TRL), 4 samples/state, KL beta 0.001, LoRA r16; NOT promoted (results/v4rl_promotion_offline.json) |


Columns come from each run's `run_config.json` / `train_summary.json` / `train_log.jsonl` (the `source` path in
`data/runs.json`). "epochs seen" = fraction of the training set covered by 1,250 × 32 rows.

## What each version changed and what happened

| version | change | result (AndroidWorld seed 30) | lesson |
|---|---|---|---|
| **v1** | AndroidControl only (official train episodes, high-level goals) | 15/116 | strong action baseline; never emits `answer` |
| **v2** | + GUI-Odyssey, AMEX, ScreenQA (v2 mix) | 3/116 (vs v1 0–12, p = 4.9e-04) | 8,739 rows had a **blank intent** (`<think></think>`): the model learned to act without planning |
| v2 + forced intent | inference-only ablation: force a one-line intent | 6/116 | confirms the blank-intent diagnosis, not a fix |
| v1 + runtime feedback | inference-only ablation: lexical app resolution + failure notes | 10/116 | worse; dropped |
| **v3** | v2 mix with every intent filled | 13/116 (vs v1 4–6, p = 0.75) | offline gains on Odyssey/AMEX/ScreenQA did not transfer to AndroidWorld |
| v4 (data 570febb) | first v4 build | — (abandoned before evaluation) | Codex data audit returned STOP (answer-leaking goals, guard gaps); retrained on rebuilt data |
| **v4 (v4b data)** | v3 rewritten to the v4 prompt (answer-vs-complete rules + the device's installed-app list) + navigate-then-answer episodes built from AndroidControl *train* episodes (questions/answers from Qwen3-VL-8B, verified by a second call and a strict typed check) + shortened ScreenQA answers | **18/116** (6 answer + 12 action) | fixed "never answers"; passed the gate; frozen as LFM3 final |
| v4-RL | 200 steps of static-screenshot GRPO from v4 (LoRA r16, KL 0.001, 4 samples/state) | not run (failed offline promotion) | answering up (0.868 → 0.890) but AndroidControl high-level step SR down (0.728 → 0.667); 60 % of groups had zero reward variance; 60 % of the state pool were terminal screens |

Other base models with the v1 recipe: Qwen3.5-2B (16/116), Qwen3.5-0.8B (12/116), LFM2.5-VL-450M (2/116). Qwen3.5-2B v2
mirrors LFM3 v2 (same mix).

## RL run details (v4-RL)

* data: alpharomercoma/AndroidAgent-RL-v4@9ba36d90 (2,000 states: 700 answer, 500 complete, 300 other, 500 click)
* steps: 200, wall 0.95 h on a Colab A100, peak GPU 13.4 GB
* mean reward first 20 steps 0.714 → last 20 steps 0.765
* GRPO (TRL), 4 samples/state, KL beta 0.001, LoRA r16; NOT promoted (results/v4rl_promotion_offline.json)

Promotion rule (pre-registered before training ended): strict dev_answer ≥ +0.05, dev_complete false answers ≤ 0.03,
AndroidControl high-level step SR ≥ −0.02, then AndroidWorld seed 30 ≥ v4. Outcome: [results/v4rl_promotion_offline.json](results/v4rl_promotion_offline.json) — fails (a) and (c).
