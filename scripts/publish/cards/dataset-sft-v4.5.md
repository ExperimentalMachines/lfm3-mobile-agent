---
license: other
license_name: mixed-source-licenses
task_categories:
- image-text-to-text
language:
- en
tags:
- android
- gui-agent
- mobile-agent
- screenshot
size_categories:
- 100K<n<1M
---
# MobileAgent-SFT-v4.5

Training mix and gate splits of round 7 of [LFM3 Mobile Agent](https://github.com/experimentalmachines/lfm3-mobile-agent):
one full pass over about twice v4's data, with a **24-step text history** and **"[no visible change]" notes**.
Rules fixed in advance: [PREREG_v45.md](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/PREREG_v45.md).

## Splits

| Split | Rows | Use |
|---|---|---|
| `train` | 173,430 | Training |
| `test_ac_high` | 9,987 | AndroidControl test, high-level + terminal rows (official labels), gate |
| `dev_answer`, `dev_complete` | 136, 80 | v4's held-out episodes, gate |
| `dev_androidlens_high` | 4,987 | AndroidLens English (evaluation only, never trained on), gate |
| `dev_memgui` | 921 | MemGUI-3K test trajectories, reported |

`androidlens/` holds the files `score_androidlens.py` checks (ground truth + sha256 manifest).

## Training rows by source

| Source | Rows | Content | Licence |
|---|---|---|---|
| AndroidControl | 82,569 + 14,218 question copies | **All** high-level steps and terminal rows of the train split, minus v4's 200 held-out episodes | Apache-2.0 |
| GUI-Odyssey | 40,218 | **All** train candidates under the v2 rules (phones, no AndroidWorld apps, no terminal rows) | CC BY 4.0 |
| AMEX | 21,925 | **All** trajectory candidates under the v2 rules | CC BY 4.0 |
| MemGUI-3K | 8,505 | Long, self-correcting trajectories (round 6), rebuilt with the 24-step history | Apache-2.0 |
| ScreenQA | 5,995 | Single-screen answers (as v4) | CC BY 4.0 |

## What changed from v4

| Change | Detail |
|---|---|
| No caps | v4 used 56,000 of 87,248 AndroidControl rows and ≤ 3 rows per GUI-Odyssey / AMEX episode |
| 24-step history | v4 showed the last 8 steps; 31,216 training rows now show more than 8 |
| No-visible-change notes | A history step gets " [no visible change]" when the next screenshot is unchanged (72 × 160 grayscale, mean abs diff < 1.0) |
| Intents for blank steps | GUI-Odyssey (inconsistent) and AMEX (none) steps get the step instruction of [Aguvis stage 2](https://huggingface.co/datasets/xlangai/aguvis-stage2) (Apache-2.0) when it fits the recorded action, else a template. Click rows still blank are not targets |
| End-of-episode clean-up | 201 AndroidControl train episodes ended with a scroll or wait that changed nothing; that step was dropped |
| Duplicates | 3,055 exact duplicates removed (v4 held 3,062 navigate-then-answer rows twice) |

Images: one JPEG screenshot per row, resized as in training (≤ 880 × 880 px of area). Coordinates: 0–1000.

## Contamination

No AndroidWorld, MobileWorld or AndroidLab tasks, apps (beyond generic system apps), trajectories, checkers or seeded
content; same filters as v2–v4. Train rows sharing an image with any gate or dev split were dropped (276).
AndroidLens is a benchmark test set and is never trained on.

## Build

`data/build_v2_mix.py` (round-7 switches) and `data/v45_build_mix.py`, on an AWS EC2 CPU instance.
Statistics: `build_stats.json`.
