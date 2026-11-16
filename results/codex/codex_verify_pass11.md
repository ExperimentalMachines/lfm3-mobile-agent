**Adversarial QA pass 11 — the pass-10 restart blocker is fixed in both chains.**

Verified on 2026-11-17 at `3e40b9ea1e23bcb4db7a11fd79479ea1d299d7cd` for Qwen3.5-2B and Qwen3.5-0.8B. The only runtime change since pass 10 is [the watcher rebinding](/Users/alpha/lfm3-android/scripts/chain_next_job.sh:19). This audit exercised production Python/Bash with local dependency/model/Colab stubs, remapped paths, shortened waits, and the same cosmetic stderr-filter removal used in pass 10. No GPU training, live VM, real upload, or model loadability was verified.

| Check | Fixed / not fixed | Classification and observed result |
|---|---|---|
| Interrupted A, replacement B | **Fixed** | **Former blocker cleared, both chains.** SIGKILL A after its genuine `running` status; start B while A's file remains. Watcher observes B running, then B exiting 0, and launches the successor exactly once with heartbeat confirmation. |
| Stale exit before any observed running | **Fixed** | Both old exit-0 and exit-7 files are ignored through B's startup. Uploads and launch occur only after the newly observed B terminates. |
| Normal single run | **Pass** | Both chains wait while the real predecessor runs, then launch exactly once after that same run exits 0. No upload occurs before completion. |
| Old exit after rebinding | **Fixed** | Replaying genuine A-running, B-running, A-exit, B-exit statuses in both chains ignores A's exit and hands off only after B's exit. |
| Partial restore / identity / row and manifest hashes | **Fixed** | Pair members use one Hub revision; missing members regenerate. Orphan predictions, wrong/missing row hashes, absent/blank manifest hashes, changed `min_pixels`, and interrupted mixed-pair uploads are refused. |
| Thinking prefill | **Fixed** | Actual Jinja `<think>` prefill is retained in saved output; both parsers reject unclosed thoughts. Closed/no-think controls pass. |
| Scroll/status types | **Fixed** | List/dict/bool/numeric inputs cause no parser or AW `step()` type crash; valid retries work. Lenient null status retains its complete default. |
| Matched no-think FT | **Fixed** | Both pipelines certify the complete high-level subset with `score.py --modes high`. Missing rows/scorer failure exits 1; orphan `.done` cannot bypass scoring. |
| Frozen GT / flattened VM default | **Fixed** | Missing manifest or SHA mismatch exits 2; flattened scorer finds `work/meta/androidcontrol_test_gt.jsonl`. Repository GT matches its manifest: 18,415 unique keys. |
| Receipt validity / recipe binding | **Fixed for requested scope** | Model/out and all seven tested recipe-field mismatches retrain. Empty/torn/incomplete receipts and missing/wrong-size merged weights retrain; matching receipts reuse. |
| Cached metrics / `metrics_ok` | **Fixed** | All three AC evaluations rescore current predictions. Misleading metrics cannot bypass checks; invalid/missing artifacts trigger generation attempts; invalid GT fails the pipeline. |
| Retraining / stale policy | **Fixed, fails closed** | Changed weights reject old Hub predictions and perform fresh FT inference. Old local thinking/pixel policies exit 1 without new certification; cleanup before retry remains an operational residual. |
| Mandatory upload failures | **Fixed** | All-upload, merged-only, and evaluation-only failures exit 1; warning-only partial pushes cannot mask mandatory failures. |
| `meta`, GT/manifest, `jobs.json` | **Fixed** | Same-session and fresh launchers create/upload required artifacts and abort on failures, including `Uploaded` text with exit 17. |
| Heartbeat / VM loss | **Fixed** | Immediate client exit, absent heartbeat, and heartbeat-then-exit fail confirmation. Live heartbeat passes; `404` with exit 1 triggers replacement/bootstrap. |
| Prerequisite / legacy job | **Fixed** | With previous local merged weights absent, 2B uses `experimentalmachines/LFM3-VL-2B-AndroidControl`. Legacy job remains absent. |
| AW answer execution / IR scoring | **Fixed** | Actual upstream cache/episode/IR/suite functions award 1 only for the executed correct answer. Wrong/empty/malformed answers and correct cache without `done` score 0. Execution failure stays open; successful retry scores 1. |
| General-summary crash recovery | **Fixed** | Both pipelines recover from interrupted `.tmp`, empty, and torn summaries. |
| Failed predecessor policy | **Acceptable, unchanged** | Matching exit 7 logs `WARNING` and launches the independent successor; stale exit 7 alone cannot authorize launch. |
| Same-size weight mutation beyond hashed 4 MiB prefix | **Not fixed** | **Nonblocking residual:** deliberate tail mutation preserves the fingerprint, as in pass 10. |
| Adapter deleted after receipt creation | **Not fixed** | **Nonblocking residual:** receipt gate still accepts the otherwise matching merged export. This checks receipt acceptance, not successful real adapter upload. |
| Trainer exits 17 after valid completion receipt | **Accepted, unchanged** | **Nonblocking residual:** pipeline accepts the valid completed receipt; the fixture does not certify incomplete training. |

**Blocking findings: none reproduced.** In the restart fixtures, the updated watchers downloaded A's stale running status 13 times (2B) and 12 times (0.8B), subsequently observed B running, and handed off on the first downloaded B exit. Event-order assertions verified every upload followed B's terminal status and each successor launched once. All lifecycle statuses came from the actual runner. [Lifecycle evidence](/private/tmp/codex-pass11-1nwnigbr/status_lifecycle_results.json), [event-order checks](/private/tmp/codex-pass11-1nwnigbr/lifecycle_order_checks.json), [normal controls](/private/tmp/codex-pass11-1nwnigbr/normal_results.json), [terminal guard](/private/tmp/codex-pass11-1nwnigbr/terminal_guard_results.json).

As a sensitivity control, the identical crash fixtures using the pass-10 watcher still timed out after 12 seconds without launching, despite downloading B's terminal status 13 and 15 times respectively. This distinguishes the fix from a fixture that never reproduced the bug. [Old-code controls](/private/tmp/codex-pass11-1nwnigbr/negative_control_results.json).

[Evidence index](/private/tmp/codex-pass11-1nwnigbr/evidence_index.json): 28 generation/scoring checks, 94 pipeline cases, 44 chain/launcher cases, eight real-runner lifecycle cases, two terminal-guard replays, two old-code controls, plus retraining, summary recovery, partial-upload, GT, and AW checks. AW commit: `55ddaf5edc6f6c25673aed343907d5b9dca66f84`. One initial replacement-VM fixture exceeded its five-second harness deadline during uploads; the unfinished chain cases passed with a 30-second deadline and unchanged production code. The original timeout and successful continuation are both retained in the [harness record](/private/tmp/codex-pass11-1nwnigbr/chain_regression_summary.json). Reproduce in fresh temporary fixtures with `python3 -B /private/tmp/codex-pass11-1nwnigbr/rerun.py`.

Only this report was written in the repository by this audit. Tested sources/configuration, frozen GT, upstream files checked, and HEAD remained unchanged. Concurrent live logging and AW output are recorded separately in the [file verification](/private/tmp/codex-pass11-1nwnigbr/source_verification.json).

**Final decision: GO for both chains within the reviewed orchestration and integrity scope.** The sole realistic pass-10 blocker is cleared; the listed residuals remain nonblocking under the same scope.
