**Verdict: FREEZE OK.** The independent development gate passes, all six credited answers have visible supporting evidence, and the permitted infrastructure retries cannot reverse the pass. Keep the frozen model. The findings below limit interpretation of the development comparison and require consistent handling in the held-out analysis. **No P1 found.**

Audit scope: seed-30 development episodes, offline predictions, source, and explicitly named development logs only. No AndroidWorld execution, emulators, servers, process signals, or sealed files/logs were accessed. All audit writes are in this directory. Episode steps below are **one-based**; screenshots show the observation **before** that step's action. [episodes.json](episodes.json) supplies every full raw episode path and SHA-256; [v4_transcripts.txt](v4_transcripts.txt) retains model outputs, reasoning, and parsed actions.

**Independent gate reconstruction.** [audit.py](audit.py) reads raw episodes without importing AndroidWorld or executing `v4_gate.py`; [recomputed.json](recomputed.json) contains exact counts and input checks.

| Saved run | Episodes | Answer successes /25 | Action successes /91 | Full successes /116 | Retained exceptions |
|---|---:|---:|---:|---:|---:|
| v4 | 116 | 6 | 12 | 18 | 4 |
| v3 | 116 | 0 | 13 | 13 | 3 |
| v1 | 116 | 0 | 15 | 15 | 2 |
| GUI-Owl matched | 116 | 10 | 13 | 23 | 0 |

Each file holds one episode; task sets and goals agree across arms, allowing only `MarkorCreateFolder`'s timestamp. All present instance seeds independently match SHA-256(`30_<task>_0`) modulo 2^32. Missing seeds occur only in exception records. The 116 v3 file hashes match the pin. All credited successes have actual recorded steps and terminal actions. Success means finite `is_successful >= 1` with no exception; v3's `TurnOnWifiAndOpenApp = 0.5` is correctly excluded. The 25-task answer list also matches the source textproto. Dropping retained exceptions gives secondary scores 18/112, 13/113, 15/114, and 23/116; these are not the primary denominators.

Using `agent_format.parse_action(strict=True)` and `data/v4_answer_check.gate_answer`, with exact coverage of the locally pinned `3375539` dev rows:

| Check | Independent result | Required |
|---|---:|---:|
| dev_answer gate_answer | 118/136 = 86.765% | ≥20% |
| dev_answer answer emitted | 130/136 = 95.588% | ≥50% |
| dev_complete false answer | 0/80 | ≤3% |
| AndroidWorld answer successes | 6 | ≥3 |
| AndroidWorld action successes | 12 | ≥13−3 = 10 |

All 216 offline outputs parse strictly. `same_answer` gives 120/136; the narrower `exact_answer` gives 111/136. Thus the gate's `dev_answer_exact` field is **gate_answer**, not literal equality. `dev_complete` emits complete on 61/80; the gate does not require every control to complete. These reproduce `results/v4_gate_seed30.txt` without relying on its computation.

**The six answer successes are legitimate observed retrievals.** No answer was emitted from the launcher or accepted as an empty/default answer. All six are also among GUI-Owl's ten successes.

| v4 episode / screenshot evidence | Navigation and final answer |
|---|---|
| [NotesMeetingAttendeeCount](screenshots/NotesMeetingAttendeeCount.jpg) | Joplin → search exact meeting title → open note; step 5 reads “25 individuals were present” and answers `25`. |
| [NotesRecipeIngredientCount](screenshots/NotesRecipeIngredientCount.jpg) | Search spirulina → Chicken Alfredo → wait for content; step 6 reads `3/4 cup spirulina`, answers `3/4 cup`. |
| [NotesTodoItemCount](screenshots/NotesTodoItemCount.jpg) | Open Ideas folder; step 4 counts the three checkbox items, answers `3`. |
| [SimpleCalendarAnyEventsOnDate](screenshots/SimpleCalendarAnyEventsOnDate.jpg) | Select Oct 28; step 3 supplies exactly the three visible titles: Game night, Product demo, Date night. |
| [SimpleCalendarEventsOnDate](screenshots/SimpleCalendarEventsOnDate.jpg) | Select Oct 24; step 3 answers the sole visible title, `Trivia Night`. |
| [SimpleCalendarLocationOfEvent](screenshots/SimpleCalendarLocationOfEvent.jpg) | Search Family reunion → open event; step 5 reads `100 Main St Chicago`. |

**P2 — Retry eligibility is obscured by discarded trajectories, and eligible retries were not applied uniformly.** `android_world/android_world/suite_utils.py:245–259` wraps initialization, interaction, and scoring in one exception handler; `_create_failed_result` at line 562 replaces **all** trajectories/lengths with NaN and omits the seed. Consequently “no recorded steps” in `docs/PREREG_v4.md:132–135` is not proof of a pre-step-1 crash. The saved [exception traces](exceptions.json) establish:

