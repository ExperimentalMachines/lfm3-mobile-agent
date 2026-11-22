# Adversarial review, pass 2: the plan's logic, decision rules, fairness and feasibility

You are an independent, skeptical reviewer. The working directory is a git checkout of branch `v41-followup`.
Pass 1 (`results/agy/v5_plan_review/report.md`, our response in `results/agy/v5_plan_review/response.md`) only
checked numbers. This pass must attack the **plan** in
[`docs/research/training-scale-and-own-attempt-learning.md`](../../docs/research/training-scale-and-own-attempt-learning.md)
(sections "Own mistakes teach most…", "Ranked plan…", "Skip, and why"). Do not repeat pass-1 findings unless our
response is wrong; if you think it is, say why with evidence.

Context and constraints: as in [`results/agy/PROMPT_v5_plan_review.md`](PROMPT_v5_plan_review.md). Relevant code:
`train/sft_vlm.py` (note `modules_to_save=["multi_modal_projector"]`), `train/grpo_vlm.py`, `data/v42_selfhist.py`,
`data/v41_build_parquet.py`, `scripts/training/vm_v42_pipeline.sh`, `scripts/androidworld/local_v41_dev_aw.sh`.

## Answer each question concretely (cite file:line)

1. **Step-DPO specification.** Preferred = human step, rejected = an own sample that differs, at v4.2's replay states.
   (a) When the human step is itself a poor label (AndroidControl copied-intent `wait`, relabelled in v4.1), does DPO
   push the model toward bad behaviour? Should such states be excluded? (b) "Differs" by what rule: action type,
   coordinates outside the target element, intent text only? Rejecting a correct click that lands 5 px away from the
   human's click would teach noise — what match rule avoids that? (c) Sampling at temperature 0.8 vs temperature-0
   inference: does it matter for DPO pairs? (d) Reference model = v4.2 with the LoRA disabled; any problem given the
   projector is trained in full (`modules_to_save`)? (e) Can any pair come from a dev/test split or an
   AndroidWorld/MobileWorld app?
2. **Gates.** For rank 3 (offline + online gates) and rank 5 (fresh rows): can a candidate pass by stopping less often
   while succeeding less? Is "false complete ≤ 15" achievable just by never stopping (budget exhaustion instead)? Should
   there be a joint rule (e.g. successes ≥ v4.2's 18 − R, and false completes down)? Is R (flips in a v4 replicate) the
   right noise yardstick when the candidate is v4.2-based — should the replicate be v4.2 instead of v4?
3. **"More training" test.** Does the fresh-rows run (never-seen rows, WSD, 60% branch) fairly answer the owner's
   "train more epochs" question? What confound exists (new rows change the data mix as well as the amount)?
4. **Fairness / benchmark-maxxing.** Anything in the plan that tunes on MobileWorld or on seed 30 beyond what is
   disclosed? Is the AndroidLab and ScreenSpot-v2 comparison fair to GUI-Owl? Is the own-rollout pilot clean?
5. **Feasibility and ordering.** Given ~5 A100-hours (Colab, about 4 rows/s for SFT), what should be cut first if
   the DPO path fails its smoke test? Is anything the owner asked about missing (they asked for "more training over
   epochs", "learn from its own attempts", "bigger LoRA?", "something in between?", "hyperparameters?", speed vs
   quality, data variety, benchmarks, overfitting)?

## Rules

Read-only outside `results/agy/v5_plan_rereview/`. No network, no git commits or ref changes, no process signals, no
emulator/adb/cloud commands. Never print secrets.

## Report

Write `results/agy/v5_plan_rereview/report.md` (create the folder). First line exactly one of `Verdict: GO`,
`Verdict: GO AFTER FIXES`, `Verdict: NO-GO`. Then a findings table ordered by severity: ID | severity (P1/P2/P3) |
file:line | what is wrong | evidence | exact fix. Then one line per question above with your answer.
