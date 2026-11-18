**Scope:** all 18 v4 and all 16 GUI-Owl successes after the five substitutions. Model outputs, parsed actions, step sequences, terminal observations and relevant checker implementations were inspected. `success_traces.json` preserves the outputs/actions, episode paths and SHA-256 hashes. Each linked image is the observation immediately before the terminal action; the harness does not save a separate screenshot/accessibility tree at checker time. No live state or database was queried.

Every counted success ends explicitly: v4 emits `status(complete)` or `answer`; GUI-Owl emits `terminate(success)` or `answer`. `suite_utils.py:261` also gates the stored score on `interaction_results.done`. There is no success obtained by simply exhausting the step budget. “Supported” below means no contradiction was found in the recorded evidence, not that the entire final database can be independently recovered from screenshots.

| Arm / task (terminal observation) | Steps | Review |
|---|---:|---|
| v4 [ClockStopWatchPausedVerify](final_screens/v4_ClockStopWatchPausedVerify.png) | 4 | **False positive.** Opens Clock, opens Stopwatch, taps Play, declares completion. Terminal screen shows 02.99 and the Pause control. See [all four steps](ClockStopWatchPausedVerify_steps.jpg). |
| v4 [ClockStopWatchRunning](final_screens/v4_ClockStopWatchRunning.png) | 4 | Supported: starts stopwatch; terminal screen shows elapsed time and Pause. |
| v4 [ExpenseDeleteSingle](final_screens/v4_ExpenseDeleteSingle.png) | 5 | Supported: selects Pest Control, deletes it; final list no longer contains the target. |
| v4 [NotesIsTodo](final_screens/v4_NotesIsTodo.png) | 6 | Supported: answers `True`; Project Proposal has a todo checkbox. |
| v4 [NotesMeetingAttendeeCount](final_screens/v4_NotesMeetingAttendeeCount.png) | 9 | Supported: answers `20`, matching Sales Strategy Discussion. |
| v4 [OpenAppTaskEval](final_screens/v4_OpenAppTaskEval.png) | 8 | Supported: Contacts is open with permission dialogs cleared. |
| v4 [RecipeDeleteSingleRecipe](final_screens/v4_RecipeDeleteSingleRecipe.png) | 7 | Supported: deletes Caprese Salad Skewers; final list empty. |
| v4 [RecipeDeleteSingleWithRecipeWithNoise](final_screens/v4_RecipeDeleteSingleWithRecipeWithNoise.png) | 10 | Supported: locates and deletes Zucchini Noodles with Pesto. |
| v4 [RetroPlayingQueue](final_screens/v4_RetroPlayingQueue.png) | 11 | Supported by the four ordered “add to playing queue” actions and checker. Final screenshot alone does not expose the queue. `retro_music.py:203-206` compares the entire queue, in order, to the requested songs. |
| v4 [SimpleCalendarLocationOfEvent](final_screens/v4_SimpleCalendarLocationOfEvent.png) | 6 | Supported: `The beach`, visible on Lunch with Client. |
| v4 [SportsTrackerActivityDuration](final_screens/v4_SportsTrackerActivityDuration.png) | 4 | Supported: `50` minutes for Thursday's climbing activity. |
| v4 [SportsTrackerTotalDurationForCategoryThisWeek](final_screens/v4_SportsTrackerTotalDurationForCategoryThisWeek.png) | 4 | Supported: `195` minutes = 135 + 60 for cycling. |
| v4 [SystemBluetoothTurnOff](final_screens/v4_SystemBluetoothTurnOff.png) | 10 | Supported: Bluetooth off. |
| v4 [SystemBluetoothTurnOnVerify](final_screens/v4_SystemBluetoothTurnOnVerify.png) | 7 | Supported: Bluetooth already on. |
| v4 [SystemBluetoothTurnOn](final_screens/v4_SystemBluetoothTurnOn.png) | 6 | No demonstrated failure: off-to-on tap, then transient disabled switch with thumb on the right. Checker reads the system setting. This transition frame is not evidence of an off state; see [all steps](SystemBluetoothTurnOn_steps.jpg). |
| v4 [SystemWifiTurnOnVerify](final_screens/v4_SystemWifiTurnOnVerify.png) | 6 | Supported: Wi-Fi on. |
| v4 [SystemWifiTurnOn](final_screens/v4_SystemWifiTurnOn.png) | 7 | Supported: Wi-Fi on after the switch action. |
| v4 [TasksIncompleteTasksOnDate](final_screens/v4_TasksIncompleteTasksOnDate.png) | 6 | Supported: the three distinct requested titles match the visible list. |
| GUI [NotesMeetingAttendeeCount](final_screens/guiowl_NotesMeetingAttendeeCount.png) | 8 | Supported: `20`. |
| GUI [NotesRecipeIngredientCount](final_screens/guiowl_NotesRecipeIngredientCount.png) | 8 | Supported: `3 teaspoons` of almond flour. |
| GUI [RecipeDeleteMultipleRecipesWithConstraint](final_screens/guiowl_RecipeDeleteMultipleRecipesWithConstraint.png) | 11 | Legitimate no-op for this instance: no recipe uses spirulina in its directions. The generator permits zero targets, and the checker requires the non-target rows to remain unchanged. See explanation below. |
| GUI [RecipeDeleteMultipleRecipes](final_screens/guiowl_RecipeDeleteMultipleRecipes.png) | 23 | Supported: deletes Sausage and Peppers Skillet, Chickpea Vegetable Soup, and Vegetable Stir Fry with Tofu. |
| GUI [SimpleCalendarEventsInTimeRange](final_screens/guiowl_SimpleCalendarEventsInTimeRange.png) | 10 | Supported: `Yoga Class` is in the requested interval; the earlier call is outside it. |
| GUI [SimpleCalendarEventsOnDate](final_screens/guiowl_SimpleCalendarEventsOnDate.png) | 6 | Supported: `Product demo`. |
| GUI [SimpleCalendarLocationOfEvent](final_screens/guiowl_SimpleCalendarLocationOfEvent.png) | 6 | Supported: `The beach`. |
| GUI [SimpleCalendarNextMeetingWithPerson](final_screens/guiowl_SimpleCalendarNextMeetingWithPerson.png) | 7 | Supported: `October 24 2023 20:00`, matching the next meeting with Lucas. |
| GUI [SimpleSmsReplyMostRecent](final_screens/guiowl_SimpleSmsReplyMostRecent.png) | 10 | Supported: replies “Where there is smoke, there is fire”; omitted final punctuation is permitted by the checker. |
| GUI [SimpleSmsResend](final_screens/guiowl_SimpleSmsResend.png) | 7 | Supported retry: sends the same “Don't cry over spilled milk.” message again to Mia Pereira. The checker requires one additional sent message and matching content. |
| GUI [SimpleSmsSendReceivedAddress](final_screens/guiowl_SimpleSmsSendReceivedAddress.png) | 15 | Supported: sends the received address to Emilia. An earlier extra message to Lily is visible but is not prohibited by this goal/checker. |
| GUI [SimpleSmsSend](final_screens/guiowl_SimpleSmsSend.png) | 10 | Supported: sends `Inconceivable!` to the requested number. |
| GUI [SystemBrightnessMaxVerify](final_screens/guiowl_SystemBrightnessMaxVerify.png) | 7 | Supported: maximum brightness, 100% on screen. |
| GUI [SystemBrightnessMin](final_screens/guiowl_SystemBrightnessMin.png) | 6 | No demonstrated failure: sets the left endpoint. Checker tests the raw system-brightness minimum; the UI percentage alone does not establish a failure. |
| GUI [TasksIncompleteTasksOnDate](final_screens/guiowl_TasksIncompleteTasksOnDate.png) | 7 | Supported: same three distinct task titles as v4, reordered. |
| GUI [TurnOnWifiAndOpenApp](final_screens/guiowl_TurnOnWifiAndOpenApp.png) | 14 | Supported: Wi-Fi enabled, then Camera opened. Final observation is the Camera launch screen; foreground-package and Wi-Fi checks must both pass for full credit. |

For the spirulina case, `android_world/android_world/task_evals/single/recipe.py:154-180` reduces the requested target count from three to zero when no matching recipe can be generated; `:148-151` deliberately disables the nonempty-target precondition. “Spirulina” occurs only in the ingredient-choice list (`:998`), not in the generated directions. GUI-Owl searches, finds no match, makes no deletion, and terminates. This is an already-satisfied instance, not an agent receiving credit for an unperformed required deletion. It should not be advertised as evidence that GUI-Owl successfully deleted recipes in this particular episode.

The stopwatch checker, by contrast, accepts a `Start` accessibility node plus two `Stopwatch` nodes (`clock.py:43-63`). Its logged success conflicts with the saved running state and the absence of a subsequent pause action. The checker-time tree is unavailable, so stale accessibility state versus an unrelated/hidden matching node cannot be distinguished offline.
