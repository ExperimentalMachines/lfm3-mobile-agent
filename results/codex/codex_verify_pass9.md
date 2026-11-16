**Adversarial QA pass 9 — NO-GO for both Qwen3.5-2B and Qwen3.5-0.8B chains.**

The two pass-8 evaluation blockers are fixed. One pass-4 concern remains: a stale predecessor status can trigger the chain during a new predecessor's startup.

Reproduced on 2026-11-16 at `16be09247f12187c0fafdbf6e2b25a6079849e84`, using production Python/Bash with local dependency/CLI stubs; no GPU, live VM, training, or real uploads. Fixtures remap `/content`, shorten waits, and remove cosmetic stderr filters. Synthetic weights verify control flow, not loadability.

| Check | Fixed / not fixed | Reproduced outcome |
|---|---|---|
| 1. Restore pair, manifest, row identity | **Fixed** | Both downloads use one revision. Missing members regenerate; orphan predictions and wrong/missing row hashes are refused. `min_pixels` is recorded and changing it is refused. An interrupted upload leaving mixed rows/manifest is rejected. |
| 2. Thinking prefill | **Fixed** | Real Jinja prompt ending in `<think>` produces saved output with that prefix. Both parsers reject unclosed thoughts; closed/no-think controls pass. |
| 3. Scroll/status types | **Fixed** | Lists, dicts, booleans and numbers cause no `TypeError` in lenient/strict parsing or AW `step()`. Invalid attempts and valid retries work. Lenient null status still defaults to complete. |
| 4. Matched no-think certification | **Fixed** | Both jobs score with `--modes high` and certify the complete subset. Missing rows/scorer failure exits 1; an orphan `.done` cannot bypass scoring. |
| 5. Frozen GT and VM default | **Fixed** | Missing GT manifest or SHA mismatch exits 2; pipelines fail. Flattened scorer finds `work/meta/androidcontrol_test_gt.jsonl`. Repository GT matches its manifest. |
| Row versus manifest `config_hash` | **Fixed** | Wrong row hash and missing/blank manifest hash each fail scoring. |
| Receipt validity/config binding | **Fixed for requested scope** | Each max_steps/epochs/max_agent_rows/lr/lora_r/bs/GA or model/out mismatch retrains. Empty/torn/incomplete receipts and missing/wrong-size merged weights retrain; matching receipts reuse. |
| Cached metrics / `metrics_ok` | **Fixed** | All three evaluations rescore current predictions against frozen GT. Cached `complete:false`, misleading success and missing/corrupt artifacts cannot bypass scoring. |
| Pass-8: Hub predictions after retraining | **Fixed** | Both real-generator reruns reject old Hub pairs, perform two FT inference calls and certify new outputs. New weights change `model_fingerprint`; matching pairs still restore without inference. |
| Pass-8: stale evaluation policy | **Fixed, fails closed** | Old 345600-pixel/no-think outputs under the current recipe trigger three generation attempts, manifest refusals and pipeline exit 1. No new certification; stale local files need cleanup before retry. |
| Mandatory upload failure | **Fixed** | All-upload, merged-only and evaluation-only failures produce pipeline exit 1. Partial-checkpoint warnings do not override mandatory wrapper failures. |
| 6. `meta`, GT/manifest, `jobs.json` | **Fixed** | Same-session and fresh launchers create/upload them and abort on failures, including `Uploaded` text with exit 17. |
| Startup heartbeat / VM loss | **Fixed** | Immediate exit, absent heartbeat and heartbeat-then-exit fail confirmation. Live heartbeat passes. `404` plus exit 1 allocates, bootstraps and launches both jobs. |
| 7. Prerequisite / legacy job | **Fixed** | With prior local merged weights absent, 2B evaluation receives `experimentalmachines/LFM3-VL-2B-AndroidControl`. Legacy `qwen35_train_l4.json` is absent. |
| 8. AW answer and execution | **Fixed** | Actual upstream cache/episode/IR/suite functions: executed correct answer scores 1; wrong/empty/malformed answers score 0. Correct cache without `done` scores 0. Execution failure leaves the episode open; successful retry scores 1. |
| General-summary crash recovery | **Fixed** | Interrupted summary write leaves `.tmp`; retry succeeds. Empty/torn legacy summaries regenerate in both jobs. |
| Failed predecessor policy | **Acceptable** | Actual predecessor exit 7 logs `WARNING` and starts the independent successor. Predecessor success is unnecessary for this policy. |
| Predecessor status freshness | **Not fixed** | Both watchers accept an earlier run's terminal status while a newly started predecessor remains alive. |

**Remaining blocker:** the actual `vm_blocking_jobs.py` first produced an untouched terminal status (tested exit 0 and 7), then started a new local predecessor. During its startup stagger, both chain scripts accepted the old file, returned **0**, and confirmed the stubbed successor while the current predecessor remained alive. No status/prediction/receipt was forged. The [status gate](/Users/alpha/lfm3-android/scripts/chain_next_job.sh:18) lacks current-run identity; the [runner](/Users/alpha/lfm3-android/scripts/vm_blocking_jobs.py:24) publishes its first status after staggering. This reproduction covers attaching during startup, before the current predecessor's first heartbeat; it does **not** establish live Colab overlap. Bind completion to the current predecessor before clearing unattended startup/restart chaining. [Exit-0 evidence](/private/tmp/codex-pass9-y3y2wbb4/stale_status_zero_results.json), [exit-7 evidence](/private/tmp/codex-pass9-y3y2wbb4/stale_status_results.json).

Nonblocking residuals: deliberately changing same-size weight bytes beyond the hashed 4 MiB prefix preserves the fingerprint; deliberately deleting an adapter after receipt creation passes the receipt gate. Trainer exit 17 **after** producing a valid completion receipt is accepted. These do not reproduce incomplete training being certified. The stale-status case above is a separate realistic lifecycle issue.

[Evidence index](/private/tmp/codex-pass9-y3y2wbb4/evidence_index.json): 28 generation/scoring checks, 94 pipeline cases, 44 chain/launcher cases, four real-runner stale-status cases, plus retraining/policy, partial-upload, summary-recovery and AW reproductions. Scripts: `/private/tmp/codex-pass9-y3y2wbb4/verify_*.py`, run with `python3 -B`. AW commit: `55ddaf5edc6f6c25673aed343907d5b9dca66f84`.

Only this report was added to the repository. All 1,999 initially hashed files, six tested upstream AW files, and HEAD remained unchanged. [Verification](/private/tmp/codex-pass9-y3y2wbb4/source_verification.json).
