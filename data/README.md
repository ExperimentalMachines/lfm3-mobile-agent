# data/

Dataset builders (one per published dataset, named after it: `sft_<recipe>.py` builds `MobileAgent-SFT-<Recipe>`), the
mixes built inside training jobs, and the fixed split files in [`meta/`](meta/README.md). The names follow
[docs/naming.md](../docs/naming.md); the docstrings keep the labels the scripts were written under.

| Script | Builds |
|---|---|
| `sft_androidcontrol.py` | `MobileAgent-SFT-AndroidControl` (train / val / test from AndroidControl; also the frozen test ground truth) |
| `sft_multisource.py` | `MobileAgent-SFT-MultiSource` (+ GUI-Odyssey, AMEX, ScreenQA) |
| `sft_filledintents_intents.py`, `sft_filledintents.py` | `MobileAgent-SFT-FilledIntents`: fill the blank intents (templates + a teacher model), then rebuild the parquet shards |
| `sft_main_select.py`, `sft_main_teacher.py`, `sft_main_teacher_verify.py`, `sft_main_answer_check.py`, `sft_main_parquet.py` | `MobileAgent-SFT` (the main model's data): pick episodes, teacher questions and answers, the second verification pass, the strict answer check, the final build |
| `rl_states.py` | `MobileAgent-RL` (static states for the GRPO run) |
| `sft_waitrelabel.py`, `sft_ownhistory.py` | The `-Dev-WaitRelabel` and `-Dev-OwnHistory` training data (rebuilt from `MobileAgent-SFT`; not published as datasets) |
| `dpo_allmistakes_pairs.py` | Preference pairs for `-Dev-DPOAllMistakes` / `-Dev-DPOStopMistakes` |
| `sft_memgui_rows.py`, `sft_memgui_mix.py`, `change_notes.py`, `eval_androidlens.py` | `MobileAgent-SFT-MemGUI`: MemGUI rows, the three training mixes, the "[no visible change]" notes, the AndroidLens eval splits |
| `sft_fullmix.py` | `MobileAgent-SFT-FullMix` |
| `sft_counterfactual.py` | `MobileAgent-SFT-Counterfactual` |
| `sft_counterfactual_waitfix.py`, `sft_counterfactual_waitfix_mix.py` | `MobileAgent-SFT-Counterfactual-WaitFix` and its continuation mix |
| `odyssey_endings_terminals.py`, `odyssey_endings_filter.py` | Round 10 "multi-part endings": the GUI-Odyssey ending candidates and their first by-eye filter (the never-built `Endings` full builder, `sft_endings.py`, was removed; its rules live on in `endings_mix.py`) |
| `stopdpo_candidates.py`, `stopdpo_pairs.py`, `stopdpo_filter_pairs.py` | Round 10 stop-DPO: candidate rows, preference pairs from the model's own stop decisions, judge-checked filtering |
| `ac_complete_rows.py` | Every real AndroidControl `complete` row of `MobileAgent-SFT-Counterfactual`'s training split (for the judge's labels) |
| `endings_mix.py`, `donecheck_mix.py`, `ownhistory_sft_mix.py` | Mixes built inside the round 11 / 12 / 14 SageMaker jobs |
| `build_general_replay.py` | General-multimodal replay set to limit forgetting (used for the LFM2.5-VL-450M model) |
