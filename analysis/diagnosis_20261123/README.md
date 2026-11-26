# analysis/diagnosis_20261123/

The 2026-11-23 "vision vs planning vs sequence" diagnosis that motivated round 6. Reads committed results only.

| Script | What |
|---|---|
| `diagnose.py` | Splits the failures into vision, planning and sequence errors |
| `stepnum_build.py`, `stepnum_score.py` | Builds the step-number test set (AndroidControl test steps at index ≥ 9) and scores it (`python3 -I analysis/diagnosis_20261123/stepnum_score.py`) |

Outputs: `results/diagnosis_20261123/`.
