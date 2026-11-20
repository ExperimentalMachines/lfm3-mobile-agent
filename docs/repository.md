# Repository notes

**Contents:** [Layout](#layout) · [2026-11-20 restructure](#2026-11-20-restructure) ·
[Secrets](#secrets-and-history-rewrites) · [Branches and tags](#branches-and-tags)

---

## Layout

| Path | What it holds | Edited after the fact? |
|---|---|---|
| `README.md`, `docs/*.md` | Documentation | Yes: kept current |
| `docs/PREREG_v4.md` | Preregistration + dated deviations | **No**: append-only record |
| `docs/research/` | Literature reviews (deep-research reports + notes) | No |
| `analysis/` | Scripts that compute reported numbers | Yes |
| `train/`, `data/`, `eval/` | Training code, dataset builders, benchmark harnesses | Yes |
| `scripts/` | Run orchestration by purpose ([scripts/README.md](../scripts/README.md)) | Yes |
| `results/` | Raw results and computed summaries ([results/README.md](../results/README.md)) | Summaries are regenerated, raw files never edited |
| `results/codex/` | Codex audit briefs, reports and evidence | No |
| `logs/` | Run logs kept as evidence ([logs/README.md](../logs/README.md)) | No |

Git-ignored local folders used by the scripts: `models/` (GGUF and merged weights), `tools/` (llama.cpp,
MobileWorld, Android SDK shims), `android_world/` (AndroidWorld clone), `.venv*`, raw MobileWorld trajectories.

---

## 2026-11-20 restructure

Goal: a layout a person can read. Nothing that a reported number depends on was removed; every analysis was re-run
afterwards with identical output ([reproduce.md](reproduce.md)).

**Everything removed or moved is still in git** at tag `archive/pre-restructure-2026-11-20`, at its original path:

```bash
git show archive/pre-restructure-2026-11-20:scripts/local_sealed_aw_v2.sh
git ls-tree -r --name-only archive/pre-restructure-2026-11-20 logs/
```

Paths in `docs/PREREG_v4.md`, Codex reports and logs refer to the old layout. Use the tables below or the tag.

### Moved scripts

| Was in `scripts/` | Now in |
|---|---|
| `bench_speed_report.py`, `build_report.py`, `devstream_report.py`, `mw_summarize_r2.py`, `qdc_report_v6.py`, `sealed_analysis.py`, `sealed_sensitivity.py`, `strict_dev_metrics.py`, `v2_compare.py`, `v4_gate.py`, `v4rl_promotion.py` | `analysis/` |
| `aw_emu_guard.sh`, `aw_watchdog.sh`, `local_450m_base_aw.sh`, `local_aw_lane.sh`, `local_aw_queue_v2.sh`, `local_aw_rerun.sh`, `local_emu2_fill_v4.sh`, `local_forcethink_aw.sh`, `local_launch_450m_aw.sh`, `local_lfm3_to_aw.sh`, `local_maiui_aw.sh`, `local_qwen_to_aw.sh`, `local_runtime_ablation_aw.sh`, `local_sealed_aw_v3.sh`, `local_sealed_queue.sh`, `local_v2_to_aw.sh`, `local_v4_to_aw_v2.sh`, `pause_sealed_arm.sh` | `scripts/androidworld/` |
| `aws_mw_launch.sh`, `aws_mw_setup.sh`, `check_maiui_server.py`, `colab2_mw_maiui_failover.py`, `colab2_upload_maiui.sh`, `colab_mw_maiui_q8.py`, `colab_mw_models.sh`, `gcp_mw_launch.sh`, `gcp_mw_maiui_watch.sh`, `gcp_mw_resume_vm.sh`, `gcp_mw_resume_watch.sh`, `mw_pull_r2.sh`, `mw_snapshot_r2.sh` | `scripts/mobileworld/` |
| `jobs/*.json` (30 files) | `scripts/training/jobs/` |
| `chain_next_job.sh`, `colab_bootstrap.py`, `colab_get_gpu.sh`, `colab_watchdog_v2.sh`, `gpu_session.sh`, `launch_gpu_jobs.sh`, `launch_on_session.sh`, `make_v4_train_job.py`, `modal_app.py`, `move_08b_to_g4.sh`, `move_2b_to_g4.sh`, `provision_and_launch.sh`, `v3_modal_chain.sh`, `v3_train_when_ready.sh`, `v4_relaunch.sh`, `vm_450m_pipeline.sh`, `vm_blocking_jobs.py`, `vm_eval.sh`, `vm_logprob_only.sh`, `vm_model_pipeline.sh`, `vm_prepare_data.sh`, `vm_prepare_list.sh`, `vm_prepare_slice.sh`, `vm_push_data.sh`, `vm_rl_go.sh`, `vm_rl_hook.sh`, `vm_train.sh`, `vm_train_eval_push.sh`, `vm_v3_intents.sh`, `vm_v4_teacher.sh`, `vm_v4_teacher2.sh`, `wait_hub_step.py` | `scripts/training/` |
| `android_cli.sh`, `bench_speed.sh`, `devstream_chain_v3.sh`, `devstream_device_v4.sh`, `devstream_device_v5.sh`, `devstream_device_v6.sh`, `devstream_keeper_v3.sh`, `qdc_chain.sh`, `qdc_chain2.sh`, `qdc_tunnel_keeper.sh` | `scripts/speed/` |
| `check_local_merge.py`, `hf_publish_v4.py`, `local_export_gguf.sh`, `publish_hf.py`, `publish_v2_hf.py`, `publish_v3_hf.py` | `scripts/publish/` |

Each moved script's internal paths, repository-root detection and process-matching patterns were updated.

### Other moves

| Was | Now |
|---|---|
| `docs/HISTORY_REWRITE_20261119.md` | `docs/history-rewrites.md` |
| `reports/Beating GUI Owl at 2B fairly.md` | `docs/research/beating-gui-owl-at-2b-fairly.md` |
| `reports/Small GUI agent training methods.md` | `docs/research/small-gui-agent-training-methods.md` |
| `research_notes/<topic>/*.md` | `docs/research/notes/<topic>/*.md` |

### Removed

| Removed script | Why |
|---|---|
| `scripts/build_runs_registry.py` | run-log site generator (replaced by the static docs) |
| `scripts/colab_keepalive_loop.sh` | session keep-alive helper (no results depend on it) |
| `scripts/colab_poll_fast_gpu.sh` | GPU polling helper (no results depend on it) |
| `scripts/colab_watchdog.sh` | superseded by scripts/training/colab_watchdog_v2.sh |
| `scripts/devstream_chain.sh` | superseded by scripts/speed/devstream_chain_v3.sh |
| `scripts/devstream_chain_v2.sh` | superseded by scripts/speed/devstream_chain_v3.sh |
| `scripts/devstream_device.sh` | superseded by scripts/speed/devstream_device_v4.sh |
| `scripts/devstream_device_v2.sh` | superseded by scripts/speed/devstream_device_v4.sh |
| `scripts/devstream_device_v3.sh` | superseded by scripts/speed/devstream_device_v4.sh |
| `scripts/devstream_keeper.sh` | superseded by scripts/speed/devstream_keeper_v3.sh |
| `scripts/devstream_keeper_v2.sh` | superseded by scripts/speed/devstream_keeper_v3.sh |
| `scripts/docs_refresh_loop.sh` | run-log site generator (replaced by the static docs) |
| `scripts/gen_timeline_audits.py` | run-log site generator (replaced by the static docs) |
| `scripts/local_emu1_queue.sh` | one-off emulator-1 queue for 2026-11-18 (superseded by local_sealed_queue.sh) |
| `scripts/local_emu2_fill.sh` | superseded by scripts/androidworld/local_emu2_fill_v4.sh |
| `scripts/local_emu2_fill_v2.sh` | superseded by scripts/androidworld/local_emu2_fill_v4.sh |
| `scripts/local_emu2_fill_v3.sh` | superseded by scripts/androidworld/local_emu2_fill_v4.sh |
| `scripts/local_milestone_poll.sh` | progress polling helper (no results depend on it) |
| `scripts/local_sealed_aw.sh` | superseded by scripts/androidworld/local_sealed_aw_v3.sh (it ran the seed-7 v1 and GUI-Owl arms) |
| `scripts/local_sealed_aw_v2.sh` | superseded by scripts/androidworld/local_sealed_aw_v3.sh (it ran the sealed arms started on 2026-11-18 before v3; see PREREG 02:45) |
| `scripts/local_v4_to_aw.sh` | superseded by scripts/androidworld/local_v4_to_aw_v2.sh |
| `scripts/local_watch_base_eval.sh` | one-off watcher (no results depend on it) |
| `scripts/local_watch_base_eval_only.sh` | one-off watcher (no results depend on it) |
| `scripts/refresh_partial_aw.sh` | progress summaries of unfinished runs (no results depend on it) |
| `scripts/update_runs_docs.sh` | run-log site generator (replaced by the static docs) |
| `scripts/wait_v3_or_aw.sh` | progress polling helper (no results depend on it) |

| Removed doc | Replaced by |
|---|---|
| `STATUS.md` | replaced by README.md |
| `docs/DATASETS_AND_SPLITS.md` | rewritten as docs/datasets.md |
| `docs/DATA_V2_PLAN.md` | superseded plan; outcome in docs/models.md and docs/datasets.md |
| `docs/EVAL_PROTOCOL.md` | rewritten as docs/evaluation.md |
| `docs/GUI_OWL_LESSONS.md` | folded into docs/evaluation.md |
| `models/v2_adapters/README.md` | folded into docs/models.md |

Also removed:
- 58 operational logs (Colab session launches, keep-alive, GPU polling, tunnel and stop markers, smoke tests,
  instance files with VM addresses).
- 224 files in `results/codex/datasets_scratch/` (354 MB of public papers and licence pages that Codex downloaded
  for the dataset-viability audit).

### Added

| File | Why |
|---|---|
| `analysis/aw_dev_seed30.py` → `results/androidworld/dev_seed30_summary.*` | Seed-30 scores and Apple M5 speed were computed by the removed run-log generator; same computation, now reproducible here |
| `analysis/reproduce.sh` | One command to recompute and check every number |
| `README.md` files in `analysis/`, `scripts/`, `results/`, `logs/`, `docs/research/` | Folder guides |

---

## Secrets and history rewrites

| Date | What leaked into a run log | Fix |
|---|---|---|
| 2026-11-19 | Environment variables printed by AndroidWorld's setup (an API key, a session token) | Redacted in every commit (`git filter-branch`) |
| 2026-11-20 | An expired Colab file-proxy token inside a download URL | Redacted in every commit (`git filter-branch`) |

- Old → new commit hashes: [history-rewrites.md](history-rewrites.md).
- A scan of every file in every pushed commit (including compressed episode files) finds no credentials. It
  checked cloud keys, Hugging Face / OpenAI / Anthropic / GitHub / Google / Modal tokens, private keys, JWTs and
  `*_KEY`/`*_TOKEN`/`*_SECRET`/`*_PASSWORD` values.
- New log commits are redacted automatically: `.gitattributes` applies the `redact-env` clean filter to `*.log`.
  It needs a one-time local setup:

```bash
git config filter.redact-env.clean "LC_ALL=C sed -E -e \"s/'([A-Z0-9_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)': '[^']*'/'\\\\1': '<redacted>'/g\" -e 's/eyJ[A-Za-z0-9_-]{15,}[.]eyJ[A-Za-z0-9_-]{15,}[.][A-Za-z0-9_-]{10,}/<redacted-token>/g'"
git config filter.redact-env.smudge cat
```

---

## Branches and tags

| Ref | What |
|---|---|
| `main` | This repository |
| `lfm3-android` | Same commit as `main` (the branch name used while the project ran) |
| tag `archive/pre-restructure-2026-11-20` | Snapshot before the restructure |
| `main` history before the merge | An auto-generated run-log site (2026-11-18 to 11-19), superseded by `docs/` |
