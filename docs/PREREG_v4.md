# Pre-registration: LFM3 v4 vs GUI-Owl-1.5-2B (written 2026-11-18 ~02:30 Asia/Manila, before any held-out run)

Committed to git before the first held-out episode is run. Anything below that changes later is listed in a dated
"Deviations" section at the end; nothing above it is edited.

## Question
Under the same on-device budget (one screenshot per step, Q4_K_M GGUF, llama.cpp, our harness), does our final LFM3
model match GUI-Owl-1.5-2B on AndroidWorld? "Match" = non-inferiority with margin 8 tasks per 116 (6.9 pp).

## Arms
* **GUI-Owl matched**: `run_aw.py --agent=guiowl --guiowl_images=1 --guiowl_max_pixels=1048576`, GUI-Owl-1.5-2B-Instruct
  Q4_K_M + Q8_0 mmproj, plus the device's installed-app list in its instruction (mirrors the input v4 receives).
* **LFM3 final**: v4 (prompt v4 with installed-app list) if it passes the development gate below; otherwise v3 and v1
  are reported (v1 = best seed-30 model; neither receives an app list, which can only favour GUI-Owl).
* **LFM3 v1** (reference, original prompt).
GUI-Owl's native-configuration number (67.9% published, own harness) is shown next to the matched number, never in
place of it.

## Protocol (all arms)
AndroidWorld commit 55ddaf5 + local patches, Pixel 6 API 33 arm64 AVDs, 116 tasks, `n_task_combinations=1`,
10x task-complexity step budget, success only if the agent ended the episode (`suite_utils.py`), temperature 0,
one parse retry (LFM3). Primary score: full successes (`is_successful >= 1`, exception = failure) over 116.
Secondary: official rule (exceptions dropped). Infrastructure crash before step 1 (emulator/adb, not model output)
is re-run once; everything else counts.

## Seeds
Development: 30 (already used to choose v1/v2/v3 — not evidence for the final claim).
Held-out, sealed: **7, 1234, 2026**, run in that order. Seed 7 runs tonight for GUI-Owl matched and LFM3 v1; the final
LFM3 model runs seed 7 after it is frozen. Sealed = results written under `results/androidworld_sealed/`; run logs are
filtered so per-task outcomes are not printed; only episode counts are inspected until every arm on a seed has
finished. 38 of the 116 templates are seed-invariant; results on the 78 seed-varying templates are reported separately.

## v4 development gate (seed 30 and offline; decided before seeing held-out seeds)
v4 is frozen and run on held-out seeds only if all hold: (1) answer exact-match on held-out question episodes clearly
above 0; (2) answer actions on AndroidControl-style action goals ≤ 3% of terminal steps; (3) AndroidWorld seed 30:
≥ 3 answer-task successes and action-task successes not lower than v3's by more than 3. Otherwise v4 is reported as a
development result only.

## Analysis
Primary: paired difference LFM3 final − GUI-Owl over all held-out instances, template-clustered sign-flip permutation
test (10,000 permutations, clusters = task templates); non-inferiority if the lower 95% bound > −6.9 pp.
Also reported: exact McNemar per seed, Wilson CIs, answer-task vs action-task split, per-difficulty, seed-varying
templates only. With one held-out seed only (tonight), the result is labelled preliminary (detectable gap ≈ 14 tasks).

## Contamination statement
No AndroidWorld tasks, variants, trajectories or checkers in any LFM3 training data. v4 adds question episodes built
from AndroidControl *train* episodes (non-AndroidWorld apps) with a teacher (Qwen3-VL-8B-Instruct); dev questions come
from AndroidControl val episodes. The installed-app list at inference is read from the device. GUI-Owl's training
exposure to AndroidWorld is undisclosed by its authors.

## Deviations
* 2026-11-18 02:35 (before any held-out result was read): (1) the question dev set is 200 screen-disjoint AndroidControl
  *train* episodes held out from v4 training (their action versions are removed too; v4 trains from the base model),
  not AndroidControl val as written above; (2) teacher labels are accepted only under a strict type-aware answer check
  (data/v4_answer_check.py) adopted after Codex's research found false agreements in the generation-time check;
  (3) the sealed v1 seed-7 arm is paused while v4's seed-30 development pass runs and resumed from its AndroidWorld
  checkpoint (same seed and harness; an interrupted episode is re-run); (4) a possible second branch, `v4-RL`
  (static-screenshot GRPO from v4, Codex research rank 1), would be a separate, dated arm: it can replace v4 as
  "LFM3 final" only if it passes the same gate on seed 30 plus an offline promotion rule written down before its
  training ends, and only before seed 7 is unsealed.
