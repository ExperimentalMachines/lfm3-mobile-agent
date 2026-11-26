# Where our Android agent fails (LFM3-VL-2B v1–v4.2, local result files only)

Scope: read-only analysis of this repo's own result files (2026-11-22). No web sources. Every number names the file it
came from. Numbers marked "computed" were recomputed from the saved episode / trajectory files with helper scripts in
the session scratchpad (`/private/tmp/claude-501/-Users-alpha-lfm3-android/4efa3977-532d-411f-ad28-f4737438aa00/scratchpad/failure_analysis/`,
temporary: `aw_features.py` → `aw_features.json`, `aw_taxonomy.py`, `aw_paired.py`, `aw_details.py`, `aw_more.py`,
`fresh2.py`, `mw_compare.py`, `mw_tails.py`, `train_curves.py`, `offline.py`, `ac_preds.py`, `latency.py`).
Recomputed success counts match the published ones exactly (dev: v1 15, v2 3, v3 13, v4 18, v4+g 18, v4.1 12,
v4.1+g 14, v4.2 18, v4.2+g 13, GUI-Owl 23; held-out: v4 18/17/19, GUI-Owl 16/13/18, v1 11/10/11), and the recomputed
outcome labels match the existing `*.failure_modes.json` files for v1, v2, v3 and GUI-Owl.

Short names: v4+g = v4 with runtime loop guards (A), v4.1 (B), v4.1+g (C), v4.2+g (D), v4.2 (E); "held-out" =
sealed seeds 7, 1234, 2026 pooled (348 episodes per arm, preregistered re-runs of setup crashes applied).

## 1. Failure taxonomy per version (AndroidWorld seed 30, plus the 348 held-out episodes)

### Takeaway
Two behaviours cost the most tasks in every LFM3 version, and no version so far has changed them. (1) Episodes stall in
a loop that repeats the same intent until the step budget runs out (44 of v4's 98 seed-30 failures; 129 of 294
held-out failures). (2) The agent ends tasks it has not finished with `complete` (20–28 per run; 71 held-out). On top
of that, v4's typed answers are usually wrong (14 of its 20 answers on seed 30). GUI-Owl almost never ends a task it
has not finished (0 false `complete`s on seed 30, 4 held-out). Its failures are almost all step-budget exhaustion.

### Cited Findings

**Method and definitions (computed).** Each failed episode gets one primary category, checked in this order:
- `infra_exception`: the harness raised an exception. It counts as a failure, as in the published scores.
- `partial_credit`: the checker gave a score between 0 and 1.
- Episodes the agent ended itself:
  - `false_complete`: an action task ended with `status: complete`, and the checker says it failed.
  - `completed_without_answer`: an answer task ended with `complete` instead of an answer.
  - `wrong_answer`: an `answer` action that the checker failed.
- Step budget exhausted (no terminal action), classified by the last 5 steps:
  - `stuck_wait`: all 5 steps are `wait`.
  - `stuck_same_intent`: the same intent text appears in all 5 steps, whatever the actions are.
  - `scroll_heavy`: at least 3 of the 5 steps are scrolls.
  - `repeat_loop`: the same action (taps on a 25-unit grid) at least 3 times in a row, making up at least 30% of the episode.
  - `wandering`: none of the above.

"No visible effect" means the mean absolute difference between the 72×160 grayscale versions of consecutive saved
thumbnails is below 1.0. This is the same measure that `train/agent_guards.py` uses, and it is a proxy.
GUI-Owl episodes store no intent text, so `stuck_same_intent` cannot be detected for GUI-Owl.
Sources: [eval/androidworld/failure_modes.py](../../../../eval/androidworld/failure_modes.py),
[train/agent_guards.py](../../../../train/agent_guards.py),
[data/meta/androidworld_task_metadata.json](../../../../data/meta/androidworld_task_metadata.json),
[results/codex/v3_audit/answer_tasks.json](../../../../results/codex/v3_audit/answer_tasks.json).

**Table 1: primary category per run, seed 30, 116 tasks (computed)**
Source: episode files in [results/androidworld/](../../../../results/androidworld/), latest `run_*` folder of each of
`lfm3vl2b_ft` (v1), `lfm3vl2b_v2`, `lfm3vl2b_v3`, `lfm3vl2b_v4`, `lfm3vl2b_v4_guards`, `lfm3vl2b_v41`, `lfm3vl2b_v41_guards`,
`lfm3vl2b_v42`, `lfm3vl2b_v42_guards` and `guiowl15_2b_matched`.

| Category | v1 | v2 | v3 | v4 | v4+g | v4.1 | v4.1+g | v4.2 | v4.2+g | GUI-Owl |
|---|---|---|---|---|---|---|---|---|---|---|
| **success** | 15 | 3 | 13 | 18 | 18 | 12 | 14 | 18 | 13 | 23 |
| false `complete` (action task) | 27 | 20 | 21 | 25 | 28 | 24 | 26 | 25 | 25 | **0** |
| `complete` instead of answer (answer task) | 18 | 16 | 17 | 0 | 0 | 4 | 2 | 0 | 0 | 0 |
| wrong answer | 0 | 1 | 0 | 14 | 16 | 14 | 11 | 11 | 12 | 1 |
| budget: stuck on same intent | 24 | 24 | 41 | 32 | 37 | 20 | 24 | 23 | 13 | n/a |
| budget: stuck on `wait` | 14 | 15 | 2 | 11 | 0 | 2 | 0 | 2 | 0 | 0 |
| budget: repeated identical action | 0 | 14 | 2 | 1 | 6 | 6 | 3 | 3 | 2 | 17 |
| budget: scroll-heavy | 1 | 7 | 0 | 0 | 1 | 0 | 2 | 1 | 0 | 12 |
| budget: wandering (no loop at the end) | 15 | 11 | 16 | 11 | 9 | 27 | 26 | 24 | 27 | 63 |
| infrastructure exception | 2 | 5 | 3 | 4 | 1 | 7 | 8 | 9 | 24 | 0 |
| partial credit | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Table 2: same categories, held-out seeds pooled, 348 episodes per arm (computed)**
Source: [results/androidworld_sealed/](../../../../results/androidworld_sealed/) (`v4_seed*`, `guiowl_seed*`,
`v1_seed*`, with each `_rerun` folder substituted for setup crashes).

| Category | v4 | GUI-Owl | v1 |
|---|---|---|---|
| success | 54 | 47 | 32 |
| false `complete` | **71** | 4 | 82 |
| `complete` instead of answer | 0 | 0 | 49 |
| wrong answer | **41** | 12 | 0 |
| budget: stuck on same intent | 79 | n/a | 83 |
| budget: stuck on `wait` | 49 | 0 | 44 |
| budget: repeated identical action | 1 | 63 | 0 |
| budget: scroll-heavy | 2 | 14 | 2 |
| budget: wandering | 44 | 206 | 55 |
| infrastructure exception | 6 | 1 | 0 |
| partial credit | 1 | 1 | 1 |

**Table 3: step-level behaviour, seed 30 (computed from the same episode files)**

| Metric | v1 | v3 | v4 | v4+g | v4.1 | v4.2 | v4.2+g | GUI-Owl |
|---|---|---|---|---|---|---|---|---|
| Steps (all 116 episodes) | 1,760 | 1,790 | 1,706 | 1,817 | 1,875 | 1,681 | 1,487 | 2,228 |
| `wait` share of steps | 33.3% | 24.7% | **29.1%** | 0% | 8.7% | 5.1% | 5.9% | 2.3% |
| `wait`s with no visible change | 518 | 331 | 413 | 0 | 100 | 61 | 64 | 0 |
| Steps whose intent copies the previous step's word for word | 51.6% | 51.6% | **56.3%** | 53.4% | 35.5% | 37.9% | 30.1% | n/a |
| Clicks with no visible effect (all clicks) | 23.8% | 20.9% | 41.9% | 52.7% | 42.3% | 48.2% | 25.1% | 16.4% |
| First click under a new intent with no effect: failed episodes / successful episodes | 12% / 4% | 14% / 9% | **25% / 4%** | 25% / 2% | 19% / 10% | 24% / 3% | — | — |
| Scroll share | 2.9% | 10.3% | 5.9% | 10.1% | 5.3% | 3.5% | 9.1% | 18.6% |
| Episodes that ran out of steps | 54 | 61 | 55 | 53 | 55 | 53 | 42 | 92 |
| Failed episodes with `open_app` names that android_world cannot launch | 16 | 14 | 0 | 0 | 0 | 0 | 0 | 0 |
| Model calls (guard re-asks included) | 1,760 | 1,790 | 1,706 | 2,435 | 1,875 | 1,681 | 1,577 | — |

