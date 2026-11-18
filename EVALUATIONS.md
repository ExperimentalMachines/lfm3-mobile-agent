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
| MAI-UI-2B (matched: 1 screenshot, Q8_0) | 32 | 5 | 27 | 1 | 11 | 9.35 | maiui_2b_matched1img_q8_0 | results/androidworld/maiui_2b_matched_q8_0/run_20261118T144721333786/ |


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
| lfm3vl2b_v4 | maiui_2b_matched_q8_0 | 6 | 20 | 0.009 |
| maiui_2b_matched_q8_0 | guiowl15_2b_matched | 20 | 11 | 0.15 |


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
| guiowl_seed1234 | 116 | 116 |
| guiowl_seed2026 | 116 | 116 |
| guiowl_seed7 | 116 | 116 |
| guiowl_seed7_rerun | 1 | 116 |
| v1_seed1234 | 116 | 116 |
| v1_seed7 | 116 | 116 |
| v4_seed1234 | 85 | 116 |
| v4_seed2026 | 46 | 116 |
| v4_seed7 | 116 | 116 |
| v4_seed7_rerun | 4 | 116 |


### Held-out seed 7 (unsealed after all three arms finished)

Preregistered analysis (`scripts/sealed_analysis.py`): full successes over 116 (exception = failure); primary = paired
v4 − GUI-Owl difference, template-clustered sign-flip permutation test with a 95% interval by test inversion,
non-inferiority margin −6.9 points. One seed only, so the result is preliminary by the preregistration's own rule.
Seeds 1234 and 2026 remain sealed.

Status: **final (after the preregistered single re-runs of infrastructure crashes)**.


> One held-out seed only: PRELIMINARY (preregistered label; detectable gap ~14 tasks).

| Arm | Successes | % | Wilson 95% | Answer tasks | Action tasks | Goal can vary (78) | Easy | Medium | Hard | Exceptions |
|---|---|---|---|---|---|---|---|---|---|---|
| LFM3 v4 (final) (seed 7) | 18/116 | 15.5 | 10.0–23.2 | 6/25 | 12/91 | 11/78 | 17/61 | 0/36 | 1/19 | 0 |
| GUI-Owl-1.5-2B matched (seed 7) | 16/116 | 13.8 | 8.7–21.2 | 7/25 | 9/91 | 14/78 | 9/61 | 6/36 | 1/19 | 0 |
| LFM3 v1 (reference) (seed 7) | 11/116 | 9.5 | 5.4–16.2 | 0/25 | 11/91 | 5/78 | 10/61 | 0/36 | 1/19 | 0 |

| Comparison | Mean difference (pp) | 95% CI (sign-flip inversion, rounded outward) | p (two-sided) | Per seed: only-first / only-second / both, McNemar p |
|---|---|---|---|---|
| v4_minus_guiowl (PRIMARY) | 1.7 | [-7.3, 10.8] | 0.8517 | seed 7: 15 / 13 / 3, p=0.8506 |
| v1_minus_guiowl | -4.3 | [-12.5, 3.8] | 0.4035 | seed 7: 9 / 14 / 2, p=0.4049 |
| v4_minus_v1 | 6.0 | [0.0, 12.5] | 0.1171 | seed 7: 11 / 4 / 7, p=0.1185 |

Secondary (official rule, exceptions dropped): seed 7: 116 pairs, v4-only 15, GUI-Owl-only 13, McNemar p=0.8506

Re-runs applied: v4 s7 RecipeDeleteMultipleRecipes -> fail, v4 s7 SimpleSmsSend -> fail, v4 s7 TasksDueNextWeek -> fail, v4 s7 MarkorCreateNoteFromClipboard -> fail, guiowl s7 SimpleSmsResend -> success

Non-inferiority (lower 95% bound > -6.9 pp): **no** (lower bound -7.272727 pp).

Sensitivity, disputed checker successes counted as failures (v4 seed 7 ClockStopWatchPausedVerify): v4 17 vs GUI-Owl 16, difference 0.9 pp, 95% CI [-8.1, 9.9], p = 1.0; non-inferior: no.

