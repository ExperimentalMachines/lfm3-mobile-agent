**Adversarial QA pass 8 — NO-GO for both Qwen3.5-2B and Qwen3.5-0.8B chains.**

Reproduced 2026-11-16 at `cdb8be9384dbe91a93ae8096d5beea71f19bd187`, using production Python/Bash with local dependency/CLI stubs. No GPU, real training, VM, or upload. Fixtures remapped `/content`, shortened waits, and removed cosmetic stderr filters. Synthetic weights test control flow, not model loadability.

| Check | Fixed / not fixed | Reproduced result |
|---|---|---|
| 1. Partial restore / generation identity | **Fixed for pair/row safeguards** | Both downloads use revision A; missing either member generates fresh rows. Orphan predictions, missing/wrong row hashes, and changed `min_pixels` are refused. Manifest includes `min_pixels`. Weight identity remains deficient below. |
| 2. Thinking prefill | **Fixed** | Real Jinja prompt plus stubbed token tail saves the opening `<think>`; both parsers reject unfinished thoughts. Closed-thought and no-think controls pass. |
| 3. Scroll/status types | **Fixed** | List/dict/bool/number arguments cause no `TypeError` in either parser or AW `step()`. Failed attempts and valid retries work. Lenient null status still defaults to complete. |
| 4. Matched no-think scoring | **Fixed for fresh evaluation** | Both jobs certify high-only predictions with `--modes high`. Missing rows/scorer failure exits 1 without a new `.done`; an orphan old `.done` cannot bypass evaluation. |
| 5. Frozen GT / VM default | **Fixed** | Missing GT manifest or SHA mismatch exits 2; both pipelines fail. Flattened scorer finds `work/meta/androidcontrol_test_gt.jsonl`. Repository GT matches its SHA manifest. |
| Row versus manifest `config_hash` | **Fixed** | Wrong row hash and missing/blank manifest hash each exit 2. |
| Receipt validity | **Fixed for requested binding** | Each max_steps/epochs/max_agent_rows/lr/lora_r/bs/GA or model/out mismatch retrains. Empty/torn receipts, incomplete steps, and missing/wrong-size merged weights retrain; matching receipts reuse. |
| Cached metrics / `metrics_ok` | **Partially fixed** | All three AC evaluations rescore current predictions against frozen GT. Bogus cached metrics cannot bypass scoring; invalid artifacts trigger regeneration attempts or failure. Intended weights/policy are still unchecked below. |
| Mandatory pipeline uploads | **Fixed** | All-upload, merged-only, and evaluation-only exit-17 failures make both pipelines exit 1. Generator checkpoint-upload failures remain warnings; wrapper uploads are enforced. |
| 6. Hand-off, `jobs.json`, heartbeat | **Fixed** | Same-session and fresh launchers create `meta`, upload GT/manifest/jobs, and reject upload failures, including `Uploaded` text with exit 17. Immediate exit, absent heartbeat, and heartbeat-then-exit fail confirmation; heartbeat plus live client passes. |
| Lost-session recovery | **Fixed** | `404 not found` plus exit 1 now allocates, bootstraps, uploads, and confirms launch for both chains. |
| 7. 2B prerequisite / legacy job | **Fixed** | With previous local merged weights absent, evaluation receives `experimentalmachines/LFM3-VL-2B-AndroidControl` and succeeds in the stub. Legacy `qwen35_train_l4.json` is absent. |
| 8. AW answer / execution semantics | **Fixed** | Actual upstream cache, episode, IR comparison, and suite functions: correct answer scores 1; wrong/empty/malformed answers score 0. Correct cache without `done` scores 0. Failed execution leaves `done=False`; successful retry caches and scores 1. |
| General-summary crash recovery | **Fixed** | A summary-write crash leaves only `.tmp` and exits 1. Retry regenerates successfully. Empty/torn legacy summaries also regenerate, for both jobs. |
| Evaluation reuse after retraining | **Partially fixed** | Local FT files are deleted and regenerate correctly without a Hub copy. With prior Hub predictions, both FT branches restore old outputs and certify them against new weights. |
| Evaluation settings on reuse | **Not fixed** | Earlier 345600-pixel/no-think predictions remain certified under the current 774400-pixel/thinking recipe. |
| Failed predecessor policy | **Acceptable as specified** | Predecessor exit 7 logs `WARNING` and launches the next independent model. This does not establish predecessor success or freshness. |

**Two realistic blockers remain in both jobs:**

- **Old Hub predictions survive retraining.** Run a one-step smoke recipe, allowing the real generator to publish to a versioned local Hub stub; rerun the intended recipe. Training changes weights and deletes local FT outputs, but both FT generators restore the old pairs, make **zero inference calls**, and finish with `complete:true`, pipeline exit **0**. A fresh-generation control produces different actions. The [generation identity](/Users/alpha/lfm3-android/eval/androidcontrol/generate.py:53) binds the model path, not its weights.
- **Old evaluation policy survives rescoring.** Run with 345600 pixels and FT thinking disabled, then rerun the current recipe: **three scorers, zero generators, exit 0**, with the old manifest/output unchanged. The [reuse gate](/Users/alpha/lfm3-android/scripts/vm_model_pipeline.sh:112) checks scoring success without comparing the requested policy. Neither reproduction edits predictions or manifests; these are ordinary stale-run cases, not deliberate tampering.

Other reproduced limits: deliberate adapter deletion passes the receipt gate; trainer exit 17 after a valid completion receipt is accepted; unrelated/stale predecessor terminal status also unlocks launch.

Evidence: [28 generator/scorer checks](/private/tmp/codex-pass8-e3ciuxq6/generation_score_bcubluce/results.json), [94 pipeline cases](/private/tmp/codex-pass8-e3ciuxq6/shell_vjg1z2xw/results.json), [44 chain/launcher cases](/private/tmp/codex-pass8-e3ciuxq6/chains_usdej5an/results.json), [AW semantics](/private/tmp/codex-pass8-e3ciuxq6/aw_csx5tqfy/results.json), [retraining/policy controls](/private/tmp/codex-pass8-e3ciuxq6/recovery_results.json), [summary recovery](/private/tmp/codex-pass8-e3ciuxq6/general_recovery_results.json). Reproduction scripts: `/private/tmp/codex-pass8-e3ciuxq6/verify_*.py`, run with `python3 -B`. AW commit: `55ddaf5edc6f6c25673aed343907d5b9dca66f84`.

Only this report was added to the repository. All **1,994 initially hashed tracked files**, six tested upstream AW files, and HEAD remained unchanged. [Verification](/private/tmp/codex-pass8-e3ciuxq6/source_verification.json).
