# Development rounds since v4

Every version after v4, what it tried, how it was judged and what was decided. v4 was frozen on 2026-11-19 and is
still the main model; everything here is development work.

**Contents:** [How a round works](#how-a-round-works) · [All rounds](#all-rounds) · [What we learned](#what-we-learned) ·
[v4.1–v4.2](#v41-and-v42-2026-11-21-to-22) · [5](#round-5-learning-from-own-mistakes-vs-more-training-2026-11-22) ·
[6](#round-6-long-and-self-correcting-trajectories-2026-11-23) · [7](#round-7-all-the-data-once-with-a-longer-memory-2026-11-24) ·
[8](#round-8-judge-done-from-the-screen-not-the-history-2026-11-25) · [9](#round-9-useless-waits-2026-11-25) ·
[10](#round-10-finishing-multi-part-tasks-2026-11-25) · [11](#round-11-e-trained-on-checked-multi-part-endings-2026-11-25) ·
[12–14](#rounds-12-to-14-the-done-check-and-training-on-its-own-mistakes-2026-11-26)

---

## How a round works

| Step | What happens |
|---|---|
| 1. Plan | A preregistration fixes the data, the candidate(s), the offline gate and the online pass rule, committed before training. Later entries are dated and append-only |
| 2. Offline gate | Fixed bars on held-out splits (below). A candidate that fails does not go online |
| 3. Online test | AndroidWorld **seed 30** (116 tasks, development seed) on the Mac; pass rules usually "false done ≤ 15" plus "successes ≥ the reference" |
| 4. Decision | By the rule. Exploratory runs after a failed gate happened twice, by the owner's decision, and are marked as such |

**Noise yardstick:** two passes of the same model (v4.2) differed on 9 tasks, so one seed-30 pass cannot detect gains
smaller than about 9 tasks (R = 9).

**Offline checks used from round 8 on** (AndroidControl **test** episodes and other held-out sets; share of rows
where the model says `status`, unless stated):

| Check | What it asks | Good |
|---|---|---|
| AndroidControl step accuracy (high level) | Right next action on held-out human episodes | high |
| `dev_answer` / `dev_complete` | Answers questions; finishes held-out goals | high |
| AndroidLens steps ≥ 10 | Right action deep into long tasks | high |
| Early `status` | Says "done" 2+ steps before the human finished | low |
| **T** | Finished screen, true history | high |
| **C1** | Unfinished screen, history claims every step | low |
| **C2** | Finished screen, last 2 history steps cut | high |
| **C3 / C3n** | Screen before the last tap (C3n: that tap noted "[no visible change]") | low |
| **M_done / M_notdone** (round 11) | GUI-Odyssey final screens a calibrated judge says are done / not done | high / low |

---

## All rounds

Seed 30 = successes out of 116; false "done" = episodes the model ended as done that the checker failed.

| Round | Date | Version | Idea | Offline gate | Seed 30 | False "done" | Decision | Rules |
|---|---|---|---|---|---|---|---|---|
| — | 11-19 | **v4** | Reference | passed | 18 | 25 | Main model | [PREREG_v4](PREREG_v4.md) |
| — | 11-21 | v4.1 | Copied `wait` labels fixed; recovery histories | — | 12 | — | Worse; dropped | [PREREG_v41](PREREG_v41.md) |
| — | 11-22 | v4.2 | v4.1 + its own replayed histories | — | 18 | 25 | Kept as round 5's start (loops halved) | [PREREG_v41](PREREG_v41.md) |
| 5 | 11-22 | v4.3-dpo / -dpo2 / -sft | DPO on own mistakes; or 500 more SFT steps | dpo failed | — / 21 / 24 | — / 28 / 37 | Negative | [PREREG_v41](PREREG_v41.md) |
| 6 | 11-23 | v4.4-A / B / C | Long, self-correcting MemGUI trajectories | failed | — | — | Negative | [PREREG_v44](PREREG_v44.md) |
| 7 | 11-24 | v4.5-D | All the data once; 24-step history | failed (1 of 5) | 21* | 27 | Negative | [PREREG_v45](PREREG_v45.md) |
| 8 | 11-25 | **v4.6-E** | Rows where history and screen disagree | failed (2 of 10) | 19* | 24 | Negative; newest published model; held-out 52 / 348 (v4 54), not promoted | [PREREG_v46](PREREG_v46.md) |
| 9 | 11-25 | (v4.7 data) | Rows against useless waits | — | — | — | Candidate not trained: E already met its wait bars | [PREREG_v47](PREREG_v47.md) |
| 10 | 11-25 | E-DPO | Penalise E's premature stops and reward its missed stops, on judge-checked pairs | failed | — | — | Negative | [PREREG_v48](PREREG_v48.md) |
| 11 | 11-26 | E-T | E + 747 checked multi-part endings | failed (M_notdone) | — | — | Negative; learned "last screen → done" | [PREREG_v49](PREREG_v49.md) |

\* Exploratory: run after a failed offline gate, by the owner's decision.

---

## What we learned

| Lesson | Evidence | What we did |
|---|---|---|
| Offline gains on new data do not predict AndroidWorld | v2, v3 (offline up, AndroidWorld down); D and E (AndroidControl 0.753 / 0.758 vs v4's 0.727) at 21 / 19 vs 18 | AndroidWorld seed 30 is part of every decision |
| Blank or copied intents break the loop | v2 (8,739 blank intents: 3 / 116); copied `wait` intents → loops | v3 filled intents; v4.1–v4.3 and v4.6 relabelled waits. E waits on 3.5% of steps (v4: 29%), but repeats taps more (6 → 23 runs) |
| Inference-time patches did not replace data fixes | v1 + runtime feedback (10), v2 + forced intent (6), loop guards (no gain) | Dropped |
| **Stopping is the main weakness** | Every version tested ends 22–37 of 116 seed-30 episodes with a false "done"; about half of E's are multi-part tasks stopped part-way | Rounds 8, 10 and 11 target it |
| The model judged "done" from its history text | Unfinished screen + a history claiming every step: v4.5 54% "done" | E's counterfactual rows: 20% offline; online false "done" unchanged (24) |
| More training stops more often, right and wrong | v4.3-sft: 24 / 116 but false "done" 25 → 37 | Gates include early-stop and false-done bars |
| DPO on own mistakes did not help at this scale | v4.3-dpo collapsed action types; v4.3-dpo2 and E-DPO moved nothing measurable | Not repeated without much more signal |
| **Human "done" labels are noisy** | GUI-Odyssey final steps: 16–25% not done in the first reviews, about half under the owner's strict definition (judge 46%, by eye 27 / 56); 9 of 32 of E-DPO's first pairs wrong | A judge calibrated to the owner's definition of done (93% / 91% agreement on fresh by-eye labels; the labeller was the coding assistant, itself a Claude model, so not independent of the judge) |

The owner's definition of done (2026-11-25): a job is done when the task in the user's prompt is met in full: nothing
more, nothing less; no unnecessary waits; edge cases handled.

---

## v4.1 and v4.2 (2026-11-21 to 22)

Designed after reading v4's MobileWorld trajectories: loops of `wait` under copied intents ([PREREG_v41.md](PREREG_v41.md)).

### AndroidWorld seed 30 (2026-11-22; exceptions count as failures)

| Variant | Successes / 116 | Exceptions | vs v4 (gained / lost) |
|---|---|---|---|
| v4 (reference) | 18 | 4 | — |
| v4 + loop guards | 18 | 1 | +3 / −3 |
| v4.1 (wait relabel + recovery history) | 12 | 7 | +2 / −8 |
| v4.1 + guards | 14 | 8 | +6 / −10 |
| v4.2 + guards | 13 | 24 (20 emulator a11y crashes) | +6 / −11 |
| **v4.2 (v4.1 + own replayed history)** | **18** | 9 | +6 / −6 |

- **No variant beats v4.** v4.2 went to MobileWorld by the pre-declared rule (tied with v4 + guards; the tie order put v4.2 first).
- **Run-to-run noise is large:** v4 and v4.2 both score 18 but disagree on 12 tasks; one pass detects only gaps of
  about 9–10 points ([research notes](research/notes/training-scale-and-own-attempt-learning/benchmarks.md)).

### MobileWorld: v4.2 (post-hoc, 2026-11-22)

Source: [`results/mobileworld/mw_r3_comparison.md`](../results/mobileworld/mw_r3_comparison.md) (+ `.json`),
[PREREG_v41.md](PREREG_v41.md). Same settings as run 2 except MobileWorld-native typing (no synthetic Enter).
MobileWorld is now a development benchmark for LFM3; v4's 6/105 stays the reported number.

| v4.2 vs | Both | v4.2 only | Other only | Difference | Exact McNemar p |
|---|---|---|---|---|---|
| **v4 (primary)** | 5 | 3 | 1 | +1.9 pts | 0.625 |
| GUI-Owl-1.5-2B | 7 | 1 | 15 | −13.3 pts | 0.0005 |
| MAI-UI-2B | 5 | 3 | 6 | −2.9 pts | 0.51 |

| Loop metric | v4 | v4.2 |
|---|---|---|
| Steps that are `wait` | 21% | 5% |
| `wait` under a non-wait intent | 931 | 18 |
| Steps repeating the previous intent | 67% | 33% |
| Tasks ending at the 50-step limit | 85 | 69 |

- **Gained:** MastodonChangeHeader, MastodonFollow, MastodonNewPost. **Lost:** CloseFlightMode. Not significant.
- **Loops halved, success barely moved:** the freed steps mostly went to wandering, not to finishing tasks.

---

## Round 5: learning from own mistakes vs more training (2026-11-22)

Gates were fixed before training ([PREREG_v41.md](PREREG_v41.md), 17:00 entry). All candidates start from v4.2.
Counts: [`analysis/aw_false_complete.py`](../analysis/aw_false_complete.py) (the failure taxonomy's definition),
[`analysis/aw_paired_flips.py`](../analysis/aw_paired_flips.py); offline files in [`results/v5_dev/`](../results/v5_dev/).

| Candidate | What | AC high-level | Terminal `complete` | Seed 30 successes | Exceptions | False `complete` | Net vs v4.2 (flips, p) | Gate |
|---|---|---|---|---|---|---|---|---|
| v4.2 (reference) | — | 0.732 | 0.738 | 18 | 9 | 25 | — | — |
| v4.2 replicate | Same model, same harness, second pass | — | — | 19 | 2 | 22 | +1 (9 = R, 1.0) | noise yardstick |
| P = v4.3-dpo | DPO on all 4,163 of its own mistakes | **0.545** | 0.885 | not run | — | — | — | offline **fail** |
| P2 = v4.3-dpo2 | DPO on 851 balanced stop / copied-intent mistakes | 0.728 | 0.785 | 21 | 3 | **28** | +3 (11, 0.55) | online **fail** |
| S = v4.3-sft | 500 more SFT steps on v4.2's mix | 0.736 | 0.757 | 24 | 1 | **37** | +6 (14, 0.18) | online **fail** |

- **Pass rule:** successes ≥ 16 **and** false `complete` ≤ 15, **or** net gain over v4.2 ≥ R = 9 tasks.
- **Round 5 is negative by the declared rule: v4.2 stays.** No candidate goes to the held-out seeds.
- **P** collapsed whole action types offline (`open_app` 0.95 → 0.16, `scroll` 0.62 → 0.16). Most of its pairs were
  generic wrong clicks; that this is the cause is inferred (P2's rebalanced pairs kept per-type accuracy), not tested.
- **P2** did not change online stopping measurably: 44 episodes ended with `complete` (v4.2: 37–38; paired +10 / −7 vs
  v4.2, p 0.63), false `complete`s 26 vs 25 on the tasks neither run crashed (p 1.0). Its offline gain on recorded final
  screens did not show up online; why is not determined. Its DPO moved it little (final reward margin 0.047; P 0.43).
- **S** has the most seed-30 successes of any LFM3 version (24; MAI-UI-2B 32). The gain is the same size against v4
  (+6, p 0.15) and the replicate (+5, p 0.23), but stays below R = 9. It stops more often: 56 episodes ended with
  `complete` (paired +25 / −11 vs v4.2, p 0.03), with precision unchanged (0.34) and false `complete`s up (+20 / −11 vs v4.2,
  p 0.15; +24 / −9 vs the replicate, p 0.01). 4 of its 10 wins over v4.2 are tasks the replicate also won.
- **Run conditions:** v4.2's first pass was the second run on its emulator without a cold boot (9 exceptions); the replicate, P2 and
  S ran on cold-booted emulators. On tasks neither run crashed, the nets are replicate 0, P2 +2 (p 0.75), S +5
  (p 0.27). Two void passes (dead accessibility service before the model acted) were discarded and re-run; a Mac
  reboot interrupted P2 and S, which resumed from their checkpoints (the task in progress was restarted from scratch).

---

## Round 6: long and self-correcting trajectories (2026-11-23)

### Setup

| Item | Detail |
|---|---|
| Rules | Fixed in advance in [PREREG_v44.md](PREREG_v44.md): gates amended twice before any candidate existed, every entry timestamped |
| Diagnosis behind it | [research/failure-diagnosis-and-next-data.md](research/failure-diagnosis-and-next-data.md) |
| Evaluator | v4 and the candidates through the same path: Transformers bf16, `generate.py`, pre-rendered splits (`V4REF`) |
| Files | [`results/v44_dev/`](../results/v44_dev/) |
| Compute | 64.5 Colab units (A100) |

### New rows

8,505 [MemGUI-3K](https://huggingface.co/datasets/lgy0404/MemGUI-3K) training rows.
- **Shape:** long agent trajectories (median 16 GUI steps), with the dataset's unreasonable steps left in the
  history so that later rows show recovery.
- **Filter:** AndroidWorld, MobileWorld and AndroidLab apps removed (`data/v44_memgui.py`).

### Candidates

| Candidate | What |
|---|---|
| A | Base model + v4's rows + MemGUI ×2, v4 recipe (1,250 × 32) |
| B | A + a " [no visible change]" note on history steps whose next screenshot did not change (the run-time rule of `lfm_agent.py`) |
| C | v4 + 500 × 32 steps on 50% MemGUI / 50% v4 rows (warm-up / stable / short decay, lr 1e-4) |

### Offline gate

| Metric | v4 | A | B | C | Bar |
|---|---|---|---|---|---|
| AndroidControl test high-level step accuracy | 0.727 | 0.729 | 0.728 | 0.724 | ≥ 0.707 |
| `dev_answer` | 0.890 | 0.890 | 0.890 | 0.875 | ≥ 0.840 |
| `dev_complete` (n = 80) | 0.763 | **0.700** | 0.713 | 0.788 | ≥ 0.713 |
| AndroidControl steps ≥ 4: predicted `status` | 9.0% | **8.5%** | **8.75%** | **9.8%** | ≤ 6.0% |
| AndroidLens English, step accuracy at steps ≥ 10 | 0.367 | 0.401 | 0.402 | 0.413 | ≥ 0.347 |
| **Gate** | — | fail | fail | fail | |

### Reported, not gated

| Metric | v4 | A | B | C |
|---|---|---|---|---|
| AndroidLens step accuracy, all steps | 0.414 | 0.448 | 0.441 | 0.444 |
| AndroidLens: `complete` at the real last step | 12.2% | 21.5% | 29.1% | **47.7%** |
| AndroidLens: early `status` | 0.2% | 0.5% | 0.9% | 1.4% |
| AndroidControl terminal `complete` | 0.716 | 0.714 | 0.715 | 0.740 |
| `dev_memgui` step accuracy | 0.421 | 0.668 | 0.654 | 0.698 |

- **Round 6 is negative by the declared rule.** No candidate ran online; v4 stays.
- **What moved:**
  - Every candidate gained 3.5–4.6 points of long-task step accuracy over v4.
  - The candidates stop correctly at the real end of long tasks far more often. The notes (B) and the continuation
    from v4 (C) help most.
- **What did not move:** the late-step early-stop rate on AndroidControl, 8.5–9.8% against v4's 9.0%.
- **The gate partly measures annotation habit** (found after the results; no decision changed):
  - 141 of v4's 275 "early" stops at steps ≥ 4 are one step before the episode's end, and 61 are two steps before.
  - The human demonstration there is often a final scroll (99) or wait (51).
  - The online failure is earlier: 26 of v4's 71 held-out false `complete`s came before the task's optimal step count.
  - A later round should gate on "`status` ≥ 2 steps before the end", or on the model's own trajectories.
- **AndroidLens English** is the new long-task test set (172 episodes, median 27.5 steps; evaluation only):
  [evaluation.md](evaluation.md#androidlens-english-offline-long-tasks).
  - v4's GGUF scores 0.395 on it.
  - Accuracy falls with depth: 0.536 at steps 0–4, 0.329 at steps 20+.
  - It says `complete` at the true end of only 11.6% of episodes.

---

## Round 7: all the data once, with a longer memory (2026-11-24)

**Idea:** every run so far saw 40,000 rows (0.43 of v4's mix, sources capped). Train once over everything, with a
24-step history and "[no visible change]" notes. Data: [MobileAgent-SFT-v4.5](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v4.5)
(173,430 rows: all of AndroidControl, GUI-Odyssey and AMEX under v2's rules, v4's ScreenQA and question rows, MemGUI).

| Item | Value |
|---|---|
| Candidate | **D** = base model + LoRA (v4's recipe), one pass: 5,420 steps × 32 rows, 3.4 h on a Modal H100 |
| Offline gate | **Failed 1 of 5:** early `status` 3.64% (bar ≤ 3.24%; v4 2.74%) |
| Offline, otherwise | AndroidControl 0.753 (v4 0.727); AndroidLens steps ≥ 10 0.471 (0.367); `complete` at the real end of long tasks 57.6% (12.2%) |
| AndroidWorld seed 30 (exploratory) | 21 / 116 vs v4's 18: +9 / −6, p = 0.61; false "done" 27 (v4 25) |

**Decision:** negative. Large offline gains did not show online beyond noise; false "done" did not move. D is
published as not promoted. Files: [`results/v45_dev/`](../results/v45_dev/), [`results/androidworld/lfm3vl2b_v45d/`](../results/androidworld/lfm3vl2b_v45d/).

---

## Round 8: judge "done" from the screen, not the history (2026-11-25)

**Diagnosis:** with an unfinished screen, a history claiming every step was done raised D's "done" rate from 3.7% to
53.7%. In every demonstration the history and the screen agree, so the history was a shortcut.

**Data:** [MobileAgent-SFT-v4.6](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v4.6) (185,643 rows):
- counterfactual rows where history and screen disagree: *stale* (screen before the last action, that action noted
  "[no visible change]" → redo it), *ahead* (screen 2–3 steps before the end, full history → the action the screen
  needs), *short* (finished screen, history cut → `complete`);
- `complete` rows that two vision judges call visibly not done: dropped (2,405);
- copied `wait` intents replaced; "[no visible change]" notes recomputed with a stricter rule.

| Item | Value |
|---|---|
| Candidate | **E** = base model + LoRA, one pass: 5,802 steps × 32 rows (Colab A100, then a Modal H100) |
| Offline gate | **Failed 2 of 10, both narrowly:** early `status` 3.55% (≤ 3.24%); C1 20.0% (≤ 15%; D 53.7%) |
| Offline, otherwise | AndroidControl 0.758; T 78%; C2 71%; C3n 0.3% (D 32%) |
| AndroidWorld seed 30 (exploratory) | 19 / 116; false "done" 24; waits 3.5% of steps (v4 29.1%, D 16.9%); same-tap repeats 23 runs (v4 6) |

**Decision:** negative under the rule. E fixed waits and, offline, the history shortcut, but online false "done" stayed
at 24: about half are multi-part tasks stopped part-way. E is published with its phone GGUF as not promoted.

**Held-out run (owner's decision, post-hoc, 2026-11-25):** E on seeds 7 / 1234 / 2026, with the rule fixed first: E
replaces v4 as the main model if it is non-inferior to v4 (lower bound above −6.9 points) and makes no more false
"done" calls than v4's 71 of 348 ([PREREG_v46](PREREG_v46.md), 20:33).

| | E | v4 | GUI-Owl |
|---|---|---|---|
| Successes / 348 (seeds 7 / 1234 / 2026) | 52 (18 / 14 / 20) | 54 (18 / 17 / 19) | 47 |
| E − model, 95% CI | | −0.6 pts [−5.4, +4.2] | +1.4 pts [−4.0, +6.9] |
| False "done" (after re-runs) | 75 | 71 | 0 |

- Non-inferior to v4 (lower bound −5.3 > −6.9), but more false "done" calls: **E does not replace v4.**
- Fewer waits did not turn into more successes; false "done" is still the failure that matters.
- Source: [`results/sealed_analysis_e.md`](../results/sealed_analysis_e.md).

**MobileWorld (owner's decision, descriptive, 2026-11-26):** E 5 / 105 (v4 6, v4.2 8, MAI-UI 11, GUI-Owl 22).
Waits under a non-wait intent 931 (v4) → 0; steps repeating the previous intent 67% → 30%; but 76 of 105 tasks still
end at the 50-step limit. Source: [`mw_e_comparison.md`](../results/mobileworld/mw_e_comparison.md).
Files: [`results/v46_dev/`](../results/v46_dev/).

---

## Round 9: useless waits (2026-11-25)

- **Data built and reviewed by eye three times:** [MobileAgent-SFT-v4.7](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v4.7)
  @ `420637e9` = v4.6 + rows teaching "after a wait that changed nothing, act" (5,000) and "on a loading screen, wait"
  (1,500), plus 63 relabelled waits.
- **Candidate F (E + these rows) was not trained.** The 04:40 amendment made F conditional on E: F is skipped if E
  waits on at most 15% of C3n screens and its useless AndroidWorld waits are at most 6.7% of steps. E met both (C3n:
  98% redo the tap; useless waits 2.3%).
- The v4.7 changes are kept for the next full retrain.

---

## Round 10: finishing multi-part tasks (2026-11-25)

**Diagnosis:** the model learned when to stop only from short AndroidControl tasks. GUI-Odyssey (10 steps per episode,
many multi-part goals) and AMEX gave no "done" rows, because their end markers were judged unreliable.

| Step | Result | Decision |
|---|---|---|
| GUI-Odyssey final steps as "done" rows (planned v4.8) | By eye 16% and then 25% not done (bar 15%) | No such rows; the full v4.8 retrain was not built |
| Owner: try a penalty instead (E-DPO) | Pairs from E's own outputs: 9 of 32 wrong by eye (bar 3) | Labels need checking first |
| Automatic "done" judge, calibrated on 93 by-eye labels | Qwen3-VL-235B 72%; Claude Opus 5.5 81% (bar 90%) | Failed. Qwen misread screens; Claude's disagreements were about what "done" means for vague goals |
| **The owner's definition of done**, fresh calibration | Claude Opus 5.5: **93%** (AndroidControl pairs), **91%** (GUI-Odyssey) | Judge used |
| Judge on E-DPO's 874 pairs | 266 of 437 "early stops" were correct stops; 93 of 437 human "done" labels premature | 342 balanced pairs kept |
| E-DPO (one pass = 11 steps) | Unchanged from E: C1 19.3%, early `status` 3.49% | **Failed the gate**; not published |
| Judge on AndroidControl's own "done" rows | Spot check 26 / 32 (bar 28): too strict there | Labels not used |
| Judge on 1,766 GUI-Odyssey final steps | **947 done**, 819 not done | Carried to round 11 |

Claude API spend: $24.53 (owner's cap $95). Files: [`results/v48_dev/`](../results/v48_dev/).

---

## Round 11: E trained on checked multi-part endings (2026-11-25)

Plan: [PREREG_v49.md](PREREG_v49.md), registered 2026-11-25 20:12.

| Item | Value |
|---|---|
| Candidate | **E-T** = E + a new LoRA, 1,000 steps × 32 rows (lr 1e-4) over a fixed 32,000-row mix |
| New rows | 747 judge-confirmed GUI-Odyssey "done" rows + their counterfactual rows + the human rows 1–3 actions before those endings (from E's training split); the rest replay of E's data |
| Held out | 200 judged-done endings (**M_done**: should say done) and 819 judged-not-done endings (**M_notdone**: should not) |
| Offline gate | E's round-8 bars; early `status` ≤ 3.80% and C1 ≤ 22% (no worse than E); M_done ≥ E + 10 points and ≥ 50%; M_notdone ≤ E + 5 points |
| Online (only on a pass) | Seed 30: false "done" ≤ 15 (E 24), successes ≥ 19, useless waits ≤ 5% |
| Hardware and cost | SageMaker L4 (the L40S never got capacity), 7.1 h, about $9 |

**Result (2026-11-26): fails the offline gate.** Files: [`results/r11_dev/`](../results/r11_dev/).

| Check | E | E-T | Bar |
|---|---|---|---|
| Round-8 bars, the two E failed relaxed to "no worse than E" | 8 of 10 (original bars) | **10 of 10** | all |
| M_done: says done on judged-finished final screens | 0% | **95%** | ≥ 50% ✓ |
| M_notdone: says done on judged-unfinished final screens | 0% | **65%** | ≤ 5% ✗ |

- E-T learned "last screen of a GUI-Odyssey episode → done", only weakly tied to whether the task is finished.
- Likely cause: every unfinished final screen was held out for the M_notdone probe, so training never showed one;
  its "not done" examples were all earlier screens. A next try needs judged-unfinished final screens in training.
- No online test; nothing published. E stays the newest model.

---

## Rounds 12 to 14: the done check and training on its own mistakes (2026-11-26)

Plans: [PREREG_v410.md](PREREG_v410.md) (E-V), [PREREG_v411.md](PREREG_v411.md) and [PREREG_v412.md](PREREG_v412.md) (RL, control, test-phone fix). An external review (Codex, read-only) found four real bugs in round 13's RL; it was stopped and rebuilt.

| Candidate | What it is | Offline gate |
|---|---|---|
| E-V (round 12) | E + rows teaching a "is the task done?" question, asked before accepting `complete` | **Fails** 2 of 16: the check says "no" on 74.5% of unfinished screens (bar 75%); model + check still ends on 19.5% of them (bar 15%) |
| E-S2 (round 14) | Semi-online RL from E on 400 own-history episodes, 100 batches | **Fails**: barely moved (M_done 1%); a little worse on repeated taps (22% vs 17%) and early `status` (4.2%) |
| E-D (round 14) | Matched control: supervised rows from E's own strict misses, same episodes | **Fails**: says done on 83.5% of finished and **56.5% of unfinished** final screens (the round-11 failure again) |

What changed in how we measure: AndroidWorld's per-task app reset had never run on our emulators (no snapshots), so every
earlier run, for every model, carried app data between tasks; fixed and verified. The multi-step own-history test (SOP)
does not rank our seven models like AndroidWorld does (ρ = 0.33, bar 0.70), so it is a regression check only.
**Running out of steps is the largest failure** (v4 55, E 59 of 116) and it is looping, not budget: successes finish in a
median 5 steps, and 36 of 55 (v4) / 43 of 59 (E) exhausted episodes repeat their own actions.

**Decision:** no new candidate; v4 stays the main model, E the newest. Further gains most likely need much more data or RL
signal than this project's budget; this is a budget limit on this recipe, not a measured ceiling of the 2B model.
