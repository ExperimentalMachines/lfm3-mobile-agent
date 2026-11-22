# Response to agy pass 2 (2026-11-22)

(Attempt 1 stalled on file search and produced nothing: `logs/agy_v5_plan_rereview_attempt1.log`. Attempt 2 wrote its
report to agy's own scratch folder; copied here.)

| ID | Disposition | Change (docs/PREREG_v41.md, 2026-11-22 17:00) |
|---|---|---|
| P1-1 human `wait` labels | **Valid, adopted** | States whose human step is `wait` are excluded from DPO pairs |
| P1-2 "differs" rule | **Valid in part, adopted** | A rejection requires the scorer's `match` to fail (type, 14%-radius click, text F1), so small click offsets are never rejected. Intent text similarity is *not* added: intent wording alone never makes a rejection |
| P1-3 contamination | **Valid, made explicit** | Training rows only; dev/test episodes and AndroidWorld apps excluded, with a check in the pair builder |
| P2-1 reference vs projector | **Invalid** | The projector was never trained: every v4.x run had `modules_to_save: []` (`results/v4_dev/hub/training_logs/run_config.json`; the pipeline overrides `sft_vlm.py`'s default). DPO starts from v4.2's merged weights and the reference (adapter disabled) is exactly v4.2; round 5 does not train the projector either |
| P2-2 "more training" confound | **Valid, adopted** | S now samples from v4.2's own training mix (≈43% already-seen rows) instead of fresh rows from a changed mix |
| P3-1 budget | Noted | P first; S only if credits remain |
| Q2 joint gate, v4.2 replicate | **Adopted** | Pass needs successes ≥ 16 **and** false `complete` ≤ 15, or net gain ≥ max(R, 6); R from the v4.2 replicate |
| Q1c temperature | **Changed** | Rejections come from greedy decoding (what inference does), not temperature 0.8 |
