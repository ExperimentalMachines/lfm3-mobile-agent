# Preregistration: round 9 (v4.7), useless waits

Written 2026-11-25 03:50 PST (Mac clock), before any round-9 candidate existed. E (round 8) was still training and
no E result had been seen. Append-only.

**Status: post-hoc development round.** The diagnosis used AndroidWorld seed-30 runs (development seed) and the
AndroidControl training split; the sealed held-out v4 result stays as it is.

---

## Why: what the audit found (2026-11-25)

| Finding | Evidence | Files |
|---|---|---|
| **D waits a lot, and most waits change nothing** | AndroidWorld seed 30: 295 of 1,745 steps are `wait` (17%; v4: 29%). 234 of the 282 measurable waits leave the next screen unchanged (83%) | `analysis/done_audit/aw_waits.py` |
| **Waits come in streaks** | 39% of D's waits follow another wait, with 8 streaks of 5 or more. In AndroidControl train only 4.8% of steps after a `wait` are another `wait` | same; `analysis/done_audit/wait_detail.py` |
| The useless waits sit on stuck screens, not loading ones | 12 random by eye: empty search results ×5, a tap that did nothing ×3, a menu left open, an error page, a garbled text field | `aw_waits.py` sample sheet |
| **The model never learns that a wait did nothing** | The "[no visible change]" note skips `wait` steps, in the training data and in the agent. After a useless wait the model sees the same screen and an unmarked wait line, so it decides the same way again | `data/v46_build.py` `SKIP_TYPES`, `eval/androidworld/lfm_agent.py` |
| The wait labels are mostly right | Before/after pairs, 40 random AndroidControl waits: 33 of 36 with a changed next screen are justified (loading → loaded, "Saving…" → saved, a toast gone), 4 of 4 with an unchanged next screen are not. Whole split: 64 waits are followed by an action on the unchanged screen; 24 by another wait on a static screen | `analysis/done_audit/validation_2026-11-25.json` (corrects an earlier 43% estimate made from single screenshots) |
| Fewer waits alone is not the goal | v4.1 / v4.2 cut waits to about 6% of steps and solved fewer tasks (14 and 13 vs v4's 18, with guards) | `aw_waits.py` |

So the round targets the loop, not the labels: show the model when a wait changed nothing, and teach it to act then.
Stuck screens themselves (no results, dead taps) need recovery data, which this round does not add.

---

## Data: `experimentalmachines/MobileAgent-SFT-v4.7` (public)

v4.6's 185,643 training rows, then (`data/v47_build.py`, AWS EC2 CPU, seed 47):

| Step | Rule |
|---|---|
| Wait notes | A history line of a `wait` step gets " [no visible change]" when the episode's next screen is unchanged (v4.6's rule, `train/screen_change.py`, screens paired by position). Train, gate splits and probes. Every other line is left as it is |
| Relabel | A `wait` row whose next screen is unchanged and whose next action is not `wait` takes that next action as its label (same screen, so its coordinates hold) |
| Counterfactual **nwait** (5,000 rows) | A real screen the human acted on (not `wait`; `status` only if judged COMPLETE) + its history + 1 appended wait (2 for a quarter of rows), noted "[no visible change]" → the human's action on that screen |
| Counterfactual **nwaitload** (1,500 rows) | A real loading screen (a `wait` whose next screen changed) + the same appended noted wait(s) → `wait` |
| Wait probes (AndroidControl **test**) | **W0_base**: 300 rows with a real action, unchanged. **W1_nwait**: the same rows + one appended noted wait (expected: not `wait`). **W2_loading**: real waits whose next screen changed (expected: `wait`) |
| Round-8 probes | Rebuilt with the wait notes; otherwise identical |

Contamination rules unchanged (no AndroidWorld, MobileWorld or AndroidLab tasks, apps, trajectories or checkers). The
AndroidWorld runs were only read for diagnosis; nothing from them is trained on.

**Not changed in v4.7** (checked, small, or too costly for now):

