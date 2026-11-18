**Verdict: VALID WITH CAVEATS — as a preliminary, preregistered benchmark-checker result.** The final recorded scores and retry substitutions reproduce. Seed 7 does **not** establish non-inferiority, superiority, or equivalence. One v4 success contradicts its trajectory, and the “seed-varying” subset is misdefined. The reported 18 successes must not be described as 18 independently verified task completions.

Audit scope: the three original seed-7 runs (348 episodes), five retries, seed-30 development comparison, all dated preregistration entries, analysis/runner/agent/checker sources and seed-7 logs. No other sealed result or log was opened. No AndroidWorld, emulator, model server, adb command or process signal was executed. All audit writes are in this directory.

**Findings**

**P2-1 — v4 receives a false-positive stopwatch success.** In `v4_seed7/run_20261118T132321898379/ClockStopWatchPausedVerify_0.pkl.gz`, the goal is “Pause the stopwatch.” The four actions are open Clock → select Stopwatch → click Play → `status(complete)`. The terminal observation shows **02.99 and a Pause button**, with no subsequent pause action. The checker nevertheless logs `Start present: True`, `Stopwatch: 2`, then success. Its predicate accepts any `Start` accessibility node plus two Stopwatch nodes; the saved trajectory contradicts the accepted state. The checker-time accessibility tree was not recorded, so stale versus extraneous accessibility nodes cannot be distinguished.

Evidence: [four-step image](ClockStopWatchPausedVerify_steps.jpg), [outputs/actions](success_traces.json), [last physical tap and checker log](/Users/alpha/lfm3-android/results/androidworld_sealed/v4_seed7/run_output.SEALED.log:4591), [checker predicate](/Users/alpha/lfm3-android/android_world/android_world/task_evals/single/clock.py:43). The first teardown action follows the success log; teardown does not explain the mismatch.

Impact: changing just this score to failure gives **v4 17/116 versus GUI-Owl 16/116**, difference **+0.862 pp**, exact McNemar **p=1**, and continuous sign-flip interval **[−8.065, +9.804] pp**. Non-inferiority still fails. Preserve the preregistered checker score with this disclosure and publish the sensitivity separately; do not silently rewrite the primary endpoint.

**P2-2 — goal-string comparison is not a seed-varying-template classifier.** [Analysis lines 113–119](/Users/alpha/lfm3-android/scripts/sealed_analysis.py:113) correctly find **76 observed goal changes** between seeds 30 and 7, but label these as the preregistered varying templates. Two potentially varying goals happen to collide: `OpenAppTaskEval` chooses **contacts** in both seeds; `SportsTrackerLongestDistanceActivity` chooses **mountain biking** in both. The latter's sampled distance changes from **1200 to 4500 meters** despite identical wording. Adding these two yields the **78 templates whose goals can vary**, with final scores **11/78, 14/78, 5/78** for v4/GUI-Owl/v1, instead of **10/76, 14/76, 4/76**.

Moreover, the remaining 38 are not all invariant *instances*: 20 have seeded hidden inputs/setup, including browser puzzles, receipt contents, duplicate recipes, and calendar/task-list queries with fixed wording. Counting seeded parameters/setup gives 98 templates under that broader definition. Thus **76 is right for this observed text comparison; 78 is defensible for potentially varying goal text; neither establishes that the other instances repeat unchanged**. The literature's [38/78 split](https://arxiv.org/html/2603.07432v1) does not supply a pinned manifest for this local implementation. This affects the generalization breakdown, not the 116-task primary score. Use an explicit, source-checked template manifest and state the definition.

Evidence: [subset membership and scores](template_subsets.json), [independent parameter draws](ir_parameters_reconstructed.json), [reproduction/source catalog](subset_audit.py), [OpenApp generator](/Users/alpha/lfm3-android/android_world/android_world/task_evals/single/system.py:479), [sports task definition](/Users/alpha/lfm3-android/android_world/android_world/task_evals/information_retrieval/proto/tasks.textproto:2488).

**P2-3 — a real harness defect pollutes adb results in both arms; directional bias is unproved.** v4 `SimpleSmsSend` parses a gRPC fork-warning line as an SMS row and fails on missing `address`; GUI-Owl `SimpleSmsResend` tries to parse a warning plus a timestamp as an integer. [`adb_controller.py:129`](/Users/alpha/lfm3-android/.venv-aw/lib/python3.11/site-packages/android_env/components/adb_controller.py:129) merges stderr into stdout, allowing this contamination. Setting `GRPC_VERBOSITY` after imports in [run_aw.py:28](/Users/alpha/lfm3-android/eval/androidworld/run_aw.py:28) did not prevent it. These are infrastructure failures, not bad model outputs. [Original exception traces](exceptions.json) prove the defect.

