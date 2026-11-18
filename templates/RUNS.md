# Training runs

All LFM3-VL-2B versions use the same recipe and budget so that data/prompt changes are the only variable: LoRA r64 /
α128 on the language model only (vision tower untouched), lr 2e-4, 1,250 optimizer steps × 32 rows (batch 8 × grad-accum 4),
pixel budget 880×880, one screenshot + text history per step, output `<think>intent</think>` + one JSON action.
Checkpoints were pushed to the hub every 50 steps so a lost VM could resume.

{{table_training}}

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

{{rl_details}}
Promotion rule (pre-registered before training ended): strict dev_answer ≥ +0.05, dev_complete false answers ≤ 0.03,
AndroidControl high-level step SR ≥ −0.02, then AndroidWorld seed 30 ≥ v4. Outcome: [results/v4rl_promotion_offline.json](results/v4rl_promotion_offline.json) — fails (a) and (c).