- Held-out v4, pooled (computed):
  - 33.9% of 5,391 steps are `wait`.
  - 54.1% of steps copy the previous intent.
  - 35.0% of clicks have no visible effect.
  - 22% of first clicks under a new intent have no effect: 23% in failed episodes, 10% in successful ones.
- Held-out GUI-Owl: 2.1% `wait`, 26.4% of clicks with no effect.
- Held-out v1: 37.9% `wait`, 16% of new-intent clicks with no effect.
- PREREG_v41 reports v4's `wait` share as 35% / 37% on seeds 7 / 2026 —
  [docs/preregistrations/mobileworld-followup-waitrelabel.md](../../../../docs/preregistrations/mobileworld-followup-waitrelabel.md).

**Table 4: termination precision (successes ÷ episodes the agent ended itself with `complete` or `answer`) (computed)**

| Run | Ended by agent | Correct | Precision | `complete`: correct / used | `answer`: correct / used |
|---|---|---|---|---|---|
| v1 (seed 30) | 60 | 15 | 25% | 15 / 60 | — |
| v3 | 52 | 13 | 25% | 13 / 52 | — |
| v4 | 57 | 18 | 32% | 12 / 37 | 6 / 20 |
| v4+g | 62 | 18 | 29% | 13 / 41 | 5 / 21 |
| v4.1 | 54 | 12 | 22% | 8 / 36 | 4 / 18 |
| v4.2 | 54 | 18 | 33% | 13 / 38 | 5 / 16 |
| v4.2+g | 50 | 13 | 26% | 9 / 34 | 4 / 16 |
| **GUI-Owl (seed 30)** | 24 | 23 | **96%** | 13 / 13 | 10 / 11 |
| v4 held-out | 167 | 54 | 32% | 41 / 113 | 13 / 54 |
| GUI-Owl held-out | 64 | 47 | 73% | 28 / 33 | 19 / 31 |
| v1 held-out | 164 | 32 | 20% | 32 / 164 | — |

