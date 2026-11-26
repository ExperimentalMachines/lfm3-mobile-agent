# MobileWorld run 2: v4 vs GUI-Owl-1.5-2B, with MAI-UI-2B as a third arm (105 English GUI-only tasks)

| Model | Successes / 105 | Tasks with a result | No result (counted as failure) | Folder-level setup/scoring failures (tasks) | Device-health re-initialisations (tasks) | Task executions |
|---|---|---|---|---|---|---|
| LFM3-VL-2B-AndroidAgent-v4 | **6** (5.7%) | 104 | 1: ThanksgivingPrepTask (setup_failed) | 8 (1) | 2 (2) | 114 |
| GUI-Owl-1.5-2B | **22** (21.0%) | 102 | 3: SendInterviewEmailTask (ask_user_without_simulator), CheckInvoiceTask2 (unsupported_action), ThanksgivingPrepTask (setup_failed) | 16 (8) | 15 (14) | 148 |
| MAI-UI-2B | **11** (10.5%) | 98 | 7: MattermostReadingGroupTask (ask_user_without_simulator), ReadQwen3PaperTask4 (setup_failed), ReadQwen3PaperTask5 (setup_failed), ReadQwen3PaperTask3 (setup_failed), ReadQwen3PaperTask1 (setup_failed), SendFormsTask (setup_failed), ThanksgivingPrepTask (setup_failed) | 40 (8) | 19 (14) | 175 |

Paired on the same 105 tasks: both solved 6, v4 only 0, GUI-Owl only 16, neither 83; difference -15.2 pp, exact McNemar p = 3.05e-05 (conditional on these task pairs; one run per model).

Sensitivity (environment): excluding the 8 tasks with a folder-level setup/scoring failure in either run, v4 6 vs GUI-Owl 22 of 97; also excluding tasks with a device-health re-initialisation (18 tasks), v4 5 vs GUI-Owl 21 of 87. Excluding known errors cannot show that the remaining tasks were unaffected; GUI-Owl's container had more environment failures than v4's.

MAI-UI-2B vs v4 (paired, 105 tasks): both 4, MAI-UI only 7, v4 only 2; difference +4.8 pp, exact McNemar p = 0.18.
MAI-UI-2B vs GUI-Owl (paired, 105 tasks): both 9, MAI-UI only 2, GUI-Owl only 13; difference -10.5 pp, exact McNemar p = 0.00739.

MAI-UI's run ended 6 tasks without a result after setup failures (ReadQwen3PaperTask1, ReadQwen3PaperTask3, ReadQwen3PaperTask4, ReadQwen3PaperTask5, SendFormsTask, ThanksgivingPrepTask; GUI-Owl and v4: ThanksgivingPrepTask only). Excluding them: MAI-UI 11 vs v4 6 vs GUI-Owl 22 of 99. MAI-UI ran after the other two, on recreated containers after two spot preemptions, so its environment was not identical.

