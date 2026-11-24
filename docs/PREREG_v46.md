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
