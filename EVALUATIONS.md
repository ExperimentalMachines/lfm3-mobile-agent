# Evaluations

## 1. AndroidControl test (offline, 18,415 rows, greedy)

Step SR = predicted action matches the reference action under the project scorer (`eval/androidcontrol/score.py` in the
working repo); episode SR = every step of the episode correct. High-level = goal only; low-level = goal + step instruction.

| model | high-level step SR | high-level episode SR | low-level step SR | low-level episode SR | source |
|---|---|---|---|---|---|
| LFM3-VL-2B base | 0.3134 | 0.0272 | 0.6336 | 0.1732 | results/androidcontrol/lfm3vl2b-ac-lora_base.metrics.json |
| LFM3-VL-2B v1 | 0.7148 | 0.2826 | 0.9476 | 0.7827 | results/androidcontrol/lfm3vl2b-ac-lora_ft.metrics.json |
| LFM3-VL-2B v2 | 0.7159 | 0.2806 | 0.8932 | 0.6109 | results/androidcontrol/lfm3vl2b-v2mix-lora_ft.metrics.json |
| LFM3-VL-2B v3 | 0.7225 | 0.2871 | 0.902 | 0.6401 | results/androidcontrol/lfm3vl2b-v3mix-lora_ft.metrics.json |
| LFM3-VL-2B v4 | 0.7281 | 0.2897 | 0.9077 | 0.655 | results/v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft.metrics.json |
| LFM3-VL-2B v4-RL | 0.6672 | 0.2495 | 0.8385 | 0.5298 | results/v4rl_dev/lfm3vl2b-v4rl_ft.metrics.json |
| LFM2.5-VL-450M base | 0.0085 | 0.0 | 0.0242 | 0.0 | results/androidcontrol/lfm25vl450m-ac-lora_base.metrics.json |
| LFM2.5-VL-450M v1 | 0.5365 | 0.1283 | 0.8618 | 0.5208 | results/androidcontrol/lfm25vl450m-ac-lora_ft.metrics.json |
| Qwen3.5-2B base | 0.3841 | 0.048 | 0.5901 | 0.1342 | results/androidcontrol/qwen35-2b-ac-lora_base.metrics.json |
| Qwen3.5-2B v1 | 0.7335 | 0.3091 | 0.9492 | 0.7912 | results/androidcontrol/qwen35-2b-ac-lora_ft.metrics.json |
| Qwen3.5-2B v2 | 0.7385 | 0.3182 | 0.9065 | 0.6511 | results/androidcontrol/qwen35-2b-v2mix-lora_ft.metrics.json |
| Qwen3.5-0.8B base | 0.3916 | 0.0823 | 0.7373 | 0.2717 | results/androidcontrol/qwen35-08b-ac-lora_base.metrics.json |
| Qwen3.5-0.8B v1 | 0.6936 | 0.2534 | 0.9423 | 0.7626 | results/androidcontrol/qwen35-08b-ac-lora_ft.metrics.json |


## 2. Held-out dev splits (offline)

GUI-Odyssey test episodes, 5 % hash-held-out AMEX episodes, ScreenQA validation (v2+); `dev_answer` = 136
navigate-then-answer screens and `dev_complete` = 80 action-only completion controls (v4+, pinned at AndroidAgent-SFT-v4 @ 3375539).
Splits differ between v2/v3 and v4 builds, so compare within a version family only.