Those final setup failures have mixed histories (per task in mw_r2_comparison.json): ReadQwen3PaperTask1 (half b, 8 executions, 1 with model actions, earlier: setup_failed 6, ask_user_without_simulator 1); ReadQwen3PaperTask3 (half b, 8 executions, 2 with model actions, earlier: setup_failed 5, ask_user_without_simulator 2); ReadQwen3PaperTask4 (half b, 8 executions, 3 with model actions, earlier: setup_failed 4, ask_user_without_simulator 3); ReadQwen3PaperTask5 (half a, 8 executions, 5 with model actions, earlier: ask_user_without_simulator 5, setup_failed 2); SendFormsTask (half b, 8 executions, 0 with model actions, earlier: setup_failed 7); ThanksgivingPrepTask (half a, 8 executions, 0 with model actions, earlier: setup_failed 7). In the ReadQwen3Paper tasks MAI-UI acted and then called ask_user, which fails without a user simulator, before setup later failed. Half b's emulator (lfmenv_0) lost device health during its last invocation: ReadQwen3PaperTask2 initialised at 11:18 UTC and ran 50 steps, then initialisations failed from about 11:29 UTC. Half a had separate setup failures around 10:29-10:36 UTC. The containers' own logs (results/mobileworld/container_logs/, saved before the VM was deleted; they start at the containers' recreation after the second preemption, 06:30 UTC) show the emulator dying with a fatal KVM error (`kvm_user_backed_ram_map: error registering slot: File exists`) 6 times in mobile_world_env_0 and 11 times in lfmenv_0 from 07:14 UTC on. The matching logs of the GUI-Owl and v4 runs no longer exist (those containers were deleted by earlier preemptions), so whether they saw the same crashes is unknown. What-if for these five tasks only (not a bound on a run with every environment problem repaired): had they been successes, MAI-UI 16 vs GUI-Owl 22 (-5.7 pp, McNemar p = 0.263); GUI-Owl and v4 solved none of them. Excluding all 16 tasks with a folder-level setup/scoring failure or a device-health re-initialisation in MAI-UI's run: MAI-UI 11 vs v4 6 vs GUI-Owl 21 of 89.

Retries and harness events (no score was changed by them):

* LFM3-VL-2B-AndroidAgent-v4: earlier folders ended setup_failed 7; successes after an earlier failed folder: none; successes after a device-health re-initialisation: none.
* GUI-Owl-1.5-2B: earlier folders ended setup_failed 12, ask_user_without_simulator 6, unsupported_action 5, scoring_failed 3, invalid_model_output 2; successes after an earlier failed folder: none; successes after a device-health re-initialisation: SendWaiverTask.
* MAI-UI-2B: earlier folders ended setup_failed 34, ask_user_without_simulator 13, interrupted 4; successes after an earlier failed folder: none; successes after a device-health re-initialisation: none.
* GUI-Owl's official agent returns an `error_env` sentinel after 5 unparseable outputs, which MobileWorld's own action validator rejects (an upstream bug), so instead of ending and being scored the task was re-executed (2 executions); those tasks still scored 0.
* `ask_user` needs an LLM-backed user simulator this setup does not have: 7 GUI-Owl executions and 14 MAI-UI executions hit it (v4 has no such action). `double_tap` was rejected by GUI-Owl's official action adapter (not by the runtime).
* v4's adapter completes v4's trained type-then-Enter action with a synthetic Enter on the next environment step (138 synthetic Enters; they count toward the 50-round budget, so v4 made fewer than 50 decisions in 37 of the 85 tasks that reached the budget). When typing was the 50th round the Enter was never sent: MastodonAdjustTootsTask, MastodonUpdateContactsTask, MattermostIncidentEscalationTask (all scored 0; not evidence they would have passed).
* ThanksgivingPrepTask's initialisation failed on every attempt in both containers (and on AWS in v4 run 1): a persistent task-specific initialisation failure; whether from task code or a shared dependency is not identified.

| Setting | v4 | GUI-Owl (official agent) | MAI-UI (official agent) |
|---|---|---|---|
| Image history | current screenshot | current screenshot (`history_n` 1) | current screenshot (`history_n` 1; official default 3) |
| Text history | last 8 intent/action pairs | all previous step conclusions | official agent's own (unchanged) |
| Image budget | client resize to at most 880x880 pixels of area, server cap 1,024 tokens | full screenshot, server cap 2,600 tokens | full screenshot, server cap 2,600 tokens |
| Output cap / parse attempts | 512 tokens / up to 2 | 2,048 tokens / up to 5 | 2,048 tokens / official |
| Quantisation | Q4_K_M | Q4_K_M | Q8_0 (Q4_K_M degenerates) |
| Step budget | 50 environment rounds incl. synthetic Enters | 50 environment rounds | 50 environment rounds |

MobileWorld's own `--auto_retry 3` (same flag in every run) re-runs a task whose execution ended without a result, whatever the reason; mw_resume.sh then applied the pre-declared completion rule (docs/preregistrations/heldout-main-vs-gui-owl.md 2026-11-19 01:55, clarified 05:45: the fresh-container allowance is one more invocation, inside which `--auto_retry 3` allows up to 4 executions, equally for every model). Single run per model at temperature 0; a secondary, descriptive benchmark comparing agent pipelines, not model weights alone. Independent recomputation: results/codex/mw_r2_audit/ (VALID WITH CAVEATS).