Known limits:
* The primary score is AndroidWorld's checker verdict (preregistered). Every success is also reviewed against its saved trajectory; disputed successes are listed in results/aw_checker_disputes.json and only enter the sensitivity analysis.
* Harness defect affecting all arms: gRPC fork warnings on adb stderr can corrupt adb query output during task setup (android_env's adb controller merges stderr into stdout). Such setup crashes are exceptions and get the preregistered single re-run; the harness is not changed mid-protocol.
* The 95% CI inverts the sign-flip test (10,000 draws, seed 0); it is a nominal interval that assumes the shifted paired differences are symmetric, not an interval with guaranteed exact coverage.

Goal can vary: 78 templates in results/aw_template_manifest.json (source-checked); observed goal-text changes versus dev seed 30: seed 7: 76.


Arms: GUI-Owl-1.5-2B matched (1 screenshot, Q4_K_M, installed-app list), LFM3 v1 (reference), LFM3 v4 (final).
Primary analysis: paired difference LFM3 final − GUI-Owl, template-clustered sign-flip permutation test,
non-inferiority margin 8 tasks per 116.

## 6. MobileWorld (secondary benchmark, in progress)

Status 2026-11-19 05:06; suite: MobileWorld a026188, 105 English GUI-only tasks, max_round 50, step_wait 3 s, auto_retry 3.

| run | host | agent | finished | successes | status |
|---|---|---|---|---|---|
| v4 run 1 (AWS c8i, CPU server) | AWS c8i.4xlarge | LFM3 adapter (first version) | 105/105 | 5 | complete, NOT a fair measure: Codex (results/codex/session_1118_audit C1/C2) found the adapter reversed v4's horizontal scrolls, changed scroll distance and dropped the Enter that v4's type action includes; superseded by run 2 |
| GUI-Owl run 1 (GCP + Colab T4) | GCP n2-standard-16 + Colab T4 | MobileWorld official gui_owl_1_5 | 4/105 | 4 | INVALID: model server OOM-killed at 14:09 (RAM prompt cache); every later task failed with no model reply; discarded, not stitched |
| GUI-Owl run 2 (GCP + Colab T4, --cache-ram 0) | GCP n2-standard-16 + Colab T4 | MobileWorld official gui_owl_1_5 | 102/105 | 22 | task list finished; ONE fresh-container attempt pending for ThanksgivingPrepTask (setup fails in every container); VM stopped at its 12-h limit and the gcloud login expired, so it waits for re-login |
| v4 run 2 (GCP + Colab T4, fixed adapter) | GCP n2-standard-16 + Colab T4 | LFM3 adapter v2 (AndroidWorld scroll gesture as drag; Enter after typing as an extra step; known limits: a text action on step 50 loses its Enter, empty text gets an HTTP 500 no-op; Codex round2_audit M1/M2) | 104/105 | 6 | complete (ThanksgivingPrepTask: setup failed in every attempt, counted as failure) |

Paired so far (tasks both valid runs have finished): 105 tasks, v4 6 vs GUI-Owl 22 successes.

Only complete, valid runs are comparable. Per-task results of finished runs are in the working repo (`results/mobileworld/`).

### MobileWorld run 2: v4 vs GUI-Owl-1.5-2B (105 English GUI-only tasks) (PROVISIONAL: GUI-Owl-1.5-2B pending ThanksgivingPrepTask)

| Model | Successes / 105 | Tasks with a result | No result (counted as failure) | Folder-level setup/scoring failures (tasks) | Device-health re-initialisations (tasks) | Task executions |
|---|---|---|---|---|---|---|
| LFM3-VL-2B-AndroidAgent-v4 | **6** (5.7%) | 104 | 1: ThanksgivingPrepTask (setup_failed) | 8 (1) | 2 (2) | 114 |
| GUI-Owl-1.5-2B | **22** (21.0%) | 102 | 3: SendInterviewEmailTask (ask_user_without_simulator), CheckInvoiceTask2 (unsupported_action), ThanksgivingPrepTask (setup_failed) | 12 (8) | 15 (14) | 144 |

Paired on the same 105 tasks: both solved 6, v4 only 0, GUI-Owl only 16, neither 83; difference -15.2 pp, exact McNemar p = 3.05e-05 (conditional on these task pairs; one run per model).

Sensitivity (environment): excluding the 8 tasks with a folder-level setup/scoring failure in either run, v4 6 vs GUI-Owl 22 of 97; also excluding tasks with a device-health re-initialisation (18 tasks), v4 5 vs GUI-Owl 21 of 87. Excluding known errors cannot show that the remaining tasks were unaffected; GUI-Owl's container had more environment failures than v4's.

Retries and harness events (no score was changed by them):

* LFM3-VL-2B-AndroidAgent-v4: earlier folders ended setup_failed 7; successes after an earlier failed folder: none; successes after a device-health re-initialisation: none.
* GUI-Owl-1.5-2B: earlier folders ended setup_failed 8, ask_user_without_simulator 6, unsupported_action 5, scoring_failed 3, invalid_model_output 2; successes after an earlier failed folder: none; successes after a device-health re-initialisation: SendWaiverTask.
* GUI-Owl's official agent returns an `error_env` sentinel after 5 unparseable outputs, which MobileWorld's own action validator rejects (an upstream bug), so instead of ending and being scored the task was re-executed (2 executions); those tasks still scored 0.
* `ask_user` needs an LLM-backed user simulator this setup does not have: 7 GUI-Owl executions hit it (v4 has no such action). `double_tap` was rejected by GUI-Owl's official action adapter (not by the runtime).
* v4's adapter completes v4's trained type-then-Enter action with a synthetic Enter on the next environment step (138 synthetic Enters; they count toward the 50-round budget, so v4 made fewer than 50 decisions in 37 of the 85 tasks that reached the budget). When typing was the 50th round the Enter was never sent: MastodonAdjustTootsTask, MastodonUpdateContactsTask, MattermostIncidentEscalationTask (all scored 0; not evidence they would have passed).
* ThanksgivingPrepTask's initialisation failed on every attempt in both containers (and on AWS in v4 run 1): a persistent task-specific initialisation failure; whether from task code or a shared dependency is not identified.

| Setting | v4 | GUI-Owl (official agent) |
|---|---|---|
| Image history | current screenshot | current screenshot (`history_n` 1) |
| Text history | last 8 intent/action pairs | all previous step conclusions |
| Image budget | client resize to at most 880x880 pixels of area, server cap 1,024 tokens | full screenshot, server cap 2,600 tokens |
| Output cap / parse attempts | 512 tokens / up to 2 | 2,048 tokens / up to 5 |
| Quantisation | Q4_K_M | Q4_K_M |
| Step budget | 50 environment rounds incl. synthetic Enters | 50 environment rounds |

MobileWorld's own `--auto_retry 3` (same flag in every run) re-runs a task whose execution ended without a result, whatever the reason; mw_resume.sh then applied the pre-declared completion rule (docs/PREREG_v4.md 2026-11-19 01:55, clarified 05:45: the fresh-container allowance is one more invocation, inside which `--auto_retry 3` allows up to 4 executions, equally for every model). Single run per model at temperature 0; a secondary, descriptive benchmark comparing agent pipelines, not model weights alone. Independent recomputation: results/codex/mw_r2_audit/ (VALID WITH CAVEATS).


## 7. MAI-UI-2B on AndroidWorld (extra development arm, seed 30)

Runs at **Q8_0** (+ Q8_0 mmproj): at Q4_K_M, MAI-UI-2B's output collapsed into empty `<thinking>` loops on AndroidWorld
screens (evidence: `results/maiui_quant_check.md` in the working repo), unlike GUI-Owl, which runs at Q4_K_M. Agent ported from the official MAI-UI repo
(navigation prompt, history format); matched budget: one screenshot at ≤ 1,048,576 px, temperature 0. Runs on
emulator 1 on seed 30; see `scripts/local_maiui_aw.sh` in the working repo. Finished 2026-11-18 23:32: **32/116** full successes (plus one half-scored composite task, TurnOffWifiAndTurnOnBluetooth, not counted), 1 exception; its row and paired comparisons are in section 4. It is the strongest model on the development seed; it is not one of the preregistered held-out arms.
