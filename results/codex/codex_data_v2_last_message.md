Wrote [codex_data_v2_audit.md](/Users/alpha/lfm3-android/results/codex/codex_data_v2_audit.md).

**NO-GO for training.** Confirmed five train/dev screenshot leaks, premature completion labels, incorrect AMEX supervision, and an AndroidWorld typing/Enter mismatch.

Checked **16,999 rows** and visually reviewed **40 random rows per new source**, plus targeted examples. Used exactly three train shards and all dev splits; downloads remain in the gitignored cache.

The report includes 12 findings with severity, evidence, exact fixes, and reproducible audit scripts.