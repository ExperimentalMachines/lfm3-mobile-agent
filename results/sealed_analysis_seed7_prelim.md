# Held-out AndroidWorld analysis, seed(s) 7

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
