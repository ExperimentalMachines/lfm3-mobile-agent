# Repository notes

**Contents:** [Layout](#layout) · [2026-11-20 restructure](#2026-11-20-restructure) ·
[Secrets](#secrets-and-history-rewrites) · [Branches and tags](#branches-and-tags)

---

## Layout

| Path | What it holds | Edited after the fact? |
|---|---|---|
| `README.md`, `docs/*.md` | Documentation | Yes: kept current |
| `docs/PREREG_v4.md` | Preregistration + dated deviations | **No**: append-only record |
| `docs/research/` | Literature reviews (deep-research reports + notes) | Only dead links repaired |
| `analysis/` | Scripts that compute reported numbers | Yes |
| `train/`, `data/`, `eval/` | Training code, dataset builders, benchmark harnesses | Yes |
| `scripts/` | Run orchestration by purpose ([scripts/README.md](../scripts/README.md)) | Yes |
| `results/` | Raw results and computed summaries ([results/README.md](../results/README.md)) | Summaries are regenerated; raw files are not edited |
| `results/codex/` | Codex audit briefs, reports and evidence | No |
| `logs/` | Run logs kept as evidence ([logs/README.md](../logs/README.md)) | Only credential redaction |

Git-ignored local folders used by the scripts: `models/` (GGUF and merged weights), `tools/` (llama.cpp,
MobileWorld, Android SDK shims), `android_world/` (AndroidWorld clone), `.venv*`, raw MobileWorld trajectories.

---

## 2026-11-20 restructure

Goal: a layout a person can read. Nothing a reported number depends on was removed, and every analysis was re-run
with identical output ([reproduce.md](reproduce.md)).

**Everything moved or removed is still in git** at tag `archive/pre-restructure-2026-11-20`, at its original path:

```bash
git show archive/pre-restructure-2026-11-20:scripts/local_sealed_aw.sh
git ls-tree -r --name-only archive/pre-restructure-2026-11-20 logs/
```

Paths in `docs/PREREG_v4.md`, Codex reports and logs refer to the old layout. Use the tables below or the tag.

### Moved

| Destination | What | Files |
|---|---|---|
| `analysis/` | Scripts that compute reported numbers | 11 |
| `scripts/androidworld/` | AndroidWorld launchers, queues, re-runs, guards | 20 |
| `scripts/mobileworld/` | MobileWorld VMs, watchers, model servers | 13 |
| `scripts/training/` | Colab / Modal training and eval jobs | 32 |
| `scripts/training/jobs/` | Job configs (`jobs/*.json`) | 30 |
| `scripts/speed/` | CPU and phone speed benchmarks | 10 |
| `scripts/publish/` | GGUF export, merge check, Hugging Face upload | 6 |
| `docs/research/` | Research reports (from `reports/`) | 2 |
| `docs/research/notes/` | Research notes (from `research_notes/`) | 11 |
| `docs/` | History-rewrite record | 1 |

- Moved scripts had their internal paths, repository-root detection and process-matching patterns updated.
- Local launchers now find the repository from their own location instead of a hard-coded path.

<details>
<summary>Every moved file (old → new)</summary>

| Old path | New path |
|---|---|
| `scripts/bench_speed_report.py` | `analysis/bench_speed_report.py` |
| `scripts/build_report.py` | `analysis/build_report.py` |
| `scripts/devstream_report.py` | `analysis/devstream_report.py` |
| `scripts/mw_summarize_r2.py` | `analysis/mw_summarize_r2.py` |
| `scripts/qdc_report_v6.py` | `analysis/qdc_report_v6.py` |
| `scripts/sealed_analysis.py` | `analysis/sealed_analysis.py` |
| `scripts/sealed_sensitivity.py` | `analysis/sealed_sensitivity.py` |
| `scripts/strict_dev_metrics.py` | `analysis/strict_dev_metrics.py` |
| `scripts/v2_compare.py` | `analysis/v2_compare.py` |
| `scripts/v4_gate.py` | `analysis/v4_gate.py` |
| `scripts/v4rl_promotion.py` | `analysis/v4rl_promotion.py` |
| `scripts/aw_emu_guard.sh` | `scripts/androidworld/aw_emu_guard.sh` |
| `scripts/aw_watchdog.sh` | `scripts/androidworld/aw_watchdog.sh` |
| `scripts/local_450m_base_aw.sh` | `scripts/androidworld/local_450m_base_aw.sh` |
| `scripts/local_aw_lane.sh` | `scripts/androidworld/local_aw_lane.sh` |
| `scripts/local_aw_queue_v2.sh` | `scripts/androidworld/local_aw_queue_v2.sh` |
| `scripts/local_aw_rerun.sh` | `scripts/androidworld/local_aw_rerun.sh` |
| `scripts/local_emu2_fill_v2.sh` | `scripts/androidworld/local_emu2_fill_v2.sh` |
| `scripts/local_emu2_fill_v4.sh` | `scripts/androidworld/local_emu2_fill_v4.sh` |
| `scripts/local_forcethink_aw.sh` | `scripts/androidworld/local_forcethink_aw.sh` |
| `scripts/local_launch_450m_aw.sh` | `scripts/androidworld/local_launch_450m_aw.sh` |
| `scripts/local_lfm3_to_aw.sh` | `scripts/androidworld/local_lfm3_to_aw.sh` |
| `scripts/local_maiui_aw.sh` | `scripts/androidworld/local_maiui_aw.sh` |
| `scripts/local_qwen_to_aw.sh` | `scripts/androidworld/local_qwen_to_aw.sh` |
| `scripts/local_runtime_ablation_aw.sh` | `scripts/androidworld/local_runtime_ablation_aw.sh` |
| `scripts/local_sealed_aw_v2.sh` | `scripts/androidworld/local_sealed_aw_v2.sh` |
| `scripts/local_sealed_aw_v3.sh` | `scripts/androidworld/local_sealed_aw_v3.sh` |
| `scripts/local_sealed_queue.sh` | `scripts/androidworld/local_sealed_queue.sh` |
| `scripts/local_v2_to_aw.sh` | `scripts/androidworld/local_v2_to_aw.sh` |
| `scripts/local_v4_to_aw_v2.sh` | `scripts/androidworld/local_v4_to_aw_v2.sh` |
| `scripts/pause_sealed_arm.sh` | `scripts/androidworld/pause_sealed_arm.sh` |
| `scripts/aws_mw_launch.sh` | `scripts/mobileworld/aws_mw_launch.sh` |
| `scripts/aws_mw_setup.sh` | `scripts/mobileworld/aws_mw_setup.sh` |
| `scripts/check_maiui_server.py` | `scripts/mobileworld/check_maiui_server.py` |
| `scripts/colab2_mw_maiui_failover.py` | `scripts/mobileworld/colab2_mw_maiui_failover.py` |
| `scripts/colab2_upload_maiui.sh` | `scripts/mobileworld/colab2_upload_maiui.sh` |
| `scripts/colab_mw_maiui_q8.py` | `scripts/mobileworld/colab_mw_maiui_q8.py` |
| `scripts/colab_mw_models.sh` | `scripts/mobileworld/colab_mw_models.sh` |
| `scripts/gcp_mw_launch.sh` | `scripts/mobileworld/gcp_mw_launch.sh` |
| `scripts/gcp_mw_maiui_watch.sh` | `scripts/mobileworld/gcp_mw_maiui_watch.sh` |
| `scripts/gcp_mw_resume_vm.sh` | `scripts/mobileworld/gcp_mw_resume_vm.sh` |
| `scripts/gcp_mw_resume_watch.sh` | `scripts/mobileworld/gcp_mw_resume_watch.sh` |
| `scripts/mw_pull_r2.sh` | `scripts/mobileworld/mw_pull_r2.sh` |
| `scripts/mw_snapshot_r2.sh` | `scripts/mobileworld/mw_snapshot_r2.sh` |
| `scripts/chain_next_job.sh` | `scripts/training/chain_next_job.sh` |
| `scripts/colab_bootstrap.py` | `scripts/training/colab_bootstrap.py` |
| `scripts/colab_get_gpu.sh` | `scripts/training/colab_get_gpu.sh` |
| `scripts/colab_watchdog_v2.sh` | `scripts/training/colab_watchdog_v2.sh` |
| `scripts/gpu_session.sh` | `scripts/training/gpu_session.sh` |
| `scripts/launch_gpu_jobs.sh` | `scripts/training/launch_gpu_jobs.sh` |
| `scripts/launch_on_session.sh` | `scripts/training/launch_on_session.sh` |
| `scripts/make_v4_train_job.py` | `scripts/training/make_v4_train_job.py` |
| `scripts/modal_app.py` | `scripts/training/modal_app.py` |
| `scripts/move_08b_to_g4.sh` | `scripts/training/move_08b_to_g4.sh` |
| `scripts/move_2b_to_g4.sh` | `scripts/training/move_2b_to_g4.sh` |
| `scripts/provision_and_launch.sh` | `scripts/training/provision_and_launch.sh` |
| `scripts/v3_modal_chain.sh` | `scripts/training/v3_modal_chain.sh` |
| `scripts/v3_train_when_ready.sh` | `scripts/training/v3_train_when_ready.sh` |
| `scripts/v4_relaunch.sh` | `scripts/training/v4_relaunch.sh` |
| `scripts/vm_450m_pipeline.sh` | `scripts/training/vm_450m_pipeline.sh` |
| `scripts/vm_blocking_jobs.py` | `scripts/training/vm_blocking_jobs.py` |
| `scripts/vm_eval.sh` | `scripts/training/vm_eval.sh` |
| `scripts/vm_logprob_only.sh` | `scripts/training/vm_logprob_only.sh` |
| `scripts/vm_model_pipeline.sh` | `scripts/training/vm_model_pipeline.sh` |
| `scripts/vm_prepare_data.sh` | `scripts/training/vm_prepare_data.sh` |
| `scripts/vm_prepare_list.sh` | `scripts/training/vm_prepare_list.sh` |
| `scripts/vm_prepare_slice.sh` | `scripts/training/vm_prepare_slice.sh` |
| `scripts/vm_push_data.sh` | `scripts/training/vm_push_data.sh` |
| `scripts/vm_rl_go.sh` | `scripts/training/vm_rl_go.sh` |
| `scripts/vm_rl_hook.sh` | `scripts/training/vm_rl_hook.sh` |
| `scripts/vm_train.sh` | `scripts/training/vm_train.sh` |
| `scripts/vm_train_eval_push.sh` | `scripts/training/vm_train_eval_push.sh` |
| `scripts/vm_v3_intents.sh` | `scripts/training/vm_v3_intents.sh` |
| `scripts/vm_v4_teacher.sh` | `scripts/training/vm_v4_teacher.sh` |
| `scripts/vm_v4_teacher2.sh` | `scripts/training/vm_v4_teacher2.sh` |
| `scripts/wait_hub_step.py` | `scripts/training/wait_hub_step.py` |
| `scripts/jobs/general_logprob.logprob.json` | `scripts/training/jobs/general_logprob.logprob.json` |
| `scripts/jobs/lfm25vl450m_l4.json` | `scripts/training/jobs/lfm25vl450m_l4.json` |
| `scripts/jobs/lfm25vl450m_l4_v2.json` | `scripts/training/jobs/lfm25vl450m_l4_v2.json` |
| `scripts/jobs/lfm3_base_eval_l4.json` | `scripts/training/jobs/lfm3_base_eval_l4.json` |
| `scripts/jobs/lfm3_full_40g.json` | `scripts/training/jobs/lfm3_full_40g.json` |
| `scripts/jobs/lfm3_full_80g.json` | `scripts/training/jobs/lfm3_full_80g.json` |
| `scripts/jobs/lfm3_phase1_40g.json` | `scripts/training/jobs/lfm3_phase1_40g.json` |
| `scripts/jobs/lfm3_phase1_80g.json` | `scripts/training/jobs/lfm3_phase1_80g.json` |
| `scripts/jobs/lfm3_train_l4.json` | `scripts/training/jobs/lfm3_train_l4.json` |
| `scripts/jobs/lfm3_train_l4_resume.json` | `scripts/training/jobs/lfm3_train_l4_resume.json` |
| `scripts/jobs/lfm3_v2mix_g4.json` | `scripts/training/jobs/lfm3_v2mix_g4.json` |
| `scripts/jobs/lfm3_v2mix_g4_personal.json` | `scripts/training/jobs/lfm3_v2mix_g4_personal.json` |
| `scripts/jobs/lfm3_v3mix_modal.json` | `scripts/training/jobs/lfm3_v3mix_modal.json` |
| `scripts/jobs/lfm3_v4_a100.json` | `scripts/training/jobs/lfm3_v4_a100.json` |
| `scripts/jobs/modal_450m.json` | `scripts/training/jobs/modal_450m.json` |
| `scripts/jobs/modal_lfm3.json` | `scripts/training/jobs/modal_lfm3.json` |
| `scripts/jobs/qwen35_08b_g4.json` | `scripts/training/jobs/qwen35_08b_g4.json` |
| `scripts/jobs/qwen35_08b_l4.json` | `scripts/training/jobs/qwen35_08b_l4.json` |
| `scripts/jobs/qwen35_2b_g4.json` | `scripts/training/jobs/qwen35_2b_g4.json` |
| `scripts/jobs/qwen35_2b_l4.json` | `scripts/training/jobs/qwen35_2b_l4.json` |
| `scripts/jobs/qwen35_2b_v2mix_g4.json` | `scripts/training/jobs/qwen35_2b_v2mix_g4.json` |
| `scripts/jobs/qwen35_2b_v2mix_g4_personal.json` | `scripts/training/jobs/qwen35_2b_v2mix_g4_personal.json` |
| `scripts/jobs/qwen_logprob_g4b.json` | `scripts/training/jobs/qwen_logprob_g4b.json` |
| `scripts/jobs/v3_build.build.json` | `scripts/training/jobs/v3_build.build.json` |
| `scripts/jobs/v3_intents.intents.json` | `scripts/training/jobs/v3_intents.intents.json` |
| `scripts/jobs/v3_intents_g4b.json` | `scripts/training/jobs/v3_intents_g4b.json` |
| `scripts/jobs/v3_intents_l4b.json` | `scripts/training/jobs/v3_intents_l4b.json` |
| `scripts/jobs/v4_teacher.json` | `scripts/training/jobs/v4_teacher.json` |
| `scripts/jobs/v4_teacher2.json` | `scripts/training/jobs/v4_teacher2.json` |
| `scripts/jobs/v4_teacher_smoke.json` | `scripts/training/jobs/v4_teacher_smoke.json` |
| `scripts/android_cli.sh` | `scripts/speed/android_cli.sh` |
| `scripts/bench_speed.sh` | `scripts/speed/bench_speed.sh` |
| `scripts/devstream_chain_v3.sh` | `scripts/speed/devstream_chain_v3.sh` |
| `scripts/devstream_device_v4.sh` | `scripts/speed/devstream_device_v4.sh` |
| `scripts/devstream_device_v5.sh` | `scripts/speed/devstream_device_v5.sh` |
| `scripts/devstream_device_v6.sh` | `scripts/speed/devstream_device_v6.sh` |
| `scripts/devstream_keeper_v3.sh` | `scripts/speed/devstream_keeper_v3.sh` |
| `scripts/qdc_chain.sh` | `scripts/speed/qdc_chain.sh` |
| `scripts/qdc_chain2.sh` | `scripts/speed/qdc_chain2.sh` |
| `scripts/qdc_tunnel_keeper.sh` | `scripts/speed/qdc_tunnel_keeper.sh` |
| `scripts/check_local_merge.py` | `scripts/publish/check_local_merge.py` |
| `scripts/hf_publish_v4.py` | `scripts/publish/hf_publish_v4.py` |
| `scripts/local_export_gguf.sh` | `scripts/publish/local_export_gguf.sh` |
| `scripts/publish_hf.py` | `scripts/publish/publish_hf.py` |
| `scripts/publish_v2_hf.py` | `scripts/publish/publish_v2_hf.py` |
| `scripts/publish_v3_hf.py` | `scripts/publish/publish_v3_hf.py` |
| `reports/Beating GUI Owl at 2B fairly.md` | `docs/research/beating-gui-owl-at-2b-fairly.md` |
| `reports/Small GUI agent training methods.md` | `docs/research/small-gui-agent-training-methods.md` |
| `research_notes/Beating GUI Owl at 2B fairly/data_and_environments.md` | `docs/research/notes/beating-gui-owl-at-2b-fairly/data_and_environments.md` |
| `research_notes/Beating GUI Owl at 2B fairly/fair_evaluation.md` | `docs/research/notes/beating-gui-owl-at-2b-fairly/fair_evaluation.md` |
| `research_notes/Beating GUI Owl at 2B fairly/gui_owl_recipe.md` | `docs/research/notes/beating-gui-owl-at-2b-fairly/gui_owl_recipe.md` |
| `research_notes/Beating GUI Owl at 2B fairly/input_inference_harness.md` | `docs/research/notes/beating-gui-owl-at-2b-fairly/input_inference_harness.md` |
| `research_notes/Beating GUI Owl at 2B fairly/peer_small_models.md` | `docs/research/notes/beating-gui-owl-at-2b-fairly/peer_small_models.md` |
| `research_notes/Beating GUI Owl at 2B fairly/training_tunables.md` | `docs/research/notes/beating-gui-owl-at-2b-fairly/training_tunables.md` |
| `research_notes/Small GUI agent training methods/architecture_hparams.md` | `docs/research/notes/small-gui-agent-training-methods/architecture_hparams.md` |
| `research_notes/Small GUI agent training methods/offline_rft.md` | `docs/research/notes/small-gui-agent-training-methods/offline_rft.md` |
| `research_notes/Small GUI agent training methods/online_rl.md` | `docs/research/notes/small-gui-agent-training-methods/online_rl.md` |
| `research_notes/Small GUI agent training methods/rl_infrastructure.md` | `docs/research/notes/small-gui-agent-training-methods/rl_infrastructure.md` |
| `research_notes/Small GUI agent training methods/self_improvement_data.md` | `docs/research/notes/small-gui-agent-training-methods/self_improvement_data.md` |
| `docs/HISTORY_REWRITE_20261119.md` | `docs/history-rewrites.md` |

</details>

### Removed

| Removed | Why |
|---|---|
| `scripts/build_runs_registry.py` | Run-log site generator (replaced by the static docs; its seed-30 computation moved to `analysis/aw_dev_seed30.py`) |
| `scripts/colab_keepalive_loop.sh` | Session keep-alive helper |
| `scripts/colab_poll_fast_gpu.sh` | GPU polling helper |
| `scripts/colab_watchdog.sh` | Superseded by `scripts/training/colab_watchdog_v2.sh` |
| `scripts/devstream_chain.sh` | Superseded by `scripts/speed/devstream_chain_v3.sh` |
| `scripts/devstream_chain_v2.sh` | Superseded by `scripts/speed/devstream_chain_v3.sh` |
| `scripts/devstream_device.sh` | Superseded by `scripts/speed/devstream_device_v4.sh` |
| `scripts/devstream_device_v2.sh` | Superseded by `scripts/speed/devstream_device_v4.sh` |
| `scripts/devstream_device_v3.sh` | Superseded by `scripts/speed/devstream_device_v4.sh` |
| `scripts/devstream_keeper.sh` | Superseded by `scripts/speed/devstream_keeper_v3.sh` |
| `scripts/devstream_keeper_v2.sh` | Superseded by `scripts/speed/devstream_keeper_v3.sh` |
| `scripts/docs_refresh_loop.sh` | Run-log site generator |
| `scripts/gen_timeline_audits.py` | Run-log site generator |
| `scripts/local_emu1_queue.sh` | One-off emulator-1 queue for 2026-11-18; superseded by `local_sealed_queue.sh` |
| `scripts/local_emu2_fill.sh` | First emulator-2 filler; replaced by `local_emu2_fill_v2.sh` (its resume-directory bug is fixed there) |
| `scripts/local_emu2_fill_v3.sh` | Superseded by `local_emu2_fill_v4.sh` (identical except the launcher version) |
| `scripts/local_milestone_poll.sh` | Progress polling helper |
| `scripts/local_sealed_aw.sh` | First sealed launcher (ran the seed-7 v1 and GUI-Owl arms); superseded by v2/v3 |
| `scripts/local_v4_to_aw.sh` | Superseded by `local_v4_to_aw_v2.sh` (the hub upload it waited for failed) |
| `scripts/local_watch_base_eval.sh` | One-off watcher (pointed at a temporary session folder) |
| `scripts/local_watch_base_eval_only.sh` | One-off watcher (pointed at a temporary session folder) |
| `scripts/refresh_partial_aw.sh` | Progress summaries of unfinished runs |
| `scripts/update_runs_docs.sh` | Run-log site generator |
| `scripts/wait_v3_or_aw.sh` | Progress polling helper |
| `STATUS.md` | Rewritten as `README.md` |
| `docs/DATASETS_AND_SPLITS.md` | Rewritten as `docs/datasets.md` |
| `docs/DATA_V2_PLAN.md` | Rewritten as `docs/datasets.md`, `docs/models.md` |
| `docs/EVAL_PROTOCOL.md` | Rewritten as `docs/evaluation.md` |
| `docs/GUI_OWL_LESSONS.md` | Rewritten as `docs/evaluation.md` |
| `models/v2_adapters/README.md` | Rewritten as `docs/models.md` |
| `logs/` (58 files) | Operational logs: session launches, keep-alive, GPU polling, tunnel and stop markers, smoke tests, instance files with VM addresses |
| `results/codex/datasets_scratch/` (224 files, 354 MB) | Public papers and licence pages Codex downloaded for the dataset-viability audit |
| `results/vm_backup/` (36 files) | Byte-identical copies of files kept in `results/v4_dev/` and `results/v4rl_dev/` |

### Added

| File | Why |
|---|---|
| `analysis/aw_dev_seed30.py` → `results/androidworld/dev_seed30_summary.*` | Seed-30 scores and Apple M5 speed, previously computed only by the removed run-log generator |
| `analysis/reproduce.sh` | One command to regenerate and check every summary |
| `data/meta/androidworld_task_metadata.json` | AndroidWorld's task list and difficulty (from `55ddaf5`, Apache-2.0), so the analysis runs without an AndroidWorld checkout |
| `results/general/lfm3vl2b_v4_retention_logprob.json` | v4's paired general-knowledge test |
| Rows E/F in `results/sealed_sensitivity_final.*` | The preregistered goal-varying subgroup, as a computed result |
| `README.md` files in `analysis/`, `scripts/`, `results/`, `logs/`, `docs/research/`, `data/meta/` | Folder guides |

---

## Secrets and history rewrites

| Date | What leaked into a run log | Fix |
|---|---|---|
| 2026-11-19 | Environment variables printed by AndroidWorld's setup (an API key, a session token) | Redacted in every commit (`git filter-branch`) |
| 2026-11-20 | An expired Colab file-proxy token inside a download URL | Redacted in every commit (`git filter-branch`) |

- **Hash maps:** old → new commit hashes are in [history-rewrites.md](history-rewrites.md).
- **Scan:** two independent scans (ours and Codex's) found no credentials. They covered every file in every commit
  reachable from `main` and the archive tag, including compressed episode files.
  - Checked: cloud keys, Hugging Face / OpenAI / Anthropic / GitHub / Google / Modal tokens, private keys, JWTs and
    key/token/secret/password assignments.
  - Not checked: images (no OCR).
- **Owner identity:** the owner's git e-mail appears in commit author fields and in Codex logs that captured `git log`.
- **Automatic redaction on commit (limited).** `.gitattributes` runs the `redact-env` clean filter on `*.log` files
  only, and only where it is configured locally:
  - It redacts `'NAME_WITH_KEY|TOKEN|SECRET|PASSWORD': '…'` pairs (the format AndroidWorld prints) and JWT-shaped
    tokens.
  - It does **not** catch other formats (e.g. `HF_TOKEN=…`, lowercase JSON keys).
  - Run a scan before publishing. One-time setup:

```bash
git config filter.redact-env.clean "LC_ALL=C sed -E -e \"s/'([A-Z0-9_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)': '[^']*'/'\\\\1': '<redacted>'/g\" -e 's/eyJ[A-Za-z0-9_-]{15,}[.]eyJ[A-Za-z0-9_-]{15,}[.][A-Za-z0-9_-]{10,}/<redacted-token>/g'"
git config filter.redact-env.smudge cat
```

---

## Branches and tags

| Ref | What |
|---|---|
| `main` | This repository |
| `lfm3-android` | Same commit as `main` (the branch name used while the project ran); its pre-rewrite history was replaced |
| tag `archive/pre-restructure-2026-11-20` | Snapshot before the restructure (after the token redaction) |
| `main` history before the merge | An auto-generated run-log site (2026-11-18 to 11-19), superseded by `docs/` |
