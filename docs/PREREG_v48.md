# Preregistration: round 10 (v4.8), false completes on multi-part tasks

Written 2026-11-25 13:00 Asia/Manila, before any round-10 data or candidate existed; E's exploratory AndroidWorld run
was finishing. Append-only.

**Status: post-hoc development round.** Diagnosis used AndroidWorld seed-30 runs (development seed) and the training
data; the sealed held-out v4 result stays as it is.

---

## Why: what the audit found (2026-11-25)

| Finding | Evidence |
|---|---|
| E fixed the history shortcut offline but not AndroidWorld's false completes | History probe 54% → 20%; AndroidWorld (first 67 tasks) false completes E 18 = D 18 |
| E nearly stopped wasting steps on waits | Wait share 19.4% (D) → 2.6% (E); repeated-tap loops unchanged (14 vs 14) |
| **Most false completes are partly done tasks** | E's 19 so far, by eye: multi-part task stopped after the first part 6, found the information and stopped 2, final send/save missing 2, wrong action or target 4, one detail wrong 3, broke a constraint 1, misread the state 1 |
| **Not a size limit** | GUI-Owl-1.5-2B on the same 116 tasks: 13 "done", all real successes; 0 false completes |
| **The model learns when to stop only from short tasks** | Real `complete` rows: AndroidControl 11,075 (6.3 steps per episode, 5.8% multi-item goals), MemGUI 99. GUI-Odyssey (3,908 episodes, 21.5% multi-item, 10.3 steps) and AMEX (2,425 episodes, 91% multi-stage) give **0**: their terminal actions (Odyssey `COMPLETE`, AMEX `terminate(status="success")` via Aguvis) were dropped when the data was staged |
| A penalty on own mistakes did not help before | v4.3-dpo2 (round 5) targeted action mismatches: 28 false completes vs v4's 25 |

`analysis/done_audit/goal_parts.py`, `analysis/done_audit/aw_compare_runs.py`.

---

## Data: `MobileAgent-SFT-v4.8` (public) = v4.7 plus

| Change | Rule |
|---|---|
| **1. Completion on long multi-part tasks** | A terminal `status complete` row for every GUI-Odyssey episode ending `COMPLETE` and every AMEX episode ending `terminate(status="success")`: the terminal screenshot + the full history (positional notes, as every other row). Episodes ending `INCOMPLETE` / failed get none. Their counterfactual rows as for AndroidControl: **stale**, **ahead** (screen 2–3 steps before the end + the full history → that screen's action), **short** (terminal screen + history without its last 1–2 steps → `complete`) |
| Quality check before training | 32 random new terminal screens by eye (16 GUI-Odyssey, 16 AMEX). A source whose terminal screens look not done in more than 15% of its sample gets no terminal rows |
| **2. Progress in the reasoning** | Every target's reasoning starts with `[N left]`: N = actions after this one before the task is done (capped `5+`; `status` / `answer` rows `[0 left]`), from the episode's full length in its source. Counterfactual rows get the true N of the screen they show (ahead rows: N = k − 1 although the history claims every step). History lines never carry the prefix: stripped in the data and by the agent |
| v4.7's wait changes | Kept as published (`420637e9`) |

---

## Candidates

| | What | Recipe |
|---|---|---|
| **G** | Full v4.8 SFT from `LiquidAI/LFM3-VL-2B` @ `23387bed` | E's: LoRA r64 α128, lr 2e-4 cosine, 3% warm-up, 32 rows per step, one pass, 24-step history, fine change notes |
| **H** | G + a **penalty stage** | DPO on G's merged weights (`train/dpo_vlm.py`, β 0.1, SFT weight 1.0, lr 1e-5, one pass — round 5's dpo2 settings). Pairs from E's own greedy outputs (local GGUF) on not-done training states (real rows 1–3 actions before the end, and ahead states, all four sources): E says `complete` → chosen = the gold action (with progress), rejected = E's `complete`. Balanced 1:1 with "stop when done" pairs: terminal rows where E did not say `complete` → chosen = `complete`, rejected = E's output |

---

## Offline gate (each candidate; all must hold)

1. E's round-8 gate, every bar unchanged (`docs/PREREG_v46.md`), on the v4.8 splits.
2. **Multi-part probes** from held-out GUI-Odyssey episodes (its dev split, never trained on), multi-item goals:
   **M_mid** = rows 1–3 actions before the end (correct: not `status`); **M_done** = terminal rows (correct: `status`).
   E is measured on the same rows with the same evaluator.

| Probe | Bar |
|---|---|
| M_mid: share of `status` | ≤ E's − 5 points, and ≤ 10% |
| M_done: share of `status` | ≥ E's + 10 points, and ≥ 50% |

## Online test (only for a candidate that passes; at most one, H preferred over G if both pass)

AndroidWorld seed 30, 116 tasks, Mac (variant per candidate, `--history_steps 24 --nochange_notes --change_rule fine
--note_waits`). **Pass: false completes ≤ 15 (D: 26) and successes ≥ E's.** Reported: wait share, repeated taps,
harness errors (re-run once with `scripts/androidworld/rerun_harness_errors.sh` and reported both ways).

---

## Log

### 2026-11-25 13:15 Asia/Manila — before any v4.8 data exists: hardware and one scope change