| v4 exception episode | Actual phase | Single infrastructure retry? |
|---|---|---|
| MarkorCreateNoteAndSms | Initialization; SMS timestamp parsing, ~9 s | Yes |
| SimpleCalendarNextEvent | Initialization; directory clearing, ~7 s | Yes |
| SimpleSmsSend | **Scoring after interaction**, ~90 s | **No** |
| SimpleSmsSendClipboardContent | **Scoring after interaction**, ~86 s | **No** |

v3 retains three exceptions: `SimpleSmsSend` (initialization/ADB) qualifies; `SimpleSmsSendReceivedAddress` (scoring) does not. `RetroCreatePlaylist` is a pre-step ffmpeg encoding failure: infrastructure, but outside the rule's literal “emulator/adb” wording, so its eligibility needs an explicit recorded interpretation rather than an automatic retry. v1 retains two: `SimpleSmsSendClipboardContent` (initialization) qualifies; `RetroPlayingQueue` (scoring/missing table) does not. GUI-Owl's zero retained exceptions conceals **one earlier initialization exception**, `RecipeDeleteDuplicateRecipes3`: `logs/aw_run_guiowl_matched.log:49210` records it, line 58017 records its resumed attempt, and line 58663 records that retry failing normally. This retry was phase-eligible and did not add a success. [Development log evidence](development_log_evidence.json) distinguishes original attempts from final files.

The underlying defect is shared: `.venv-aw/lib/python3.11/site-packages/android_env/components/adb_controller.py:129–133` merges stderr into stdout; SMS validators parse that output as an integer or message rows (`sms_validators.py:125–136,228–232`). Calendar cleanup's root fallback also demonstrably fails with `rm: Needs 1 argument` (`file_utils.py:127–136`; v4 log lines 64444–64470); GUI-Owl's earlier cleanup failure shows the same error. These can impose unequal accidental penalties, but this sample does **not** establish agent-dependent exception rates, especially after GUI-Owl's retry and on different lanes/times. Sealed rates remain unknown.

Minimal compliant handling: preserve original artifacts; document and use exactly one same-instance retry for the two eligible v4 cases, v3 `SimpleSmsSend`, and eligible v1 case, with no outcome selection. Resolve the ffmpeg scope separately and consistently. GUI-Owl has already consumed its one eligible retry. Keep scoring-time exceptions as primary failures. Keep the v3 pin immutable and record retry results separately. Do not enable blanket `--retry_failed_on_resume`. For sealed arms, apply the same phase-based ledger without inspecting outcomes prematurely. Even granting **both pre-step v3 failures** successful retries, its action count would be 15 and v4's unchanged 12 still meets 15−3. No retry was performed in this audit.

**P2 — Seed-30 GUI-Owl did not receive the app list used by v4.** Its label is `guiowl15_2b_matched1img_q4km`; the development resume commands omit `--installed_apps` (`scripts/local_aw_lane.sh:30–33`, `scripts/local_lfm3_to_aw.sh:23–25`). The audited pre-v4 runner snapshot likewise lacks that option. Current `run_aw.py:51` defaults it off. v4 reads the list on reset (`lfm_agent.py:76–78`). Therefore 18 versus 23 is a development comparison with unequal inputs. The sealed launcher explicitly supplies `--installed_apps=true` to GUI-Owl and `--prompt_version=v4` to LFM (`scripts/local_sealed_aw_v3.sh:26–32`, also v2); this establishes configured parity, not verified sealed execution.

Other harness differences are bounded and should be disclosed:

| Dimension | v4 | GUI-Owl matched | Assessment |
|---|---|---|---|
| Current screenshots | 1 | 1 | Equal; old GUI images excluded with K=1. |
| Quantization | Q4_K_M + Q8_0 projector | Same | Launch paths/server logs agree; both GGUF headers have file_type 15. |
| Task budget / temperature | 10× complexity / 0 | Same | Every nonterminal saved episode reaches its statically derived budget. |
| Parse attempts per step | Up to 2 | 1 | Disclosed LFM advantage, unused here: zero retries/parse failures in either arm. |
| Screenshot sent, width×height | 576×1280 | 672×1504 | GUI-Owl receives more pixels. |
| Text history / server context | Last 8 steps / 8,192 | All prior action summaries / 20,480 | GUI-Owl retains more history; “matched” is not identical compute. |
| Output cap | 512 | 256 | No observed cap hit: maxima 52 and 108 tokens. |

Evidence: `lfm_agent.py:35–49,80–129`; `guiowl_agent.py:43–49,63–83,101–120`; `train/agent_format.py:21,87–95,253–281`; sealed launcher lines 26–32. Observed median prompt lengths are 1,303 versus 2,106 tokens (different tokenizers, not FLOP equivalence). LFM runtime-feedback/name rewriting is off; the app list supplies names through the prompt. [GGUF identity](gguf_identity.json) also confirms current v4 bytes match the export-log SHA-256.

