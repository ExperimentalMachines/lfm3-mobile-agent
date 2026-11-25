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

### 2026-11-25 15:34 Asia/Manila — E-DPO pairs FAIL the by-eye check; DPO not run

Job A (`lfm3-r10-edpo-pairs`, L40S, 46 billable min) decoded the 20,000 candidates. E's stop mistakes on its own training
rows: early stop 2.9% (last 3 actions), 0.5% (elsewhere), 4.4% (ahead rows); missed stop 12.4% (judged-COMPLETE
terminal rows). 437 + 437 balanced pairs (`results/v48_dev/r10_pairs_stats.json`). DPO smoke passed (10 GB peak).

**Review by eye (registered rule: more than 3 of 32 wrong → stop): 9 of 32 wrong → stopped; DPO not trained.**

| Kind | Wrong | What |
|---|---|---|
| early stop | 5 / 16 | The screen already met the goal (reviews visible, search results shown, the exchange rate on screen); the human kept browsing, so penalising `complete` there is wrong |
| missed stop | 4 / 16 | **E was right and the label wrong**: a filter ticked but not applied (2), a file listed but not opened, a list entry typed but not saved; E's "rejected" step was the correct next action |

AndroidControl's own `complete` labels contain premature completes even after the stage-1 judge's COMPLETE, and its
non-terminal rows include goals already met on screen. Preference pairs built on these labels are about 28% wrong.

### 2026-11-25 15:40 Asia/Manila — owner: "Proceed" with a judge calibration before any use

- **Judge:** Qwen3-VL-235B-A22B on AWS Bedrock (`qwen.qwen3-vl-235b-a22b`, on demand, us-west-2), temperature 0. Input:
  the goal, the step history and the screenshot; output COMPLETE or NOT_COMPLETE with one line of reason.
  (`analysis/done_audit/bedrock_judge.py`)
- **Calibration set: every case labelled by eye on 2026-11-25** whose label was not marked doubtful: the 32 E-DPO pairs
  (the question for each: is the task complete on that screen?) and the 64 GUI-Odyssey terminal candidates from the two
  reviews (doubtful ones and the one information-goal case left out).
- **Bar: at least 90% agreement with the by-eye labels.** Below it, no automatic judge is used: E-DPO stops and the next
  step is human-verified completion labels. At or above it, the judge filters the 874 E-DPO pairs (a pair is kept only if
  the judge agrees with its premise) and E-DPO resumes as registered on the kept pairs (still balanced 1:1).

### 2026-11-25 15:46 Asia/Manila — the Bedrock judge FAILS calibration; round 10 stops

Qwen3-VL-235B-A22B (Bedrock, temperature 0, `analysis/done_audit/bedrock_judge.py`) on the 93 cases labelled by eye
today (`results/v48_dev/bedrock_judge_calibration.jsonl`; 108k input tokens):

| Subset | Agreement |
|---|---|
| E-DPO early-stop pairs | 8 / 16 |
| E-DPO missed-stop pairs | 9 / 16 |
| GUI-Odyssey terminal review 1 / 2 | 23 / 30, 27 / 31 |
| **All** | **67 / 93 = 72%** (bar ≥ 90%) |

