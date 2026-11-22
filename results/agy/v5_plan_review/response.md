# Response to agy pass 1 (2026-11-22)

| ID | Disposition | Reason / fix |
|---|---|---|
| P1-1 train = val loss | **Invalid as stated, wording fixed** | 0.336 is the whole-run average `train_loss`; the last 100 logged steps average 0.305 vs eval 0.306 (`log_history.json`). Report now states both and notes that at 0.43 epoch each row is seen once (no memorisation, not spare capacity) |
| P1-2 false-complete counts unverifiable | **Valid (missing source), fixed** | Counts committed: `results/androidworld/failure_taxonomy_20261122.json` (`primary.false_complete`: seed 30 v4 25, v4.2 25; sealed v4 71), scripts in `analysis/failure_analysis/` |
| P1-3 latency split unverifiable | **Partly valid, fixed** | Source is `logs/llama_server_lfm3vl2b_v42.log` (outside `results/`); report now cites it and `analysis/failure_analysis/latency.py` |
| P2-1, P2-2 | Confirmations | — |
| P3-1 epoch cost 4.2 h | **Invalid** | 7,074 s covers only v4's resumed segment (steps 351–1,250 = 900 steps × 32 rows): 4.1 rows/s → 92,229 rows ≈ 6.3 h. Derivation added to the report |
| P3-2 replay states not cited | **Invalid** | The DPO recipe already cites `selfhist_state.json.gz` and `data/v42_selfhist.py` |

Pass 1 did not cover tasks 2–5 (logic, decision rules, fairness, feasibility); pass 2 asks for them.
