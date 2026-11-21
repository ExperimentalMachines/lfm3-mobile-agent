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
| 3 | **v4.1 training data.** D1: the 4,104 copied-intent `wait` targets (and 13,145 history lines that show them) get the intent "Wait for the screen to finish loading." D2: 5,244 rows (10% of eligible AndroidControl / GUI-Odyssey / AMEX rows) get one extra history step — the last step repeated once or twice, or a wait — with the human's next action still the target | [`data/v41_build_parquet.py`](../data/v41_build_parquet.py) | — |

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