**False `complete` details (computed; v4 and v4.2 trajectories, seed 30)**
- **Ended before the human path could have finished** (fewer steps than the task's `optimal_steps`):
  - Seed 30: 10 of v4's 25 false completes, 8 of v4.2's 25.
  - Held-out v4: 26 of 71.
  - Examples from v4:
    - RecipeAddMultipleRecipesFromMarkor: ended at step 8 of 24.
    - ExpenseAddMultipleFromMarkor: 6 of 15.
    - SimpleSmsResend: 4 of 6.
    - MarkorMoveNote: 5 of 7.
- **Most other false completes come right after a "save", "delete", "confirm" or "OK" click** on a form with fields
  left out. For example, in ExpenseAddSingle v4 typed "Therapy Sessions", "307.01" and "I may repeat this" but never
  set the category, then saved and completed.
- **Verify-type toggle tasks:** SystemWifiTurnOffVerify and SystemBluetoothTurnOffVerify were completed right after
  tapping the toggle.
- Only 1 of v4's 25 false-complete episodes contains a wait run of 2 or more or a same-intent run of 3 or more.
  Premature stopping and looping are separate failure modes.

**Wrong-answer details (computed; v4 seed 30: 20 answers, 6 correct)**
- **v4 answers fast:** 10 of its 20 answered episodes ended within the task's `optimal_steps`. GUI-Owl did so in
  1 of 11.
- **Reading v4's 14 wrong answers** (inference from reading them):
  - About 6 report one visible item where the question needs a list or a total over several items:
    - SportsTrackerTotalDistanceForCategoryOverInterval: answered "8.73" from one entry.
    - SportsTrackerTotalDurationForCategoryThisWeek: answered "30".
    - TasksHighPriorityTasks: answered one task.
    - SimpleCalendarEventsInNextWeek: answered 2 visible events after 3 steps.
  - 2 answer "There are no tasks here." after a search returned an empty screen (TasksDueOnDate,
    TasksIncompleteTasksOnDate). GUI-Owl solved both by scrolling the list.
  - At least 1 looks like a format mismatch with the right content. SimpleCalendarNextMeetingWithPerson:
    - v4 answered "October 27, 2023 15:15".
    - v4.2 answered "October 27, Friday 15:15".
    - GUI-Owl's successful answer was "October 27 2023 15:15".
  - 1 answered with every event on the date instead of the one at the asked time (SimpleCalendarEventOnDateAtTime).
- **Answer usage, seed 30 (answered / correct):** v4 20 / 6, v4.1 18 / 4, v4.2 16 / 5, GUI-Owl 11 / 10.
- **Answer usage, held-out:** v4 answered 54 / 75 and got 13 right; GUI-Owl answered 31 / 75 and got 19 right.

**Loop details (computed from the last 6 steps of each stuck episode)**
- **v4 (seed 30) loops pair a click intent with clicks and waits.** Of 44 stuck episodes:
  - 19 alternate `click` and `wait` under one "Click on …" intent.
  - 9 are only waits under a "Click on …" intent.
  - 4 scroll under a "Scroll …" intent.
  - The thumbnail difference across these tails is mostly 0.0, so the screen does not change.
- **v4.2's loops are mostly repeated clicks.** Of 28 stuck episodes, 18 repeat the same `click` under one "Click on …"
  intent with no screen change. The waits became taps. Examples:
  - "Click on the time section" (SimpleCalendarAddOneEventTomorrow).
  - "Click on Wi-Fi Direct" (TurnOffWifiAndTurnOnBluetooth).
- **Share of steps spent in the final same-intent loop** (budget-exhausted episodes):
  - v4: 67% (868 / 1,303).
  - v4+g: 61%.
  - v4.1: 40%.
  - v4.2: 46%.
  - Held-out v4: 62% (2,589 / 4,149).

**Guards**
- **What fired, v4+g:**
  - G1 (wait guard): 547 times.
  - G2 (repeat guard): 71 times.
  - 34% more model calls than v4.
- **The waits disappeared, but the loops stayed:**
  - Repeated clicks with no effect: 492 of 535 (92%).
  - Failures with a ≥4-step same-intent run: 49, against 48 for v4.
  - Score: unchanged at 18.
- **Example, FilesDeleteFile under v4+g:** G1 replaced 17 consecutive `wait`s (steps 6–22) with the same click at
  (903, 195) under the same intent. Sources: `lfm3vl2b_v4_guards` episodes and
  [eval/androidworld/lfm_agent.py](../../../../eval/androidworld/lfm_agent.py). The guard prefills the model's own
  intent before asking again.

**Typing, scrolling and app opening (computed)**
- **Literal typing errors are rare.** Text that is not a substring of the goal appears in:
  - 5 of v4's failed episodes.
  - 2 of v4.2's.
  - Example: v4 typed the field label "1st name" in ContactsAddContact.
- **Form failures are omissions instead.** In ContactsNewContactDraft, v4.2 typed "Grace" and "Taylor" and never typed
  the phone number.
- **Scrolling rarely causes a failure.** At most 2 scroll-heavy endings per LFM3 run.
- **v4 scrolls less than its own training data and than GUI-Owl:** 5.9% of steps, against 11.2% of v2/v3 training rows
  and 18.6% of GUI-Owl's steps.
- **App-name failures were fixed by v4's installed-app list.**
  - v1 / v3: 16 / 14 failed episodes used names android_world cannot launch ("Marker", "Markers", "SimpleSMS").
  - v4 onward: 0.
  - Source: [results/androidworld/lfm3vl2b_v3.failure_modes.json](../../../../results/androidworld/lfm3vl2b_v3.failure_modes.json)
    and the recomputation.

**Infrastructure exceptions (computed from `exception_info`)**
- **Two causes dominate:**
  - gRPC log lines in adb output: "invalid literal for int()", "FD from fork".
  - App-data reset failures: "Failed to clear directory".
- v4.2+g: 20 of its 24 exceptions are "Could not get a11y tree".
- Held-out v4 seed 1234: 113 setup crashes were re-run under the preregistered rule.
- Sources: [docs/preregistrations/mobileworld-followup-waitrelabel.md](../../../../docs/preregistrations/mobileworld-followup-waitrelabel.md), [docs/results.md](../../../../docs/results.md).

### Inferences
- **False `complete` costs about a fifth to a quarter of all tasks, and no version changed it.**
  - Every LFM3 version has 20–28 false completes per 116 tasks.
  - The count did not move across v1→v4.2 or with guards.
  - (Inference from Tables 1 and 4.)
- **Looping and stopping early are different behaviours, so fixing one does not fix the other.**
  - Only 1 of 25 false-complete episodes contains a loop.
  - Loops and premature stops hit different tasks.
- **v4.1/v4.2 changed the loops' appearance (waits became repeated clicks), not their cause.**
  - The cause is that the model cannot recover when an action has no visible effect.
  - Loops shrank from 44 (v4) to 28 (v4.2) budget episodes, but "wandering" rose from 11 to 24.
  - Total budget exhaustion stayed at about 53–55.
- **Grounding misses are a likely trigger of loops.**
  - In failed episodes, about a quarter of the first clicks under a new intent change nothing on screen (25% for v4).
  - In successful episodes, almost none do (2–4%).
  - (Proxy: some clicks legitimately change nothing visible.)
- **GUI-Owl's advantage is restraint more than skill.**
  - It rarely ends a task it has not finished (96% / 73% precision).
  - It answers only after looking.
  - It still fails 92 of 116 by running out of steps.

### Gaps
- **Click accuracy cannot be scored directly.** No ground-truth targets exist for AndroidWorld steps. Grounding
  errors are only estimated from screen-change thumbnails (360×800 JPEG).
- **Typing correctness is only checked as "typed text appears in the goal".** The checker's own per-field reasons are
  not stored in the episode pickles.
- **The cause of each wrong answer cannot be confirmed.** The expected answers are not saved in the pickles. Only
  GUI-Owl's successful answers give a reference.
- **GUI-Owl's intents are not stored for AndroidWorld,** so its same-intent loops cannot be compared.

## 2. Paired per-task changes v4 → v4.1 → v4.2, and tasks only GUI-Owl solves

### Takeaway
On the same 116 seed-30 tasks:
- v4→v4.1 lost 8 tasks and gained 2.
- v4.1→v4.2 gained 9 and lost 3.
- v4 and v4.2 are level (+6 / −6).

None of these changes is significant (exact McNemar p = 0.11, 0.15, 1.0), and individual tasks flip often between runs.

GUI-Owl solves 7 seed-30 tasks that no LFM3 run ever solved:
- 3 Calendar or Contacts form tasks (missing skill or app knowledge, plus stopping early).
- 4 question tasks: 3 are answer behaviour (answered too early, without browsing, or in the wrong format) and 1 is a
  navigation loop that never reached an answer.

### Cited Findings
**Table 5: paired seed-30 changes (computed from the episode files in Section 1)**

| Pair | Both | Gained | Lost | Neither | Exact McNemar p |
|---|---|---|---|---|---|
| v4 → v4.1 | 10 | 2 | 8 | 96 | 0.11 |
| v4.1 → v4.2 | 9 | 9 | 3 | 95 | 0.15 |
| v4 → v4.2 | 12 | 6 | 6 | 92 | 1.0 |
| v4 → v4+g | 15 | 3 | 3 | 95 | 1.0 |
| v4.1 → v4.1+g | 8 | 6 | 4 | 98 | 0.75 |
| v4.2 → v4.2+g | 9 | 4 | 9 (5 of them infrastructure exceptions) | 94 | 0.27 |
| v1 → v4 | 9 | 9 | 6 | 92 | 0.61 |
| v3 → v4 | 8 | 10 | 5 | 93 | 0.30 |
| v4 vs GUI-Owl | 12 | GUI-Owl only 11 | v4 only 6 | 87 | 0.33 |
| v4.2 vs GUI-Owl | 9 | GUI-Owl only 14 | v4.2 only 9 | 84 | 0.41 |

**v4 → v4.1**
- Lost: 8 tasks, none of them exceptions.

  | Task | What v4.1 did |
  |---|---|
  | ExpenseDeleteSingle | false complete |
  | NotesRecipeIngredientCount | wandering |
  | OpenAppTaskEval | wandering |
  | SimpleCalendarAnyEventsOnDate | wrong answer |
  | SimpleCalendarDeleteOneEvent | false complete |
  | SimpleCalendarEventsOnDate | same-intent loop |
  | SimpleSmsReply | false complete |
  | SystemWifiTurnOff | false complete |

- Gained: NotesIsTodo, RecipeDeleteSingleWithRecipeWithNoise.

**v4.1 → v4.2**
- Gained 9:
  - CameraTakePhoto, CameraTakeVideo.
  - ExpenseDeleteMultiple, ExpenseDeleteSingle.
  - NotesRecipeIngredientCount.
  - OpenAppTaskEval.
  - SimpleSmsSend.
  - SystemWifiTurnOff.
  - TasksHighPriorityTasks.
- Lost 3:
  - NotesIsTodo (wandering).
  - SystemBluetoothTurnOff (false complete).
  - SystemBluetoothTurnOn (repeat loop).

**v4 → v4.2**
- Gained 6:
  - CameraTakePhoto, CameraTakeVideo.
  - ExpenseDeleteMultiple.
  - RecipeDeleteSingleWithRecipeWithNoise.
  - SimpleSmsSend.
  - TasksHighPriorityTasks.
- Lost 6:

  | Task | What v4.2 did |
  |---|---|
  | SimpleCalendarAnyEventsOnDate | same-intent loop |
  | SimpleCalendarDeleteOneEvent | stuck on wait |
  | SimpleCalendarEventsOnDate | same-intent loop |
  | SimpleSmsReply | exception |
  | SystemBluetoothTurnOff | false complete |
  | SystemBluetoothTurnOn | repeat loop |

- Calendar successes went from 4 (v4) to 1 (v4.1) and stayed at 1 (v4.2).

**Successes by app, seed 30 (computed)**

| App (tasks) | v1 | v3 | v4 | v4.1 | v4.2 | GUI-Owl |
|---|---|---|---|---|---|---|
| Simple Calendar (17) | 1 | 1 | 4 | 1 | 1 | 7 |
| System / Settings (16) | 8 | 6 | 7 | 5 | 5 | 4 |
| Markor (14) | 0 | 0 | 0 | 0 | 0 | 0 |
| Broccoli recipes (13) | 4 | 3 | 1 | 2 | 2 | 2 |
| Pro Expense (9) | 1 | 1 | 1 | 0 | 2 | 2 |
| Simple SMS (6) | 0 | 0 | 1 | 0 | 1 | 1 |
| OpenTracks (6) | 0 | 0 | 0 | 0 | 0 | 0 |
| Tasks (6) | 0 | 0 | 0 | 0 | 1 | 2 |
| Joplin notes (4) | 0 | 0 | 3 | 3 | 3 | 3 |
| Other 25 tasks | 1 | 2 | 1 | 1 | 3 | 2 |

**How stable are tasks across runs?**
- Across the six v4-family runs (v4, v4+g, v4.1, v4.1+g, v4.2, v4.2+g):
  - 86 tasks were never solved.
  - Only 3 were solved by all six: ClockStopWatchRunning, NotesTodoItemCount, RecipeDeleteSingleRecipe.
  - 27 were solved by 1–5 of the runs.
- Held-out v4 by template across the 3 seeds: 10 solved on 3/3 seeds, 7 on 2/3, 10 on 1/3.
- 72 of 116 seed-30 tasks were solved by no run at all (any LFM3 version or GUI-Owl).

**Tasks only GUI-Owl solved on seed 30: what v4 and v4.2 did (computed)**
- ContactsAddContact: both ended with a false complete after 12 steps (optimal 5). v4 typed the label "1st name".
- SimpleCalendarAddOneEvent (hard): false complete at steps 19 / 21 (optimal 17).
- SimpleCalendarAddOneEventRelativeDay: both stuck on one intent for 34 steps (optimal 17). The tail repeats a click
  on the time picker.
- SimpleCalendarEventsInTimeRange: both looped on "Click on the right arrow icon…" and never answered.
  GUI-Owl answered "Cooking Class" in 4 steps.
- SimpleCalendarNextMeetingWithPerson: a wrong answer in 4 steps with the right date and time. The format differs
  from GUI-Owl's successful answer (see Section 1).
- TasksDueOnDate and TasksIncompleteTasksOnDate: answered "There are no tasks here." (or an incorrect list) after
  searching, in 3–5 steps. GUI-Owl scrolled the list and answered in 4 steps.

**Held-out templates**
- GUI-Owl solved 17 templates on at least one seed that v4 never solved on any held-out seed.
- 8 of those were also never solved by any seed-30 LFM3 run:
  - RecipeDeleteMultipleRecipes.
  - SimpleCalendarEventsInTimeRange, SimpleCalendarNextMeetingWithPerson.
  - SimpleSmsResend, SimpleSmsSendClipboardContent, SimpleSmsSendReceivedAddress.
  - SystemBrightnessMin.
  - TasksDueNextWeek.
- v4 solved 16 templates that GUI-Owl never solved.
- Source: [results/androidworld_sealed/](../../../../results/androidworld_sealed/) (computed).

**Apps excluded from our training vs generic apps (computed).** 88 of the 116 tasks use one of the 14
AndroidWorld-specific apps whose episodes our training data drops ([docs/datasets.md](../../../../docs/datasets.md)).

| Arm | AndroidWorld-app tasks solved | Generic-app tasks solved (Settings, Clock, Camera, Contacts, Files, Chrome) |
|---|---|---|
| v4, seed 30 | 10 / 88 | 8 / 28 |
| v4.2, seed 30 | 10 / 88 | 8 / 28 |
| GUI-Owl, seed 30 | 18 / 88 | 5 / 28 |
| v4, held-out | 31 / 264 (11.7%) | 23 / 84 (27.4%) |
| GUI-Owl, held-out | 33 / 264 (12.5%) | 14 / 84 (16.7%) |

- Difficulty, held-out ([docs/results.md](../../../../docs/results.md)):

  | Arm | Easy (183) | Medium (108) | Hard (57) |
  |---|---|---|---|
  | v4 | 50 | 3 | 1 |
  | GUI-Owl | 33 | 11 | 3 |

### Inferences
- **The version-to-version differences on seed 30 are within run-to-run noise.**
  - Most solved tasks flip between runs.
  - The union of v4-family successes is 30 tasks, while each run solves 12–18.
  - Comparing versions on one 116-task seed cannot separate a ±3–6 task effect.
- **v4.1's specific loss pattern is consistent with a side effect of the wait relabel.** It lost 4 Calendar tasks and
  gained more false completes on simple tasks. This is unconfirmed: p = 0.11.
- **v4.2 recovered the loss.** Training on its own replayed history undid v4.1's damage, but did not go beyond v4.
- **What GUI-Owl solves and we never do is mostly behaviour:**
  - Browsing a list before answering.
  - Answer format.
  - Finishing multi-field forms, including date/time pickers.
  - No one LFM3 failure mode accounts for the gap.
- **Unfamiliar apps are harder for v4 than for GUI-Owl.**
  - v4 does 2.3× better on generic apps than on the AndroidWorld apps excluded from its training.
  - GUI-Owl's gap between the two groups is smaller.
  - This is consistent with an app-knowledge gap.
  - Confound: AndroidWorld-app tasks are also the longer, multi-field ones.

### Gaps
- Each variant has only one seed-30 run. True run-to-run variance at temperature 0 (emulator timing, device state
  carried between episodes) cannot be measured from local files. `lfm3vl2b_v4_rerun` holds only 2 episodes.
- v4.1 and v4.2 have no held-out runs, so their paired changes cannot be checked beyond seed 30.

## 3. MobileWorld: where v4 diverges from GUI-Owl on the same tasks

### Takeaway
- **v4 gets stuck early in MobileWorld and stays stuck.**
  - In 64 of its 83 failed 50-step episodes, the last 10 steps have the same intent.
  - The final loop starts at a median of step 6, wasting a median of 44 of 50 steps.
- **On the 16 tasks only GUI-Owl solved:**

  | Root cause | Tasks |
  |---|---|
  | Same-intent loop after a tap that did not progress | 8 |
  | Wrong app, or apps in the wrong order | 3 |
  | Finished without typing the reply | 2 |
  | Slider manipulation (no such skill) | 2 |
  | Searched instead of browsing | 1 |

- **The first divergence from GUI-Owl is usually a different tap target** (12 of 16).

### Cited Findings
Source: local, git-ignored trajectories in `results/mobileworld/traj_r2/v4_gui_en_r2/<task>/traj.json` and
`results/mobileworld/traj_r2/guiowl_gui_en_r2/<task>/traj.json` (last attempt key, `result.txt`), task list
[results/mobileworld/mw_gui_en.json](../../../../results/mobileworld/mw_gui_en.json), paired outcomes
[results/mobileworld/mw_r2_comparison.json](../../../../results/mobileworld/mw_r2_comparison.json) (computed).

**Table 6: MobileWorld behaviour (105 tasks; v4 has 104 trajectories, GUI-Owl 102 results)**

| Metric | v4 | GUI-Owl |
|---|---|---|
| Steps | 4,461 | 4,096 |
| `wait` share | 20.9% (931; every one under an intent that is not about waiting) | 0.5% |
| `navigate_back` share | 0.7% | **9.6%** |
| Scroll/drag share | 17.5% | 11.4% |
| Steps whose intent copies the previous step's word for word | 66.9% of steps | 21.9% |
| Tasks that hit 50 steps | 85 | 72 |
| Ended by the agent: correct / total | 4 / 19 (21%): 16 "finished", 3 answers | 15 / 30 (50%) |
| Successes at the step limit | 2 | 7 |
| Failed 50-step episodes whose last 10 steps share one intent | **64 of 83** (and 13 more with two) | 15 of 65 |
| Step where the final same-intent loop starts (median, p25–p75) | **6** (3–26) | 49 (47–49) |

- PREREG_v41 gives 73% intent repetition for v4 with its own counting rule, and 85 of 104 tasks at the limit —
  [docs/preregistrations/mobileworld-followup-waitrelabel.md](../../../../docs/preregistrations/mobileworld-followup-waitrelabel.md).

**First divergence (same step index, different action type, or taps more than 100 px apart).**
- All tasks with both trajectories:
  - Tap point: 54.
  - `open_app` vs GUI-Owl tapping the icon: 30 (a harmless difference in how apps are launched).
  - Other: 20.
- The 16 GUI-Owl-only tasks:
  - Tap point: 12.
  - `open_app` vs tap: 3.
  - `click` vs `navigate_home`: 1.

**GUI-Owl-only tasks read step by step (computed dump; categories are our reading)**
- **Same-intent loop after a tap that did not progress (8):**

  | Task | v4's repeated intent | What GUI-Owl did instead |
  |---|---|---|
  | MastodonChangeLanguageTask | "Click on the profile icon…" from step 4 to the limit | three-dot menu → settings → language |
  | MastodonNewPostTask | "Click on the three dots icon…" | compose button |
  | SetAlarmTask | "Click on the time section" | — |
  | MastodonRevisePollTask | "Click on the Brazil option." | — |
  | CheckDepartTimeTask | "Open the CoolHacks email." | — |
  | RequestCarpoolingTask | "Open the conversation with Math Club." | went home, opened Messages |
  | CheckConferenceAndSendSmsTask1 | "Click on the right arrow icon to navigate to the next month." | — |
  | MastodonRevisePhotoAltTask | waited under "Go to the Posts section" | — |

- **Wrong app, or apps in the wrong order (3):**
  - MastodonInviteTask: opened Mattermost instead of Mastodon.
  - MastodonChangeHeaderTask: opened Gallery first, then reported "finished".
  - CheckConferenceLocationTask: started in Maps instead of Mail.
- **Finished without typing the reply (2):** AcceptMeetingTask and CancelMeetingTask went reply → send →
  "finished" in 5 steps. The result says "Wrong body". GUI-Owl tapped the body field and typed the message.
- **Slider manipulation (2):** AdjustBrightnessMaximumTask and AdjustBrightnessMinimumTask kept clicking "Brightness
  level". GUI-Owl dragged the slider in its step 5.
- **Search instead of browsing (1):** ChangeWallpaperTask typed "Sunflowers" into search, then waited under "Type in
  Sunflowers." until the step limit.
  GUI-Owl opened the album and picked the photo.

### Inferences
- **MobileWorld shows the same three LFM3 failure modes as AndroidWorld, more strongly:**
  - Same-intent loops, which dominate.
  - Premature "finished".
  - App and plan errors.
- **The loops start very early** (median step 6). The 50-step budget is mostly spent in one repeated intent, so a
  larger step budget would not help v4.
- **GUI-Owl's recovery behaviour is visible in its actions.** It uses `navigate_back` on 9.6% of steps (v4: 0.7%) and
  changes intent until the end.
- **Slider and drag gestures are missing from our action space and training data** (see Section 5). The two
  brightness tasks fail by construction. Four AndroidWorld SystemBrightness tasks behave the same way (Section 1 loop
  tails).

### Gaps
- No v4.2 MobileWorld result exists locally yet (the run is in progress and was not touched).
- The categories for the 16 tasks come from reading the first divergence and the tail. Screenshots were not inspected,
  so "a tap that did not progress" vs "a mis-tap" is not resolved.
- Container logs for the v4 and GUI-Owl runs no longer exist ([docs/results.md](../../../../docs/results.md)), so
  emulator-side problems in those runs cannot be checked.

## 4. Training signals: under-training, overfitting, and which offline metrics track online success

### Takeaway
- **No overfitting is visible in the losses.**
  - v4's final train loss is 0.301 and its eval loss is 0.306.
  - Only 0.43 epoch was seen, with no repeated rows.
- **The flattening at step 1,250 is mostly the learning-rate schedule.** The LR is below 2e-5 after step 1,000 and
  reaches 0 at about 1,240.
  - Eval loss was still falling about 0.01 per 250 steps at 750→1,000.
  - That is a mild under-training signal.
- **No offline metric reliably predicts AndroidWorld success** across v1–v4.2:
  - AndroidControl step accuracy rose from 0.715 to 0.732 while online successes went 15 → 3 → 13 → 18 → 12 → 18.
  - The closed-loop failure modes (waits, intent copying, early `complete`) are invisible or mismeasured offline.

### Cited Findings
**Loss curves (computed from the training logs)**
- v4 training logs:
  - [results/v4_dev/hub/training_logs/log_history.json](../../../../results/v4_dev/hub/training_logs/log_history.json),
  - `train_log.jsonl`,
  - [run_config.json](../../../../results/v4_dev/hub/training_logs/run_config.json).
- v1–v3 and baselines: `results/training/*/log_history.json`, `train_log.jsonl`.
- Learning-rate schedule (all 2e-4 runs):

  | Step | 10 | 50 | 500 | 750 | 1,000 | 1,200 | 1,240 |
  |---|---|---|---|---|---|---|---|
  | LR | 4.7e-5 | 2.0e-4 | 1.37e-4 | 7.3e-5 | 2.0e-5 | 9e-7 | 0 |

**Table 7: loss by training step (computed)**

| Run | Train loss, steps 1–100 | 450–550 | 700–800 | 950–1,050 | 1,150–1,240 | Eval loss at 250 / 500 / 750 / 1,000 / 1,250 | Final train (last 50 steps) vs eval |
|---|---|---|---|---|---|---|---|
| LFM3 v1 | 0.730 | — | 0.296 | 0.277 | 0.285 | — / — / 0.309 / 0.290 / 0.288 | 0.288 vs 0.288 |
| LFM3 v2 | 0.832 | 0.376 | 0.354 | 0.333 | 0.340 | 0.376 / 0.335 / 0.316 / 0.303 / 0.299 | 0.336 vs 0.299 |
| LFM3 v3 | 0.803 | 0.375 | 0.348 | 0.330 | 0.321 | 0.364 / 0.338 / 0.317 / 0.302 / 0.300 | 0.316 vs 0.300 |
| **LFM3 v4** | 0.818 | 0.366 | 0.342 | 0.317 | 0.304 | 0.364 / 0.343 / 0.318 / 0.309 / **0.306** | 0.301 vs 0.306 |
| Qwen3.5-2B v1 | 0.467 | 0.281 | 0.249 | 0.228 | 0.235 | 0.313 / 0.289 / 0.262 / 0.244 / 0.240 | 0.238 vs 0.240 |
| Qwen3.5-0.8B (1 epoch, 1,875 steps, lr 1e-4, r16) | 0.671 | 0.407 | 0.393 | 0.401 | 0.380 | … 0.283 at 1,250 → 0.278 / 0.276 / 0.276 at 1,500 / 1,750 / 1,875 | 0.382 vs 0.276 |
| LFM2.5-VL-450M (same recipe as 0.8B) | 1.048 | 0.495 | 0.471 | 0.479 | 0.464 | … 0.384 at 1,250 → 0.375 at 1,875 | 0.469 vs 0.375 |

- **Fraction of the data seen:**
  - v4: 0.434 epoch (40,000 of 92,229 rows) —
    [results/v4_dev/hub/training_logs/train_summary.json](../../../../results/v4_dev/hub/training_logs/train_summary.json).
  - v2 / v3: about 0.51 epoch.
- **The eval set is the AndroidControl validation split in the v1 prompt format** (`experimentalmachines/AndroidControl-screen-agent-sft@val`,
  827 rows; [results/data/dataset_verification.json](../../../../results/data/dataset_verification.json)).
  This holds for every run, including v4, whose training prompt is the v4 format.
- **No v4.1 or v4.2 loss curves are stored locally.** Their Colab job logs contain only heartbeats
  ([logs/v41_jobs_cell_lfm3_v41_a100.log](../../../../logs/v41_jobs_cell_lfm3_v41_a100.log),
  [logs/v41_jobs_cell_lfm3_v41_evals_v42_a100.log](../../../../logs/v41_jobs_cell_lfm3_v41_evals_v42_a100.log)).

**Table 8: offline metrics vs online successes**
Sources:
- [results/androidcontrol/lfm3vl2b-ac-lora_ft.metrics.json](../../../../results/androidcontrol/lfm3vl2b-ac-lora_ft.metrics.json) (v1),
  `lfm3vl2b-v2mix-lora_ft.metrics.json`, `lfm3vl2b-v3mix-lora_ft.metrics.json`.
- [results/v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft.metrics.json](../../../../results/v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft.metrics.json).
- [results/v41_dev/lfm3vl2b-v41-lora_ft.metrics.json](../../../../results/v41_dev/lfm3vl2b-v41-lora_ft.metrics.json),
  [results/v42_dev/lfm3vl2b-v42-lora_ft.metrics.json](../../../../results/v42_dev/lfm3vl2b-v42-lora_ft.metrics.json).
- Dev splits `results/v4{,1,2}_dev/*_dev_*.metrics.json`.
- MMStar from [docs/preregistrations/mobileworld-followup-waitrelabel.md](../../../../docs/preregistrations/mobileworld-followup-waitrelabel.md) and [docs/results.md](../../../../docs/results.md).

| Version | AndroidWorld seed 30 | AndroidControl high-level step accuracy | Low-level | Terminal `complete` | Episode accuracy | `wait` step accuracy | `open_app` step accuracy | dev_answer | dev_complete | MMStar |
|---|---|---|---|---|---|---|---|---|---|---|
| v1 | 15 | 0.715 | 0.948 | 0.792 | 0.283 | 0.596 | 0.816 | — | — | 57.1 |
| v2 | 3 | 0.716 | 0.893 | 0.732 | 0.281 | 0.570 | 0.789 | — | — | 54.6 |
| v3 | 13 | 0.723 | 0.902 | 0.725 | 0.287 | 0.593 | 0.817 | — | — | 55.3 |
| v4 | 18 | 0.728 | 0.908 | 0.716 | 0.290 | 0.594 | 0.926 | 0.890 | 0.762 | 52.9 |
| v4.1 | 12 | 0.732 | 0.895 | 0.739 | 0.291 | 0.589 | 0.933 | 0.882 | 0.850 | 55.6 |
| v4.2 | 18 | 0.732 | 0.888 | 0.738 | 0.303 | 0.591 | 0.946 | 0.868 | 0.812 | 55.7 |

- **Rank correlation with online successes (Spearman, n = 6, computed; with n = 6 none of these is reliable):**

  | Offline metric | ρ |
  |---|---|
  | `wait` step accuracy | 0.67 |
  | AndroidControl episode accuracy | 0.55 |
  | `open_app` step accuracy | 0.55 |
  | click step accuracy | 0.37 |
  | high-level step accuracy | 0.28 |
  | low-level step accuracy | 0.20 |
  | MMStar | 0.14 |
  | scroll step accuracy | −0.12 |
  | terminal `complete` | −0.17 |
  | eval loss (v1–v4 only) | −0.4 |

- **v4.1 looked better than v4 offline and did worse online.**
  - dev_complete: 0.850 vs v4's 0.762.
  - AndroidControl high-level accuracy: 0.732 vs 0.728.
  - Online seed 30: 12 vs 18 — [docs/preregistrations/mobileworld-followup-waitrelabel.md](../../../../docs/preregistrations/mobileworld-followup-waitrelabel.md).

**What offline evaluation shows vs closed-loop behaviour (computed from the per-step AndroidControl test predictions
in `results/androidcontrol/lfm3vl2b-v{2,3}mix-lora_ft.jsonl` and `results/v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft.jsonl`)**
- **`wait` is calibrated offline and over-produced online.**
  - Offline, v4 predicts `wait` on 579 of 8,444 high-level steps; the ground truth has 567 (6.9% vs 6.7%).
  - Only 242 (3.1%) are `wait` where the human did something else.
  - Online, `wait` is 29.1% of steps (AndroidWorld) and 20.9% (MobileWorld).
- **Premature `status` already shows up offline, with the human history supplied (teacher-forced):**

  | Model | `status` on non-terminal steps | AndroidControl test episodes with ≥1 premature `status` |
  |---|---|---|
  | v4 | 391 of 8,444 (4.6%) | 309 of 1,543 (20.0%) |
  | v3 | 4.6% | 19.3% |
  | v2 | 5.0% | 21.0% |
  | Qwen3.5-2B v1 | 5.5% | 20.9% |

- **Most common v4 confusions on AndroidControl test (true → predicted):**

  | True | Predicted | Count |
  |---|---|---|
  | status | scroll | 219 |
  | click | wait | 183 |
  | scroll | click | 172 |
  | click | scroll | 156 |
  | scroll | status | 154 |
  | click | status | 152 |

### Inferences
- **Under-training: weak evidence only.**
  - Loss was still falling when the cosine schedule ended, and only 43% of the rows were seen once.
  - The two 1-epoch baselines kept lowering eval loss past step 1,250 (by 0.007–0.009).
  - Training longer would probably lower loss a little.
  - The gain in AndroidWorld success is unknown: eval loss and step accuracy barely track online success (Table 8).
- **Overfitting: no train–eval gap, but behaviour overfits.**
  - The model copies AndroidControl's habits in closed loop: copying the previous intent, `wait` after a tap, and
    `complete` after "save".
  - More steps on the same data would not obviously remove these.
  - (Inference from Section 1, Table 3, and the confusion counts.)
- **The premature-`status` rate has stayed at about 5% per step in every version and base model** (Qwen too). The
  termination signal in the SFT data has never been changed.
  - Rough independence estimate: a 10-step task gives about a 1 − 0.954¹⁰ ≈ 37% chance of at least one early `status`.
  - That is the same order as the 20–28 false completes per 116 tasks.
  - Labelled inference: steps are not independent, and the policy only acts on `status` once.
- **Better development metrics:**
  - Closed-loop measures: termination precision, `wait` share, the intent-copy rate, and loop onset.
  - Offline: premature-`status` rate on non-terminal steps.
  - AndroidControl step accuracy alone should not be used.

### Gaps
- No v4.1/v4.2 training losses are stored locally, so their curves cannot be compared with v4's.
- No v1 LFM3 AndroidControl prediction file is stored (`lfm3vl2b-ac-lora_ft.jsonl` is absent), so v1's
  premature-`status` rate cannot be computed.
- v4.1/v4.2 AndroidControl test predictions are not local (only manifests), so the offline premature-`status` and
  `wait` confusions cannot be computed for them.
- No run trained beyond 1,250 steps on LFM3-VL-2B, so the effect of training amount on online success is untested
  locally.

## 5. Data signals: training-data action mix vs what fails online; v4.2 self-history

### Takeaway
- **The training mix teaches stopping only from AndroidControl's single synthetic `complete` step per episode,** with
  no "looks done but isn't" negatives.
- **It contains:**
  - no slider or drag gestures (they were truncated out);
  - only 12 `keyboard_enter` rows and 169 `long_press` rows;
  - `wait` targets that copy the previous intent (94%).
- **v4.2's self-replay shows exposure bias offline.** Under its own history, v4.1's rate of copying the previous
  intent rises from 1.4% at step 1 to 24% at step 9. Only 128 rows ended up showing the model one of its own mistakes.

### Cited Findings
**Table 9: action mix, training data vs online (training counts: [results/data/dataset_verification.json](../../../../results/data/dataset_verification.json)
for v1; [results/data_v2/stats.json](../../../../results/data_v2/stats.json) `full_dataset_assertions` for v2/v3; online computed)**

| Action | v1 train (99,216 rows) | v2/v3 train (78,982) | v4 online, AndroidWorld seed 30 | GUI-Owl online |
|---|---|---|---|---|
| click | 53.6% | 53.9% | 48.1% | 67.5% |
| scroll | 11.4% | 11.2% | 5.9% | 18.6% |
| status (complete/infeasible) | 13.7% | 7.6% | 2.2% | 0.6% |
| answer | 0 | 7.6% (ScreenQA) | 1.2% | 0.5% |
| input_text | 6.2% | 7.4% | 4.7% | 9.2% |
| wait | 6.0% | 4.4% | **29.1%** | 2.3% |
| open_app | 5.8% | 4.3% | 8.4% | 0 (taps icons) |
| navigate_back | 3.1% | 2.3% | 0.5% | 0.8% |
| navigate_home | 0.03% | 1.1% | 0 | 0.4% |
| long_press | 0.18% | 0.21% | 0 | 0.2% |
| keyboard_enter | 0 | 12 rows | 0 | — |

**v4's data by source** ([results/v42/v41_data_manifest.json](../../../../results/v42/v41_data_manifest.json)):

| Source | Rows |
|---|---|
| AndroidControl | 69,213 (v2/v3: 55,936; the difference is the v4 navigate-then-answer rows) |
| GUI-Odyssey | 9,972 |
| AMEX | 7,049 |
| ScreenQA | 5,995 |

**Termination supervision comes from AndroidControl only.** GUI-Odyssey's 3,244 and AMEX's 1,714 "complete" markers
were dropped as unreliable ([results/data_v2/stats.json](../../../../results/data_v2/stats.json) `truncate_at_COMPLETE`;
[docs/datasets.md](../../../../docs/datasets.md)). AndroidControl adds one synthetic `complete` per episode.

**Gestures were removed from training.** Swipes that are not a centre-line page scroll end the training episode:
- AMEX: `truncate_at_SWIPE` 975.
- GUI-Odyssey: `truncate_at_SCROLL` 1,417, plus `truncate_scroll_not_a_page_scroll` 126.
- Sources: [results/data_v2/stats.json](../../../../results/data_v2/stats.json), [docs/datasets.md](../../../../docs/datasets.md).
- The action space has no drag or slider action ([docs/models.md](../../../../docs/models.md)).

**`wait` supervision copies intents.** 4,151 AndroidControl rows are `wait`; 3,918 (94%) repeat the previous step's
intent. Only 12 `keyboard_enter` rows exist — [docs/preregistrations/mobileworld-followup-waitrelabel.md](../../../../docs/preregistrations/mobileworld-followup-waitrelabel.md).

**v4.1's data edits** ([results/v42/v41_data_manifest.json](../../../../results/v42/v41_data_manifest.json)):

| Edit | Count |
|---|---|
| `wait` targets relabelled | 4,104 |
| `wait` lines relabelled in history | 13,145 (in 10,982 rows) |
| Rows given an extra repeated step in history (once / twice) | 1,350 / 1,320 |
| Rows given an extra `wait` in history | 2,574 |

**v4.2's self-history** ([results/v42/selfhist_stats.json](../../../../results/v42/selfhist_stats.json); field
definitions in [data/v42_selfhist.py](../../../../data/sft_ownhistory.py)):
- **Replay coverage:** 6,922 episodes replayed (40% of eligible); 21,147 steps generated.
- **Replay accuracy:**
  - v4.1 matched the human action on 14,769 steps (69.8%).
  - It predicted `wait` on 696 (3.3%).
  - It copied the previous intent on 1,764 (8.3%).
  - 3 replies could not be parsed.
