# Infrastructure and incidents

Where each part of the project ran, how costs were kept in check, and what went wrong.

**Contents:** [Where things ran](#where-things-ran) · [Cost controls](#cost-controls) · [Incidents](#incidents-and-fixes) ·
[Lessons](#lessons)

---

## Where things ran

| Work | Hardware |
|---|---|
| SFT v1, v3, LFM2.5-VL-450M | Modal GPU containers (A100 / H100) |
| SFT Qwen3.5-2B / 0.8B, v2 mixes | Google Colab GPUs |
| SFT v4, offline evals, v4-RL (GRPO) | Colab A100-40GB |
| AndroidWorld: every seed-30 and held-out run | Apple M5 Mac, 2 Android emulators (Pixel 6, API 33, arm64), llama.cpp on Metal |
| MobileWorld v4 run 1 (discarded) | AWS EC2 `c8i.4xlarge` (nested virtualisation), model on CPU |
| MobileWorld run 2: GUI-Owl, v4, MAI-UI | GCP `n2-standard-16` spot VM (nested virtualisation); models on a Colab T4 through a reverse SSH tunnel restricted to the model ports |
| CPU speed benchmark | The same GCP VM, idle, before its MobileWorld run |
| Phone speed benchmark | Qualcomm Device Cloud (Snapdragon 8 Elite Extreme Gen 6 reference phone); earlier attempt on a Pixel 9 via Firebase device streaming |
| Audits and research | Codex CLI on the Mac |
| Follow-up rounds v4.1–v4.3 (2026-11-21 to 23) | Training and offline gates on Colab A100 (second Colab account); seed-30 runs on the Mac; MobileWorld run 3 (v4.2) on a new GCP `n2-standard-16` VM with the model on a Colab T4, as in run 2; reviews by agy |
| Round 6 (v4.4, 2026-11-23) | Colab A100 (64.5 compute units) |
| Rounds 7–8 (D, E, 2026-11-24 to 25) | Data built on an AWS EC2 CPU instance; training on Modal H100 (E: Colab A100 to step 3,100, then Modal); evaluations on the same GPUs |
| Round 9 (v4.7 data, 2026-11-25) | Data built on the AWS EC2 CPU instance; a SageMaker smoke job on `ml.g6.2xlarge` (L4) for F, which was never trained |
| Rounds 10–11 (2026-11-25) | AWS SageMaker `ml.g6e.2xlarge` (1× L40S 48 GB): pair generation, DPO, SFT and every gate eval in one job each; the AWS EC2 CPU instance for data building and GGUF export, started and stopped per use |
| "Done" judges (round 10) | Qwen3-VL-235B on AWS Bedrock (calibration only); Claude Opus 5.5 via the Anthropic API (Batch API for bulk labels) |
| AndroidWorld runs after v4 (v4.1–v4.3, D, E; E's held-out seeds) | The same Apple M5 Mac, 2 emulators, Q4_K_M GGUF on llama.cpp |

Colab VMs have no KVM, so Android emulators could not run there. That is why MobileWorld moved to AWS and GCP.

---

## Cost controls

- Every cloud VM powers itself off after 12 h (AWS `shutdown -h`, GCP `--max-run-duration`).
- Colab sessions were stopped by a watchdog once their jobs finished.
- Teardown (2026-11-23): the GCP project was deleted (VM, disk, static IP, firewall rules, network), after checking
  that every MobileWorld result, screenshot and log was saved locally. Its storage bucket (copies of the phone-test
  model files and the Android llama.cpp build) was deleted first, after each file's CRC32C matched a local copy.
- Claude API labels (round 10): every call priced into a ledger ([`results/v48_dev/claude_spend.jsonl`](../results/v48_dev/claude_spend.jsonl)); nothing was sent if the worst case of the work in flight could pass $90 (owner's cap $95). Spent: $24.53.
- SageMaker jobs carry a maximum runtime and sync checkpoints to S3, so a stopped job resumes instead of restarting.
- The whole pipeline was smoke-tested before any paid run (rule adopted after an early v3 attempt failed inside a
  paid pipeline).

---

## Incidents and fixes

| When (Manila) | Incident | Handling |
|---|---|---|
| 11-16/17 | Early v3 attempt failed inside its paid pipeline | Rule: smoke-test the whole pipeline before paid compute |
| 11-17 | v2 scored 3/116 | Blank intents suspected (forcing an intent: 3 → 6, p = 0.25); v3 filled them |
| 11-18 04:51 | Colab A100 VM lost during v4 SFT (step 353) | Resumed from the step-350 Hub checkpoint on a new A100; training refuses to restart from scratch if a checkpoint exists |
| 11-18 06:25 | Answer check accepted padded answers ("12M is incorrect") | Stricter gate criterion, fixed before any v4 result |
| 11-18 08:10 | Hugging Face private storage full; merged v4 upload failed | Weights copied off the VM and verified tensor by tensor; the v2 dataset was made public to free space |
| 11-18 09:30 | Resuming an AndroidWorld run would retry saved exceptions | Patched: saved failures stay failures; checkpoints written atomically |
| 11-18 11:20 | GUI-Owl on CPU ≈ 45–58 s per step | Served from a Colab GPU through a tunnel |
| 11-18 13:50 | llama.cpp's RAM prompt cache served repeated screenshots in the speed test | Cached calls excluded from the statistics |
| 11-18 14:09 | GUI-Owl's MobileWorld model server killed by out-of-memory (prompt cache) | Run 1 discarded; run 2 with `--cache-ram 0` |
| 11-19 00:35–08:06 | Emulator 2 hung; 113 v4 seed-1234 episodes crashed in setup | Preregistered single re-run on emulator 1 with a liveness guard ([`aw_emu_guard.sh`](../scripts/androidworld/aw_emu_guard.sh)) |
| 11-19 04:57 | GCP VM stopped at its 12-h limit; MobileWorld containers vanished (`docker run --rm`) | Containers recreated with the original command |
| 11-19 10:30 | Restarted container's emulator refused to boot (stale AVD locks) | Graceful emulator stop + lock cleanup before every restart |
| 11-19 12:40 | First Colab model session hit its 24-h limit | Failover session with identical files (SHA-256), build and flags took over in 1 s |
| 11-19 12:42, 14:29 | Two spot-VM preemptions during MAI-UI's run | Watcher restarted the VM, recreated containers, re-ran interrupted tasks |
| 11-19 (MAI-UI run) | Emulators died 17 times with a fatal KVM error | Disclosed; affected tasks reported as a sensitivity analysis |

Full details and timing: dated entries in [PREREG_v4.md](PREREG_v4.md).

---

## Lessons

| Lesson | Applied as |
|---|---|
| Episode counts hide total failure | Watch exception counts and emulator liveness during sealed runs, not just progress |
| `--rm` containers vanish on VM stop | Recreate containers from the original command; stop emulators gracefully |
| Prompt caches distort speed and memory | Disable or exclude cached calls in benchmarks |
| Paid runs fail late | Smoke-test the full pipeline first; persist outputs as you go |
