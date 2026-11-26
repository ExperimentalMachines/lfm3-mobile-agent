# Models

Every model, what it adds to its parent, how it was trained, and where it is published. **`LFM3-VL-2B-MobileAgent` ("Main")
is the main model**; the rest are development rounds ([rounds.md](rounds.md)). Names, old labels and the glossary of
recipe tags: [naming.md](naming.md).

**Contents:** [Models](#models-at-a-glance) · [Recipe](#training-recipe) · [Training runs](#training-runs) ·
[GRPO](#grpo-not-promoted) · [Released artifacts](#released-artifacts)

---

## Models at a glance

AndroidWorld = development seed 30, successes out of 116 ([results.md](results.md#androidworld-development-seed-30), [rounds.md](rounds.md#all-rounds)).

| Model (`LFM3-VL-2B-MobileAgent` + suffix) | Old label | What it adds | AndroidWorld seed 30 | Lesson |
|---|---|---|---|---|
| `-Dev-AndroidControlOnly` | v1 | AndroidControl only (official train episodes) | 15 | Strong at acting; never uses `answer` |
| `-Dev-MultiSource` | v2 | + GUI-Odyssey, AMEX, ScreenQA | 3 | 8,739 rows had a **blank intent**: a suspected cause (the data mix also changed) |
| `-Dev-MultiSource` + forced intent (inference only) | v2 + forced intent | Inference-only test: force a one-line intent | 6 | Supports the blank-intent suspicion, but small: 3 wins, 0 losses, paired p = 0.25 |
| `-Dev-AndroidControlOnly` + runtime feedback (inference only) | v1 + runtime feedback | Inference-only test: app-name resolution + failure notes | 10 | Worse; dropped |
| `-Dev-FilledIntents` | v3 | MultiSource mix with blank intents filled (2,603 by action templates, 6,106 by a teacher model; 30 rows dropped) | 13 | Offline gains on the new datasets did not transfer to AndroidWorld |
| (first build of the main data; abandoned) | v4 (first build) | First Main dataset | — | Codex data audit said STOP (answer leaks, guard gaps); run abandoned, retrained on rebuilt data |
| **`(none)`** | v4 | FilledIntents data in the v4 prompt + navigate-then-answer episodes + installed-app list + shorter ScreenQA answers | **18** | Fixed "never answers" (0 → 6 answer tasks); passed the gate; frozen |
| `-Dev-GRPO` | v4-RL | 200 steps of GRPO on static screenshots, from Main | not run | Failed its offline promotion rule |
| `-Dev-WaitRelabel` | v4.1 | Main data with `wait` relabelled + recovery-history augmentation ([MobileWorld follow-up preregistration](preregistrations/mobileworld-followup-waitrelabel.md)) | 12 | Data fix alone lost ground (+2 / −8 vs Main) |
| `-Dev-OwnHistory` | v4.2 | WaitRelabel + the model's own replayed history on training episodes (offline, DAgger-style) | 18 | Back to Main's level (+6 / −6); MobileWorld 8/105 vs Main's 6 (p = 0.63, post-hoc) with loops halved |
| `-Dev-DPOAllMistakes` | v4.3-dpo | OwnHistory + DPO on all 4,163 of its own mistakes ([round 5](rounds.md#round-5-learning-from-own-mistakes-vs-more-training-2026-11-22)) | not run | Failed offline (AC 0.732 → 0.545): DPO on generic wrong clicks pushed down whole action types |
| `-Dev-DPOStopMistakes` | v4.3-dpo2 | OwnHistory + DPO on 851 balanced stop / copied-intent mistakes | 21 | Net +3 vs OwnHistory is noise (R = 9); stopping not measurably changed (false `complete` 28) |
| `-Dev-ContinuedSFT` | v4.3-sft | OwnHistory + 500 more SFT steps on the same mix ("more epochs") | 24 | Best LFM3 seed-30 count, but +6 vs OwnHistory is below the noise yardstick (9); it stops more often at unchanged precision, so false `complete` rose to 37 |
| `-Dev-MemGUI` | v4.4-A | Main recipe on Main's rows + 8,505 MemGUI rows ×2: long, self-correcting trajectories ([round 6](rounds.md#round-6-long-and-self-correcting-trajectories-2026-11-23)) | not run | Failed the offline gate. Long-task accuracy up (AndroidLens steps ≥ 10: 0.367 → 0.401); late early-stops unchanged |
| `-Dev-MemGUIChangeNotes` | v4.4-B | MemGUI + "no visible change" notes in the history | not run | Failed the offline gate. Correct stop at the end of long tasks 12% → 29% |
| `-Dev-MemGUIContinuedSFT` | v4.4-C | Main + 500 steps on 50% MemGUI / 50% Main rows | not run | Failed the offline gate on late early-stops only. Best offline: AndroidLens end-of-task stop 48%, steps ≥ 10 0.413 |
| `-Dev-FullMix` | v4.5-D | All the data once (173,430 rows), 24-step history, change notes ([round 7](rounds.md#round-7-all-the-data-once-with-a-longer-memory-2026-11-24)) | 21 (exploratory) | Failed the offline gate on early stops. Offline gains (AndroidControl 0.753, long tasks 0.471) did not show online |
| `-Counterfactual` | v4.6-E | Counterfactual rows where history and screen disagree; judge-filtered "done" labels ([round 8](rounds.md#round-8-judge-done-from-the-screen-not-the-history-2026-11-25)) | 19 (exploratory) | Failed the offline gate narrowly (2 of 10). Waits 29% → 3.5% of steps; false "done" unchanged (24). Held-out 52 / 348 (Main 54; 75 false "done" vs 71): not promoted. Newest published model |
| `Counterfactual+StopDPO` (never published) | E-DPO | Counterfactual + DPO on 342 judge-checked stop pairs ([round 10](rounds.md#round-10-finishing-multi-part-tasks-2026-11-25)) | not run | Failed the offline gate: one pass (11 steps) left Counterfactual unchanged. Not published |
| `Counterfactual+Endings` (never published) | E-T | Counterfactual + 747 checked GUI-Odyssey "done" endings, 1,000 steps ([round 11](rounds.md#round-11-counterfactual-trained-on-checked-multi-part-endings-2026-11-25)) | — | Failed the offline gate (M_notdone 65% vs ≤ 5%): says "done" on most final screens, finished or not. Not published |
| `Counterfactual+DoneCheck` (never published) | E-V | Counterfactual + rows teaching a "is the task done?" question asked before `complete` ([round 12](rounds.md#rounds-12-to-14-the-done-check-and-training-on-its-own-mistakes-2026-11-26)) | — | Failed the offline gate (2 of 16): the check says "no" on 74.5% of unfinished screens (bar 75%) and the model + check still ends on 19.5% of them (bar 15%). Not published |
| `Counterfactual+OwnHistoryRL` (never published) | E-S2 (E-S: stopped) | Semi-online RL on 400 of its own histories, 100 batches ([round 14](rounds.md#rounds-12-to-14-the-done-check-and-training-on-its-own-mistakes-2026-11-26)) | — | Failed the offline gate: barely moved (says done on 1% of finished final screens); slightly worse on repeated taps. Not published |
| `Counterfactual+OwnHistorySFT` (never published) | E-D | Matched control: supervised rows from its own strict misses on the same episodes (round 14) | — | Failed the offline gate: says done on 83.5% of finished and 56.5% of unfinished final screens. Not published |

Other base models on AndroidControlOnly's data: Qwen3.5-2B with the same recipe (16); Qwen3.5-0.8B and LFM2.5-VL-450M with a
smaller one (LoRA r16, 1 epoch): 12 and 2.

---

### What the first three models taught us

| Lesson | Seen in | Acted on |
|---|---|---|
| Offline gains on new datasets do not predict AndroidWorld | MultiSource, FilledIntents | AndroidWorld seed 30 became part of the gate (Main) |
| Blank intents break the agent loop | MultiSource | FilledIntents filled them |
| Copied `wait` intents cause loops | AndroidControlOnly, MultiSource, FilledIntents, Main | WaitRelabel relabelled them; OwnHistory halved loops on MobileWorld |
| ScreenQA alone does not make the agent `answer` | MultiSource, FilledIntents (0 answer tasks) | Main: navigate-then-answer episodes + answer rules in the prompt (0 → 6 answer tasks) |
| Long ScreenQA answers | FilledIntents | Main: shorter answers |
| Inference-time patches did not replace data fixes | AndroidControlOnly + runtime feedback (10), MultiSource + forced intent (6) | Dropped |

Per-model details for these three (data audits, evaluation numbers, Hugging Face links): [results.md](results.md#offline-evaluations), [datasets.md](datasets.md#training-data-per-dataset) and [Released artifacts](#released-artifacts).

---

## Training recipe

The first four LFM3-VL-2B SFT runs (AndroidControlOnly, MultiSource, FilledIntents, Main) share this recipe and target budget, so data and prompt are the intended variables.
Per-run deviations (resumes, checkpoint cadence) are listed under [Training runs](#training-runs).

| Setting | Value |
|---|---|
| Method | LoRA SFT on the language model only; vision tower frozen |
| LoRA | rank 64, alpha 128; attention, MLP and convolution projections |
| Optimiser | lr 2e-4, 1,250 steps × 32 rows (batch 8 × gradient accumulation 4) |
| Image | One screenshot per step, area budget 880 × 880 px (≈ 720 image tokens for a phone screen) |
| Input | Goal + text history of earlier steps + current screenshot (Main: + installed-app list) |
| Output | `<think>short intent</think>` + one JSON action, coordinates on a 0–1000 grid |
| Checkpoints | Saved so a lost machine can resume: every 100 steps (AndroidControlOnly, LFM2.5-VL-450M), 50 steps (MultiSource through the MemGUI models), 100 steps (FullMix on; to the Hub, Modal volumes or S3) |

**Changed after Main**

| From | Change |
|---|---|
| MemGUIChangeNotes, then FullMix on | "[no visible change]" notes in the history |
| FullMix | One full pass over the whole mix (5,000–6,000 steps), 24-step history, no gradient checkpointing (micro-batch 4 × 8 for FullMix, 2 × 16 for Counterfactual) |
| Counterfactual | Stricter change rule for the notes; history-vs-screen counterfactual rows |
| Counterfactual+StopDPO, Counterfactual+Endings | Continue from Counterfactual's merged weights with a new LoRA: DPO lr 1e-5 (Counterfactual+StopDPO); SFT lr 1e-4, 1,000 steps (Counterfactual+Endings) |

Code: [`train/sft_vlm.py`](../train/sft_vlm.py), prompt and action format in
[`train/agent_format.py`](../train/agent_format.py), each run's configuration in its `run_config.json` under [`results/training/`](../results/training/).

### Action space

`click`, `long_press`, `input_text` (types, then presses Enter), `scroll` (up/down/left/right), `open_app`,
`navigate_back`, `navigate_home`, `keyboard_enter`, `wait`, `answer` (Main), `status` (`complete` / `infeasible`).

---

## Training runs

Sources: `run_config.json`, `log_history.json` and `train_log.jsonl` per run under
[`results/training/`](../results/training/) and [`results/v4_dev/hub/training_logs/`](../results/v4_dev/hub/training_logs/).
Eval loss is on the AndroidControl validation split at the final step.

| Run | Training rows | Steps × rows | LoRA rank, lr | Final eval loss | Where | Run history |
|---|---|---|---|---|---|---|
| LFM3-VL-2B AndroidControlOnly | 99,216 | 1,250 × 32 | 64, 2e-4 | 0.287 | Modal | Resumed from a checkpoint after ~700 steps |
| LFM3-VL-2B MultiSource | 78,982 | 1,250 × 32 | 64, 2e-4 | 0.299 | Colab | A resume after completion ran one extra step (1,251); eval loss unchanged |
| LFM3-VL-2B FilledIntents | 78,952 | 1,250 × 32 | 64, 2e-4 | 0.300 | Modal | One uninterrupted run |
| **LFM3-VL-2B Main** | 92,229 | 1,250 × 32 | 64, 2e-4 | 0.306 | Colab A100 | VM lost at step 353; resumed from the step-350 checkpoint |
| Qwen3.5-2B AndroidControlOnly | 99,216 | 1,250 × 32 | 64, 2e-4 | 0.240 | Colab | Resumed after ~600 steps |
| Qwen3.5-2B MultiSource | 78,982 | 1,250 × 32 | 64, 2e-4 | 0.250 | Colab | As LFM3 MultiSource (extra step 1,251) |
| Qwen3.5-0.8B AndroidControlOnly | 60,000 | 1,875 × 32 (1 epoch) | 16, 1e-4 | 0.276 | Colab | Resumed after ~1,200 steps |
| LFM2.5-VL-450M AndroidControlOnly | 60,000 | 1,875 × 32 (1 epoch) | 16, 1e-4 | 0.375 | Modal | Resumed after ~700 steps |
| LFM3-VL-2B FullMix | 173,430 | 5,420 × 32 (1 pass) | 64, 2e-4 | 0.252 | Modal H100 | One uninterrupted run, 3.4 h ([`results/v45_dev/training/`](../results/v45_dev/training/)) |
| LFM3-VL-2B Counterfactual | 185,643 | 5,802 × 32 (1 pass) | 64, 2e-4 | — | Colab A100 → Modal H100 | Resumed at step 3,100 from the Hub checkpoint ([round 8 preregistration](preregistrations/round-08-done-from-the-screen.md)) |
| Counterfactual+StopDPO (from Counterfactual) | 342 preference pairs | 11 × 32 (1 pass) | 64, 1e-5 (DPO β 0.1) | — | SageMaker L40S | [`results/v48_dev/r10edpo_eval/`](../results/v48_dev/r10edpo_eval/) |

- **Losses are not comparable across models:** the data and prompts differ.
- **Peak GPU memory** in the logged segments was 8.3–11.5 GB (FullMix without gradient checkpointing: 39.6 GB).
- **Wall time** is per segment for resumed runs (see each `train_summary.json`). Main's resumed segment
  (steps 351–1,250) took 2.0 h on an A100.

---

## GRPO (not promoted)

| Item | Value |
|---|---|
| Start | Main |
| Method | GRPO (TRL) on static screenshots, 4 samples per state, KL β 0.001, LoRA r16, lr 1e-5 |
| Data | 2,000 states (700 answer, 500 complete, 300 other, 500 click) |
| Run | 200 steps, 0.95 h on a Colab A100; mean reward over the first / last 20 steps 0.714 → 0.765 |
| Outcome | Answer match up (0.868 → 0.890) but AndroidControl step SR down (0.728 → 0.667): **failed** the rule fixed before training ended |
| Diagnosis | On average 66% of groups per step had zero reward variance; 60% of states were terminal screens |

Code: [`train/grpo_vlm.py`](../train/grpo_vlm.py), [`train/rl_reward.py`](../train/rl_reward.py);
decision: [`results/v4rl_promotion_offline.json`](../results/v4rl_promotion_offline.json).

---

## Released artifacts

Everything is **public** in the [experimentalmachines](https://huggingface.co/experimentalmachines) Hugging Face org ([collection](https://huggingface.co/collections/experimentalmachines/lfm3-mobile-agent-6b03a79f8e23b8dde16e8326)). Each model repo holds the merged weights, the LoRA adapter (`lora_adapter/`), training logs (`training_logs/`), the prediction files behind its offline numbers (`eval/`), the base model's LICENSE and a card with its status. Cards: [`scripts/publish/cards/`](../scripts/publish/cards/). Names follow [naming.md](naming.md); the repos were renamed on 2026-11-26 (Hugging Face redirects every old name, but **file names inside the GGUF / LiteRT repos changed** to match).

| Model (weights) | Phone formats | Status |
|---|---|---|
| [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) (was v4) | [`LFM3-VL-2B-MobileAgent-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-GGUF), [`LFM3-VL-2B-MobileAgent-LiteRT`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-LiteRT) | **Main model** (held-out evaluated) |
| [`LFM3-VL-2B-MobileAgent-Counterfactual`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual) (was v4.6-E) | [`LFM3-VL-2B-MobileAgent-Counterfactual-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual-GGUF) | Evaluated alternative: not promoted (held-out 52 / 348 vs Main's 54, more false "done"); waits on 3.5% of AndroidWorld steps; needs the 24-step history harness |
| [`LFM3-VL-2B-MobileAgent-Dev-AndroidControlOnly`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-AndroidControlOnly) (was v1) | [`LFM3-VL-2B-MobileAgent-Dev-AndroidControlOnly-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-AndroidControlOnly-GGUF) | Development checkpoint: SFT on AndroidControl only (official train episodes) |
| [`LFM3-VL-2B-MobileAgent-Dev-MultiSource`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MultiSource) (was v2) | [`LFM3-VL-2B-MobileAgent-Dev-MultiSource-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MultiSource-GGUF) | Development checkpoint: + GUI-Odyssey, AMEX, ScreenQA (8,739 rows with a blank intent) |
| [`LFM3-VL-2B-MobileAgent-Dev-FilledIntents`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-FilledIntents) (was v3) | [`LFM3-VL-2B-MobileAgent-Dev-FilledIntents-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-FilledIntents-GGUF) | Development checkpoint: the blank intents filled (templates + a teacher model) |
| [`LFM3-VL-2B-MobileAgent-Dev-GRPO`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-GRPO) (was v4-RL) | [`LFM3-VL-2B-MobileAgent-Dev-GRPO-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-GRPO-GGUF) | Development checkpoint: 200 GRPO steps on static screenshots |
| [`LFM3-VL-2B-MobileAgent-Dev-WaitRelabel`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-WaitRelabel) (was v4.1) | [`LFM3-VL-2B-MobileAgent-Dev-WaitRelabel-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-WaitRelabel-GGUF) | Development checkpoint: copied `wait` intents relabelled + recovery-history augmentation |
| [`LFM3-VL-2B-MobileAgent-Dev-OwnHistory`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory) (was v4.2) | [`LFM3-VL-2B-MobileAgent-Dev-OwnHistory-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory-GGUF) | Development checkpoint: + the model's own replayed history on training episodes |
| [`LFM3-VL-2B-MobileAgent-Dev-DPOAllMistakes`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-DPOAllMistakes) (was v4.3-dpo) | none | Development checkpoint: DPO on all 4,163 of its own mistakes |
| [`LFM3-VL-2B-MobileAgent-Dev-DPOStopMistakes`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-DPOStopMistakes) (was v4.3-dpo2) | [`LFM3-VL-2B-MobileAgent-Dev-DPOStopMistakes-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-DPOStopMistakes-GGUF) | Development checkpoint: DPO on 851 balanced stop / copied-intent mistakes |
| [`LFM3-VL-2B-MobileAgent-Dev-ContinuedSFT`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-ContinuedSFT) (was v4.3-sft) | [`LFM3-VL-2B-MobileAgent-Dev-ContinuedSFT-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-ContinuedSFT-GGUF) | Development checkpoint: 500 more SFT steps on the same mix |
| [`LFM3-VL-2B-MobileAgent-Dev-MemGUI`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MemGUI) (was v4.4-A) | none | Development checkpoint: + MemGUI long, self-correcting trajectories |
| [`LFM3-VL-2B-MobileAgent-Dev-MemGUIChangeNotes`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MemGUIChangeNotes) (was v4.4-B) | none | Development checkpoint: + "[no visible change]" notes in the history |
| [`LFM3-VL-2B-MobileAgent-Dev-MemGUIContinuedSFT`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-MemGUIContinuedSFT) (was v4.4-C) | none | Development checkpoint: 500 more steps on 50% MemGUI / 50% main-model rows |
| [`LFM3-VL-2B-MobileAgent-Dev-FullMix`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-FullMix) (was v4.5-D) | none | Development checkpoint: one pass over all candidate sources, 24-step history, change notes |
| [`Qwen3.5-2B-MobileAgent-Dev-AndroidControlOnly`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-Dev-AndroidControlOnly) (was Qwen3.5-2B v1) | [`Qwen3.5-2B-MobileAgent-Dev-AndroidControlOnly-GGUF`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-Dev-AndroidControlOnly-GGUF) | Comparison model (same recipe family on another base) |
| [`Qwen3.5-2B-MobileAgent-Dev-MultiSource`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-Dev-MultiSource) (was Qwen3.5-2B v2) | [`Qwen3.5-2B-MobileAgent-Dev-MultiSource-GGUF`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-Dev-MultiSource-GGUF) | Comparison model (same recipe family on another base) |
| [`Qwen3.5-0.8B-MobileAgent-Dev-AndroidControlOnly`](https://huggingface.co/experimentalmachines/Qwen3.5-0.8B-MobileAgent-Dev-AndroidControlOnly) (was Qwen3.5-0.8B v1) | [`Qwen3.5-0.8B-MobileAgent-Dev-AndroidControlOnly-GGUF`](https://huggingface.co/experimentalmachines/Qwen3.5-0.8B-MobileAgent-Dev-AndroidControlOnly-GGUF) | Comparison model (same recipe family on another base) |
| [`LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly`](https://huggingface.co/experimentalmachines/LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly) (was LFM2.5-VL-450M v1) | [`LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly-GGUF`](https://huggingface.co/experimentalmachines/LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly-GGUF) | Comparison model (same recipe family on another base) |

`-LiteRT` is one int8 `.litertlm` that runs on a phone's GPU with the training-time 1280 × 576 screenshot grid; it picks the same action as the bf16 model on 90.6% of 180 AndroidControl test steps (the GGUF: 89.4%). It was converted, checked and wrapped in an Android app in [ExperimentalMachines/mobile-agent](https://github.com/ExperimentalMachines/mobile-agent).

| Dataset | Revision used for training | Trains |
|---|---|---|
| [`MobileAgent-SFT-AndroidControl`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-AndroidControl) (was MobileAgent-SFT-v1) | (not pinned) | `-Dev-AndroidControlOnly` and the other-base comparison models; its `test` split is the AndroidControl test set used offline |
| [`MobileAgent-SFT-MultiSource`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-MultiSource) (was MobileAgent-SFT-v2) | `42f7f763` | `-Dev-MultiSource`, Qwen3.5-2B `-Dev-MultiSource` |
| [`MobileAgent-SFT-FilledIntents`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-FilledIntents) (was MobileAgent-SFT-v3) | `565ba76c` | `-Dev-FilledIntents` |
| [`MobileAgent-SFT`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT) (was MobileAgent-SFT-v4) | `3375539` | Main; `-Dev-WaitRelabel` / `-Dev-OwnHistory` rebuild their data from it |
| [`MobileAgent-RL`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-RL) (was MobileAgent-RL-v4) | `9ba36d90` | `-Dev-GRPO` |
| [`MobileAgent-SFT-MemGUI`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-MemGUI) (was MobileAgent-SFT-v4.4) | `2b481ae3` | `-Dev-MemGUI*`: the new MemGUI rows only (mixed with Main's at training time by `data/sft_memgui_mix.py`); also holds the AndroidLens English eval set (`androidlens/`, **never trained on**) |
| [`MobileAgent-SFT-FullMix`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-FullMix) (was MobileAgent-SFT-v4.5) | `45331aaa` | `-Dev-FullMix` |
| [`MobileAgent-SFT-Counterfactual`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-Counterfactual) (was MobileAgent-SFT-v4.6) | `0ace5559` | `-Counterfactual` |
| [`MobileAgent-SFT-Counterfactual-WaitFix`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-Counterfactual-WaitFix) (was MobileAgent-SFT-v4.7) | `420637e9` | nothing yet (built in round 9, not trained on) |

### Integrity records

- Main's merged weights were checked tensor by tensor against base + LoRA (within 1 bf16 ulp): [`results/v4_local_export_manifest.json`](../results/v4_local_export_manifest.json).
- GRPO export: [`results/v4rl_local_export_manifest.json`](../results/v4rl_local_export_manifest.json).
- MultiSource LoRA adapter SHA-256:
  - LFM3-VL-2B: `d8c46cbdc6ceae847b53390fb85dd033e2212ab8271b53074ab7d37a7bf2f252`
  - Qwen3.5-2B: `b5d1272fb4368eecc1ac6cd95368c318987f362d9c3a36fbd51003db1cf08b35`
- The 2026-11-26 rename moved repos, renamed files and rewrote cards; no weight or data file changed: every LFS hash is identical before and after ([`results/hf_snapshot_pre_rename_2026-11-26.json`](../results/hf_snapshot_pre_rename_2026-11-26.json), [`results/hf_migration/`](../results/hf_migration/)).
- Deleted as stale: logs-only partial copies, six intermediate `*-LoRA-ckpt` repos (earlier), and on 2026-11-26 the two training-checkpoint repos of FullMix and Counterfactual (their final adapters are identical to the `lora_adapter/` of the final repos).

