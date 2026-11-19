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
(none yet)
