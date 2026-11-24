# Preregistration: round 7 (v4.5), one full pass over twice the data with a longer memory

Written 2026-11-24 14:15 Asia/Manila (06:15 UTC), before any round-7 candidate existed. The training data was being
built at the time; its final counts go into the [Log](#log) before the first training step. Append-only: later entries
go under the Log with a timestamp.

**Status: post-hoc development round,** like rounds 5 and 6. The sealed v4 result (54/348) stays as it is.

---

## Why

| Evidence (ours) | Source |
|---|---|
| More training is the only change with a positive online sign so far: v4.3-sft (+500 steps) 24/116 vs v4's 18 (below the noise yardstick R = 9) | [results.md, round 5](results.md#round-5-learning-from-own-mistakes-vs-more-training-pre-registered-2026-11-22) |
| Every run so far saw 40,000 rows (1,250 × 32), 0.43 of v4's 92,229-row mix. The sources were capped too: AndroidControl 56,000 of 87,248 rows, GUI-Odyssey ≤ 3 rows per episode, AMEX ≤ 3 | [models.md](models.md#training-recipe), `results/data_v2/stats.json` |
| Round 6: long trajectories raised long-task accuracy (AndroidLens steps ≥ 10: 0.367 → 0.40–0.41) and end-of-task stopping (12% → 22–48%) | [PREREG_v44.md](PREREG_v44.md) |
| The prompt shows only the last 8 steps. AndroidLens accuracy falls from 0.54 (steps 0–4) to 0.33 (steps 20+) even with the true history | [evaluation.md](evaluation.md#androidlens-english-offline-long-tasks) |
| A step uses ~1,400 of the 4,096-token context (system 276, user text 310–485, screenshot 720); a history line is ~26 tokens | measured 2026-11-24 |
| Training on a Colab A100 is GPU-bound (92% busy at 4.23 rows/s); without gradient checkpointing (bs 4 × 8) 6.35 rows/s, same loss | `results/v45_dev/speedcheck*` |

---

## Data: `experimentalmachines/MobileAgent-SFT-v4.5` (public)

Built on an AWS EC2 CPU instance with `data/build_v2_mix.py` (round-7 switches, defaults unchanged) and
`data/v45_build_mix.py`. Every row: v4 system prompt, installed-app line, **24-step text history**, and
**" [no visible change]" notes** (round 6's rule).

| Part | Content |
|---|---|
| AndroidControl | **All** high-level steps and terminal rows of the v1 train split (portrait, AndroidWorld-alias episodes dropped), minus v4's 200 held-out dev episodes (`data/meta/v4_heldout_episodes.json`) |
| GUI-Odyssey | **All** train candidates under v2's rules and split (`hflqf88888/GUIOdyssey` annotations and `random_split.json`, screenshots from `OpenGVLab/GUI-Odyssey` @ `71e0e7e2`); no per-episode cap |
| AMEX | **All** train candidates under v2's rules (`Yuxiang007/AMEX` @ `17196b29`); no per-episode cap |
| ScreenQA, navigate-then-answer | v4's rows (`MobileAgent-SFT-v4` @ `3375539`), history and notes updated |
| MemGUI | Round 6's 8,505 rows rebuilt with the 24-step history |

**Cleaning and relabelling**

| Step | Rule |
|---|---|
| Blank intents (GUI-Odyssey inconsistent ones, all of AMEX) | Aguvis stage-2 L2 step instruction (`xlangai/aguvis-stage2` @ `bd6f1ed4`, Apache-2.0) if `intent_consistent()` accepts it, else v3's templates. AMEX matched by `<episode>step<k>.png` (k = step position; all 24,802 checked taps agree), GUI-Odyssey by file name (98.2% of checked taps agree) |
| Click rows still without an intent | Not training targets (they stay in later rows' history) |
| End of AndroidControl episodes (train only) | If the last step before the terminal row is a `scroll` or `wait` with no visible change, it is dropped and the terminal row's history no longer lists it. The test split keeps the official labels |
| Screen-disjointness | Train rows whose image is byte-identical to any gate or dev image are dropped; exact duplicates dropped |
| Contamination | As v2/v4: AndroidWorld app / package / alias filters, no AndroidWorld, MobileWorld or AndroidLab tasks, trajectories, checkers or seeded content. AndroidLens stays evaluation-only |

---

## Candidate D (the only one)

| Item | Value |
|---|---|
| Start | `LiquidAI/LFM3-VL-2B` (as v4) |
| Recipe | v4's: LoRA r64 α128 on the language model, vision frozen, lr 2e-4 cosine with 3% warm-up, 32 rows per optimizer step, thinking on |
| Amount | **One pass** over the train split: steps = ⌈rows / 32⌉, each row seen once |
| Throughput setting | No gradient checkpointing; micro-batch 4 × 8 or 8 × 4 (same maths), whichever the smoke job measures faster |
| Hardware | AWS SageMaker `ml.g7e.2xlarge` (RTX PRO 6000, 96 GB), owner-approved; checkpoints every 250 steps synced to S3 |

**Smoke job first:** 30 steps of each micro-batch setting on 2,000 rows, then every eval on 16 rows, every scorer and
the gate script. D does not start before it passes.

---

## Offline gate (all must hold; same evaluator as round 6)

D is evaluated on its own prompt format; v4's numbers are round 6's V4REF on v4's own format
(`scripts/training/v4_reference_r7.json`).

| Check | v4 | Bar |
|---|---|---|
| AndroidControl test, high-level step accuracy | 0.727 | ≥ 0.707 (v4 − 0.02) |
| `dev_answer` | 0.890 | ≥ 0.840 (v4 − 0.05) |
| `dev_complete` | 0.763 | ≥ 0.713 (v4 − 0.05) |
| **New:** AndroidControl test, predicted `status` at least 2 steps before the episode's terminal row | 2.74% | ≤ 3.24% (v4 + 0.5 pt) |
| AndroidLens English, step accuracy at steps ≥ 10 | 0.367 | ≥ 0.367 (no loss) |

**Why the stopping check changed (from round 6's results, before any round-7 candidate):** round 6's check counted
`status` at steps ≥ 4. Half of v4's such stops were one step before the end, where the human demonstrations add a final
scroll or wait. Stops one step before the end (v4: 13.2%) are therefore reported, not gated.

**Reported, not gated:** AndroidLens all-steps accuracy, `complete` at the real end, early `status`; AndroidControl
terminal `complete`; `dev_memgui`; round 6's late-step `status` rate.

---

## Online test (only if the offline gate passes)

| Item | Value |
|---|---|
| Benchmark | AndroidWorld development seed 30, 116 tasks, on the Mac (2 emulators), as every earlier seed-30 run |
| Harness | v4's sealed seed-30 harness plus two options matching D's training: 24-step history and the no-visible-change note (no other runtime feedback, no guards) |
| Pass rule | Net paired gain over v4 ≥ R = 9 tasks, **or** successes ≥ 18 with false `complete` ≤ 15 (round 5's rule shape) |
| After a pass | A held-out run is proposed in a new Log entry; nothing is promoted automatically |

**If D fails the offline gate:** round 7 is reported as negative, D's weights are published as not promoted, no
online run.

---

## Allowed without a new entry

- Resuming an interrupted job from its last checkpoint with the same configuration.
- The micro-batch choice above (it does not change the maths).

---

## Log

### 2026-11-24 14:30 Asia/Manila — data built; smoke job started (no candidate exists)

**Training split: 173,430 rows** (v4: 92,229). D's one pass = ⌈173,430 / 32⌉ = **5,420 steps**.

| Source | Rows | Notes |
|---|---|---|
| AndroidControl | 82,569 | All 87,248 stage rows − 1,324 rows of the 200 held-out episodes − 201 end-of-episode no-ops (+ dedupe). Every 24-step history matched the stored 8-step text (85,723 / 85,723) |
| AndroidControl question copies (#qa) | 14,218 | From v4; 64 lost a cleaned final no-op line |
| GUI-Odyssey | 40,218 | 41,247 candidates (v2: 44,207; 318 episodes are cut where `OpenGVLab/GUI-Odyssey`'s screenshot zip lacks a screen); 7,201 intents from Aguvis, 39 from templates; 866 blank click targets dropped |
| AMEX | 21,925 | 22,625 candidates; 22,674 intents from Aguvis (incl. dev rows), 446 from templates; 675 blank click targets dropped; v2's input_text quota (also a ceiling at 1,000) switched off |
| MemGUI | 8,505 | Round 6's rows with the 24-step history |
| ScreenQA | 5,995 | v4's rows |

- **Dropped:** 276 rows sharing an image with a gate / dev split; 3,055 exact duplicates (found: v4's training
  data held 3,062 navigate-then-answer rows twice).
- **Rows showing more than 8 history steps:** train 31,216; AndroidControl test 780; AndroidLens 3,439.
- **Sources pinned:** v1 @ `f88a8432`, v4 @ `3375539`, OpenGVLab/GUI-Odyssey @ `71e0e7e2` (screenshots),
  hflqf88888/GUIOdyssey @ `61632d0f` (annotations, `random_split.json`), Yuxiang007/AMEX @ `17196b29`,
  xlangai/aguvis-stage2 @ `bd6f1ed4`, MemGUI-3K @ `003822b5`, AndroidLens @ `984576f3`.
- **Statistics:** `results/v45_dev/build_stats.json`, `stats_odyssey.json`, `stats_amex.json`, `stats_ac.json`.
- **AndroidWorld harness:** new opt-in flags `--history_steps` and `--nochange_notes` (defaults = v4's sealed harness).

### 2026-11-24 15:50 Asia/Manila — hardware changed by the owner before any training step (no candidate exists)

- **What changed:** SageMaker never assigned a GPU (both smoke jobs waited for capacity, then were stopped without
  billing). The owner said: "Run it on google colab and we'll switch to modal later, checkpoint well".
- **D's recipe is unchanged:** one pass, 5,420 steps × 32 rows, bs 4 × 8 without gradient checkpointing (measured on
  the Colab A100: same loss as 8 × 4, 1.5× faster), base `LiquidAI/LFM3-VL-2B` pinned to `23387bed`, training data
  `experimentalmachines/MobileAgent-SFT-v4.5` pinned to `45331aaa`.
- **Checkpoints:** every 100 steps, pushed to the public repo `experimentalmachines/LFM3-VL-2B-MobileAgent-v4.5-D-ckpt`
  (private Hub storage is full). The resume check compares data id and revision, steps, batch, LoRA and lr, so the same
  command resumes on a new Colab VM or on Modal. A guard stops the Colab session below 1.5 units.
- **Before the run:** a smoke test on Colab (4 steps on 200 rows, saves every 2 steps to a separate public repo, local
  folder deleted, then the command must restore step 4 from the Hub).
- **Evals and gate:** unchanged, on whichever platform finishes training (`scripts/training/sm_r7.sh`'s eval and gate
  steps, or the same scripts on Modal).
