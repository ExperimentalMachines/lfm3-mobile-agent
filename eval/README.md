# eval/

Benchmark harnesses. How each benchmark is run and kept fair: [docs/evaluation.md](../docs/evaluation.md).

| Folder | What |
|---|---|
| `androidcontrol/` | Offline step-level evaluation: `generate.py` (model → predictions), `score.py` / `score_dev.py` (scoring), `sop.py` (the multi-step own-history test, round 13) |
| `androidlens/` | `score_androidlens.py`: the long-task AndroidLens English splits (evaluation only) |
| `androidworld/` | The AndroidWorld agents (`lfm_agent.py` for ours, `guiowl_agent.py`, `maiui_agent.py` + `maiui_ref/` for the comparison models), the runner `run_aw.py`, summaries (`summarize_aw.py`, `paired_aw.py`, `failure_modes.py`), `app_resolver.py` (opt-in deployment-style `open_app` resolution), the round-12 done check (`replay_done_check.py`, `test_done_check.py`), and the two patches applied to AndroidWorld / android_env |
| `mobileworld/` | MobileWorld agents for our model and MAI-UI, and `bench_speed.py` (per-step speed on identical inputs) |
| `devicestream/` | Recording proxies for the phone speed benchmarks (symlinks into `train/` and `mobileworld/` for the shared agent code) |
| `general/` | General-knowledge retention check and its paired comparison |
