# Models

**Contents:** [Versions](#versions-at-a-glance) · [Recipe](#training-recipe) · [Training runs](#training-runs) ·
[v4-RL](#v4-rl-not-promoted) · [Released artifacts](#released-artifacts)

---

## Versions at a glance

AndroidWorld = development seed 30, successes out of 116 ([results.md](results.md#androidworld-development-seed-30)).

| Version | What changed | AndroidWorld | Lesson |
|---|---|---|---|
| **v1** | AndroidControl only (official train episodes) | 15 | Strong at acting; never uses `answer` |
| **v2** | + GUI-Odyssey, AMEX, ScreenQA | 3 | 8,739 rows had a **blank intent**; the model learned to act without planning |
| v2 + forced intent | Inference-only test: force a one-line intent | 6 | Confirms the blank-intent diagnosis |
| v1 + runtime feedback | Inference-only test: app-name resolution + failure notes | 10 | Worse; dropped |
| **v3** | v2 mix with every intent filled in by a teacher model | 13 | Offline gains on the new datasets did not transfer to AndroidWorld |
| v4 (first build) | First v4 dataset | — | Codex data audit said STOP (answer leaks, guard gaps); run abandoned, retrained on rebuilt data |
| **v4 (final)** | v3 data in the v4 prompt + navigate-then-answer episodes + installed-app list + shorter ScreenQA answers | **18** | Fixed "never answers" (0 → 6 answer tasks); passed the gate; frozen |
| v4-RL | 200 steps of GRPO on static screenshots, from v4 | not run | Failed its offline promotion rule |

Other base models trained with the v1 recipe: Qwen3.5-2B (16), Qwen3.5-0.8B (12), LFM2.5-VL-450M (2).

---

## Training recipe

Every LFM3-VL-2B version uses the same recipe and budget, so data and prompt are the only things that change.

| Setting | Value |
|---|---|
| Method | LoRA SFT on the language model only; vision tower frozen |
| LoRA | rank 64, alpha 128; attention, MLP and convolution projections |
| Optimiser | lr 2e-4, 1,250 steps × 32 rows (batch 8 × gradient accumulation 4) |
| Image | One screenshot per step, area budget 880 × 880 px (≈ 720 image tokens for a phone screen) |
| Input | Goal + text history of earlier steps + current screenshot (v4: + installed-app list) |
| Output | `<think>short intent</think>` + one JSON action, coordinates on a 0–1000 grid |
| Checkpoints | Pushed to the Hub every 50 steps so a lost VM can resume |

Code: [`train/sft_vlm.py`](../train/sft_vlm.py), prompt and action format in
[`train/agent_format.py`](../train/agent_format.py), job configs in
[`scripts/training/jobs/`](../scripts/training/jobs/).

### Action space

`click`, `long_press`, `input_text` (types, then presses Enter), `scroll` (up/down/left/right), `open_app`,
`navigate_back`, `navigate_home`, `keyboard_enter`, `wait`, `answer` (v4), `status` (`complete` / `infeasible`).

---

## Training runs

Source: each run's `run_config.json`, `train_summary.json` and `train_log.jsonl` under
[`results/training/`](../results/training/) and [`results/v4_dev/hub/training_logs/`](../results/v4_dev/hub/training_logs/).

| Run | Training rows | Train loss | Eval loss | Wall time | Peak GPU | Where |
|---|---|---|---|---|---|---|
| LFM3-VL-2B v1 | 99,216 | 0.285 | 0.288 | 1.1 h | 11.0 GB | Modal |
| LFM3-VL-2B v2 | 78,982 | 0.205 | 0.299 | 1.6 h | 10.2 GB | Colab |
| LFM3-VL-2B v3 | 78,952 | 0.385 | 0.300 | 1.2 h | 11.0 GB | Modal |
| **LFM3-VL-2B v4** | 92,229 | 0.336 | 0.306 | 2.0 h* | 11.5 GB | Colab A100 |
| Qwen3.5-2B v1 | 99,216 | 0.239 | 0.240 | 0.9 h | 10.8 GB | Colab |
| Qwen3.5-2B v2 | 78,982 | 0.168 | 0.250 | 1.6 h | 10.0 GB | Colab |
| Qwen3.5-0.8B v1 | 60,000 (1 epoch, LoRA r16, lr 1e-4) | 0.381 | 0.276 | 0.6 h | 8.3 GB | Colab |
| LFM2.5-VL-450M v1 | 60,000 (1 epoch, LoRA r16, lr 1e-4) | 0.469 | 0.375 | 1.0 h | 8.5 GB | Modal |

\* v4's VM was lost at step 353; training resumed from the step-350 Hub checkpoint. 2.0 h is the resumed part
(steps 351–1,250).

Losses are not comparable across versions: the data and prompts differ.

---

## v4-RL (not promoted)

| Item | Value |
|---|---|
| Start | v4 |
| Method | GRPO (TRL) on static screenshots, 4 samples per state, KL β 0.001, LoRA r16, lr 1e-5 |
| Data | 2,000 states (700 answer, 500 complete, 300 other, 500 click) |
| Run | 200 steps, 0.95 h on a Colab A100; mean reward 0.714 → 0.765 |
| Outcome | Answer match up (0.868 → 0.890) but AndroidControl step SR down (0.728 → 0.667): **failed** the rule fixed before training ended |
| Diagnosis | 60% of groups had zero reward variance; 60% of states were terminal screens |

Code: [`train/grpo_vlm.py`](../train/grpo_vlm.py), [`train/rl_reward.py`](../train/rl_reward.py);
decision: [`results/v4rl_promotion_offline.json`](../results/v4rl_promotion_offline.json).

---

## Released artifacts

Hugging Face, private unless noted.

| Artifact | Repository |
|---|---|
| **v4** (merged weights / GGUF) | `experimentalmachines/LFM3-VL-2B-AndroidAgent-v4`, `…-v4-GGUF` |
| v4-RL (not promoted) | `experimentalmachines/LFM3-VL-2B-AndroidAgent-v4-RL`, `…-v4-RL-GGUF` |
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