| model | split | rows | step SR | type match | answer F1 | source |
|---|---|---|---|---|---|---|
| LFM3-VL-2B v2 | dev_odyssey | 1000 | 0.644 | 0.84 |  | results/v2_dev/lfm3_v2_dev_odyssey.metrics.json |
| LFM3-VL-2B v2 | dev_amex | 468 | 0.735 | 0.9338 |  | results/v2_dev/lfm3_v2_dev_amex.metrics.json |
| LFM3-VL-2B v2 | dev_screenqa | 500 | 0.764 | 1.0 | 0.6894233360924235 | results/v2_dev/lfm3_v2_dev_screenqa.metrics.json |
| LFM3-VL-2B v3 | dev_odyssey | 1000 | 0.662 | 0.862 |  | results/v3_dev/lfm3_v3_dev_odyssey.metrics.json |
| LFM3-VL-2B v3 | dev_amex | 468 | 0.7415 | 0.9274 |  | results/v3_dev/lfm3_v3_dev_amex.metrics.json |
| LFM3-VL-2B v3 | dev_screenqa | 500 | 0.724 | 1.0 | 0.661670737490106 | results/v3_dev/lfm3_v3_dev_screenqa.metrics.json |
| LFM3-VL-2B v4 | dev_odyssey | 1000 | 0.637 | 0.856 |  | results/v4_dev/hub/eval/lfm3_v4_dev_odyssey.metrics.json |
| LFM3-VL-2B v4 | dev_amex | 468 | 0.7308 | 0.9103 |  | results/v4_dev/hub/eval/lfm3_v4_dev_amex.metrics.json |
| LFM3-VL-2B v4 | dev_screenqa | 500 | 0.79 | 1.0 | 0.7035510704374546 | results/v4_dev/hub/eval/lfm3_v4_dev_screenqa.metrics.json |
| LFM3-VL-2B v4 | dev_answer | 136 | 0.8897 | 0.9559 | 0.8647058823529411 | results/v4_dev/hub/eval/lfm3_v4_dev_answer.metrics.json |
| LFM3-VL-2B v4 | dev_complete | 80 | 0.7625 | 0.7625 |  | results/v4_dev/hub/eval/lfm3_v4_dev_complete.metrics.json |
| LFM3-VL-2B v4-RL | dev_odyssey | 1000 | 0.638 | 0.853 |  | results/v4rl_dev/lfm3_v4rl_dev_odyssey.metrics.json |
| LFM3-VL-2B v4-RL | dev_amex | 468 | 0.7329 | 0.9145 |  | results/v4rl_dev/lfm3_v4rl_dev_amex.metrics.json |
| LFM3-VL-2B v4-RL | dev_screenqa | 500 | 0.786 | 1.0 | 0.7013981882319408 | results/v4rl_dev/lfm3_v4rl_dev_screenqa.metrics.json |
| LFM3-VL-2B v4-RL | dev_answer | 136 | 0.9118 | 1.0 | 0.8846638655462185 | results/v4rl_dev/lfm3_v4rl_dev_answer.metrics.json |
| LFM3-VL-2B v4-RL | dev_complete | 80 | 0.9625 | 0.9625 |  | results/v4rl_dev/lfm3_v4rl_dev_complete.metrics.json |


## 3. General-capability retention (forced-choice log-prob)

| model | MMStar (1,500, log-prob) | MMLU (1,000, log-prob) | source |
|---|---|---|---|
| LFM3-VL-2B base | 0.5213 | 0.489 | results/general/lfm3vl2b-ac-lora_base_general_logprob.summary.json |
| LFM3-VL-2B v1 | 0.5713 | 0.495 | results/general/lfm3vl2b-ac-lora_ft_general_logprob.summary.json |
| LFM3-VL-2B v2 | 0.546 | 0.509 | results/general/lfm3vl2b-v2mix-lora_ft_general_logprob.summary.json |
| LFM3-VL-2B v3 | 0.5533 | 0.5 | results/general/lfm3vl2b-v3mix-lora_ft_general_logprob.summary.json |
| LFM3-VL-2B v4 | 0.5287 | 0.504 | results/v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft_general_logprob.summary.json |
| Qwen3.5-2B base | 0.4927 | 0.555 | results/general/qwen35-2b-ac-lora_base_general_logprob.summary.json |
| Qwen3.5-2B v1 | 0.5733 | 0.537 | results/general/qwen35-2b-ac-lora_ft_general_logprob.summary.json |
| Qwen3.5-2B v2 | 0.54 | 0.56 | results/general/qwen35-2b-v2mix-lora_ft_general_logprob.summary.json |
| Qwen3.5-0.8B base | 0.424 | 0.439 | results/general/qwen35-08b-ac-lora_base_general_logprob.summary.json |
| Qwen3.5-0.8B v1 | 0.4887 | 0.452 | results/general/qwen35-08b-ac-lora_ft_general_logprob.summary.json |
| LFM2.5-VL-450M base | 0.3847 | 0.399 | results/general/lfm25vl450m-ac-lora_base_general_logprob.summary.json |
| LFM2.5-VL-450M v1 | 0.3927 | 0.392 | results/general/lfm25vl450m-ac-lora_ft_general_logprob.summary.json |


