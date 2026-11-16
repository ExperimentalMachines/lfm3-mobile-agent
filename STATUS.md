# Status (2026-11-16 ~18:35, session paused at usage limit)

## Running unattended
* **LFM3-VL-2B LoRA SFT** on Colab L4 session `lfm3l4b` (config: scratchpad l4b.json), blocking kernel cell
  (`scripts/vm_blocking_jobs.py`), 1,250 steps × eff. batch 32 (~40k rows), checkpoints pushed every 100 steps to
  private HF repo `experimentalmachines/LFM3-VL-2B-AndroidControl-LoRA-ckpt` (`last-checkpoint/`). Resumable on any GPU:
  `train/sft_vlm.py` auto-restores `last-checkpoint` from the hub. Outputs on VM: `/content/runs/lfm3vl2b-ac-lora/{lora,merged,logs}`.
  L4 ≈ 1.94 CU/h; run ≈ 8–9 h on L4. **Stop it with** `colab --config <l4b.json> stop -s lfm3l4b` if needed.
* **AndroidWorld baseline** (base LFM3-VL-2B Q4_K_M via local llama-server :8091, no-think) on local emulator
  5556/8556 → `results/androidworld/lfm3vl2b_base_nothink/run_*`. Summarize: `.venv-aw/bin/python eval/androidworld/summarize_aw.py <run_dir> --out results/androidworld/base.summary.json`.

## Done
* Datasets/splits researched + decided: `docs/DATASETS_AND_SPLITS.md`; protocol: `docs/EVAL_PROTOCOL.md`.
* Processed dataset (official AndroidControl splits, zero train/val/test overlap verified, AW-app filtered, scroll
  convention verified = AndroidWorld's) on HF (private): `experimentalmachines/AndroidControl-screen-agent-sft`
  (train 99,216 rows / val 827 / test 18,415).
* Pipeline smoke-tested on GPU (TRL 1.16 / transformers 5.20.2 / torchao 0.18 pins).
* AndroidWorld env set up locally (patches in `eval/androidworld/*.patch`: monkey syskeys, never kill shared adb).

## Next
1. Base offline eval: `scripts/jobs/lfm3_base_eval_l4.json` via `scripts/launch_gpu_jobs.sh` (needs a GPU session).
2. When training ends: eval fine-tuned (`vm_eval.sh MODEL=/content/runs/lfm3vl2b-ac-lora/merged THINK=1`), download logs/metrics
   (`colab download`), push merged model + GGUF Q4_K_M (llama.cpp convert) to private HF, run AndroidWorld with FT GGUF.
3. Qwen3.5-2B same recipe (`--chat_template_path train/qwen35_chat_template_gen.jinja`); baselines GUI-Owl-1.5-2B, MAI-UI-2B.
4. Codex independent evaluation (`codex exec`, see docs/EVAL_PROTOCOL.md §3).