- **Copying the previous intent rises with depth in the episode:**

  | Replay round | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
  |---|---|---|---|---|---|---|---|---|---|
  | Copy rate | 1.4% (98 / 6,922) | 7.1% | 11.9% | 13.1% | 14.3% | 16.1% | 17.6% | 19.0% | 24.1% (65 / 270) |

- **Predicted `wait` by depth:** 1.3% at round 0, 3.3–6.0% at rounds 1–6.
- **What was patched into training:**
  - 24,001 of 92,229 rows (26%) got new history.
  - 6,378 wrong steps were replaced with the human step.
  - Only 128 rows show the model's own `wait` mistake.

### Inferences
- **The two biggest failure modes have no corrective signal in the data.** False `complete` and loops after a tap with
  no effect both lack it:
  - Termination is learned from one positive example per episode, and none of the "done-looking but not done" kind.
  - Recovery after a tap that changed nothing (`navigate_back`, choosing a different target) is rare in the data
    (2–3% back actions) and rarer still online (0.5–0.7%).
- **The v4.2 replay confirms exposure bias offline.** The intent-copy rate grows with depth under self-generated
  history, which is the AndroidWorld/MobileWorld loop signature. Yet v4.2 replaced wrong steps with human steps and
  showed only 128 own mistakes. Most rows still never show "my last action failed; now do something different".
  This is consistent with loops shrinking only modestly (Section 1).