## 4. AndroidWorld, development seed 30 (116 tasks)

Harness for every row: AndroidWorld 55ddaf5 + local fixes, Pixel 6 API 33 arm64 emulator on an Apple M5 Mac, model
served by llama.cpp as Q4_K_M + Q8_0 mmproj, one screenshot per step, temperature 0, step budget 10× task complexity,
success only if the agent ends the episode and the checker passes (exception = failure). Answer tasks = the 25
information-retrieval tasks scored on the agent's answer. Latency = median model time per step during the run.

| model | successes /116 | answer tasks (of 25) | action tasks (of 91) | exceptions | median steps | median step latency (s, Mac) | agent label | run |
|---|---|---|---|---|---|---|---|---|
| LFM3-VL-2B base (no thinking) | 1 | 0 | 1 | 2 | 12 | 2.13 | lfm3vl2b_base_nothink_q4km | results/androidworld/lfm3vl2b_base_nothink/run_20261116T190932199444/ |
| LFM3-VL-2B v1 | 15 | 0 | 15 | 2 | 10 | 2.66 | lfm3vl2b_ft_q4km | results/androidworld/lfm3vl2b_ft/run_20261117T030335477504/ |
| LFM3-VL-2B v1 + runtime feedback (ablation) | 10 | 0 | 10 | 7 | 10 | 2.85 | lfm3vl2b_ft_q4km_runtimefb | results/androidworld/lfm3vl2b_ft_runtimefb/run_20261117T112723045785/ |
| LFM3-VL-2B v2 | 3 | 0 | 3 | 5 | 10 | 2.61 | lfm3vl2b_v2_q4km | results/androidworld/lfm3vl2b_v2/run_20261117T153954478386/ |
| LFM3-VL-2B v2 + forced intent (inference ablation) | 6 | 0 | 6 | 4 | 10 | 2.68 | lfm3vl2b_v2_q4km_forcethink | results/androidworld/lfm3vl2b_v2_forcethink/run_20261117T201810135662/ |
| LFM3-VL-2B v3 | 13 | 0 | 13 | 3 | 10 | 2.61 | lfm3vl2b_v3_q4km | results/androidworld/lfm3vl2b_v3/run_20261117T210853476910/ |
| LFM3-VL-2B v4 (frozen final) | 18 | 6 | 12 | 4 | 10 | 2.96 | lfm3vl2b_v4_q4km | results/androidworld/lfm3vl2b_v4/run_20261118T093443059487/ |
| GUI-Owl-1.5-2B (matched: 1 screenshot, Q4_K_M) | 23 | 10 | 13 | 0 | 12 | 7.0 | guiowl15_2b_matched1img_q4km | results/androidworld/guiowl15_2b_matched/run_20261116T231457945810/ |
| Qwen3.5-2B v1 | 16 | 0 | 16 | 2 | 9 | 4.2 | qwen35_2b_ft_q4km | results/androidworld/qwen35_2b_ft/run_20261117T111259609427/ |
| Qwen3.5-0.8B v1 | 12 | 0 | 12 | 1 | 10 | 2.0 | qwen35_08b_ft_q4km | results/androidworld/qwen35_08b_ft/run_20261117T152004373700/ |
| LFM2.5-VL-450M base | 0 | 0 | 0 | 3 | 12 | 2.21 | lfm25vl450m_base_q4km | results/androidworld/lfm25vl450m_base/run_20261117T062246232259/ |
| LFM2.5-VL-450M v1 | 2 | 0 | 2 | 4 | 12 | 1.14 | lfm25vl450m_ft_q4km | results/androidworld/lfm25vl450m_ft/run_20261117T022926194002/ |


Paired comparisons on the same 116 task instances:

