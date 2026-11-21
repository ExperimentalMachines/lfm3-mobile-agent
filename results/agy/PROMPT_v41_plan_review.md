# Adversarial review: v4.1 follow-up plan and code (before any result is used)

You are an independent, skeptical reviewer. The working directory is a git checkout of branch `v41-followup` of an
Android GUI-agent project. Find everything that is wrong, unfair, misleading or broken. Do not trust comments,
commit messages or docs: check them against the code and data.

## Context

- v4 is a 2B screenshot-only Android agent. Its MobileWorld score (6/105) is final; GUI-Owl-1.5-2B scored 22/105 and
  MAI-UI-2B 11/105. This follow-up tries to raise MobileWorld fairly, after seeing those results.
- The plan is [`docs/PREREG_v41.md`](../../docs/PREREG_v41.md). Three changes: loop guards
  (`train/agent_guards.py`, wired into `eval/androidworld/lfm_agent.py` and `eval/mobileworld/lfm3_mw_agent.py`),
  MobileWorld-native typing (`eval/mobileworld/lfm3_mw_agent.py`), and v4.1 training data
  (`data/v41_build_parquet.py`, trained by `scripts/training/vm_v41_pipeline.sh` with
  `scripts/training/jobs/lfm3_v41_a100.json`). Seed-30 development runs: `scripts/androidworld/local_v41_dev_aw.sh`.
- v4's own training data (read-only, do not copy elsewhere):
  `/Users/alpha/lfm3-android/data/v4work/build/out/data/train-*.parquet` (columns `messages`, `source`,
  `episode_id`, `step_idx`; `messages` = [system, user, assistant]; the assistant intent is in `reasoning_content`).
  Use `uv run --no-project --with pyarrow python` to read it.
- v4's MobileWorld trajectories: `results/mobileworld/traj_r2/v4_gui_en_r2/*/traj.json`.

## Tasks

1. **Fairness and design** (`docs/PREREG_v41.md`): Is anything tuned on the test set? Is the selection rule fixed
   and unambiguous? Is the gate sensible? Is the "post-hoc" labelling sufficient? What is missing that a reader
   needs (e.g. power at n = 105, multiple comparisons, image-budget asymmetry, the fact that only v4 gets a second
   attempt)? Is any claim in the "Why" table wrong? Recompute at least: the 3,918 / 4,151 copied-intent `wait`
   rows in the training data, and the 931 `wait` steps / 4,461 steps in v4's MobileWorld trajectories.
2. **Data builder** (`data/v41_build_parquet.py`): verify D1 and D2 do exactly what the docstring and PREREG say;
   check history renumbering and the 8-step window, determinism, that targets' actions and images never change,
   that dev splits are untouched, and edge cases (history lines without an intent, `(invalid output)` lines,
   lines whose text contains " -> "). Recompute the counts 4,104 / 13,145 / 2,574 / 1,350 / 1,320 if you can.
3. **Guards** (`train/agent_guards.py` and both integrations): find logic bugs. Is the GBNF grammar valid for
   every action and does it match `train/agent_format.action_to_str`? Are G1 and G2 as described? Can a guard end
   an episode, loop forever, or change behaviour when guards are OFF (diff against `git show main:<file>`)? Is
   the screen-change measure right in both agents (which screen is compared with which)?
4. **Training job**: diff `scripts/training/jobs/lfm3_v41_a100.json` against `lfm3_v4_a100.json` and
   `vm_v41_pipeline.sh` against the plan's claim "identical to v4 except the text edits". Any difference that could
   matter (row order, shuffle, evaluation splits, hyperparameters)?
5. **Dev launcher** (`scripts/androidworld/local_v41_dev_aw.sh`): same harness as v4's seed-30 pass
   (`scripts/androidworld/local_v4_to_aw_v2.sh`)? Bash 3.2 (macOS) safe? Can it mix runs or reuse a wrong model?

## Rules

- Read-only on everything outside `results/agy/v41_plan_review/` (you may write scratch files there).
- No network, no git commits or ref changes, no process signals, no emulator/adb/cloud commands.
- Never print secrets.

## Report

Write `results/agy/v41_plan_review/report.md`. First line exactly one of: `Verdict: GO`, `Verdict: GO AFTER FIXES`,
`Verdict: NO-GO`. Then a findings table ordered by severity: ID | severity (P1 = breaks the experiment or its
fairness; P2 = material; P3 = minor) | file:line | what is wrong | evidence | exact fix. Then, briefly, what you
checked and found correct (with the numbers you recomputed).
