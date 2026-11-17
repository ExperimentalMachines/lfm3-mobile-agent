# Fair and correct evaluation of Android GUI agents on AndroidWorld (LFM3-VL-2B vs GUI-Owl-1.5-2B)

Scope: what a fair claim of "matches or beats GUI-Owl-1.5-2B" requires on AndroidWorld (AW): protocol details, run/seed variance, statistical power (computed here), harness parity, contamination, and reporting practice. Research date 2026-11-18. Local project numbers come from `/Users/alpha/lfm3-android/results/androidworld/*.summary.json`. Computation scripts are in `/private/tmp/claude-501/-Users-alpha-lfm3-android/4efa3977-532d-411f-ad28-f4737438aa00/scratchpad/power/` (`power.py`, `cluster_sim.py`, `equiv.py`). That scratchpad may be wiped, so the method and the outputs are also restated below.

## Q1. AndroidWorld protocol: instances, seeds, step budgets, pass@k, exceptions/NaN, emulator, flaky tasks, versions

### Takeaway
The official protocol is 116 templates × `n_task_combinations=1` at `task_random_seed=30`, run once (pass@1). The step budget is `int(10 × complexity)`, where complexity was re-based in Nov 2024 to about 2× human steps. The emulator is a Pixel 6 AVD on API 33. An episode scores as a success only if the checker passes **and** the agent itself signalled done. Note that the official code drops episodes that raised exceptions from the denominator (their score is NaN), so it does not count them as failures. The checkers and step budgets have changed several times since the paper, and the public leaderboard was archived in Nov 2026 as saturated. Pin the AW commit, and say explicitly how exceptions are scored.

