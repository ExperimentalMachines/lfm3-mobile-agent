# Preregistration: v4.1 follow-up for MobileWorld

Written 2026-11-21 20:05 Asia/Manila (12:05 UTC), before any v4.1 or guarded result existed (v4.1 training had
just started; no seed-30 or MobileWorld run of any variant had begun). Append-only: later entries go under
[Log](#log) with a timestamp.

**Status: post-hoc.** The idea came from reading v4's MobileWorld trajectories after its result was final. v4's
reported MobileWorld score (6/105) and every sealed AndroidWorld result stay as they are. Every number from this
follow-up is labelled "made after seeing the MobileWorld results". GUI-Owl and MAI-UI get no such second attempt.

---

## Why

| Evidence | Source |
|---|---|
| In MobileWorld, 931 of v4's 4,461 steps (21%) were `wait`, none of them under an intent about waiting; 73% of consecutive steps repeat the previous intent word for word; 85 of 104 tasks ended at the 50-step limit | v4 MobileWorld trajectories (`results/mobileworld/traj_r2/v4_gui_en_r2/`) |
| Same pattern in AndroidWorld: 35% / 37% of v4's steps are `wait` on held-out seeds 7 / 2026 | sealed AndroidWorld episodes |
| **Cause, in v4's training data:** 4,151 AndroidControl rows are `wait`; 3,918 of them (94%) repeat the previous step's intent ("Click on the search button" → `wait`) | `alpharomercoma/AndroidAgent-SFT-v4` @ `3375539` |
| MobileWorld's own agents type without pressing Enter; v4's adapter added an Enter step after every text entry (138 extra steps; 3 tasks lost the Enter at the step limit). v4's training data has only 12 `keyboard_enter` rows; after typing the model nearly always taps a button | `eval/mobileworld/lfm3_mw_agent.py`, MobileWorld `a026188`, v4 training data |

---

## The three changes

| # | Change | Where | Default |
|---|---|---|---|
| 1 | **Loop guards.** G1: a `wait` whose intent does not mention waiting or loading is replaced. G2: an action proposed for the third time in a row is replaced when the screen is the same as two steps earlier (frozen screen or on/off toggle). Replacement = the model asked again with its own intent prefilled and a grammar that excludes the banned type, `wait`, `status` and `answer` | [`train/agent_guards.py`](../train/agent_guards.py) | off (`--guards`, `LFM3_GUARDS=1`) |
| 2 | **MobileWorld typing as MobileWorld defines it:** `input_text` only types; Enter only when the model outputs `keyboard_enter` | [`eval/mobileworld/lfm3_mw_agent.py`](../eval/mobileworld/lfm3_mw_agent.py) | off (`LFM3_MW_TYPING=native`) |
| 3 | **v4.1 training data.** D1: the 4,104 `wait` targets whose intent does not mention waiting or loading (3,918 of them copy the previous intent word for word), and the 13,145 history lines that show such steps, get the intent "Wait for the screen to finish loading." D2: 5,244 rows (10% of eligible AndroidControl / GUI-Odyssey / AMEX rows) get one extra history step — the last step repeated once or twice, or a wait — with the human's next action still the target | [`data/v41_build_parquet.py`](../data/v41_build_parquet.py) | — |

**v4.1 training:** identical to v4 except the text edits — same base model, recipe (LoRA r64, lr 2e-4, 1,250 × 32),
rows, row order (same shuffle seed and row count), image budget, prompt and dev splits; A100 like v4. Job:
[`scripts/training/jobs/lfm3_v41_a100.json`](../scripts/training/jobs/lfm3_v41_a100.json).

**Contamination rule (extended to MobileWorld):** no AndroidWorld or MobileWorld tasks, task variants, trajectories,
checkers or seeded app content in training data. The edits use only v4's own training rows.

---

## Development selection (AndroidWorld seed 30)

| Variant | Model | Guards (1) |
|---|---|---|
| A | v4 | on |
| B | v4.1 | off |
| C | v4.1 | on |

- Each variant runs once on AndroidWorld seed 30 (116 tasks), with v4's seed-30 harness (prompt v4, thinking on, same
  llama-server flags, Q4_K_M). Reference: v4 = 18/116 on seed 30 (existing run, not repeated).
