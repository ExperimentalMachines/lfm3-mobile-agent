# Status — 2026-11-18 02:00 (Asia/Manila)

Auto-generated table with every model: `results/SUMMARY.md` (`python3 scripts/build_report.py`).
Codex (gpt-6-astra, max) audits: `results/codex/`. Research: `reports/Small GUI agent training methods.md`,
`reports/Beating GUI Owl at 2B fairly.md` (notes in `research_notes/`).

## Running
| What | Where | Status |
|---|---|---|
| Codex independent audit of the v3 results + published v3 card | local (`logs/codex_v3_audit.log`) | running → `results/codex/codex_v3_audit.md` |
| AndroidWorld emulators 1 and 2 | this Mac | idle |

## LFM3-VL-2B versions (same recipe and budget: LoRA r64/α128, lr 2e-4, 1,250 steps × 32 rows)
| Version | Training data | AC test high / low | Held-out Odyssey / AMEX / ScreenQA | AndroidWorld (116, seed 30, Q4_K_M, 1 screenshot) |
|---|---|---|---|---|
| v1 | AndroidControl | 0.715 / 0.948 | 0.269 / 0.306 / 0.000 | **15/116** |
| v2 | v2 mix (AC + GUI-Odyssey + AMEX + ScreenQA), 8,739 blank intents | 0.716 / 0.893 | 0.644 / 0.735 / 0.764 | 3/116 (vs v1: 0–11, p=0.001) |
| v2 + forced intent (inference only) | — | — | — | 6/116 (vs v2: 3–0, p=0.25; vs v1: 0–9, p=0.004) |
| v3 | v2 mix with every intent filled (`alpharomercoma/AndroidAgent-SFT-v3` @ 565ba76c) | 0.723 / 0.902 | 0.662 / 0.741 / 0.724 | 13/116 + 1 half-credit (vs v1: 4–6, p=0.75; vs v2: 10–0, p=0.002) |

Reference: GUI-Owl-1.5-2B under the same harness and budget 23/116 (vs v3: GUI-Owl-only 18, v3-only 8, p=0.076;
vs v1: 16–8, p=0.15). Its published 67.9% uses its own harness (5 screenshots, full resolution, unquantized) and is
not comparable. Qwen3.5-2B (v1 recipe) 16/116, Qwen3.5-0.8B 12/116, LFM2.5-VL-450M 2/116.

What the AndroidWorld runs show: the matched GUI-Owl lead is the ~25 answer-scored tasks (GUI-Owl 10, LFM3 v1/v3 0 —
LFM3 never emits `answer` and declares `complete` instead); on the other tasks v1 and GUI-Owl are level. AndroidWorld
credits a success only if the agent ends the episode (`suite_utils.py`), so false 'complete' (v3: 38) and running out
of steps both score 0. Offline gains from the v2/v3 data (Odyssey .27→.66, AMEX .31→.74) did not transfer.
Seed 30 has been used to choose between versions: treat these as development-set numbers.

## Published (private Hugging Face, alpharomercoma)
`LFM3-VL-2B-AndroidAgent-v3` (merged + card) and `LFM3-VL-2B-AndroidAgent-v3-GGUF` (Q4_K_M + base mmproj; sizes
verified); v2 LFM3 / Qwen3.5-2B repos with cards; dataset `AndroidAgent-SFT-v3`. Script: `scripts/publish_v3_hf.py`.

## Next (awaiting go-ahead; plan in `reports/Beating GUI Owl at 2B fairly.md`)
1. v4 data on the Mac (no GPU): navigate-then-answer episodes from non-AndroidWorld sources, terse answers, explicit
   answer/complete rules in the prompt, installed-app list (fixes "Marker" vs Markor).
2. Train v4 once on the Colab G4 (~1.5 of ~2.5 GPU-hours left), same recipe, then AndroidWorld.
3. Fair comparison: GUI-Owl and LFM3 on ≥3 held-out seeds (~350 paired episodes, sealed), pre-registered margin.

## Budget
Colab (main account): 25.5 CU left (G4 ≈ 10 CU/h). Modal (alpharomercoma): $18.44 of credits used this month,
allowance to confirm. Modal (old account): within the $26/$28 cap.