### Cited Findings
- **Task suite.** 116 hand-crafted tasks across 20 apps. Parameters are drawn at random, so millions of variations exist. Footprint is 2 GB RAM and 8 GB disk. — [AW README](https://github.com/google-research/android_world)
- **Difficulty mix.** `task_metadata.json` currently has 116 entries: 61 easy, 36 medium, 19 hard. Each entry carries an `optimal_steps` field. — [task_metadata.json](https://github.com/google-research/android_world/blob/main/android_world/task_metadata.json)
- **Emulator.** Hardware **Pixel 6**, system image **Tiramisu, API 33**, AVD name `AndroidWorldAvd`. Launch from the command line with `-no-snapshot -grpc 8554`. — [AW README](https://github.com/google-research/android_world)
- **Fixed device state.** The paper fixes the OS to a Pixel 6 emulator on Android 13 and resets the device clock to **Oct 15 2023, 15:34 UTC** before every task. Open-source apps are installed at fixed F-Droid versions. — [AW paper §3.3](https://arxiv.org/html/2405.14573)
- **API level is no longer enforced.** A commit on 2024-11-27 is titled "Remove API level check from AndroidWorld", so the code no longer refuses to run on other API levels. — [AW commit history](https://github.com/google-research/android_world/commits/main/)
- **Device and OS sensitivity.** On a Pixel 5 running Android 12, M3A scored 28.4%. The authors describe the variation as "akin to those from random seed changes". — [AW paper §5](https://arxiv.org/html/2405.14573)
- **Default flags.** `task_random_seed` defaults to **30** and `n_task_combinations` to **1**. With `fixed_task_seed` set, every combination reuses the same parameters. — [run.py](https://github.com/google-research/android_world/blob/main/run.py)
- **Instance seeding.** Each instance seed is `sha256(f"{seed}_{task_name}_{i}") mod 2^32`. Parameters therefore depend only on (seed, task name, index), not on run order or which emulator executes the task. — [suite_utils.py `create_suite`](https://github.com/google-research/android_world/blob/main/android_world/suite_utils.py)
- **Step budget.** `max_n_steps = _allocate_step_budget(task.complexity)`, which returns `int(10 * task_complexity)`. — [suite_utils.py](https://github.com/google-research/android_world/blob/main/android_world/suite_utils.py)
- **Budget update (README).** "As of 11/18/2024, the max_steps/step_budget for each task … updated to approximately 2x the human average completion time." The README links a per-task spreadsheet of the changes. — [AW README](https://github.com/google-research/android_world)
- **Success requires a done signal.** The score is `agent_successful = task_successful if interaction_results.done else 0.0`. Hitting the step limit without the agent declaring done scores 0 even if the device state is correct. — [suite_utils.py `_run_task`](https://github.com/google-research/android_world/blob/main/android_world/suite_utils.py); [episode_runner.py](https://github.com/google-research/android_world/blob/main/android_world/episode_runner.py)
- **Exceptions are dropped from the official score.**
  - Any exception during initialize/run/is_successful produces `_create_failed_result` with `IS_SUCCESSFUL = np.nan`, plus the exception text.
  - The running tally skips these episodes ("Don't include episode in tally if execution/eval logic errored out").
  - `process_episodes` averages `is_successful` per template, then across templates, using pandas mean, which skips NaN.
  - Net effect: the official summary is success over *completed* episodes, and a template that only errored becomes NaN rather than 0.
  - [suite_utils.py](https://github.com/google-research/android_world/blob/main/android_world/suite_utils.py)
- **Macro-average with multiple instances.** `process_episodes` groups by template and averages templates. With `n_task_combinations > 1` the headline number is therefore a template-macro average. — [suite_utils.py](https://github.com/google-research/android_world/blob/main/android_world/suite_utils.py)
- **Leaderboard conventions.**
  - Columns: Screen Representation (Screenshot / A11y tree / both), **Success Rate (pass@1)**, **Number of trials**, **Success Rate (pass@k)**, trajectory submissions.
  - The sheet now reads: "Leaderboard Archived (Nov 2026): With multiple submissions reaching 100%, AndroidWorld is now considered saturated … Scores are self-reported and unverified."
  - Some entries report pass@k separately, e.g. Midscene "pass@2 95.69, pass@3 97.41" and Surfer 2 "pass@3 93.1".
  - [AW leaderboard](https://docs.google.com/spreadsheets/d/1cchzP9dlTZ3WXQTfYNhh3avxoLipqHN75v1Tb86uhHo)
- **Leaderboard trajectory problems.** One entry's note: "Some trajectories (e.g., MarkorCreateNoteFromClipboard, BrowserMaze) are labeled as successful by the authors but contain incorrect actions"; the labeling issue was later corrected. — [AW leaderboard, mobile-use row](https://docs.google.com/spreadsheets/d/1cchzP9dlTZ3WXQTfYNhh3avxoLipqHN75v1Tb86uhHo)
- **Checker and budget changes since the paper.** Commit titles:
  - 2024-11-19: "Bug fix for audio recorder task eval"; "Increase max steps to roughly 2x the optimal steps".
  - 2025-01-07: "Relax the checking of stop watch to handle alternate screen representation".
  - 2025-03-02: "Fix sms task", "Fix RetroPlaylistDuration Task", "Fix integer error".
  - 2025-03-21: "Add more step counts for tasks adding multiple expenses and recipes".
  - 2025-05-21: "Increase the complexity of SimpleCalendarAddOneEventInTwoWeeks and FilesDeleteFile".
  - 2026-02-03: "Add Markor dependency for multi-app tasks".
  - Oct 2026: fuzzywuzzy replaced with thefuzz.
  - [AW commits](https://github.com/google-research/android_world/commits/main/); [README file list](https://github.com/google-research/android_world)
- **Bugs found during construction.** Human annotation surfaced and fixed "over 30 bugs". Two software engineers had one attempt per task, and human success is 80%. — [AW paper App. D.4](https://arxiv.org/html/2405.14573)
- **38 templates ignore the seed.** "We exclude 38 templates that consistently produce identical task instances regardless of seed, leaving 78 templates." — [AndroidWorld-Generalization, App. C](https://arxiv.org/abs/2603.07432)
- **Saturation.** "Recent agents achieving over 90% success rates indicate its saturation." — [MobileWorld](https://arxiv.org/abs/2512.19432). Minitap reports 100% on all 116 tasks using the "official AndroidWorld evaluation protocol without modification". — [Minitap](https://arxiv.org/abs/2602.07787)
- **pass@k on a fixed instance rewards memorization.**
  - A replay script that never observes the screen can beat frontier models on static benchmarks.
  - "Its expected success rate is exactly equal to the source agent's pass@k in deterministic environments."
  - pass@k is "fundamentally inappropriate for stateful UI interactions".
  - [Computer Use at the Edge of the Statistical Precipice](https://arxiv.org/abs/2605.08261)

### Inferences
- **Your "exceptions count as failures" rule is stricter than the official code.** Always also report the official "over completed" number so readers can line it up with papers.
  - LFM3 v1 had 2 exception episodes, so 15/116 = 12.9% under your rule versus 15/114 = 13.2% officially.
  - LFM3 v2 had 5, so 3/116 versus 3/111.
  - Source for exception counts: `n_exceptions_counted_as_fail` in the local summaries.
- **Re-run infrastructure crashes under a rule written before the run**, e.g. "re-run any exception episode once with the same seed; if it fails again, count it as a failure". Apply it identically to every model.
- **Score with the done-flag rule for every model.** Your matched-harness GUI-Owl run self-terminated in only 20.7% of episodes, versus 51.7% for LFM3 v1 and 58.6% for Qwen3.5-2B (`frac_episodes_self_terminated` in the local summaries). If GUI-Owl's `answer`/`terminate` outputs are not mapped to done, GUI-Owl is mechanically capped by the done-flag rule.
- **Cross-paper comparisons are only approximate.** Budgets and checkers changed in 2024-11, 2025-03 and 2025-05, so numbers depend on the repo snapshot. For your own comparisons, record the AW commit hash, the AVD image (ABI, API level, build), the app APK hashes and the emulator flags, and run every model on the same snapshot.
- **Extra seeds help less than they appear to.** Only 78 of 116 templates change with the seed (per AndroidWorld-Generalization), so a held-out seed only partly hides the test set. The 38 fixed templates are the same instances you already iterated on.
- **pass@1 on one run is the convention.** The leaderboard and most papers report it. Report pass@k only as a secondary envelope, never as the headline, and never compare your pass@k to someone else's pass@1.

### Gaps
- No public, maintained list of flaky AW tasks or broken checkers turned up. The GitHub issues page lists titles such as "Error when get the reward" and "Issues with Evaluation in Verification Tasks", but I did not audit them.
- I could not open the per-task step-budget spreadsheet linked from the README.
- I found no evidence on whether arm64 emulator images (as on Apple Silicon Macs) score differently from the x86_64 images most papers use. Treat the ABI as an uncontrolled factor and keep it constant across models.

## Q2. Run-to-run and seed variance on AndroidWorld; how many runs/seeds are standard

### Takeaway
Single-run AW scores move by roughly 2–4 pp (about 2.5–4.5 tasks) between seeds or runs, and individual tasks swing far more. The norm is still one run at seed 30. A minority of papers report 3 seeds (mean ± std), 3 trials, 8 trials (pass@1/2/4/8), or a 64-run average. With 116 tasks, a 3–5 task gap between two single runs is inside the noise.

### Cited Findings
- **AW paper, three seeds.** M3A with GPT-4 Turbo scored "27.6%, 26.3% and 33.2% (mean 29.0%)". The authors keep the single-seed result for consistency with the literature and say "performance is best represented by the mean across seeds". — [AW paper §5](https://arxiv.org/html/2405.14573)
- **AW paper, repeated trials.** 20 trials per task on 5 tasks. "Performance varies even with a fixed seed, suggesting model non-determinism affects reliability. Performance varies significantly more with different seeds." The paper uses Wilson 95% CIs. — [AW paper §5, Fig. 3](https://arxiv.org/html/2405.14573)
- **Seeds can change task difficulty.** In ExpenseAddSingle the seed picks the category; categories hidden behind horizontal scrolling make the agent fail "consistently". — [AW paper App. E.5](https://arxiv.org/html/2405.14573)
- **AndroidWorld-Generalization.**
  - Reports "mean and standard deviation over three evaluation seeds — seed 30 (the AndroidWorld default) and seeds 7 and 1234".
  - UI-TARS-7B-SFT: 23.0 ± 2.2. Their RL 7B: 49.1 ± 8.2.
  - Per-difficulty SDs reach ±13.2 on hard tasks.
  - [AndroidWorld-Generalization](https://arxiv.org/abs/2603.07432)
- **MobileRL.** "We run eight test trials at temperature 1.0 and report pass@1/2/4/8." — [MobileRL](https://arxiv.org/abs/2509.18119)
- **UI-Voyager.** "We report the average success rate of UI-Voyager over 64 independent runs with randomized task parameters, whereas baseline results are taken from prior papers." — [UI-Voyager](https://arxiv.org/abs/2603.24533)
- **Coati.** Reports 86.5% "over three trials" with a fixed backbone. — [Coati](https://arxiv.org/abs/2611.02644)
- **Leaderboard.** Nearly every row lists "Number of trials = 1". — [AW leaderboard](https://docs.google.com/spreadsheets/d/1cchzP9dlTZ3WXQTfYNhh3avxoLipqHN75v1Tb86uhHo)
- **SWE-bench evidence (agentic, not GUI).** Single-run pass@1 "vary by 2.2 to 6.0 percentage points depending on which run is selected, with standard deviations exceeding 1.5 percentage points even at temperature 0". Trajectories diverge early. — [On Randomness in Agentic Evals](https://arxiv.org/abs/2602.07150)
- **Single runs can get the sign wrong.** A computer-use RL study: "a single-run improvement of the size this field publishes would have the wrong sign roughly one-third of the time in a comparable regime". The run-to-run distribution can be bimodal, so mean ± std is the wrong summary. — [Teach it to stop, not just to click](https://arxiv.org/abs/2607.17136)

### Inferences
- **Calibration numbers (computed in `power.py`).**
  - The AW paper's three seeds give SD 3.7 pp and range 6.9 pp (≈ 8 tasks).
  - AndroidWorld-Generalization gives SD 2.2 pp for a 7B SFT model.
  - Binomial sampling SD of a single 116-task score at p = 0.20 is 3.7 pp (4.3 tasks), which is a different quantity: task sampling, not run noise.
  - Working assumption: run/seed noise σ ≈ 2–4 pp.
- **Measure your own run-to-run noise.** You have no repeated runs of an identical config yet, so you cannot separate model differences from run noise. Re-run one config (e.g. LFM3 v1) unchanged at seed 30 and measure the paired discordance. That is the d parameter in Q3.
- **Known asymmetry in your comparison.** GUI-Owl's official harness uses temperature 0. If LFM3 samples at temperature > 0, its noise is larger; report the decoding settings for each model.

### Gaps
- I found no paper that runs a 2B screenshot-only agent on AW repeatedly with identical config and reports the run-to-run SD. All AW variance figures above come from larger models or seed variation.

## Q3. Statistical power: what n = 116 paired can detect; seeds needed for +5 / +8 tasks

### Takeaway
At the discordance you actually observe (GUI-Owl vs LFM3 v1: d ≈ 0.21), one 116-instance run detects a gap only if it is about **+14 tasks or more** (80% power, α = 0.05).
- **+8 tasks:** about 348 paired instances (3 seeds' worth, *if* independent).
- **+5 tasks:** about 884 paired instances (7–8 seeds' worth).
- **"Matches GUI-Owl within ±5 tasks"** (equivalence): about 950 paired instances.

Pooling multiple seeds into one McNemar test inflates false positives when templates differ. Test at the template level instead.

### Cited Findings
- **Observed discordance in your runs** (computed from per-episode files under `/Users/alpha/lfm3-android/results/androidworld/`):

  | Comparison | Discordant pairs | d | Exact McNemar p |
  |---|---|---|---|
  | GUI-Owl (matched harness, 23) vs LFM3 v1 (15) | 16 Owl-only, 8 v1-only | 0.207 | 0.152 |
  | GUI-Owl vs Qwen3.5-2B (16) | 15 vs 8 | 0.198 | 0.210 |
  | LFM3 v1 vs Qwen3.5-2B | 5 vs 6 | 0.095 | — |
  | LFM3 v1 vs v2 | 12 vs 0 | 0.103 | 0.0005 |
  | LFM3 v1 vs v1-runtime-feedback | 6 vs 1 | 0.060 | — |

- **Per-difficulty breakdown** (easy/61, medium/36, hard/19). Nearly all successes are on easy tasks, and the GUI-Owl gap sits mostly in medium/hard. — local summaries above

  | Model | Easy | Medium | Hard |
  |---|---|---|---|
  | GUI-Owl matched | 17 | 4 | 2 |
  | LFM3 v1 | 14 | 0 | 1 |
  | Qwen3.5-2B | 14 | 2 | 0 |

- **Power-analysis recipe.** One paper recommends power analysis to choose the number of runs, using n ≥ 2((z_{α/2}+z_β)/(Δ/σ))². Its SWE-bench example: detecting a 2 pp gain needs ~9 runs at σ = 1.5 pp. — [On Randomness in Agentic Evals, App. A](https://arxiv.org/abs/2602.07150)
- **Intervals and bootstrap.**
  - Wilson intervals keep near-nominal coverage even with 1–3 rollouts, whereas Wald covers only 25% at R = 3.
  - A bootstrap that resamples only rollouts reached 17% suite-level coverage; adding configuration resampling gave 56%; full hierarchical resampling (scenario → configuration → rollout) gave 95%.
  - [Computer Use at the Edge of the Statistical Precipice](https://arxiv.org/abs/2605.08261)

### Computations (method shown)
- **Wilson 95% CIs at n = 116** (`power.py`). They overlap heavily, so these unpaired intervals alone cannot rank the models.

  | Model | Score | Wilson 95% CI |
  |---|---|---|
  | LFM3 v1 | 15/116 = 12.9% | [8.0, 20.2] |
  | LFM3 v2 | 3/116 = 2.6% | [0.9, 7.3] |
  | v2+force_think | 6/116 = 5.2% | [2.4, 10.8] |
  | Qwen3.5-2B | 16/116 = 13.8% | [8.7, 21.2] |
  | GUI-Owl-1.5-2B, your harness | 23/116 = 19.8% | [13.6, 28.0] |

- **Paired difference CIs** (`equiv.py`).
  - LFM3 v1 − GUI-Owl = −6.9 pp. Newcombe paired 95% CI [−15.4, +1.6] pp (≈ [−17.9, +1.8] tasks). Paired bootstrap gives [−15.5, +0.9].
  - Qwen3.5-2B − GUI-Owl = −6.0 pp, CI [−14.4, +2.3].
  - Conclusion: you cannot yet claim GUI-Owl is better than LFM3 v1, and you also cannot claim the two are equivalent.
- **How overlap changes significance** for the same 23-vs-15 totals:
  - If all of LFM3's wins were also GUI-Owl wins (8 vs 0 discordant), p = 0.008.
  - With 16 vs 8 (observed), p = 0.15.
  - With 23 vs 15, p = 0.26.
  - Always report the discordant counts, not just the totals.
- **Power model.**
  - Exact conditional McNemar (two-sided binomial test on discordant pairs), α = 0.05.
  - Parameterized by Δ = p10 − p01 (true advantage) and d = p10 + p01 (discordance).
  - Power = Σ_D Bin(D; n, d) · P(reject | D), with K | D ~ Bin(D, p10/d), counting only rejections in the true direction.
  - Under independence at p ≈ 0.2, d ≈ 0.33–0.36. Your observed cross-family d is about 0.20, and within-family about 0.06–0.10.
- **Power for +5 tasks (Δ = 4.3 pp):**

  | d | n=116 | n=232 | n=348 | n=464 | n=580 | n=696 | n=928 |
  |---|---|---|---|---|---|---|---|
  | 0.10 | .21 | .47 | .67 | .82 | .90 | .95 | .99 |
  | 0.20 | .13 | .27 | .39 | .51 | .61 | .70 | .82 |
  | 0.30 | .10 | .19 | .28 | .37 | .45 | .52 | .65 |

- **Power for +8 tasks (Δ = 6.9 pp):**

  | d | n=116 | n=232 | n=348 | n=464 | n=580 | n=696 | n=928 |
  |---|---|---|---|---|---|---|---|
  | 0.10 | .58 | .92 | .99 | 1.0 | 1.0 | 1.0 | 1.0 |
  | 0.20 | .30 | .61 | .80 | .90 | .96 | .98 | 1.0 |
  | 0.30 | .22 | .44 | .62 | .75 | .85 | .91 | .97 |

- **Paired instances needed for 80% power:**

  | d | +5 tasks | +8 tasks |
  |---|---|---|
  | 0.10 | 448 (3.9 × 116) | 172 |
  | 0.20 | **884 (7.6 × 116)** | **348 (3.0 × 116)** |
  | 0.30 | 1308 | 520 |
  | 0.36 | 1564 | 620 |

  The normal approximation (Connor 1987, n = [z_α√d + z_β√(d−Δ²)]²/Δ²) agrees: 843 and 328 at d = 0.20.
- **Smallest gap detectable with 80% power at n = 116:** d = 0.10 → +10 tasks; 0.15 → +12; **0.20 → +14 (12.1 pp)**; 0.30 → +18; 0.36 → +19.
- **Equivalence ("matches").**
  - At n = 116 and d = 0.207, the 95% CI half-width for the paired difference is ±8.2 pp (≈ ±9.5 tasks).
  - Margin ±5 tasks: n ≈ 428 for CI half-width ≤ margin; n ≈ 954 for TOST with 80% power when the true difference is 0.
  - Margin ±8 tasks: 167 and 373 respectively.
- **Clustering when you add seeds** (`cluster_sim.py`, 800 reps per cell; my own assumption-dependent simulation).
  - Model: logistic, template base logits N(−2.2, 2); template-specific model advantage e_t ~ N(0, sd_e); instance (seed) effect N(0, 1) shared by both models; Bernoulli rollouts; true mean effect 0.
  - With sd_e = 1, pooling m = 5 seeds into one McNemar gives Type I error 0.074. With sd_e = 2 it gives 0.077 (m = 3) and 0.136 (m = 5).
  - A template-level sign-flip permutation test on per-template mean differences stays at 0.04–0.064.
  - With m = 1 both tests are conservative (≈0.025).
- **Selection bias from picking the best variant on the test set** (E[max of k iid N(0,1)] × σ). Even with no true differences, best-of-k inflates the score:

  | k variants | σ = 2.2 pp | σ = 3.6 pp |
  |---|---|---|
  | 3 | +1.9 pp (2.2 tasks) | +3.1 pp (3.5 tasks) |
  | 5 | +2.6 pp (3.0 tasks) | +4.2 pp (4.9 tasks) |
  | 10 | +3.4 pp (3.9 tasks) | +5.5 pp (6.4 tasks) |

  These are upper-ish bounds, because variants scored on the same instances share instance noise.

### Inferences
- **Adding seeds.** Seeds 30 + two more (n = 348) gives roughly 80% power for +8 tasks at d ≈ 0.20. But 38 of 116 templates are seed-invariant (Q1), so extra seeds add only 78 new instances each; the 38 fixed ones are repeats that capture run noise only.
- **Primary test across seeds.** Make it template-clustered: paired sign-flip/permutation on per-template differences, or a cluster bootstrap over templates (the hierarchical bootstrap of the Statistical Precipice paper, with templates as scenarios and seeds as configurations). Report pooled McNemar only as secondary.
- **Detecting +5 tasks** needs about 8 seeds (~900 paired instances), which is likely outside your Modal/local budget. Pre-commit to the effect size you can afford to detect (e.g. +8 tasks over 3 seeds) and write a weaker claim if the margin is smaller.
- **Phrasing an equivalence claim at your sample size.** "Matches GUI-Owl" at n = 116 can honestly read only as "the 95% CI of the paired difference is [x, y]", which today spans about ±8 pp. A true non-inferiority claim needs a stated margin and roughly 400–950 paired instances.

### Gaps
- d for a future LFM3 version vs GUI-Owl is unknown. The 0.207 measured against v1 is a proxy.
- The simulation's variance components are assumed, not fitted. Fit them from a 3-seed pilot before finalizing the seed count.

## Q4. Harness parity: how to compare against GUI-Owl-1.5-2B, and GUI-Owl's official AW setup

### Takeaway
GUI-Owl-1.5-2B reports 67.9% on AW in its own harness; it scores 19.8% (23/116) in yours. A 48 pp gap like this is far larger than any model difference you are trying to measure, so harness choice dominates the comparison. A fair claim needs GUI-Owl run in its native harness (the reference ceiling) **and** in your matched screenshot-only harness, with LFM3 in the same matched harness, all on the same AW commit, AVD and seed. Any cross-harness number must be disclosed as such.

### Cited Findings
- **Self-reported AW scores.** GUI-Owl-1.5-2B-Instruct: AndroidWorld **67.9**, Mobile-World 31.3, OSWorld-Verified 43.5. 4B: 69.8. 8B-Thinking: 71.6. — [HF model card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct); [Mobile-Agent-v3.5 README](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/README.md)
- **Official AW evaluation instructions.** Install AW per the official repo, fill vLLM info into `run_guiowl15.sh` or `run_ma35.sh`, and run. — [Mobile-Agent-v3.5 README](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/README.md)
  - The same README's TODO still lists "[ ] Open source evaluation code on benchmarks" as unchecked.
  - `run_guiowl15.sh` invokes `python run_ma3.py`, but the `android_world_v3.5/` directory contains only `run_ma35.py`.
  - [run_guiowl15.sh](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/run_guiowl15.sh); repo tree via GitHub API
- **Native agent details** (`gui_owl.py` in the v3.5 AW fork). [gui_owl.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py)
  - Multi-turn chat. The system prompt defines a `mobile_use` function-call tool with actions key, click, long_press, swipe, type, system_button, open, wait, answer and terminate.
  - Each user turn reads: "Please generate the next move according to the UI screenshot, instruction and previous actions. Instruction: … Previous actions: StepN: <conclusion>".
  - **`last_image=5`**: the most recent 5 screenshots are kept as image turns with their full assistant responses; older turns are reduced to text action summaries.
  - An `answer` action is followed automatically by `terminate(success)`.
- **Run configuration.** — [run_ma35.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/run_ma35.py); [infer_ma3.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/infer_ma3.py)
  - Agent built as `gui_owl.GUIOwl(..., "qwen-vl", ...)`.
  - `task_random_seed` default 30, `n_task_combinations` flag kept.
  - Model wrapper uses `temperature = 0.0` and retries API errors up to 10 times.
- **Recommended serving.** vLLM with `--limit-mm-per-prompt image=5`, `--max-model-len 32768`, and a pixel range of 65,536–3,072,000. The model outputs relative (0–1000) coordinates by default. — [HF model card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct); [README](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/README.md)
- **Step budget in the fork** is unchanged: `int(10 * task_complexity)`.
- **Checkers in the fork match upstream.** My diff of all 57 `task_evals/*.py` files between the fork and current upstream main, ignoring license and type-checker comments, found only one substantive difference: upstream adds `app_names = (_APP_NAME, 'markor')` to two multi-app tasks in `expense.py` and `recipe.py`. Checkers and complexities are otherwise identical. — [upstream task_evals](https://github.com/google-research/android_world/tree/main/android_world/task_evals); [fork task_evals](https://github.com/X-PLUG/MobileAgent/tree/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/task_evals)
- **GUI-Owl v1 history window.** Mobile-Agent-v3 says GUI-Owl "typically retain[s] only the most recent 1 to 3 images" and stores only the model's "conclusion" in history. GUI-Owl-7B scored 66.4 on AW; inside the Mobile-Agent-v3 framework, 73.3. — [Mobile-Agent-v3 §2.1, Table 7](https://arxiv.org/abs/2508.15144)
- **Cross-framework scores collapse.**
  - Mobile-Agent-v3 also ran models inside a third-party framework (Mobile-Agent-E on AW): GUI-Owl-7B 59.5, GUI-Owl-32B 62.1, UI-TARS-1.5 14.1, UI-TARS-72B 14.8, Qwen2.5-VL-72B 52.6. — [Mobile-Agent-v3 Table 8](https://arxiv.org/abs/2508.15144)
  - UI-TARS-72B is listed at 46.6 on the AW leaderboard. — [AW leaderboard](https://docs.google.com/spreadsheets/d/1cchzP9dlTZ3WXQTfYNhh3avxoLipqHN75v1Tb86uhHo)
  - That is a ~32 pp drop for the same model in a different framework.
- **GUI-Owl in an independent benchmark harness.** MobileWorld ran GUI-Owl-7B and GUI-Owl-32B: 7.7 and 8.5 on GUI-only tasks (116), 4.5 and 5.5 overall. — [MobileWorld Table 6](https://arxiv.org/abs/2512.19432). GUI-Owl-1.5's self-reported MobileWorld scores are 31.3 (2B) to 46.8 (32B); same organization (Tongyi Lab). — [HF card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct)
- **Harness can matter more than the model.** "Harness-induced variance can substantially exceed model-induced variance, including cases of model ranking reversal." — [Stop Comparing LLM Agents Without Disclosing the Harness](https://arxiv.org/abs/2605.23950)
- **Coding agents (Terminal-Bench subset).** "Model-to-model comparison is valid when the harness is fixed"; harness choice changed tokens per solved task by up to 40×. — [The Scaffold Effect](https://arxiv.org/abs/2607.22585)
- **HAL.** Provides "a standardized evaluation harness … eliminating common implementation bugs" and runs a three-way analysis over models, scaffolds and benchmarks. — [HAL](https://arxiv.org/abs/2510.11977)
- **AI Agents That Matter.** "Agent evaluations lack standardization and reproducibility … These errors inflate accuracy estimates." — [AI Agents That Matter](https://arxiv.org/abs/2407.01502)
- **Your own runs.** The native-harness smoke test passed 2/2 easy tasks (`guiowl15_2b_native_sample.summary.json`). The full matched run reached 23/116 with only 20.7% of episodes self-terminated and 19.2 mean steps (`guiowl15_2b_matched.summary.json`).

### Inferences
- **Run three arms on one pinned AW commit, AVD and seed set:**
  - (a) GUI-Owl-1.5-2B in its native harness: 5-image multi-turn history, its prompt, its action parser, temperature 0, upstream step budgets. This reproduces (or fails to reproduce) the 67.9.
  - (b) GUI-Owl-1.5-2B in your matched one-screenshot harness.
  - (c) LFM3 in the same matched harness.
  - Fairness claim: compare (c) vs (b) with the same harness and history budget. Capability claim: compare (c) vs (a) as an absolute bar.
  - If you also give LFM3 its best native-style harness, label it a "system vs system" comparison.
- **Settle whether 23/116 is a harness artifact before using it as the target.** The gap from 67.9 is huge, and GUI-Owl rarely self-terminates in your harness. Check:
  - `answer` → `terminate` handling;
  - coordinate convention (relative 0–1000 vs absolute);
  - image resizing (Qwen smart-resize, pixel limits);
  - the history format the model was trained on;
  - whether the `terminate` status is mapped to done.
  - If the native harness gives ~60–70% on a full run, "beating GUI-Owl-1.5-2B" against the matched 23/116 would mislead readers.
- **History parity.** GUI-Owl's native setup sees up to 5 screenshots; your harness gives one. That is legitimate for an on-device budget, but disclose it as a constraint the baseline was not designed for. Consider also running GUI-Owl with `last_image=1` in its native prompt format, which isolates "history budget" from "prompt format" as the cause.
- **Disclose per arm:** prompt, action space, history window and number of images, image resolution and token budget, decoding settings, retry/parse-repair policy, step budget, and done semantics.

### Gaps
- No full native-harness GUI-Owl-1.5-2B run on your setup exists yet; only 2 episodes. Whether 67.9 reproduces on this AW snapshot and a Mac emulator is unknown.
- The GUI-Owl-1.5 paper does not state the number of AW trials or the seed. The released scripts imply seed 30 and one run, but the paper does not confirm it.

## Q5. Contamination: who trained on AW tasks/environments, split conventions, what counts as legitimate, held-out alternatives

### Takeaway
Many top AW models trained directly on AW: other-seed instances of the same 116 templates, the AW environment with its rule-based checkers as RL reward, or AW-derived tasks. AW has no official train split. The emerging convention is "train on other seeds, test on seed 30, remove identical instances", which the AW authors frame as a legitimate use of the environment, but it is in-distribution. Your rule (no AW tasks or variants, no AW eval trajectories, no AW checkers as rewards) is stricter than common practice, which is a selling point. Disclose app-level overlap and test-set-driven model selection as well, and report at least one held-out benchmark that nobody in the comparison trained on.

### Cited Findings
- **AW authors on training use.** Dynamic task construction "supports online learning, particularly reinforcement learning, … while also streamlining train/test dataset generation for supervised learning". Non-zero rewards under some seeds point to "potential enhancements through RL-like mechanisms". — [AW paper §3.3, §5](https://arxiv.org/html/2405.14573)
- **No official training split.** "AndroidWorld was originally designed for evaluation rather than training"; it "provides only a single task instance per template (116 total) for evaluation … and therefore includes no RL-capable training split".
  - AndroidWorld-Generalization defines three regimes: unseen instance (same 78 templates, other seeds; 1149 train / 234 test), unseen template (57 / 18), and unseen app (12 / 5 apps).
  - RL gains: +26.1 on unseen instances, +15.7 on unseen templates, +8.3 on unseen apps.
  - [AndroidWorld-Generalization](https://arxiv.org/abs/2603.07432)
- **MobileRL-9B (80.2% on AW).**
  - Generates "a large number of training tasks" from AW's randomized parameters. "To prevent overlap with the evaluation set, we remove all tasks whose specific content and initial states coincide with those in the test set … we curate 2,000 tasks."
  - "The best model, MobileRL-9B, is gained from online RL purely on the AndroidWorld environment" with AW's rule-based reward.
  - [MobileRL App. D.4, App. E](https://arxiv.org/abs/2509.18119)
- **UI-Voyager-4B (81.0% pass@1).**
  - Uses "a seed task generator that synthesizes novel tasks by perturbing key parameters … from original task templates", run in AW with a "durable, rule-based verifier … using the Android Debug Bridge".
  - States "we only consider AndroidWorld in this work".
  - I read this as training on AW templates and checkers; the paper does not use the word "contamination".
  - [UI-Voyager](https://arxiv.org/abs/2603.24533)
- **Leaderboard disclosures.**
  - V-Droid: "Training data consists of apps and tasks from the AndroidWorld benchmark."
  - AGI-0: "Trained open source models using our novel training technique on AndroidWorld tasks."
  - Both remain ranked, with only a note.
  - [AW leaderboard](https://docs.google.com/spreadsheets/d/1cchzP9dlTZ3WXQTfYNhh3avxoLipqHN75v1Tb86uhHo)
- **MAI-UI (2B: 49.1; 8B: 70.7; 235B: 76.7 on AW).**
  - Online RL in a containerized environment "inspired by an experimental feature in AndroidWorld", integrating "over 35 applications" including Mattermost, Mastodon and Mall4Uni, which are also MobileWorld's apps.
  - RL raised AW scores: 2B 45.1 → 49.1, 8B 64.7 → 70.7.
  - I found no statement on AW app or task overlap.
  - [MAI-UI §2.3.3, Table 9](https://arxiv.org/abs/2512.22047); [MobileWorld](https://arxiv.org/abs/2512.19432)
- **GUI-Owl-1.5.**
  - Trained with a "hybrid data flywheel" over "simulated environments and cloud-based sandbox environments" plus MRPO environment RL. Mobile data comes from real-device exploration, virtual web-rendered environments, and human annotation on "the same real device environments".
  - I found no statement about excluding AW apps or tasks in the passages I retrieved.
  - [Mobile-Agent-v3.5](https://arxiv.org/abs/2602.16855)
  - GUI-Owl v1 likewise used "a cloud-based virtual environment infrastructure spanning … Android"; no decontamination statement found. — [Mobile-Agent-v3](https://arxiv.org/abs/2508.15144)
- **ZeroGUI.** Runs online RL with auto-generated tasks and VLM rewards inside the OSWorld and AndroidLab environments, and reports gains on those same environments. — [ZeroGUI](https://arxiv.org/abs/2505.23762)
- **Holdouts must match the claimed generality.**
  - "The more general the intended generality of the agent, the more the held-out set should differ from the training set." A domain-general benchmark needs held-out *tasks*; per the authors' survey, only 1 of 8 domain-general benchmarks had a proper holdout.
  - "Without proper hold-outs, agent developers can take shortcuts, even unintentionally."
  - [AI Agents That Matter §5](https://arxiv.org/abs/2407.01502)
- **Memorization on deterministic benchmarks.** A replay script's success equals the source agent's pass@k, and static configurations "allow agents to succeed via memorized action sequences". — [Statistical Precipice](https://arxiv.org/abs/2605.08261)
- **Held-out and alternative benchmarks:**
  - **MobileWorld**: 201 tasks / 20 apps; GUI-only subset of 116; max 50 steps; deterministic backend checks. — [MobileWorld](https://arxiv.org/abs/2512.19432)
  - **AndroidLab**: 138 tasks / 9 apps on predefined AVDs. — [AndroidLab](https://arxiv.org/abs/2410.24024)
  - **A3**: 100 tasks / 20 online Play-Store apps, MLLM "essential-state" judge. — [A3](https://arxiv.org/abs/2501.01149)
  - **B-MoCA**: 131 daily tasks across device configurations. — [B-MoCA](https://arxiv.org/abs/2404.16660)
  - **SPA-Bench**: English and Chinese system and third-party apps. — [SPA-Bench](https://arxiv.org/abs/2410.15164)
  - **MobileGym-Bench**: 416 templates with a 256-test / 160-train template split, deterministic judges. — [MobileGym](https://arxiv.org/abs/2605.26114)
  - **AndroidReality**: perturbation benchmark built on AW. — [AndroidReality](https://arxiv.org/abs/2608.07775)
  - **AndroidWorld-Generalization**: unseen-template and unseen-app splits. — [AW-Gen](https://arxiv.org/abs/2603.07432)
  - **DigiWorld**: 15 sandboxed apps, 3.2M configurations, built to resist replay. — [Statistical Precipice](https://arxiv.org/abs/2605.08261)
  - **AndroidDaily**: 350 tasks / 94 closed-source apps. — [AndroidDaily](https://arxiv.org/abs/2605.27761)
  - **APPSim-Bench**: 557 tasks / 17 apps. — [APPSim-Bench](https://arxiv.org/abs/2609.07712)
- **LLM judges on mobile benchmarks.** One benchmark of judges compiled 931 human-annotated trajectories across 6 mobile benchmarks to test judge methods, including those from SPA-Bench, A3 and AndroidArena. That matters when an alternative benchmark (A3, SPA-Bench) scores with a VLM judge rather than a deterministic checker. — [Benchmarking LLM Judges for Mobile Agent Evaluation](https://arxiv.org/abs/2608.11434)

### Inferences
- **Taxonomy for your disclosure section**, strongest to weakest exposure:
  1. AW eval trajectories or seed-30 instances in training: test leakage.
  2. AW templates at other seeds: in-distribution, the "unseen instance" regime.
  3. AW checkers as RL reward, even on new tasks: reward from the test oracle.
  4. Same 20 AW apps with different tasks: the "unseen template" regime.
  5. AW-like emulator infrastructure with different apps.
  6. **Adaptive test-set reuse**: choosing checkpoints, prompts or decoding tricks by AW seed-30 score. Your v1 → v2 → force_think → v3 iterations are of this kind.
  - Your rule covers 1–3. State your stance on 4 explicitly: do your SFT sources (AndroidControl, AMEX, Odyssey, synthetic) include Markor, Simple Calendar Pro, Broccoli, OsmAnd, etc.? Also acknowledge 6.
- **GUI-Owl's own exposure is undocumented.** If LFM3 is clean and GUI-Owl's status is unknown, frame the comparison as "clean model vs. a model with undisclosed training environments", and lean on a held-out benchmark that neither team targets.
- **MobileWorld is not neutral for Tongyi models.** MobileWorld and MAI-UI are both Tongyi Lab work, and MAI-UI's RL apps overlap MobileWorld's. GUI-Owl is from a different Tongyi group, but its MobileWorld numbers are self-reported.
- **Practical held-out choices for a 2B screenshot-only agent:**
  - AndroidWorld-Generalization unseen-app or unseen-template test splits. Same infrastructure, but you have not trained on AW at all, so for you the whole of AW is already "unseen".
  - MobileGym-Bench test templates.
  - MobileWorld GUI-only (116 tasks).
  - AndroidLab (138 tasks).
  - Prefer deterministic-checker benchmarks over VLM-judged ones for small-gap claims.

### Gaps
- I could not confirm whether GUI-Owl-1.5's sandbox or RL environments include AW's F-Droid apps or task templates.
- I did not verify AndroidArena's task counts or protocol; it appears only as a judge source in the 2026 judges benchmark.
- I did not establish whether PhoneBuddy, OpenMobile-2, K²-Agent or MobileForge trained on AW tasks.

## Q6. Reporting best practices for small-model agent claims (checklist)

### Takeaway
The minimum defensible claim has six parts:
- (i) a pinned, disclosed protocol;
- (ii) a pre-registered final config evaluated on a held-out seed set (and ideally a held-out benchmark);
- (iii) paired, template-clustered tests with Wilson and paired CIs;
- (iv) multiplicity control over every variant you tried;
- (v) per-difficulty and failure-mode breakdowns;
- (vi) a harness-parity table.

At n = 116 single-run you can claim only gaps of about 14 or more tasks. "Matches" needs an equivalence margin and several hundred paired instances.

### Cited Findings
- **Wilson intervals.** The AW paper itself reports Wilson 95% CIs for its robustness analysis. — [AW paper Fig. 3](https://arxiv.org/html/2405.14573). Wilson plus hierarchical bootstrap is the recommended aggregation for CUA benchmarks. — [Statistical Precipice](https://arxiv.org/abs/2605.08261)
- **Multiple runs and power analysis.** Use multiple runs, a power analysis, and pass@k (optimistic) alongside pass^k (pessimistic) as an envelope. — [On Randomness](https://arxiv.org/abs/2602.07150)
- **Multi-seed reporting.** Replicating across seeds caught two of the authors' own over-claims; they release a library for routine k-seed reporting. — [Teach it to stop](https://arxiv.org/abs/2607.17136)
- **Cost and holdouts.** Report cost alongside accuracy, use holdouts matched to the claimed generality, and standardize the harness. — [AI Agents That Matter](https://arxiv.org/abs/2407.01502); [HAL](https://arxiv.org/abs/2510.11977)
- **Precedent for difficulty and pass@k splits.** MobileRL reports success by complexity level and pass@1/2/4/8. AndroidWorld-Generalization reports easy/medium/hard with SDs. AW's own `process_episodes` prints success by tag and difficulty. — [MobileRL](https://arxiv.org/abs/2509.18119); [AW-Gen](https://arxiv.org/abs/2603.07432); [suite_utils.py](https://github.com/google-research/android_world/blob/main/android_world/suite_utils.py)
- **Don't compare pass@k to pass@1.** MobileForge reports its result as "67.2% Pass@3 … close to … GUI-Owl-1.5-8B … at 69.0%". 69.0 is GUI-Owl's self-reported AW number; the abstract does not say whether it was re-measured at Pass@3. — [MobileForge](https://arxiv.org/abs/2606.19930); [HF card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct)
- **Same harness, different baseline sources.** UI-Voyager averages 64 runs for its own model but takes baselines "from prior papers". — [UI-Voyager](https://arxiv.org/abs/2603.24533)

### Inferences (checklist)
1. **Pin the protocol.**
   - AW commit hash and AVD (Pixel 6, API 33; record the ABI and image build).
   - Fixed app APKs, `-no-snapshot`, clock reset, upstream step budgets (10 × complexity).
   - Done semantics as in upstream.
   - Seed list declared in advance: dev = 30, test = e.g. 7, 1234, 2026; note that 38 templates are seed-invariant.
   - Record emulator ID per episode, and check that the two emulators do not differ systematically.
2. **Score exceptions both ways.**
   - Primary: exceptions = failure over 116.
   - Secondary: the official over-completed number.
   - Infrastructure re-run rule fixed in advance; report the exception count per model.
3. **Pre-register.**
   - Freeze the LFM3 checkpoint, prompt and decoding before touching the test seeds.
   - Write down the primary hypothesis: a one-sided directional "LFM3 ≥ GUI-Owl (matched)", or equivalence with margin ±m tasks.
   - Name the primary test: template-clustered paired permutation; secondary exact McNemar per seed.
   - Fix α and the number of seeds, chosen from the power table: ≥ 3 seeds for an 8-task effect at d ≈ 0.2.
   - This is the AW analogue of "hold out a test set". Every v1/v2/v3 decision so far used seed 30, which is now a dev set.
4. **Control multiplicity.**
   - Count every variant and harness tweak evaluated against GUI-Owl; apply Holm (or Bonferroni) to confirmatory claims.
   - Report the number tried. Best-of-5 alone inflates by about 3–5 tasks under null noise (computed above).
   - Treat exploratory comparisons (v1 vs v2 vs force_think) as hypothesis-generating.
5. **Report per model and arm:**
   - successes/116 with Wilson CI;
   - paired discordant counts (A-only / B-only) with exact McNemar p and the paired-difference CI (Newcombe or cluster bootstrap);
   - per-seed and pooled results with the template-clustered CI;
   - per-difficulty (61/36/19) and per-tag success;
   - exception count, self-termination rate, mean steps, parse-failure rate;
   - latency and tokens (cost axis, per AI Agents That Matter and HAL).
6. **Harness-parity table.** GUI-Owl native, GUI-Owl matched, LFM3 matched (Q4), plus the published 67.9 and any gap analysis. Never put a matched-harness GUI-Owl number next to "beats GUI-Owl" without the native number beside it.
7. **pass@1 headline from a fixed number of runs.** pass@k / pass^k only as an envelope, and only against baselines measured the same way.
8. **Contamination statement.**
   - The taxonomy in Q5, items 1–6, with your status on each, including app-level overlap of SFT data with AW's 20 apps and adaptive test-set reuse.
   - The baseline's known or unknown exposure.
9. **At least one held-out benchmark with a deterministic checker** (e.g. MobileWorld GUI-only, AndroidLab, or AW-Generalization unseen-app), run under the same harness rules for all arms.
10. **Release per-episode results** (task, seed, success, exception, steps) for every arm so others can recompute paired statistics. The AW leaderboard asks for trajectory submissions for the same reason.

### Gaps
- No AW-specific methodology standard (an "AW-Verified" protocol) appears to exist. The leaderboard is archived and self-reported, so the checklist above combines general agent-evaluation guidance with the AW code's semantics rather than an official AW rule set.
