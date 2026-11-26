# Preregistration: round 14 (v4.12), the review's six steps

Registered 2026-11-26 15:20 Asia/Manila, before any round-14 training or measurement.

Owner, after the external review ([`docs/reviews/codex-adversarial-review-2026-11-26.md`](../reviews/codex-adversarial-review-2026-11-26.md))
and its verification ([PREREG_v411](round-13-yardstick-own-history.md), 15:00): "Proceed to do them all."

Round 13's E-S was stopped and is not evaluated (its returns crossed the human patch, its 12-step cap dropped most
endings, it used labels that had failed their audit). This round replaces it.

---

## Step 1 and 2: corrected RL against a matched control

Both arms start from E, use the **same 400 training episodes** (seed 14: 280 AndroidControl, 120 GUI-Odyssey, at most
12 steps each), the same history format (24 steps, fine notes) and a new LoRA r64 / α128.

| What changed from round 13 (review finding) | Now |
|---|---|
| Returns crossed the human patch (C1) | A step's return sums rewards only to the end of its own natural segment (UI-S1's t_end); the episode term uses the first segment only |
| A premature `complete` could be patched and continue (C1) | A premature `status` or `answer` ends that attempt, as in deployment |
| Wrong actions could earn full reward (M1) | `score.strict_match`: inside the element box when known (no distance fallback), else within 5% of the screen; exact text up to case and spaces. Fixtures: the review's three wrong-but-accepted cases are now rejected |
| The 12-step cap dropped the endings (M2) | Longer episodes become **suffix windows** (the last 12 steps, the human's earlier steps as history), so every window holds the real ending. This is a different condition from starting at step 0, said here |
| Labels that failed their audit (M4) | AndroidControl's judge verdicts are not used: its human `complete` labels stay as they are |
| "Completed" counted truncated prefixes | Counted only when the window reaches the true end with no patch and every step right |

Tests: `train/test_semi_online_rl.py` (the review's counter-example: a premature `complete` now gets return 0.1 and a
negative advantage; a near miss scores 0.5 and its segment ends; continuations are new segments; collection rows) and
the strict-matcher fixtures. Both pass.

| Arm | Training |
|---|---|
| **E-S2** (RL) | Semi-online RL: 100 batches × 4 episodes × 4 rollouts, temperature 1.0, patch budget 1, γ 0.5, ω 1.0, lr 3e-5, one AdamW step per batch. SageMaker A10G (us-west-2) |
| **E-D** (matched control) | E's **greedy** own-history rollouts on the same episodes; every step where its action fails the strict matcher becomes an SFT row (screen + own history → the human's action and intent); premature endings are kept as rows and patched. Mixed with uniform replay of E's training split to 3,200 rows; 100 steps × 32, lr 1e-4 cosine. SageMaker L4 (us-east-1) |

**Decision between the arms:** RL is kept only if it beats the control on the strict multi-step test (below) by
≥ 2 points; otherwise the simpler control is the candidate.

**Offline gate (both arms, same job):** round 11's first 10 checks (no regression vs E) and the ending probes
(M_done `status` ≥ 50%, M_notdone `status` ≤ 25%), as round 13.

## Step 3: full outcome accounting (reporting, every AndroidWorld run from now on)

`analysis/aw_outcomes.py`: success; unsuccessful completion claims (`complete` on any task not fully met, **partial
credit included**); wrong answers; infeasible declarations; budget exhaustion; exceptions. For the done check: blocks,
**recovered successes** (blocked, then succeeded) and **lost successes** (succeeded without the check on the paired run,
failed with it). A lower false-complete count is a secondary result; the primary is additional successes.

## Step 4: reliable test phones, then contemporaneous paired runs

- Diagnose why AndroidWorld's app snapshots are missing ("Snapshot not found" about 270 times per pass) and restore a
  per-task reset; verify it with sentinel checks (state written in one task must be gone at the next task's start).
- Until the reset is verified, every comparison runs **E and the candidate in the same session**, one on each emulator,
  with the emulator assignment **swapped halfway** (by task-list halves), cold-booted.
- No cloud emulator machines until this works locally (review recommendation 2).

## Step 5: does the agent need to see the screen before its last action? (diagnostic)

On the 164 seed-30 false completes of the replay set: classify the last step (screen unchanged and noted; changed in the
wrong way; changed as intended but more was needed). If a before/after view could distinguish a meaningful share that
the current note cannot, a before/after input is designed as its own round; otherwise it is dropped.

## Step 6: fresh confirmation seeds and one frozen candidate

- **AndroidWorld seeds 101, 202 and 303** are reserved now. They have never been run by any model in this project. They
  are opened once, for one frozen final candidate against v4 and E, after steps 1–5.
- Seeds 7 / 1234 / 2026 and AndroidControl test are labelled reused from now on.

## The multi-step test as a provisional measure (review M6)

The SOP validation registered in round 13 finishes as registered and is reported with leave-one-model-out sensitivity,
the per-depth premature-stop hazard, and the share of episodes ending on a human `wait`. Whatever ρ it gives, SOP stays
a provisional regression measure; candidates are judged on it with a strict-matcher variant added
(`eval/androidcontrol/sop.py --strict`), and only AndroidWorld decides.

---

## Log

### 2026-11-26 16:01 Asia/Manila — RL smoke passed; full E-S2 launched; harness and accounting done

- RL smoke `lfm3-r14-rl-smoke` (A10G, ~21 billed minutes): episode build with suffix windows (850 AndroidControl and 510
  GUI-Odyssey episodes become windows that keep their ending; GUI-Odyssey endings 597 done / 450 unfinished), 2 RL
  batches (71 samples with non-zero advantage; strict step accuracy 0.69; 2 rollouts ended by a premature terminal
  action), merge, all evals and the gate ran ("R14 rl smoke DONE"). Full run `lfm3-r14-rl` launched (100 batches).
- The control's smoke (`lfm3-r14-sft-smoke`) waits for an L40S (the us-east-1 L4 could not be used: the SageMaker role has
  no access to that bucket, and IAM is not changed without the owner). If no capacity by 17:30, the control runs on the
  us-west-2 L4 after round 12's job.
