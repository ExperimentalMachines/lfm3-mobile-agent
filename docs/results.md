# Results

Every number below is read from a file in [`results/`](../results/); each section names its source.
To recompute them all, see [reproduce.md](reproduce.md).

**Contents:** [AndroidWorld held-out](#androidworld-held-out-seeds-primary) ·
[AndroidWorld development seed](#androidworld-development-seed-30) · [MobileWorld](#mobileworld) ·
[Speed](#speed) · [Offline evaluations](#offline-evaluations)

---

## AndroidWorld, held-out seeds (primary)

Preregistered comparison ([PREREG_v4.md](PREREG_v4.md)): 116 tasks × seeds 7, 1234, 2026; one run per model per seed.
Source: [`results/sealed_analysis_final.md`](../results/sealed_analysis_final.md) (+ `.json`).

### Scores

| Model | Seed 7 | Seed 1234 | Seed 2026 | Total / 348 | Answer tasks / 75 | Action tasks / 273 |
|---|---|---|---|---|---|---|
| **LFM3-VL-2B v4** | 18 | 17 | 19 | **54 (15.5%)** | 13 | 41 |
| GUI-Owl-1.5-2B (matched) | 16 | 13 | 18 | 47 (13.5%) | 19 | 28 |
| LFM3-VL-2B v1 | 11 | 10 | 11 | 32 (9.2%) | 0 | 32 |

- Success = AndroidWorld's checker says the task is done **and** the agent ended the episode.
- Exceptions count as failures.
- "Answer tasks" (25 per seed) need a typed answer; v1 never learned to answer.

### Comparisons (paired, template-clustered sign-flip test, 10,000 draws)

| Comparison | Difference | 95% CI | p | Verdict |
|---|---|---|---|---|
| **v4 − GUI-Owl (primary)** | **+2.0 pts** | [−4.5, +8.6] | 0.60 | **Non-inferior** (lower bound > −6.9); not superior |
| v4 − v1 | +6.3 pts | [+1.1, +11.5] | 0.02 | v4 better |
| v1 − GUI-Owl | −4.3 pts | [−10.6, +1.9] | 0.21 | No significant difference |

Per-seed exact McNemar tests for v4 − GUI-Owl: p = 0.85, 0.52 and 1.0. No single seed is significant.

### Sensitivity analyses

Source: [`results/sealed_sensitivity_final.md`](../results/sealed_sensitivity_final.md). None of these was preregistered.

| Variant | v4 | GUI-Owl | Difference | 95% CI | Non-inferior? |
|---|---|---|---|---|---|
| A. Primary | 54 | 47 | +2.0 | [−4.5, +8.6] | yes |
| B. Drop the 7 pairs that still end in an exception | 54 | 44 | +2.9 | [−3.4, +9.3] | yes |
| B3. Drop 3 templates with scoring-phase exceptions (all seeds) | 54 | 43 | +3.2 | [−3.1, +9.6] | yes |
| **C. Count v4 seed 1234's 113 re-runs as failures** | 37 | 47 | **−2.9** | [−8.4, +2.7] | **no** |
| D. Exclude seed 1234 | 37 | 34 | +1.3 | [−5.8, +8.4] | yes |
| Disputed checker successes counted as failures | 53 | 47 | +1.7 | [−4.8, +8.3] | yes |

**Key point:** only variant C fails. In C, the preregistered "re-run once if the emulator crashed before step 1"
rule is not applied to v4's seed-1234 episodes. Emulator 2 hung from 00:35 to 08:06 on 2026-11-19, and every v4
seed-1234 episode in that window crashed during task setup.

### Re-runs and exceptions

| Arm | Episodes re-run once (setup crash before step 1) | Still an exception after re-run |
|---|---|---|
| v4 | seed 7: 4 · seed 1234: 113 | seed 1234: 4 (counted as failures) |
| GUI-Owl | seed 7: 1 · seed 1234: 1 · seed 2026: 2 | none |
| v1 | seed 2026: 1 | none |

Not re-run, counted as failures (the crash was not before step 1): v4 seed 1234 BrowserDraw,
v4 seed 2026 SimpleSmsReplyMostRecent, GUI-Owl seed 1234 SimpleSmsSendReceivedAddress.

### Disputed checker successes

Every checker success was compared with its saved screenshots. Two contradict the screens. They stay successes in
the primary score and count as failures only in the sensitivity row above.

| Arm | Seed | Task | Why disputed |
|---|---|---|---|
| v4 | 7 | ClockStopWatchPausedVerify | Stopwatch left running |
| v1 | 2026 | OpenAppTaskEval | Opened Contacts, then deleted the only contact before finishing |

Source: [`results/aw_checker_disputes.json`](../results/aw_checker_disputes.json).

### Known limits

- **Device state is not fully reset between episodes (all models).** AndroidWorld's app-snapshot restore is
  skipped ("Snapshot not found"), so data a task's own setup does not clear can carry over. Bias direction is unknown.
- **Power is limited.** Cluster standard error is about 3.25 points. Detecting superiority with 80% power would need
  about a 9-point true gap.
- **A harness defect affects all models:** gRPC warnings on adb's error output can corrupt adb replies during task
  setup. Those crashes fall under the re-run rule.
- **The interval is nominal.** The 95% CI comes from inverting the sign-flip test, so it assumes symmetric paired
  differences and exact coverage is not guaranteed.
- **GUI-Owl runs in our harness, not its own.** It gets one screenshot at ≤ 1,048,576 pixels and 4-bit weights,
  not its published configuration of 5 screenshots and full resolution. Its published AndroidWorld score is 67.9%.

---

## AndroidWorld, development seed 30

Seed 30 was used to choose between versions, so these are development numbers. Source:
[`results/androidworld/dev_seed30_summary.md`](../results/androidworld/dev_seed30_summary.md).

| Model | Successes / 116 | Answer / 25 | Action / 91 | Exceptions | Apple M5 s/step (median) |
|---|---|---|---|---|---|
| **LFM3-VL-2B v4 (final)** | **18** | 6 | 12 | 4 | 2.96 |
| MAI-UI-2B (1 screenshot, 8-bit) | 32 | 5 | 27 | 1 | 9.35 |
| GUI-Owl-1.5-2B (1 screenshot) | 23 | 10 | 13 | 0 | 7.00 |
| Qwen3.5-2B v1 | 16 | 0 | 16 | 2 | 4.20 |
| LFM3-VL-2B v1 | 15 | 0 | 15 | 2 | 2.66 |
| LFM3-VL-2B v3 | 13 | 0 | 13 | 3 | 2.61 |
| Qwen3.5-0.8B v1 | 12 | 0 | 12 | 1 | 2.00 |
| LFM3-VL-2B v1 + runtime feedback (ablation) | 10 | 0 | 10 | 7 | 2.85 |
| LFM3-VL-2B v2 + forced intent (ablation) | 6 | 0 | 6 | 4 | 2.68 |
| LFM3-VL-2B v2 | 3 | 0 | 3 | 5 | 2.61 |
| LFM2.5-VL-450M v1 | 2 | 0 | 2 | 4 | 1.14 |
| LFM3-VL-2B base | 1 | 0 | 1 | 2 | 2.13 |
| LFM2.5-VL-450M base | 0 | 0 | 0 | 3 | 2.21 |

- **MAI-UI-2B is the strongest model on this seed.** It ran later as an extra arm and is not part of the
  preregistered comparison. It needs 8-bit weights because its 4-bit output degenerates
  ([`results/maiui_quant_check.md`](../results/maiui_quant_check.md)). Its official prompt lists AndroidWorld's apps.
- GUI-Owl's seed-30 run did not get the installed-app list that v4 gets. The held-out runs give it to both.
- v4 passed its preregistered development gate on this seed ([`results/v4_gate_seed30.txt`](../results/v4_gate_seed30.txt)).

---

## MobileWorld

Secondary and descriptive: 105 English GUI-only tasks, one run per model, temperature 0, 50 rounds per task.
This compares agent pipelines, not model weights alone. Source:
[`results/mobileworld/mw_r2_comparison.md`](../results/mobileworld/mw_r2_comparison.md) (+ `.json`).

### Scores

| Model | Successes / 105 | Tasks with a result | No result (counted as failure) |
|---|---|---|---|
| GUI-Owl-1.5-2B (official agent) | **22 (21.0%)** | 102 | 3 |
| MAI-UI-2B (official agent, 8-bit) | 11 (10.5%) | 98 | 7 |
| LFM3-VL-2B v4 | 6 (5.7%) | 104 | 1 |

### Paired comparisons (exact McNemar)

| Comparison | Both solved | Only first | Only second | Difference | p |
|---|---|---|---|---|---|
| v4 vs GUI-Owl | 6 | 0 | 16 | −15.2 pts | 3.05 × 10⁻⁵ |
| MAI-UI vs v4 | 4 | 7 | 2 | +4.8 pts | 0.18 |
| MAI-UI vs GUI-Owl | 9 | 2 | 13 | −10.5 pts | 0.0074 |

### Sensitivity (environment problems)

| Tasks kept | v4 | GUI-Owl | MAI-UI |
|---|---|---|---|
| All 105 | 6 | 22 | 11 |
| 97: drop tasks with a setup/scoring failure in the v4 or GUI-Owl run | 6 | 22 | — |
| 87: also drop tasks where v4's or GUI-Owl's device was re-initialised | 5 | 21 | — |
| 89: drop the 16 tasks with an environment problem in MAI-UI's run | 6 | 21 | 11 |

- **What-if, not a bound:** if MAI-UI had solved the 5 tasks it lost to final setup failures, it would score 16
  vs GUI-Owl's 22 (p = 0.26). GUI-Owl and v4 solved none of those 5.
- MAI-UI ran last, on recreated containers after two spot-VM preemptions. Its emulators crashed with a fatal KVM
  error 17 times. The GUI-Owl and v4 container logs no longer exist, so whether they saw the same crashes is unknown.

### Settings per model

| Setting | v4 | GUI-Owl | MAI-UI |
|---|---|---|---|
| Screenshots per step | 1 | 1 (official default) | 1 (official default 3) |
| Text history | last 8 intent/action pairs | all earlier step summaries | official |
| Image budget | ≤ 880×880 px area, ≤ 1,024 tokens | full screen, ≤ 2,600 tokens | full screen, ≤ 2,600 tokens |
| Weights | 4-bit | 4-bit | 8-bit |
| Parse attempts | 2 | 5 | official |

### Harness notes (disclosed, not corrected)

- **No user simulator:** `ask_user` needs an LLM-backed simulator this setup lacks. GUI-Owl hit it in 7 executions
  and MAI-UI in 14. v4 has no such action.
- **Typing and Enter cost v4 rounds:** its adapter sends Enter as an extra round after typing. In 3 tasks the
  Enter fell on round 50 and was never sent. 37 tasks that hit the budget had fewer than 50 model decisions.
- **One task fails for every model:** ThanksgivingPrepTask setup failed on every attempt.
- **Discarded runs:** v4's first run (5/105) used an adapter that changed v4's scroll and Enter behaviour, so it is
  not counted. GUI-Owl's first run lost its model server after 4 tasks and was discarded.

---

## Speed

v4 sends far fewer prompt tokens per step (a smaller image) and processes them faster.

### CPU (Intel Xeon 2.8 GHz, 8 threads, idle GCP n2-standard-16)

Same 5 screenshots and goals for every model, through each model's own evaluation agent; 4-bit models, llama.cpp
`cd959bae9`. Source: [`results/speed/speed_t8.md`](../results/speed/speed_t8.md).

| Model | s/step (median) | Prompt tokens | Prompt tokens/s | Output tokens | Server memory |
|---|---|---|---|---|---|
| **v4** | **6.4** | 803 | 149 | 28 | 2.8 GB |
| GUI-Owl-1.5-2B | 58.0 | 2,570 | 47 | 47 | 7.5 GB* |
| MAI-UI-2B | 58.2 | 2,575 | 48 | 90 | 7.4 GB* |

\* Inflated by llama.cpp's RAM prompt cache. Model files are 1.30 GB (v4) and 1.55 GB (GUI-Owl, MAI-UI at 4-bit).

### Apple M5 GPU, measured inside the AndroidWorld seed-30 runs

Source: [`results/androidworld/dev_seed30_summary.md`](../results/androidworld/dev_seed30_summary.md).

| Model | Weights | Steps timed | s/step median (p10–p90) | Prompt tokens | Output tokens |
|---|---|---|---|---|---|
| **v4** | 4-bit | 1,706 | **2.96** (1.7–4.6) | 1,303 | 22 |
| GUI-Owl-1.5-2B | 4-bit | 2,228 | 7.00 (4.6–10.4) | 2,106 | 47 |
| MAI-UI-2B | 8-bit | 2,053 | 9.35 (6.2–13.9) | 2,086 | 51 |

### Phone (Qualcomm reference phone, Snapdragon 8 Elite Extreme Gen 6, CPU, 4 threads)

Model runs on the phone (llama.cpp b12110); compared at the same sampled core frequency (~2.65 GHz).
Source: [`results/qdc/speed_qdc_v6.md`](../results/qdc/speed_qdc_v6.md).

| Setting | v4 | GUI-Owl-1.5-2B | MAI-UI-2B (8-bit) |
|---|---|---|---|
| As evaluated (image ceiling: v4 1,024 tokens, others 2,600) | **~39 s** | ~1,100 s | ~1,063 s |
| Same 1,024-token ceiling for all | **~39 s** | ~198 s | ~183 s |

- GUI-Owl and MAI-UI reused 460–990 cached prompt tokens per call; v4 reused none. This favours them.
- The phone throttled under sustained load (fastest core 4.03 → 2.65 GHz), so the equal-ceiling runs used both
  model orders.
- An earlier Pixel 9 attempt (Firebase device streaming) measured v4 only, at 74.4 s/step with heavy throttling
  ([`results/devstream/`](../results/devstream/)).

---

## Offline evaluations

### AndroidControl test (official split, 8,444 steps) and general knowledge

Source: [`results/SUMMARY.md`](../results/SUMMARY.md) and [`results/V2_COMPARISON.md`](../results/V2_COMPARISON.md).
Step success rate; history is teacher-forced, so this is an upper bound on closed-loop behaviour.

| Model | High-level step SR | Low-level step SR | "complete" accuracy | MMStar | MMLU |
|---|---|---|---|---|---|
| LFM3-VL-2B base | 0.313 | 0.634 | 0.000 | 52.1% | 48.9% |
| LFM3-VL-2B v1 | 0.715 | 0.948 | 0.792 | 57.1% | 49.5% |
| LFM3-VL-2B v2 | 0.716 | 0.893 | 0.732 | 54.6% | 50.9% |
| LFM3-VL-2B v3 | 0.723 | 0.902 | 0.725 | 55.3% | 50.0% |
| LFM3-VL-2B v4 | 0.728 | — | — | — | — |
| Qwen3.5-2B v1 | 0.734 | 0.949 | 0.784 | 57.3% | 53.7% |
| Qwen3.5-0.8B v1 | 0.694 | 0.942 | 0.745 | 48.9% | 45.2% |
| LFM2.5-VL-450M v1 | 0.536 | 0.862 | 0.561 | 39.3% | 39.2% |

- No significant drop in general knowledge was detected for any fine-tune.
- MMStar rose after fine-tuning for every 2B model (paired McNemar, 95% CIs in `results/general/`).

### v4 development gate and v4-RL promotion

Sources: [`results/v4_gate_seed30.txt`](../results/v4_gate_seed30.txt),
[`results/v4rl_promotion_offline.json`](../results/v4rl_promotion_offline.json).

| Check | Threshold | v4 | v4-RL | Result |
|---|---|---|---|---|
| Strict answer match on held-out questions | v4 ≥ 0.20; RL ≥ v4 + 0.05 | 0.868 | 0.890 | v4 pass; RL fail |
| False answers on action goals | ≤ 0.03 | 0.00 | 0.00 | pass |
| AndroidControl high-level step SR | RL ≥ v4 − 0.02 | 0.728 | 0.667 | RL fail |
| AndroidWorld seed 30 | ≥ 3 answer successes; action ≥ v3 − 3 | 6; 12 (v3 13) | not run | v4 pass |

**Outcome:** v4 was frozen as the final model. v4-RL was not promoted.
