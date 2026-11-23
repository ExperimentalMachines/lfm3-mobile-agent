# Models

**Contents:** [Versions](#versions-at-a-glance) · [v1–v3 in detail](#v1v3-in-detail) · [Recipe](#training-recipe) ·
[Training runs](#training-runs) · [v4-RL](#v4-rl-not-promoted) · [Released artifacts](#released-artifacts)

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
| v4.3-dpo | v4.2 + DPO on all 4,163 of its own mistakes ([round 5](results.md#round-5-learning-from-own-mistakes-vs-more-training-pre-registered-2026-11-22)) | not run | Failed offline (AC 0.732 → 0.545): DPO on generic wrong clicks pushed down whole action types |
| v4.3-dpo2 | v4.2 + DPO on 851 balanced stop / copied-intent mistakes | 21 | Net +3 vs v4.2 is noise (R = 9); stopping not measurably changed (false `complete` 28) |
| v4.3-sft | v4.2 + 500 more SFT steps on the same mix ("more epochs") | 24 | Best LFM3 seed-30 count, but +6 vs v4.2 is below the noise yardstick (9); it stops more often at unchanged precision, so false `complete` rose to 37 |

Other base models on v1's data: Qwen3.5-2B with the same recipe (16); Qwen3.5-0.8B and LFM2.5-VL-450M with a
smaller one (LoRA r16, 1 epoch): 12 and 2.

---

## v1–v3 in detail

The three versions before v4 (2026-11-16 to 18). They share one recipe ([below](#training-recipe)), so the training
data is what changed. Sources: [`results/SUMMARY.md`](../results/SUMMARY.md),
[`results/V2_COMPARISON.md`](../results/V2_COMPARISON.md), [`results/v3_dev/`](../results/v3_dev/),
[seed-30 results](results.md#androidworld-development-seed-30), failure causes from
[`results/androidworld/failure_taxonomy_20261122.json`](../results/androidworld/failure_taxonomy_20261122.json).

| | v1 | v2 | v3 |
|---|---|---|---|
| Built | 11-16 → 11-17, Modal | 11-17, Colab | 11-17 → 11-18, Modal H100 |
| Question it tested | Does LoRA SFT on AndroidControl make LFM3 an agent? | Do more data sources help? | Were v2's blank intents the problem? |
| Training data | AndroidControl only, 99,216 rows | + GUI-Odyssey, AMEX, ScreenQA: 78,982 rows | v2 with its 8,739 blank intents filled: 78,952 rows |
| AndroidControl high / low / terminal `complete` | 0.715 / **0.948** / 0.792 | 0.716 / 0.893 / 0.732 | 0.723 / 0.902 / 0.725 |
| Dev splits: GUI-Odyssey / AMEX / ScreenQA | 0.269 / 0.306 / 0.000 | 0.644 / 0.735 / **0.764** | **0.662 / 0.741** / 0.724 |
| MMStar / MMLU (base 52.1% / 48.9%) | 57.1% / 49.5% | 54.6% / 50.9% | 55.3% / 50.0% |
| **AndroidWorld seed 30** (/116) | **15** | 3 | 13 |
| Answer tasks solved (seed 30, /25) | 0 | 0 | 0 |
| Most common failure (seed 30) | False `complete` (27) | Stuck repeating one intent (24) | Stuck repeating one intent (41) |
| Held-out AndroidWorld (/348) | 32 (seeds 7 / 1234 / 2026: 11 / 10 / 11) | not run | not run |
| MobileWorld | not run | not run | not run |
| Apple M5, median s/step | 2.66 | 2.61 | 2.61 |
| Hugging Face (public) | [`LFM3-VL-2B-MobileAgent-v1`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v1) (+ `-GGUF`) | [`LFM3-VL-2B-MobileAgent-v2`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v2) (+ `-GGUF`) | [`LFM3-VL-2B-MobileAgent-v3`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-v3) (+ `-GGUF`) |
| Local GGUF (git-ignored) | `models/LFM3-VL-2B-AndroidControl-GGUF/` | `models/lfm3vl2b_v2-GGUF/` | `models/lfm3vl2b_v3-GGUF/` |

### v1: AndroidControl only

- **Result:** base 1/116 → 15/116 on seed 30 (paired p = 1.2 × 10⁻⁴). The best LFM3 version at single actions of
  those measured (low-level step SR 0.948).
- **Weaknesses:** it never uses `answer` (AndroidControl has no answer supervision), so every answer task fails. A
  third of its steps are `wait`, all under an intent that is not about waiting: the copied-intent pattern later traced
  to AndroidControl's labels and fixed in v4.1.
- **Codex review** ([final_results_eval](../results/codex/codex_final_eval.md)): offline gains real, robust phone use not
  shown. Its first suggestion became the **runtime-feedback ablation** (app-name resolution + failure notes at
  inference): 10/116, worse, dropped.
- **What we did with it:**
  - Kept as "our first model" in the preregistered held-out comparison: 32/348.
    - v4 − v1 = +6.3 points (95% CI +1.1 to +11.5, p = 0.02).
    - v1 − GUI-Owl = −4.3 points (p = 0.21).
    - One disputed checker success (seed 2026, OpenAppTaskEval).
  - The same data trained Qwen3.5-2B (16/116), Qwen3.5-0.8B (12) and LFM2.5-VL-450M (2) for a base-model comparison.

### v2: more data sources

- **Data:** four Codex data audits before training (three No-go, then Go on `42f7f763`). They fixed train/dev screen
  leakage and conversion bugs.
- **Offline:** large gains on the new dev splits (GUI-Odyssey 0.27 → 0.64, AMEX 0.31 → 0.74, ScreenQA answers 0 →
  0.76), but lower low-level and terminal `complete` accuracy than v1.
- **AndroidWorld:** collapsed to 3/116 (v1-only 11 tasks, v2-only 0, p = 0.001). 30.4% of its steps had an empty
  intent; 8,739 training rows had a blank intent.
- **Forced-intent ablation:** forcing a one-line intent at inference gave 6/116 (+3 / −0 vs v2, p = 0.25). This
  supports the blank-intent suspicion, but the effect is small and the data mix changed too.
- **What we did with it:**
  - Published the model and GGUF (private at first; public since 2026-11-23).
  - Made the dataset public (now superseded).
  - Trained Qwen3.5-2B on the same data (offline only; AndroidWorld not run).
  - Built v3 to test the blank-intent explanation.

### v3: v2 with the intents filled

- **Data:**
  - 2,603 blank intents filled from action templates.
  - 6,106 filled by a teacher model.
  - 30 rows dropped.
  - Empty intents on the dev splits fell to 0% (v2: 100% on AMEX, 13.5% on GUI-Odyssey).
- **Offline:** close to v2. ScreenQA was lower (0.724 vs 0.764, p = 0.008) because v3 gave more full-sentence answers.
- **AndroidWorld:** 13/116.
  - Recovered from v2: v3-only 10 tasks, v2-only 0, p = 0.002.
  - Not above v1: v1-only 6, v3-only 4, p = 0.75.
  - Still no `answer` actions, although ScreenQA was in its training data.
- **Codex review** ([v3_audit](../results/codex/codex_v3_audit.md)): numbers reproduce; No-go on the model-card
  wording, which was fixed.
- **What we did with it:**
  - Published the model and GGUF (private at first; public since 2026-11-23).
  - Its data became v4's base: v3's rows in the v4 prompt, plus navigate-then-answer episodes, the installed-app list
    and shorter ScreenQA answers.
  - Its 13 action successes set part of v4's gate: action successes ≥ v3 − 3.

### What v1–v3 taught us

| Lesson | Seen in | Acted on |
|---|---|---|
| Offline gains on new datasets do not predict AndroidWorld | v2, v3 | AndroidWorld seed 30 became part of the gate (v4) |
| Blank intents break the agent loop | v2 | v3 filled them |
| Copied `wait` intents cause loops | v1–v4 | v4.1 relabelled them; v4.2 halved loops on MobileWorld |
| ScreenQA alone does not make the agent `answer` | v2, v3 (0 answer tasks) | v4: navigate-then-answer episodes + answer rules in the prompt (0 → 6 answer tasks) |
| Long ScreenQA answers | v3 | v4: shorter answers |
| Inference-time patches did not replace data fixes | v1 + runtime feedback (10), v2 + forced intent (6) | Dropped |

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
| Qwen3.5-2B v1, v2 | [`Qwen3.5-2B-MobileAgent-v1`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-v1), [`…-v2`](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-v2) | `…-v1-GGUF`, `…-v2-GGUF` | Comparison |
| Qwen3.5-0.8B v1 | [`Qwen3.5-0.8B-MobileAgent-v1`](https://huggingface.co/experimentalmachines/Qwen3.5-0.8B-MobileAgent-v1) | `…-v1-GGUF` | Comparison |
| LFM2.5-VL-450M v1 | [`LFM2.5-VL-450M-MobileAgent-v1`](https://huggingface.co/experimentalmachines/LFM2.5-VL-450M-MobileAgent-v1) | `…-v1-GGUF` | Comparison |

| Dataset | Revision used for training | Trains |
|---|---|---|
| [`MobileAgent-SFT-v1`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v1) | (not pinned) | v1 and the comparison fine-tunes; its `test` split is the AndroidControl test set used offline |
| [`MobileAgent-SFT-v2`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v2) | `42f7f763` | v2, Qwen3.5-2B v2 |
| [`MobileAgent-SFT-v3`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v3) | `565ba76c` | v3 |
| [`MobileAgent-SFT-v4`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v4) | `3375539` | v4; v4.1 / v4.2 rebuild their data from it |
| [`MobileAgent-RL-v4`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-RL-v4) | `9ba36d90` | v4-RL |

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