Reading the 26 disagreements: in about 4-7 the judge is right and the by-eye label lenient (weather "history" vs a
forecast; reviews of another product; a post still uploading); about 15 are judge errors (sent messages called "not
sent"; an open share sheet called "shared"; a PIN prompt called "verified"); the rest are goals that are ambiguous to
anyone ("see if you can purchase", "proceed to Amazon", "read the reviews"). Crediting the judge wherever it is arguably
right still leaves agreement under about 80%.

**Decision (registered rule): no automatic judge; E-DPO is not trained; round 10 ends here, negative.**
Findings carried forward:
1. "Done" labels are the bottleneck for false completes: GUI-Odyssey COMPLETE markers 16-25% wrong, AndroidControl
   `complete` labels include premature completes, and its non-terminal rows include goals already met on screen.
2. Neither an 8B / 32B (round 8) nor a 235B (round 10) judge reaches careful human agreement on "is it done?".
3. A fair share of goals is ambiguous about what "done" means (read / browse / see-if goals).
Next step (not registered yet): human-verified completion labels with written guidelines, on goals with an explicit end
state, and a decision on how browse / read / see-if goals should end.

### 2026-11-25 15:57 Asia/Manila — owner: label with the Claude API; the same calibration comes first

Owner: "label with claude API … You have $100 of credits. Don't go over $95". Registered before any Claude output:

| Item | Setting |
|---|---|
| Judge | Claude Opus 5.5 (`claude-opus-5-5`, Anthropic API, owner's credit), adaptive thinking, effort `high`, max 8,000 output tokens |
| Input, prompt, parsing | Exactly as the Bedrock judge: goal + step history + the stored screenshot (576×1280 JPEG, about 1,300-1,600 input tokens); first line COMPLETE / NOT_COMPLETE (`analysis/done_audit/claude_judge.py` imports them from `bedrock_judge.py`) |
| Calibration set | The same 93 cases labelled by eye on 2026-11-25; one run, no prompt change after seeing any output |
| Bar | **At least 84 / 93 (90%)** agreement; refusals, unparsed and errors count as disagreements |
| Budget | Every response priced at list price ($4 / $20 per M tokens in / out; Batch API half) in `results/v48_dev/claude_spend.jsonl`; the script sends nothing that could take the total past **$90** (owner cap $95) |

- **Pass:** Claude filters the 874 E-DPO pairs through the Batch API (keep rule as registered at 15:40), and E-DPO
  resumes as registered (balanced 1:1 on the kept pairs, E's round-8 gate, online bar false completes ≤ 15 and
  successes ≥ 19).
- **Fail:** no Claude label is used; round 10 stays negative.
- A second judge after the first failed gives two tries at the bar; at 84 / 93 a judge whose true agreement is 80% passes
  with probability under 1%, so the selection effect is small.

### 2026-11-25 16:01 Asia/Manila — the Claude judge FAILS calibration too (81%); no Claude label is used

Claude Opus 5.5 (effort high; `results/v48_dev/claude_judge_calibration.jsonl`) on the same 93 cases; **$1.03** spent
(ledger `results/v48_dev/claude_spend.jsonl`; mean 235 output tokens per case):

| Subset | Claude Opus 5.5 | Qwen3-VL-235B (15:46) |
|---|---|---|
| E-DPO early-stop pairs | 10 / 16 | 8 / 16 |
| E-DPO missed-stop pairs | 11 / 16 | 9 / 16 |
| GUI-Odyssey review 1 / 2 | 25 / 30, 29 / 31 | 23 / 30, 27 / 31 |
| **All** | **75 / 93 = 81%** (bar 84) | 67 / 93 = 72% |

**Decision (registered rule): fail; no Claude label is used; round 10 stays negative.**

Diagnostic re-reading of the 18 disagreements at full resolution with the full history
(`results/v48_dev/claude_judge_adjudication.json`; the by-eye labels came from 220×489 sheets with two history lines):

| Class | Cases | Example |
|---|---|---|
| By-eye label wrong, judge right | 3 | bus "for November 9" but departure still "Leave: Now"; forecast shown for "weather history" |
| Goal asks for more; judge's strict reading defensible | 4 | "make the purchase": product page only |
| Deliverable visible; judge demands an extra step | 4 | "show my progress": profile summary shown, judge wants Stats |
| Goal does not define "done" | 7 | "compare these shoes with others", "read the product reviews" |

- 12 of the 18 are also Qwen disagreements. Unlike Qwen's errors (sent messages called "not sent"), Claude's are not
  misreadings of the screen: they are disagreements about **what "done" means** for vague goals.
- Crediting the judge for the 7 defensible cases gives 82 / 93 = 88%, still under the bar.
- Caveat: the by-eye labels and this re-reading were made by the coding assistant (also a Claude model), not a person.

Next step (not registered): a written "done" guideline (per goal type: search / view / multi-part / commit), used in the
judge prompt and by the labeller, calibrated on a **fresh** set (the 93 cases have now shaped the guideline).
