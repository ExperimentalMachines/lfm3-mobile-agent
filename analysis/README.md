# analysis/

Scripts that compute the reported summaries from the files in [`results/`](../results/) (episode files, request logs,
predictions and per-run metric files).
Run them all with `bash analysis/reproduce.sh` (see [docs/reproduce.md](../docs/reproduce.md)).

| Script | Computes | Writes |
|---|---|---|
| `sealed_analysis.py` | Held-out AndroidWorld: preregistered primary analysis | `results/sealed_analysis_final.{json,md}` |
| `sealed_sensitivity.py` | Held-out AndroidWorld: sensitivity variants A–D, goal-varying subgroups E/F | `results/sealed_sensitivity_final.{json,md}` |
| `aw_dev_seed30.py` | AndroidWorld development seed 30: scores + Apple M5 speed | `results/androidworld/dev_seed30_summary.{json,md}` |
| `main_gate.py` | Main development gate (seed 30 + offline) | `results/v4_gate_seed30.txt` |
| `strict_dev_metrics.py` | Main answer / complete dev metrics | `results/v4_dev/lfm3_v4_strict.json` |
| `grpo_promotion.py` | GRPO offline promotion rule | `results/v4rl_promotion_offline.json` |
| `build_report.py` | Offline AndroidControl + general-knowledge table | `results/SUMMARY.md` |
| `multisource_vs_androidcontrolonly.py` | AndroidControlOnly vs MultiSource offline comparison | `results/V2_COMPARISON.md` |
| `../eval/general/paired_retention.py` | Main general-knowledge retention vs base | `results/general/lfm3vl2b_v4_retention_logprob.json` |
| `mw_summarize_r2.py` | MobileWorld scores and paired tests | `results/mobileworld/*_summary.json`, `mw_r2_comparison.{json,md}` |
| `bench_speed_report.py` | CPU speed benchmark | `results/speed/speed_t8.{json,md}` |
| `qdc_report.py` | Phone speed (Qualcomm Device Cloud) | `results/qdc/speed_qdc_v6.{json,md}` |
| `devstream_report.py` | Phone speed (Pixel 9, partial) | `results/devstream/run_*/speed_phone_partial.{json,md}` |

`results/sealed_analysis_seed7*` are earlier interim outputs (seed 7 only), kept as the record of that stage.

## Development rounds (run by hand)

Not run by `reproduce.sh`. The AndroidWorld scripts print JSON lines; run them with
`.venv-aw/bin/python -I analysis/<script>.py results/androidworld/<run> ...`.

| Script | Computes | Writes |
|---|---|---|
| `aw_paired_flips.py` | Paired seed-30 comparison against a reference run (first argument): successes, flips, net gain, exact McNemar p; also on tasks neither run crashed | Prints |
| `aw_false_complete.py` | Successes, exceptions and false `complete`s per run (the failure taxonomy's definition) | Prints |
| `mw_summarize_r3.py` | MobileWorld follow-up run (OwnHistory) vs run 2's models, loop metrics | `results/mobileworld/mw_r3_comparison.{json,md}`, `v42_gui_en_r3_summary.json` |
| [`failure_analysis/`](failure_analysis/) | Failure taxonomy, paired task changes, loss curves, latency ([its guide](failure_analysis/README.md)) | A temp folder (committed copy: `results/androidworld/failure_taxonomy_20261122.json`) |
| `aw_outcomes.py` | Full outcome accounting of AndroidWorld runs (round 14): success, unfinished `complete` claims, wrong answers, budget exhaustion, exceptions; paired done-check yield | Prints |
| `sop_validation.py` | Does the multi-step own-history test (SOP) rank the models like AndroidWorld? Spearman ρ over seven models (round 13) | `--out` prefix (`.json`, `.md`) |
| `mw_summarize_counterfactual.py` | MobileWorld run of `-Counterfactual` vs run 2's models | `results/mobileworld/mw_e_comparison.{json,md}` |
| `mw_summarize_r3.py`, `mw_summarize_r2.py` | See above | |
| [`done_audit/`](done_audit/README.md) | Round 8–12 label audits: the "done" judges, wait audits, history probes, review sheets | Files in `results/v46_dev/`, `v47_dev/`, `v48_dev/`, `r1*_dev/` |
| [`diagnosis_20261123/`](diagnosis_20261123/README.md) | The 2026-11-23 step-count diagnosis | `results/diagnosis_20261123/` |

Names in the output files are the labels in use when they were written; see [docs/naming.md](../docs/naming.md#records-keep-the-old-names).
