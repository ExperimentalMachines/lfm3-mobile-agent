# scripts/

Orchestration: how the runs were launched, watched and published. Scripts that **compute** results are in
[`../analysis/`](../analysis/).

- Local launchers find the repository from their own location; scripts that run on a cloud job use that job's paths.
- On 2026-11-26 the scripts bound to sessions and machines that no longer exist (Colab / Modal / GCP / AWS-VM launchers,
  watchers and hand-offs, the old publishers, the per-run job configs) were removed. They are intact at tag
  `archive/pre-naming-cleanup-2026-11-26` (`git show archive/pre-naming-cleanup-2026-11-26:scripts/training/gpu_session.sh`);
  older layouts are at `archive/pre-restructure-2026-11-20` ([docs/repository.md](../docs/repository.md)).
- Hugging Face names inside scripts follow [docs/naming.md](../docs/naming.md); Hugging Face redirects the old ones.

## androidworld/ — AndroidWorld runs on the Mac's two emulators

| Script | Does |
|---|---|
| `local_sealed_aw_v3.sh` | **Runs one held-out arm** (model × seed) with the preregistered flags; results stay sealed. Usage: `<arm> <seed> <console port> <grpc port> <server port>` |
| `local_sealed_aw_e.sh` | The same for `-Counterfactual` (post-hoc held-out run, round 8) |
| `local_aw_rerun.sh`, `local_aw_rerun_e.sh` | The preregistered single re-run of setup-crash episodes (any arm / `-Counterfactual`, with a cold-booted emulator) |
| `rerun_harness_errors.sh` | Re-runs only the episodes of a finished pass that ended in a harness exception |
| `aw_emu_guard.sh` | Kills a run before a crash is recorded if the emulator stops answering |
| `aw_watchdog.sh` | Kills hung child processes of a run |
| `local_maiui_aw.sh` | MAI-UI-2B seed-30 run (8-bit): the comparison arm |
| `setup_snapshots.py`, `verify_reset.py` | Create AndroidWorld's per-app clean snapshots on an emulator and verify the per-task reset works (round 14; without snapshots no earlier run reset app data) |

## eval/ — evaluation helpers

| Script | Does |
|---|---|
| `run_sop_lane.sh` | The multi-step own-history test (SOP, round 13) for a list of models on one llama-server port |

## mobileworld/ — MobileWorld

| Script | Does |
|---|---|
| `gcp_mw_resume_vm.sh` | **Runs on the MobileWorld VM:** finishes a run under the preregistered completion rule |
| `mw_pull_r2.sh`, `mw_pull_r3.sh`, `mw_pull_e.sh` | Pull trajectories from the VM for run 2, the follow-up run and the `-Counterfactual` run (inputs of `analysis/mw_summarize_*.py`) |

## speed/ — speed benchmarks

| Script | Does |
|---|---|
| `bench_speed.sh` | CPU benchmark on an idle VM |
| `qdc_chain2.sh` | Phone benchmark on Qualcomm Device Cloud (round 2) |
| `devstream_device_v6.sh` | One phone's benchmark over a remote adb server (used by `qdc_chain2.sh`) |

## training/ — GPU jobs on AWS SageMaker

The SageMaker job pattern used for rounds 7–14: `sm_launch_rN.sh` uploads the code and inputs and creates the training job;
`sm_rN.sh` runs inside it (train, merge, evaluate, gate). Rounds 1–6 ran on Colab and Modal with scripts that were removed
(see above); `train/sft_vlm.py` is the trainer every run used, and each run's configuration is in its
`run_config.json` under [`results/training/`](../results/training/) and the round's `results/*_dev/` folder.

| Script | Does |
|---|---|
| `sm_launch_r7.sh` … `sm_launch_r14.sh` | Launch the round-N job (`R9_BUCKET=<bucket> sm_launch_rN.sh <job> smoke\|full [hours] [KEY=VALUE ...]`) |
| `sm_r7.sh` … `sm_r14.sh` | Run inside the job: round 7 (FullMix), 9, 10, 10dpo (stop-DPO), 11, 12, 13, 14 |
| `sm_r7_gate.py`, `sm_r8_gate.py`, `sm_r10_gate.py` … `sm_r13_gate.py` | The offline gates, as registered for each round |
| `vm_r8_eval.sh`, `vm_r9_eval.sh`, `vm_r10_eval.sh` | The round-8 evaluation suite (and its round-9 / round-10 variants), run inside a job after training |
| `merge_adapter.py` | Merge a LoRA adapter into its base model |
| `main_reference_r7.json` | Main's offline reference numbers the gates compare against |

## publish/ — export and release

| Script | Does |
|---|---|
| `naming.py` | **The naming table** (single source of truth for [docs/naming.md](../docs/naming.md)); `--check`, `--markdown`, `--json` |
| `publish_cards.py` | Uploads / compares the cards in `cards/` against the Hugging Face repos (`--apply`, `--check`) |
| `cards/models/`, `cards/datasets/` | Every Hugging Face card, one file per repo (`<repo name>.md`) |
| `local_export_gguf.sh` | Merged model → phone GGUF (4-bit) |
| `check_local_merge.py` | Verifies merged weights = base + LoRA, tensor by tensor |