- **Some skills are missing by construction:** slider drag, date/time pickers, long-press menus. These need new data
  sources or new action types, not more steps on the current mix.

### Gaps
- v4's exact training action mix (with the 13,277 navigate-then-answer rows) is not stored locally; only v1 and v2/v3
  counts are.
- The datasets themselves were not downloaded, as instructed. Per-app and per-screen coverage (for example, any
  date-picker screens) cannot be measured locally.
- v4.2's self-history is stored only as decisions (`selfhist_state.json.gz`). Which rows received own-mistake history
  for non-`wait` errors was not analysed.

## 6. Latency: where step time goes, and what 20–40 extra output tokens would cost

### Takeaway
- **Step time is dominated by reading the prompt** (mostly image tokens), not by generating the reply:
  - Apple M5, inside the runs: prompt 70–75% of model time.
  - CPU: about 90%.
  - Phone: 98%.
- **v4 writes a median of 22 output tokens; GUI-Owl writes 47.**
- **Cost of 20–40 extra output tokens per step:**

  | Device | Extra seconds per step | Share of step time |
  |---|---|---|
  | Phone | +0.4–1.0 s | +1–3% |
  | CPU | +0.5–0.9 s | +7–14% |
  | M5 GPU | +0.3–1.1 s | +15–44% |