The 4-v4/1-GUI exception split does **not** establish emulator-2 or shared-adb load as its cause. Both use server port 5037 with explicit device serials; both original logs contain adb/SIGTRAP failures. The local controller suppresses shared-server restarts, and the reviewed logs record no restart. GUI-Owl/v1 log filtering removes fork-warning lines, so raw warning counts cannot be compared with v4's unfiltered log. No contemporaneous load/isolation record proves or excludes interference from other jobs. The prescribed retries replace all five exception records; four remain failures and GUI-Owl gains one success. Do not claim either a clean infrastructure run or a demonstrated v4-favoring load bias.

**P3-1 — the CI grid trims the accepted interval inward.** [Analysis lines 164–171](/Users/alpha/lfm3-android/scripts/sealed_analysis.py:164) report the first/last accepted **0.1-pp grid points**, not the continuous inversion endpoints. Final primary **[−7.2, +10.7]** is actually **[−7.272727, +10.769231] pp** for the same 10,000 draws. Report continuous endpoints or round outward to **[−7.3, +10.8]**. This does not change the seed-7 decision. The permutation `+1` correction and endpoint indexing are correct; this is discretization, not an off-by-one episode error.

**Independent numerical reconciliation**

The audit reads episodes directly; it does not execute/import `sealed_analysis.py`. Wilson intervals use the normal 0.975 quantile. Sign-flip inversion uses algebraic equality endpoints for each draw, followed by an independent, binomial-weighted enumeration of all sign assignments. [130 numeric/identity comparisons](reported_numeric_checks.json) match the two saved JSON analyses, and their Markdown tables agree. Reproductions: [recompute.py](recompute.py), [intervals.py](intervals.py), [verify_reported.py](verify_reported.py).

| Final checker result | v4 | GUI-Owl | v1 |
|---|---:|---:|---:|
| Successes / 116 | 18 | 16 | 11 |
| Percent | 15.517 | 13.793 | 9.483 |
| Wilson 95%, percent | 10.0466–23.1985 | 8.6718–21.2356 | 5.3777–16.1853 |
| Answer / 25 | 6 | 7 | 0 |
| Action / 91 | 12 | 9 | 11 |
| Easy / 61 | 17 | 9 | 10 |
| Medium / 36 | 0 | 6 | 0 |
| Hard / 19 | 1 | 1 | 1 |
| Exceptions after substitutions | 0 | 0 | 0 |

| Final pair | Difference, pp | First-only / second-only / both | 10k sign-flip p | Exact McNemar p | Continuous 10k inversion, pp |
|---|---:|---:|---:|---:|---:|
| v4 − GUI-Owl | +1.724138 | 15 / 13 / 3 | 0.851715 | 0.850554 | −7.272727 to +10.769231 |
| v1 − GUI-Owl | −4.310345 | 9 / 14 / 2 | 0.403460 | 0.404873 | −12.500000 to +3.773585 |
| v4 − v1 | +6.034483 | 11 / 4 / 7 | 0.117088 | 0.118469 | 0 to +12.500000 |

One seed means one observation per template: clustering does not change the 116 paired units. At zero, exact sign-flip equals exact McNemar; Monte Carlo differences are expected. Exact-enumeration inversion is identical to the final primary interval; v1−GUI-Owl's upper endpoint is 3.703704 pp under exact enumeration. The v4−v1 lower endpoint of zero is genuine discreteness, not evidence of superiority.

Before retries, GUI-Owl was 15/116 (Wilson 7.9954–20.2431%), action 8/91, medium 5/36, varying-text 13/76; v4/v1 numerators were unchanged. Primary difference was +2.586207 pp, discordants 15/12, McNemar 0.701108, Monte Carlo p=0.707029; continuous Monte Carlo interval [−6.250000, +11.475410], exact interval [−6.349206, +11.475410]. The provisional NI “yes” becomes **“no”** after the valid GUI-Owl retry. Final lower bound −7.272727 is below −6.9; exact two-sided p at −6.9 is 0.061193. Using precisely −8/116 instead of rounded −6.9 pp does not alter this decision.

Secondary exceptions-dropped results before retries: **18/112, 15/115, 11/116**; the paired analysis correctly retains only **111 common nonexception pairs**, 15/10 discordants, difference +4.504505 pp, McNemar 0.424356. After substitution, all 116 pairs are nonexceptional, so secondary equals primary. Complete before/after numbers, including all reference comparisons, are in [recomputed.json](recomputed.json) and [interval_recomputed.json](interval_recomputed.json).

