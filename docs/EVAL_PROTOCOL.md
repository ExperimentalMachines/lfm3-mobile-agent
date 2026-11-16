# Evaluation protocol

Two benchmarks, both run with the **same prompt + action format** used in training
(`train/agent_format.py`): one current screenshot (resized with `smart_resize`, ≤ 880×880 px budget →
576×1280 for a 1080×2400 Pixel screen ≈ 720 image tokens), goal, last 8 steps of text history,
output = short intent in `<think>` + one JSON action with `point_2d` in a 0–1000 grid.

## 1. Offline: AndroidControl test (frozen, official split)

* Data: `experimentalmachines/AndroidControl-screen-agent-sft`, split `test` — official test episode ids
  (1,543 episodes / 8,444 steps). Every step appears in two modes:
  * `high`: goal + history → action (the realistic agent setting; headline number)
  * `low`: additionally given the step instruction ("Current step hint") → measures grounding/execution
  * plus 1,543 `is_terminal` rows (final screen → `status: complete`), reported separately.
* Generation: greedy (`do_sample=False`), max 256 new tokens, HF transformers bf16 on GPU
  (`eval/androidcontrol/generate.py`). Base model evaluated with `enable_thinking=False` (its native
  thinking is long and not trained for this action format); fine-tuned models with
  `enable_thinking=True` (they emit a one-line intent then `</think>`).
* Scoring (`eval/androidcontrol/score.py`, pure python, from raw outputs):
  * **type match**: predicted `action_type` == ground truth
  * **step success rate (SR)**: type match AND
    * click / long_press: predicted point inside the AndroidControl-Curated element bbox **or**
      within 14% of the screen (Euclidean, normalized coords) of the GT point
      (the OS-Atlas/UI-TARS convention); `click_bbox_hit_strict` reports bbox-only accuracy
    * input_text: normalized exact match or token-F1 ≥ 0.5
    * scroll: same direction; open_app: case-insensitive equality/containment
    * navigate_back/home, wait: type match suffices
  * **episode SR**: all steps of an episode correct (offline task-completion proxy)
  * unparseable outputs count as wrong; parse rate reported
  * breakdowns by official subsplit: IDD, app_unseen, task_unseen, category_unseen (overlapping sets)
* Scroll convention: verified empirically that AndroidControl's `scroll down` = content moves up
  (same as AndroidWorld), via phase correlation of consecutive screenshots
  (`results/androidcontrol/scroll_convention_check.json`).

## 2. Online: AndroidWorld (116 tasks)

* Local Pixel 6 AVD, Android 13 (API 33, google_apis arm64), emulator ports 5556/8556, AndroidWorld
  @55ddaf5 with two local patches (`eval/androidworld/*.patch`): monkey `--pct-syskeys 0` (setup on
  software-key emulators) and never killing the shared adb server.
* Model served by **llama.cpp `llama-server` with the Q4_K_M GGUF + Q8_0 mmproj** — i.e. the exact
  quantized artifact that would ship to a phone, not the bf16 GPU model.
* Agent: `eval/androidworld/lfm_agent.py` (screenshot only — no accessibility tree, no SoM),
  temperature 0, one retry on unparseable output, step budget = AndroidWorld default
  (10 × task complexity), `n_task_combinations=1`, `task_random_seed=30`.
* Metric: success rate over 116 task instances; **exceptions count as failures** (upstream drops them
  as NaN). Also: per-difficulty SR (61 easy / 36 medium / 19 hard), self-termination rate, mean
  per-step model latency on an Apple M5 (proxy for on-device cost), mean prompt tokens, parse-failure
  rate (`eval/androidworld/summarize_aw.py`).
* Caveats: single seed (±~4 pp standard error at 116 tasks); a few upstream tasks are known-broken
  (e.g. `AudioRecorderRecordAudioWithFileName`, Wi-Fi tasks); no `answer`-action training data, so
  information-retrieval tasks are expected to be weak.

## 3. Independent check by Codex

Codex CLI (`codex exec`, model from `~/.codex/config.toml`) is given the raw prediction files, the
split files and this protocol, and asked to (a) re-implement the scorer independently and recompute
all offline numbers, (b) audit the splits/builder for leakage, (c) recompute AndroidWorld success
from the episode files and categorize failure modes. Its report: `results/codex_eval_report.md`.