### Cited Findings
**Table 10: Apple M5 per-step timing inside the seed-30 runs (computed from each episode's llama.cpp `timings`; two
emulators and two servers shared the machine, so speeds are not controlled)**

| Run | Prompt time (median) | Uncached prompt tokens | Output time (median) | Output tokens p10 / p50 / p90 | ms per output token | Output share of model time (pooled) | Step time, median (p90) | +20 / +40 tokens |
|---|---|---|---|---|---|---|---|---|
| v4 | 2,112 ms | 1,196 | 630 ms | 13 / 22 / 30 | 28.0 | 26.7% | 2.96 s (4.63) | +0.56 s (+19%) / +1.12 s (+38%) |
| v4.1 | 1,322 ms | 1,211 | 493 ms | 17 / 23 / 30 | 20.3 | 29.5% | 2.02 s (3.03) | +0.41 s (+20%) / +0.81 s (+40%) |
| v4.2 | 1,289 ms | 1,192 | 510 ms | 18 / 23 / 31 | 22.0 | 30.3% | 2.00 s (3.13) | +0.44 s (+22%) / +0.88 s (+44%) |
| v4+g | 894 ms | 1,190 | 290 ms | 13 / 22 / 30 | 12.9 | 25.5% | 1.67 s (2.97) | +0.26 s (+15%) / +0.52 s (+31%) |
| GUI-Owl | 4,755 ms | 1,009 (+1,097 cached) | 1,885 ms | 43 / 47 / 65 | 38.7 | 29.1% | 7.00 s (10.40) | +0.77 s (+11%) / +1.55 s (+22%) |

