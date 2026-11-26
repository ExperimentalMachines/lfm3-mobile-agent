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
# MobileAgent-SFT-Counterfactual

- **Name:** `MobileAgent-SFT-Counterfactual` (formerly `MobileAgent-SFT-v4.6`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Trains:** [`LFM3-VL-2B-MobileAgent-Counterfactual`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual)

Training mix and gate splits of round 8 of [LFM3 Mobile Agent](https://github.com/experimentalmachines/lfm3-mobile-agent):
[MobileAgent-SFT-FullMix](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-FullMix) with the
**"done but not done yet"** fixes. Rules fixed in advance:
[preregistrations/round-08-done-from-the-screen.md](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/preregistrations/round-08-done-from-the-screen.md).

## Why

On the same unfinished screen, a history claiming every step was done raised a FullMix-trained model's `complete` rate
from 3.7% to 53.7%: the model judged completion from its own history, not the screen. In every demonstration the
history and the screen agree, so the history was a shortcut. This version adds rows where they disagree and fixes the
labels and notes that taught it.

## Splits

| Split | Rows | Use |
|---|---|---|
| `train` | 185,643 | Training |
| `test_ac_high` | 9,987 | AndroidControl test, high-level + terminal rows (official labels), gate |
| `dev_answer`, `dev_complete` | 136, 80 | Held-out episodes, gate |
| `dev_androidlens_high` | 4,987 | AndroidLens English (evaluation only), gate |
| `dev_memgui` | 921 | MemGUI-3K test trajectories, reported |
| `probe_*` (6 splits) | 300 each | History-reliance probes from AndroidControl **test** episodes, gate (see below) |

## Changes from FullMix

| Change | Rows |
|---|---|
| No-visible-change notes recomputed with a finer rule (360 × 800, status and navigation bars masked, > 0.02% of pixels changed); round 6's rule was wrong on 67% of its flags. Screens paired by position in the episode (AMEX and GUI-Odyssey step numbers are not positions) | notes 62,161 → 7,794 |
| `status` rows that two vision judges (Qwen3-VL-8B, then Qwen3-VL-32B with a stricter prompt) both judge visibly not done: dropped | −2,405 |
| `status` rows on a screen that is still loading or processing: relabelled `wait` | 67 |
| `wait` steps carrying a copied intent: intent set to "Wait for the screen to finish loading." | 5,616 targets, 22,309 history lines |
| **Counterfactual rows** from training episodes: *stale* (screen before the last action, that step noted "[no visible change]" → redo it), *ahead* (screen 2–3 steps before the end, full history → the action the screen needs), *short* (verified final screen, history without its last 1–2 steps → `complete`) | +7,140 / +5,266 / +2,212 |

## Probes (gate)

| Split | Changed | Correct behaviour |
|---|---|---|
| `probe_T_term` | nothing (finished screen) | `status` |
| `probe_C2_hist_cut` | finished screen, last 2 steps removed from the history | `status` |
| `probe_C0_base` | nothing (≥ 2 steps before the end) | not `status` |
| `probe_C1_hist_done` | unfinished screen, history claims every step | not `status` |
| `probe_C3_stale` | screen before the last action, full history | not `status` |
| `probe_C3n_stale_note` | as C3, last step noted "[no visible change]" | not `status` |

## Sources and licences

AndroidControl (Apache-2.0), GUI-Odyssey (CC BY 4.0), AMEX (CC BY 4.0; intents from
[Aguvis stage 2](https://huggingface.co/datasets/xlangai/aguvis-stage2), Apache-2.0), MemGUI-3K (Apache-2.0),
ScreenQA (CC BY 4.0), AndroidLens (Apache-2.0, evaluation only).

## Contamination

No AndroidWorld, MobileWorld or AndroidLab tasks, apps (beyond generic system apps), trajectories, checkers or
seeded content. AndroidWorld runs were read only to diagnose the failure; nothing from them is in this dataset.

## Build

`data/sft_counterfactual.py` on an AWS EC2 CPU instance; statistics in `build_stats.json`.
