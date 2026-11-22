# Models

**Contents:** [Versions](#versions-at-a-glance) · [Recipe](#training-recipe) · [Training runs](#training-runs) ·
[v4-RL](#v4-rl-not-promoted) · [Released artifacts](#released-artifacts)

---

## Versions at a glance

AndroidWorld = development seed 30, successes out of 116 ([results.md](results.md#androidworld-development-seed-30)).

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

Other base models on v1's data: Qwen3.5-2B with the same recipe (16); Qwen3.5-0.8B and LFM2.5-VL-450M with a
smaller one (LoRA r16, 1 epoch): 12 and 2.

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
| Checkpoints | Pushed to the Hub so a lost VM can resume: every 100 steps (v1, LFM2.5-VL-450M), 50 steps (all later runs) |

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

- **Losses are not comparable across versions:** the data and prompts differ.
- **Peak GPU memory** in the logged segments was 8.3–11.5 GB.
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

Hugging Face, private unless noted.

| Artifact | Repository |
|---|---|
| **v4** (merged weights / GGUF) | `experimentalmachines/LFM3-VL-2B-AndroidAgent-v4`, `…-v4-GGUF` |
| v4-RL (not promoted) | `experimentalmachines/LFM3-VL-2B-AndroidAgent-v4-RL`, `…-v4-RL-GGUF` |
| v4.2, v4.1 (**public**) | `alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.2` (+ `-GGUF`), `…-v4.1` (+ `-GGUF`) |
| v3, v2 | `alpharomercoma/LFM3-VL-2B-AndroidAgent-v3` (+ `-GGUF`), `…-v2` (+ `-GGUF`) |
| v1 | `experimentalmachines/LFM3-VL-2B-AndroidControl` (+ `-GGUF`) |
| v4 training data | `alpharomercoma/AndroidAgent-SFT-v4` @ `3375539` |
| v3 training data | `alpharomercoma/AndroidAgent-SFT-v3` @ `565ba76c` |
| v2 training data | `experimentalmachines/AndroidAgent-SFT-v2` @ `42f7f763` (**public**, superseded) |
| v1 training data | `experimentalmachines/AndroidControl-screen-agent-sft` |
| RL state pool | `alpharomercoma/AndroidAgent-RL-v4` @ `9ba36d90` |

### Integrity records

- v4's merged weights were checked tensor by tensor against base + LoRA (within 1 bf16 ulp):
  [`results/v4_local_export_manifest.json`](../results/v4_local_export_manifest.json).
- v4-RL export: [`results/v4rl_local_export_manifest.json`](../results/v4rl_local_export_manifest.json).
- v2 LoRA adapter SHA-256:
  - LFM3-VL-2B: `d8c46cbdc6ceae847b53390fb85dd033e2212ab8271b53074ab7d37a7bf2f252`
  - Qwen3.5-2B: `b5d1272fb4368eecc1ac6cd95368c318987f362d9c3a36fbd51003db1cf08b35`
