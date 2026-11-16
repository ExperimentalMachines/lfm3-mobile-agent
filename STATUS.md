# Status — 2026-11-17 05:20 (Asia/Manila)

Audited by Codex (gpt-6-astra, max) in `results/codex/codex_final_eval.md` (cutoff 04:43); numbers below follow it.
Auto-generated table with every model: `results/SUMMARY.md` (`python3 scripts/build_report.py`).

## Running
| What | Where | Status |
|---|---|---|
| AndroidWorld 116, LFM3-VL-2B FT (Q4_K_M) | this Mac, emulator 1 | 7/61 done → then GUI-Owl matched reference resumes (9/60 done) |
| AndroidWorld 116, LFM2.5-VL-450M FT (Q4_K_M) | this Mac, emulator 2 | 0/86 done → then 450M base |
| Qwen3.5-2B (LFM3 recipe) | Colab L4 `qwen2bl4` (<account-A>) | step ~300/1250; restarting from hub ckpt with flash-linear-attention (reference GDN path ran 46 s/step) |
| Qwen3.5-0.8B (keep-knowledge recipe) | Colab L4 `lfm25l4` (<account-B>, via `state-dashboard-v4:~/vl`) | step ~400/1875; same FLA restart |

Modal (A100-40GB, ≈ $2.8/h per job): **$13.40 metered** so far (LFM3 resume+evals, 450M resume+evals, forced-choice evals); target ≤ $26.

## Results
| Model | AndroidControl test step SR (high / low) | AndroidWorld (116) | General knowledge (forced-choice, paired vs base) |
|---|---|---|---|
| LFM3-VL-2B base (no-think) | 0.313 / 0.634 (Codex independent scorer 0.289 / 0.582); terminal 0% | **1/116 (0.9%)**, 2.25 s/step | MMStar 52.1%, MMLU 48.9% |
| **LFM3-VL-2B fine-tuned** (Q4_K_M 1.1 GB + 0.2 GB mmproj) | **0.715 / 0.948**; episode 0.283 / 0.783; terminal 0.792; unseen app/task/category 0.671/0.696/0.681; no-think matched 0.664 | partial **7/61** (running), 2.8 s/step | MMStar **+5.0 pp** (p=3e-7), MMLU +0.6 pp [−1.7, +3.0] — no decline detected |
| LFM2.5-VL-450M base | 0.009 / 0.024 (parse rate ~2%) | queued | MMStar 38.5%, MMLU 39.9% |
| **LFM2.5-VL-450M fine-tuned** (Q4_K_M ≈ 330 MB incl. mmproj) | **0.536 / 0.862**; episode 0.128 / 0.521; terminal 0.561; 100% valid format | partial **0/86** (running), 1.4 s/step | MMStar +0.8 pp [−0.8, +2.4], MMLU −0.7 pp [−2.3, +0.8] — no decline detected |
| GUI-Owl-1.5-2B, 1 image (reference) | — | partial 9/60, 6.2 s/step, 2.3k prompt tokens | — |
| GUI-Owl-1.5-2B native, 5 images | — | 2/2 *selected easy* tasks (not a suite score); 61 s/step, 10.7k tokens | — |

Paired LFM3 base vs FT on identical AW task instances (Codex, 47 pairs at cutoff): FT-only wins 2, base-only 0, McNemar p=0.50 —
the closed-loop gain is **not yet statistically established**; the full 116 run will decide.

## What AndroidWorld shows (eval/androidworld/failure_modes.py → results/androidworld/*.failure_modes.json)
* Neither FT model ever emits `answer`: AndroidControl has **zero** answer/keyboard_enter/infeasible labels → all
  information-retrieval tasks fail by construction.
* LFM3 FT signals `complete` on ~1/3 of failed episodes (often after a plausible save/confirm click) — completion is
  over-confident; AC's synthetic terminal step only teaches "final screen of a successful demo".
* App naming: `File Manager` (AW maps `Files`), `Stopwatch`/`Timer` (Clock), `Marker` (Markor), `Calendar Pro`.
* 450M FT: wait runs and repeated identical clicks after an action had no visible effect → no recovery behaviour.
* Offline AC gains do not transfer proportionally to closed-loop control (teacher-forced history vs own history).

## Codex reviews
* passes 1–11: adversarial QA of the pipeline (3 critical + ~20 major issues found and fixed); pass 11 GO.
* dataset viability (web search): `docs/DATA_V2_PLAN.md`; GUI-Owl lessons: `docs/GUI_OWL_LESSONS.md`.
* final results audit: `results/codex/codex_final_eval.md` — corrections applied (stale base numbers, p-value
  rounding, "no forgetting" wording, 450M image-token note, classifier schema/loop definitions, protocol row counts).

## Next
1. Finish the 116-task runs (LFM3 FT, 450M FT, 450M base, GUI-Owl matched) → refresh SUMMARY, cards, paired stats.
2. Qwen3.5-2B / 0.8B: training → AC + general evals on Colab → GGUF (converter supports Qwen3.5) → AndroidWorld.
3. v2 (Codex's top recommendations): runtime app-name resolution + execution-error feedback; train answer actions,
   recovery and calibrated completion (ScreenQA / GUI-Odyssey / AMEX mix, `DATA_V2_PLAN.md`) vs an equal-budget
   AC-only control; then a physical-phone latency/memory/thermal test.
