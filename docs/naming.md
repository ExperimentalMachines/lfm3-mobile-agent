# Naming

One scheme names every model, dataset, phone format and script. It replaced the earlier version numbers and letters
(`v4.3-dpo2`, `v4.4-A`, `v4.6-E`, `MobileAgent-SFT-v4.5`, ...) on 2026-11-26.

**Contents:** [The scheme](#the-scheme) · [Glossary](#recipe-glossary) · [Models](#models) · [Datasets](#datasets) ·
[Candidates that were never published](#candidates-that-were-never-published) · [What keeps a version number](#what-keeps-a-version-number) ·
[Files that were renamed](#files-that-were-renamed) · [Records keep the old names](#records-keep-the-old-names) · [Adding a name](#adding-a-name)

---

## The scheme

```
Model    <Base>-MobileAgent[-<Variant> | -Dev-<Recipe>][-<Format>]
Dataset  MobileAgent-<Kind>[-<Recipe>]
```

| Part | Meaning |
|---|---|
| `<Base>` | The upstream model, unchanged: `LFM3-VL-2B`, `Qwen3.5-2B`, `Qwen3.5-0.8B`, `LFM2.5-VL-450M` |
| *(nothing)* | **The recommended model.** Only `LFM3-VL-2B-MobileAgent` has this form (called *Main* in the docs): the model evaluated on the held-out AndroidWorld seeds |
| `-<Variant>` | An **evaluated alternative**, documented and benchmarked, **not** a recommendation over Main. Today: `-Counterfactual` |
| `-Dev-<Recipe>` | A **development checkpoint**, kept so results can be reproduced. Not recommended |
| `<Recipe>` | A CamelCase tag for **what was added** to its parent's recipe (initialisation and recipe parent are in [Models](#models)). Same tag on a model and its dataset |
| `<Format>` | `GGUF` (4-bit, llama.cpp) or `LiteRT` (int8, phone GPU). Safetensors repos carry no format suffix |
| `<Kind>` | `SFT` (supervised rows) or `RL` (states for reinforcement learning) |

Rules: a name never contains a version number or a letter code; a tag is never reused for a different recipe (a re-run
of the same recipe is a Hugging Face revision, not a new name); one dataset can feed several models (for example
`MobileAgent-SFT-MemGUI` feeds three `-Dev-MemGUI*` models, mixed with Main's rows at training time), so the
dataset tag and the model tag match only where there is one model per dataset.

---

## Recipe glossary

| Tag | What it means |
|---|---|
| `AndroidControlOnly` | Supervised fine-tuning on AndroidControl's official training episodes only |
| `MultiSource` | + GUI-Odyssey, AMEX and ScreenQA (the mix had 8,739 rows with a blank intent) |
| `FilledIntents` | `MultiSource` with the blank intents filled (action templates + a teacher model) |
| *(none)* | `FilledIntents` data in the final prompt (answer-vs-complete rules, installed-app list) + navigate-then-answer episodes + shorter ScreenQA answers |
| `GRPO` | Reinforcement learning (GRPO) on static screenshots, 200 steps |
| `WaitRelabel` | Copied `wait` intents relabelled, with recovery-history augmentation |
| `OwnHistory` | `WaitRelabel` + the model's own replayed history on training episodes (offline, DAgger-style) |
| `DPOAllMistakes` / `DPOStopMistakes` | DPO on all of `OwnHistory`'s own mistakes / on a balanced set of its stop and copied-intent mistakes |
| `ContinuedSFT` | `OwnHistory` + 500 more SFT steps on the same mix |
| `MemGUI` | + MemGUI long, self-correcting trajectories (MemGUI-3K) |
| `MemGUIChangeNotes` | `MemGUI` + "[no visible change]" notes in the history |
| `MemGUIContinuedSFT` | Main + 500 steps on 50% MemGUI / 50% Main rows |
| `FullMix` | One pass over all candidate sources (no per-episode caps), 24-step history with change notes. "Full" means all the sources this project used, not every dataset that exists |
| `Counterfactual` | `FullMix` + rows where the history and the screen disagree, with judge-checked "done" labels |
| `Counterfactual-WaitFix` (dataset only) | `Counterfactual` + rows against useless waits; built, never trained on |

---

## Models

| Name | Old label | Tier | Initialised from | Recipe builds on | What it adds |
|---|---|---|---|---|---|
| [`LFM3-VL-2B-MobileAgent-Dev-AndroidControlOnly`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-AndroidControlOnly) | v1 | dev | the base model | — | SFT on AndroidControl only (official train episodes) |
| [`LFM3-VL-2B-MobileAgent-Dev-MultiSource`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MultiSource) | v2 | dev | the base model | `LFM3-VL-2B-MobileAgent-Dev-AndroidControlOnly` | + GUI-Odyssey, AMEX, ScreenQA (8,739 rows with a blank intent) |
| [`LFM3-VL-2B-MobileAgent-Dev-FilledIntents`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-FilledIntents) | v3 | dev | the base model | `LFM3-VL-2B-MobileAgent-Dev-MultiSource` | the blank intents filled (templates + a teacher model) |
| [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) | v4 | main | the base model | `LFM3-VL-2B-MobileAgent-Dev-FilledIntents` | the FilledIntents data in the final prompt (answer-vs-complete rules, installed-app list) + navigate-then-answer episodes + shorter ScreenQA answers |
| [`LFM3-VL-2B-MobileAgent-Dev-GRPO`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-GRPO) | v4-RL | dev | `LFM3-VL-2B-MobileAgent` | `LFM3-VL-2B-MobileAgent` | 200 GRPO steps on static screenshots |
| [`LFM3-VL-2B-MobileAgent-Dev-WaitRelabel`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-WaitRelabel) | v4.1 | dev | the base model | `LFM3-VL-2B-MobileAgent` | copied `wait` intents relabelled + recovery-history augmentation |
| [`LFM3-VL-2B-MobileAgent-Dev-OwnHistory`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory) | v4.2 | dev | the base model | `LFM3-VL-2B-MobileAgent-Dev-WaitRelabel` | + the model's own replayed history on training episodes |
| [`LFM3-VL-2B-MobileAgent-Dev-DPOAllMistakes`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-DPOAllMistakes) | v4.3-dpo | dev | `LFM3-VL-2B-MobileAgent-Dev-OwnHistory` | `LFM3-VL-2B-MobileAgent-Dev-OwnHistory` | DPO on all 4,163 of its own mistakes |
| [`LFM3-VL-2B-MobileAgent-Dev-DPOStopMistakes`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-DPOStopMistakes) | v4.3-dpo2 | dev | `LFM3-VL-2B-MobileAgent-Dev-OwnHistory` | `LFM3-VL-2B-MobileAgent-Dev-OwnHistory` | DPO on 851 balanced stop / copied-intent mistakes |
| [`LFM3-VL-2B-MobileAgent-Dev-ContinuedSFT`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-ContinuedSFT) | v4.3-sft | dev | `LFM3-VL-2B-MobileAgent-Dev-OwnHistory` | `LFM3-VL-2B-MobileAgent-Dev-OwnHistory` | 500 more SFT steps on the same mix |
| [`LFM3-VL-2B-MobileAgent-Dev-MemGUI`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MemGUI) | v4.4-A | dev | the base model | `LFM3-VL-2B-MobileAgent` | + MemGUI long, self-correcting trajectories |
| [`LFM3-VL-2B-MobileAgent-Dev-MemGUIChangeNotes`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MemGUIChangeNotes) | v4.4-B | dev | the base model | `LFM3-VL-2B-MobileAgent-Dev-MemGUI` | + "[no visible change]" notes in the history |
| [`LFM3-VL-2B-MobileAgent-Dev-MemGUIContinuedSFT`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MemGUIContinuedSFT) | v4.4-C | dev | `LFM3-VL-2B-MobileAgent` | `LFM3-VL-2B-MobileAgent` | 500 more steps on 50% MemGUI / 50% main-model rows |
| [`LFM3-VL-2B-MobileAgent-Dev-FullMix`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-FullMix) | v4.5-D | dev | the base model | `LFM3-VL-2B-MobileAgent` | one pass over all candidate sources, 24-step history, change notes |
| [`LFM3-VL-2B-MobileAgent-Counterfactual`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual) | v4.6-E | variant | the base model | `LFM3-VL-2B-MobileAgent-Dev-FullMix` | + rows where history and screen disagree; judge-checked "done" labels |
| [`Qwen3.5-2B-MobileAgent-Dev-AndroidControlOnly`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-Dev-AndroidControlOnly) | Qwen3.5-2B v1 | dev | the base model | — | same recipe family as the LFM3 model of that tag |
| [`Qwen3.5-2B-MobileAgent-Dev-MultiSource`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-Dev-MultiSource) | Qwen3.5-2B v2 | dev | the base model | — | same recipe family as the LFM3 model of that tag |
| [`Qwen3.5-0.8B-MobileAgent-Dev-AndroidControlOnly`](https://huggingface.co/experimentalmachines/Qwen3.5-0.8B-MobileAgent-Dev-AndroidControlOnly) | Qwen3.5-0.8B v1 | dev | the base model | — | same recipe family as the LFM3 model of that tag |
| [`LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly`](https://huggingface.co/experimentalmachines/LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly) | LFM2.5-VL-450M v1 | dev | the base model | — | same recipe family as the LFM3 model of that tag |

Phone formats: append `-GGUF` or `-LiteRT` to the model name (GGUF repos exist for the models listed in [models.md](models.md#released-artifacts); `-LiteRT` only for Main).

## Datasets

| Name | Old name | Trains |
|---|---|---|
| [`MobileAgent-SFT-AndroidControl`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-AndroidControl) | MobileAgent-SFT-v1 | `-Dev-AndroidControlOnly` (+ comparison models) |
| [`MobileAgent-SFT-MultiSource`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-MultiSource) | MobileAgent-SFT-v2 | `-Dev-MultiSource` |
| [`MobileAgent-SFT-FilledIntents`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-FilledIntents) | MobileAgent-SFT-v3 | `-Dev-FilledIntents` |
| [`MobileAgent-SFT`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT) | MobileAgent-SFT-v4 | Main |
| [`MobileAgent-RL`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-RL) | MobileAgent-RL-v4 | `-Dev-GRPO` |
| [`MobileAgent-SFT-MemGUI`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-MemGUI) | MobileAgent-SFT-v4.4 | `-Dev-MemGUI`, `-Dev-MemGUIChangeNotes`, `-Dev-MemGUIContinuedSFT` |
| [`MobileAgent-SFT-FullMix`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-FullMix) | MobileAgent-SFT-v4.5 | `-Dev-FullMix` |
| [`MobileAgent-SFT-Counterfactual`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-Counterfactual) | MobileAgent-SFT-v4.6 | `-Counterfactual` |
| [`MobileAgent-SFT-Counterfactual-WaitFix`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-Counterfactual-WaitFix) | MobileAgent-SFT-v4.7 | nothing yet |

## Deleted repositories

Two intermediate training-checkpoint repos were deleted on 2026-11-26 (`LFM3-VL-2B-MobileAgent-v4.5-D-ckpt`, `LFM3-VL-2B-MobileAgent-v4.6-E-ckpt`, i.e. the checkpoints of `-Dev-FullMix` and `-Counterfactual`): their final adapters are byte-identical to `lora_adapter/` of the final repos; only optimizer states were lost.

## Candidates that were never published

Round candidates that failed their gates before upload. They exist only in the documentation and the preregistration logs.
The letters of those rounds (`E`, `E-DPO`, ...) are `Counterfactual` plus what the round added:

| Name used in the docs | Old label | Round |
|---|---|---|
| `Counterfactual+StopDPO` | E-DPO | 10 |
| `Counterfactual+Endings` | E-T | 11 |
| `Counterfactual+DoneCheck` | E-V | 12 |
| `Counterfactual+OwnHistoryRL (stopped)` | E-S | 13 |
| `Counterfactual+OwnHistoryRL` | E-S2 | 14 |
| `Counterfactual+OwnHistorySFT` | E-D | 14 |
| `Counterfactual-WaitFix (never trained)` | F | 9 |

## What keeps a version number

Some `v4`-style tokens are **format or schema versions**, not model names, and were left alone:

| Token | What it is |
|---|---|
| `prompt_version="v4"` (also `v1`..`v5` in `train/agent_format.py`, `"prompt_version": "v4"` in the LiteRT `model.json`) | The system-prompt / user-text format. Main and the models that followed use format `v4` |
| `V4REF` | The evaluation path that renders Main's prompt for every candidate (round 6) |
| `SYSTEM_PROMPT_V4` | The same prompt format, in the LiteRT card's example |
| Round numbers (`round 8`, `sm_r14.sh`) | Chronology; they stay |
| Probe names (`C1`, `C3n`, `M_done`, `T`, ...) | Offline probes defined in [rounds.md](rounds.md) |

Earlier names (before the `MobileAgent` rename on 2026-11-23, e.g. `LFM3-VL-2B-AndroidControl`, `…-AndroidAgent-v4`,
`AndroidAgent-SFT-v3`) still redirect, to the current names.

## Files that were renamed

Hugging Face redirects repo names but **not file names**. Inside the GGUF and LiteRT repos the files were renamed to match
the repo (bytes unchanged; every LFS hash is identical, see [models.md](models.md#integrity-records)):

| Old file | New file |
|---|---|
| `LFM3-VL-2B-MobileAgent-v4-Q4_K_M.gguf` | `LFM3-VL-2B-MobileAgent-Q4_K_M.gguf` |
| `LFM3-VL-2B-MobileAgent-v4.6-E-Q4_K_M.gguf` | `LFM3-VL-2B-MobileAgent-Counterfactual-Q4_K_M.gguf` |
| `LFM3-VL-2B-MobileAgent-v4_int8_g1280x576_ctx4096.litertlm` | `LFM3-VL-2B-MobileAgent_int8_g1280x576_ctx4096.litertlm` (and `model.json`'s `file` field) |
| `mmproj-Qwen3.5-2B-MobileAgent-v2-F16.gguf` | `mmproj-Qwen3.5-2B-MobileAgent-Dev-MultiSource-F16.gguf` |
| every other `<old repo>-Q4_K_M.gguf` | `<new repo>-Q4_K_M.gguf` (the LFM3 vision projector `mmproj-LFM3-VL-2B-Q8_0.gguf` is unchanged) |

## Records keep the old names

`results/`, `logs/`, `docs/reviews/`, `docs/research/`, `docs/audits.md`, `docs/history-rewrites.md` and the
preregistrations are **records**: they say what was true when they were written, so their text and file names still use
the old labels (`results/v46_dev/`, `lfm3vl2b_v45d`, `E-DPO`, ...). Only the preregistration files were renamed (link
targets repaired, text untouched). This is how to read them:

| Record name | Means |
|---|---|
| `results/v2_dev/`, `v3_dev/`, `v4_dev/`, `v4rl_dev/` | development-split predictions of `-Dev-MultiSource`, `-Dev-FilledIntents`, Main, `-Dev-GRPO` |
| `results/v41_dev/`, `v42_dev/`, `v42/` | `-Dev-WaitRelabel`, `-Dev-OwnHistory` (and its data build) |
| `results/v5_dev/` | round 5: `-Dev-DPOAllMistakes`, `-Dev-DPOStopMistakes`, `-Dev-ContinuedSFT` |
| `results/v44_dev/` | round 6: `-Dev-MemGUI`, `-Dev-MemGUIChangeNotes`, `-Dev-MemGUIContinuedSFT` |
| `results/v45_dev/` | round 7: `-Dev-FullMix` |
| `results/v46_dev/`, `v47_dev/` | round 8 (`-Counterfactual`) and round 9 (`Counterfactual-WaitFix` data) |
| `results/v48_dev/` | round 10 (stop-DPO, the judge) |
| `results/r11_dev/` … `r14_dev/` | rounds 11–14 |
| `results/androidworld/lfm3vl2b_v4`, `…_v41`, `…_v42`, `…_v43dpo`, `…_v43dpo2`, `…_v43sft`, `…_v44a/b/c`, `…_v45d`, `…_v46e`, `…_v4rl` | AndroidWorld seed-30 runs of Main, `WaitRelabel`, `OwnHistory`, `DPOAllMistakes`, `DPOStopMistakes`, `ContinuedSFT`, `MemGUI*`, `FullMix`, `Counterfactual`, `GRPO` |
| `results/androidworld/lfm3vl2b_ft`, `lfm3vl2b_v2`, `lfm3vl2b_v3` | `-Dev-AndroidControlOnly`, `-Dev-MultiSource`, `-Dev-FilledIntents` |
| `results/androidworld_sealed/v4_seed*`, `v1_seed*`, `e_seed*` | held-out runs of Main, `-Dev-AndroidControlOnly`, `-Counterfactual` |
| `models/lfm3vl2b_v46e-GGUF` etc. (git-ignored local folders) | the local GGUF folders of the same models; scripts still read these paths |

### Preregistrations

| Old file | New file |
|---|---|
| `docs/PREREG_v4.md` | `docs/preregistrations/heldout-main-vs-gui-owl.md` |
| `docs/PREREG_v41.md` | `docs/preregistrations/mobileworld-followup-waitrelabel.md` |
| `docs/PREREG_v44.md` | `docs/preregistrations/round-06-long-trajectories.md` |
| `docs/PREREG_v45.md` | `docs/preregistrations/round-07-full-mix-long-history.md` |
| `docs/PREREG_v46.md` | `docs/preregistrations/round-08-done-from-the-screen.md` |
| `docs/PREREG_v47.md` | `docs/preregistrations/round-09-useless-waits.md` |
| `docs/PREREG_v48.md` | `docs/preregistrations/round-10-multi-part-false-completes.md` |
| `docs/PREREG_v49.md` | `docs/preregistrations/round-11-checked-endings.md` |
| `docs/PREREG_v410.md` | `docs/preregistrations/round-12-done-check.md` |
| `docs/PREREG_v411.md` | `docs/preregistrations/round-13-yardstick-own-history.md` |
| `docs/PREREG_v412.md` | `docs/preregistrations/round-14-own-history-vs-control.md` |

### Code

Scripts were renamed to follow the dataset or model they build; their docstrings still quote the old labels they were
written under.

| Old path | New path |
|---|---|
| `data/build_androidcontrol.py` | `data/sft_androidcontrol.py` |
| `data/build_v2_mix.py` | `data/sft_multisource.py` |
| `data/vm_v3_intents.py` | `data/sft_filledintents_intents.py` |
| `data/v3_build_parquet.py` | `data/sft_filledintents.py` |
| `data/vm_v4_teacher.py` | `data/sft_main_teacher.py` |
| `data/vm_v4_teacher2.py` | `data/sft_main_teacher_verify.py` |
| `data/v4_select.py` | `data/sft_main_select.py` |
| `data/v4_answer_check.py` | `data/sft_main_answer_check.py` |
| `data/v4_build_parquet.py` | `data/sft_main_parquet.py` |
| `data/v4_rl_pool.py` | `data/rl_states.py` |
| `data/v41_build_parquet.py` | `data/sft_waitrelabel.py` |
| `data/v42_selfhist.py` | `data/sft_ownhistory.py` |
| `data/v5_pairs.py` | `data/dpo_allmistakes_pairs.py` |
| `data/v44_androidlens_eval.py` | `data/eval_androidlens.py` |
| `data/v44_memgui.py` | `data/sft_memgui_rows.py` |
| `data/v44_nochange.py` | `data/change_notes.py` |
| `data/v44_build_mix.py` | `data/sft_memgui_mix.py` |
| `data/v45_build_mix.py` | `data/sft_fullmix.py` |
| `data/v46_build.py` | `data/sft_counterfactual.py` |
| `data/v47_build.py` | `data/sft_counterfactual_waitfix.py` |
| `data/v47_cont_mix.py` | `data/sft_counterfactual_waitfix_mix.py` |
| `data/v48_build.py` | *(renamed `sft_endings.py`, then removed 2026-11-26: the never-built `Endings` builder)* |
| `data/v48_odyssey_filter.py` | `data/odyssey_endings_filter.py` |
| `data/v48_odyssey_terminals.py` | `data/odyssey_endings_terminals.py` |
| `data/r10_candidates.py` | `data/stopdpo_candidates.py` |
| `data/r10_filter_pairs.py` | `data/stopdpo_filter_pairs.py` |
| `data/r10_stop_pairs.py` | `data/stopdpo_pairs.py` |
| `data/r11_mix.py` | `data/endings_mix.py` |
| `data/r12_mix.py` | `data/donecheck_mix.py` |
| `data/r14_sft_mix.py` | `data/ownhistory_sft_mix.py` |
| `data/meta/v4_heldout_episodes.json` | `data/meta/main_heldout_episodes.json` |
| `scripts/training/make_v4_train_job.py` | *(removed 2026-11-26 with the job configs it wrote)* |
| `scripts/training/v4_reference_r7.json` | `scripts/training/main_reference_r7.json` |
| `analysis/v2_compare.py` | `analysis/multisource_vs_androidcontrolonly.py` |
| `analysis/v4_gate.py` | `analysis/main_gate.py` |
| `analysis/v4rl_promotion.py` | `analysis/grpo_promotion.py` |
| `analysis/qdc_report_v6.py` | `analysis/qdc_report.py` |
| `analysis/mw_summarize_e.py` | `analysis/mw_summarize_counterfactual.py` |
| `analysis/done_audit/v47_sheets.py` | `analysis/done_audit/waitfix_sheets.py` |
| `analysis/done_audit/v47_sheets_round3.py` | `analysis/done_audit/waitfix_sheets_round3.py` |
| `analysis/done_audit/r10_pair_sheets.py` | `analysis/done_audit/stopdpo_pair_sheets.py` |
| `analysis/done_audit/validation_v47_2026-11-25.json` | `analysis/done_audit/validation_waitfix_2026-11-25.json` |

## Adding a name

1. Pick `-Dev-<Recipe>` and say in one sentence what was added to the parent; add it to `scripts/publish/naming.py`
   (`python3 scripts/publish/naming.py --check` validates the table) and to the glossary above.
2. Use the same tag for the dataset if the data is new.
3. Promote to a `-<Variant>` or to no suffix only by a preregistered rule; record the old name under "Old label".

