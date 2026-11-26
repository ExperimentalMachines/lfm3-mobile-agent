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

The SageMaker job pattern used for rounds 9–14 (round 7's SageMaker job was never placed; `-Dev-FullMix` trained on Modal): `sm_launch_rN.sh` uploads the code and inputs and creates the training job;
`sm_rN.sh` runs inside it (train, merge, evaluate, gate). Rounds 1–6 ran on Colab and Modal with scripts that were removed
(see above, and round 7's unused SageMaker job); `train/sft_vlm.py` is the trainer every run used, and each run's configuration is in its
`run_config.json` under [`results/training/`](../results/training/) and the round's `results/*_dev/` folder.

| Script | Does |
|---|---|
| `sm_launch_r9.sh`, `sm_launch_r10dpo.sh`, `sm_launch_r11.sh` … `sm_launch_r14.sh` | Launch the round-N job (the usage line is in each script's header; most take `R9_BUCKET=<bucket> <script> <job> smoke\|full [hours] [KEY=VALUE ...]`) |
| `sm_r9.sh`, `sm_r10dpo.sh`, `sm_r11.sh` … `sm_r14.sh` | Run inside the job: round 9, 10 (stop-DPO), 11, 12, 13, 14 |
| `sm_r7_gate.py`, `sm_r8_gate.py`, `sm_r11_gate.py` … `sm_r13_gate.py` | The offline gates, as registered for each round (the round-8 gate builds on the round-7 one) |
| `vm_r8_eval.sh`, `vm_r9_eval.sh` | The round-8 evaluation suite (and its round-9 variant), run inside a job after training |
| `merge_adapter.py` | Merge a LoRA adapter into its base model |
| `main_reference_r7.json` | Main's offline reference numbers the gates compare against |

## publish/ — export and release

| Script | Does |
|---|---|
| `naming.py` | **The naming table** (single source of truth for [docs/naming.md](../docs/naming.md)); `--check`, `--markdown`, `--json` |
| `publish_cards.py` | Uploads / compares the cards in `cards/` against the Hugging Face repos (`--apply`, `--check`) |
| `cards/models/`, `cards/datasets/` | Every Hugging Face card, one file per repo (`<repo name>.md`) |
| `local_export_gguf.sh` | Published merged model → phone GGUF (4-bit); the download folder's name becomes the GGUF's `general.name` |
| `make_receipt.py` | Writes the conversion receipt next to a GGUF (source repo + pinned revision, SHA-256 of the converted weights, llama.cpp commit, quantization, output hash); `local_export_gguf.sh` calls it, `publish_gguf.py` refuses a GGUF without one |
| `publish_gguf.py` | Uploads a GGUF as the model's `-GGUF` repo (with the unchanged vision projector and LICENSE) and writes its card; `--parity` first checks it against an earlier GGUF of the same weights |
| `compare_gguf.py` | Compares two GGUFs tensor by tensor (names, types, shapes, hashes of the data) |
| `test_receipts.py` | Offline regression checks for pinned source revisions, weight hashes, retrospective receipt opt-in and failed comparisons; run `python3 -m unittest discover -s scripts/publish -p 'test_*.py'` |
| `check_hub.py` | Audits the Hugging Face repos on every branch: **no partially trained checkpoints** (training-state names plus a weight-file allowlist; `--selftest` runs the rules offline), every model and dataset in `naming.py` present, every model with a GGUF repo (Q4_K_M + vision projector), all repos public |
| `check_local_merge.py` | Verifies merged weights = base + LoRA, tensor by tensor |
