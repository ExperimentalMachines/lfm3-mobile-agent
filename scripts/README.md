# scripts/

Orchestration: how the runs were launched, watched and published. Scripts that **compute** results are in
[`../analysis/`](../analysis/).

Notes:
- Most scripts drove a specific machine or cloud session that no longer exists.
- Local launchers find the repository from their own location; scripts that run on a VM use that VM's paths.
- Superseded versions are kept at tag `archive/pre-restructure-2026-11-20` ([docs/repository.md](../docs/repository.md)).

## androidworld/ — AndroidWorld runs on the Mac's two emulators

| Script | Does |
|---|---|
| `local_sealed_aw_v3.sh` | **Runs one held-out arm** (model × seed) with the preregistered flags; results stay sealed |
| `local_sealed_queue.sh` | Queues the remaining held-out arms on one emulator |
| `local_aw_rerun.sh` | The preregistered single re-run of setup-crash episodes |
| `aw_emu_guard.sh` | Kills a run before a crash is recorded if the emulator stops answering |
| `local_aw_queue_v2.sh`, `local_aw_lane.sh` | Queue / resume one emulator's jobs (e.g. after a reboot) |
| `pause_sealed_arm.sh` | Pauses a sealed arm so it can resume later |
| `local_emu2_fill_v2.sh` | Emulator-2 hand-off (2026-11-18): pauses the GUI-Owl seed-1234 arm when v4 is exported, resumes it after v4's seed-30 run |
| `local_emu2_fill_v4.sh` | Emulator-2 schedule after that: v4 seed-30 pass → gate → held-out arm → resume the paused arm |
| `local_v4_to_aw_v2.sh` | v4 hand-off: merged weights → GGUF → seed-30 run |
| `local_lfm3_to_aw.sh`, `local_v2_to_aw.sh`, `local_qwen_to_aw.sh` | Earlier models: wait for weights → GGUF → seed-30 run |
| `local_maiui_aw.sh` | MAI-UI-2B seed-30 run (8-bit) |
| `local_forcethink_aw.sh`, `local_runtime_ablation_aw.sh` | Inference-only ablations (forced intent, runtime feedback) |
| `local_launch_450m_aw.sh`, `local_450m_base_aw.sh` | LFM2.5-VL-450M seed-30 runs |
| `aw_watchdog.sh` | Kills hung child processes of a run |
| `local_v41_dev_aw.sh` | Follow-up rounds: one seed-30 pass per variant (A–E, the v4.2 replicate R, round-5 P / Q = P2 / S) |

## mobileworld/ — MobileWorld on cloud VMs

