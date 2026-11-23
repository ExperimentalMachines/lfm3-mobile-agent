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

### 2026-11-22 04:00 Asia/Manila — offline evals complete (D and E running, no D/E outcome seen)
| Dev split (step success) | v4 | v4.1 | v4.2 |
|---|---|---|---|
| dev_answer | 0.890 | 0.882 | 0.868 |
| dev_complete | 0.762 | 0.850 | 0.812 |
| dev_screenqa | 0.790 | 0.780 | 0.788 |
| dev_odyssey | 0.637 | 0.634 | 0.645 |
| dev_amex | 0.731 | 0.731 | 0.714 |
| MMStar / MMLU | 0.529 / 0.504 | 0.556 / 0.511 | 0.557 / 0.503 |

- Files: `results/v41_dev/`, `results/v42_dev/`; v4.2's self-history decisions (enough to rebuild its data from v4.1's):
  `results/v42/selfhist_state.json.gz`. The A100 session is stopped.

### 2026-11-22 06:05 Asia/Manila — D and E final; MobileWorld model selected by the rule
| Seed 30 | Successes / 116 (primary) | Exceptions | Exceptions dropped | On the 79 tasks no run crashed |
|---|---|---|---|---|
| v4 | 18 | 4 | 18/112 | 11 |
| A (v4 + guards) | 18 | 1 | 18/115 | 11 |
| B (v4.1) | 12 | 7 | 12/109 | 8 |
| C (v4.1 + guards) | 14 | 8 | 14/108 | 8 |
| D (v4.2 + guards) | 13 | 24 | 13/92 | 9 |
| E (v4.2) | 18 | 9 | 18/107 | 10 |

- **D's exceptions are infrastructure.** Emulator 5556's accessibility service stopped answering, and the last 20 tasks
  in run order (`SystemBluetoothTurnOnVerify` through `VlcCreateTwoPlaylists`) each ended after ~30 s with "Could not get
  a11y tree" before the model acted. The rest are 2 gRPC-log and 2 app-data-reset crashes.
- **Rule applied as written:** exceptions count as failures, so D = 13 < 18. Fallback: the best of A, B, C, E with at
  least 18. A and E tie at 18; the tie order (E, B, C, A) selects **E = v4.2 without guards** (MobileWorld case `v42`,
  native typing). Not re-litigated: where neither D nor E crashed (87 tasks), D and E tie 13–13, so the guards make no
  measurable difference to v4.2 here.
- **Reading:** no variant beats v4 on seed 30. v4.1 alone lost ground (12); v4.2, trained on its own replayed history,
  is back to v4's level (18). Guards: neutral on v4 (A) and v4.2 (D vs E), +2 on v4.1 (C vs B).

### 2026-11-22 16:00 Asia/Manila — MobileWorld result (the one counted run): v4.2 8/105
| MobileWorld, 105 English GUI-only | Successes | Both | v4.2 only | Other only | Exact McNemar p |
|---|---|---|---|---|---|
| **v4 (primary comparison)** | 6 | 5 | 3 | 1 | **0.625** |
| GUI-Owl-1.5-2B (descriptive) | 22 | 7 | 1 | 15 | 0.0005 |
| MAI-UI-2B (descriptive) | 11 | 5 | 3 | 6 | 0.51 |

- **v4.2 = 8/105** (104 tasks with a result; ThanksgivingPrepTask failed setup on every attempt, as for every model).
  Gained vs v4: MastodonChangeHeader, MastodonFollow, MastodonNewPost; lost: CloseFlightMode. **Not significant.**
- **Loops fell, success barely moved:** `wait` 21% → 5% of steps (non-wait-intent waits 931 → 18), steps repeating
  the previous intent 67% → 33%, tasks ending at the 50-step limit 85 → 69. Step counts are not strictly comparable
  (v4 used synthetic Enters, v4.2 native typing).
- **Run log:** the Mac watcher stopped acting after the last invocation (12:39) because the gcloud login expired
  (VM status unreadable); the rule's one remaining fresh-container invocation (ThanksgivingPrepTask only) was started
  by hand at 15:43 with the same restart + `mw_resume.sh v42` steps, and ended setup_failed → `v42_complete`.
- Files: `results/mobileworld/mw_r3_comparison.{md,json}`, `results/mobileworld/v42_gui_en_r3_summary.json`
  ([`analysis/mw_summarize_r3.py`](../analysis/mw_summarize_r3.py)); trajectories in `results/mobileworld/traj_r3/`
  (git-ignored).
