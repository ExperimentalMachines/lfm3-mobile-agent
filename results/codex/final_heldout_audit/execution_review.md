**Execution and identity evidence**

This is an offline artifact review. Times below are host times in Asia/Manila. No evaluator, emulator, model server or adb command was run, and no process was signalled.

The original preregistration commit is `29d5d25`, 2026-11-18 01:29:42 +08:00, before the first v1 server-ready line at 01:30:13. Everything before the Deviations section is byte-identical to that commit (`prereg_provenance.json`); approximate times in the prose headings should not replace commit/log chronology. Seed-30 episode reconstruction gives v4 18 successes (6 answer, 12 action), v3 13 (all action), v1 15 and matched GUI-Owl 23. The saved development reruns add no success (`development_counts.json`). The v4 AndroidWorld gate therefore passes as described, before its held-out run; seed 30 is never part of the final primary count.

**Eligibility and exactly one rerun**

All 122 substituted originals have an outermost `_run_task -> initialize_task` exception: 117 from the new seeds, plus the previously disclosed five from seed 7. `exceptions.json` preserves every traceback; `rerun_identity.json` maps every original to its replacement. The six rerun logs each have exactly one timestamped `Running task:` enumeration and one `Wrote task episodes` record for every requested template, with no duplicate writes. Both guard logs contain only startup and normal watcher exit; neither records an intervention or restart. See `execution_logs.json` for line numbers and timestamps.

| Original | Evidence / phase | Rerun outcome |
|---|---|---|
| v4 / 1234, 113 templates | `initialize_task -> initialize_device_time`; emulator-5558 `settings put global auto_time` timeouts, 00:37:15–08:06:35. No model step reached. | 113 reruns on 5556, 13:24:46–16:07:49: 17 successes, 92 ordinary failures, four exceptions. |
| GUI-Owl / 1234, RecipeDeleteSingleRecipe | Setup DB push cannot clear Broccoli databases, verified nonempty; 20:57:27–20:57:37 Nov 18. | Ordinary failure. |
| GUI-Owl / 2026, NotesTodoItemCount | Setup fails listing device DB directory, before model execution; 01:48:14–01:48:18. | Success, reviewed as #62. |
| GUI-Owl / 2026, SimpleSmsSendReceivedAddress | Setup `get_android_time` cannot parse adb output polluted by gRPC stderr; 04:13:23–04:13:24. | Ordinary failure. |
| v1 / 2026, SimpleSmsSendClipboardContent | Same setup time-parser failure; 12:44:45–12:44:46. | Ordinary failure. |
| v4 / 1234, BrowserDraw | `run_episode -> agent.step -> get_post_transition_state`; successful screen fetches at 00:33:57, 00:34:02, 00:34:09 before the hang. | No rerun; correctly a failure. |
| v4 / 2026, SimpleSmsReplyMostRecent | Outermost `is_successful -> get_android_time`, 07:05:05; adb stderr pollution. | No rerun; correctly a failure. |
| GUI-Owl / 1234, SimpleSmsSendReceivedAddress | Outermost `is_successful -> get_android_time`, Nov 18 23:08:03. | No rerun; correctly a failure. |

The four v4/1234 rerun exceptions are NotesTodoItemCount (setup DB push), SimpleSmsReplyMostRecent (setup time parsing), and both VLC tasks (`episode_runner.py:76 -> agent.reset`, **before step 1**). All four exhaust their single allowed rerun. The 16:20 entry's “in an agent step” description of VLC is wrong, but its failure scores are correct. An outer `run_episode` frame alone does not establish that a model step occurred.

One further logged teardown exception occurs on the failed v4/1234 rerun NotesIsTodo (`aux_data`, failed Joplin DB directory clear). It does not change a success to failure because the task already failed. Later Joplin tasks perform their own initialization/DB clearing; no additional success contradiction was established. This is included in the inventory rather than silently treated as an `exception_info` episode.