- Harness: after a blocked `complete`, `answer` is excluded too (review M10); unit test updated and passing.
- Step 3: `analysis/aw_outcomes.py`. On existing runs it shows that **running out of steps is the largest failure**
  (v4 seed 30: 55 of 116; E: 59; held-out seed 7: v4 62, E 55), ahead of unfinished `complete` claims (20–37) and wrong
  answers (12–17). Rounds 8–12 targeted the second.

### 2026-11-26 16:12 Asia/Manila — step 4: the per-task reset fixed and verified; step 5: before/after input dropped

**Step 4.** Root cause of the carryover: `/data/data/android_world/snapshots` did not exist on either emulator, so
AndroidWorld's per-task restore (`TaskEval.initialize_task` → `app_snapshot.restore_snapshot`) skipped every app
("Snapshot not found"); app data carried over between tasks in **every earlier run of every model** (ours and the
baselines alike). Fix: AndroidWorld's own app setup (clear data, configure, save the snapshot) on both emulators
(`scripts/androidworld/setup_snapshots.py` app by app on 5556, 24 / 24 ok; the stock `--perform_emulator_setup` on 5558,
completed): 24 snapshots each. Verified with `scripts/androidworld/verify_reset.py`: a marker written into each app's
data is removed by AndroidWorld's own restore for **23 / 23 apps on both emulators** (clipper is never restored by
design). Not covered: data held by Android's system providers (contacts, SMS, call log, shared storage), which each
task's own setup handles. Consequence, as registered: every comparison from now on runs E and the candidate in the same
session on the reset emulators; earlier numbers are not mixed with new ones.

**Step 5.** All 164 seed-30 false completes: the last action changed the screen in 134, left it unchanged in 30 (the
note already flags those). By eye, 24 random changed cases (`results/r13_dev/fc_last_step_review.json`): the current
screen visibly shows the goal unmet in **11** (stopwatch started instead of paused, Wi-Fi turned on, a file instead of a
folder, wrong contact fields, a running timer), parts of a multi-part goal remain in **8**, the evidence is only on the
screen before the last action in **2**, unclear in **3**. A before/after input would address about 2 in 24: **dropped**
as registered. The levers are judging the current screen against the goal and tracking which parts remain.

### 2026-11-26 18:19 Asia/Manila — SOP validation finished (bar not met); E-S2 training done; control launched

- **SOP validation over all seven models** (`analysis/sop_validation.py`, 400 episodes each): ρ(SOP, AndroidWorld successes)
  = **0.33** (exact one-sided p 0.25; bar 0.70 **not met**); TSR 0.63 (p 0.07); premature `status` vs false completes 0.43.
  Leave-one-out ρ(SOP) 0.00–0.53. The multi-step test stays a provisional regression check only, as registered; it cannot
  select a model. Consequence for the arm decision: the "≥ 2 points on the strict multi-step test" rule picks between two
  arms on a measure that does not rank models; any arm that passes the offline gate must therefore be compared on paired
  AndroidWorld runs (step 4) before it is kept.
- E-S2 (RL): 100 batches finished at 18:05 (last batch: strict step accuracy 0.62, premature terminal 1.2% per step);
  merge done, evals and gate running on the A10G job.
- Control `lfm3-r14-sft` (full; collect → mix → 100×32 SFT → evals) launched on ml.g6e.2xlarge, us-west-2, 6 h cap (the
  smoke ran there). Round 12's E-V job is still evaluating on the L4.

### 2026-11-26 21:43 Asia/Manila — E-S2 (RL) and E-D (control) both fail the offline gate; no online test

Gate: round 11's checks (early `status` ≤ 3.80%, C1 ≤ 22%, the rest no worse than E) plus the ending probes. Raw logs:
`results/r14_dev/r14_rl.log`, `r14_sft.log`.

