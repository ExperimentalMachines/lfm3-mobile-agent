# Codex adversarial audits

Every audit was run with Codex CLI (model gpt-6-astra, reasoning effort max) as an independent reviewer with read access to the working repository; prompts are next to the reports. Verdict = the first verdict line of each report. Full reports are copied under `audits/`.

| report | verdict (first line) |
|---|---|
| [`codex_adversarial_pass2.md`](audits/codex_adversarial_pass2.md) | NO-GO |
| [`codex_data_v2_audit.md`](audits/codex_data_v2_audit.md) | Verdict: NO-GO for training the published v2 revision |
| [`codex_data_v2_verify.md`](audits/codex_data_v2_verify.md) | verdict: NO-GO for training LFM3-VL-2B on `d33cb3c21756403deac1ac74e5e4a1d1909f3fdf`, including t |
| [`codex_data_v2_verify3.md`](audits/codex_data_v2_verify3.md) | NO-GO |
| [`codex_data_v2_verify4.md`](audits/codex_data_v2_verify4.md) | GO |
| [`codex_eval_pass1.md`](audits/codex_eval_pass1.md) | Verdict: not yet fit to publish trustworthy, comparable headline benchmark numbers |
| [`codex_final_eval.md`](audits/codex_final_eval.md) | Verdict: offline action adaptation is supported; robust autonomous phone operation is not |
| [`codex_overnight_research.md`](audits/codex_overnight_research.md) | stop |
| [`codex_recovery_gate_audit.md`](audits/codex_recovery_gate_audit.md) | FIX BEFORE SWITCH |
| [`codex_v3_audit.md`](audits/codex_v3_audit.md) | NO-GO |
| [`codex_v4_data_audit.md`](audits/codex_v4_data_audit.md) | STOP |
| [`codex_v4_local_lane_audit.md`](audits/codex_v4_local_lane_audit.md) | FIX FIRST |
| [`codex_v4_pipeline_audit.md`](audits/codex_v4_pipeline_audit.md) | see report |
| [`codex_v4b_reaudit.md`](audits/codex_v4b_reaudit.md) | STOP |
| [`codex_verify_pass10.md`](audits/codex_verify_pass10.md) | NO-GO |
| [`codex_verify_pass11.md`](audits/codex_verify_pass11.md) | GO |
| [`codex_verify_pass3.md`](audits/codex_verify_pass3.md) | NO-GO |
| [`codex_verify_pass4.md`](audits/codex_verify_pass4.md) | NO-GO |
| [`codex_verify_pass5.md`](audits/codex_verify_pass5.md) | NO-GO |
| [`codex_verify_pass6.md`](audits/codex_verify_pass6.md) | NO-GO |
| [`codex_verify_pass7.md`](audits/codex_verify_pass7.md) | NO-GO |
| [`codex_verify_pass8.md`](audits/codex_verify_pass8.md) | NO-GO |
| [`codex_verify_pass9.md`](audits/codex_verify_pass9.md) | NO-GO |
| [`dataset_viability_v4.md`](audits/dataset_viability_v4.md) | Verdict  |
| [`dataset_viability.md`](audits/dataset_viability.md) | Verdict for this v2  |
| [`emu2_v3_promo_audit/report.md`](audits/emu2_v3_promo_audit__report.md) | Verdict: FIX — two P2 findings |
| [`v4_lane_reaudit/codex_v4_lane_reaudit.md`](audits/v4_lane_reaudit__codex_v4_lane_reaudit.md) | Verdict: FIX |
| [`v4_local_lane_audit/codex_v4_local_lane_audit.md`](audits/v4_local_lane_audit__codex_v4_local_lane_audit.md) | Verdict: FIX FIRST |
| [`v4_seed30_audit/report.md`](audits/v4_seed30_audit__report.md) | Verdict: FREEZE OK |
| [`round2_audit/report.md`](audits/round2_audit__report.md) | / Requested section / Verdict / Reason / |
| [`session_1118_audit/report.md`](audits/session_1118_audit__report.md) | / Section / Verdict / Main reason / |
| [`seed7_analysis_audit/report.md`](audits/seed7_analysis_audit__report.md) | Verdict: VALID WITH CAVEATS — as a preliminary, preregistered benchmark-checker result. The final recorded scores and retry substitutions reproduce. Seed 7 does |
| [`mw_r2_audit/report.md`](audits/mw_r2_audit__report.md) | Verdict: VALID WITH CAVEATS — the provisional 6/105 versus 22/105 scores and paired test are reproducible; environmental reporting needs correction, and the pla |