- **Status of this follow-up:** post-hoc; MobileWorld is now a development benchmark. v4's 6/105 stays the held-out
  MobileWorld number; v4's sealed AndroidWorld result stays the AndroidWorld claim.

### 2026-11-22 16:35 Asia/Manila — noise replicate started (before any new training)
- **R = v4.2 replicate on seed 30** (identical to E: same GGUF, harness and flags; output `results/androidworld/lfm3vl2b_v42_rep/`),
  emulator 5558. Purpose: the number of tasks that flip between two identical v4.2 passes (R) is the noise yardstick for
  the next candidates, which all start from v4.2. Its score is not a new result for v4.2 and selects nothing.

### 2026-11-22 17:00 Asia/Manila — round 5 plan (pre-declared before any new training)
Basis: [research report](research/training-scale-and-own-attempt-learning.md) and two agy passes
(`results/agy/v5_plan_review/`, `results/agy/v5_plan_rereview/`). Both candidates start from **v4.2** (merged).

| Candidate | What | Answers the owner's question |
|---|---|---|
| **P = v4.2 + step-DPO on its own mistakes** | v4.2 decodes greedily (as at inference) on training rows. Where its action fails the AndroidControl scorer's `match` (eval/androidcontrol/score.py: type, 14%-radius click, text F1), a pair is made: preferred = the human step, rejected = v4.2's own step. Loss = DPO (β 0.1) + 0.5 × SFT on the preferred step; new language-only LoRA r64/α128 (projector not trained), one pass over the pairs | "Learn from its own attempts" |
| **S = v4.2 + more SFT on the same mix** | 800 more steps × 32 rows sampled uniformly from v4.2's own training data (so ~43% are rows it already saw: this is "more epochs" without changing the mix); warm-up → constant → linear decay over the last 15%; new LoRA r64/α128 | "Train more over epochs" |

**Pair rules (P):** training rows only (no dev/test episode, no AndroidWorld app, as in [datasets.md](datasets.md)); states
whose human step is `wait` are excluded (noisy label); intent wording alone never makes a rejection; unparseable outputs
are not used as rejections. Pair statistics by kind (early `status`/`answer`, missed stop, `wait`, copied intent,
wrong click, wrong type) are saved before training.

**Offline gate (each candidate, before any emulator time):** parse rate ≥ 0.99; AndroidControl high-level step accuracy
≥ 0.712 (v4.2 0.732 − 0.02); terminal `complete` accuracy ≥ 0.70 (v4.2 0.738); `dev_answer` ≥ 0.848 (v4.2 0.868 − 0.02).

**Online gate (AndroidWorld seed 30, development; exceptions count as failures):**
- Noise yardstick **R** = tasks that flip between E (v4.2) and its replicate (started 16:35).
- A candidate **passes** if successes ≥ 16 **and** false `complete`s ≤ 15 (v4.2: 25), **or** its net gain over E is
  ≥ max(R, 6) tasks. False `complete` = the agent ended with `complete` and the checker scored 0
  (`analysis/failure_analysis/aw_taxonomy.py`, primary category `false_complete`).
- Both pass → more successes; tie → fewer false `complete`s; tie → P. Neither → round 5 is negative; v4.2 stays.
- Passing makes a **held-out candidate** (sealed seeds next), not a "better" claim. No MobileWorld run in this round.
- More than 10 exceptions in a run → re-run only the crashed tasks once, reported separately.
- **Budget order:** P first; S only if Colab credits remain after P's training and export.