- Sources: the episode files named in Section 1; medians agree with
  [results/androidworld/dev_seed30_summary.md](../../../../results/androidworld/dev_seed30_summary.md) (v4 2.96 s,
  1,303 prompt tokens, 22 output; GUI-Owl 7.0 s, 2,106, 47).
- **A sample v4.2 server log line:** prompt 1,346 ms for 1,133 tokens (842 tok/s); output 497 ms for 22 tokens
  (42 tok/s) — [logs/llama_server_lfm3vl2b_v42.log](../../../../logs/llama_server_lfm3vl2b_v42.log).
- **CPU (Xeon, 8 threads), v4** — [results/speed/speed_t8.md](../../../../results/speed/speed_t8.md):
  - 6.4 s per step.
  - Prompt: 5.59 s for 803 tokens (149 tok/s).
  - Output: 0.64 s for 28 tokens (43.4 tok/s).
  - Computed: +20 / +40 tokens ≈ +0.46 / +0.92 s (+7% / +14%).
- **Phone (Snapdragon 8 Elite Gen 6 CPU, 4 threads)** — [results/qdc/speed_qdc_v6.md](../../../../results/qdc/speed_qdc_v6.md):

  | Clock | Step time | Prompt | Output speed | +20 / +40 tokens (computed) |
  |---|---|---|---|---|
  | 2.65 GHz | 39.2 s | 36.2 s for 1,081 tokens | 28 tokens at 41 tok/s | ≈ +0.49 / +0.98 s (+1.2% / +2.5%) |
  | 4.03 GHz | 27.7 s | 25.0 s | 50 tok/s | ≈ +0.4 / +0.8 s (+1.4% / +2.9%) |

