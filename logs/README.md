# logs/

Run logs kept as evidence; they are not edited, except for credential redaction. Where the local `redact-env` filter is
configured, commits redact two formats (AndroidWorld's environment dump and JWT-shaped tokens); other formats are not
caught ([docs/repository.md](../docs/repository.md#secrets-and-history-rewrites)).
Operational noise (session launches, keep-alive, polling) was removed on 2026-11-20 and is at tag
`archive/pre-restructure-2026-11-20`.

| Files | Evidence for |
|---|---|
| `llama_server_<model or arm>.log` | Exact model-server flags, model files and per-request timings of each run |
| `aw_run_<model>.log` | Seed-30 AndroidWorld runs (full runner output) |
| `aw_sealed_<arm>_seed7.log` | The first two held-out arms (logs written by the first sealed runner) |
| `local_sealed_<arm>_seed<s>.log`, `local_sealed_queue_emu*.log` | Held-out arm launches and queues (progress only; outcomes stayed inside the sealed folders) |
| `local_aw_rerun_<arm>_seed<s>.log`, `local_aw_queue_emu*_rerun.log` | The preregistered single re-runs |
| `aw_emu_guard_<port>.log` | Emulator liveness guard during re-runs (it never fired) |
| `emulator_aw*.log`, `aw_emulator*_setup.log` | Emulator output, including the 2026-11-19 hang and restart |
| `*_jobs_cell*.log`, `modal_*.log`, `v3_*.log` | Training and offline-eval jobs on Colab and Modal |
| `codex_*.log` | Codex audit sessions (the reports are in `results/codex/`) |
| `gcp_mw_*.log`, `mw_pull_r2_full.log`, `colab_failover.log` | MobileWorld run 2 and its model servers |
| `qdc_*`, `devstream_*` | Phone speed benchmarks |
| `maiui_q8_sha256.txt`, `colab_maiui_q8_attestation.txt` | Proof that the MAI-UI model files served in the cloud match the Mac's |
