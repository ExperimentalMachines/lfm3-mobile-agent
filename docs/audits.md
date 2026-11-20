# Codex audits

Every important step was checked by an independent, adversarial reviewer before the project relied on it.

| | |
|---|---|
| Reviewer | Codex CLI, model gpt-6-astra, maximum reasoning effort |
| Access | Read access to the repository; writes only inside its own audit folder |
| Where | [`results/codex/`](../results/codex/): `PROMPT_<name>.md` (the brief) + the report and its evidence |
| Paths inside reports | Refer to the repository at audit time. Moved or removed files are at tag `archive/pre-restructure-2026-11-20` ([repository.md](repository.md)) |

Start times are Asia/Manila (UTC+8), from each Codex session's log.

## Final results (the ones the headline numbers rest on)

| Started | Audit | Checked | Verdict | Outcome |
|---|---|---|---|---|
| 11-19 16:11 | [final_heldout_audit](../results/codex/final_heldout_audit/report.md) | Held-out AndroidWorld: every number and re-run; the 88 successes on seeds 1234 and 2026 | **Valid with caveats** | Numbers reproduce (723 checks). Added: device-state caveat, one v1 dispute, stronger input checks, three-template sensitivity |
| 11-19 20:03 | [mw_maiui_audit](../results/codex/mw_maiui_audit/report.md) | MobileWorld MAI-UI arm | **Valid with caveats** | 11/105 reproduces. Corrected our account of MAI-UI's environment failures |
| 11-19 05:02 | [mw_r2_audit](../results/codex/mw_r2_audit/report.md) | MobileWorld v4 vs GUI-Owl | **Valid with caveats** | 6 vs 22 reproduces. Environment reporting corrected; completion rule clarified |
| 11-19 00:31 | [seed7_analysis_audit](../results/codex/seed7_analysis_audit/report.md) | Held-out seed 7 (preliminary) | Valid with caveats | Template manifest, outward-rounded CI and per-success review adopted before later seeds were opened |
| 11-18 13:25 | [v4_seed30_audit](../results/codex/v4_seed30_audit/report.md) | v4 development gate | **Freeze OK** | v4 frozen as the final model |

## Training data

| Started | Audit | Checked | Verdict | Outcome |
|---|---|---|---|---|
| 11-16 22:18 | [dataset_viability](../results/codex/dataset_viability.md) | Which public datasets are usable | Per-dataset verdicts | v2 mix chosen ([datasets.md](datasets.md#sources-considered)) |
| 11-17 11:24 | [data_v2_audit](../results/codex/codex_data_v2_audit.md) | v2 dataset | No-go | Train/dev screen leakage and conversion bugs fixed |
| 11-17 12:20 | [data_v2_verify](../results/codex/codex_data_v2_verify.md) | v2 fixes | No-go | More fixes |
| 11-17 12:58 | [data_v2_verify3](../results/codex/codex_data_v2_verify3.md) | v2 fixes | No-go | Two blockers left |
| 11-17 13:25 | [data_v2_verify4](../results/codex/codex_data_v2_verify4.md) | Last two blockers | **Go** | v2 trained on `42f7f763` |
| 11-17 17:11 | [dataset_viability_v4](../results/codex/dataset_viability_v4.md) | Nine more datasets for v4 | Admit none | No new sources for v4 |
| 11-18 03:19 | [v4_data_audit](../results/codex/codex_v4_data_audit.md) | First v4 dataset | **Stop** | First v4 run abandoned; data rebuilt |
| 11-18 04:08 | [v4b_reaudit](../results/codex/codex_v4b_reaudit.md) | Rebuilt v4 dataset | Stop | Training continued; residual errors measured and disclosed in the preregistration |

## Pipeline, harness and models

| Started | Audit | Checked | Verdict | Outcome |
|---|---|---|---|---|
| 11-16 18:36 | [pass 1](../results/codex/codex_eval_pass1.md) | Evaluation pipeline | Not yet fit to publish | Harness fixes |
| 11-16 21:42 → 11-17 00:06 | passes [2](../results/codex/codex_adversarial_pass2.md)–[11](../results/codex/codex_verify_pass11.md) | Fixes, re-verified each round | No-go ×9, then **Go** | Pipeline accepted after pass 11 |
| 11-17 04:42 | [final_results_eval](../results/codex/codex_final_eval.md) | v1-era results | Offline gains real; robust phone use not shown | Its first recommendation became the runtime-feedback ablation |
| 11-18 01:16 | [v3_audit](../results/codex/codex_v3_audit.md) | v3 results and model card | No-go on the card; numbers pass | Card wording and a summarizer defect fixed |
| 11-18 01:51 | [overnight_research](../results/codex/codex_overnight_research.md) | What to do next | Corrected v4 SFT, then a GRPO pilot | Plan for v4 and v4-RL |
| 11-18 02:00 | [v4_pipeline_audit](../results/codex/codex_v4_pipeline_audit.md) | v4 build and sealed runner | Not ready (7 serious defects) | Fixed before the build; gate made numeric |
| 11-18 06:02 | [recovery_gate_audit](../results/codex/codex_recovery_gate_audit.md) | VM-loss recovery, gate | Fix before switch | Stricter answer criterion; safer resume |
| 11-18 09:11 | [v4_local_lane_audit](../results/codex/v4_local_lane_audit/codex_v4_local_lane_audit.md) | Local merge/export, sealed resume | Fix first | Merge check and resume fixed |
| 11-18 09:31 | [v4_lane_reaudit](../results/codex/v4_lane_reaudit/codex_v4_lane_reaudit.md) | Re-check of the above | Fix | Atomic checkpoints; unreadable files stop a resume |
| 11-18 10:16 | [emu2_v3_promo_audit](../results/codex/emu2_v3_promo_audit/report.md) | Emulator queue, v4-RL promotion | Fix (two moderate findings) | Fixed; v4-RL promotion recomputed (fails) |
| 11-18 18:03 | [session_1118_audit](../results/codex/session_1118_audit/report.md) | Phone speed, MobileWorld run 1, docs | Fix | MobileWorld run 1 found unfair; replaced by run 2 |
| 11-18 21:35 | [round2_audit](../results/codex/round2_audit/report.md) | Phone round 2, MobileWorld adapter v2 | Fix (no serious finding) | Wording and adapter limits corrected and disclosed |

Verdict words follow each report's own first line. Severity labels in reports: P1 = serious, P2 = moderate, P3 = minor.
