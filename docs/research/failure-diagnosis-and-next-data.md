# Failure diagnosis and the next training data (2026-11-23)

What the v4 family gets wrong (vision, planning or sequence), which Hugging Face data could fix it, and what 100 Colab
compute units buy. Numbers marked *ours* are reproducible from this repo:
[`analysis/diagnosis_20261123/`](../../analysis/diagnosis_20261123/), outputs in
[`results/diagnosis_20261123/`](../../results/diagnosis_20261123/). The dataset survey is in
[`notes/hf-mobile-gui-datasets-2026-11-23.md`](notes/hf-mobile-gui-datasets-2026-11-23.md).

**Bottom line**

- **Mostly a sequence problem, partly planning, rarely vision.** 82% of held-out AndroidWorld failures are sequence
  behaviours: looping, stopping too early, answering too early. Only 2.2% of AndroidControl steps are pure location
  misses.
- **The model collapses on long tasks.** It solves 34% of AndroidWorld tasks that need 1–3 steps but 1% of those that
  need 11 or more. Its false-`complete` rate climbs with task length (9% → 33%); GUI-Owl's stays at 0–2%.
- **It is not reading the step numbers.** Renumbering the history did not change early stops (27 vs 27 of 300).
- **Train on different data, not more or deeper.** That means long episodes, recovery after mistakes, verified endings
  and answers that need navigation, with contamination filters. One clean source has all four: **MemGUI-3K**, after
  filtering. There is still no clean mobile dataset for recovering from loops.
- **100 compute units fit a full data round:** two full-size candidates, one continuation, one rollout fine-tune, all
  offline checks, and 15% contingency. Full epochs over the enlarged mix, online RL and MobileWorld runs do not fit.

---

## Vision, planning or sequence?

### Executing a step vs choosing it

AndroidControl scores every test screen twice: with the step instruction (low-level) and without (high-level). v4's
outputs on all 8,428 paired non-terminal steps (*ours*):

| Outcome | Steps | Share | Reading |
|---|---|---|---|
| Right both ways | 6,073 | 72.1% | — |
| **Right only with the instruction** | 1,577 | **18.7%** | Can execute; chose the wrong next step (**planning**) |
| Wrong even with the instruction | 713 | 8.5% | Execution: see the split below |
| Right only without the instruction | 65 | 0.8% | Noise / labels |

| Low-level (instruction given) errors | Steps | Share of all steps |
|---|---|---|
| Wrong action type (e.g. `wait` vs tap, scroll vs tap) | 515 | 6.1% |
| **Right type, wrong place (grounding)** | 188 | **2.2%** |
| Right type, wrong text / direction / app | 75 | 0.9% |

- **Grounding misses are wrong elements, not imprecise taps:** the median miss lands 41% of the screen away.
- **Reading is fine:** v4 scores 0.79 on ScreenQA dev and 0.89 on the v4 question dev set when the answer is on the
  screen it sees.
