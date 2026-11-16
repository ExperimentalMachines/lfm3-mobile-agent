# Status — 2026-11-16 23:20 (Asia/Manila)

## Running
| What | Where | Progress / ETA |
|---|---|---|
| LFM3-VL-2B LoRA SFT (1,250 steps × 32 = 40k AC rows) → FT AC-test eval → push `experimentalmachines/LFM3-VL-2B-AndroidControl` | Colab L4 `lfm3l4b`, account <account-A> | ~31 s/step; train ends ~05:55, eval+push ~08:00 |
| LFM2.5-VL-450M "keep general knowledge" SFT (48k AC + 12k the_cauldron replay = 20%, LoRA r16, lr 1e-4) → general eval FT, AC test base/FT → push `experimentalmachines/LFM2.5-VL-450M-AndroidControl` | Colab L4 `lfm25l4`, account <account-B>, launched from `state-dashboard-v4:~/vl` | ~12.6 s/step × 1,875; train ends ~05:20, evals ~06:45 |
| chain → Qwen3.5-2B (same recipe as LFM3) | after LFM3 on `lfm3l4b` (`logs/chain_main_qwen2b.log`) | ~20:00–22:00 Nov 17 |
| chain → Qwen3.5-0.8B (keep-knowledge recipe like 450M) | after 450M on `lfm25l4` (`~/vl/logs/chain_qwen08.log`) | ~13:00–14:00 Nov 17 |
| GUI-Owl-1.5-2B AndroidWorld, compute-matched (1 image ≤1,024 tokens) | this Mac, emulator 5556, llama-server :8092 | ~2–3 h |

Every run checkpoints to the Hub every 100 steps (`*-LoRA-ckpt` repos) and resumes from there; evals push partial predictions.

## Results so far
| Model | AndroidControl test step SR (high / low) | AndroidWorld (116) | General knowledge |
|---|---|---|---|
| LFM3-VL-2B base (no-think) | 0.315 / 0.634 lenient (Codex independent scorer: 0.291 / 0.584); termination 0% | **1/116 (0.9%)**, 2.25 s/step, 1.1k prompt tokens | — |
| LFM2.5-VL-450M base | (pending, in pipeline) | — | MMStar 41.1%, MMLU 39.5% (n=1000) |
| GUI-Owl-1.5-2B native (5 imgs) | — | 2/2 sample tasks; **61 s/step**, 10.7k prompt tokens | — |

## Codex (gpt-6-astra, max) reviews
* pass 1 audit → 2 critical AW-patch bugs found and fixed (vocabulary corruption, silent cleanup); invalid base run discarded.
* passes 2–11 adversarial QA (gpt-6-astra, max effort): 3 critical + ~20 major issues found and fixed (stage receipts,
  failure propagation, frozen-GT scoring with sha256, prediction identity/fingerprints, matched base/FT evals, strict parsing,
  thinking-prefill, provenance, chain hand-off incl. lost-session + restarted-predecessor handling).
  **Pass 11 verdict: GO for both Qwen chains**; residuals are deliberate-tampering only (`results/codex/codex_verify_pass11.md`).
* dataset viability (web search): `docs/DATA_V2_PLAN.md`; GUI-Owl lessons: `docs/GUI_OWL_LESSONS.md`.

## Next
1. When LFM3 FT is on the Hub: convert merged → GGUF Q4_K_M (tools/llama.cpp converter + brew `llama-quantize`),
   run AndroidWorld 116 with it (same harness, answer-ends-episode rule). Same for 450M (and later Qwen).
2. Codex final evaluation pass over all results (`results/`), then report.
3. v2 data round (DATA_V2_PLAN.md) on LFM3-VL-2B vs an equal-budget AC-only control.
