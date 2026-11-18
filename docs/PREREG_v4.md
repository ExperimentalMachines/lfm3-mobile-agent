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
* 2026-11-18 06:25 (before any v4 result; after Codex's recovery/gate audit, results/codex/codex_recovery_gate_audit.md):
  the gate's answer criterion becomes stricter: a dev_answer prediction counts only if `same_answer` holds AND it adds no
  content words to the reference (data/v4_answer_check.gate_answer; appending "is incorrect" to every reference scored
  92.6% under same_answer alone). The 0.20 threshold is unchanged; the same_answer rate is still reported. The v4-RL
  promotion rule's "strict dev_answer" is computed with the same gate_answer, locally from the downloaded predictions.
  Gate inputs are now also bound to the pinned v3 run (sha256 of its 116 episode files), the generate.py manifests
  (model, dataset@split#revision, greedy, thinking mode), one episode per file and >= 1 step for any success.
  Recovery: sft_vlm.py now refuses to train from scratch if a hub checkpoint repo exists but cannot be listed/restored,
  and refuses checkpoints written under a different run configuration (run_config.json pinned on the checkpoint repo).
* 2026-11-18 09:30 (v4 offline dev evals were read; no v4 or v4-RL AndroidWorld result exists; nothing sealed was
  opened): infrastructure, no design change. (1) The merged-v4 upload to the hub failed ("Private storage limit
  reached"); the merged weights were copied from the VM and verified before export: bf16(base@23387beda4 + 2*B@A of the
  final step-1250 adapter, hub ckpt repo @58bcb65) within 1 bf16 ulp on all 153 LoRA targets, the other 271 tensors
  bit-identical to the base, and the 14 non-weight files byte-identical to the v3 merged release; pinned in
  results/v4_local_export_manifest.json, exported by scripts/local_v4_to_aw_v2.sh (seed-30 flags unchanged). v4-RL
  weights will be copied from the VM the same way. (2) Resuming a paused AndroidWorld arm no longer re-runs saved
  exception episodes (android_world's default would have given paused arms a second try): they stay scored failures,
  as written above; only the episode interrupted by the pause, which was never saved, is run again
  (run_aw.py --retry_failed_on_resume, default off). No sealed arm had been resumed before this change. (3) The
  emulator-2 filler would have resumed the paused GUI-Owl seed-1234 arm from its log file instead of its run directory;
  replaced by scripts/local_emu2_fill_v2.sh before the pause happened.
* 2026-11-18 10:10 (same state; Codex re-audit results/codex/v4_lane_reaudit/): checkpoint files are now written
  atomically and an unreadable saved episode stops a resume instead of being silently re-run (android_world's default
  skipped unreadable files). The 33 saved GUI-Owl seed-1234 episode files pass `gzip -t` (no contents read).
  v4-RL offline promotion is computed by scripts/v4rl_promotion.py (item 10 thresholds, gate_answer, inputs bound to
  the pinned dev rows, one prompt/pixel setting for both models).
* 2026-11-18 10:40 (no v4 or v4-RL AndroidWorld result read): v4-RL offline promotion (item 10) FAILS, so v4-RL is
  not a candidate for "LFM3 final" and gets no seed-30 run as one (results/v4rl_promotion_offline.json; Codex recomputed
  (a) independently, results/codex/emu2_v3_promo_audit/report.md): strict dev_answer 0.890 vs v4 0.868 (+0.022 < +0.05);
  false answers 0/80 (pass); AndroidControl test high-level step SR 0.667 vs 0.728 (-0.061 < -0.02). The Colab VM was
  stopped. Emulator 2 runs scripts/local_emu2_fill_v4.sh: after the v4 seed-30 pass it applies the gate mechanically
  (PASS -> sealed v4 seed 7; FAIL -> sealed v3 seed 7, v1 seed 7 being done; input error -> none) and then resumes the
  sealed GUI-Owl seed-1234 arm.
* 2026-11-18 13:22 (seed 30 only; no sealed outcome read): the v4 development gate PASSES (results/v4_gate_seed30.txt):
  seed 30 = 18/116 (6 answer-task + 12 action-task successes; v3 13 = 0 + 13; v1 15; GUI-Owl matched 23 = 10 + 13);
  dev_answer gate_answer 0.868, emitted 0.956; dev_complete false answers 0/80. v4 is frozen as "LFM3 final"
  (models/lfm3vl2b_v4-GGUF, manifest results/v4_local_export_manifest.json) and its sealed seed-7 arm started
  automatically on emulator 2 (scripts/local_emu2_fill_v4.sh). Four seed-30 v4 episodes ended in infrastructure
  exceptions with no recorded steps (adb output polluted by a gRPC fork warning: SimpleSmsSend,
  SimpleSmsSendClipboardContent, MarkorCreateNoteAndSms; app-data reset failure: SimpleCalendarNextEvent); they count as
  failures here and do not change the gate. Codex's adversarial review: results/codex/v4_seed30_audit/.
* 2026-11-18 18:25 (no sealed outcome read yet): every seed-7 arm has finished (GUI-Owl matched, v4 = LFM3 final, v1:
  116 episode files each), so seed 7 is unsealed now for the preliminary analysis in "Analysis" (one held-out seed ->
  labelled preliminary). Nothing about the remaining arms changes with what seed 7 shows: v4 is frozen, harness and flags
  are fixed. Remaining sealed arms are queued (scripts/local_sealed_queue.sh, same runner local_sealed_aw_v3.sh):
  emulator 2 after GUI-Owl seed 1234 -> v4 seed 1234 -> v1 seed 2026; emulator 1 after the MAI-UI seed-30 development
  run -> GUI-Owl seed 2026 -> v4 seed 2026.
* 2026-11-19 00:56 (seeds 1234 and 2026 still sealed; only seed 7 has been read): changes from Codex's audit of the seed-7
  analysis (results/codex/seed7_analysis_audit/report.md, verdict VALID WITH CAVEATS), fixed before any further seed is
  opened. (1) The "seed-varying" breakdown now uses a source-checked manifest of the 78 templates whose goal text can
  vary with the seed (results/aw_template_manifest.json), as this document originally stated; the earlier goal-text
  comparison against seed 30 found 76 because two templates drew the same wording by chance. (2) The 95% CI reports
  the exact endpoints of the inverted sign-flip test for the fixed 10,000 draws, rounded outward to 0.1 pp (the 0.1-pp
  grid trimmed them inward); the non-inferiority decision uses the unrounded lower bound. Seed 7 is unchanged by this:
  [-7.27, +10.77] pp, not non-inferior. (3) Every checker success of every arm on every held-out seed gets the same
  trajectory review once that seed is unsealed; successes the saved trajectory contradicts are listed in
  results/aw_checker_disputes.json and counted as failures only in a reported sensitivity analysis. The primary
  endpoint stays the checker verdict. Seed 7 has one such case: v4 ClockStopWatchPausedVerify (stopwatch left running);
  sensitivity v4 17 vs GUI-Owl 16, +0.9 pp, CI [-8.1, +9.9]. (4) Disclosed, not fixed mid-protocol: gRPC fork warnings
  on adb stderr can corrupt adb output during task setup in every arm. Such setup crashes remain exceptions handled by
  the single re-run rule, so all remaining arms run on the same harness.
* 2026-11-19 01:55 (MobileWorld run 2, before any re-run outcome): completion rule for both MobileWorld runs (GUI-Owl
  and v4; also any later MAI-UI run), implemented in scripts/gcp_mw_resume_vm.sh. A task without a result counts as a
  failure unless the environment caused it: task setup failed (/task/init 500) or scoring failed (/task/eval 500) gets
  ONE more attempt in a freshly restarted container after the run's list ends; a task cut off by a VM stop or
  preemption, or never reached, is run. Not re-run (counted as failures, disclosed): an action the runtime rejects
  (GUI-Owl's double_tap), output the official agent cannot parse after its own retries, and ask_user, whose simulated
  user needs an LLM API key this setup does not have. Replaced task folders are kept under traj_logs/_interrupted/ and
  every decision is logged (traj_logs/_retry_manifest_<run>.jsonl). Known before this rule: GUI-Owl's container had 5
  setup and 2 scoring failures (mostly Mastodon tasks); v4's container had none. Tasks that did produce a result in
  that container may also have been affected; not corrected, disclosed. The VM's IP is reserved so a restart keeps the
  model tunnels.