| Script | Does |
|---|---|
| `gcp_mw_launch.sh` | Creates the GCP VM with nested virtualisation |
| `gcp_mw_resume_vm.sh` | **Runs on the VM:** finishes a run under the preregistered completion rule |
| `gcp_mw_resume_watch.sh`, `gcp_mw_maiui_watch.sh` | Mac-side watchers: restart the VM / containers and resume after stops or preemptions |
| `colab_mw_models.sh` | Serves GUI-Owl and MAI-UI on a Colab GPU (same llama.cpp build and flags) |
| `colab_mw_maiui_q8.py`, `colab2_mw_maiui_failover.py`, `colab2_upload_maiui.sh` | MAI-UI 8-bit server and its failover session |
| `check_maiui_server.py` | Verifies the server behind the tunnel is the right model, build and context |
| `mw_pull_r2.sh`, `mw_snapshot_r2.sh` | Pull trajectories / live counts from the VM |
| `aws_mw_launch.sh`, `aws_mw_setup.sh` | AWS host for MobileWorld run 1 (discarded) |
| `mw_v41_vm_setup.sh` | Follow-up run 3: creates and prepares the environment VM, same environment as run 2 |
| `colab_mw_v41_server.sh` | **Runs on Colab:** serves the selected LFM3 GGUF with run 2's server flags through a restricted tunnel |
| `gcp_mw_v41_watch.sh` | Mac-side watcher for run 3 (run 2's restart-and-resume logic) |
| `mw_pull_r3.sh` | Pull run 3's trajectories to `results/mobileworld/traj_r3/` |
| `colab_keepalive_loop.sh` | Keeps a Colab model-server session from idling out |

## training/ — GPU jobs on Colab and Modal

| Script | Does |
|---|---|
| `jobs/*.json` | **Job configs:** model, dataset revision, steps, LoRA, evals |
| `vm_model_pipeline.sh` | **Runs on the GPU:** train → evaluate → push, each step skipped if already done |
| `vm_train.sh`, `vm_eval.sh`, `vm_train_eval_push.sh`, `vm_logprob_only.sh` | Single stages of the pipeline |
| `vm_prepare_*.sh`, `vm_push_data.sh` | Build and push the AndroidControl parquet |
| `vm_v3_intents.sh`, `vm_v4_teacher.sh`, `vm_v4_teacher2.sh` | Teacher-model labelling for v3 / v4 data |
| `vm_rl_go.sh`, `vm_rl_hook.sh` | v4-RL (GRPO) job |
| `vm_450m_pipeline.sh` | LFM2.5-VL-450M pipeline |
| `modal_app.py` | Same pipeline on Modal |
| `gpu_session.sh`, `colab_bootstrap.py` | Upload code to a Colab session and install pinned packages |
| `launch_gpu_jobs.sh`, `launch_on_session.sh`, `provision_and_launch.sh`, `chain_next_job.sh` | Start jobs in a session |
| `vm_blocking_jobs.py` | Runs a job list inside a Colab kernel cell |
| `make_v4_train_job.py`, `v3_modal_chain.sh`, `v3_train_when_ready.sh`, `v4_relaunch.sh` | Version-specific launch / recovery |
| `colab_get_gpu.sh`, `colab_watchdog_v2.sh`, `move_*_to_g4.sh`, `wait_hub_step.py` | Get a GPU, restart a lost VM, move a run between GPUs |
| `vm_v41_pipeline.sh` | **v4.1:** rebuilds the v4.1 data (`data/v41_build_parquet.py`), then the unchanged v4 pipeline |
| `vm_v42_pipeline.sh` | **v4.2:** replays training episodes with the model's own history (`data/v42_selfhist.py`), then the v4 pipeline |
| `vm_v5_pipeline.sh` | **Round 5:** rebuilds v4.2's data, DPO pairs from own mistakes (`data/v5_pairs.py`, `train/dpo_vlm.py`), more SFT, offline gates |
| `vm_finish_merge.py` | Finishes a run whose final Hub push failed: merge + receipt, exactly as `sft_vlm.py` |

## speed/ — speed benchmarks

| Script | Does |
|---|---|
| `bench_speed.sh` | CPU benchmark on the idle VM |
| `qdc_chain.sh`, `qdc_chain2.sh` | Phone benchmark on Qualcomm Device Cloud (rounds 1 and 2) |
| `devstream_device_v5.sh`, `devstream_device_v6.sh` | One phone's benchmark over a remote adb server (used by the QDC chains) |
| `qdc_tunnel_keeper.sh` | Keeps the QDC tunnel alive |
| `devstream_chain_v3.sh`, `devstream_device_v4.sh`, `devstream_keeper_v3.sh`, `android_cli.sh` | Pixel 9 attempt via Firebase device streaming |

## publish/ — export and release

| Script | Does |
|---|---|
| `local_export_gguf.sh` | Merged model → phone GGUF (4-bit) |
| `check_local_merge.py` | Verifies merged weights = base + LoRA, tensor by tensor |
| `publish_hf.py`, `publish_v2_hf.py`, `publish_v3_hf.py`, `hf_publish_v4.py` | Upload models and cards to Hugging Face (private) |
| `vm_export_gguf.sh` | **Runs on Colab:** merged weights → F16 GGUF with the Mac's converter version |
| `local_quantize_publish.sh` | Mac: F16 → 4-bit GGUF (v4 byte-parity check first), optional public GGUF repo; `publish-only` re-uploads an evaluated GGUF after checking its hashes |
| `vm_publish_public.py`, `vm_publish_public.sh` | **Runs on Colab:** public model repos (merged weights, LoRA adapter, training logs, card) for v4.1+ |
| `cards/` | Model cards for the public v4.1+ repos (`<version>.md`, `<version>-GGUF.md`) |
