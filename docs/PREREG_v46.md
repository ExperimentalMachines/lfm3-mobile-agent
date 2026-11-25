# Preregistration: round 8 (v4.6), "done but not done yet"

Written 2026-11-24 22:40 Asia/Manila (14:40 UTC), before any round-8 candidate existed. The training data was being
built (its final counts go into the [Log](#log) before training). Append-only.

**Status: post-hoc development round.** The diagnosis used AndroidWorld seed-30 runs (development seed) and the
AndroidControl test split; the sealed held-out v4 result stays as it is.

---

## Why: what the audit found (2026-11-24)

| Finding | Evidence | Files |
|---|---|---|
| **The model decides `complete` from its own history, not the screen** | Same unfinished AndroidControl test screen; only the history changed to list every step: D says `complete` 3.7% → **53.7%**, v4 2.0% → 40.3%. Finished screen with the last 2 steps cut from the history: D 84% → 54% | `analysis/done_audit/build_history_probes.py`, `results/v46_dev/probes_r7.json` |
| AndroidWorld false completes look exactly like that | 137 false completes in five seed-30 runs (56 tasks). The model says `complete` right after the step it meant to be last (119 clicks); the screenshot shows the task undone (Wi-Fi still on, reply not sent, note empty, nothing recorded) | `analysis/done_audit/aw_false_complete_dump.py` |
| Training data teaches the shortcut | In every demonstration the history and the screen agree, so the history alone predicts the end. 629 `status` rows follow a step marked "[no visible change]" | v4.5 audit |
| Round 6's no-visible-change rule is mostly wrong | It flags 570 of 8,444 consecutive AndroidControl test screens; 67% of those have a real change (size selected, star, word chip) | `train/screen_change.py` docstring |
| Some `complete` labels are wrong | 24 random AndroidControl terminal rows checked by eye: 19 done, 1 not done, 2 still loading, 2 unsure | `analysis/done_audit/manual_terminal_review.json` |
| AndroidControl `wait` steps carry a copied intent | e.g. "click on the upload button" three times with `wait`; the history then claims clicks that never happened | v4.6 build stats |

---

## Data: `experimentalmachines/MobileAgent-SFT-v4.6` (public)

v4.5's 173,430 training rows, then (`data/v46_build.py`, AWS EC2 CPU):

| Step | Rule |
|---|---|
| New change rule | `train/screen_change.py`: 360 × 800 grayscale, status and navigation bars masked, changed if > 0.02% of pixels differ by > 25 grey levels (threshold chosen by eye on test pairs). Every history note recomputed from the episode's real screens; no note where a screen is missing |
| Completion judge | Every `status` row: Qwen/Qwen3-VL-8B-Instruct @ `0c351dd` sees only the goal and the final screenshot. NOT_COMPLETE → row dropped; PENDING → relabelled `wait`. Calibration: 21 / 24 agreement with the hand review |
| `wait` intents | A `wait` step whose intent does not describe waiting gets "Wait for the screen to finish loading." (targets and history lines) |
| Counterfactual rows (training episodes only) | **stale**: screen before the last action + full history, last step noted "[no visible change]" → the expert action on that screen. **ahead**: screen 2–3 steps before the end + full history → the expert action on that screen. **short**: judged-COMPLETE final screen + history without its last 1–2 steps → `status complete`. Only at the end of episodes, so mid-task use of the history as memory is untouched |
| Gate splits | Notes recomputed with the new rule; probes rebuilt from the new test split |

Contamination rules unchanged (no AndroidWorld, MobileWorld or AndroidLab tasks, apps, trajectories or checkers). The
AndroidWorld false completes were only read for diagnosis; nothing from them is trained on.

---

## Candidate E (the only one)

| Item | Value |
|---|---|
| Start | `LiquidAI/LFM3-VL-2B` @ `23387bed` (as v4 and D) |
| Recipe | D's: LoRA r64 α128, lr 2e-4 cosine with 3% warm-up, 32 rows per step, no gradient checkpointing (bs 4 × 8), one pass over the v4.6 train split |
| Prompt | 24-step history, notes with the new rule |
| Hardware | Modal H100; checkpoints every 100 steps to a public Hub repo |

Smoke first: the training command on 200 rows (4 steps) plus evals and probes on 16 rows.

---

## Offline gate (all must hold)

E on its own format; v4 and D numbers from the same evaluator (`scripts/training/v4_reference_r7.json`, round 7).

| Check | v4 | D | Bar |
|---|---|---|---|
| AndroidControl test, high-level step accuracy | 0.727 | 0.753 | ≥ 0.707 |
| `dev_answer` / `dev_complete` | 0.890 / 0.763 | 0.882 / 0.800 | ≥ 0.840 / ≥ 0.713 |
| AndroidLens English step accuracy at steps ≥ 10 | 0.367 | 0.471 | ≥ 0.367 |
| AndroidControl: `status` ≥ 2 steps before the end | 2.74% | 3.64% | ≤ 3.24% |
| **Probe: unfinished screen, history claims every step** | 40.3% | 53.7% | **≤ 15%** |
| **Probe: screen before the last action, step noted "no visible change"** | — | 32.0% | **≤ 10%** |
| **Probe: screen before the last action, no note** | 31.3% | 37.0% | **≤ 20%** |
| **Probe: finished screen, true history (must still stop)** | 73.7% | 84.3% | **≥ 70%** |
| **Probe: finished screen, history without its last 2 steps** | 38.7% | 54.3% | **≥ 60%** |

Probes: 300 rows each, built from AndroidControl **test** episodes (never trained on) by
`analysis/done_audit/build_history_probes.py`; E's probes use its own prompt format (new notes). The counterfactual
training rows have the same shapes, so the probes check that the behaviour transfers to held-out episodes; the online
test decides.

**Reported, not gated:** AndroidLens all steps, end-of-task `complete`, early `status`; AndroidControl terminal
`complete`; `dev_memgui`; validation loss.

---

## Online test (only if the offline gate passes)

| Item | Value |
|---|---|
| Benchmark | AndroidWorld seed 30, 116 tasks, Mac, as every seed-30 run (`scripts/androidworld/local_v41_dev_aw.sh`) |
| Harness | `--history_steps 24 --nochange_notes --change_rule fine` (E's training format) |
| Pass rule | **False `complete` ≤ 15 and successes ≥ 18** (v4's count), or net paired gain over v4 ≥ R = 9 tasks |
| Reported | False completes and successes against v4 and against D's run (exception run, 2026-11-24) |

If E fails the offline gate: round 8 is reported as negative; E published as not promoted.

---

## Log

### 2026-11-24 23:40 Asia/Manila — data-construction changes before any candidate (no candidate exists)

**1. Judge rule: two stages.** Stage 1 (Qwen3-VL-8B) called 4,677 of 13,170 AndroidControl and 416 of 475 MemGUI
`status` rows NOT_COMPLETE (plus 67 PENDING, 3 UNSURE). Its reasons show many are "the screen does not prove it"
(a share or logout leaves no trace on the final screen), not "the screen shows it is not done". Dropping all would
remove a third of the `complete` labels. New rule:
- **Drop** a `status` row only if stage 1 says NOT_COMPLETE **and** stage 2 says CONTRADICTS. Stage 2 is
  Qwen/Qwen3-VL-32B-Instruct @ `0cfaf481`, asked whether something *visible* shows the task not done (CONTRADICTS) or
  the screen merely lacks proof (NO_PROOF).
- **PENDING** rows are relabelled `wait`, as before.
- On the four flagged hand-reviewed rows stage 2 agreed with the hand review on two. Its CONTRADICTS calls are
  spot-checked by eye before the build uses them (result logged).

**2. Notes are paired by position, not step number** (found while checking the build). GUI-Odyssey and AMEX step
numbers are not positions: AMEX counts from 1, and merged keyboard steps leave gaps.

| Source | Rows whose step number differs from their position | Effect in v4.5 |
|---|---|---|
| AMEX | all 21,925 | Round 6's notes, which keyed screens by step number, were attached to the wrong action |
| GUI-Odyssey | 11,810 | Wrong after a merged keyboard step |

v4.6 keys screens by the row's position (its last history line number), and leaves a line without a note when
either screen is missing.

**3. Reported, not gated: MobileJudgeBench** (WesleyWzq/MobileJudgeBench @ `2170e51c`, CC BY 4.0). Other agents' real
runs on SPA-Bench, A3, AndroidArena and B-MoCA (AndroidWorld and AndroidLab parts not downloaded), with human success
labels: 648 runs, 376 successes. Of the 482 runs where the agent itself said done, humans judge 131 failures. One row
per run at the moment that agent decided (`analysis/done_audit/mjb_build.py`); the share where the model says `status`:

| | v4 | D |
|---|---|---|
| Human success (376) | 65.4% | 78.7% |
| Human failure (272) | 33.8% | 48.5% |
| **Agent said done, humans say failed (131)** | **45.0%** | **60.3%** |

E is measured the same way (its own format).

### 2026-11-24 23:55 Asia/Manila — stage-2 judge result and the drop decision (no candidate exists)

| Source | Stage 1 NOT_COMPLETE | Stage 2 CONTRADICTS (dropped) | Stage 2 NO_PROOF (kept) |
|---|---|---|---|
| AndroidControl | 4,677 | 2,031 | 2,646 |
| MemGUI | 416 | 374 | 42 |

- **Spot check by eye** (16 random CONTRADICTS, `analysis/done_audit/contradicts_review.json`): about 6 right, 7 wrong,
  3 ambiguous.
  - Right: not added to cart, wrong file restored, timer not extended, wrong route mode, song not played.
  - Wrong: "Entry saved" and "Reminder completed" toasts, a workout in progress, an edit applied.
  - Neither judge alone nor both together reach high precision on "is it done?" from a final screenshot.
- **Decision: drop the 2,405 rows both judges flag** (11% of `complete` labels; roughly 40% of them wrong). The costs
  are lopsided:
  - A wrong `complete` label teaches exactly the false-done failure this round targets.
  - A lost good one only lowers the stop rate, which the `T_term` probe gate (≥ 70%) guards.
  - PENDING (67) → `wait`, as registered.
- **Short-history counterfactual rows** use only stage-1 COMPLETE final screens.

### 2026-11-25 00:25 Asia/Manila — v4.6 data built (no candidate exists)

**Training split: 185,643 rows.** E's one pass = ⌈185,643 / 32⌉ = **5,802 steps**.

| Change from v4.5 (173,430 rows) | Rows |
|---|---|
| `status` rows dropped (both judges) | −2,405 (AndroidControl 2,031, MemGUI 374) |
| `status` → `wait` (still loading) | 67 |
| `wait` intents fixed | 5,616 targets, 22,309 history lines |
| Notes (new rule, paired by position) | 62,161 → 7,794; 34,198 history lines without a screen pair get no note |
| Counterfactual rows: stale / ahead / short | +7,140 / +5,266 / +2,212 |
| `status` labels in the result | 13,385 (incl. the 2,212 short rows) |

- **Gate splits:** notes recomputed. Probes: 300 rows each from the same AndroidControl test episodes as round 7's
  (same seed), in E's format.
- **Build:** `results/v46_dev/build_stats.json`. One rerun was needed after the build instance's disk filled (no
  change to the code or inputs).

### 2026-11-25 01:00 Asia/Manila — E restarted on Colab (Modal workspace disabled)

- **What happened:** E's Modal run stopped at about step 105 with "workspace … is disabled" (Modal billing / spend
  limit; owner action needed). The step-100 checkpoint had not finished uploading, so E restarts from step 0.
- **New plan:** per the owner's earlier instruction ("Run it on google colab and we'll switch to modal later,
  checkpoint well"), E runs on a Colab A100 or G4 (`scripts/training/colab_r8_start.sh`) with the identical command and
  checkpoints every 100 steps to the public Hub repo. The credit guard stops Colab below 1.5 units; the same command
  finishes on Modal once it is re-enabled.
- **Unchanged:** recipe, data and gate. E smoke passed on Modal before the run (training, Hub restore, all evals,
  probes and the round-8 gate on 16 rows).

### 2026-11-25 01:10 Asia/Manila — E's micro-batch: 2 × 16 (same 32 rows per step)

On the Colab A100-40GB, bs 4 × 8 ran out of memory at about step 10: v4.6's 24-step rows are longer than the v4 rows
of the speed check (the Modal smoke already peaked at 37.1 GB on an H100). E restarted from step 0 with micro-batch
2 × 16 and PyTorch's expandable-segments allocator. It is still 32 rows per optimizer step with the same schedule; only
memory and speed change, which the prereg allows ("the micro-batch choice ... does not change the maths"). The Modal
stretch uses the identical command.

### 2026-11-25 09:35 Asia/Manila — E's offline gate: FAIL (2 of 10 checks, both near the bar)

E trained 5,802 steps (Colab to step 3,100, then Modal H100 from the Hub checkpoint; Modal metered $17.31 incl. the
evals). `results/v46_dev/e_eval/r8e_offline_gate.json`.

| Check | v4 | D | **E** | Bar | Pass |
|---|---|---|---|---|---|
| AndroidControl test, high-level step accuracy | 0.727 | 0.753 | **0.758** | ≥ 0.707 | ✓ |
| `dev_answer` / `dev_complete` | 0.890 / 0.763 | 0.882 / 0.800 | **0.882 / 0.775** | ≥ 0.840 / ≥ 0.713 | ✓ |
| AndroidLens step accuracy at steps ≥ 10 | 0.367 | 0.471 | **0.462** | ≥ 0.367 | ✓ |
| AndroidControl `status` ≥ 2 steps before the end | 2.74% | 3.64% | **3.55%** | ≤ 3.24% | ✗ |
| Probe C1: unfinished screen, history claims every step | 40.3% | 53.7% | **20.0%** | ≤ 15% | ✗ |
| Probe C3n: screen before the last action, step noted | — | 32.0% | **0.3%** | ≤ 10% | ✓ |
| Probe C3: screen before the last action, no note | 31.3% | 37.0% | **16.7%** | ≤ 20% | ✓ |
| Probe T: finished screen, true history | 73.7% | 84.3% | **78.0%** | ≥ 70% | ✓ |
| Probe C2: finished screen, last 2 steps cut | 38.7% | 54.3% | **71.0%** | ≥ 60% | ✓ |

What E does instead of `status` on the stale screens: C3n 98% click (redo the tap; D: 48% wait), C3 65% click, 8.7% wait.

**Per the registered rule:** round 8 is reported as negative and E is not promoted; the online test was conditional on
the gate.

### 2026-11-25 09:55 Asia/Manila — reported: MobileJudgeBench for E (not gated)

Same 648 runs and rule as D and v4 (`results/v46_dev/mjb/e.jsonl`, `e_summary.json`); share where the model says `status`:

| | v4 | D | **E** |
|---|---|---|---|
| Human success (376) | 65.4% | 78.7% | **69.7%** |
| Human failure (272) | 33.8% | 48.5% | **37.1%** |
| **Agent said done, humans say failed (131)** | 45.0% | 60.3% | **45.0%** |

E says "done" less often than D on other agents' failures (back to v4's level), but the gap between successes and
failures (E 32.6 points, v4 31.6, D 30.2) is about the same: on outside data E is more cautious, not yet a better
judge of "done".

**Owner decision:** run E on AndroidWorld seed 30 as an exploratory exception (as D in round 7), not a confirmatory test
(variant U, `--history_steps 24 --nochange_notes --change_rule fine`).

### 2026-11-25 13:00 Asia/Manila — exploratory AndroidWorld run of E (owner exception, not confirmatory)

Seed 30, 116 tasks, variant U (`--history_steps 24 --nochange_notes --change_rule fine`), Q4_K_M GGUF. The first launch
crashed on every step (agent bug: `sc` shadowed in `lfm_agent.step`, fixed in `86bb728`; 17 crashed episodes deleted, log
kept). Four harness errors (task setup / SMS checker parsing a gRPC fork log line) were re-run once with
`scripts/androidworld/rerun_harness_errors.sh`. `results/v46_dev/aw_e_vs_d_vs_v4_rerun.json`.

| | v4 | D | **E** |
|---|---|---|---|
| Successes | 18 | 21 | **19** |
| False completes | 25 | 27 | **24** |
| Wait share of steps | 29.1% | 16.9% | **3.5%** |
| Useless waits (next screen unchanged) | 21.1% | 13.4% | **2.3%** |
| Repeated-tap runs (same tap 3+ times) | 6 | 18 | **23** |

E vs D: 5 wins, 7 losses (McNemar p = 0.77). Against the registered online bar (false completes ≤ 15, successes ≥ 18)
E would fail on false completes. Waits nearly gone; false completes barely moved: 10 of the first 19 are partly done
multi-part tasks (round 10, `docs/PREREG_v48.md`).

### 2026-11-25 20:33 Asia/Manila — owner: E on the held-out AndroidWorld seeds (post-hoc; registered before any run)

Owner: "What's wrong with the E that we haven't run the full suite on it yet. I think it's okay". E failed its offline
gate (2 of 10, narrowly), so the round-8 rule never sent it to the held-out seeds. This entry adds that evaluation as an
owner decision, with the comparison fixed before any episode runs.

| Item | Value |
|---|---|
| Question | Is E at least as good as v4 on the held-out seeds, so that it can replace v4 as the main model? |
| Runs | AndroidWorld seeds 7, 1234, 2026 × 116 tasks; E's Q4_K_M GGUF (`experimentalmachines/LFM3-VL-2B-MobileAgent-v4.6-E-GGUF`, sha256 `fa8f2dca…`), harness variant U (`--history_steps=24 --nochange_notes=true --change_rule=fine`), prompt v4, thinking on, the same llama-server flags as v4 |
| Same rules as v4's sealed runs | `--task_random_seed=<seed> --n_task_combinations=1`; an episode whose emulator crashed before step 1 is re-run once; exceptions count as failures; outcome lines kept out of the logs; no result read until all three seeds have finished |
| One difference | A cold-booted emulator for every pass (`scripts/androidworld/local_sealed_aw_e.sh`), as for every development pass since 2026-11-22 (the accessibility forwarder fails on a second pass) |
| Analysis | `analysis/sealed_analysis.py` with E added as an arm: the same paired, template-clustered sign-flip test (10,000 draws) against v4 and GUI-Owl on the same instances |
| **E replaces v4 as the main model if** | (a) E − v4 lower 95% bound > −6.9 points (the preregistered non-inferiority margin of `docs/PREREG_v4.md`), **and** (b) E's false completes on the 348 episodes ≤ v4's 71 |
| Otherwise | v4 stays the main model; E's held-out numbers go on its card and in `docs/results.md` |

**Status: post-hoc.** The held-out seeds were unsealed on 2026-11-19, and v4's held-out false completes were read for
round 6's diagnosis, so they are not pristine for models built after that. E was never trained or selected on them.
MobileWorld for E needs a new cloud machine (owner's approval) and is not part of this rule.