### 2026-11-22 17:35 Asia/Manila — round 5 launched (no outcome seen)
- Colab-b A100 session `v5` (6.73 compute units/h; 43.95 left at start). Jobs: `scripts/training/jobs/lfm3_v5_a100.json`.
- Settings fixed at launch: P samples 16,000 training rows (15% terminal rows), DPO β 0.1, SFT weight 0.5, lr 2e-5,
  batch 4 × 8, one pass; S = 800 steps, lr 1e-4 (half of v4.2's peak, as continued training), WSD with the last 15%
  decaying, sampler seed 5 (v4.2 used 42, so the 25,600 rows are a fresh uniform draw from the same mix).
- Candidate names: P = `LFM3-VL-2B-AndroidAgent-v4.3-dpo`, S = `LFM3-VL-2B-AndroidAgent-v4.3-sft` (public repos, marked
  unvalidated). Correction to the agy response: the projector was never trained in any v4.x run (`modules_to_save: []`).
- **17:45: replicate R void.** All 116 episodes ended with "Could not get a11y tree" before the model acted (emulator
  5558's accessibility forwarder was dead from the start; same failure as D's last 20 tasks on 5556). Moved to
  `results/androidworld/_invalid/lfm3vl2b_v42_rep_a11y_dead_20261122/`; both emulators cold-restarted; R relaunched on
  5558. From now on every pass is checked for exceptions within its first episodes.

### 2026-11-22 20:15 Asia/Manila — P fails the offline gate; P2 pre-declared (post-hoc variant), run before S
| Offline gate | v4.2 | P | Threshold |
|---|---|---|---|
| AndroidControl high-level step accuracy | 0.732 | **0.545** | ≥ 0.712 → **fail** |
| Terminal `complete` accuracy | 0.738 | 0.885 | ≥ 0.70 |
| `dev_answer` / `dev_complete` | 0.868 / 0.812 | 0.875 / 0.850 | ≥ 0.848 / — |

- **P gets no emulator time** (rule). Cause, from the per-type scores: whole action types collapsed regardless of the
  screen — `open_app` 0.946 → 0.161, `wait` 0.591 → 0.004, `scroll` 0.623 → 0.160, while `navigate_back` rose 0.662 →
  0.840. 3,039 of the 4,163 pairs were generic wrong clicks/types, and `wait` was only ever rejected (human-wait states
  were excluded), so DPO lowered those action types' prior everywhere (a known DPO failure: likelihood displacement).
  Pairs: 16,000 rows, 74% matched, 4,163 pairs (wrong target 2,102, wrong type 937, missed stop 558, early stop 356,
  copied intent 139, wait 71). DPO itself trained as intended (reward accuracy 0.62 → ~0.84, margin ~0.4).
- **P2 (post-hoc, declared before any P2 or S outcome):** the same pairs restricted to the behaviours the report
  targets and balanced so no action type is only ever rejected: early stop 356 + missed stop 356 (random 356 of 558) +
  copied intent 139 = 851 pairs; no `wait`, wrong-target or wrong-type pairs. DPO β 0.1 with SFT weight 1.0 (was 0.5),
  lr 1e-5 (was 2e-5), one pass. Same offline and online gates as P. Name `LFM3-VL-2B-AndroidAgent-v4.3-dpo2`.
- **Order:** P2 runs before S (the owner ranked learning from own attempts above more epochs); S follows if credits
  remain. S's first minutes of training are discarded (killed for the reorder, not for any result).

### 2026-11-22 20:20 Asia/Manila — S shortened to 500 steps (credits; no S outcome seen)
- 19.80 compute units remained at 19:58 (A100 6.73/h). P2 plus 800 S steps plus evaluations would exhaust them before
  S's evaluation ends, so S runs **500 steps** (16,000 rows, ≈0.17 epoch more; WSD decay over the last 75). The 25 S steps
  run before the 20:15 reorder were discarded. S restarts after P2's offline evaluation finishes. Gates unchanged.

### 2026-11-22 20:25 Asia/Manila — noise yardstick R = 9
| Seed 30 | Successes | Exceptions | False `complete` |
|---|---|---|---|
| E = v4.2 (03:06 pass) | 18 | 9 | 25 |
| v4.2 replicate (17:37 pass, cold-booted emulator 5558) | 19 | 2 | 22 |

- **R = 9 tasks flip** between two identical v4.2 passes (5 replicate-only, 4 E-only). The online gate's success path
  therefore needs a net gain of ≥ 9 over E. False `complete` counts (22–25) stay inside the 20–28 band of all earlier runs.
- Counts from [`analysis/aw_false_complete.py`](../analysis/aw_false_complete.py) (reproduces the taxonomy's v4 25 and E 25).

### 2026-11-22 20:30 Asia/Manila — P2 passes the offline gate
| Offline gate | v4.2 | P2 | Threshold |
|---|---|---|---|
| Parse rate | 1.000 | 1.000 | ≥ 0.99 |
| AndroidControl high-level step accuracy | 0.732 | 0.728 | ≥ 0.712 |
| Terminal `complete` accuracy | 0.738 | 0.785 | ≥ 0.70 |
| `dev_answer` / `dev_complete` | 0.868 / 0.812 | 0.875 / 0.838 | ≥ 0.848 / — |

- P2 (851 balanced stop/copy pairs) keeps step accuracy and stops correctly more often at the last step. It goes to the
  online gate (seed 30). S was restarted at the declared 500 steps (the pipeline had started the old 800-step setting).
- **20:41 P2 pass void, restarted 20:45.** Its first tasks failed with "Could not get a11y tree" before the model
  acted: emulator 5558 had just finished the replicate, and its accessibility forwarder does not survive into a second
  pass (third occurrence). Moved to `results/androidworld/_invalid/lfm3vl2b_v43dpo2_a11y_dead_20261122/`. The launcher
  now cold-boots its own emulator before every pass. The restarted pass's first episodes ran without exceptions.
- **22:48 the Mac rebooted** (no panic report) during both passes: P2 had 55 episodes, S had 6. Both passes were
  **resumed from their checkpoints** at 23:18 (completed episodes kept, only unstarted tasks run; nothing re-run). The
  adb server was down after the reboot and was started by the first `adb devices`.

### 2026-11-23 00:30 Asia/Manila — P2 fails the online gate
| Seed 30 (116 tasks) | Successes | Exceptions | False `complete` | Net vs E | Flips vs E | McNemar p |
|---|---|---|---|---|---|---|
| E = v4.2 | 18 | 9 | 25 | — | — | — |
| v4.2 replicate | 19 | 2 | 22 | +1 | 9 (= R) | 1.0 |
| **P2 = v4.3-dpo2** | **21** | 3 | **28** | **+3** (7 − 4) | 11 | 0.55 |

- **Gate:** behaviour path needs false `complete` ≤ 15 → **28, fail**; success path needs net gain ≥ 9 → **+3, fail**.
  P2 is not a held-out candidate.
- Its offline gain at the last step (terminal `complete` 0.738 → 0.785) did not transfer: on the phone it ends with a
  false `complete` *more* often than v4.2 (28 vs 22–25). Stopping correctly on a recorded final screen is not the same
  skill as knowing, mid-task, that the task is done.
- Of its 7 E-only wins, 4 (SMS reply ×2, Bluetooth on/off) are tasks the identical v4.2 replicate also won over E (one
  was an E exception); against the replicate P2 is +2 with 6 flips (p 0.69). This is noise-level.
- Counts: [`analysis/aw_false_complete.py`](../analysis/aw_false_complete.py) and the new
  [`analysis/aw_paired_flips.py`](../analysis/aw_paired_flips.py) (reproduces R = 9: 5 replicate-only, 4 E-only).
- S is still running (47/116 at 00:30: 7 successes, 16 false `complete`s, so its behaviour path is already closed;
  its success path is decided when the pass ends).

### 2026-11-23 01:35 Asia/Manila — S fails the online gate; round 5 is negative, v4.2 stays
| Seed 30 (116 tasks) | Successes | Exceptions | False `complete` | Net vs E | Flips vs E | McNemar p |
|---|---|---|---|---|---|---|
| E = v4.2 | 18 | 9 | 25 | — | — | — |
| v4.2 replicate | 19 | 2 | 22 | +1 | 9 (= R) | 1.0 |
| P2 = v4.3-dpo2 | 21 | 3 | 28 | +3 | 11 | 0.55 |
| **S = v4.3-sft** | **24** | 1 | **37** | **+6** (10 − 4) | 14 | 0.18 |

- **Gate:** behaviour path needs false `complete` ≤ 15 → **37, fail**; success path needs net gain ≥ 9 → **+6, fail**.
  Neither candidate passes, so by the declared rule **round 5 is negative and v4.2 stays**. No held-out run.
- S has the most seed-30 successes of any LFM3 version so far (MAI-UI-2B: 32), and its gain is the same size against all three references
  (+6 vs E, +5 vs the replicate p 0.23, +6 vs v4 p 0.15). It is still below the pre-declared noise yardstick, so it is
  a lead, not a result.
- **How S gains:** it ends far more episodes with `complete` (56 vs 37–38; right 19, wrong 37) and fewer at the step
  budget (37 vs 53–59). Stop precision is unchanged (0.34; v4.2 0.34 / 0.41; P2 0.36). Of its 10 wins over E, 4 are
  tasks the identical v4.2 replicate also won (SMS reply, Bluetooth ×3: noise); 5 are tasks where E used up its steps
  and S stopped with `complete` (Wi-Fi/Bluetooth combos, brightness, two recipe tasks). Whether S acted better there or
  only stopped where v4.2 kept going is not determined. P2 moved the same way, less.
- Pass timing: 6 S episodes before the 22:48 reboot, 110 after the resume; 1 exception (none a11y-related).

### 2026-11-23 01:55 Asia/Manila — corrections after an independent review (no decision changes)
The agy quota was exhausted (resets ≈ 2026-11-28), so the round-5 results were checked by an independent Claude
reviewer with the same prompt ([`results/review/v5_results_review_claude/report.md`](../results/review/v5_results_review_claude/report.md)).
All gate decisions reproduce. Corrections to earlier entries (the log stays append-only):

| Entry | Correction |
|---|---|
| 00:30 P2 | "Ends with a false `complete` *more* often" and "stopping correctly … is not the same skill" overstate noise. Paired on tasks neither run crashed: false `complete` 26 vs 25 against E (+9 / −8, p 1.0); episodes ending with `complete` +10 / −7 (p 0.63). P2's online stopping did not change measurably; why its offline gain did not show up is not determined. Its final DPO reward margin was 0.047 (P: 0.43) |
| 01:35 S | Holds, with paired tests: S ends more episodes with `complete` (+25 / −11 vs E, p 0.03; +28 / −9 vs the replicate, p 0.003); false `complete`s +20 / −11 vs E (p 0.15), +24 / −9 vs the replicate (p 0.01) |
| 22:48 reboot note | "Nothing re-run" is inaccurate: the task in progress at the reboot was restarted from scratch after the resume (P2: RecipeDeleteMultipleRecipesWithNoise, S: CameraTakeVideo; both failed). Their aborted first attempts left no result |
| Run conditions (not logged before) | E was the second pass on emulator 5558 without a cold boot (9 exceptions, 2 of them the end-of-pass a11y failure); the replicate, P2 and S were cold-booted. On tasks neither run crashed: replicate 0, P2 +2 (p 0.75), S +5 (p 0.27). [`analysis/aw_paired_flips.py`](../analysis/aw_paired_flips.py) now prints this view |
| S offline gate (not logged before) | S passed at 21:56 (AC high-level 0.736, terminal `complete` 0.757, `dev_answer` 0.860, `dev_complete` 0.875), before its 22:12 seed-30 pass |
| Heading times | The 16:35 and 17:00 entries were committed at 16:09 (`da3a327`); the replicate actually started 16:05 and was relaunched 17:37. The 20:15 entry was committed at 19:54 (`bc38f4b`), the 20:20/20:25 entries at 20:08, the 20:30 entry at 20:27. These declared earlier than labelled. The 17:35 entry was committed at 18:34 (`fb5bbc6`), after P's pair statistics were printed; its settings had been in code since 16:18 (`2341bd7`) and were not changed |
| Counting scripts | `aw_false_complete.py` now reproduces the taxonomy's `false_complete` exactly (answer tasks, partial credit and unparseable last steps excluded); counts are unchanged for every round-5 run and now match the taxonomy for v1–v4.2 too. Success was changed from `> 0` to `>= 1` after P2's result; no count changes (exception episodes store NaN) |

### 2026-11-23 09:50 Asia/Manila — merged into `main` (no decision changes)
- The owner decided to merge `v41-followup` into `main` on the independent stand-in review (01:55 entry), with the
  agy results review still outstanding (quota exhausted until ≈ 2026-11-28). That review is to be run on `main` when
  the quota returns; any finding will be logged here as a new entry.
- Before the merge, `README.md`, `docs/audits.md`, `docs/repository.md` and the folder guides were brought up to date
  with rounds v4.1–v4.3. The round-5 counts were re-run from the episode files and are unchanged (successes 18 / 19 / 21
  / 24, false `complete` 25 / 22 / 28 / 37 for E / replicate / P2 / S).

### 2026-11-23 10:15 Asia/Manila — agy results review not run (owner's decision; no decision changes)
- A retry of the agy results review hit the same account-wide quota on every agy model (gpt-oss-120b-medium: resets in
  126 h; a one-line availability probe of gemini-3.8-flash-high: same error), logged in
  [`results/agy/v5_results_review/agy_stdout.log`](../results/agy/v5_results_review/agy_stdout.log).
- The owner decided not to run it. This supersedes the plan in the 09:50 entry: the independent stand-in review
  (01:55 entry) is the only adversarial check of the round-5 results.