- **Selection rule:** the variant with the most seed-30 successes. Ties: B, then C, then A (fewer runtime heuristics,
  training fix preferred).
- **Gate:** if the selected variant scores below 18, MobileWorld is not run and the follow-up is reported as negative.
- Change 2 cannot be tested in AndroidWorld (its `input_text` types and presses Enter for every agent); it is part of
  every MobileWorld run in this follow-up.
- Offline (v4.1 only, informational): AndroidControl test step accuracy, the v4 dev splits, general-knowledge retention.

---

## MobileWorld run (one run, the selected variant + change 2)

| Item | Setting |
|---|---|
| Tasks | The same 105 English GUI-only tasks |
| Benchmark settings | MobileWorld `a026188`, 50 rounds, 3 s step wait, `--auto_retry 3`, temperature 0 |
| Completion rule | Unchanged (PREREG_v4 2026-11-19 01:55 / 05:20 / 05:45) |
| Model | Q4_K_M, llama.cpp `cd959bae9`, image ≤ 880×880 px area (unchanged; GUI-Owl and MAI-UI keep their larger budgets) |
| Infrastructure | New GCP n2-standard-16 spot VM (environment), Colab T4 on the `colab-b` account (model server), reverse SSH tunnel; as before |
| Primary comparison | Selected variant vs v4 (6/105): paired, exact two-sided McNemar on the same 105 tasks |
| Secondary (descriptive) | vs GUI-Owl (22/105) and MAI-UI (11/105) from the existing runs; not re-run |

- Only one MobileWorld run counts. Other variants may be run afterwards only as labelled ablations; they never replace
  the primary result.
- v4.1 is not run on the held-out AndroidWorld seeds in this follow-up; the AndroidWorld held-out claim stays v4's.
- Adversarial review: `agy` with `gpt-oss-120b-medium` on this plan and the code before the MobileWorld run, and on
  the results and docs before merging.

---

## Log

### 2026-11-21 20:05 Asia/Manila
Plan written. v4.1 training job launched 20:00 on a Colab A100 (`colab-b` session `v41`). Nothing evaluated yet.

### 2026-11-21 20:11 Asia/Manila
agy review of plan and code (`results/agy/v41_plan_review/`): GO AFTER FIXES. One valid finding (D1 wording: 4,104
relabelled targets, of which 3,918 copy the previous intent) — fixed above; no count or code changed. The other seven
were checked against the code and data and did not hold (details in `response.md`). Run A had started at 20:06; no
seed-30 result had been looked at.