**P3 — Gate input binding omits available provenance fields.** `scripts/v4_gate.py:71–85` validates dev row IDs/labels, model **path**, split, greedy decoding, and thinking mode, but ignores `prompt`, `max_pixels`, `model_fingerprint`, and row/manifest `config_hash`. [binding_probe.py](binding_probe.py) extracts only this validator and demonstrates that changing each of those fields separately is still accepted; [results](binding_probe_results.json). The actual answer/complete manifests and row hashes are consistent, so this is not evidence of swapped predictions. AndroidWorld identity similarly stops at `agent_name`, not a run-bound model/harness manifest. Pin the existing configuration, prediction hashes, model/export identity, and input image/prompt identity before reusing the gate; retain this audit's hashes for the frozen decision. Exception seed omissions do not inflate the present score because those episodes fail.

**P2 — One credited action success includes an unrequested write.** In [OpenAppTaskEval](screenshots/OpenAppTaskEval.jpg), opening Contacts already satisfies the goal, but steps 4–6 create `My Label`; step 7 visibly shows “Label created.” The checker tests only the foreground package (`task_evals/single/system.py:484–492`). Keep its official success, but do not interpret all 12 action successes as clean instruction following. Conversely, `SystemBluetoothTurnOnVerify` and `SystemWifiTurnOnVerify` are legitimate: their initializers intentionally leave the setting on (`system.py:166–178,252–264`), and v4 navigates to the visible on switch before completing. No toggle is required.

**P2 — Answer emission improved; verification and action completion remain weak.** Exhaustive mutually exclusive endings account for all **98 v4 failures**. [failure_categories.csv](failure_categories.csv) records every failure, budget, observable tags, and selected manually reviewed causes; [supplement.py](supplement.py) reproduces budget checks and comparison statistics.

| Failure ending | v4 | v3 | GUI-Owl |
|---|---:|---:|---:|
| Budget exhausted without terminal action | 55 | 61 | 92 |
| False complete | 25 | 39 | 0 |
| Incorrect answer | 14 | 0 | 1 |
| Exception | 4 | 3 | 0 |
| **Total** | **98** | **103** | **93** |

- **Never-answer:** 4/24 executable v4 question episodes, versus v3 25/25 and GUI-Owl 14/25. v4 answers 20 questions but succeeds on only 6/20; GUI-Owl succeeds on 10/11 answers. All 14 wrong v4 answers stop before the budget. `TasksDueOnDate` text-searches “October 24” and answers the empty search state, despite three matching due dates visible earlier; `SimpleCalendarEventOnDateAtTime` answers all events rather than the 20:00 event. `SportsTrackerLongestDistanceActivity` returns a prior-week row's **8.86 miles** as the requested **meters**. These are premature, incorrectly scoped answers, not parser failures.
- **False complete / early stop:** 22 of v4's 25 false completes occur before the budget. `ExpenseAddMultipleFromMarkor` stops at step 6/60 while still in Markor, without opening Pro Expense. v4's action-only false completes are **25 versus v3's 22**; the overall reduction from 39 mainly reflects replacing unanswered questions with answers.
- **Loop/no-op indicators:** exact action patterns of length 1–4 repeated at least three times occur in 46 v4 failures, 49 v3 failures, and 28 GUI-Owl failures. These overlapping indicators are not a separate partition or proof that screens never change. `VlcCreatePlaylist` repeatedly taps the already selected tab on an empty view; `SimpleCalendarAddOneEventInTwoWeeks` advances month 26 times, reaching November 2025.
- **Wrong app / grounding:** `CameraTakeVideo` opens YouTube; `SystemCopyToClipboard` opens Drive and waits through a sign-in error. `MarkorChangeNoteContent` repeatedly clicks a non-editable title without entering the replacement text. v3's 72 saved execution errors across 14 episodes are failed invented app names; v4 and GUI-Owl have zero saved execution errors. Correct launch names have not solved choosing the appropriate app, control, or recovery.
- **Format and constraints:** `SimpleCalendarNextMeetingWithPerson` sees the correct date/time but inserts a comma (`October 27, 2023 15:15`); the checker splits on commas and rejects it (`information_retrieval/proto_utils.py:137–162`). `ContactsNewContactDraft` explicitly clicks Save despite “Do NOT hit save.” These should not be lumped into OCR mistakes.

**Next work:** prioritize non-AndroidWorld training examples that require filtering, date/unit conversion, aggregation, checking completion, obeying negative constraints, and recovering from unchanged/error screens. The aggregate +5 over v3 is six answer gains with a net **one-action loss** (four action gains, five losses). Static screenshot answer RL alone does not address those sequential failures and can reward answering before the necessary navigation. Establish cleaner demonstrations and outcome-sensitive trajectory evaluation first; consider environment-based RL afterward under a separately registered arm. Preserve the frozen v4 and sealed evaluation boundary.
