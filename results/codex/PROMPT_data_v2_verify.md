Re-verify the v2 SFT mix after fixes. Your previous audit is results/codex/codex_data_v2_audit.md (NO-GO, findings
F1-F12). The builder data/build_v2_mix.py was changed (see `git diff 2af34de -- data/build_v2_mix.py`) and the dataset
was rebuilt and re-pushed: HF dataset `experimentalmachines/AndroidAgent-SFT-v2`, revision d33cb3c217 (pin it). New
build stats/logs: results/data_v2/stats.json (includes `full_dataset_assertions` computed over EVERY row on the builder
machine) and results/data_v2/build_*.log; card results/data_v2/README.md. Reuse your cache/scripts under
results/codex/ (HF_HOME under results/codex/data_v2_cache; token at ~/.cache/huggingface/token). Download at most 4
train shards (choose different shard indices than last time) plus all dev splits.

For each finding F1-F12: state FIXED / PARTIALLY FIXED / NOT FIXED with evidence from the new revision (re-run your
leak hashing across all downloaded train vs all dev rows, the executor probe reasoning for type+Enter, scroll-band rule
vs the dropdown example, key-text and typo checks, terminal OCR/goal rules, app-alias policy, per-episode caps, AMEX
blank intents, duplicates, frame mismatch). Re-review >= 30 random rows per new source visually. Flag any NEW problem
introduced by the fixes (e.g. history now referencing dropped steps, empty-intent rendering, quota shortfalls,
over-filtering that removes most scrolls). Note what is a documented policy choice vs a defect.

Write results/codex/codex_data_v2_verify.md: per-finding table, new issues, and a final GO / NO-GO for training
LFM3-VL-2B on this revision with the v1 recipe (1,250 steps x 32 rows, equal budget vs v1).
