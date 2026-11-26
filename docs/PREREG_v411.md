# Preregistration: round 13 (v4.11), the right yardstick, then training on the model's own history

Registered 2026-11-26 13:26 Asia/Manila, before any result of step 1 exists.

Owner, after round 12 was launched: "Do you honestly and objectively think this is enough to resolve the encountered
issue … acknowledge the limitation now and resolve it through the data, sequencing, or algorithm. Are we doing something
wrong? Be critical and search/read the literature."

---

## The limitation, stated plainly

| Finding | Evidence |
|---|---|
| A model checking its own "done" catches little | VLAA-GUI ([arXiv 2604.21375](https://arxiv.org/html/2604.21375v1)): frontier backbones with a same-backbone completeness verifier still have 86–92% of failures as "believed it succeeded"; the verifier cut false completions by about 4 points; success moved −2.9 to +2.9 points. Same-family verifiers share blind spots ([2512.02304](https://arxiv.org/html/2512.02304v1)) |
| A blocked false "done" is not a success | GUI-Owl makes 0 false completes on the held-out seeds and scores below v4 (47 vs 54 / 348) |
| **We train and gate on the wrong situation** | Every round trains on human histories (every past step correct) and gates on one-step probes. Failures happen on the agent's own history. UI-S1 ([2509.11543](https://arxiv.org/html/2509.11543v1)): AndroidControl step accuracy explains R² 0.47 of AndroidWorld; a multi-step test keeping the model's own history (SOP) explains 0.93 |
| One symptom per round | Waits, history shortcut, done labels, DPO, done check: each passed its own probe; the early-stop rate never moved. This is causal confusion ([de Haan 2019](https://arxiv.org/pdf/1905.11979)); the reliable cure is training on states the policy itself visits |
| What does work from static data | UI-S1's semi-online RL on AndroidControl + AMEX only: AndroidWorld 21.7 (SFT) → 34.0 at 7B; one-step offline RL gave nothing (15.7) |

Round 12 keeps running (already paid) but is demoted to a harness add-on (its replay gate decides).

---

## Step 1: validate the yardstick (this entry)

**Question:** does a multi-step test on AndroidControl that keeps each model's own history rank our models the way
AndroidWorld does? If yes, it gates every later candidate and the early-stop failure becomes measurable offline.

| Item | Value |
|---|---|
| Test | `eval/androidcontrol/sop.py` (SOP as UI-S1 defines it): AndroidControl test (`MobileAgent-SFT-v4.6` @ `0ace5559`, `test_ac_high`), 400 complete episodes (Random(13)); the model's own intents and actions as history; the first step that does not match the human's (`score.match`) ends the episode |
| Measures | PG (share of steps done before the first miss), TSR (episodes completed), SOP = (PG + TSR) / 2, **premature `status`** (episodes ended by the model saying done while the human still acted), missed `status` |
| Models | The 7 with a seed-30 AndroidWorld pass: v4, v4.1, v4.2, v4.3-dpo2, v4.3-sft, v4.5-D, v4.6-E; each with its own Q4_K_M GGUF and AndroidWorld history options (v4–v4.3: 8 steps, no notes; D: 24 steps, coarse notes; E: 24 steps, fine notes); llama-server with 4 slots, temperature 0 |
| AndroidWorld reference (seed 30, as run) | successes 18 / 12 / 18 / 21 / 24 / 21 / 19; false completes 25 / 24 / 25 / 28 / 37 / 26 / 23 |
| **Validated if** | Spearman ρ(SOP, AndroidWorld successes) ≥ 0.70 (n = 7, one-sided p ≈ 0.04) |
| Also reported | ρ(premature `status`, AndroidWorld false completes); episodes ending on a human `wait` step (a bias against models trained not to wait) |

**Low power, said now:** the seven AndroidWorld numbers span 12–24 and a repeat of v4.2 differed by 1 success and 3
false completes, so ρ on seven points can be noisy either way. A pass makes SOP our gate; a fail means it is not shown to
track AndroidWorld *for these near-identical models*, and step 2 is then gated on AndroidWorld directly.

## Step 2: train on the model's own history (registered in full before any training)

Semi-online RL (UI-S1's recipe) from E on AndroidControl + GUI-Odyssey + AMEX training trajectories: rollouts keep the
model's own history, the human's step patches a mistake, step rewards with discounted future returns, the judge-checked
GUI-Odyssey endings decide when `complete` earns reward. Feasibility first (UI-S1's code and LFM3-VL support; compute).

---

## Log
