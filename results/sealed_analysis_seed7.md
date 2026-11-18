# Held-out AndroidWorld analysis, seed(s) 7

> One held-out seed only: PRELIMINARY (preregistered label; detectable gap ~14 tasks).

| Arm | Successes | % | Wilson 95% | Answer tasks | Action tasks | Seed-varying | Easy | Medium | Hard | Exceptions |
|---|---|---|---|---|---|---|---|---|---|---|
| LFM3 v4 (final) (seed 7) | 18/116 | 15.5 | 10.0–23.2 | 6/25 | 12/91 | 10/76 | 17/61 | 0/36 | 1/19 | 0 |
| GUI-Owl-1.5-2B matched (seed 7) | 16/116 | 13.8 | 8.7–21.2 | 7/25 | 9/91 | 14/76 | 9/61 | 6/36 | 1/19 | 0 |
| LFM3 v1 (reference) (seed 7) | 11/116 | 9.5 | 5.4–16.2 | 0/25 | 11/91 | 4/76 | 10/61 | 0/36 | 1/19 | 0 |

| Comparison | Mean difference (pp) | 95% CI (sign-flip inversion) | p (two-sided) | Per seed: only-first / only-second / both, McNemar p |
|---|---|---|---|---|
| v4_minus_guiowl (PRIMARY) | 1.7 | [-7.2, 10.7] | 0.8517 | seed 7: 15 / 13 / 3, p=0.8506 |
| v1_minus_guiowl | -4.3 | [-12.5, 3.7] | 0.4035 | seed 7: 9 / 14 / 2, p=0.4049 |
| v4_minus_v1 | 6.0 | [0.0, 12.5] | 0.1171 | seed 7: 11 / 4 / 7, p=0.1185 |

Secondary (official rule, exceptions dropped): seed 7: 116 pairs, v4-only 15, GUI-Owl-only 13, McNemar p=0.8506

Re-runs applied: v4 s7 RecipeDeleteMultipleRecipes -> fail, v4 s7 SimpleSmsSend -> fail, v4 s7 TasksDueNextWeek -> fail, v4 s7 MarkorCreateNoteFromClipboard -> fail, guiowl s7 SimpleSmsResend -> success

Non-inferiority (lower 95% bound > -6.9 pp): **no** (lower bound -7.2 pp).