**Every episode overlapping emulator 2's midnight–10:05 window**

There are 124 saved episodes, exhaustively enumerated in `emulator2_overnight_episodes.json`:

| Work on emulator 5558 | Time | Result relevant to hang |
|---|---|---|
| GUI-Owl / 1234: TurnOnWifiAndOpenApp, VlcCreatePlaylist, VlcCreateTwoPlaylists | 23:58:16–00:20:21 | 20/28/48 steps; ordinary failures, no exception. Includes the task straddling midnight. |
| v4 / 7: four reruns | 00:21:22–00:27:11 | No exceptions; maximum screen-fetch time 3.4 s. |
| GUI-Owl / 7: SimpleSmsResend rerun | 00:27:42–00:30:07 | Success; no exception; maximum fetch 2.6 s. |
| v4 / 1234: both AudioRecorder tasks | 00:30:34–00:33:49 | Responsive screens, 12/20 steps, model waits; ordinary failures. |
| v4 / 1234: BrowserDraw | 00:33:53–00:37:15 | Hang after first steps; counted failure. |
| v4 / 1234: remaining 113 | 00:37:15–08:06:35 | Setup crashes; eligible. |
| v1 / 2026 environment launch | 08:06–08:18 | Zero tasks enumerated and zero checkpoints written; no episode to count or consume a task rerun. |

The two AudioRecorder trajectories are saved in `audio_AudioRecorder*.jpg`; they show onboarding/setup and repeated waits, not failed screen retrieval. LFM's `open_app` targets Audio Recorder's WelcomeActivity (`adb_utils.py:62`), while GUI-Owl uses the launcher; an onboarding difference alone would not establish a sick emulator. No evidence justifies reclassifying the preceding ten noncrashed episodes. No other arm records an emulator-2 episode before the 10:05 restart. The failed v1 environment log and queue logs account for the zero-episode interval.

**Arm assignment and resume history**

| Arm | Seed 7 | Seed 1234 | Seed 2026 |
|---|---|---|---|
| v4 | 5558; four reruns also 5558 | Original 5558; 113 reruns 5556 | 5556 |
| GUI-Owl | 5556; one rerun 5558 | 5558, paused/resumed; one rerun 5558 | 5556; two reruns 5558 |
| v1 | 5558 | 5556 | Initial 5558 setup failed, 0 episodes; full relaunch 5556; one rerun 5558 |

The v1/2026 relaunch started 10:04 and finished 13:20:45. The failed 5558 attempt contains no `Running task:` or checkpoint record. GUI-Owl/1234 resumed the same run directory at 18:07, skipped the 33 already saved episodes and restarted the interrupted MarkorMergeNotes. Its repeated task enumerations are not repeated execution: the log explicitly says `Skipping already processed task`. Exactly one result was written for each template. v1/7's planned pause in the 02:35 entry did not actually occur: its single run proceeds 01:30–06:32; the later GUI-Owl/1234 arm was the one paused for development. This is a chronology clarification, not score selection.

Initial seed-7 v1/GUI-Owl used `local_sealed_aw.sh`. Later sealed work used v2/v3; v3 adds bounded, PID-bound server startup, not different model/agent arguments. All rerun SRV/RUN arrays match the respective sealed arm. The checkpoint changes disable automatic retry of saved exceptions and make checkpoint writes atomic/fail-closed; they do not alter ordinary agent actions. The later `run_aw.py` change adds MAI-UI without changing the LFM or GUI-Owl branches. The local patch and actual `suite_utils.py` both require agent termination for success.

| Config | v4 | GUI-Owl matched | v1 |
|---|---|---|---|
| Model | AndroidAgent-v4 Q4_K_M | GUI-Owl-1.5-2B-Instruct Q4_K_M | AndroidControl Q4_K_M |
| Projector | LFM3 Q8_0 | GUI-Owl Q8_0 | LFM3 Q8_0 |
| Context / image token cap | 8192 / 1024 | 20480 / 2600 | 8192 / 1024 |
| Pixel cap / completion tokens | 774400 / 512 | 1048576 / 256 | 774400 / 512 |
| Prompt / installed apps | v4 / yes | GUI-Owl / yes | original / no, as preregistered |
| Other | deepseek reasoning | jinja, one image | deepseek reasoning |