* 2026-11-18 02:45 (after Codex's adversarial pipeline audit, results/codex/codex_v4_pipeline_audit.md; still before any
  held-out result was read): (5) gate criterion (1) is made numeric: strict typed answer match on dev_answer >= 0.20
  and `answer` emitted on >= 50% of its rows (scripts/v4_gate.py now also fails on incomplete inputs); (6) the two arms
  started at 01:30/01:35 (v1 and GUI-Owl, seed 7) use the first sealed runner, whose run logs
  (logs/aw_sealed_*_seed7.log) still contain android_world's per-episode result tables: those files have not been
  opened (only episode-file counts were checked) and will not be opened before every seed-7 arm has finished; all
  later sealed arms use scripts/local_sealed_aw_v2.sh (output only inside the sealed dir, truthful exit status);
  (7) question data: AndroidWorld-app guard tightened (episode-wide app names vs android_world's launcher patterns,
  whole-word app-type terms), the rewritten direct question is used as a goal only if separately verified on the same
  screen (otherwise the verified compound goal), and dev_complete controls exclude information-seeking original goals;
  (8) the preregistered single infrastructure retry is applied manually (documented per case), not by the runner.
* 2026-11-18 04:05 (before any v4 or v4-RL result): (9) Codex's audit of the built v4 data (results/codex/codex_v4_data_audit.md)
  returned STOP; the first v4 training run (data 570febb) is abandoned and v4 is retrained from the base model on a rebuilt
  dataset (answer-leaking goals dropped, guard v3 on goals + history text, goal-named apps added to the installed-app
  list, magnitude/date/time/unit-aware answer check, information-seeking goals removed from dev_complete), under a new run
  name and checkpoint repo. (10) v4-RL promotion rule, fixed now: v4-RL replaces v4 as "LFM3 final" only if, versus v4,
  strict dev_answer match is >= +0.05 absolute, dev_complete false-answer rate <= 0.03, AndroidControl test high-level
  step SR >= -0.02, and on AndroidWorld seed 30 it passes the gate with total full successes >= v4's. Otherwise v4 stays.
* 2026-11-18 04:45: Codex's re-audit of the rebuilt data (results/codex/codex_v4b_reaudit.md) again recommended STOP. Decision:
  continue the v4 (v4b) SFT run and disclose the measured residuals instead of a second restart: answer errors 4/40 in a
  balanced visual sample (Wilson 95% CI 4-23%; teacher errors that both teacher calls share, not removable without a
  stronger adjudicator), goal-named apps missing from the inventory in 179/2,386 QA endpoints, 53 QA episodes involving
  Google apps (Gmail/Drive/Maps/YouTube) that are installed on the AndroidWorld image but used by no AndroidWorld task.
  The formal rule (no AndroidWorld tasks, variants, trajectories or checkers) holds. Before RL starts, its reward is
  changed to exact normalised answer equality (data/v4_answer_check.exact_answer) because the re-audit showed the
  typed-agreement check rewards padded answers ("12M is incorrect"); strict dev metrics use the strict parser.

* 2026-11-18 06:10 (before any v4 result): infrastructure, no design change. The Colab A100 VM was pruned at 04:51 during
  v4b SFT (step 353/1250). Training resumes from the step-350 hub checkpoint (adapter, optimizer, scheduler, RNG state and
  trainer_state; data order continues from the saved step), first on an interim L4 for ~5 min that wrote no checkpoint
  (stopped before step 400), then on a new A100 (session lfm3v4a) where the RL hook was reinstalled. Steps 351-353 are
  recomputed. The gate script gained input-identity checks (episode agent_name; same goal text, modulo the run timestamp
  of MarkorCreateFolder, and instance seed as the v3 seed-30 run; dev predictions must equal the dev splits pinned at
  3375539 and come from the v4 merged model) without changing any threshold.