- **The phone GPU computes what the Mac does:** the same file gives the same action on 98–99% of 180 steps
  ([mobile-agent](https://github.com/ExperimentalMachines/mobile-agent) `docs/conversion.md`).

**Vision is not the bottleneck.** The gaps that look visual (sliders, date pickers, AM/PM) are skills missing from the
data, not perception errors.

### Long tasks: where AndroidWorld is lost

348 held-out episodes per model (seeds 7 / 1234 / 2026), by the task's optimal step count (*ours*):

| Steps the task needs | Tasks | v4 solved | GUI-Owl solved | v4 false `complete` | GUI-Owl false `complete` |
|---|---|---|---|---|---|
| 1–3 | 96 | **34%** | 23% | 9% | 0% |
| 4–6 | 101 | 15% | 18% | 22% | 1% |
| 7–10 | 66 | 8% | 2% | 21% | 2% |
| 11+ | 79 | 1% | 6% | 33% | 2% |

- **Some stops are impossible:** 26 of v4's 71 false `complete`s came before the task's optimal step count.
- **Failure mix:** of the 294 held-out failures, loops are 44%, false `complete`s 24%, wandering 15%, and wrong or
  too-early answers 14% ([training-scale-and-own-attempt-learning.md](training-scale-and-own-attempt-learning.md)).
- **The same holds offline, with perfect expert history.** On AndroidControl the early-`status` rate climbs with the
  step index:

  | Step index | 0–1 | 2–3 | 4–5 | 6–7 | 8+ |
  |---|---|---|---|---|---|
  | Wrong `status` | 0.9% | 3.6% | 7.9% | 10.6% | 9.5% |
  | Step accuracy | 0.752 | 0.744 | 0.691 | 0.668 | 0.721 |

- **Training episodes are short:** AndroidControl test episodes have a median of 6 steps; 80% have 8 or fewer.

### Is it the step numbers? No

- **Idea:** the history numbers steps absolutely ("11." at step 12), so the model could learn "stop around step 6".
- **Test:** 300 high-level, non-terminal AndroidControl test steps at step 9 or later. The same 8 history lines,
  numbered as usual (e.g. 5.–12.) or renumbered 1.–8. Model: v4 GGUF, evaluation flags.

| | Early `status` | Step accuracy |
|---|---|---|
| Original numbers | 27 / 300 | 0.727 |
| Renumbered 1.–8. | 27 / 300 | 0.717 |

- **Result:** exact McNemar p = 1.0 (1 vs 1 discordant). The cue is in the screens or the history content, not the
  numbers, so renumbering is not a fix.

### What this means for training

| Cause | Evidence | What fixes it |
|---|---|---|
| Expert-only, short demonstrations | Episodes of median 6 steps; stopping and accuracy degrade with position; collapse on long tasks | Long trajectories (MemGUI, AndroidLens), with more weight on episodes > 8 steps |
| The model never sees its own mistakes | Loops = 44% of failures. About 25% of first taps in failed episodes change nothing | Rows with a bad step and then recovery (MemGUI, GUI-Reflection); a "last action changed nothing" note in the history |
| "Looks done but isn't" states never occur in recorded data | Round 5's stop pairs passed offline, not online | Own rollouts on non-benchmark apps, judged by adb state checks |
| Questions are answered from the current screen in training | Answers at step 1 without navigating ("Android 10") | Question tasks that need navigation first (MemGUI's 784) |
| Missing skills | Sliders, date / time pickers, almost no `keyboard_enter` | AndroidLens pickers, DragOn sliders, restored Odyssey / AMEX swipes, AITZ Enter |

---

## Training data on Hugging Face

Full survey (about 110 cards, contamination checked against AndroidWorld, MobileWorld and AndroidLab):
[notes/hf-mobile-gui-datasets-2026-11-23.md](notes/hf-mobile-gui-datasets-2026-11-23.md).

| Dataset | Adds | Size usable | Licence | Contamination | Verdict |
|---|---|---|---|---|---|
| lgy0404/MemGUI-3K | Long histories (median 18 steps), 784 question tasks answered after reading, 4.3K bad-step-then-recovery steps, checker-verified endings | ≈991 trajectories / 20.9K steps after filtering (49 GB raw) | Apache-2.0 | **Filter**: Joplin, Audio Recorder (AndroidWorld) and Bluecoins (AndroidLab) appear | **Use, filtered** |
| yuecao0119/AndroidLens | Long episodes (≈26 steps), date / time pickers, "not done yet" milestones | 172 English episodes | Apache-2.0 | Clean | **Use** |
| craigwu/GUI_Reflection_SFT_train | Recovery from ineffective actions | ≈15K + 17K rows | MIT | Clean | Maybe |
| Android-in-the-Zoo (full train mirror) | Short reasoning, "what this action changed", native Enter | 18.6K steps | Unclear | Clean after app filter | Once licensed |
| GUIAgent/Magic-RICH | "Already done / still loading" judgments | 1K steps | Apache-2.0 | Clean | Maybe |
| Hcompany/DragOn, slider part | Slider drags | 571K (synthetic) | Apache-2.0 | Clean, but web and landscape | Maybe, small sample |

**Rejected, collected inside our benchmarks:**
- AndroidFlux
- MobileForge
- UI-MOPD/Uni-GUI-Mobile
- UI-Genie and its repacks
- OS-Shepherd-100K
- Tonic/android-operator-episodes (re-splits AndroidControl test into train)
- Several AndroidWorld run archives

No clean mobile date-picker dataset exists. Nothing usable was uploaded after 2026-11-22.

---

## What 100 Colab compute units buy

### Unit costs (measured in round 5, Colab A100 at 6.73 units/h)

| Job | Measured | Units |
|---|---|---|
| SFT throughput | 4.11 rows/s (v4.2: 40,000 rows in 9,724 s; v4.3-sft: 16,000 in 3,887 s) | 0.46 per 1,000 rows |
| One v4-size SFT run (1,250 steps × 32 = 40K rows) | 2.7 h | 18.2 |
| Offline check (AndroidControl high-level + terminal, dev sets) | ~20 + ~3 min | ~2.8 (≈3.7 with a long-horizon dev set) |
| DPO on ~4K pairs (131 steps) | 40 min | 4.5 |
| Own-action sampling over training states (round 5 pairs) | 47 min | 5.3 |
| Session start (install, downloads) | ~15 min | ~1.7 per session |

- **Other GPUs:** G4 costs ≈ 10 units/h and pays only if it is ≥ 1.5× faster than the A100 on this job, which is
  unmeasured (time it in the smoke test). L4 costs ≈ 1.9 units/h and is too slow for SFT at this size.
- **Free work (Mac or phone):**
  - building the data, if done shard by shard (78 GB free disk);
  - merges and GGUF / LiteRT exports;
  - AndroidWorld passes on the two emulators;
  - phone checks on QDC.

### A plan that fits

| # | Job | Rows / steps | Units |
|---|---|---|---|
| 1 | Data build: MemGUI shard-by-shard filter, AndroidLens, GUI-Reflection subset, Magic-RICH, restored swipes; mark "no change" steps from screen diffs | — | 0–2 (CPU runtime or Mac) |
| 2 | Smoke test of the whole pipeline (50 steps, tiny eval, export) | — | 2 |
| 3 | **v4.4-A**: v4's recipe from the base model on the new mix (v4 rows + ~45K new rows, long episodes up-weighted), 1,250 steps | 40K rows | 18.2 + 3.7 |
| 4 | **v4.4-B**: same as A, with a "last action changed nothing" note in the history | 40K rows | 18.2 + 3.7 |
| 5 | **v4.4-C**: v4 + 500 steps on the new rows only (the cheap "more of the right data" test) | 16K rows | 7.3 + 3.7 |
| 6 | Own rollouts on non-benchmark apps (Mac / phone), judged by adb checks; then an SFT/DPO pass on the best candidate | ~10K rows | 4.6 + 3.7 |
| 7 | Session starts (≈4) | — | 7 |
| 8 | Contingency (VM loss, restarts; one A100 VM was lost mid-run before) | — | 15 |
| | **Total** | | **≈ 87–89 (≈ 11 left)** |

- **Online checks cost no units:**
  - every candidate gets an AndroidWorld seed-30 pass on the Mac;
  - only the winner gets the held-out seeds;
  - pre-declared behaviour gates: false `complete` and loop counts, not success alone.
- **If the smoke test shows G4 is ≥ 1.5× faster,** switch rows 3–6 to G4.

### What does not fit

| Idea | Cost | Why not |
|---|---|---|
| Full epoch over the enlarged mix (~140K rows) | ≈ 64 units per epoch | Most of the budget for one run, and more epochs fixed nothing in round 5 |
| Full fine-tuning / deeper training | ≥ the above, more memory | Train = validation loss; vision is fine. Nothing for capacity to fix |
| Online RL on Colab | — | Colab has no hardware virtualization for Android emulators; rollouts must run on the Mac or the phone |
| MobileWorld runs | VM + T4 hours | Needs a cloud VM (the GCP project is gone); not Colab |
| All of AitW | 365–494 GB | Disk; only an app-filtered subset is realistic |

---

## Outcome: round 6 (added 2026-11-24)

The plan ran as A, B and C ([../preregistrations/round-06-long-trajectories.md](../preregistrations/round-06-long-trajectories.md), [results](../rounds.md#round-6-long-and-self-correcting-trajectories-2026-11-23)).

| Prediction here | What happened |
|---|---|
| Long, self-correcting trajectories help long tasks | **Yes, offline.** AndroidLens step accuracy at steps ≥ 10: 0.367 → 0.401–0.413 |
| A "no visible change" signal helps with stopping and loops | **Partly.** Correct stops at the real end of long tasks: 22% (A) → 29% (B); 48% for C. Late-step early stops on AndroidControl did not move (8.5–9.8% vs 9.0%) |
| 100 units fit the round | **Yes.** 64.5 used (smoke, v4 reference, A, B, C); 47.0 left |

- **No candidate passed the offline gate,** so none ran online.
- **The stopping gate was partly mis-specified:** half of v4's "early" stops on AndroidControl's late steps are one step
  before the end, where demonstrations add a final scroll or wait.
- **Still the open lever:** the "looks done but isn't" states that only the model's own runs produce, judged by adb
  checks.
