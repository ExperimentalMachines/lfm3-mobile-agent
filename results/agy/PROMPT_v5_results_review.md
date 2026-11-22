# Adversarial review: round-5 results, gate decisions and docs (before merge)

You are an independent, skeptical reviewer. The working directory is a git checkout of branch `v41-followup` of an
Android GUI-agent project. Round 5 trained three candidates from v4.2 under gates fixed in advance. Check that the
gates were applied exactly as declared, that every number in the docs reproduces from the repo files, and that no
claim says more than the evidence.

## Read

- Pre-registration log: [`docs/PREREG_v41.md`](../../docs/PREREG_v41.md), entries from "2026-11-22 17:00" onward
  (plan and gates), through the last entry.
- Docs changed this round: [`docs/results.md`](../../docs/results.md) section "Round 5…",
  [`docs/models.md`](../../docs/models.md) (v4.3 rows, released artifacts),
  [`docs/research/training-scale-and-own-attempt-learning.md`](../../docs/research/training-scale-and-own-attempt-learning.md)
  section "Round 5 as executed", model cards `scripts/publish/cards/v4.3-*.md`.
- Analysis scripts: `analysis/aw_false_complete.py`, `analysis/aw_paired_flips.py`.
- Raw data: per-episode files `results/androidworld/<run>/run_*/*.pkl.gz` for runs `lfm3vl2b_v42` (E),
  `lfm3vl2b_v42_rep`, `lfm3vl2b_v43dpo2` (P2), `lfm3vl2b_v43sft` (S); offline gate files in `results/v5_dev/`;
  training code `train/dpo_vlm.py`, `train/sft_vlm.py`, `data/v5_pairs.py`, `scripts/training/vm_v5_pipeline.sh`.
- Publishing: `scripts/publish/local_quantize_publish.sh` (new `publish-only` mode).

You may run the two analysis scripts with `.venv-aw/bin/python -I analysis/<script>.py results/androidworld/<run> ...`
(the episode files are pickles written by this repo's own harness).

## Answer concretely (cite file:line)

1. **Numbers.** Recompute successes, exceptions, false `complete`s and paired flips vs E for every run; the stop
   counts quoted for P2 (44 episodes ending with `complete`, 16 right, 28 wrong, precision 0.36; v4.2 37–38, 0.34/0.41);
   the offline gate values. Flag any number that does not reproduce.
2. **Gate application.** Were the declared gates applied exactly (thresholds, exceptions counted as failures, the
   tie-break order, "passing makes a held-out candidate, not a claim")? Were any gate parameters changed after an
   outcome was seen? P2 and the S step cut (800 → 500) were declared post-hoc: is each declared before the outcome it
   could have been tuned to, per the log's timestamps and the git history (`git log --format='%h %ad %s' -- docs/PREREG_v41.md`)?
3. **Definitions.** Is "success" the same in both scripts (`is_successful >= 1` vs `> 0`)? Does it matter for any count?
   Is the false-`complete` definition identical to the one declared (taxonomy primary category)?
4. **Claims.** Does any doc or card claim an improvement, a cause or a mechanism that the data does not support (e.g.
   the explanation of why P2's stop training did not transfer)? Are inferences labelled as inference?
5. **Disclosure.** Is everything that could bias the result disclosed (void passes, the Mac reboot and checkpoint
   resume, emulator cold boots, E's 9 exceptions vs the replicate's 2)? Does the resume after the reboot change the
   protocol for any episode?
6. **Publishing.** Do the cards match the evidence (status lines, numbers, links that exist)? Does the `publish-only`
   mode publish exactly the GGUF that was evaluated (check the sha256 printed in `logs/local_v41_dev_aw.log` against
   `results/v43-*_gguf_manifest.json`)?

## Rules

- Read-only on everything outside `results/agy/v5_results_review/` (create it; you may write scratch files there).
- No network, no git commits or ref changes, no process signals, no emulator/adb/cloud commands.
- Never print secrets.

## Report

Write `results/agy/v5_results_review/report.md`. First line exactly one of: `Verdict: GO`, `Verdict: GO AFTER FIXES`,
`Verdict: NO-GO` (GO = the branch can be merged as is). Then a findings table ordered by severity: ID | severity
(P1 = a wrong gate decision or a false claim; P2 = material; P3 = minor) | file:line | what is wrong | evidence |
exact fix. Then one line per question above with your answer and the numbers you recomputed.