| A | B | A-only successes | B-only successes | exact McNemar p |
|---|---|---|---|---|
| lfm3vl2b_v4 | guiowl15_2b_matched | 6 | 11 | 0.332 |
| lfm3vl2b_v4 | lfm3vl2b_v3 | 10 | 5 | 0.302 |
| lfm3vl2b_v4 | lfm3vl2b_ft | 9 | 6 | 0.607 |
| lfm3vl2b_v3 | lfm3vl2b_ft | 4 | 6 | 0.754 |
| lfm3vl2b_v2 | lfm3vl2b_ft | 0 | 12 | 4.9e-04 |
| lfm3vl2b_ft | guiowl15_2b_matched | 8 | 16 | 0.152 |
| qwen35_2b_ft | lfm3vl2b_ft | 6 | 5 | 1.0 |


Notes from Codex's seed-30 audit ([report](audits/v4_seed30_audit__report.md)):
* the six v4 answer successes are genuine on-screen retrievals; one credited action success (`OpenAppTaskEval`)
  includes an unrequested write that the checker ignores;
* of v4's 4 exceptions, 2 happened during task initialization (eligible for the single pre-registered infrastructure
  re-run) and 2 during scoring (stay failures); v3 and v1 each have one eligible case; none can change the gate;
* the seed-30 GUI-Owl run did **not** get the installed-app list that v4 gets (sealed runs give both models the list);
  GUI-Owl also receives more pixels (672×1504 vs 576×1280) and more text history;
* v4 failure endings (98): 55 budget exhausted, 25 false "complete", 14 wrong answers, 4 exceptions
  (GUI-Owl: 92 / 0 / 1 / 0; v3: 61 / 39 / 0 / 3).

### Development gate (pre-registered, decided before any held-out seed)

v4 gate (from `results/v4_gate_seed30.txt`):

```json
{
 "aw_episodes_v4": 116,
 "aw_answer_task_successes_v4": 6,
 "aw_action_task_successes_v4": 12,
 "aw_action_task_successes_v3": 13,
 "dev_answer_emitted": 0.956,
 "dev_answer_exact": 0.868,
 "dev_answer_typed_same_answer": 0.882,
 "dev_complete_false_answer": 0.0,
 "dev_complete_status": 0.762,
 "gate": {
  "1_answers": true,
  "2_no_false_answers": true,
  "3_aw": true
 },
 "PASS": true
}
```

v4-RL offline promotion (from `results/v4rl_promotion_offline.json`): criteria `a_dev_answer_gate_delta>=+0.05` = False, `b_dev_complete_false_answer<=0.03` = True, `c_ac_high_step_sr_delta>=-0.02` = False → **not promoted**.


## 5. Sealed held-out runs

Pre-registered seeds 7, 1234, 2026 ([PREREG](docs/PREREG_v4.md)). Outcomes stay sealed until every arm on a seed has
finished; only episode-file counts are reported:

| sealed arm | episode files present | of |
|---|---|---|
| guiowl_seed1234 | 58 | 116 |
| guiowl_seed7 | 116 | 116 |
| v1_seed1234 | 116 | 116 |
| v1_seed7 | 116 | 116 |
| v4_seed7 | 116 | 116 |


### Held-out seed 7 (unsealed after all three arms finished)

Preregistered analysis (`scripts/sealed_analysis.py`): full successes over 116 (exception = failure); primary = paired
v4 − GUI-Owl difference, template-clustered sign-flip permutation test with a 95% interval by test inversion,
non-inferiority margin −6.9 points. One seed only, so the result is preliminary by the preregistration's own rule.
Seeds 1234 and 2026 remain sealed.

Status: **PRELIMINARY: before the preregistered single re-runs of 5 infrastructure-crash episodes (4 v4, 1 GUI-Owl), which are queued**.


> Exceptions without a re-run directory yet (check eligibility; preregistered single re-run pending): v4 seed 7: ['MarkorCreateNoteFromClipboard', 'RecipeDeleteMultipleRecipes', 'SimpleSmsSend', 'TasksDueNextWeek']; guiowl seed 7: ['SimpleSmsResend']
> One held-out seed only: PRELIMINARY (preregistered label; detectable gap ~14 tasks).

