# Status — 2026-11-17 12:35 (Asia/Manila)

Auto-generated table with every model: `results/SUMMARY.md` (`python3 scripts/build_report.py`).
Codex (gpt-6-astra, max) audits: `results/codex/` (final results audit `codex_final_eval.md`; v2 data audit
`codex_data_v2_audit.md` → NO-GO, fixes applied, re-verification `codex_data_v2_verify.md` running).

## Running
| What | Where | Status |
|---|---|---|
| Qwen3.5-0.8B training (resumed from step 1200) → evals | Colab **G4** (RTX PRO 6000 96 GB), main account | 1.8 s/step (L4 was 18 s/step); done ≈ 13:30 |
| Codex re-verification of the v2 data (revision `d33cb3c217`) | local | running |
| AndroidWorld: Qwen3.5-2B fine-tuned | this Mac, emulator 1 | started 11:12 |
| AndroidWorld: LFM3-VL-2B FT + runtime feedback (app-name resolution + failure notes) | this Mac, emulator 2 | started 11:26; Qwen3.5-0.8B follows |
| v2 data builder box | AWS spot c6id.8xlarge (us-east-1) | kept until Codex GO, then terminated + key/SG deleted |

Queued on the G4 after the 0.8B: **LFM3-VL-2B v2** (`scripts/jobs/lfm3_v2mix_g4.json`): v1 recipe and budget
(1,250 steps × 32 rows, LoRA r64, lr 2e-4) on the v2 mix → AC test, v2 dev splits for base / v1 / v2, forced-choice
general eval for v2 and the four Qwen models. v1 (AC-only, same budget) is the equal-budget control.

Recovery note: the Mac rebooted ~08:37 and both Colab L4 VMs were reclaimed after their exec websockets dropped;
everything resumed from hub checkpoints (`scripts/provision_and_launch.sh`, `scripts/local_aw_lane.sh`).
Checkpoints now every 50 steps where the trainer honours it.

## Results
| Model | AndroidControl test step SR (high / low) | AndroidWorld (116) | General knowledge |
|---|---|---|---|
| LFM3-VL-2B base | 0.313 / 0.634 | 1/116 | MMStar 52.1%, MMLU 48.9% (forced-choice) |
| **LFM3-VL-2B FT (v1)** | **0.715 / 0.948**, terminal 0.792 | **15/116 (12.9%)**, 2.7 s/step | MMStar +5.0 pp (p=3e-7), MMLU +0.6 pp |
| LFM2.5-VL-450M base | 0.009 / 0.024 | **0/116** (82% unparseable) | MMStar 38.5%, MMLU 39.9% |
| LFM2.5-VL-450M FT | 0.536 / 0.862 | 2/116 (+1 half-credit); paired vs base 2–0, p=0.5 | +0.8 / −0.7 pp (n.s.) |
| Qwen3.5-2B base | 0.384 / 0.590 | — | forced-choice pending (G4 job) |
| **Qwen3.5-2B FT** | **0.734 / 0.949**, terminal 0.784 | running | forced-choice pending |
| Qwen3.5-0.8B FT | training | queued | — |
| GUI-Owl-1.5-2B, compute-matched (1 image) | — | **23/116 (19.8%)**, 7.9 s/step | — |

Paired AndroidWorld (identical task instances): LFM3 FT vs base 14–0 (p=1.2e-4); GUI-Owl vs LFM3 FT 16–8 (p=0.15,
n.s.) — GUI-Owl's extra wins are mostly question/answer tasks (calendar lookups, counts), which AC cannot teach.

## v2 training data — `experimentalmachines/AndroidAgent-SFT-v2` (private, revision d33cb3c217)
79,320 train rows = AndroidControl 55,936 · GUI-Odyssey 9,940 · AMEX 7,450 · ScreenQA 5,994; dev: GUI-Odyssey 998,
AMEX 491, ScreenQA 500. Built on AWS from the raw sources by `data/build_v2_mix.py`; filters, counts and every-row
assertions in `results/data_v2/stats.json` and the dataset card (`results/data_v2/README.md`). Revision 2 fixes Codex
findings F1–F12 (screen-disjoint dev, type+Enter merged for AndroidWorld's executor, centre-band scrolls only,
key-text/typo removal, no unreviewed infeasible labels, no silent completion of question tasks, OCR rejection of
Pending/Loading end screens, ambiguous-app exclusion, per-episode caps, blank AMEX intents).
GUI-Owl-1.5 releases no training data; ScreenSpot-v2 (mobile) and MobileWorld (GUI-only) are the recommended extra
benchmarks (eval only).

## Budget
Colab: main account 63 CU (G4 ≈ 10 CU/h), second account 40 CU (idle). Modal: $13.0 of $26 used. AWS: one spot box.