| Check | E | E-S2 (RL) | E-D (control) | Bar |
|---|---|---|---|---|
| AndroidControl high step accuracy | 0.758 | 0.743 | 0.753 | no worse than E (round 8 bar) |
| Early `status` (2+ steps before the end) | 3.55% | **4.20%** ✗ | 3.70% | ≤ 3.80% |
| Probe C1 (done on a finished-looking history) | 20.0% | **22.3%** ✗ | **25.3%** ✗ | ≤ 22% |
| Probe C3 stale (repeats a stale tap) | 16.7% | **22.0%** ✗ | **24.7%** ✗ | round 8 bar (E passes at 16.7%) |
| M_done (says done on judged-finished final screens) | 0% | **1.0%** ✗ | 83.5% ✓ | ≥ 50% |
| M_notdone (says done on judged-unfinished final screens) | 0% | 0% ✓ | **56.5%** ✗ | ≤ 25% |
| Other checks (answer, complete, AndroidLens, T_term, C2, C3n) | pass | pass | pass | |

- **Both arms fail; per the registered gate and round 11's precedent there is no online test and nothing is published.**
  E stays the newest model, v4 the main model.
- **RL (100 batches, 400 episodes) barely moved the model**: M_done 1%, and it is slightly worse than E on repeated taps
  (C3 22% vs 17%) and early `status`. Training curve (20-batch means): strict step accuracy at temperature 1.0 0.68, 0.63, 0.65, 0.67, 0.69 and first-segment return 2.2, 2.0, 2.2, 2.3, 2.5: flat to slightly rising, on different episodes each batch, so not distinguishable from noise.
  At this scale the update was too small to help and large enough to cost a little.
- **The control did change behaviour, in the wrong way**: it learned "done" (83.5% on finished screens) but also says
  done on 56.5% of unfinished final screens: the same failure as E-T in round 11 (95% / 65%). Training on E's own
  mistakes with the human's labels pushes toward "end here", whatever the screen shows.
- The registered tie-break (RL kept only if it beats the control by ≥ 2 points on the strict multi-step test) is moot:
  neither arm is a candidate. Not run.
- Round 12's E-V is still training on the L4 (step ≳ 900 of 1000) and its evals follow.

### 2026-11-26 21:44 Asia/Manila — what "running out of steps" is (read from the seed-30 episodes of v4 and E)

Budget-exhausted episodes (no `status`/`answer`, no exception): v4 55, E 59 of 116. Successes finish in a median of 5–5.5
steps (maximum 7 for v4, 11 for E), so the step budget is not what binds: a longer budget would not rescue these. **36 of
55 (v4) and 43 of 59 (E) are loops** (fewer than half of the episode's actions are distinct; for E, 39% of steps repeat the
previous action exactly). Loop guards were already tried (round 5: v4 + guards 18 vs 18, v4.1 + guards worse) and gave no
gain. So the largest failure is a model that does not find the right action and then repeats a wrong one, not an
interface or budget problem. That is a capability / training-signal limit, not something a cheap harness change fixes.

### 2026-11-26 22:02 Asia/Manila — round 12's E-V fails its offline gate; round 14 closed

E-V (`lfm3-r12-ev`, 1,000 × 32, done-check rows included) finished; log `results/r12_dev/r12_ev.log`. Round-11 checks:
all 10 pass (AndroidControl high 0.760, early `status` 3.49%, C1 22.0%, C3 stale 17.7%). Ending probes: M_done 91% ✓,
M_notdone 34.5% (bar ≤ 25%; round 12's registered bar is on the system, below). Done-check probes (registered bars):

| Check | E-V | Bar |
|---|---|---|
| V_done: check answers yes on finished screens | 82.0% | ≥ 75% ✓ |
| **V_notdone: check answers no on unfinished screens** | **74.5%** | ≥ 75% ✗ (one screen short of 150/200) |
| Model + check on M_done: `status` and not blocked | 79.0% | ≥ 50% ✓ |
| **Model + check on M_notdone: `status` and not blocked** | **19.5%** | ≤ 15% ✗ |

**Fails (2 of 16 checks); no replay run, no online run, nothing published.** The first miss is by one screen and I do not
round it up after the fact; the second is 4.5 points over and is not borderline. E-V's AndroidControl done-check rows
come from the label source that failed its audit (noted in PREREG_v411), so the result is confounded either way.

**Round 14 conclusion.** No candidate this round: E-S2 (RL) and E-D (control) fail round 11's gate, E-V fails round 12's.
Paired AndroidWorld runs (step 4) are therefore not run (there is nothing to pair against E), and the fresh seeds 101,
202 and 303 stay unopened. v4 remains the main model; E the newest. The reset fix (step 4) and the outcome accounting
(step 3) stay in the harness for any later run. Compute this round: RL job ~2.2 h on A10G, control ~1.3 h on L40S, E-V
~9 h on L4 (all SageMaker, us-west-2).