- **Hardware (owner decision): AWS SageMaker ml.g6e.2xlarge (1x L40S 48 GB, $2.80/h)**, `scripts/training/sm_r10.sh`,
  instead of Colab. A smoke run first measures speed and memory; the micro-batch is chosen from it (32 rows per step in
  every case, which does not change the maths). Checkpoints every 100 steps to S3; a stopped job resumes from them.
- **Scope change: no AMEX terminal rows this round.** The AMEX raw screenshots were deleted on 2026-11-24 to free disk;
  re-fetching them is a 94 GB multi-volume zip. GUI-Odyssey's terminal screens were re-downloaded (OpenGVLab/GUI-Odyssey
  @ 71e0e7e2). AMEX rows still get the progress count (from Aguvis' `terminate(status="success")` step); AMEX episodes
  without one leave the training split. The by-eye check therefore reviews **32 GUI-Odyssey terminal rows** (same rule:
  more than 15% not done → no GUI-Odyssey terminal rows).
- GUI-Odyssey's COMPLETE markers were quarantined by an earlier audit (`data/build_v2_mix.py`, F5/F6: pending installs,
  unanswered information requests). `data/v48_odyssey_terminals.py` excludes information-request and install goals by
  rule and OCR-filters pending screens (as AndroidControl's terminal rows) before the review.
- E's baseline on the multi-part probes is measured by the same evaluator (generate.py, bf16) on the same hardware.

### 2026-11-25 14:05 Asia/Manila — GUI-Odyssey terminal rows FAIL the by-eye check (no candidate exists)

`data/v48_odyssey_terminals.py`: 2,120 candidates from 3,908 training episodes (1,224 truncated before the end, 124 not
ending COMPLETE, 378 install goals, 34 information requests, 28 OCR-pending screens).

| Review | Sample | Not done | Result |
|---|---|---|---|
| 1 (as registered) | 32 | 5 (16%): 3 AppLock "verify with the PIN" stopped on the PIN screen; a movie page never played; an information goal ("determine its price") that should end with an answer | fail (> 15%) |
| 2 (amendment before any candidate: also exclude PIN-verification and information-only goals, `data/v48_odyssey_filter.py`, 1,766 left; **fresh** sample) | 32 | **8 (25%)**: 3 ride bookings stopped at "choose a payment method"; second parts never done (reminder, volume, sharing); a movie never played; a learning task never saved | **fail** |

**Decision (the registered rule): no GUI-Odyssey terminal rows in v4.8.** The earlier audit's quarantine was right, and the
failures are the very pattern this round targets: annotators also stopped multi-part tasks after the first part.
`analysis/done_audit/` review sheets are not kept in the repo (screenshots); counts above.

### 2026-11-25 14:20 Asia/Manila — owner decision: round 10 becomes ONE candidate, E-DPO (no candidate exists)

With no reliable multi-part completions, G (full v4.8 SFT) and its progress counts are deferred to the next full retrain.
Owner: "Proceed with B". The round tests the penalty alone, on E:

| Item | Value |
|---|---|
| **E-DPO** | E's merged weights (`experimentalmachines/LFM3-VL-2B-MobileAgent-v4.6-E` @ `0203bc5a`) + a new language-only LoRA (r64 α128) trained with DPO (sigmoid, β 0.1) + 1.0 × SFT on the chosen side (`train/dpo_vlm.py`), lr 1e-5, one pass, 32 pairs per step; reference = E |
| Candidate rows (E's own training split, MobileAgent-SFT-v4.6 @ `0ace5559`; no AndroidWorld app in the goal) | 12,000 real rows whose human action is not `wait` / `status` / `answer` (70% from the last 3 actions of their episode); 4,000 *ahead* counterfactual rows (screen before the end, history claims every step); 4,000 real AndroidControl `status complete` rows that the stage-1 judge called COMPLETE |
| Pairs (E decodes greedily, bf16, thinking on, as at inference) | **early stop**: E says `status` / `answer` on a non-terminal row → chosen = the human step, rejected = E's step. **missed stop**: E does not stop on a judged-COMPLETE terminal row → chosen = `status complete`, rejected = E's step. Unparseable outputs never become rejections. **Balanced 1:1** (the larger kind capped at random, seed 49) |
| Check before training | 16 random pairs of each kind by eye: an early-stop pair whose screen already looks done, or a missed-stop pair whose screen does not, counts as wrong; more than 3 of 32 wrong → stop and report |
| Hardware | SageMaker ml.g6e.2xlarge (L40S): job A generates and builds pairs; job B trains, merges and evaluates |

**Offline gate (all must hold): E's round-8 gate, all 10 bars** (`docs/PREREG_v46.md`), on the v4.6 splits, same evaluator.
E failed two (C1 history probe 20% vs ≤ 15%; early `status` 3.55% vs ≤ 3.24%); E-DPO must pass all ten, including the
two that guard against over-correction (finished screen ≥ 70%, finished screen with cut history ≥ 60%).

**Online (only if the gate passes): AndroidWorld seed 30, 116 tasks, variant of E's harness** (`--history_steps 24
--nochange_notes --change_rule fine`). **Pass: false completes ≤ 15 and successes ≥ 19 (E's).** Reported against D and E:
successes, false completes, waits, repeated taps; harness errors re-run once and reported both ways.
