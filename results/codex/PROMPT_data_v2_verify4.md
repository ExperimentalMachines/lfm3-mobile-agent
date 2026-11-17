Fourth, NARROW verification of the v2 SFT mix. Your third report results/codex/codex_data_v2_verify3.md found exactly two
blocking defects (B1 false keyboard-submit merges; B2 control/selection drags converted to scroll) and judged the
remaining source-label noise non-blocking. The builder was changed only for those (`git diff HEAD~1 -- data/build_v2_mix.py`
shows `keyboard_tap_kind`, `DRAG_WORDS_RE`, the stricter `swipe_dir`, and the Odyssey/AMEX loop changes) and GUI-Odyssey,
AMEX and the merge were rebuilt. Pinned DATA revision: `experimentalmachines/AndroidAgent-SFT-v2` @
42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a. Stats: results/data_v2/stats.json; logs results/data_v2/build_*.log.

Check only:
1. B1: re-run your actual-loop fixtures (TEXT -> "hide the keyboard" -> result tap; toolbar-above-keyboard; suggestion
   tap; genuine bottom-right Enter/Search) against the current code, and confirm the published examples
   5994133452263654 (WPS), 4912446279173881, 6951686067814574 no longer have rows whose history omits a deleted
   non-submit action (they should now be cut at that tap). Spot-check >= 15 published rows that follow a submit merge.
2. B2: confirm 4394352513523177/22, 0173202679441530/21 (dev) and 4143524179769456/4 are no longer published as scrolls,
   and visually review >= 15 published new-source scroll rows for control drags.
3. Confirm nothing else regressed: pinned stats every-row assertions, train/dev image overlap 0, caps, job pin
   (scripts/jobs/lfm3_v2mix_g4.json and qwen35_2b_v2mix_g4.json now pin 42f7f763...).
Use at most 2 train shards + the dev splits at the pinned revision (reuse results/codex/data_v2_cache).
Write results/codex/codex_data_v2_verify4.md: B1/B2 status table and a final GO / NO-GO for training LFM3-VL-2B and
Qwen3.5-2B on this revision with the v1 recipe.
