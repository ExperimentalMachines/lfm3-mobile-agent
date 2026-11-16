**Adversarial QA pass 10 — NO-GO for both Qwen3.5-2B and Qwen3.5-0.8B chains.**

Reproduced locally on 2026-11-16–17 at `fb41e8cac68dfee423b6c757936ed0fca5aef695`. Production Python/Bash with dependency/CLI stubs; no GPU, live VM, training, or real uploads. Fixtures remap paths, shorten waits, and remove cosmetic stderr filters. Synthetic weights establish control flow, not loadability.

| Check | Fixed / not fixed | Reproduced result |
|---|---|---|
| 1. Partial restore / identity | **Fixed** | Pair downloads use one revision; missing members regenerate. Orphan predictions and wrong/missing row hashes are refused. Manifest includes `min_pixels`; changing it is refused. Interrupted mixed-pair uploads are rejected. |
| 2. Thinking prefill | **Fixed** | Real Jinja prompt ending in `<think>` produces prefixed saved output; both parsers reject unclosed thoughts. Closed/no-think controls pass. |
| 3. Scroll/status types | **Fixed** | List/dict/bool/numeric arguments cause no `TypeError` in lenient/strict parsing or AW `step()`. Failed attempts and valid retries work. Lenient null status still defaults to complete. |
| 4. Matched no-think FT | **Fixed** | Both pipelines certify the complete subset with `score.py --modes high`. Missing rows/scorer failure exits 1; orphan `.done` cannot bypass scoring. |
| 5. Frozen GT / VM default | **Fixed** | Missing GT manifest or SHA mismatch exits 2. Flattened scorer finds `work/meta/androidcontrol_test_gt.jsonl`. Repository GT matches its manifest: 18,415 unique keys. |
| Row versus manifest hash | **Fixed** | Wrong row hash and absent/blank manifest `config_hash` fail scoring. |
| Receipt validity / recipe binding | **Fixed for requested scope** | Model/out and each max_steps/epochs/max_agent_rows/lr/lora_r/bs/GA mismatch retrain. Empty/torn/incomplete receipts and missing/wrong-size merged weights retrain; matching receipts reuse. |
| Cached metrics / `metrics_ok` | **Fixed** | All three AC evaluations rescore current predictions. Misleading cached metrics cannot bypass checks; corrupt/missing artifacts trigger generation attempts. Invalid GT fails the pipeline. |
| Retraining / stale policy regressions | **Fixed, fails closed** | New weights reject old Hub predictions and perform fresh FT inference. Old local thinking/pixel policy exits 1 without new certification; cleanup is needed before retry. |
| Mandatory upload failure | **Fixed** | All-upload, merged-only, and evaluation-only failures exit 1. Warning-only partial uploads cannot override mandatory wrapper failures. |
| 6. `meta`, GT/manifest, `jobs.json` | **Fixed** | Same-session and fresh launchers create/upload required artifacts and abort on failures, including `Uploaded` text with exit 17. |
| Heartbeat / VM loss | **Fixed** | Immediate client exit, missing heartbeat, and heartbeat-then-exit fail confirmation. Live heartbeat passes; `404` plus exit 1 triggers replacement/bootstrap. |
| 7. Prerequisite / legacy job | **Fixed** | With prior local merged weights absent, 2B receives `experimentalmachines/LFM3-VL-2B-AndroidControl`. Legacy job is absent. |
| 8. AW answer execution / IR scoring | **Fixed** | Actual upstream cache, episode, IR and suite functions: executed correct answer scores 1; wrong/empty/malformed answers score 0. Correct cache without `done` scores 0. Execution failure stays open; successful retry scores 1. |
| General-summary crash recovery | **Fixed** | Interrupted `.tmp`, empty and torn summaries recover in both pipelines. |
| Failed predecessor policy | **Acceptable** | Matching predecessor exit 7 logs `WARNING` and launches the independent successor. |
| Pass-9 stale terminal status | **Fixed** | Genuine old exit-0/exit-7 statuses are ignored; launch follows the newly observed run's termination. |
| Restart with stale **running** status | **Not fixed — blocking** | Both watchers remain bound to the interrupted run and fail to launch after the replacement predecessor completes. |

**Blocking, realistic crash/restart:** execute runner A, kill it after its genuine `running` status, then start runner B while that untouched file remains during startup. Both watchers bind A. They subsequently observe B running and exiting 0, but [line 19](/Users/alpha/lfm3-android/scripts/chain_next_job.sh:19) never replaces `SEEN_RID`. The 12-second bounded fixtures downloaded B's terminal status **16 times (2B), 20 times (0.8B)** without launching. Both IDs came from the actual runner; no status was forged. Publish/bind the current run before startup staggering and handle verified restarts without retaining the old binding. [Reproduction evidence](/private/tmp/codex-pass10-on8gfqqf/status_lifecycle_results.json).

**Nonblocking deliberate-tampering residuals:** same-size weight changes beyond the hashed 4 MiB prefix preserve the fingerprint; deleting an adapter after receipt creation still passes the receipt gate. Separately, trainer exit 17 after producing a valid completion receipt is accepted; this did not certify incomplete training.

[Evidence index](/private/tmp/codex-pass10-on8gfqqf/evidence_index.json): 28 generation/scoring checks, 94 pipeline cases, 44 chain/launcher cases, six real-runner lifecycle cases, plus recovery/partial-upload/AW checks. Repeat in fresh temporary fixtures with `python3 -B /private/tmp/codex-pass10-on8gfqqf/rerun.py`. AW commit: `55ddaf5edc6f6c25673aed343907d5b9dca66f84`.

Only this report was written in the repository by this audit. Tested sources/configuration, upstream AW files, and HEAD remained unchanged; five existing live logs changed during the audit. [Hash verification](/private/tmp/codex-pass10-on8gfqqf/source_verification.json).
