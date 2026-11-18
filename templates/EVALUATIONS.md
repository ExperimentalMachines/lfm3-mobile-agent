# Evaluations

## 1. AndroidControl test (offline, 18,415 rows, greedy)

Step SR = predicted action matches the reference action under the project scorer (`eval/androidcontrol/score.py` in the
working repo); episode SR = every step of the episode correct. High-level = goal only; low-level = goal + step instruction.

{{table_ac}}

## 2. Held-out dev splits (offline)

GUI-Odyssey test episodes, 5 % hash-held-out AMEX episodes, ScreenQA validation (v2+); `dev_answer` = 136
navigate-then-answer screens and `dev_complete` = 80 action-only completion controls (v4+, pinned at AndroidAgent-SFT-v4 @ 3375539).
Splits differ between v2/v3 and v4 builds, so compare within a version family only.

{{table_dev}}

## 3. General-capability retention (forced-choice log-prob)

{{table_gen}}

## 4. AndroidWorld, development seed 30 (116 tasks)

Harness for every row: AndroidWorld 55ddaf5 + local fixes, Pixel 6 API 33 arm64 emulator on an Apple M5 Mac, model
served by llama.cpp as Q4_K_M + Q8_0 mmproj, one screenshot per step, temperature 0, step budget 10× task complexity,
success only if the agent ends the episode and the checker passes (exception = failure). Answer tasks = the 25
information-retrieval tasks scored on the agent's answer. Latency = median model time per step during the run.

{{table_aw}}

Paired comparisons on the same 116 task instances:

{{table_pairs}}

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

{{gate}}

## 5. Sealed held-out runs

Pre-registered seeds 7, 1234, 2026 ([PREREG](docs/PREREG_v4.md)). Outcomes stay sealed until every arm on a seed has
finished; only episode-file counts are reported:

{{table_sealed}}

### Held-out seed 7 (unsealed after all three arms finished)

Preregistered analysis (`scripts/sealed_analysis.py`): full successes over 116 (exception = failure); primary = paired
v4 − GUI-Owl difference, template-clustered sign-flip permutation test with a 95% interval by test inversion,
non-inferiority margin −6.9 points. One seed only, so the result is preliminary by the preregistration's own rule.
Seeds 1234 and 2026 remain sealed.

{{sealed_seed7}}

Arms: GUI-Owl-1.5-2B matched (1 screenshot, Q4_K_M, installed-app list), LFM3 v1 (reference), LFM3 v4 (final).
Primary analysis: paired difference LFM3 final − GUI-Owl, template-clustered sign-flip permutation test,
non-inferiority margin 8 tasks per 116.

## 6. MobileWorld (secondary benchmark, in progress)

{{mobileworld}}

## 7. MAI-UI-2B on AndroidWorld (extra development arm, seed 30)

Runs at **Q8_0** (+ Q8_0 mmproj): at Q4_K_M, MAI-UI-2B's output collapsed into empty `<thinking>` loops on AndroidWorld
screens (evidence: `results/maiui_quant_check.md` in the working repo), unlike GUI-Owl, which runs at Q4_K_M. Agent ported from the official MAI-UI repo
(navigation prompt, history format); matched budget: one screenshot at ≤ 1,048,576 px, temperature 0. Runs on
emulator 1 on seed 30; see `scripts/local_maiui_aw.sh` in the working repo. Finished 2026-11-18 23:32: **32/116** full successes (plus one half-scored composite task, TurnOffWifiAndTurnOnBluetooth, not counted), 1 exception; its row and paired comparisons are in section 4. It is the strongest model on the development seed; it is not one of the preregistered held-out arms.
