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

### 2026-11-26 13:56 Asia/Manila — step 2 registered in full (before any training)

**Feasibility.** UI-S1's public code is a fork of verl pinned to vLLM 0.8.2 and Qwen2.5-VL; running LFM3-VL on it would
mean porting that stack. Instead the method is implemented on our own Transformers + LoRA code
(`train/semi_online_rl.py`, no new dependencies). Local checks on the Mac GPU: the loop runs end to end; on two complete
AndroidControl episodes the 4 rollouts per episode sample different actions and 37 of 37 samples get a non-zero
advantage; one update with A = +1 raises the sampled completion's mean log-probability (−1.25 → −0.56).

**Candidate E-S** (the only one)

| Item | Value |
|---|---|
| Start | E's merged weights; new LoRA r64 / α128 on the language model |
| Episodes | E's training split: AndroidControl (70%) and GUI-Odyssey (30%) episodes with contiguous steps, first 12 steps; AndroidControl's 113 judged-unfinished `complete` steps dropped; GUI-Odyssey endings as judged (done → `complete`, unfinished → Claude's written action); the 400 probe episodes excluded |
| Rollouts | B = 4 episodes × G = 4 rollouts per batch, temperature 1.0, own history (24 steps, fine notes), patch budget 1 |
| Reward / advantage | UI-S1 Eq. 8 step reward (0.1 parseable + 0.4 type + 0.5 action); γ = 0.5 discounted return; A = A_episode + 1.0 × A_step |
| Update | one AdamW step per batch on −A × mean token log-prob (on-policy), lr 3e-5, grad-norm clip 1.0 |
| Size | 100 batches = 400 episodes (set after the smoke's s/batch if needed, logged before the full run) |
| Hardware | SageMaker `ml.g5.2xlarge` (A10G 24 GB, us-west-2; the L4 quota is in use by round 12) |

**Gates, in order (all must hold to go on):**

1. **Offline, same job** (`scripts/training/sm_r13_gate.py`): round 11's first 10 checks (no regression vs E) and the
   GUI-Odyssey ending probes: M_done `status` ≥ 50%, M_notdone `status` ≤ 25%.
2. **Multi-step test on the 4-bit GGUF (Mac):** SOP ≥ E's + 3 points and premature `status` ≤ E's. Applies whatever
   step 1 concludes about AndroidWorld: it is what the training optimises; failing it means the training did not work.
3. **AndroidWorld seed 30** (E's harness): **successes ≥ 22 (E 19), false completes ≤ 23 (E's), useless waits ≤ 5%.**
   Passing sends E-S to the three held-out seeds under E's rule (non-inferior to v4, false completes ≤ 71) with the
   superiority test reported.

If any gate fails: reported, nothing published, and the next step is decided from the data (no new single-symptom patch).

### 2026-11-26 14:24 Asia/Manila — RL smoke passed; full E-S run launched (100 batches, as registered)

- Smoke job `lfm3-r13-es-smoke` (A10G, ~18 billed minutes): episode build on the full split (13,006 AndroidControl and
  1,047 GUI-Odyssey episodes usable; 450 of the latter end in a written next action; 317 probe episodes excluded; 110
  judged-unfinished AndroidControl completes dropped), 2 RL batches (16–32 samples with non-zero advantage each, peak
  6.5 GB), merge, every round-8 eval, both ending probes and the round-13 gate ran ("R13 smoke DONE"; 16-row numbers
  meaningless).
- Smoke timing (B 2, ≤ 6 steps): 30–45 s per batch, so the full setting (B 4, ≤ 12 steps) is estimated at ~3 min per
  batch: **100 batches ≈ 5 h**, plus merge and evals. Size unchanged from the registration.
- Full job `lfm3-r13-es` launched (`R13_BATCHES=100`, lr 3e-5, 12 h limit, resumable).

### 2026-11-26 15:00 Asia/Manila — external review: four defects confirmed; E-S stopped

The owner asked for an adversarial review by Codex (`gpt-6.1-sol`, medium; read-only, no network; redacted transcript +
repository). Report: [`docs/reviews/codex-adversarial-review-2026-11-26.md`](../reviews/codex-adversarial-review-2026-11-26.md).
Checked against the code and notes before acting:

| Finding | Check | Consequence |
|---|---|---|
| C1: returns run across the human patch, so a wrong action is credited with progress the patch made possible | Confirmed: our own UI-S1 notes (`docs/research/notes/training-on-own-mistakes-and-overfitting/own_mistakes_methods.md`) sum returns only to the end of the naturally matching segment; `semi_online_rl.py` sums across patches | The "stopping early forfeits later reward" mechanism is not enforced |
| M2: the 12-step cap drops the endings round 13 was built to teach | Confirmed: 371 / 619 written next actions and 468 / 947 judged-done endings sit at step ≥ 12 and are cut | Most GUI-Odyssey endings never reach training |
| M4: AndroidControl's own "done" verdicts failed their spot check in round 10 (26 / 32, bar 28; "labels not used") yet are used | Confirmed (`docs/rounds.md`, round 10 table) | Round 12 trains 1,003 done-check rows from them and removes 129 replay rows; round 13 drops 110 completes |
| M10: after a blocked `complete` the grammar still allows `answer`, which ends the episode unchecked | Confirmed (`lfm_agent.py`, `ag.grammar({"status"})`) | A blocked "done" can turn into an ending the check never sees |

- **E-S (job `lfm3-r13-es`) stopped at about batch 20 of 100** (checkpoint kept). It is not evaluated: its credit
  assignment and episode set are not what was registered in intent. A corrected run is a new, separately registered
  experiment.
- Round 12 (E-V) keeps training; its AndroidControl done-check rows come from the failed label source (a registered but
  wrong choice), so E-V's results will be reported with and noted as confounded by that. The `answer` loophole is
  fixed in the harness before any online run (logged when made).
- Also accepted: my statement "every round trains on human histories" was overstated (v4.2 replayed its own
  histories); starting E-S before the yardstick was validated contradicted "fix the yardstick first"; the
  E / D false-complete references above (23 / 26) are the as-run counts, the rerun-adjusted ones are 24 / 27.
