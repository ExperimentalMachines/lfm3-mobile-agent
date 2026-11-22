# Train on own mistakes, not more epochs

Written 2026-11-22, after the v4.1/v4.2 seed-30 runs ([PREREG_v41.md](../PREREG_v41.md)). The MobileWorld run of v4.2 finished after the report was drafted:

| MobileWorld (105 tasks) | v4 | v4.2 |
|---|---|---|
| Successes | 6 | 8 (+3 / −1, McNemar p = 0.63) |
| Steps that are `wait` | 21% | 5% |
| Steps repeating the previous intent | 67% | 33% |
| Tasks ending at the 50-step limit | 85 | 69 |

Loops halved, but success barely moved. That matches this report's main finding: removing loops frees steps, and the model then wanders or stops early instead of finishing ([mw_r3_comparison.md](../../results/mobileworld/mw_r3_comparison.md)).

**Bottom line**

- **What is going wrong:** two behaviours that our training data never corrects cause about two-thirds of held-out failures.
  - **Looping:** the model repeats an action that changed nothing until it runs out of steps (44% of held-out failures).
  - **Stopping early:** the model says `complete` before the task is done (24%).
  - Every LFM3 version has made 20–28 false `complete`s per 116 tasks. GUI-Owl made 0 on seed 30.
- **Not the cause:** too few epochs, too small a LoRA, or bad hyperparameters. Train loss over the last 100 steps equals validation loss (0.305 vs 0.306); at 0.43 epoch each row is seen at most once, so this shows no memorisation rather than spare capacity. The loss curve flattened because the learning rate reached zero. Rank, LoRA variant and learning rate are all in the range where published studies find little left to gain (1–2% or less).
- **Best next step:** step-level preference training (DPO) on the model's own wrong answers at the same screens.
  - Sample the model's own actions where it disagrees with the human step, then train it to prefer the human step.
  - It needs no teacher and no emulator, and has a 2B result.
  - Rollouts on non-benchmark apps with adb-checked rewards are the second step. They need about half a day of engineering and a full day of emulator time.
- **Speed:** on the phone, 20–40 extra output tokens add only 1–3% per step, because reading the screenshot dominates step time. A short, trained check before acting or stopping is affordable. Longer prompts are what cost time: extra screenshots, long history summaries, and re-asking the model.
- **Evaluation:** a single 116-task pass cannot detect changes smaller than about 9 points. Decide on behaviour counts and no-regression gates instead. Keep the new held-out benchmarks (AndroidLab, sealed seeds) for frozen versions only.

**Abbreviations and labels**

| Short | Meaning |
|---|---|
| AW / MW | AndroidWorld / MobileWorld (online benchmarks) |
| AC | AndroidControl (offline dataset and test split) |
| SS-v2 | ScreenSpot-v2 (single-screen grounding benchmark) |
| SFT | Supervised fine-tuning (imitating human steps) |
| DPO | Preference training: push up the preferred action, push down the rejected one, at the same screen |
| WSD | Learning-rate schedule: warm-up, stay constant, short cool-down at the end |
| False `complete` | The agent declared the task done; the checker says it is not |
| Ours / Reported / Inference | Measured in this repo / the authors' own number / my reasoning, not measured |

---

## Short answers to the nine questions

| Question | Short answer | Confidence |
|---|---|---|
| Where are we going wrong? | Loops after no-effect actions and false `complete`s, neither ever targeted in training. Also: choosing versions on one noisy seed-30 pass, and trusting offline metrics that do not track online success | High (ours) |
| Train more epochs? | Not as the main lever. One epoch alone costs ~6.3 A100-hours, more than the budget. Test "more training" only with fresh rows and a WSD schedule | Medium |
| Learn from own attempts without a paid teacher or benchmark environments? | Yes. Step-level DPO on own wrong samples at v4.2's replay states (no emulator). Later: own rollouts on non-benchmark apps, rewarded by adb state checks | Medium (the 2B evidence is not mobile) |
| Bigger LoRA: good or bad? | Neither. It is not useful at our data size. If tested, keep α fixed, or the effective learning rate jumps ~4× | Medium–high |
| Between LoRA and full fine-tuning? | Yes: projector training, vision LoRA, partial unfreezing (LISA, Spectrum), full LM fine-tuning. Not recommended now | Medium |
| Is it hyperparameters? | No. Change only the schedule (cosine → WSD), so that checkpoints answer "would more training help?" | Medium–high |
| Would short reasoning slow replies too much? | Not on the phone (+1–3% for 20–40 tokens). On the Mac GPU it costs +15–44%. Keep it ≤10–15 tokens, trained, and out of the history | High for speed; low for quality gain |
| Is the dataset varied enough? | Many apps, few kinds of supervision: no recovery, no "give up", no drag, almost no long histories | High (ours) |
| Do our benchmarks suffice? Add GUI-Owl's? | Enough for the narrow matched claim. Add SS-v2, AndroidLab, a v4 replicate run and AC-Curated rescoring. Skip GUI-Owl's desktop benchmarks | Medium–high |
| How do we avoid overfitting and benchmark-maxxing? | Pre-declared behaviour gates, paired comparisons, held-out sets touched only by frozen versions, and an exposure table per model | — |

---

## Two untrained behaviours cause two-thirds of held-out failures

### Why held-out v4 episodes failed

Computed from the 348 sealed-seed episodes per model ([ours](../../results/androidworld_sealed/)). Each failure has one primary category: per-run counts in [failure_taxonomy_20261122.json](../../results/androidworld/failure_taxonomy_20261122.json) (`primary`), built by [analysis/failure_analysis/](../../analysis/failure_analysis/).

