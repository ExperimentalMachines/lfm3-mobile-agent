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
# MobileAgent-SFT-v4.7

Training mix and gate splits of round 9 of [LFM3 Mobile Agent](https://github.com/experimentalmachines/lfm3-mobile-agent):
[MobileAgent-SFT-v4.6](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v4.6) with the
**useless-wait** fixes. Rules fixed in advance:
[PREREG_v47.md](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/PREREG_v47.md).

## Why

On AndroidWorld, a v4.5-trained model spent 17% of its steps on `wait`, and 83% of those waits changed nothing on the
screen; 39% of its waits followed another wait. The "[no visible change]" note never marked a `wait` step, so after a
useless wait the model saw the same screen and an unmarked wait line, and waited again. The wait labels themselves are
mostly right: checked with before/after screen pairs, most waits sit on a screen that is still loading.

## Splits

| Split | Rows | Use |
|---|---|---|
| `train` | 192,143 | Training (full mix) |
| `train_f` | 32,000 | Candidate F's continuation mix: every new counterfactual and relabelled row, the rest drawn from `train` |
| `test_ac_high` | 9,987 | AndroidControl test, high-level + terminal rows (official labels), gate |
| `dev_answer`, `dev_complete` | 136, 80 | Held-out episodes, gate |
| `dev_androidlens_high` | 4,987 | AndroidLens English (evaluation only), gate |
| `dev_memgui` | 921 | MemGUI-3K test trajectories, reported |
| `probe_*` (6 splits) | 300 each | Round 8's history-reliance probes, with wait notes |
| `probe_W0_base`, `probe_W1_nwait`, `probe_W2_loading` | 300 each | Wait probes from AndroidControl **test** episodes (see below) |

## Changes from v4.6

| Change | Rows |
|---|---|
| History lines of `wait` steps get " [no visible change]" when the next screen is unchanged (the v4.6 rule) | 611 train history lines |
| A `wait` that the human followed with an action on the unchanged screen takes that action as its label | 63 (AndroidControl 59, MemGUI 4); a wait before `complete` only if that `complete` row was judged visibly done |
| **nwait** rows: a screen the human acted on + its history + 1–2 appended waits noted "[no visible change]" → the human's action | +5,000 (1,243 with two waits) |
| **nwaitload** rows: a real loading screen (a wait whose next screen changed and whose next action is a real action, not `complete`) + the same appended waits → `wait` | +1,500 (368 with two waits) |

## Wait probes

| Split | Screen | Correct behaviour |
|---|---|---|
| `probe_W0_base` | screens where the human acted, unchanged | the action, not `wait` |
| `probe_W1_nwait` | the same rows after one appended wait that changed nothing | the action, not `wait` |
| `probe_W2_loading` | real waits whose next screen changed (still loading) | `wait` |

## Sources and licences

AndroidControl (Apache-2.0), GUI-Odyssey (CC BY 4.0), AMEX (CC BY 4.0; intents from
[Aguvis stage 2](https://huggingface.co/datasets/xlangai/aguvis-stage2), Apache-2.0), MemGUI-3K (Apache-2.0),
ScreenQA (CC BY 4.0), AndroidLens (Apache-2.0, evaluation only).

## Contamination

No AndroidWorld, MobileWorld or AndroidLab tasks, apps (beyond generic system apps), trajectories, checkers or
seeded content. AndroidWorld runs were read only to diagnose the failure; nothing from them is in this dataset.

## Build

`data/v47_build.py` and `data/v47_cont_mix.py` on an AWS EC2 CPU instance; statistics in `build_stats.json`.
