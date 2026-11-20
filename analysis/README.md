# analysis/

Scripts that compute the reported summaries from the files in [`results/`](../results/) (episode files, request logs,
predictions and per-run metric files).
Run them all with `bash analysis/reproduce.sh` (see [docs/reproduce.md](../docs/reproduce.md)).

| Script | Computes | Writes |
|---|---|---|
| `sealed_analysis.py` | Held-out AndroidWorld: preregistered primary analysis | `results/sealed_analysis_final.{json,md}` |
| `sealed_sensitivity.py` | Held-out AndroidWorld: sensitivity variants A–D, goal-varying subgroups E/F | `results/sealed_sensitivity_final.{json,md}` |
| `aw_dev_seed30.py` | AndroidWorld development seed 30: scores + Apple M5 speed | `results/androidworld/dev_seed30_summary.{json,md}` |
| `v4_gate.py` | v4 development gate (seed 30 + offline) | `results/v4_gate_seed30.txt` |
| `strict_dev_metrics.py` | v4 answer / complete dev metrics | `results/v4_dev/lfm3_v4_strict.json` |
| `v4rl_promotion.py` | v4-RL offline promotion rule | `results/v4rl_promotion_offline.json` |
| `build_report.py` | Offline AndroidControl + general-knowledge table | `results/SUMMARY.md` |
| `v2_compare.py` | v1 vs v2 offline comparison | `results/V2_COMPARISON.md` |
| `../eval/general/paired_retention.py` | v4 general-knowledge retention vs base | `results/general/lfm3vl2b_v4_retention_logprob.json` |
| `mw_summarize_r2.py` | MobileWorld scores and paired tests | `results/mobileworld/*_summary.json`, `mw_r2_comparison.{json,md}` |
| `bench_speed_report.py` | CPU speed benchmark | `results/speed/speed_t8.{json,md}` |
| `qdc_report_v6.py` | Phone speed (Qualcomm Device Cloud) | `results/qdc/speed_qdc_v6.{json,md}` |
| `devstream_report.py` | Phone speed (Pixel 9, partial) | `results/devstream/run_*/speed_phone_partial.{json,md}` |

`results/sealed_analysis_seed7*` are earlier interim outputs (seed 7 only), kept as the record of that stage.