| Failure | Held-out v4 (294 failures) | Seed 30: v4 / v4.2 | MW v4 (99 failures) | Training signal today |
|---|---|---|---|---|
| **Loop:** same intent, `wait` or repeated tap on an unchanged screen until the step budget runs out | **129 (44%)** | 44 / 28 | 77 | None. v4.2 showed the model its own mistake in only 128 rows ([ours](../../results/v42/selfhist_stats.json)) |
| **False `complete`** | **71 (24%)** | 25 / 25 | 12 "finished" + 3 answers | None. One synthetic `complete` per AC episode; no "looks done but isn't" examples |
| Wandering with no progress (no stable loop) | 44 (15%) | 11 / 24 | 6 | App and navigation knowledge |
| Wrong or too-early answer | 41 (14%) | 14 / 11 | 3 | Answers come mostly from single-screen ScreenQA |

- **Looping and stopping early are separate problems.** Only 1 of v4's 25 false-`complete` episodes on seed 30 contains a loop. Fixing one does not fix the other.
- **Loops start early.** On MW the final same-intent loop starts at a median of step 6 of 50. A bigger step budget would not help.
- **A likely trigger is a tap that does nothing.** In failed episodes, ~25% of first taps under a new intent change nothing on screen. In successful ones it is 2–4%. This is a proxy based on screen difference ([ours](../../results/androidworld/)).

### GUI-Owl's edge is restraint, not skill

| Episodes the agent ended itself | v4 seed 30 | v4.2 seed 30 | GUI-Owl seed 30 | v4 held-out | GUI-Owl held-out |
|---|---|---|---|---|---|
| Ended with `complete` or `answer` | 57 | 54 | 24 | 167 | 64 |
| Of those, correct | 18 | 18 | 23 | 54 | 47 |
| **Precision** | 32% | 33% | **96%** | 32% | **73%** |

- GUI-Owl still runs out of steps on 92 of 116 seed-30 tasks. It wins by not stopping wrongly and by browsing before it answers ([ours](../../results/androidworld/)).
- **Where v4 is already better:**

  | Subset (held-out) | v4 | GUI-Owl |
  |---|---|---|
  | Generic apps | 27.4% | 16.7% |
  | Easy tasks | 50 of 183 | 33 of 183 |

- **Where GUI-Owl is better:** medium tasks (11 vs 3 of 108) and hard tasks (3 vs 1 of 57) ([ours](../results.md)).

### What our fixes changed

| Change | Visible effect | Seed-30 successes |
|---|---|---|
| v4.1: `wait` relabel + 10% repeated steps in history | `wait` share 29.1% → 8.7% of steps | 18 → 12 (p = 0.11) |
| v4.2: training on its own replayed history (wrong steps replaced by the human step) | Copied intents 56% → 38%; waits turned into repeated taps | 18 → 18 (6 tasks gained, 6 lost) |
| Runtime loop guards on v4 | `wait` 0%; 34% more model calls | 18 → 18 |
| v4, v4 + guards, v4.1, v4.2 | 53–55 episodes still run out of steps in each | — |

Source: [PREREG_v41.md](../PREREG_v41.md) and seed-30 episode files ([ours](../../results/androidworld/)).

### Process mistakes

- **We pick versions on one noisy pass.**
  - No paired seed-30 change is significant (exact McNemar p = 0.11 to 1.0).
  - Only 3 tasks were solved by all six v4-family runs ([ours](../../results/androidworld/)).
- **Offline metrics have misled us.**
  - v4.1 looked better offline: `dev_complete` 0.850 vs 0.762, AC high-level 0.732 vs 0.728.
  - Online it scored 12 vs 18 ([PREREG_v41.md](../PREREG_v41.md)).
  - Across six versions, AC step accuracy rank-correlates only 0.28 with AW success (ours, n = 6).
- **The early-stop rate has never moved.**
  - On non-terminal AC test steps, v4 predicts `status` on 4.6% of steps. v2, v3 and Qwen3.5-2B all sit at 4.6–5.5%.
  - At ~5% per step, a 10-step task has roughly a one-in-three chance of an early stop (inference, assuming independent steps).
- **Some skills are missing by design:**
  - Drag and slider moves were cut out of the data. No v4-family run solved any of the four AW brightness tasks, and v4 looped on both MW brightness tasks.
  - There are 12 `keyboard_enter` rows.
  - No LFM3 run solved any of the five SimpleCalendarAdd tasks (date and time pickers).

---

## More epochs would lower loss, not fix behaviour

### What the v4 training logs show

Source: [log_history.json](../../results/v4_dev/hub/training_logs/log_history.json), [train_summary.json](../../results/v4_dev/hub/training_logs/train_summary.json).

| Signal | Value | Reading |
|---|---|---|
| Train vs validation loss at the end | 0.305 (mean of the last 100 steps; the whole-run average is 0.336) vs 0.306 | No memorisation (each row is seen at most once) |
| Data seen | 0.434 epoch (40k of 92k rows), no row repeated | Most rows never seen |
| Validation gain per 250 steps | −0.021, −0.024, −0.010, −0.003 | Flattening… |
| Learning rate | 2e-5 by step 1,000; 0 at ~1,240 (cosine) | …because the learning rate reached zero |
| Validation entropy vs loss | 0.309 vs 0.306 | The remaining loss is real uncertainty: intent wording or label noise (inference) |

### Evidence from published recipes