**CI interpretation:** test inversion is a reasonable operational reading of [the preregistration](/Users/alpha/lfm3-android/docs/PREREG_v4.md:39), which names sign-flipping and a lower 95% bound but leaves inversion, tails, grid and RNG unspecified. It is **not an exact finite-sample 95% interval for a binary mean difference merely because its randomization distribution was enumerated exactly**. Away from zero, flipping `d−delta` requires a symmetry/exchangeability justification beyond the mean-null; ternary differences shifted by −6.9 pp do not satisfy that symmetry automatically. Treat this as a nominal sign-flip interval with an explicit assumption, not guaranteed coverage. See the symmetry condition in [Arias-Castro, §18.1.2, Proposition 18.9](https://mathweb.ucsd.edu/~eariasca/index_files/principles_of_statistical_analysis_free_v1.0.pdf). No stronger statistical claim follows from seed 7.

**Retry eligibility and instance identity**

| Original exception | Setup failure | Retry instance seed | Retry steps / score |
|---|---|---:|---:|
| v4 MarkorCreateNoteFromClipboard | `clipper.set` adb timeout, 10 s | 443795809 | 10 / 0 |
| v4 RecipeDeleteMultipleRecipes | adb `whoami` SIGTRAP during database setup | 1081798181 | 11 / 0 |
| v4 TasksDueNextWeek | adb SIGTRAP checking task database directory | 979320987 | 5 / 0 |
| v4 SimpleSmsSend | gRPC-polluted adb SMS query in initialization | 3301419143 | 8 / 0 |
| GUI-Owl SimpleSmsResend | gRPC-polluted adb time query in initialization | 3808889176 | 7 / 1 |

All five traces go through `suite_utils.py:245 task.initialize_task`, before `run_episode` at line 247. **Eligibility is established by stack location, not empty episode data**: `_create_failed_result` discards steps for any caught exception. Each supplied retry contains exactly one new episode per eligible task; all five replace their originals, including all four failed retries. This follows the once-only rule.

Every retry goal matches byte-for-byte, every agent label matches, and every retry seed equals `sha256("7_<task>_0") mod 2^32`. All 343 nonexception original episodes also carry the expected seed. [Suite construction](/Users/alpha/lfm3-android/android_world/android_world/suite_utils.py:149) seeds each template independently and filters only after instantiation, so a task subset does not shift the draws. Initialization reseeds setup randomness. The clipboard payload also matches in original/retry logs. Full parameter/database snapshots are not saved, and original exception records omit the seed; identity is supported by launch logs, deterministic source, goals and the retry/opposite-arm records, rather than direct full-parameter comparison.

Across arms, the only goal mismatch is `MarkorCreateFolder`: the name contains each run's wall-clock timestamp ([generator](/Users/alpha/lfm3-android/android_world/android_world/task_evals/single/markor.py:162)). All arms fail it, so this imperfect pairing contributes zero to the observed difference. Nor does a matching Python seed guarantee byte-identical environments: the video generator uses [unseeded NumPy noise](/Users/alpha/lfm3-android/android_world/android_world/task_evals/utils/user_data_generation.py:246), and some database IDs use UUIDs. No differing task goal/seed was found among the counted successes. The [per-success review](success_review.md) covers all 34 successes, including the legitimate zero-target spirulina deletion and the correctly repeated GUI-Owl SMS.

**Execution comparability**

Original local times on November 18: GUI-Owl **01:35–09:30**, emulator 5556; v1 **01:30–06:32**, emulator 5558; v4 **13:22–18:07**, emulator 5558. Each original log has one run start/end and no checkpoint-resume/skipped-task marker; episode timestamps do not show a pause/restart. The preregistered possibility of pausing v1 is not evidence it actually occurred. Initial preregistration commit `29d5d25` predates the first launch, despite the approximate time in its heading.

The first runner used by GUI-Owl/v1 differs from v4's later runner in logging/startup/exit handling. The resume/atomic-checkpoint changes do not give a saved seed-7 episode another attempt. Both primary arms receive the same app-list construction, one screenshot, temperature 0, one-second post-action waits and `int(10 × complexity)` steps. [Static budget and episode checks](execution_checks.json) find no over-budget episode across originals/retries. The actual per-episode app-list text was not persisted, so exact installed-package equality cannot be proved from the episodes.

[Original runner](/Users/alpha/lfm3-android/scripts/local_sealed_aw_v3.sh:26) and [retry runner](/Users/alpha/lfm3-android/scripts/local_aw_rerun.sh:21) use the same per-arm model/mmproj paths and inference flags. v4 uses 774,400 input pixels, 1,024 image-token cap, context 8,192, output cap 512; GUI-Owl uses 1,048,576 pixels, cap 2,600, context 20,480, output cap 256. These are matched-input adaptations, not identical compute allocations. No recorded generation reaches either output cap (observed maxima 68/114), and no LFM parse retry occurs. The app list and v4 prompt are declared differences from the v1 reference, not a controlled model-only comparison.

Both November 19 retries run sequentially on emulator 5558, so GUI-Owl's retry changes device instance from 5556. The prescribed model/prompt/server configuration remains the same; the recorded evidence does not establish a systematic advantage from that move. Server logs corroborate model paths, but do not supply run-time weight hashes. No observed configuration change, capped-output asymmetry, unended success, or selective retry establishes a v4-favoring protocol violation. These limits, the checker error and subset correction are why the verdict is **VALID WITH CAVEATS**, with the result still **PRELIMINARY**.
