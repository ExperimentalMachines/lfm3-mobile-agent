# MobileWorld run 2: v4 vs GUI-Owl-1.5-2B (105 English GUI-only tasks)

| Model | Successes / 105 | Tasks with a result | No result (counted as failure) | Setup/scoring errors over all attempts (tasks) | Tasks attempted more than once |
|---|---|---|---|---|---|
| LFM3-VL-2B-AndroidAgent-v4 | **6** (5.7%) | 104 | 1: ThanksgivingPrepTask (setup_failed) | 8 (1) | 1 |
| GUI-Owl-1.5-2B | **22** (20.9%) | 102 | 3: SendInterviewEmailTask (ask_user_without_simulator), CheckInvoiceTask2 (unsupported_action), ThanksgivingPrepTask (setup_failed) | 12 (8) | 14 |

Paired on the same 105 tasks: both solved 6, v4 only 0, GUI-Owl only 16, neither 83; difference -15.2 pp, exact McNemar p = 3.05e-05.

Sensitivity: excluding the 8 tasks that hit a setup or scoring error in either run, v4 6 vs GUI-Owl 22 of 97.

Earlier (replaced) attempts, by how they ended:

* LFM3-VL-2B-AndroidAgent-v4: setup_failed 7; successes that came after an earlier failed attempt: none.
* GUI-Owl-1.5-2B: setup_failed 8, ask_user_without_simulator 6, unsupported_action 5, scoring_failed 3, invalid_model_output 2; successes that came after an earlier failed attempt: none.

MobileWorld's own `--auto_retry 3` (same flag for both runs) re-runs a task whose attempt ended without a result, whatever the reason, including the model's own crashes; mw_resume.sh then applied the pre-declared completion rule (docs/PREREG_v4.md, 2026-11-19 01:55). Single run per model at temperature 0; a secondary, descriptive benchmark.
