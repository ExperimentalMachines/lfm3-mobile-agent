# Verdict: GO AFTER FIXES

## Findings Table (ordered by severity)

| ID | Severity | File:Line | What is Wrong | Evidence | Exact Fix |
|---|---|---|---|---|---|
| P1-1 | P1 | docs/research/training-scale-and-own-attempt-learning.md:99-100 | Human "wait" steps were relabeled after v4.1, still noisy; DPO would treat these as correct preferences, pushing bad behavior. | "wait" relabel D1 mentioned in lines 99‑100. | Exclude replay states where the human step originates from a relabeled "wait" (detect via intent containing "wait" without waiting intent). |
| P1-2 | P1 | data/v42_selfhist.py:9‑11 | Matching rule for "differs" is loosely defined; current code uses 14% screen‑radius match which may accept incorrect clicks. | `match` rule cited in lines 9‑11. | Clarify DPO pair generation to require action‑type match and screen‑distance ≤14% *and* intent‑text similarity; reject clicks that differ only by small coordinate offsets. |
| P1-3 | P2 | docs/datasets.md:10‑12 | Pairs drawn from dev/test splits or MobileWorld could violate contamination rule. | Contamination rule lines 10‑12. | Restrict DPO sample pool to training‑only rows; never sample from dev/test or benchmark app episodes. |
| P2-1 | P2 | sft_vlm.py:39 | Reference model for DPO is v4.2 with LoRA disabled, but `modules_to_save` includes the multi‑modal projector which is fully trained; disabling LoRA also disables the projector, causing a mismatch. | `modules_to_save=["multi_modal_projector"]` line 39. | Use a reference checkpoint that retains the projector (e.g., disable only LoRA adapters, keep projector weights) or exclude projector from `modules_to_save`. |
| P2-2 | P3 | docs/research/training-scale-and-own-attempt-learning.md:161‑166 | "More training" test uses fresh rows which also change data mix, confounding the hypothesis that more epochs alone help. | Fresh‑rows run description lines 161‑166. | Add a control run with same fresh‑row proportion but same epoch count to isolate effect; report both. |
| P3-1 | P3 | docs/research/training-scale-and-own-attempt-learning.md:150‑154 | Cost estimate for additional epochs exceeds 5 A100‑hour budget (one epoch ~6.3 h). | Cost table lines 150‑154. | Prioritize cutting guard experiments or fresh‑row run; if DPO fails, fallback to longer SFT with WSD schedule rather than extra epochs. |

## Answers to Review Questions

1. **Step‑DPO specification**
   - (a) Yes, using noisy human steps (e.g., relabeled `wait` from v4.1) would push the model toward the same bad behavior. Such states should be filtered out (see P1‑1). 
   - (b) "Differs" should be defined by **action type**, **screen‑distance ≤14 % radius** (as in `score.match` lines 9‑11), and **intent text difference**; a pure coordinate offset on a correct click must not be treated as a reject. 
   - (c) Sampling temperature only affects the diversity of the rejected samples; the preference label (preferred vs rejected) is deterministic, so temperature 0.8 vs 0 is irrelevant for the pair correctness. 
   - (d) Using the v4.2 checkpoint with the LoRA disabled while `modules_to_save` includes the projector creates a mismatch because the projector would also be disabled. The reference model must keep the projector weights (see P1‑3). 
   - (e) Pairs must **not** be drawn from any dev/test split or from AndroidWorld/MobileWorld apps to respect the contamination rule (docs/datasets.md lines 10‑12). Only training rows are allowed.

2. **Gates**
   - A candidate could technically satisfy the false‑complete ≤15 gate by never stopping, but this would lead to budget exhaustion and be caught by the *budget* gate (implicit step‑budget limit). The plan should require **both** a minimum success count (≥ v4.2 − R) **and** false‑complete ≤15. Using the v4.2 replicate as the noise baseline (instead of v4) is more appropriate because the candidate builds on v4.2.

3. **"More training" test**
   - The fresh‑rows run conflates **more data** with **different data distribution**; therefore it does not isolate the effect of additional epochs. A proper test would keep the data mix constant and only increase epoch count (or use a WSD schedule branch as a control).

4. **Fairness / benchmark‑maxxing**
   - The plan does **not** tune on MobileWorld beyond the required run; however the selection rule uses seed‑30 results (PREREG_v41.md lines 102‑105) which can over‑fit to that noisy seed. The AndroidLab and ScreenSpot‑v2 comparisons are disclosed and use frozen versions, so they are fair. The own‑rollout pilot is clean because it uses non‑benchmark apps.

5. **Feasibility and ordering**
   - With ~5 A100‑hours, the first cut should be the **fresh‑rows run** (since it adds ~57 % new rows without extra compute) and the **guard ablations** (loop/stop guards) if the DPO smoke test fails. The owner’s requested items that remain are:
     - "more training over epochs" → cannot be afforded beyond one epoch (cost ≈ 6 h). 
     - "learn from its own attempts" → DPO is the primary path. 
     - "bigger LoRA?" → not needed (see P1‑3). 
     - "hyperparameters?" → schedule change (WSD) already planned. 
     - "speed vs quality, data variety, benchmarks, overfitting" → covered by gates and fairness checks.

*Overall, the plan is largely sound but requires the fixes listed above before proceeding.*