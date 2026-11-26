---
license: apache-2.0
task_categories:
- image-text-to-text
language:
- en
tags:
- android
- gui-agent
- mobile-agent
- long-horizon
configs:
- config_name: default
  data_files:
  - split: memgui_train
    path: data/memgui_train-*.parquet
  - split: dev_memgui
    path: data/dev_memgui-*.parquet
---

# MobileAgent-SFT-MemGUI (new rows only)

- **Name:** `MobileAgent-SFT-MemGUI` (formerly `MobileAgent-SFT-v4.4`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Trains:** [`LFM3-VL-2B-MobileAgent-Dev-MemGUI`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MemGUI), [`LFM3-VL-2B-MobileAgent-Dev-MemGUIChangeNotes`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MemGUIChangeNotes), [`LFM3-VL-2B-MobileAgent-Dev-MemGUIContinuedSFT`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MemGUIContinuedSFT)

The rows that round 6 (MemGUI) of [LFM3 Mobile Agent](https://github.com/experimentalmachines/lfm3-mobile-agent) adds to
[MobileAgent-SFT](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT). The training mixes
themselves are built from these rows plus Main's at training time by `data/sft_memgui_mix.py` (deterministic, seed 44).

| Split / folder | What | Rows | Use |
|---|---|---|---|
| `memgui_train` | [lgy0404/MemGUI-3K](https://huggingface.co/datasets/lgy0404/MemGUI-3K) train trajectories, converted to Main's format | 8505 | Training |
| `dev_memgui` | MemGUI-3K test trajectories, same conversion | 921 | Development check |
| `androidlens/` | [AndroidLens](https://huggingface.co/datasets/yuecao0119/AndroidLens) English test episodes (172, about 26 steps each), high- and low-level | 4,987 per split | **Evaluation only. Never train on these rows** |

## MemGUI rows

- **Source:** MemGUI-3K @ `003822b5aa3d5450232b8e6305d3094f564a1cf1` (Apache-2.0).
- **Kept trajectories:** only successful, feasible ones.
- **Targets:** the steps MemGUI' judge rated reasonable.
- **Recovery:** unreasonable steps stay in the history, so many rows show a mistake followed by the right next step.
- **Removed:** memory ("ConAct") actions; and answer rows, because their answers are full sentences.
- **Contamination filter:** no AndroidWorld, MobileWorld or AndroidLab tasks, apps or trajectories.
  - Dropped: Joplin and Audio Recorder (AndroidWorld), Bluecoins and calendar apps (AndroidLab), Messages / SMS
    (MobileWorld).
  - Kept, generic system apps: Settings, Clock, Chrome, Contacts, Files.
- **Intents:** the agent's own decision sentence, written before its action, shortened. Calculator keys are named from
  the tap position.
- **Known differences from AndroidWorld screenshots:**
  - Android's pointer-location overlay and touch trails are visible.
  - Typing does not press Enter.
- **Full counts and drop reasons:** `data/v44work/memgui_stats.json` from `data/sft_memgui_rows.py`.

## AndroidLens rows (evaluation only)

- **Source:** AndroidLens @ `984576f3eb733f27cd18479b7b20e18565e98dda` (Apache-2.0), English test episodes, converted by
  `data/eval_androidlens.py`.
- **Ground truth:** AndroidLens's alternative valid actions are kept in `gt_alternatives`.
- **Scoring:** `eval/androidlens/score_androidlens.py`, which checks `androidlens/manifest.json` (sha256) first.
- **Never train on these rows.** They exist to test long tasks.

## License

- **Licence:** Apache-2.0, as both sources.
- **Attribution:** MemGUI-3K (Liu et al., 2026) and AndroidLens (Cao et al.). The screenshots come from these sources.