- **Extra model calls (computed):**
  - Guards added 34% more calls for v4+g (2,435 calls / 1,817 steps).
  - v4.1+g: 5% more (1,858 / 1,771). v4.2+g: 6% more (1,577 / 1,487).
  - No LFM3 run had a first-attempt parse failure on seed 30.

### Inferences
- **On the target device (phone CPU), a longer reply is almost free:**
  - The image prompt costs about 25–36 s per step.
  - 20–40 extra tokens of reasoning (for example a "did my last action work?" check, or "is the goal really done?"
    before `complete`) would add about 1–3%.
- **On the M5 GPU, the extra tokens cost up to 44% of a step,** because prompt processing there is fast.
- **GUI-Owl's speed handicap is its larger prompt, not its longer replies** (47 vs 22 tokens).
- **Re-asking on every loop (guards) multiplies prompt cost:** each re-ask repeats the full image prompt.
  Self-checking text in one reply is cheaper than a second call.

### Gaps
- The M5 timings were taken with two emulators and two servers running, so the per-token speed varies 2× between
  runs (12.9–28 ms). No controlled M5 benchmark is stored.
- Image-encoding time is not logged separately in the llama-server logs checked. It is presumably inside the prompt
  time.
- The phone figures cover 2–15 calls per setting.

## 7. The most important problems, ranked by tasks lost, and the kind of fix each needs

### Takeaway
Ranked by held-out v4 failures (294 of 348 episodes):
1. Loops after an action that has no effect: about 44%.
2. False `complete`: about 24%.
3. Wandering without progress in unfamiliar apps: about 15%.
4. Wrong or early answers: about 14%.

Grounding misses and missing gesture skills cut across 1 and 3. The wait relabel (v4.1) and own-history replay
(v4.2) changed how the loops look, not the success count. Termination has never been targeted.

### Cited Findings
| # | Problem | Held-out v4 episodes lost (of 348) | Seed-30 v4 / v4.2 | MobileWorld v4 (99 failures) | Evidence (sections above) |
|---|---|---|---|---|---|
| 1 | Loops: same intent, `wait` or repeated tap after an action with no effect, until the budget runs out | 129 (79 same-intent + 49 `wait` + 1 repeat) | 44 / 28 | 77 (64 same intent + 13 two intents over the last 10 steps) | Tables 1–3, 6; median loop onset step 6 in MobileWorld; 92% of repeated taps change nothing |
| 2 | False `complete` (stopping early or not checking) | 71 | 25 / 25 | 12 "finished" + 3 answers ended by the agent | Tables 1, 2, 4; precision 32% vs GUI-Owl 73–96%; 4.6% premature `status` offline |
| 3 | Wandering: budget runs out without a stable loop (navigation or app knowledge) | 44 | 11 / 24 | 6 varied | Table 1; Markor 0/14 and OpenTracks 0/6 for every LFM3 run; v4 11.7% vs 27.4% on AndroidWorld vs generic apps (held-out) |
| 4 | Wrong answers (answered too early, one screen only, no totals, format) | 41 | 14 / 11 | 3 | Section 1; 24% answer precision held-out (GUI-Owl 61%) |
| 5 | Grounding misses (a tap that changes nothing) | cross-cutting (triggers #1) | 25% / 24% of first taps under a new intent in failed episodes (2–4% in successes) | 12/16 GUI-Owl-only tasks first diverge at a tap point | Table 3; Section 3 |
| 6 | Missing skills: sliders/drag, date/time pickers, multi-field forms, multi-app plans | ≥ 9 seed-30 templates (SystemBrightness ×4: none solved by any v4-family run, 2 once by v1/v3; SimpleCalendarAdd* ×5: none solved by any LFM3 run, with picker or arrow loops) | — | 2 brightness, 3 multi-app plan, 2 reply-body | Sections 1, 3, 5 |
| 7 | Infrastructure exceptions | 6 (after 113 re-runs) | 4 / 9 (v4.2+g: 24) | 1 without a result | Section 1 |
| 8 | `wait` over-production (v4: 29% of steps; 88% of waits on a static screen) | mostly inside #1 | 497 / 86 waits | 931 waits | Table 3; fixed in form by v4.1/v4.2 without a score gain |

### Inferences
| # | Kind of fix | Why |
|---|---|---|
| 1 | **Own-attempt learning, plus data** | The model must see its own no-effect action followed by a different action (back, another target, scroll). Approaches: (a) rollouts or replays that keep the model's own failed step in history and label a recovery; (b) on-policy correction (DAgger-style); (c) a "previous action had no effect" cue that the model is trained on. Fixes that did not help: v4.2 kept the human step at wrong steps and showed 128 own mistakes; guards kept the stuck intent; the untrained runtime feedback ablation ("[no visible change]" notes plus app-name resolution) made v1 worse (15 → 10, with 7 exceptions; [docs/models.md](../../../../docs/models.md)). |
| 2 | **Data plus own-attempt learning, possibly harness** | Add terminal negatives ("done-looking but not done") and a short verify step before `complete`. Label the model's own premature completes from rollouts as wrong (DPO/RL on termination). The per-step premature rate has not changed since v2 (about 5%), so more steps of the same data are unlikely to fix it. |
| 3 | **Data (app and navigation diversity, longer episodes); training amount unknown** | GUI-Owl's edge is concentrated on AndroidWorld apps (seed 30). Our training drops those apps by design, so the fix must come from similar apps or synthetic exploration that does not touch AndroidWorld. Whether more training steps help is untested (Section 4). |
| 4 | **Data** | Multi-screen information-seeking episodes that scroll or filter before answering, with totals across items and the goal's requested format. Possibly own-attempt learning on answer timing. |
| 5 | **Unknown / data** | No ground truth exists to separate a mis-tap from a correct tap on an inactive element. A grounding-focused eval on the failed screens is needed before choosing data. |
| 6 | **Data plus action space** | Add drag/slider and picker interactions; stop truncating non-page swipes. |
| 7 | **Harness** | The adb gRPC log lines, app-data reset and a11y-tree failures are environment-side, not model-side. |
| 8 | **Mostly addressed** | v4.1/v4.2 relabelling took `wait` from 29% to 5% of steps. The underlying loop (#1) remains. |

- **More SFT steps on the current mix alone would probably not fix the top problems** (inference).
  - Problems 1, 2 and 4 are closed-loop behaviours that offline loss and step accuracy do not measure (Section 4).
  - Their training signal is absent rather than under-fitted.
- **Training amount is the right lever mainly for problems 3 and 5,** and even there its effect is unmeasured.

### Gaps
- The cost estimates are mutually exclusive primary categories. They are not a causal decomposition:
  - Fixing #2 would turn some false completes into loops or wandering, not into successes.
  - GUI-Owl never stops early and still fails 79% of seed-30 tasks by running out of steps.
- No experiment isolates training amount, so the "training amount" column stays "unknown" for every problem.
- The ranking uses held-out v4 (348 episodes). v4.1/v4.2 have only one 116-task run each, so whether their category
  mix differs is within noise.
