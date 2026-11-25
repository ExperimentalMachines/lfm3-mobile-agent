# Preregistration: round 11 (v4.9 mix), finishing multi-part tasks

Written 2026-11-25 20:12 Asia/Manila, before the round-11 mix or candidate exists. Owner: "Proceed" (to the round-10
wrap-up's proposal: train E further on the confirmed GUI-Odyssey final steps). Append-only.

**Status: post-hoc development round.** AndroidWorld seed 30 is the development seed; the sealed held-out v4 result
stays as it is.

---

## Why

| Finding | Evidence |
|---|---|
| E's false completes are mostly partly done multi-part tasks | 10 of E's first 19 false completes on AndroidWorld (`docs/PREREG_v48.md`) |
| E learned when to stop only from short tasks | Real `complete` rows in E's data: AndroidControl 11,075 (6.3 steps per episode), MemGUI 99; GUI-Odyssey and AMEX 0 |
| Trustworthy multi-part final steps now exist | 947 of 1,766 GUI-Odyssey terminal candidates judged done by the calibrated judge (Claude Opus 5.5, owner's definition of done; 51 / 56 = 91% on fresh by-eye labels) |
| A penalty alone did not move E | E-DPO, 342 pairs, 11 optimizer steps: unchanged from E (round 10) |

---

## Data: the v4.9 continuation mix

Built inside the training job by `data/r11_mix.py` (seed 11) from public or committed inputs: E's training split
(`experimentalmachines/MobileAgent-SFT-v4.6` @ `0ace5559`, train), the 1,766 candidates (`ody_term2.parquet`, sha256 `c171f2ee11c75b28…`, from
`data/v48_odyssey_terminals.py` + `data/v48_odyssey_filter.py`) and the judge's verdicts
(`results/v48_dev/claude_ody_terminal_verdicts.jsonl`).

| Part | Rows | Rule |
|---|---|---|
| **GUI-Odyssey final steps, judged done** | 747 | Terminal screen + the episode's full history, rebuilt from E's own last training row of the episode → `status complete`. The rebuilt text must equal the text the judge saw; otherwise the build stops |
| Counterfactual rows of those episodes | about 1,490 | v4.8's rules: *stale* (screen before the last action, that action noted "[no visible change]" → redo it; every episode), *ahead* (screen 2–3 actions before the end, full history → that screen's action; half), *short* (final screen, history without its last 1–2 lines → `status complete`; half) |
| E's real rows 1–3 actions before the end of those episodes | about 2,200 | Unchanged: the same goals, not done yet |
| Replay | the rest of 32,000 | Uniform from E's training split |
| Probe **M_done** (held out, never trained) | 200 | Random among the 947 judged done |
| Probe **M_notdone** (never trained) | 819 | Every candidate the judge says is not done: where a human annotator stopped too early |

- Expected `status` share: about 9.7% of the mix (E's split: 7.2%).
- Contamination rules unchanged: nothing from AndroidWorld, MobileWorld or AndroidLab.
- Label noise: on the GUI-Odyssey calibration, 26 / 28 of the judge's "done" and 25 / 28 of its "not done" verdicts
  matched the by-eye labels.

---

## Candidate E-T (the only one)

| Item | Value |
|---|---|
| Start | E's merged weights (`experimentalmachines/LFM3-VL-2B-MobileAgent-v4.6-E`; the S3 copy used by round 10) |
| Recipe | A new LoRA (r64, α128, language model only) on E: lr 1e-4 cosine, 3% warm-up, 32 rows per step, **1,000 steps = one pass over the mix** (round 9's candidate-F recipe, `docs/PREREG_v47.md`) |
| Hardware | SageMaker ml.g6e.2xlarge (1x L40S), `scripts/training/sm_r11.sh` |
| Smoke job first | Mix on 40 rows per class, 30 steps at two micro-batches (speed and memory), then every eval, scorer and gate on 16 rows. The micro-batch comes from it (32 rows per step either way) |
| Cost | About $2 for the smoke run and $10 for the full run (about 3.5 h at $2.80/h) |

---

## Offline gate (all must hold)

E's round-8 gate on the v4.6 splits (`scripts/training/vm_r8_eval.sh`), same evaluator, plus the two new probes. E and
E-T are run on the probes in the same job.

| Check | Bar | E |
|---|---|---|
| Round-8 bars E passes (8): AndroidControl step accuracy, `dev_answer`, `dev_complete`, AndroidLens steps ≥ 10, C3n, C3, T, C2 | Unchanged (`docs/PREREG_v46.md`) | all pass |
| AndroidControl `status` ≥ 2 steps before the end | **≤ 3.80%** | 3.55% |
| Probe C1: unfinished screen, history claims every step | **≤ 22%** | 20.0% |
| **M_done**: share of `status` | **≥ E's + 10 points, and ≥ 50%** | measured in the job |
| **M_notdone**: share of `status` | **≤ E's + 5 points** | measured in the job |

- The two bars E fails are set to "no worse than E by more than about one standard error". This round targets
  multi-part completion, not the history shortcut; E failed both bars narrowly. The online test decides.
- The 5-point allowance on M_notdone covers the done screens among the judge's "not done" verdicts (about 1 in 9).
- `scripts/training/sm_r11_gate.py`.

---

## Online test (only if the offline gate passes)

| Item | Value |
|---|---|
| Benchmark | AndroidWorld seed 30, 116 tasks, Mac, Q4_K_M GGUF |
| Harness | E's: `--history_steps 24 --nochange_notes --change_rule fine` |
| **Pass** | **False completes ≤ 15 (E: 24), successes ≥ 19 (E's), and useless waits ≤ 5% of steps (E: 2.3%)** |
| Reported | Against E: repeated taps, waits, false completes by type (by eye, as in round 10); harness errors re-run once and reported both ways |

**If it passes:** E-T and the new rows (terminal rows, counterfactual rows, both probes) are published in
experimentalmachines. **If not:** results are reported and nothing is published.

---

## Log

### 2026-11-25 20:35 Asia/Manila — inputs checked; smoke job queued (no candidate exists)

- Inputs uploaded to S3 (`r11/in/`: `ody_term2.parquet`, the verdicts). Before any paid run, a text-only check rebuilt
  every candidate's history from E's training split: **1,766 / 1,766 identical** to the text the judge saw, 0 missing.
- Smoke job `lfm3-r11-et-smoke` (ml.g6e.2xlarge) submitted 20:12; SageMaker reports "waiting for capacity" (nothing
  billed while waiting).

### 2026-11-26 00:52 Asia/Manila — hardware changed to L4 before any training (no candidate exists)

- The L40S smoke job waited 4 h 40 min for capacity and was stopped (never started, nothing billed).
- New hardware: **SageMaker ml.g6.2xlarge (1x L4, 24 GB)**, the hardware of round 9's measurements. Nothing else
  changes: same data, recipe (32 rows per step, 1,000 steps), evals and gate.
- Smoke micro-batches for 24 GB: **2 x 16 without gradient checkpointing** (round 9: 18.0 s/step, 21.1 GB peak) and
  **4 x 8 with it**. The full run uses the faster one that fits.
- Cost revised: about $1 for the smoke run; the full run is about 5 h of training plus the evals, about $9 at $1.22/h.

### 2026-11-26 01:45 Asia/Manila — L4 smoke passed; full run launched (no candidate exists yet)

- Smoke job `lfm3-r11-et-smoke2` (ml.g6.2xlarge, 43 billed minutes): mix, both training configurations, both M probes
  for E and the smoke model, every round-8 eval, both gates and the round-11 gate ran end to end ("SMOKE OK"; numbers on
  16 rows are meaningless by design).
- Speed: **2 x 16 without checkpointing 18.1 s/step, peak 20.95 GB**; 4 x 8 with checkpointing 35.0 s/step, peak 8.8 GB.
  The full run uses 2 x 16 without checkpointing (the faster one that fits): 1,000 steps ≈ 5 h.
- Smoke mix (40 rows per class): 80 / 80 rebuilt histories identical to the judged text; `status` share 7.4% (E's
  training split 7.2%).
- Full job `lfm3-r11-et` launched with `R11_BS=2 R11_GA=16 R11_GC=nogc`, 10 h limit, checkpoints to S3 (resumable).