| Gap | Size | Why not now |
|---|---|---|
| `complete` rows kept with no visible proof | 2,688 rows; by eye 9 / 16 visibly done, 6 / 16 provable only from the history (share, send), 1 / 16 probably not done | A re-judge that sees the last few screens costs about $3–5 of GPU; the expected change is about 170 rows |
| Intent wording names a nearby element | about 3 / 32 (AMEX 1 / 12, GUI-Odyssey 2 / 20); the tap itself is right | Needs a model pass over about 100k rows |
| History lines with no screen pair get no note | 34,198 lines (screens outside the mix); about 1% would be noted | Small |
| Stuck screens (no results, dead taps) | Rare in human demonstrations | Needs on-policy recovery data in non-AndroidWorld apps (next round) |

---

## Candidate F (the only one), only if E passes its own offline gate

| Item | Value |
|---|---|
| Start | E's merged weights (pinned Hub revision) |
| Recipe | A new LoRA r64 α128 on top, lr 1e-4 cosine with 3% warm-up, 32 rows per step, **1,000 steps** over a fixed 32,000-row mix: every counterfactual nwait / nwaitload row (6,500), every relabelled row, and the rest drawn uniformly from the v4.7 train split (seed 47) |
| Prompt | 24-step history, notes with the fine rule, `wait` steps noted too |

If E fails its gate, F is not trained; the v4.7 changes go into the next full retrain together with whatever fixes E's
failure. A full retrain on v4.7 (about 6,000 steps) is the fallback if F fails a non-wait check below.

---

## Offline gate for F (all must hold)

1. **E's round-8 gate**, every bar unchanged (`docs/PREREG_v46.md`), on the v4.7 splits.
2. **Wait probes**, scored with the same local evaluator for D, E and F: llama-server, Q4_K_M GGUF (the deployment
   format), `analysis/done_audit/probe_llama.py`.

| Probe | Measure | Bar |
|---|---|---|
| **W1_nwait**: a screen needing an action, after a wait that changed nothing | share of `wait` | **≤ 5%** |
| W1_nwait | action type matches the human's | ≥ E's on W0_base − 3 points |
| **W2_loading**: a real loading screen | share of `wait` | **≥ E's − 10 points** |
| W0_base: a screen needing an action | share of `wait` | ≤ E's + 2 points |

D's numbers on the wait probes are logged below before F exists.

---

## Online test (only if the offline gate passes)

| Item | Value |
|---|---|
| Benchmark | AndroidWorld seed 30, 116 tasks, Mac, as every seed-30 run |
| Harness | `--history_steps 24 --nochange_notes --change_rule fine --note_waits` (F's training format) |
| Pass rule | **Successes ≥ E's, and useless waits (next screen unchanged) ≤ half of E's** |
| Reported | Wait share, streaks of 3 or more, false completes, against D and E (`analysis/done_audit/aw_waits.py`) |

---

## Log

### 2026-11-25 04:20 PST — v4.7 data built, reviewed and published (no candidate exists)

**`experimentalmachines/MobileAgent-SFT-v4.7` @ `f1e466a7004643c94a41afd66836636f67595bda`.** Training split
192,143 rows; F's mix `train_f` 32,000 rows (6,564 new or relabelled + 25,436 drawn from `train`).

| Change from v4.6 (185,643 rows) | Rows |
|---|---|
| `wait` history lines noted "[no visible change]" | 611 (28,758 wait lines with a changed next screen stay as they are; 640 without a screen pair) |
| `wait` relabelled to the next action on the unchanged screen | 64: click 42, input_text 12, scroll 5, status 2, other 3 |
| nwait rows (1 / 2 appended waits) | +3,754 / +1,246 |
| nwaitload rows (1 / 2 appended waits) | +1,138 / +362 |
| `wait` labels in the result | 8,028 (6,592 − 64 + 1,500) |

**Review by eye** (`analysis/done_audit/validation_v47_2026-11-25.json`, 16 random per kind):

| Kind | Result |
|---|---|
| Relabelled waits | 16 / 16: identical screens, label = the human's next action (2 inherit AndroidControl's "text already visible before `input_text`") |
| nwait | 16 / 16: loaded screen, the human's action |
| nwaitload | 9 visibly loading, 3 defensible (a tap not yet answered, an ad, a live camera), 4 look loaded (the app was still busy: the next screen changed) |

Kept as built. 1,500 nwaitload against 5,000 nwait rows = 23% "wait again", close to AndroidControl's humans after a
wait that changed nothing (24 of 86, 28%).