| Finding | Source |
|---|---|
| GUI SFT recipes use 1–3 epochs (Aguvis 1 per stage, GUI-Libra 2, AgentCPM-GUI 3, AppVLM 3 per round), usually with full fine-tuning at lr ~1e-5 | [Aguvis](https://arxiv.org/abs/2412.04454), [GUI-Libra](https://arxiv.org/abs/2602.22190), [AgentCPM-GUI](https://arxiv.org/abs/2506.01391), [AppVLM](https://arxiv.org/abs/2502.06395) |
| General SFT stops improving after ~2 epochs. Fresh rows beat repeated rows in all 12 comparisons (mean 16% lower NLL) | [2609.01244](https://arxiv.org/abs/2609.01244) |
| Cosine schedules hide progress partway through a run. Constant LR plus a short cool-down matches cosine, and a cool-down can branch from any saved checkpoint | [Hägele et al.](https://arxiv.org/abs/2405.18392) |
| More AndroidControl data widens the gap between familiar and unfamiliar apps | [AndroidControl](https://arxiv.org/abs/2406.03679) |

### Cost

| Option | Colab A100 at 4.07 rows/s ([ours](../../results/v4_dev/hub/training_logs/train_summary.json)) |
|---|---|
| One v4-sized run (40k rows) | ~2.7 h |
| One epoch of 92k rows | ~6.3 h (v4's resumed segment: 900 steps × 32 rows in 7,074 s = 4.1 rows/s) |
| Two epochs | ~12.6 h |

- The same recipe ran 2.2× faster on Modal (9.09 rows/s) ([ours](../../results/training/lfm3vl2b_v3/train_summary.json)).
- Check GPU use in the first minutes of the next run. If it is below ~80%, the data loader is the limit, and fixing it buys more rows than any training change (inference).

### What to do

- **Do not repeat the same rows as the main lever.** The two biggest failures have no example in the data to learn from. More passes cannot add one.
- **Test "more training" cheaply:**
  - Use never-seen rows (57% of the mix) in a run that is needed anyway.
  - Use a WSD schedule with a branch checkpoint, which gives two training lengths from one run.
- **Cheaper first check (A100, minutes):**
  - Compare loss on seen and never-seen rows.
  - Split validation loss by part: intent text, action type, coordinates.
  - If most of the remaining loss is intent wording, more steps will polish wording, not actions (inference).

---

## Own mistakes teach most when paired with the right step

### What own-attempt methods achieved

| Method | What the model learns from | Size | Result (reported unless ours) | Needs | Fit today |
|---|---|---|---|---|---|
| **Agentic-DPO** ([2607.10601](https://arxiv.org/abs/2607.10601)) | Its own one-step mistakes (rejected) vs the human step (preferred); DPO plus 0.5 × SFT anchor | **2B** (Qwen3.5) | Mind2Web step success 35.4 → 52.3; τ-bench 18.0 → 35.2, above online GRPO's 32.1 | An SFT start; 2–4 samples per state; ~1.6× SFT cost per step | **High**: our v4.2 replay states already exist |
| Digi-Q ([2502.15760](https://arxiv.org/abs/2502.15760)) | Its own best of 16 samples, ranked by an offline value model | 3–7B | AitW 71.2 vs 54.5 for filtering successes alone | A value model; failures in the data | Low |
| UI-S1 ([2509.11543](https://arxiv.org/abs/2509.11543)) | Its own history over human screens (RL) | 3B / 7B | AW 5.0 → 13.1 (3B); 21.7 → 34.0 (7B) | RL stack; 32 GPUs | Later |
| DeLoop ([2610.19376](https://arxiv.org/abs/2610.19376)) | Its own loop-then-recover rollouts as DPO pairs | 8B | Loops 57.3% → 6.1% of tasks; success only 25.1 → 25.9 | An environment | Pilot first |
| VeriGUI ([2604.05477](https://arxiv.org/abs/2604.05477)) | 30% rows with a failed previous action on an unchanged screen | 3B | Recovery 29.7% → 45.5%; step success −0.9. At 50% rows, step success 42.6 → 39.2 | Failure rows (GPT-4o wrote them) | Fallback recipe |
| v4.2 (ours) | Own history; wrong steps replaced by the human step | LFM3 2B | 18 → 18 | — | Done: it had no contrast between own mistake and right step |
| v4-RL static GRPO (ours) | 4 samples per state | LFM3 2B | AC 0.728 → 0.667; 66% of groups had no reward variance ([models.md](../models.md)) | — | Failed |

- **Large gains come from contrasting a wrong and a right action at the same screen.** Re-imitating the model's own correct steps adds less:
  - Digi-Q vs filtering successes: 71.2 vs 54.5 ([Digi-Q](https://arxiv.org/abs/2502.15760)).
  - Self-distillation at fork points vs rejection fine-tuning: 81.0 vs 73.2 ([UI-Voyager](https://arxiv.org/abs/2603.24533)). UI-Voyager trained on AW templates, which our rule forbids, so read this as a method comparison only.
  - v4.2's null result fits this pattern.
- **Anchors matter at 2B.** Agentic-DPO reached 0% without an SFT warm-up and lost 14–18 points without the SFT anchor. Its 2B model overfit after the best refresh round ([Agentic-DPO](https://arxiv.org/abs/2607.10601)).

### Recipe for our step-level DPO

- **States:** v4.2's replayed self-history states on AC, GUI-Odyssey and AMEX training episodes. The saved decisions ([selfhist_state.json.gz](../../results/v42/selfhist_state.json.gz), written by [v42_selfhist.py](../../data/v42_selfhist.py)) are enough to rebuild them.
- **Samples:** 4 per state from v4.2 at temperature ~0.8.
- **Pairs:** preferred = the human step; rejected = an own sample that differs. Over-sample three kinds:
  - `complete` or `answer` at a step that is not the last;
  - `wait` where the human interacted;
  - a copied intent where the human's intent changed.
- **Loss:** DPO + 0.5 × SFT on the preferred step. Small β (0.008 in the paper). At most one refresh round. About 500 steps (~1.7 A100-h at 1.6× SFT cost, inference).
- **Fallback if the DPO trainer cannot take LFM3-VL's image format in the preflight:** own-mistake recovery rows in the existing SFT pipeline.
  - Keep the model's own no-effect step (`wait` or a repeat) in the history.
  - Keep the same screenshot, and use the human action as the target.
  - Use them for ≤30% of rows (the VeriGUI dose that worked).
  - Use only no-effect mistakes. For wrong taps the real next screen is unknown, and fabricated screens hurt in BacktrackAgent ([2505.20660](https://arxiv.org/abs/2505.20660)).

### Rollouts in real apps, without a paid teacher or benchmark environments

| Reward source | Evidence (reported) | Use |
|---|---|---|
| **adb state checks** (`settings get`, `dumpsys alarm`, contacts provider, files on `/sdcard`) | GRPO on AW with rule rewards scored 36.8, against 30.2 for the best judge and 26.4 for a Qwen judge ([MobileJudgeBench](https://arxiv.org/abs/2608.11434)) | Yes, for self-made tasks |
| **Hindsight relabelling** (describe what the rollout actually did) | NNetNav, with open models only: 7.2 vs 4.2 WebArena against instruction-first data ([NNetNav](https://arxiv.org/abs/2410.02907)) | Yes. An adb state diff can replace the labelling model (inference) |
| **Open VLM judge** | Qwen judge: 85.7% accuracy, but 71 false positives vs 7 false negatives ([MobileJudgeBench](https://arxiv.org/abs/2608.11434)) | Answer tasks only. At our ~15% success rate, a 10% false-positive rate makes ~39% of "successes" wrong (inference) |

- **Our scale (inference from our timings):**

  | Item | Estimate |
  |---|---|
  | AW-length episodes, two emulators, 20 h | ~1,700 |
  | Short self-made tasks, same 20 h | ~2,200–2,400 |
  | Tasks covered at 4 tries each | 400–600 |
  | Verified successful steps | 2–5k |

  The online methods with double-digit gains ran far more in parallel. ARPO used 256 parallel environments ([ARPO](https://arxiv.org/abs/2505.16282)). MAI-UI used 32–512 and saw early saturation with fewer ([MAI-UI](https://arxiv.org/abs/2512.22047)).
- **Expect little transfer to the benchmark apps:**

  | Study | Gain on apps or tasks not trained on |
  |---|---|
  | ZeroGUI, self-generated tasks only ([ZeroGUI](https://arxiv.org/abs/2505.23762)) | +0.5 to +0.7 |
  | ARPO, out-of-domain ([ARPO](https://arxiv.org/abs/2505.16282)) | +1.1 (plain GRPO: −3.1) |
  | GRPO with many tasks ([AW-Generalization](https://arxiv.org/abs/2603.07432)) | +8.3 on unseen apps |

  A realistic hope is 0 to +3 AW tasks (inference). What transfers is behaviour (stopping, recovering), not app knowledge.
- **Which apps:**
  - Settings, Clock, Contacts and Files, with task text deduplicated against the 116 AW templates and 105 MW tasks.
  - Offline F-Droid apps that are in neither benchmark, such as [Loop Habit Tracker](https://f-droid.org/en/packages/org.isoron.uhabits/).
  - Avoid Fossify apps. MW's Calendar is Fossify ([MobileWorld](https://arxiv.org/abs/2512.19432)), and the Fossify suite ([fossify.org](https://www.fossify.org/)) continues the line that AW's "Simple" apps come from.

---

## Rank, LoRA variants and full fine-tuning are not the bottleneck

| Option | Evidence | Verdict | Phone speed after merging |
|---|---|---|---|
| **r128 / r256** | Rank gains stop at ~r64 across 0.6–32B models ([2609.01244](https://arxiv.org/abs/2609.01244)). r4 → r64 helped AC (+5.9 high-level) ([AndroidControl](https://arxiv.org/abs/2406.03679)). r256 helped only for new skills such as code ([Biderman et al.](https://arxiv.org/abs/2405.09673)). Our r64 has 65.9M trainable parameters for ~2.1M supervised tokens per epoch (ours / inference) | **Not useful.** If tested, keep α = 128 or use rsLoRA ([rsLoRA](https://arxiv.org/abs/2312.03732)). At r256, α = 2r (= 512) at the same LR makes the update ~4× larger (inference) | No change |
| LoRA variants (DoRA, PiSSA, LoRA+, …) | All within 1–2% of plain LoRA once LR is tuned ([2602.04998](https://arxiv.org/abs/2602.04998), [2601.22708](https://arxiv.org/abs/2601.22708)) | Skip | No change (merge them) |
| Train the projector | No GUI ablation; cheap | Later, as an ablation | No change |
| LoRA or full training on the vision encoder | Conflicting evidence. POINTS-GUI-G gained ([2602.06391](https://arxiv.org/abs/2602.06391)); Prismatic lost localisation ([2402.07865](https://arxiv.org/abs/2402.07865)). Our perception is close to GUI-Owl's: ScreenSpot-Pro 55.5 ([LFM3-VL-2B card](https://huggingface.co/LiquidAI/LFM3-VL-2B)) vs 57.8 ([GUI-Owl-1.5](https://arxiv.org/abs/2602.16855)) | Skip: it risks what already works | No change |
| Partial unfreezing (LISA, Spectrum) | Text LLMs only ([LISA](https://arxiv.org/abs/2403.17919), [Spectrum](https://arxiv.org/abs/2406.06623)) | Skip | No change |
| **Full fine-tuning of the language model** | No GUI paper compares it with LoRA. LoRA beat full FT for tool calling at 4B: 88.0 vs 80.4 on xLAM ([2609.17848](https://arxiv.org/abs/2609.17848)). Full SFT cut Qwen3-VL-2B's ScreenSpot-Pro from 40.16 to 31.56 ([LiteGUI](https://arxiv.org/abs/2605.07505)). It fits comfortably in 40 GB only with bf16 or 8-bit optimiser states, at ~1.5× compute (inference) | Not now | No change |

**Is it hyperparameters? No.**

- **Our settings are already in range:**
  - LR: α × lr = 0.026, against a published optimum of ~0.032 ([2609.01244](https://arxiv.org/abs/2609.01244)).
  - Tuning the LR away from its default gains 0.0008 nats ([2609.01244](https://arxiv.org/abs/2609.01244)).
  - Batch 32 is in LoRA's safe range ([Thinking Machines](https://thinkingmachines.ai/blog/lora/)).
- **GUI-sized swings come from data and training stage:**

  | Change | Effect | Source |
  |---|---|---|
  | Mixing action-only copies into SFT | AW 5.2 → 11.3 at 3B | [GUI-Libra](https://arxiv.org/abs/2602.22190) |
  | Adding RL after SFT | AW 21.7 → 34.0 at 7B | [UI-S1](https://arxiv.org/abs/2509.11543) |

- **Change only the schedule** (cosine → WSD), so that checkpoints can answer "would more training help?"

---

## Twenty extra output tokens cost 1–3% on the phone

### Where step time goes (ours)

| Device | Step time | Reading the prompt (image + text) | Writing the reply | +20 / +40 output tokens |
|---|---|---|---|---|
| **Phone CPU** (Snapdragon, 2.65 GHz) | 39.2 s | 36.2 s for 1,081 tokens | 28 tokens at 41 tok/s | **+0.5 / +1.0 s (+1.2% / +2.5%)** |
| Xeon CPU, 8 threads | 6.4 s | 5.59 s for 803 tokens | 28 tokens at 43 tok/s | +0.46 / +0.92 s (+7% / +14%) |
| Apple M5 (v4.2, inside runs) | 2.0 s | 1.29 s for ~1,190 tokens | 23 tokens at ~22 ms each | +0.44 / +0.88 s (+22% / +44%) |

Sources: [speed_qdc_v6.md](../../results/qdc/speed_qdc_v6.md), [speed_t8.md](../../results/speed/speed_t8.md); M5 split from the seed-30 server log [llama_server_lfm3vl2b_v42.log](../../logs/llama_server_lfm3vl2b_v42.log) via [latency.py](../../analysis/failure_analysis/latency.py).

- **GUI-Owl is slower because of its bigger prompt, not longer replies.** On the M5: 2,106 vs 1,303 prompt tokens and 7.00 vs 2.96 s per step. On the phone at the same image limit: ~198 vs ~39 s per step ([results.md](../results.md)).
- **What costs more than writing longer replies:**

  | Change | Cost |
  |---|---|
  | Re-asking the model | Repeats the whole image prompt; guards added 34% more calls ([ours](../../results/androidworld/)) |
  | A summary carried in the history | Re-read on every later step. The phone reads the prompt at ~30 tokens/s, so 15 tokens × 10 history steps can add up to ~5 s per step late in a task (inference, upper bound) |
  | Looping | The largest cost: v4 used all 50 steps on 85 of 104 MW tasks. Judge speed as steps × seconds per step |

### Evidence on reasoning at small scale

| Study | Finding (reported) |
|---|---|
| [Ferret-UI Lite](https://arxiv.org/abs/2509.26539), 3B | AW: no reasoning 13.7, short reasoning 15.8, long reasoning 19.6 |
| [GUI-Libra](https://arxiv.org/abs/2602.22190), 3B | After SFT, ~223-token reasoning grounds worse than ~68-token replies (SS-v2 73.4 vs 81.0); RL closes the gap |
| [Think or Not](https://arxiv.org/abs/2503.16188), 2B | Reasoning-style RL "may lead to trivial reasoning" at 2B |
| [GUI-G1](https://arxiv.org/abs/2505.15810), 3B | Longer chains lead to worse grounding |
| [AgentCPM-GUI](https://arxiv.org/abs/2506.01391) | A compact action format of ~9.7 tokens, chosen for edge latency |
| [VeriGUI](https://arxiv.org/abs/2604.05477), 3B | A structured think → verify → act → expected-effect format gave its recovery gains |
| v1 runtime notes (ours) | Untrained "[no visible change]" notes: 15 → 10 successes ([results.md](../results.md)) |

### Verdict

- **Yes to a short, trained, structured check of ≤10–15 tokens.** Examples: "last action changed screen: no", or "done? missing: category". The first can be computed from consecutive training screenshots, with no teacher.
- **No to free-form reasoning for now:**
  - it needs teacher-written text;
  - the 2–3B evidence is mixed;
  - it costs +40% on the Mac.
- **Never add runtime notes the model was not trained on.**
- **Speed guardrail for every candidate:** median output ≤ 30 tokens, and prompt length within ±5% of v4.2.

---

## Many apps, few kinds of supervision

App count is not the gap: AC's training split alone covers 769 apps ([AndroidControl](https://arxiv.org/abs/2406.03679)). What is missing is the *kind* of row.

| Gap | Our mix ([stats.json](../../results/data_v2/stats.json), [v41_data_manifest.json](../../results/v42/v41_data_manifest.json)) | Failure it feeds | Clean fix |
|---|---|---|---|
| No recovery | 0 recovery rows in v4; 94% of AC `wait` rows copy the previous intent ([PREREG_v41.md](../PREREG_v41.md)) | Loops | Own-mistake DPO or recovery rows |
| No "stop is wrong here" | Every `status` row in the v3 base is `complete` (5,998); 0 `infeasible`; Odyssey's 3,244 and AMEX's 1,714 terminal markers dropped as unreliable | False `complete` | DPO pairs at premature stops |
| Short histories | 1.41% of rows have ≥20 earlier steps. AC episodes average 5.5 steps ([AndroidControl](https://arxiv.org/abs/2406.03679)); MW tasks 27.8 ([MobileWorld](https://arxiv.org/abs/2512.19432)). Odyssey and AMEX are capped at ≤3 rows per episode | MW long tasks | Lift the caps: ~34k more Odyssey and ~15.6k more AMEX rows |
| No gestures | Non-page swipes cut out (1,417 Odyssey, 975 AMEX episodes); no drag action | Slider tasks | New action plus data (next week) |
| Typing then submitting | 12 `keyboard_enter` rows | Replies sent without text | — |
| Answers after browsing | 5,995 single-screen ScreenQA + 2,386 navigate-then-answer episodes | Wrong answers (14%) | More multi-screen answer episodes |
| No grounding or element-function rows | 0 | Taps that do nothing | AMEX Level I/II (elements and "what this element does"): adding them to AC gave +11.9 AC-High offline ([AMEX](https://arxiv.org/html/2407.17490)) |
| Little social or chat | 0.7% / 1.2% of AC episodes | MW Mastodon (36 tasks), Mattermost (17) | Odyssey's "Social Sharing" category ([GUI-Odyssey](https://arxiv.org/html/2406.08451)): 16.6% of our Odyssey episodes by keyword match (ours) |

- **Peer mixes:**
  - Sizes range from ~32K samples ([InfiGUI-R1-3B](https://arxiv.org/abs/2504.14239)) to ~28.7M ([Ferret-UI Lite](https://arxiv.org/abs/2509.26539)).
  - Most give 28–68% of the mix to grounding or perception ([ShowUI](https://arxiv.org/abs/2411.17465), [UI-Venus-1.5](https://arxiv.org/html/2602.09082)).
- **Grounding's online effect at ≤8B is weak.** In GUIMid, GUI perception data raised AW by +5.0, the same as non-GUI perception data ([GUIMid](https://arxiv.org/html/2504.10127)).
- **Ready within a day:** AC low-level rows (the builder flag exists) and Odyssey rows that already have intents.
- **Need more work:**

  | Source | Blocker |
  |---|---|
  | Full AMEX episodes | No intents |
  | AMEX Level II | Format conversion not prototyped |
  | [OpenMobile-Data-v2](https://huggingface.co/datasets/OpenMobile-2/OpenMobile-Data-v2) (non-AW apps) | No licence tag |

---

## One pass cannot see changes under ~9 points

### The current suite

| Benchmark | Role now | Problem |
|---|---|---|
| AW seed 30 (116) | Development | 12+ configurations chosen on it. v4 and v4.2 both score 18 but disagree on 12 tasks ([ours](../../results/androidworld/)) |
| AW sealed seeds 7 / 1234 / 2026 (348) | Held-out, used once | v4's lead comes from the 38 templates whose goal does not change with the seed ([results.md](../results.md)) |
| MW, 105 English GUI-only tasks | Development since v4 | Single-run noise ~8–9 pts ([MW #58](https://github.com/Tongyi-MAI/MobileWorld/issues/58)); baselines from the benchmark's own lab |
| AC test, dev splits | Offline regression check | All come from training sources; did not predict online changes |

### What to add, and what to skip

| Add | Why | Cost on our Mac (inference) | Peer numbers (reported) |
|---|---|---|---|
| **SS-v2**, mobile split (501), for v4.2 **and** GUI-Owl in our pipeline | The one score almost every peer reports; re-runs reproduce it within ~1.6 pts ([ClawGUI](https://arxiv.org/abs/2604.11784)); catches forgetting; shows the 4-bit + image-cap cost | ~20–25 min per model ([dataset](https://huggingface.co/datasets/OS-Copilot/ScreenSpot-v2)) | GUI-Owl-1.5-2B 89.7, MAI-UI-2B 92.5, UI-Venus-1.5-2B 92.8 |
| **AndroidLab** (138 tasks, 9 offline apps) | Never used by us; official Mac AVD; no logins ([AndroidLab](https://arxiv.org/abs/2410.24024), [Mac setup](https://github.com/THUDM/Android-Lab/blob/main/docs/prepare_for_mac.md)) | ~1.5–3 h per pass for v4 | UI-Venus-1.5-2B 36.2; Qwen3-VL-2B 33.3 ([UI-Venus-1.5](https://arxiv.org/html/2602.09082)) |
| **v4 replicate on seed 30** | We have never measured pure run-to-run noise | ~3 h | — |
| **AC test rescored on AndroidControl-Curated** | Label fixes move scores 10–17 pts; makes our AC number comparable | Minutes, if labels map ([AC-Curated](https://arxiv.org/abs/2510.18488)) | MAI-UI-2B 67.3 (different metric) |
| Optional: AnyAppBench new-app subset | Same tasks on new apps. UI-Voyager-4B, trained on AW templates, falls 53.9 → 28.6 ([AnyAppBench](https://arxiv.org/html/2609.34139v1)) | ≤15 h for all 520 pairs | No 2B numbers |

- **GUI-Owl's own benchmarks:**
  - Reproduce SS-v2 (and optionally MMBench-GUI L2's Android/iOS split) in our pipeline.
  - Skip ScreenSpot-Pro, OSWorld-G, OSWorld and WindowsAgentArena. They are desktop benchmarks and would measure a domain we never trained on.
  - Keep GUI-Owl's self-reported AW 67.9 only as a labelled reference. Our matched held-out score for it is 13.5% ([results.md](../results.md)).

### Statistics

| True gap | Power of one 116-task pass | Paired episodes for 80% power (tasks disagree 10% / 15% of the time) |
|---|---|---|
| 5 pts | 0.29 | ~310 / ~470 (3–4 passes) |
| 8 pts | — | ~120 / ~180 |

Computed with a paired McNemar test (ours).

- One pass needs a net gain of ~10 tasks (8.6 pts) to show up.
- **Behaviour counts have far more power than success counts.** False `complete`s ranged 20–28 across all nine LFM3 runs. A fix that drops them to ≤15 is visible in one pass, even when success is not (inference from the run-to-run range).
- **Never mix reporting styles:**
  - pass@3 vs pass@1: Step-GUI-4B's AW is 75.8 vs 63.9 ([Step-GUI](https://arxiv.org/html/2512.15431)).
  - 100-step vs 50-step MW budgets.

### Safeguards against overfitting and benchmark-maxxing

| Risk | Check | Pre-declared rule |
|---|---|---|
| Memorising rows | Loss on seen vs never-seen rows | Gap > 0.01 nats → never repeat rows |
| Copying dataset habits | Behaviour monitors every run: `wait` share, copied-intent rate, false `complete`s, loop start step | Always reported next to success |
| Forgetting | SS-v2 mobile, MMStar | Any drop > 2 pts vs v4.2 → reject |
| Picking on seed 30 | Replicate run; paired win/loss counts; seed-varying subset reported | No "better" claim from seed 30 alone |
| Tuning to MW | MW is development since v4 | An MW gain counts only if AndroidLab or sealed seeds agree |
| Exposure | Self-made tasks deduplicated against AW/MW text; no AW/MW trajectories; no GUI-Owl or MAI-UI as teacher | Exposure table per model and benchmark |
| Held-out sets wearing out | AndroidLab protocol frozen before its first run | Only frozen versions run on AndroidLab and sealed seeds |

- **Peer exposure goes in the table too.** MAI-UI trained in an RL environment containing MW's Mastodon, Mattermost and Mall4Uni apps ([MAI-UI](https://arxiv.org/abs/2512.22047)). ClawGUI trained in 64 MW containers ([ClawGUI](https://arxiv.org/abs/2604.11784)).
- **Reading the results:** a gap that appears on MW or AW but disappears on AndroidLab is more likely exposure than skill.

---

## Ranked plan for one day, ~5 A100-hours and two emulators

All decision rules go into a PREREG_v41 amendment **before** any new score. Seed-30 numbers in this plan are development numbers.

| Rank | Step | What exactly | A100 | Mac / emulators | Pre-declared decision rule |
|---|---|---|---|---|---|
| **1** | **Freeze the yardstick** | Write the amendment. Start a v4 replicate on seed 30. MW v4.2 has finished (8/105, development) | 0 | Emulator 1: ~3 h | R = the number of tasks that flip between v4 and its replicate. A seed-30 change counts only if the net change ≥ max(R, 10) tasks. Otherwise the result is "no measurable change", and the behaviour gates below decide |
| **2** | **Diagnostics and pair sampling** | (a) Loss on seen vs never-seen rows. (b) Validation loss split into intent, action type and coordinates. (c) v4.2's early-`status` rate on non-final AC test steps (v4: 4.6%). (d) 4 samples per state on ~6k v4.2 replay states → DPO pairs. First run the whole DPO path with a tiny `--limit`, through adapter save and GGUF export | ~0.5 h | — | (a) Gap > 0.01 nats → no repeated rows ever. (b) Action + coordinate tokens < 30% of the remaining loss → drop "more epochs". (d) Continue only with ≥3,000 pairs, ≥20% of them stop-related and ≥20% wait- or copy-related. Otherwise retry once with 8 samples, then fall back to recovery-row SFT |
| **3** | **Step-DPO on own mistakes** (v4.2-dpo) | From v4.2: DPO + 0.5 × SFT anchor, ~500 steps, one round | ~2 h | Emulator 1: ~3 h (seed 30) | **Offline gate, before any emulator time:** early-`status` rate ≤ ⅔ of v4.2's; final-step `complete` accuracy ≥ 0.70 (v4.2: 0.738), so it still stops; AC high-level ≥ 0.712; `dev_answer` ≥ 0.848. **Online gate:** false `complete`s ≤ 15 (all runs so far: 20–28), successes ≥ 16, median output ≤ 30 tokens. More than 10 exceptions → re-run the crashed tasks first. Passing makes it a held-out candidate, not a "better" claim |
| **4** | **Peer-comparable and held-out checks** | SS-v2 mobile for v4.2 and GUI-Owl. AndroidLab: check the Mac AVD; freeze the protocol (25 rounds, exact-match answers, exceptions count as failures); run frozen v4 and GUI-Owl once each. Rescore AC on AndroidControl-Curated | 0 | Emulator 2 + Mac: ~1 h SS-v2, ~2–3 h v4, ~4–7 h GUI-Owl | SS-v2 is a guard, not a selector: a candidate > 2 pts below v4.2 is rejected. If v4's held-out AW lead over GUI-Owl reverses on AndroidLab, report the AW lead as benchmark-specific. AndroidLab never runs unfrozen versions |
| **5** | **Fresh-rows run** (answers "train more?") | From v4.2: never-seen rows of the current mix, Odyssey rows freed by lifting the 3-row cap (those with intents), and 10% AC low-level rows. LR 2e-4, WSD with a 15% cool-down, and a branch checkpoint at 60%. Preflight: overlap and AW-app checks pass, plus a 50-step smoke run. Check GPU use in the first minutes | ~2 h | Emulator 1: ~3 h (seed 30) | If the final and 60% checkpoints differ by < 0.01 nats and < 1 AC pt, **and** false `complete`s stay at 20–28 and copied intents within ±5 pts of v4.2, more SFT on this mix is closed: no full epoch. Only a net gain ≥ max(R, 10) tasks earns a full epoch (~6.3 A100-h) next week |
| **6** | **Own-rollout pilot on clean apps** | 20–30 templated tasks on Settings, Clock, Contacts, Files and 2–3 offline F-Droid apps, deduplicated against AW/MW. adb checks; 4 tries per task at temperature ~0.7 with the day's best model | 0 today | Both emulators overnight | Train on it next day (~1.5 A100-h: successes as SFT, own loop steps as rejected DPO samples) only if: ≥30% of tasks succeed on some but not all 4 tries; the adb check agrees with a manual review on ≥19 of 20 episodes; and a reset takes ≤60 s. Otherwise redesign the tasks |

**Budget:** A100 ≈ 0.5 + 2 + 2 + ~0.5 for exports and offline evaluations ≈ **5 h**. Emulators ≈ 25–30 of 48 available hours.

### Timeline

| Hours from start | Colab A100 | Emulator 1 | Emulator 2 / Mac |
|---|---|---|---|
| 0–1 | DPO path smoke test (tiny `--limit`) | v4 replicate, seed 30 | SS-v2 mobile: v4.2, GUI-Owl |
| 1–2 | Rank 2 diagnostics and sampling | Replicate | AndroidLab AVD preflight (never restart the shared adb server) |
| 2–4.5 | Rank 3 DPO, GGUF export, offline gate | Replicate ends ~3 h | AndroidLab: v4 |
| 4.5–7 | Rank 5 fresh-rows run, export, offline gate; then **stop the session** | DPO seed 30 (if the offline gate passed) | AndroidLab: GUI-Owl |
| 7–10 | — | Fresh-rows model, seed 30 | Write pilot tasks and adb checks |
| 10–24 | — | Pilot rollouts | Pilot rollouts |

### Skip, and why

| Skip | Reason |
|---|---|
| Two or more epochs of the same rows | ~6.3 A100-h per epoch; the top failures have nothing to learn from in the data; fresh rows beat repeats |
| r128 / r256, LoRA variants | Gains stop at r64; variants are within 1–2% |
| Full fine-tuning, vision unfreezing | No GUI evidence it helps; forgetting risk; perception is not the gap |
| Static or online GRPO | v4-RL failed (66% of groups had no reward variance); online methods used ≥64 environments |
| Free-form reasoning | Needs teacher text; mixed evidence at 2–3B; +40% step time on the Mac |
| An open VLM judge as the reward | About a third of its "successes" would be wrong at our success rate (inference) |
| GUI-Owl or MAI-UI as a teacher | Circular; their training exposure is undisclosed |
| AW/MW tasks or trajectories, MAI-Gym | Breaks the contamination rule |

**Next week, depending on today's gates:**

- **Training:**
  - an own-rollout training round;
  - full AMEX episodes with intents, plus 10% AMEX Level II rows;
  - a trained "screen changed?" field;
  - a drag/slider action;
  - OpenMobile-Data-v2 non-AW apps, after a licence check.
- **Evaluation:** the frozen best candidate on sealed seeds and AndroidLab, with 3 passes for any 5-point claim.

---

## Round 5 as executed (2026-11-22/23)

The ranked plan was cut to what the credits allowed, then pre-registered ([PREREG_v41.md](../PREREG_v41.md), 17:00):
rank 1 used a **v4.2** replicate (not v4), rank 3 became P/P2, rank 5 became S (more SFT on the same mix, not fresh
rows). Rank 2 ran only as pair sampling (one greedy decode per state, not 4 samples), and ranks 4 and 6 were
not run.

| Plan rank | What ran | Result |
|---|---|---|
| 1 Yardstick | v4.2 replicate on seed 30 | R = 9 tasks flip between two identical passes; false `complete`s 22 vs 25 |
| 3 Step-DPO | **P:** all 4,163 own mistakes, β 0.1, 0.5 × SFT | Failed offline: AC high-level 0.732 → 0.545 (whole action types collapsed) |
| 3 Step-DPO (post-hoc fix) | **P2:** 851 balanced stop / copied-intent pairs, 1.0 × SFT, lr 1e-5 | Passed offline (terminal `complete` 0.738 → 0.785); failed online: 21/116, net +3 (noise), false `complete` 28 |
| 5 More training | **S:** 500 more SFT steps (0.17 epoch), WSD, lr 1e-4 | Passed offline (AC 0.736; val loss 0.340 → 0.334); failed online: 24/116 (the most of any LFM3 version), net +6 (below R = 9), false `complete` 37 |

**What this changes in the report**

| Earlier claim | After round 5 |
|---|---|
| "Step-level DPO on own wrong answers is the best next step" | Not confirmed at this scale. Unfiltered pairs destroy action priors; targeted pairs move the stop *rate*, not stop *accuracy* |
| "False-`complete` counts are tight (20–28), so a real fix shows in one pass" | Held: P2's 28 and the replicate's 22 sit in the band; no candidate left it downwards |
| "Offline metrics do not track online success" | Confirmed again: P2's best-ever terminal `complete` (0.785) came with its worst false-`complete` count (28) |
| "More epochs would lower loss, not fix behaviour" | Partly revised: 0.17 epoch more gave the largest seed-30 gain of the round (+5 to +6 against three references, none significant), but through more stopping, not better stopping (precision 0.34). Worth one more test; not yet a result |

**Why P2's stop training did not transfer (ours + inference):**
- Pairs show the model a *recorded* final screen and the human's `complete`. On a live phone the hard cases are screens
  that look finished but are not (a draft not saved, a toggle not applied). Those states never occur in demonstration
  data, so no pair can contrast them.
- 356 early-stop and 356 missed-stop pairs push in opposite directions; the net effect was a higher overall stop rate
  (44 vs 37–38 episodes ending with `complete`) with unchanged precision (0.36).
- The remaining lever is the one the plan ranked 6th: rollouts on non-benchmark apps where an adb check says whether
  the task is really done, so "looks done but isn't" states exist in training.

---

## Conclusion

- **The question is what to train on, not how much.** By the textbook tests the model is neither too small nor overfit. It imitates AndroidControl's habits faithfully, and it has never seen a corrected version of its own two worst habits. Each method in the literature with a large own-attempt gain contrasts a wrong and a right action at the same screen. Neither more passes nor more parameters adds that contrast.
- **Restraint is the cheapest gap to close and the easiest to measure.** GUI-Owl's advantage is stopping correctly (96% vs 33% precision on seed 30), and that is teachable without a teacher. False-`complete` counts sit in a tight 20–28 band across nine runs, so a real fix shows up in one pass, even when success counts cannot.
- **Speed is an asset to protect.** On the phone, almost all step time is spent reading the screenshot. Training method, adapter size and a few extra reply tokens barely matter. Longer prompts and wasted loop steps matter a lot.
