# Infrastructure, cost and incidents

## Where things ran

| what | where |
|---|---|
| SFT v1, LFM2.5-VL-450M, v3 | Modal (GPU containers) |
| SFT Qwen3.5-2B/0.8B, v2 mixes | Google Colab GPUs |
| SFT v4 (v4b data) + offline evals + v4-RL (GRPO) + RL evals | Colab A100-40GB (`lfm3v4a`, 06:02–10:39 on 2026-11-18, ≈ 31 compute units at 6.73 CU/h) after the first A100 VM was lost |
| AndroidWorld (all seed-30 runs, sealed arms, MAI-UI) | Apple M5 Mac, 2 Android emulators (Pixel 6 API 33 arm64), llama.cpp Metal |
| MobileWorld v4 | AWS EC2 `c8i.4xlarge` (16 vCPU, nested virtualization), us-west-2, on-demand $0.75/h, model on CPU |
| MobileWorld GUI-Owl / MAI-UI | GCP `n2-standard-16` spot (nested virtualization), us-west1, with the models on a Colab T4 reached through a restricted reverse SSH tunnel |
| Speed benchmark | the GCP VM above, before its MobileWorld run |
| Adversarial audits / research | Codex CLI (gpt-6-astra, max effort) on the Mac |

## Budget snapshot (2026-11-18 14:19)

* Colab: 100 compute units bought on 2026-11-18 on top of the remaining balance; ≈ 75 left after the A100 run, then a T4 for model serving.
* Modal: v1/v3 era runs within the account's allowance (see the working repo's `STATUS.md`).
* AWS: account credits ≈ $22 + card; one on-demand c8i.4xlarge for MobileWorld; vCPU quota increase to 192 (on-demand and spot) requested 2026-11-18, under review.
* GCP: $26 of credits; one spot n2-standard-16 + 200 GB disk; GPU quota 0 → 1 requested.
* Cost guards: every cloud VM powers itself off (AWS `shutdown -h`, GCP `--max-run-duration`, 12 h); Colab VMs are
  stopped by a watchdog after their jobs finish.

## Incidents and fixes (chronological)

| when (2026-11-18) | incident | fix / handling |
|---|---|---|
| 04:51 | Colab A100 VM pruned during v4b SFT (step 353), ~20 min after its exec websocket dropped | resumed from the step-350 hub checkpoint on a new A100; watchdog with keep-alive client and re-provisioning; `sft_vlm.py` refuses to restart from scratch if a hub checkpoint exists but cannot be restored |
| 06:25 | Codex: the answer criterion accepted padded answers ("12M is incorrect") | stricter `gate_answer` (no added content words), pre-registered before any v4 result |
| 08:10 | merged v4 upload failed: Hugging Face private storage full (user and org namespaces at ~100 GB) | merged weights copied from the VM and verified tensor-by-tensor (bf16(base + 2·B·A) within 1 ulp); later `AndroidAgent-SFT-v2` was made public and marked superseded, freeing 31 GB, and v4/v4-RL were uploaded |
| 09:12 | emulator-2 filler would have resumed a paused sealed arm from its log file | replaced before the pause happened |
| 09:30 | AndroidWorld resume re-runs saved exception episodes (would give paused arms a second try) | patched: saved failures are kept; checkpoints written atomically; unreadable checkpoints stop the resume |
| 10:16 | v4-RL tokenizer files differed from v4 (left-padding block) | v4's files used for the RL export; originals kept |
| 11:05 | Colab VMs have no KVM (Android emulators cannot run) | MobileWorld moved to AWS/GCP instances with nested virtualization |
| 11:20 | GUI-Owl on CPU ≈ 45–58 s/step (2,600-token images) | served from a Colab GPU through a reverse tunnel restricted to two ports |
| 12:45 | Colab upload API rejects files > ~100 MB | 64 MB chunks, reassembled and SHA-256-checked |
| 13:50 | speed benchmark: llama-server RAM prompt cache served repeated screenshots | cache hits excluded from the statistics |
| 13:55 | MAI-UI MobileWorld wrapper missing `tools` (would have crashed in evaluation) | fixed before the evaluation |

Earlier (2026-11-16/17), from the working repo's history: an early v3 attempt failed inside its paid pipeline (the
project's "smoke-test the whole pipeline before paid compute" rule came from that), the v2 blank-intent regression was diagnosed with the
forced-intent ablation, and AndroidWorld harness fixes (teardown exceptions, adb paths) are tracked in
`eval/androidworld/android_world_local_fixes.patch`.