**Gate-split side effect:** AndroidLens marks far more waits as useless (1,843 noted, 1,295 changed); AndroidControl
test 33 noted, 1,911 changed.

### 2026-11-25 05:10 PST — second review, rebuild, D's baselines, and an amendment (no candidate exists; no E result seen)

**Second review by eye** (owner: "Do 32 more by eye"; 32 fresh rows per kind with the episode's real next screen;
totals over 48 per kind in `analysis/done_audit/validation_v47_2026-11-25.json`):

| Kind | Result (48) |
|---|---|
| Relabelled waits | 47 right; 1 wrong: a wait on a blank page relabelled `complete` (that `complete` row was kept with no visible proof) |
| nwait | 48 / 48 |
| nwaitload | 38 loading or defensible, 8 look loaded, 2 show a dialog that needs a tap; 6 of the 10 doubtful ones sit right before `complete` |

**Rebuilt and re-published: `MobileAgent-SFT-v4.7` @ `420637e95d63c823f04c84bb9c03dd8159275f21`** (replaces
`f1e466a7`, which no candidate used):
- A wait is relabelled to `status` only if that `status` row was judged COMPLETE (63 relabels; the blank-page one stays a wait).
- nwaitload rows come only from waits whose next real action is not `status` / `answer` (pool 3,393). A fresh
  16-row check: 10 loading, 3 defensible, 3 doubtful.
- Probes byte-identical to the first build.

**D's baselines** (local llama-server, Q4_K_M, `analysis/done_audit/probe_llama.py`, `results/v47_dev/`):

| Probe | D's share of `wait` | D's share of `status` |
|---|---|---|
| W0_base | 2.0% | 6.7% |
| W1_nwait (one noted useless wait) | 0.3% | 7.3% |
| W1u (same, note removed) | 0.3% | 8.3% |
| W2_loading | 59.3% | 12.7% |
| C3_stale (screen before the last tap) | 35.0% | 36.3% |
| **C3n_stale_note** (same, the tap noted "[no visible change]") | **48.3%** | 28.3% |

**What this changes.** On AndroidControl screens D does not repeat waits (W1 0.3%), so W1's bar (≤ 5%) measures
nothing. D waits when a tap did nothing (C3n 48%), as in AndroidWorld: 104 of D's 180 first waits there follow a tap
that left the screen unchanged. v4.6's stale rows (6,965 "tap noted no change → do what the screen needs") already
target that state, so E may fix most of it.

**Amendment (registered before any E result):**
1. **Primary offline wait measure: share of `wait` on C3n_stale_note**, read from E's own round-8 probe outputs and
   from the local GGUF evaluator for D, E and F. W1 stays reported, not gated.
2. **F is on hold until E's offline gate and AndroidWorld run.** F is not trained if E has C3n `wait` ≤ 15% and
   AndroidWorld useless waits (next screen unchanged) ≤ 6.7% of steps (half of D's 13.4%): v4.7 then goes into the
   next full retrain. If E fails either, F is trained as registered above, with its wait bars replaced by:
   **C3n `wait` ≤ 15%**, W2_loading `wait` ≥ E's − 10 points, and E's round-8 gate.

### 2026-11-25 05:40 PST — third review by eye of the published build (no candidate exists)

Owner: "do 32 more of each". Rows not reviewed before, seed 49 (`analysis/done_audit/v47_sheets_round3.py`):

| Kind | Result | All reviews of `420637e9` |
|---|---|---|
| Relabelled waits | 16 / 16 (the last unreviewed ones) | **63 / 63 right**; 4 inherit AndroidControl quirks |
| nwait | 32 / 32; 4 inherited label quirks (2 AndroidControl taps off target, 2 GUI-Odyssey intents naming a nearby element) | **80 / 80** |
| nwaitload | 17 loading, 10 defensible, 5 doubtful (a permission dialog, a tooltip, a toast, a picker, a list) | **40 / 48 good (83%)** |

No change to the data: the doubtful nwaitload rows are about 1 in 6 of 1,500 rows (≈ 0.1% of the split), against
5,000 nwait rows teaching the opposite on loaded screens; no automatic rule separates them.
