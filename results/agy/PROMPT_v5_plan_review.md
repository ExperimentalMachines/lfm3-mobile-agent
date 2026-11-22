# Adversarial review: research report and next-step training plan (before any new training)

You are an independent, skeptical reviewer. The working directory is a git checkout of branch `v41-followup` of an
Android GUI-agent project. Find everything that is wrong, unsupported, unfair, misleading or infeasible. Do not trust
the report: check its numbers against the repo files it cites.

## Context

- LFM3-VL-2B is fine-tuned (LoRA r64, 0.43 epoch of 92,229 rows) into a screenshot-only Android agent. Versions v4,
  v4.1, v4.2: [`docs/models.md`](../../docs/models.md), results in [`docs/results.md`](../../docs/results.md), the
  follow-up log in [`docs/PREREG_v41.md`](../../docs/PREREG_v41.md).
- The report under review: [`docs/research/training-scale-and-own-attempt-learning.md`](../../docs/research/training-scale-and-own-attempt-learning.md),
  built from five note files in `docs/research/notes/training-scale-and-own-attempt-learning/`.
- The owner asked: train more epochs; learn from the model's own attempts; is a bigger LoRA good or bad; is there
  something between LoRA and full fine-tuning; is it just hyperparameters; would short written reasoning slow replies;
  is the dataset varied enough; do our benchmarks suffice; are we overfitting or benchmark-maxxing.
- Constraints the plan must respect: no AndroidWorld/MobileWorld tasks, variants, trajectories, checkers or seeded
  content in training ([`docs/datasets.md`](../../docs/datasets.md)); no paid teacher or external LLM API; about 5
  A100-hours on Colab and one Mac with two Android emulators; on-device speed matters.

## Tasks

1. **Numbers.** Recompute from repo files at least:
   - v4 train vs eval loss at step 1,250 and the learning rate near the end
     (`results/v4_dev/hub/training_logs/log_history.json`, `train_log.jsonl`);
   - false `complete` counts per run on seed 30 and the "GUI-Owl 96% vs v4.2 33% stop precision" claim
     (per-episode files under `results/androidworld/<run>/`; scripts in `analysis/failure_analysis/`);
   - the MobileWorld v4 vs v4.2 table (`results/mobileworld/mw_r3_comparison.json`);
   - the latency split (prompt vs decode) if the cited logs exist.
   Flag every number you cannot reproduce or whose source does not say what the report claims.
2. **Logic.** Does the evidence support "not epochs / not rank / not hyperparameters"? Is "more training" fairly
   tested by the fresh-rows run? Is step-level DPO on own samples at replay states correctly specified (what is
   "preferred" when the human step itself was a copied-intent `wait`? does the DPO anchor or sampling at temperature
   0.8 create train/test mismatch with temperature-0 inference? can pairs leak the evaluation sets?) Is the fallback sound?
3. **Decision rules** (the ranked plan table): are the gates pre-declared, unambiguous and hard to game? Can a
   candidate pass by stopping less often while succeeding less? Is "false complete ≤ 15" a sound single-pass gate
   given the stated 20–28 band? Is R (replicate flips) used correctly? Any multiple-comparison problem across the
   variants tried so far?
4. **Fairness and benchmark-maxxing.** Any step that tunes on MobileWorld or on seed-30 more than disclosed? Is the
   AndroidLab / ScreenSpot-v2 plan fair to GUI-Owl (same inputs, same harness)? Is the own-rollout pilot clean (app
   choice, Fossify, deduplication against AW/MW tasks)?
5. **Feasibility.** Does the budget (A100 hours, emulator hours, timeline) add up? What is most likely to break first
   (DPO trainer with LFM3-VL images, sampling speed, AndroidLab on an arm64 Mac, adb server safety)? Is anything
   missing that the owner explicitly asked about?

## Rules

- Read-only on everything outside `results/agy/v5_plan_review/` (you may write scratch files there).
- No network, no git commits or ref changes, no process signals, no emulator/adb/cloud commands.
- Never print secrets. Claims that only cite an external paper: mark "not verifiable offline" rather than guessing.

## Report

Write `results/agy/v5_plan_review/report.md`. First line exactly one of: `Verdict: GO`, `Verdict: GO AFTER FIXES`,
`Verdict: NO-GO`. Then a findings table ordered by severity: ID | severity (P1 = breaks the plan or its fairness;
P2 = material; P3 = minor) | file:line | what is wrong | evidence | exact fix. Then, briefly, what you checked and
found correct (with the numbers you recomputed).
