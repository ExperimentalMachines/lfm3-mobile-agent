Wrote [codex_data_v2_verify3.md](/Users/alpha/lfm3-android/results/codex/codex_data_v2_verify3.md).

**NO-GO for both models** on `836e401958` with the v1 recipe. Two blockers remain:

- Submit merging deletes real non-submit actions while retaining dependent observations.
- Clock-hand and text-selection drags become incompatible generic scrolls.

Checked **21,833 rows** from four unused train shards plus all dev splits; visually reviewed **32 random rows per new source**. Residual source-label noise—2 clear errors and 4 uncertain cases among 96—was not the reason for rejection.