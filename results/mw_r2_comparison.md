# MobileWorld run 2: v4 vs GUI-Owl-1.5-2B (105 English GUI-only tasks) (PROVISIONAL: GUI-Owl-1.5-2B pending ThanksgivingPrepTask)

| Model | Successes / 105 | Tasks with a result | No result (counted as failure) | Folder-level setup/scoring failures (tasks) | Device-health re-initialisations (tasks) | Task executions |
|---|---|---|---|---|---|---|
| LFM3-VL-2B-AndroidAgent-v4 | **6** (5.7%) | 104 | 1: ThanksgivingPrepTask (setup_failed) | 8 (1) | 2 (2) | 114 |
| GUI-Owl-1.5-2B | **22** (21.0%) | 102 | 3: SendInterviewEmailTask (ask_user_without_simulator), CheckInvoiceTask2 (unsupported_action), ThanksgivingPrepTask (setup_failed) | 12 (8) | 15 (14) | 144 |

Paired on the same 105 tasks: both solved 6, v4 only 0, GUI-Owl only 16, neither 83; difference -15.2 pp, exact McNemar p = 3.05e-05 (conditional on these task pairs; one run per model).

Sensitivity (environment): excluding the 8 tasks with a folder-level setup/scoring failure in either run, v4 6 vs GUI-Owl 22 of 97; also excluding tasks with a device-health re-initialisation (18 tasks), v4 5 vs GUI-Owl 21 of 87. Excluding known errors cannot show that the remaining tasks were unaffected; GUI-Owl's container had more environment failures than v4's.

Retries and harness events (no score was changed by them):

* LFM3-VL-2B-AndroidAgent-v4: earlier folders ended setup_failed 7; successes after an earlier failed folder: none; successes after a device-health re-initialisation: none.
* GUI-Owl-1.5-2B: earlier folders ended setup_failed 8, ask_user_without_simulator 6, unsupported_action 5, scoring_failed 3, invalid_model_output 2; successes after an earlier failed folder: none; successes after a device-health re-initialisation: SendWaiverTask.
* GUI-Owl's official agent returns an `error_env` sentinel after 5 unparseable outputs, which MobileWorld's own action validator rejects (an upstream bug), so instead of ending and being scored the task was re-executed (2 executions); those tasks still scored 0.
* `ask_user` needs an LLM-backed user simulator this setup does not have: 7 GUI-Owl executions hit it (v4 has no such action). `double_tap` was rejected by GUI-Owl's official action adapter (not by the runtime).
* v4's adapter completes v4's trained type-then-Enter action with a synthetic Enter on the next environment step (138 synthetic Enters; they count toward the 50-round budget, so v4 made fewer than 50 decisions in 37 of the 85 tasks that reached the budget). When typing was the 50th round the Enter was never sent: MastodonAdjustTootsTask, MastodonUpdateContactsTask, MattermostIncidentEscalationTask (all scored 0; not evidence they would have passed).
* ThanksgivingPrepTask's initialisation failed on every attempt in both containers (and on AWS in v4 run 1): a persistent task-specific initialisation failure; whether from task code or a shared dependency is not identified.

| Setting | v4 | GUI-Owl (official agent) |
|---|---|---|
| Image history | current screenshot | current screenshot (`history_n` 1) |
| Text history | last 8 intent/action pairs | all previous step conclusions |
| Image budget | client resize to at most 880x880 pixels of area, server cap 1,024 tokens | full screenshot, server cap 2,600 tokens |
| Output cap / parse attempts | 512 tokens / up to 2 | 2,048 tokens / up to 5 |
| Quantisation | Q4_K_M | Q4_K_M |
| Step budget | 50 environment rounds incl. synthetic Enters | 50 environment rounds |

MobileWorld's own `--auto_retry 3` (same flag in every run) re-runs a task whose execution ended without a result, whatever the reason; mw_resume.sh then applied the pre-declared completion rule (docs/PREREG_v4.md 2026-11-19 01:55, clarified 05:45: the fresh-container allowance is one more invocation, inside which `--auto_retry 3` allows up to 4 executions, equally for every model). Single run per model at temperature 0; a secondary, descriptive benchmark comparing agent pipelines, not model weights alone. Independent recomputation: results/codex/mw_r2_audit/ (VALID WITH CAVEATS).
