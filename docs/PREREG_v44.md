# Preregistration: round 6 (v4.4), training on long and self-correcting trajectories

Written 2026-11-24 10:00 Asia/Manila (2026-11-23 18:00 PST), before any v4.4 data, training or result existed (the
data converters had just started). Append-only: later entries go under [Log](#log) with a timestamp.

**Status: post-hoc development round.** The diagnosis behind it
([failure-diagnosis-and-next-data.md](research/failure-diagnosis-and-next-data.md)) used held-out AndroidWorld
episodes. The sealed v4 result (54/348) stays as it is, and v4.4's held-out run (if any) is labelled as made after
that diagnosis.

---

## Why

| Evidence (ours) | Source |
|---|---|
| 82% of v4's held-out AndroidWorld failures are sequence behaviours: loops 44%, false `complete` 24%, too-early answers 14% | [training-scale-and-own-attempt-learning.md](research/training-scale-and-own-attempt-learning.md) |
| v4 solves 34% of tasks needing 1–3 steps but 1% of those needing 11+; its false-`complete` rate rises 9% → 33% (GUI-Owl 0–2%) | [failure-diagnosis-and-next-data.md](research/failure-diagnosis-and-next-data.md) |
| Planning, not vision: 18.7% of AndroidControl steps are right only with the step instruction; 2.2% are pure location misses | same |
| Training episodes are short (AndroidControl median 6 steps) and expert-only | same |

## Data (built before training; revisions recorded in the Log before the first training step)

| Part | Content | Use |
|---|---|---|
| v4 rows | `experimentalmachines/MobileAgent-SFT-v4` train @ `3375539` (AndroidControl, GUI-Odyssey, AMEX, ScreenQA) | All candidates |
| **MemGUI rows** | lgy0404/MemGUI-3K train trajectories, successful ones only. Targets = steps the dataset judges reasonable. Unreasonable steps stay in the history (recovery). Converted by `data/v44_memgui.py` | All candidates |
| Contamination filter | No AndroidWorld, MobileWorld or AndroidLab tasks, apps (beyond generic system apps), trajectories or checkers: AndroidWorld app / package / alias regex of `build_v2_mix.py`, plus AndroidLab and MobileWorld app lists | All |
| "No visible change" notes | A history step gets ` [no visible change]` when the next screenshot differs from it by a mean absolute difference < 1.0 on a 72 × 160 grayscale thumbnail (not after `wait` / `status` / `answer`). This is the rule of `eval/androidworld/lfm_agent.py` `runtime_feedback` | Candidate B only, in training **and** at run time |
| New dev splits (eval only, never trained on) | `dev_memgui` (MemGUI test trajectories, same filter); `dev_androidlens_high` / `_low` (AndroidLens English, 172 episodes, about 26 steps; `data/v44_androidlens_eval.py`) | Offline gates |

## Candidates

| Name | Start | Data | Steps | Recipe |
|---|---|---|---|---|
| **A** | LiquidAI/LFM3-VL-2B (as v4) | v4 rows + MemGUI rows ×2 | 1,250 × 32 | v4's (LoRA r64 α128, lr 2e-4 cosine, vision frozen, thinking on) |
| **B** | as A | A's mix, with "no visible change" notes | 1,250 × 32 | as A |
| **C** | v4 merged weights | 50% MemGUI rows, 50% v4 rows | 500 × 32 | lr 1e-4, warm-up / stable / short decay (round 5's S schedule) |

Smoke test first: 50 steps of A plus every eval on a few rows plus the export. No candidate trains before it passes.
Order: A, B, C. If credits run short, C is dropped first, then B.

## Offline gates (each candidate, before any online run)

| Gate | Bar | v4 reference |
|---|---|---|
| AndroidControl test, high-level step accuracy | ≥ v4 − 0.02 | 0.728 |
| `dev_complete` / `dev_answer` | ≥ v4 − 0.05 each | 0.762 / 0.89 |
| **AndroidLens English, early `status` on non-terminal steps** | ≤ ⅔ of v4's | measured on v4 before any candidate exists |
| AndroidLens English, high-level step accuracy | ≥ v4 − 0.02 | as above |

A candidate failing any gate does not go online. No gate is changed after a candidate's number is seen.

## Online (AndroidWorld, Mac emulators, v4's harness)

- **Runs:** each candidate that passes the gates runs AndroidWorld seed 30 once (116 tasks), with v4's settings (prompt
  v4, thinking on, Q4_K_M, llama-server flags). B also gets the matching runtime notes.
- **Reference:** v4 = 18/116 with 25 false `complete`s. Two identical passes flip R = 9 tasks; false-`complete`
  counts have sat in a 20–28 band across nine runs.
- **Promotion to held-out:** the best candidate goes to the held-out seeds (7 / 1234 / 2026, 348 episodes) only if
  **false `complete` ≤ 15** on seed 30 (outside the 20–28 band) and **success ≥ 18**; or if **success ≥ 27** (v4 + R).
  Ties go to the fewer-heuristics candidate: A, then C, then B. If none qualifies, nothing goes held-out, and the round
  is reported as negative.
- **Held-out claim:** paired against v4's 54/348, with the template-clustered sign-flip test as for v4, labelled
  post-hoc.

## Budget

- Original Colab account, 111.52 compute units at the start (A100 at about 6.73 units/h).
- Plan: ≈ 87–89 units, as in the research note (smoke 2, A and B 22 each, C 11, rollout fine-tune 8, sessions 7,
  contingency 15).
- The rollout fine-tune (own runs on non-benchmark apps, judged by adb checks) is a later step. It needs its own Log
  entry before it starts.
- Data building and online runs use no Colab units.

## Review

- **Before merging, an adversarial review of the data builders and the round's claims.** agy is out of quota until
  about 2026-11-28, so a Claude sub-agent stands in, as in round 5.

---

## Log

### 2026-11-24 10:00 Asia/Manila

- Written before any v4.4 data, training or result.
- Converters running: `data/v44_memgui.py` and `data/v44_androidlens_eval.py`.

### 2026-11-24 12:10 Asia/Manila — data facts and two gate amendments (before any candidate exists)

**MemGUI rows** (`data/v44_memgui.py`, MemGUI-3K @ `003822b5aa3d5450232b8e6305d3094f564a1cf1`):

| What | Count |
|---|---|
| Trajectories kept | 567 of 2,661 train, 63 of 295 test |
| Dropped, AndroidWorld apps (Joplin, Audio Recorder) | 1,471 train |
| Dropped, AndroidLab apps (Bluecoins and others) | 104 |
| Dropped, calendar apps | 108 |
| Dropped, MobileWorld | 1, plus Messages / SMS trajectories (dropped conservatively) |
| Dropped, infeasible tasks | 264 |
| Dropped, inexpressible actions (mostly drags) | 66 |
| Answer rows removed | 81 train, 11 dev. Their answers are full sentences, and v4 / AndroidWorld want short answers. The steps before them stay |

- About half the rows are past step 8.
- About a third have an unreasonable step earlier in their history: recovery.
- Final counts are in `data/v44work/memgui_stats.json`.

**"No visible change" notes on v4's rows** (`data/v44_nochange.py`):
- 9.0% of AndroidControl rows get at least one note (3.9% of history lines), mostly after taps and scrolls.
- Odyssey 0.2%; ScreenQA and AMEX 0.

**Same evaluator for v4 and the candidates:**
- v4's gate numbers come from the Colab pipeline's `V4REF` stage: Transformers bf16, `generate.py`, the same pre-rendered splits.
- The GGUF baseline on AndroidLens (llama.cpp on the Mac) is informational only.

**Amendment 1: the stopping gate moves to AndroidControl.**
- v4's partial AndroidLens baseline (1,891 scored steps, GGUF) has almost no early stops: 0.4% overall, 0–1% per bucket.
- On these long, unfamiliar tasks v4 fails by not stopping (terminal accuracy 9%), while step accuracy falls from 0.54 (steps 0–4) to 0.34 (steps 20+).
- "≤ ⅔ of v4's early-stop rate" on AndroidLens would test a floor.
- The new stopping gate is the AndroidControl test, high-level, non-terminal rows at step index ≥ 4: the predicted-`status` rate must be ≤ ⅔ of v4's. In v4's published bf16 run that rate is 276 / 3,064 = 9.0%; the bar uses `V4REF`'s number.

**Amendment 2: AndroidLens becomes a no-regression check where v4 is weakest.**
- Step accuracy on steps ≥ 10 must be ≥ v4's − 0.02, using `V4REF`'s number.
- Overall AndroidLens step accuracy stays reported, not gated.

Both amendments are made before any v4.4 candidate exists or is trained; only v4's own numbers were seen.

### 2026-11-24 13:25 Asia/Manila — smoke passed; v4 reference measured; A training (no candidate result exists)

- **Smoke test:** passed. Full mix built: train_a / train_b 109,239 rows (92,229 v4 + 2 × 8,505 MemGUI), 8,369 B rows
  with notes, train_c 17,010. 50 training steps and every eval on 16 rows ran.
- **v4 reference** (`V4REF`: Transformers bf16, `generate.py`, the pre-rendered splits; the same path as the
  candidates):

  | Metric | v4 | Candidate bar |
  |---|---|---|
  | AndroidControl test high-level step accuracy | 0.727 (published 0.728) | ≥ 0.707 |
  | AndroidControl high-level non-terminal steps ≥ 4, predicted `status` | 9.0% (275 / 3,064; published run 276) | ≤ 6.0% |
  | `dev_answer` / `dev_complete` | 0.890 / 0.763 | ≥ 0.840 / ≥ 0.713 |
  | AndroidLens English, step accuracy at steps ≥ 10 | 0.367 (overall 0.414; terminal `complete` 12%) | ≥ 0.347 |
  | `dev_memgui` step accuracy | 0.421 | Reported only |

- **Candidates:** A started training at 13:23.

### 2026-11-24 00:45 Asia/Manila — A fails the offline gate (2 of 5 checks); B training

| Metric | A | v4 | Bar | Result |
|---|---|---|---|---|
| AndroidControl high-level step accuracy | 0.729 | 0.727 | ≥ 0.707 | pass |
| `dev_answer` | 0.890 | 0.890 | ≥ 0.840 | pass |
| `dev_complete` (n = 80) | 0.700 | 0.763 | ≥ 0.713 | **fail** (56 vs the 57 needed) |
| AndroidControl steps ≥ 4, predicted `status` | 8.5% | 9.0% | ≤ 6.0% | **fail** |
| AndroidLens steps ≥ 10, step accuracy | 0.401 | 0.367 | ≥ 0.347 | pass |

**Reported, not gated:**

| Metric | A | v4 |
|---|---|---|
| AndroidLens overall step accuracy | 0.448 | 0.414 |
| AndroidLens terminal `complete` | 21.5% | 12.2% |
| AndroidLens early `status` | 0.5% | 0.2% |
| `dev_memgui` | 0.668 | 0.421 |

- **Rule applied:** A does not go online.
- **Reading:** the MemGUI rows lifted long-task step accuracy and end-of-task stopping. They did not lower the early-stop rate on AndroidControl's late steps, which is the habit the round targets.
- **Next:** B started training at 00:40 Manila (16:40 UTC). Its weights are public at `experimentalmachines/LFM3-VL-2B-MobileAgent-v4.4-A`. Gate file: `results/v44_dev/lfm3_v44a_offline_gate.json`.

### 2026-11-24 01:40 Asia/Manila — timestamp correction

**The error:** three earlier headings converted this Mac's "PST" as US Pacific time. It is Philippine Standard Time
(UTC+8, the same as Asia/Manila), so the headings are 16 hours off.

**The correct times** come from the commits, and the order of events is unchanged:

| Heading as written | Correct time (Asia/Manila) | Commit |
|---|---|---|
| "2026-11-24 10:00 … (2026-11-23 18:00 PST)" (preregistration written) | 2026-11-23 18:00 | `dda0e0f` |
| "2026-11-24 12:10" (data facts, gate amendments) | 2026-11-23 19:41 | `a6b535e` |
| "2026-11-24 13:25" (smoke passed, v4 reference) | 2026-11-23 21:26 | `73143d1` |

- "A started training at 13:23" was 13:23 UTC = 21:23 Manila.
- The A entry, "2026-11-24 00:45", is correct (commit `160fb0f` at 00:42).

### 2026-11-24 04:05 Asia/Manila — B fails the offline gate (1 of 5 checks); C training

| Metric | B | A | v4 | Bar | B result |
|---|---|---|---|---|---|
| AndroidControl high-level step accuracy | 0.728 | 0.729 | 0.727 | ≥ 0.707 | pass |
| `dev_answer` | 0.890 | 0.890 | 0.890 | ≥ 0.840 | pass |
| `dev_complete` (n = 80) | 0.713 | 0.700 | 0.763 | ≥ 0.713 | pass (57 / 80, at the bar) |
| AndroidControl steps ≥ 4, predicted `status` | 8.75% | 8.5% | 9.0% | ≤ 6.0% | **fail** |
| AndroidLens steps ≥ 10, step accuracy | 0.402 | 0.401 | 0.367 | ≥ 0.347 | pass |

**Reported, not gated:**

| Metric | B | A | v4 |
|---|---|---|---|
| AndroidLens terminal `complete` | 29.1% | 21.5% | 12.2% |
| AndroidLens early `status` | 0.9% | 0.5% | 0.2% |
| `dev_memgui` | 0.654 | 0.668 | 0.421 |

- **Splits:** B was evaluated on the `_notes` splits, as pre-registered.
- **Rule applied:** B does not go online.
- **Reading:**
  - The "no visible change" notes raised correct stopping at the real end of long tasks (AndroidLens terminal 22% → 29% vs A).
  - They did not change the early stops on AndroidControl's late steps. Neither the new data nor the progress signal moves that rate.
- **Next:** C started at 03:58 Manila (19:58 UTC). B's weights are public at
  `experimentalmachines/LFM3-VL-2B-MobileAgent-v4.4-B`.

### 2026-11-24 05:45 Asia/Manila — C fails the offline gate (1 of 5 checks); round 6 ends negative

| Metric | C | B | A | v4 | Bar | C result |
|---|---|---|---|---|---|---|
| AndroidControl high-level step accuracy | 0.724 | 0.728 | 0.729 | 0.727 | ≥ 0.707 | pass |
| `dev_answer` | 0.875 | 0.890 | 0.890 | 0.890 | ≥ 0.840 | pass |
| `dev_complete` | 0.788 | 0.713 | 0.700 | 0.763 | ≥ 0.713 | pass |
| AndroidControl steps ≥ 4, predicted `status` | 9.8% | 8.75% | 8.5% | 9.0% | ≤ 6.0% | **fail** |
| AndroidLens steps ≥ 10, step accuracy | 0.413 | 0.402 | 0.401 | 0.367 | ≥ 0.347 | pass |

**Reported, not gated:**

| Metric | C | B | A | v4 |
|---|---|---|---|---|
| AndroidLens terminal `complete` | **47.7%** | 29.1% | 21.5% | 12.2% |
| AndroidControl terminal `complete` | 0.740 | 0.715 | 0.714 | 0.716 |
| `dev_memgui` | 0.698 | 0.654 | 0.668 | 0.421 |

**Decision under the rule:** no candidate passes the offline gate, so nothing goes online and round 6 is reported
as negative. All three candidates are public: `experimentalmachines/LFM3-VL-2B-MobileAgent-v4.4-A`, `-B` and `-C`.

**Gate-design observation** (made after the results; it changes no decision):
- v4's 275 "early" `status` predictions at AndroidControl steps ≥ 4 mostly fall right before the end.
  - 141 (51%) are exactly one step before the episode's terminal row; 61 are two steps before.
  - The ground-truth action at those steps is click 114, scroll 99, wait 51, back 11.
  - The human demonstrations often add a final scroll or wait before finishing.
- So this gate partly measures AndroidControl's annotation habit, not the online failure. The online failure is
  different: 26 of v4's 71 held-out false `complete`s came before the task's optimal step count.
- A better stopping gate would be "`status` predicted ≥ 2 steps before the end", or a check on the model's own
  trajectories. That is for a later, separately pre-registered round.

**What the round showed (offline):**
- Long-task step accuracy rose 3.5–4.6 points over v4 in all three candidates.
- Correct stopping at the real end of long tasks rose 12% → 22% (A), 29% (B) and 48% (C).
- Late-step early stopping on AndroidControl did not move (8.5–9.8% vs 9.0%).

**Compute:** 64.5 Colab units for the smoke test, V4REF, A, B and C; 47.0 left. The session was stopped after the
results were downloaded (`results/v44_dev/`).