All use one screenshot per step, temperature 0, a one-second action wait, `int(10*complexity)` steps, one task combination, `-np 1 -ngl 99`. LFM has one parse retry as preregistered. “Matched” therefore describes the specified configuration, not equal token limits or FLOPs. Both app-list paths call `app_resolver.device_app_names`; the actual per-episode prompt/app-list values are not saved, so byte-for-byte prompt parity cannot be independently certified.

Server logs consistently identify the same model path, projector and context for each arm across seeds/reruns. Current model mtimes all precede their held-out runs. There is no evidence of a model change, but runtime hashes/build receipts were not recorded; identical historical bytes cannot be proven from paths alone. The v4 export manifest pins the merged model rather than a per-launch GGUF receipt.

Current AVD configurations match after whitespace normalization except equivalent `6442450944` versus `6G` disk sizing: Pixel 6, API 33 arm64, 1080×2400, density 420, four CPUs, 2 GiB RAM. Original/restart logs show emulator 37.1.11, the same system-image path and software graphics configuration. `avd_config_comparison.json` captures these read-only configuration checks. These facts do not establish equal writable device state: snapshot resets are skipped throughout the logs (report P2-1).

**The nine date-wording replacements**

All nine are v4/1234, originally crashing during initial device setup, and all nine reruns fail. Each replacement's saved seed equals `sha256('1234_<template>_0') mod 2**32`, its `instance_id` is 0, and its goal equals both GUI-Owl and v1 on that seed/template. No scoring benefit arises from accepting these nine failures rather than retaining their original failures.

| Template | Original date text → rerun text |
|---|---|
| SimpleCalendarAnyEventsOnDate | October 25 2023 → the Wednesday after next |
| SimpleCalendarEventOnDateAtTime | October 23 2023 → the Monday after next |
| SimpleCalendarEventsInTimeRange | October 21 2023 → this Saturday |
| SimpleCalendarEventsOnDate | October 20 2023 → Friday |
| SportsTrackerActivitiesOnDate | October 7 2023 → October 07 |
| SportsTrackerActivityDuration | October 15 2023 → today |
| SportsTrackerTotalDistanceForCategoryOverInterval | October 3 2023 → October 03 2023 |
| TasksCompletedTasksForDate | October 20 2023 → October 20 |
| TasksHighPriorityTasksDueOnDate | October 22 2023 → this Sunday |

`InformationRetrieval.initialize_task` calls its parent/device initialization, initializes the proto, and only then calls `_maybe_replace_date` (lines 82–85). Parent initialization resets RNG to the instance seed. The date alternatives use AndroidWorld's fixed date, not the host date. Proto initialization precedes wording mutation, preserving the underlying date value. Thus the saved raw/reworded goals are explained by different initialization phases. `suite_utils.py:149–168` instantiates the full registry from independent per-template seeds before task-subset filtering, so rerunning a subset does not shift the RNG for later templates.

All 1,037 artifacts that store a seed match their expected instance seed, all 1,166 store instance 0, and all final cross-arm goals match after the known MarkorCreateFolder timestamp normalization. The 129 exception artifacts omit instance seed and the artifacts do not persist full parameter dictionaries, so identity of those crashed originals rests on the launch seed, deterministic derivation, task/template and goal evidence. A direct comparison of every hidden parameter is unavailable.

`git diff dd2f7f7 -- scripts/sealed_analysis.py` contains only the documented alternate-goal admission, its `goal_matched` annotation/comments, and the pending-rerun note correction. No statistic, threshold or scoring code changed. The goal predicate itself is not a proof of instance identity; see report P3-1 and `validator_counterexample.json`.
