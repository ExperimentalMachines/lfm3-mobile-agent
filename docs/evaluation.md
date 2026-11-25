# How the benchmarks were run

How each benchmark was set up and kept fair. The offline checks used to judge development rounds (history probes,
early-stop rate, multi-part probes) are explained in [rounds.md](rounds.md#how-a-round-works).

**Contents:** [Fairness at a glance](#fairness-at-a-glance) · [AndroidWorld](#androidworld) ·
[MobileWorld](#mobileworld) · [AndroidControl](#androidcontrol-offline) ·
[General knowledge](#general-knowledge-retention) · [Speed](#speed)

---

## Fairness at a glance

### AndroidWorld (primary comparison: v4 vs GUI-Owl)

| Setting | v4 | GUI-Owl-1.5-2B | Same? |
|---|---|---|---|
| Tasks, seeds, emulator image, harness | AndroidWorld, 116 tasks × seeds 7/1234/2026 | same | yes |
| Screenshots per step | 1 | 1 | yes |
| Step budget, temperature | 10 × task complexity, 0 | same | yes |
| Weights | 4-bit (Q4_K_M) | 4-bit (Q4_K_M) | yes |
| Installed-app list in the prompt | yes | yes | yes |
| Image size | ≤ 880×880 px area (≈ 720 tokens) | ≤ 1,048,576 px (≈ 1,024 tokens) | no: GUI-Owl gets a larger image |
| Prompt and output format | its own (trained) | its official one, ported | no |
| Parse retries | 1 | 0 (an unparseable reply wastes the step) | no |
| AndroidWorld in training data | none (contamination rule) | undisclosed by its authors | unknown |

GUI-Owl is not run in its published setup (5 screenshots at full resolution). That setup took 61 s per step on the
M5 (~10,700 prompt tokens), so a full 116-task run would take about two days per seed. The project targets an
on-device budget of one screenshot.

### MobileWorld (secondary)

| Setting | v4 | GUI-Owl / MAI-UI |
|---|---|---|
| Agent | our adapter | MobileWorld's official agents |
| Screenshots per step | 1 | 1 |
| Image | ≤ 880×880 px area, ≤ 1,024 tokens | full screenshot, ≤ 2,600 tokens |
| Weights | 4-bit | GUI-Owl 4-bit; MAI-UI 8-bit (its 4-bit output degenerates) |

The larger image budgets give GUI-Owl and MAI-UI more visual detail; their effect on accuracy was not isolated.

---

## AndroidWorld

### Setup (all models)

| Item | Setting |
|---|---|
| Benchmark | AndroidWorld @ `55ddaf5` + local patches (below); 116 task templates, 1 instance each |
| Device | Pixel 6 AVD, Android 13 (API 33, arm64); two emulators (ports 5556, 5558) on an Apple M5 Mac |
| Model server | llama.cpp `llama-server` on Metal, one request at a time |
| Weights | 4-bit (Q4_K_M) + 8-bit image projector; MAI-UI 8-bit (Q8_0) |
| Step budget | AndroidWorld default: 10 × task complexity |
| Decoding | Temperature 0 |
| Seeds | Development: 30. Held-out: 7, 1234, 2026 |
| Success | Checker score ≥ 1 **and** the agent ended the episode. Exceptions are failures |

### Per-model settings (held-out runs)

| | v4 | GUI-Owl-1.5-2B (matched) | v1 |
|---|---|---|---|
| Agent code | `eval/androidworld/lfm_agent.py`, prompt v4 | `eval/androidworld/guiowl_agent.py` (official prompt, ported) | `lfm_agent.py`, original prompt |
| Screenshots per step | 1 | 1 | 1 |
| Image | ≤ 880×880 px area (≈ 720 tokens; server cap 1,024) | ≤ 1,048,576 px (≈ 1,024 tokens; server cap 2,600 not reached) | as v4 |
| Context window | 8,192 | 20,480 | 8,192 |
| Installed-app list | yes | yes | no |
| Output | `<think>intent</think>` + one JSON action | `Action:` + `<tool_call>` | as v4 |

Launcher with the exact flags: [`scripts/androidworld/local_sealed_aw_v3.sh`](../scripts/androidworld/local_sealed_aw_v3.sh).

### Local patches to AndroidWorld

Files: `eval/androidworld/android_world_local_fixes.patch`, `eval/androidworld/android_env_no_adb_kill.patch`.
None touches model input/output or scoring.

- App launch works on software-key emulators (`monkey --pct-syskeys 0`).
- The shared adb server is never killed; optional adb server port.
- Directory cleanup is verified; a failed cleanup fails the attempt.
- A crash in `tear_down` is recorded on the episode instead of stopping the suite.
- Resume keeps saved exception episodes as failures; checkpoints are written atomically.

### Held-out protocol (preregistered)

- **Sealed:** results went to `results/androidworld_sealed/`; only episode counts were checked until every model
  had finished that seed.
- **Re-run rule:** an infrastructure crash before step 1 (emulator/adb, not model output) is re-run once.
  Everything else counts as it is.
- **Trajectory review:** checker successes are compared with their saved screenshots (done for all v4 and GUI-Owl
  successes and v1's on seeds 1234/2026). Contradicted successes are listed in `results/aw_checker_disputes.json`
  and enter only a sensitivity analysis.
- **Primary analysis:** paired difference v4 − GUI-Owl over 348 instances; template-clustered sign-flip test
  (10,000 draws, seed 0); 95% CI by test inversion.
- **Decision rule:** non-inferior if the CI's lower bound is above −6.9 points (8 tasks of 116).
- **Development gate:** v4 had to pass a gate on seed 30 and offline checks before it could run held-out. It passed.

Full text and every dated change: [PREREG_v4.md](PREREG_v4.md).

---

## MobileWorld

| Item | Setting |
|---|---|
| Benchmark | MobileWorld @ `a026188`, 105 English GUI-only tasks |
| Environment | Official Docker image (`ghcr.io/tongyi-mai/mobile_world`), on a GCP n2-standard-16 spot VM with nested virtualisation |
| Model servers | llama.cpp `cd959bae9` on a Colab T4 GPU, reached through a restricted reverse SSH tunnel |
| Task settings | 50 rounds, 3 s step wait, `--auto_retry 3`, temperature 0 |
| v4 agent | Our adapter: `eval/mobileworld/lfm3_mw_agent.py` |
| GUI-Owl agent | MobileWorld's official `gui_owl_1_5` agent |
| MAI-UI agent | MobileWorld's official agent, 1 screenshot (`eval/mobileworld/maiui_mw_agent.py`) |

**Completion rule** (fixed 2026-11-19 01:55, before any re-run outcome; in
[`scripts/mobileworld/gcp_mw_resume_vm.sh`](../scripts/mobileworld/gcp_mw_resume_vm.sh)):

| Task ended because… | Handling |
|---|---|
| Setup or scoring failed (HTTP 500 from the environment) | One more invocation in a freshly restarted container (up to 4 executions inside it) |
| VM stop or preemption cut it off, or never reached | Run it |
| Model server unreachable (added before MAI-UI started) | Run it |
| Unsupported action, unparseable output, `ask_user` without a simulator | Failure |

MAI-UI ran in two halves (53/52 tasks, alternating) in parallel containers, after GUI-Owl and v4 had finished.

---

## AndroidControl (offline)

| Item | Setting |
|---|---|
| Data | Official **test** episodes: 1,543 episodes, 8,444 steps |
| Modes | High-level (goal + history → action; headline), low-level (+ step instruction), terminal rows (→ `complete`) |
| History | Teacher-forced (human step instructions + ground-truth actions); an upper bound on closed-loop behaviour |
| Generation | Greedy, ≤ 256 new tokens, bf16 on GPU (`eval/androidcontrol/generate.py`) |
| Scoring | `eval/androidcontrol/score.py`; unparseable output = wrong |

Step success rate counts a step correct if the action type matches and:

| Action | Correct if |
|---|---|
| click, long_press | Point inside the target element's box, or within 14% of the screen of the true point |
| input_text | Normalised exact match or token F1 ≥ 0.5 |
| scroll | Same direction |
| open_app | Case-insensitive match or containment |
| back, home, wait | Type match is enough |

Development splits (GUI-Odyssey, AMEX, ScreenQA, v4 questions) use the same scorer; see [datasets.md](datasets.md).

---

## General knowledge (retention)

- MMStar (1,500 questions) and MMLU (1,000), forced-choice next-token scoring (independent of output format).
- Each fine-tune is compared with its base model on the same questions (paired, exact McNemar).
- Code: `eval/general/eval_general.py`, `eval/general/paired_retention.py`.

---

## Speed

| Measurement | How |
|---|---|
| CPU | 5 screenshots, 1 warm-up + 3 passes, 8 threads; cached calls excluded (14 / 4 / 4 kept) |
| Apple M5 | Model time per step recorded inside the AndroidWorld seed-30 runs, while emulators and other servers were running |
| Phone | Model runs on the phone's CPU (4 threads); 2 calls per model at the evaluation ceiling, 2 × 5 calls at the equal ceiling |

- **CPU host:** idle GCP n2-standard-16; each model's own evaluation agent; [`scripts/speed/bench_speed.sh`](../scripts/speed/bench_speed.sh).
- **Phone:** Qualcomm reference phone via Qualcomm Device Cloud; llama.cpp b12110, RAM prompt cache off; model files
  checked by SHA-256; [`scripts/speed/qdc_chain2.sh`](../scripts/speed/qdc_chain2.sh).

Phone caveats:
- Frequencies are sampled, not controlled.
- GUI-Owl and MAI-UI reused cached system-prompt tokens, which favours them.
- v4's agent sends a 576×1280 screenshot; the others send 1080×2400.

## AndroidLens English (offline, long tasks)

**Evaluation only, never trained on.** Added in round 6 ([PREREG_v44.md](PREREG_v44.md)) because AndroidControl's
episodes are short (median 6 steps) and v4 fails long tasks online.

| Item | Detail |
|---|---|
| Source | [yuecao0119/AndroidLens](https://huggingface.co/datasets/yuecao0119/AndroidLens) @ `984576f3`, `test/en`: 172 episodes, 4,987 steps (median 27.5, p90 43), 42 apps, 93 cross-app (Apache-2.0) |
| Conversion | [`data/v44_androidlens_eval.py`](../data/v44_androidlens_eval.py): v4 prompt, ground-truth history (intents from `low_instruction`), screenshots resized as in training |
| Copy | Frozen in [`MobileAgent-SFT-v4.4`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v4.4) `androidlens/`, checked by sha256 |
| Scorer | [`eval/androidlens/score_androidlens.py`](../eval/androidlens/score_androidlens.py): AndroidControl's step rule (`score.match`); any listed valid alternative counts |
| Metrics | By step bucket (0–4, 5–9, 10–19, 20+): early `status`, terminal `complete`, milestone and prefix progress, episode-bootstrap CIs |

**Action mapping:**

| AndroidLens action | Ours | Unscored |
|---|---|---|
| Tap | `click` | — |
| Swipe | `scroll` (direction = where the content is revealed) | 140: drags, system gestures |
| Long press, type, wait, back, home | `long_press`, `input_text`, `wait`, `navigate_back`, `navigate_home` | — |
| Terminate | `status complete` | — |

Unscored steps stay in the history.

**Caveats:**
- **Ground truth:** there are no element boxes for most clicks (the 0.14 distance rule applies), so the numbers are
  not comparable with the paper's table.
- **Bad hints:** on home screens, `low_instruction` often names the icon one row above the tap (118 steps flagged
  `hint_suspect`).
- **Not a test of online failures:** with ground-truth history, early stops are rare (v4: 0.26%). It does not
  measure the online false-`complete` failure, which happens on the model's own off-track history.
