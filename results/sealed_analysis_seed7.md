# Held-out AndroidWorld analysis, seed(s) 7

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
