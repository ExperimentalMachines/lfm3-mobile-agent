# Status — 2026-11-16 23:20 (Asia/Manila)

## Running (updated 01:45 Nov 17)
| What | Where | Status |
|---|---|---|
| LFM3-VL-2B: resume from step 700 → 1,250, then general eval base/FT, AC test FT + base + matched no-think, push | **Modal A100-40GB** (user decision; budget ≤ $26) | started 01:36 |
| LFM2.5-VL-450M: resume from step 700 → 1,875 (+20% replay), then general eval FT, AC test FT + base, push | **Modal A100-40GB** | step 1,400 at 01:38 (~3.4 s/step) |
| Qwen3.5-2B (same recipe as LFM3) | Colab L4 `qwen2bl4`, account <account-A> | started 01:40 |
| Qwen3.5-0.8B (keep-knowledge recipe) | Colab L4 `lfm25l4`, account <account-B> (via `state-dashboard-v4:~/vl`) | started 00:50 |
| GUI-Owl-1.5-2B AndroidWorld, compute-matched | this Mac | in progress |

Modal cost ≈ $2.8/h per run (A100-40GB $2.10 + 6 cores + 48 GiB); estimated total ≈ $15.

## Results so far
| Model | AndroidControl test step SR (high / low) | AndroidWorld (116) | General knowledge |
|---|---|---|---|
| LFM3-VL-2B base (no-think) | 0.315 / 0.634 lenient (Codex independent scorer: 0.291 / 0.584); termination 0% | **1/116 (0.9%)**, 2.25 s/step, 1.1k prompt tokens | — |
| LFM2.5-VL-450M base | (in pipeline) | — | MMStar 41.6%, MMLU 39.4% |
| **LFM2.5-VL-450M fine-tuned** (Q4_K_M ≈ 330 MB incl. mmproj) | **0.536 / 0.862**; episode 0.128 / 0.521; terminal 0.561; 100% valid format | running | forced-choice: MMStar 38.5→39.3% (+0.8pp, p=0.37), MMLU 39.9→39.2% (−0.7pp, p=0.45) — no forgetting |
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