### 2026-11-21 22:05 Asia/Manila — amendment: fix 4 and the all-fixes candidate (before any seed-30 score)
- **Why:** the owner asked for fix 4 (train on the model's own mistakes) so that the one MobileWorld run applies all
  four fixes.
- **Fix 4 = v4.2.** v4.1's merged weights replay 40% of training episodes (deterministic by episode id;
  AndroidControl / GUI-Odyssey / AMEX) on their recorded screens with their own history. Steps the model gets right (the
  AndroidControl scorer's match rule) keep its own words in the history; wrong steps and steps without a stored screen
  get the human step. The rows of those episodes then carry this self-generated history; targets, images and row order
  are unchanged. v4.2 is trained from the base model with the same recipe ([`data/v42_selfhist.py`](../data/v42_selfhist.py),
  [`scripts/training/vm_v42_pipeline.sh`](../scripts/training/vm_v42_pipeline.sh)). No environment, no teacher, no
  benchmark data. Closest published method: UI-S1's semi-online patching (arXiv 2509.11543), without its RL.
- **New seed-30 variants:** D = v4.2 + guards (all four fixes once MobileWorld typing is added), E = v4.2.
- **Selection rule (replaces the one above):** D is the primary MobileWorld candidate and runs if its seed-30 score is
  at least 18 (v4). If D scores below 18, the best of A, B, C, E with at least 18 runs instead (ties: E, B, C, A); if
  none reaches 18, MobileWorld is not run. A, B, C and E are reported as seed-30 ablations.
- **State at this time:** run A at 69/116 episodes, its success count not computed (one early episode's outcome was
  seen while checking guard logs); B and C not started; v4.1 training at step ~900 of 1,250. Literature notes:
  `docs/research/notes/training-on-own-mistakes-and-overfitting/`.

### 2026-11-21 22:25 Asia/Manila — fix 4 detail (before any v4.2 data or seed-30 score)
- The literature review (`docs/research/training-on-own-mistakes-and-overfitting.md`) noted that replacing every wrong
  step with the human step never shows the model its own mistakes. Added: where v4.1 wrongly predicted `wait` (its
  typical loop), the row for that step also shows that prediction (its own intent + `wait`) as the last history step.
  A wait leaves the screen unchanged, so the recorded screen and the human target still fit. The count is reported
  (`rows_own_wait_mistake`). Nothing else changes.

### 2026-11-22 01:25 Asia/Manila — exceptions on seed 30; dev evals blocked (B and C running)
- **Exceptions:** counted as failures, as in v4's seed-30 score of 18 (its 4 setup crashes were not re-run). No
  seed-30 re-runs for any variant (A–E). Secondary: the official rule (exceptions dropped) is reported next to it.
  Fixed after seeing interim counts: B 4 successes in 48 episodes (2 exceptions), C 4 in 52 (6 exceptions). All 8 are
  setup crashes before the model acted (gRPC log lines in adb output; app-data reset failures).
- **Offline dev evals:** v4.1's five dev-split evals failed. Hugging Face now refuses to *read* private repos while the
  account is over its private-storage limit (403), and the dev splits live only in the private v4 dataset. v4.1's
  AndroidControl test and general evals finished. Seed-30 selection does not use the dev evals.

### 2026-11-22 01:40 Asia/Manila — Hugging Face reads restored
- With the owner's approval, deleted 7 private checkpoint repos of finished trainings (`*-LoRA-ckpt`, `*-RL-ckpt`).
  Each model's final adapter and training logs remain in its final repo. Private reads worked again at once.
- v4.2's dev evals run as planned. v4.1's dev evals are re-run on the same Colab session after the current cell ends.

### 2026-11-22 03:50 Asia/Manila — B and C final (D and E running, no D/E outcome seen)
| Seed 30 | Successes / 116 (primary) | Exceptions | Exceptions dropped | vs v4: gained / lost |
|---|---|---|---|---|
| v4 | 18 | 4 | 18/112 | — |
| A (v4 + guards) | 18 | 1 | 18/115 | +3 / −3 |
| B (v4.1) | 12 | 7 | 12/109 | +2 / −8 (no loss is an exception) |
| C (v4.1 + guards) | 14 | 8 | 14/108 | +6 / −10 (3 losses are exceptions) |

- All 16 B/C exceptions are setup crashes before the model acted. Most are gRPC log lines in adb output (B and C ran on
  two emulators at once, as D and E do now); the rest are app-data reset failures.
- B's losses include 4 Calendar tasks (`SimpleCalendarEventsOnDate`, `…AnyEventsOnDate`, `…DeleteOneEvent`, plus
  `…LocationOfEvent` for C). They will be analysed after D and E finish.
- v4.2 offline (AndroidControl test, high-level step accuracy): v4 0.728, v4.1 0.732, v4.2 0.732; low-level 0.908 /
  0.895 / 0.888. AndroidControl's test labels keep the copied-intent waits, which v4.1/v4.2 are trained away from.
- D (v4.2 + guards, emulator 5556) started 03:03; E (v4.2, emulator 5558) started 03:06. The rule is unchanged: D runs
  on MobileWorld if it reaches 18.