| Arm | Successes | % | Wilson 95% | Answer tasks | Action tasks | Seed-varying | Easy | Medium | Hard | Exceptions |
|---|---|---|---|---|---|---|---|---|---|---|
| LFM3 v4 (final) (seed 7) | 18/116 | 15.5 | 10.0–23.2 | 6/25 | 12/91 | 10/76 | 17/61 | 0/36 | 1/19 | 4 |
| GUI-Owl-1.5-2B matched (seed 7) | 15/116 | 12.9 | 8.0–20.2 | 7/25 | 8/91 | 13/76 | 9/61 | 5/36 | 1/19 | 1 |
| LFM3 v1 (reference) (seed 7) | 11/116 | 9.5 | 5.4–16.2 | 0/25 | 11/91 | 4/76 | 10/61 | 0/36 | 1/19 | 0 |

| Comparison | Mean difference (pp) | 95% CI (sign-flip inversion) | p (two-sided) | Per seed: only-first / only-second / both, McNemar p |
|---|---|---|---|---|
| v4_minus_guiowl (PRIMARY) | 2.6 | [-6.2, 11.4] | 0.707 | seed 7: 15 / 12 / 3, p=0.7011 |
| v1_minus_guiowl | -3.4 | [-11.5, 4.6] | 0.5216 | seed 7: 9 / 13 / 2, p=0.5235 |
| v4_minus_v1 | 6.0 | [0.0, 12.5] | 0.1171 | seed 7: 11 / 4 / 7, p=0.1185 |

Secondary (official rule, exceptions dropped): seed 7: 111 pairs, v4-only 15, GUI-Owl-only 10, McNemar p=0.4244

Re-runs applied: none

Non-inferiority (lower 95% bound > -6.9 pp): **yes** (lower bound -6.2 pp).


Arms: GUI-Owl-1.5-2B matched (1 screenshot, Q4_K_M, installed-app list), LFM3 v1 (reference), LFM3 v4 (final).
Primary analysis: paired difference LFM3 final − GUI-Owl, template-clustered sign-flip permutation test,
non-inferiority margin 8 tasks per 116.

## 6. MobileWorld (secondary benchmark, in progress)

Status 2026-11-18 21:03; suite: MobileWorld a026188, 105 English GUI-only tasks, max_round 50, step_wait 3 s, auto_retry 3.

| run | host | agent | finished | successes | status |
|---|---|---|---|---|---|
| v4 run 1 (AWS c8i, CPU server) | AWS c8i.4xlarge | LFM3 adapter (first version) | 105/105 | 5 | complete, NOT a fair measure: Codex (results/codex/session_1118_audit C1/C2) found the adapter reversed v4's horizontal scrolls, changed scroll distance and dropped the Enter that v4's type action includes; superseded by run 2 |
| GUI-Owl run 1 (GCP + Colab T4) | GCP n2-standard-16 + Colab T4 | MobileWorld official gui_owl_1_5 | 4/105 | 4 | INVALID: model server OOM-killed at 14:09 (RAM prompt cache); every later task failed with no model reply; discarded, not stitched |
| GUI-Owl run 2 (GCP + Colab T4, --cache-ram 0) | GCP n2-standard-16 + Colab T4 | MobileWorld official gui_owl_1_5 | 39/105 | 16 | in progress |
| v4 run 2 (GCP + Colab T4, fixed adapter) | GCP n2-standard-16 + Colab T4 | LFM3 adapter v2 (AndroidWorld scroll gesture as drag; Enter after typing as an extra step) | 16/105 | 4 | in progress |

Paired so far (tasks both valid runs have finished): 14 tasks, v4 4 vs GUI-Owl 9 successes.

Only complete, valid runs are comparable. Per-task results of finished runs are in the working repo (`results/mobileworld/`).


## 7. MAI-UI-2B on AndroidWorld (extra development arm, in progress)

Converted to Q4_K_M + Q8_0 mmproj exactly like GUI-Owl's files; agent ported from the official MAI-UI repo
(navigation prompt, history format); matched budget: one screenshot at ≤ 1,048,576 px, temperature 0. Runs on
emulator 1 on seed 30; see `scripts/local_maiui_aw.sh` in the working repo. Results will be added when the run finishes.
