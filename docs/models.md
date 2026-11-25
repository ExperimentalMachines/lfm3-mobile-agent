# Models

Every model version, how it was trained, and where it is published. **v4 is the main model**; versions after it are
development rounds ([rounds.md](rounds.md)).

**Contents:** [Versions](#versions-at-a-glance) · [Recipe](#training-recipe) · [Training runs](#training-runs) ·
[v4-RL](#v4-rl-not-promoted) · [Released artifacts](#released-artifacts)

---

## Versions at a glance

AndroidWorld = development seed 30, successes out of 116 ([results.md](results.md#androidworld-development-seed-30), [rounds.md](rounds.md#all-rounds)).

| Version | What changed | AndroidWorld | Lesson |
|---|---|---|---|
| **v1** | AndroidControl only (official train episodes) | 15 | Strong at acting; never uses `answer` |
| **v2** | + GUI-Odyssey, AMEX, ScreenQA | 3 | 8,739 rows had a **blank intent**: a suspected cause (the data mix also changed) |
| v2 + forced intent | Inference-only test: force a one-line intent | 6 | Supports the blank-intent suspicion, but small: 3 wins, 0 losses, paired p = 0.25 |
| v1 + runtime feedback | Inference-only test: app-name resolution + failure notes | 10 | Worse; dropped |
| **v3** | v2 mix with blank intents filled (2,603 by action templates, 6,106 by a teacher model; 30 rows dropped) | 13 | Offline gains on the new datasets did not transfer to AndroidWorld |
| v4 (first build) | First v4 dataset | — | Codex data audit said STOP (answer leaks, guard gaps); run abandoned, retrained on rebuilt data |
| **v4 (final)** | v3 data in the v4 prompt + navigate-then-answer episodes + installed-app list + shorter ScreenQA answers | **18** | Fixed "never answers" (0 → 6 answer tasks); passed the gate; frozen |
| v4-RL | 200 steps of GRPO on static screenshots, from v4 | not run | Failed its offline promotion rule |
| v4.1 | v4 data with `wait` relabelled + recovery-history augmentation ([PREREG_v41](PREREG_v41.md)) | 12 | Data fix alone lost ground (+2 / −8 vs v4) |
| v4.2 | v4.1 + the model's own replayed history on training episodes (offline, DAgger-style) | 18 | Back to v4's level (+6 / −6); MobileWorld 8/105 vs v4's 6 (p = 0.63, post-hoc) with loops halved |
| v4.3-dpo | v4.2 + DPO on all 4,163 of its own mistakes ([round 5](rounds.md#round-5-learning-from-own-mistakes-vs-more-training-2026-11-22)) | not run | Failed offline (AC 0.732 → 0.545): DPO on generic wrong clicks pushed down whole action types |
| v4.3-dpo2 | v4.2 + DPO on 851 balanced stop / copied-intent mistakes | 21 | Net +3 vs v4.2 is noise (R = 9); stopping not measurably changed (false `complete` 28) |
| v4.3-sft | v4.2 + 500 more SFT steps on the same mix ("more epochs") | 24 | Best LFM3 seed-30 count, but +6 vs v4.2 is below the noise yardstick (9); it stops more often at unchanged precision, so false `complete` rose to 37 |
| v4.4-A | v4 recipe on v4's rows + 8,505 MemGUI rows ×2: long, self-correcting trajectories ([round 6](rounds.md#round-6-long-and-self-correcting-trajectories-2026-11-23)) | not run | Failed the offline gate. Long-task accuracy up (AndroidLens steps ≥ 10: 0.367 → 0.401); late early-stops unchanged |
| v4.4-B | A + "no visible change" notes in the history | not run | Failed the offline gate. Correct stop at the end of long tasks 12% → 29% |
| v4.4-C | v4 + 500 steps on 50% MemGUI / 50% v4 rows | not run | Failed the offline gate on late early-stops only. Best offline: AndroidLens end-of-task stop 48%, steps ≥ 10 0.413 |
| v4.5-D | All the data once (173,430 rows), 24-step history, change notes ([round 7](rounds.md#round-7-all-the-data-once-with-a-longer-memory-2026-11-24)) | 21 (exploratory) | Failed the offline gate on early stops. Offline gains (AndroidControl 0.753, long tasks 0.471) did not show online |
| **v4.6-E** | Counterfactual rows where history and screen disagree; judge-filtered "done" labels ([round 8](rounds.md#round-8-judge-done-from-the-screen-not-the-history-2026-11-25)) | 19 (exploratory) | Failed the offline gate narrowly (2 of 10). Waits 29% → 3.5% of steps; false "done" unchanged (24). Held-out 52 / 348 (v4 54; 75 false "done" vs 71): not promoted. Newest published model |
| E-DPO | E + DPO on 342 judge-checked stop pairs ([round 10](rounds.md#round-10-finishing-multi-part-tasks-2026-11-25)) | not run | Failed the offline gate: one pass (11 steps) left E unchanged. Not published |
| E-T | E + 747 checked GUI-Odyssey "done" endings, 1,000 steps ([round 11](rounds.md#round-11-e-trained-on-checked-multi-part-endings-queued)) | — | Registered 2026-11-25; smoke job queued for a GPU |

Other base models on v1's data: Qwen3.5-2B with the same recipe (16); Qwen3.5-0.8B and LFM2.5-VL-450M with a
smaller one (LoRA r16, 1 epoch): 12 and 2.

---

### What v1–v3 taught us

| Lesson | Seen in | Acted on |
|---|---|---|
| Offline gains on new datasets do not predict AndroidWorld | v2, v3 | AndroidWorld seed 30 became part of the gate (v4) |
| Blank intents break the agent loop | v2 | v3 filled them |
| Copied `wait` intents cause loops | v1–v4 | v4.1 relabelled them; v4.2 halved loops on MobileWorld |
| ScreenQA alone does not make the agent `answer` | v2, v3 (0 answer tasks) | v4: navigate-then-answer episodes + answer rules in the prompt (0 → 6 answer tasks) |
| Long ScreenQA answers | v3 | v4: shorter answers |
| Inference-time patches did not replace data fixes | v1 + runtime feedback (10), v2 + forced intent (6) | Dropped |

Per-version details for v1–v3 (data audits, evaluation numbers, Hugging Face links): [results.md](results.md#offline-evaluations), [datasets.md](datasets.md#training-data-per-version) and [Released artifacts](#released-artifacts).

---

## Training recipe

The LFM3-VL-2B SFT runs v1–v4 share this recipe and target budget, so data and prompt are the intended variables.
Per-run deviations (resumes, checkpoint cadence) are listed under [Training runs](#training-runs).

| Setting | Value |
|---|---|
| Method | LoRA SFT on the language model only; vision tower frozen |
| LoRA | rank 64, alpha 128; attention, MLP and convolution projections |
| Optimiser | lr 2e-4, 1,250 steps × 32 rows (batch 8 × gradient accumulation 4) |
| Image | One screenshot per step, area budget 880 × 880 px (≈ 720 image tokens for a phone screen) |
| Input | Goal + text history of earlier steps + current screenshot (v4: + installed-app list) |
| Output | `<think>short intent</think>` + one JSON action, coordinates on a 0–1000 grid |
| Checkpoints | Saved so a lost machine can resume: every 100 steps (v1, LFM2.5-VL-450M), 50 steps (v2–v4.4), 100 steps (v4.5-D on; to the Hub, Modal volumes or S3) |

**Changed after v4**

| From | Change |
|---|---|
| v4.4-B, then v4.5 on | "[no visible change]" notes in the history |
| v4.5-D | One full pass over the whole mix (5,000–6,000 steps), 24-step history, no gradient checkpointing (micro-batch 4 × 8 for D, 2 × 16 for E) |
| v4.6-E | Stricter change rule for the notes; history-vs-screen counterfactual rows |
| E-DPO, E-T | Continue from E's merged weights with a new LoRA: DPO lr 1e-5 (E-DPO); SFT lr 1e-4, 1,000 steps (E-T) |

Code: [`train/sft_vlm.py`](../train/sft_vlm.py), prompt and action format in
[`train/agent_format.py`](../train/agent_format.py), job configs in
[`scripts/training/jobs/`](../scripts/training/jobs/).

### Action space

`click`, `long_press`, `input_text` (types, then presses Enter), `scroll` (up/down/left/right), `open_app`,
`navigate_back`, `navigate_home`, `keyboard_enter`, `wait`, `answer` (v4), `status` (`complete` / `infeasible`).

---

## Training runs

Sources: `run_config.json`, `log_history.json` and `train_log.jsonl` per run under
[`results/training/`](../results/training/) and [`results/v4_dev/hub/training_logs/`](../results/v4_dev/hub/training_logs/).
Eval loss is on the AndroidControl validation split at the final step.

| Run | Training rows | Steps × rows | LoRA rank, lr | Final eval loss | Where | Run history |
|---|---|---|---|---|---|---|
| LFM3-VL-2B v1 | 99,216 | 1,250 × 32 | 64, 2e-4 | 0.287 | Modal | Resumed from a checkpoint after ~700 steps |
| LFM3-VL-2B v2 | 78,982 | 1,250 × 32 | 64, 2e-4 | 0.299 | Colab | A resume after completion ran one extra step (1,251); eval loss unchanged |
| LFM3-VL-2B v3 | 78,952 | 1,250 × 32 | 64, 2e-4 | 0.300 | Modal | One uninterrupted run |
| **LFM3-VL-2B v4** | 92,229 | 1,250 × 32 | 64, 2e-4 | 0.306 | Colab A100 | VM lost at step 353; resumed from the step-350 checkpoint |
| Qwen3.5-2B v1 | 99,216 | 1,250 × 32 | 64, 2e-4 | 0.240 | Colab | Resumed after ~600 steps |
| Qwen3.5-2B v2 | 78,982 | 1,250 × 32 | 64, 2e-4 | 0.250 | Colab | As LFM3 v2 (extra step 1,251) |
| Qwen3.5-0.8B v1 | 60,000 | 1,875 × 32 (1 epoch) | 16, 1e-4 | 0.276 | Colab | Resumed after ~1,200 steps |
| LFM2.5-VL-450M v1 | 60,000 | 1,875 × 32 (1 epoch) | 16, 1e-4 | 0.375 | Modal | Resumed after ~700 steps |
| LFM3-VL-2B v4.5-D | 173,430 | 5,420 × 32 (1 pass) | 64, 2e-4 | 0.252 | Modal H100 | One uninterrupted run, 3.4 h ([`results/v45_dev/training/`](../results/v45_dev/training/)) |
| LFM3-VL-2B v4.6-E | 185,643 | 5,802 × 32 (1 pass) | 64, 2e-4 | — | Colab A100 → Modal H100 | Resumed at step 3,100 from the Hub checkpoint ([PREREG_v46](PREREG_v46.md)) |
| E-DPO (from E) | 342 preference pairs | 11 × 32 (1 pass) | 64, 1e-5 (DPO β 0.1) | — | SageMaker L40S | [`results/v48_dev/r10edpo_eval/`](../results/v48_dev/r10edpo_eval/) |

- **Losses are not comparable across versions:** the data and prompts differ.
- **Peak GPU memory** in the logged segments was 8.3–11.5 GB (v4.5-D without gradient checkpointing: 39.6 GB).
- **Wall time** is per segment for resumed runs (see each `train_summary.json`). v4's resumed segment
  (steps 351–1,250) took 2.0 h on an A100.

---

## v4-RL (not promoted)

| Item | Value |
|---|---|
| Start | v4 |
| Method | GRPO (TRL) on static screenshots, 4 samples per state, KL β 0.001, LoRA r16, lr 1e-5 |
| Data | 2,000 states (700 answer, 500 complete, 300 other, 500 click) |
| Run | 200 steps, 0.95 h on a Colab A100; mean reward over the first / last 20 steps 0.714 → 0.765 |
| Outcome | Answer match up (0.868 → 0.890) but AndroidControl step SR down (0.728 → 0.667): **failed** the rule fixed before training ended |
| Diagnosis | On average 66% of groups per step had zero reward variance; 60% of states were terminal screens |

Code: [`train/grpo_vlm.py`](../train/grpo_vlm.py), [`train/rl_reward.py`](../train/rl_reward.py);
decision: [`results/v4rl_promotion_offline.json`](../results/v4rl_promotion_offline.json).

---

## Released artifacts

Everything is **public** in the [experimentalmachines](https://huggingface.co/experimentalmachines) Hugging Face org ([collection](https://huggingface.co/collections/experimentalmachines/lfm3-mobile-agent-6b03a79f8e23b8dde16e8326))
(released 2026-11-23 with [`scripts/publish/em_release.py`](../scripts/publish/em_release.py); log:
[`logs/em_release_hf.log`](../logs/em_release_hf.log)). Each model repo holds the merged weights, the LoRA adapter
(`lora_adapter/`), training logs (`training_logs/`), the prediction files behind its offline numbers (`eval/`), the
base model's LICENSE and a card with its status. Cards: [`scripts/publish/cards/`](../scripts/publish/cards/).

| Model | Weights | Phone GGUF | Status |
|---|---|---|---|
| **v4** | [`LFM3-VL-2B-MobileAgent-v4`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4) | [`…-v4-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4-GGUF) | **Main model** (held-out evaluated) |
| v1, v2, v3 | [`…-v1`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v1), [`…-v2`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v2), [`…-v3`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v3) | `…-v1-GGUF`, `…-v2-GGUF`, `…-v3-GGUF` | Superseded |
| v4-RL | [`…-v4-RL`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4-RL) | `…-v4-RL-GGUF` | Not promoted |
| v4.1, v4.2 | [`…-v4.1`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.1), [`…-v4.2`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.2) | `…-v4.1-GGUF`, `…-v4.2-GGUF` | Experimental follow-ups |
| v4.3-dpo, -dpo2, -sft | [`…-v4.3-dpo`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.3-dpo), [`…-v4.3-dpo2`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.3-dpo2), [`…-v4.3-sft`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.3-sft) | `…-v4.3-dpo2-GGUF`, `…-v4.3-sft-GGUF` (dpo: none) | Failed their gates |
| v4.4-A, -B, -C | [`…-v4.4-A`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.4-A), [`…-v4.4-B`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.4-B), [`…-v4.4-C`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.4-C) | — | Not promoted (round 6, offline gate) |
| v4.5-D | [`…-v4.5-D`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.5-D) | — (local only) | Not promoted (round 7, offline gate) |
| **v4.6-E** | [`…-v4.6-E`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.6-E) | [`…-v4.6-E-GGUF`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4.6-E-GGUF) | Not promoted (round 8, offline gate 8 / 10; held-out 52 / 348 vs v4's 54, more false "done"); best-behaved so far: waits 3.5% of AndroidWorld steps |
| Qwen3.5-2B v1, v2 | [`Qwen3.5-2B-MobileAgent-v1`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-v1), [`…-v2`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-v2) | `…-v1-GGUF`, `…-v2-GGUF` | Comparison |
| Qwen3.5-0.8B v1 | [`Qwen3.5-0.8B-MobileAgent-v1`](https://huggingface.co/experimentalmachines/Qwen3.5-0.8B-MobileAgent-v1) | `…-v1-GGUF` | Comparison |
| LFM2.5-VL-450M v1 | [`LFM2.5-VL-450M-MobileAgent-v1`](https://huggingface.co/experimentalmachines/LFM2.5-VL-450M-MobileAgent-v1) | `…-v1-GGUF` | Comparison |

- **v4 for LiteRT-LM:** [`LFM3-VL-2B-MobileAgent-v4-LiteRT`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v4-LiteRT)
  is one int8 `.litertlm` that runs on a phone's GPU with the training-time 1280 × 576 screenshot grid. It picks the
  same action as the bf16 model on 90.6% of 180 AndroidControl test steps (the v4 GGUF: 89.4%). It was converted, checked
  and wrapped in an Android app in [ExperimentalMachines/mobile-agent](https://github.com/ExperimentalMachines/mobile-agent).

| Dataset | Revision used for training | Trains |
|---|---|---|
| [`MobileAgent-SFT-v1`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v1) | (not pinned) | v1 and the comparison fine-tunes; its `test` split is the AndroidControl test set used offline |
| [`MobileAgent-SFT-v2`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v2) | `42f7f763` | v2, Qwen3.5-2B v2 |
| [`MobileAgent-SFT-v3`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v3) | `565ba76c` | v3 |
| [`MobileAgent-SFT-v4`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v4) | `3375539` | v4; v4.1 / v4.2 rebuild their data from it |
| [`MobileAgent-RL-v4`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-RL-v4) | `9ba36d90` | v4-RL |
| [`MobileAgent-SFT-v4.4`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v4.4) | `2b481ae3` | v4.4-A / B / C: the new MemGUI rows only (mixed with v4's at training time by `data/v44_build_mix.py`); also holds the AndroidLens English eval set (`androidlens/`, **never trained on**) |

### Old names (scripts and earlier docs use them; Hugging Face redirects them)

| Old name | New name |
|---|---|
| `experimentalmachines/LFM3-VL-2B-AndroidControl` (+ `-GGUF`) | `experimentalmachines/LFM3-VL-2B-MobileAgent-v1` (+ `-GGUF`) |
| `alpharomercoma/LFM3-VL-2B-AndroidAgent-v2` … `-v4.3-sft` (+ `-GGUF`); `experimentalmachines/LFM3-VL-2B-AndroidAgent-v4`, `-v4-RL` (+ `-GGUF`) | `experimentalmachines/LFM3-VL-2B-MobileAgent-<same version>` (+ `-GGUF`) |
| `experimentalmachines/Qwen3.5-2B-AndroidControl`, `alpharomercoma/Qwen3.5-2B-AndroidAgent-v2` | `experimentalmachines/Qwen3.5-2B-MobileAgent-v1`, `-v2` |
| `experimentalmachines/Qwen3.5-0.8B-AndroidControl`, `experimentalmachines/LFM2.5-VL-450M-AndroidControl` (+ `-GGUF`) | `experimentalmachines/Qwen3.5-0.8B-MobileAgent-v1`, `experimentalmachines/LFM2.5-VL-450M-MobileAgent-v1` (+ `-GGUF`) |
| `experimentalmachines/AndroidControl-screen-agent-sft`, `experimentalmachines/AndroidAgent-SFT-v2`, `alpharomercoma/AndroidAgent-SFT-v3`, `-v4`, `alpharomercoma/AndroidAgent-RL-v4` | `experimentalmachines/MobileAgent-SFT-v1` … `-v4`, `experimentalmachines/MobileAgent-RL-v4` |

- GGUF files were renamed to match (e.g. `LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf` → `LFM3-VL-2B-MobileAgent-v4-Q4_K_M.gguf`);
  the bytes are unchanged, so the hashes in the manifests below still apply.
- Deleted as stale (owner's decision): logs-only partial copies of v2 / Qwen3.5-2B v2 in the org, logs-only stubs of
  v4 / v4-RL in the personal account, and six intermediate `*-LoRA-ckpt` repos.

### Integrity records

- v4's merged weights were checked tensor by tensor against base + LoRA (within 1 bf16 ulp):
  [`results/v4_local_export_manifest.json`](../results/v4_local_export_manifest.json).
- v4-RL export: [`results/v4rl_local_export_manifest.json`](../results/v4rl_local_export_manifest.json).
- v2 LoRA adapter SHA-256:
  - LFM3-VL-2B: `d8c46cbdc6ceae847b53390fb85dd033e2212ab8271b53074ab7d37a7bf2f252`
  - Qwen3.5-2B: `b5d1272fb4368eecc1ac6cd95368c318987f362d9c3a36fbd51003db1cf08b35`
