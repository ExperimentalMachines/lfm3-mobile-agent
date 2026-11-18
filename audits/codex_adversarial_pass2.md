# Adversarial training/evaluation audit — pass 2

**Decision: NO-GO for the two Qwen jobs as configured.** The Qwen template patch and LoRA target regex pass the local checks. The blockers are experiment identity, failure propagation, recoverability, and the validity of the before/after measurements. A job can skip training because an incomplete model directory exists, continue after failed evaluations, accept predictions from a different experiment, and still finish with exit code zero.

Audit date: 2026-11-16. Initial checkout: `f5aaed289ec3383e64c203b118dccefc6b6b0e2b`. This audit wrote only under `results/codex/`; it did not edit training, evaluation, job, or launcher files. During the audit, another process changed `data/build_general_replay.py` to resize/JPEG-encode replay images and added `scripts/chain_next_job.sh`. Those changes were left intact and inspected. Replay line references below use the **55-line version** preserved in [concurrent_build_general_replay.py.txt](pass2/concurrent_build_general_replay.py.txt); the original was 51 lines. The new chain script is preserved in [concurrent_chain_next_job.sh.txt](pass2/concurrent_chain_next_job.sh.txt). Other requested source files matched the initial snapshot when checked before report preparation; see the final verification artifact for the final comparison.

**Evidence:** [CPU reproducer](pass2/reproduce.py), [successful reproduction results](pass2/repro_sct3_8ps/results.json), [initial source hashes](pass2/input_manifest.json), [dependency/source provenance](pass2/source_index.json), [current local artifact checks](pass2/current_artifact_checks.json). Run the reproducer with:

```sh
python3 -B results/codex/pass2/reproduce.py
```

It creates a new `results/codex/pass2/repro_*` directory. Eight groups of checks passed. “Passed” means the expected counterexamples or positive controls reproduced, not that the pipeline is safe. Tests use Python/Jinja, tiny fake dataset objects, actual parser/scorer/summarizer code, AST-extracted production functions, and isolated copies of shell scripts with fake Python/upload commands. They do not start a Colab session, run a GPU model, upload anything, or download weights/datasets. Versioned upstream source was read to establish dependency behavior. Actual Arrow casting, tokenizer-level masks on model tokenizers, CUDA memory, active VM code versions, and Hub checkpoint contents were **not** validated. Character-mask and source evidence must not be described as a successful training batch.

| Rank | Severity | Finding | Immediate relevance |
|---|---|---|---|
| C1 | Critical | File existence substitutes for successful, matching stage completion | Both Qwen jobs can reuse incomplete/stale weights and results |
| C2 | Critical | Errors disappear through outer scripts and the blocking-cell runner | Failed runs can be reported and chained as completed |
| C3 | Critical | Prediction resume and scoring do not establish experiment or test-set identity | Mixed/stale results can pass integrity checks |
| M1 | Major | General-eval image resolution changes between Qwen base and FT | Apparent forgetting is confounded by preprocessing |
| M2 | Major | Agent base/FT results use different thinking policies | Reported gains do not isolate fine-tuning |
| M3 | Major | General answer extraction can score prose or unfinished reasoning | Retention accuracy can move without knowledge changing |
| M4 | Major | 500-item MMLU check cannot certify preservation without paired uncertainty | Small forgetting can be missed; no acceptance threshold exists |
| M5 | Major | Failed/incompatible training resume is not rejected | Restart, schedule, data, and provenance can silently change |
| M6 | Major | Evaluation progress is not durable during a stage | VM loss can erase substantial evaluation work |
| M7 | Major | Replay proportion/provenance is not enforced or versioned | “20% replay” is conditional and changes can reuse old data |
| M8 | Major | Reasoning-only actions can count as final actions | Thinking-enabled Qwen scores can overstate final-answer validity |
| M9 | Major | “Strict” parser accepts noncanonical coordinates and duplicate keys; lenient NaN still escapes AW handling | Invalid outputs can score or abort a task |
| M10 | Major | New teardown handling hides lifecycle failures from the reported reward/exception count | Pass-1 fix still permits misleading AW outcomes |
| M11 | Major | AW summaries have no scheduled denominator and still truncate/normalize incorrectly | Missing attempts and invalid numeric fields distort results |
| M12 | Major | Immutable data/model/runtime identities are missing | Equal seeds and model names do not reproduce an experiment |
| M13 | Major | Offline high-mode history remains privileged | Offline numbers cannot establish closed-loop agent gains |
| m1 | Minor | Large raw eval files are silently omitted from upload; uploads mix run namespaces | Future raw evidence can be missing despite metrics being present |
| m2 | Minor | Retry telemetry fixes create misleading statistics for older traces | Historical runs can appear to have zero valid first attempts |
| m3 | Minor | Coordinate/schema/metric edge cases remain | Narrow discrepancies survive the new parser path |
| m4 | Minor | Several documentation claims still exceed the evidence | Reporting needs bounded language and exact denominators |

**C1 — Critical: stage skipping can certify incomplete or stale artifacts.**

Evidence: `scripts/vm_model_pipeline.sh:32–36,42,51–59,70–83`; `scripts/vm_450m_pipeline.sh:17–24`. Training is skipped whenever `$OUT/merged/config.json` exists. No weight-file completeness, successful export receipt, adapter/processor presence, final step, or configuration match is required. A model configuration is not a transaction commit for `save_pretrained`; a VM interruption can leave it without all weights or the processor saved at `train/sft_vlm.py:209–210`. The replay-directory and summary/metrics existence checks have the same flaw. A partially written summary also satisfies `-f`.

The isolated shell reproduction seeds only `merged/config.json` with `{"stale_and_no_weights":true}`. The generic pipeline skips `sft_vlm.py`, enters “push merged + adapter,” attempts evaluations, and ends `PIPELINE DONE` with **exit 0**. The fake uploader deliberately accepts its input; this proves the shell gate, not a real successful Hub upload. Changed `MODEL`, `MAX_STEPS`, LoRA settings, template, replay preprocessing, or dataset contents are never compared with the cached stages. If real evaluation then fails loading that directory, C2 hides the failure. If old weights are valid, the pipeline can publish and score the wrong experiment instead.

Impact: both Qwen jobs use this exact wrapper. Qwen 0.8B also reuses the shared `/content/data/replay` directory. The replay builder changed during this audit, but the wrapper would keep any already existing replay directory without checking which builder produced it. On a **new** VM the converse problem occurs: already uploaded evaluation artifacts/final exports are not restored, so work is repeated.

Fix: give each stage an immutable input fingerprint and an atomic completion receipt. Export to a temporary directory, verify all weight shards/index, adapter, tokenizer/processor/template and final trainer step, then atomically publish the directory and receipt. Reuse only a verified matching receipt. Restore matching receipts and artifacts from durable storage before scheduling work; an arbitrary `config.json`, directory, or metrics filename must not authorize reuse.

**C2 — Critical: checked failures become successful pipeline exits.**

Evidence: `vm_model_pipeline.sh:8,35–38,61–86`, `vm_450m_pipeline.sh:6,24–53`, `vm_train_eval_push.sh:5,8–31`, and `vm_blocking_jobs.py:29–38`. These three outer shells enable `-u` and `pipefail`, but not `-e`. `generate && score` only prevents scoring after failed generation; it does not stop the outer script after either failure. The final `log`/`echo` usually returns zero. `vm_train.sh:3` and `vm_eval.sh:4` do fail locally, but their callers can discard that status.

Reproduction, from actual shell control flow with local stubs:

```text
vm_model_pipeline.sh: eval_general exits 17, score exits 2 -> PIPELINE DONE, exit 0
vm_450m_pipeline.sh: replay/general failures, score exits 2 -> PIPELINE DONE, exit 0
vm_train_eval_push.sh: TRAIN DONE rc=17; FT EVAL DONE rc=2 -> PIPELINE DONE, exit 0
vm_blocking_jobs.py: child status = "exit 7" -> ALL JOBS FINISHED, runner exit 0
```

The bootstrap chain has two additional gaps: `colab_bootstrap.py:20–21` prints failed pip status without raising, and `launch_gpu_jobs.sh:9` suppresses the bootstrap pipeline's failure with `|| true`. Imports can then resolve old preinstalled versions. The blocking runner writes local status but never returns a nonzero aggregate code. The new `chain_next_job.sh:13–16` accepts **any** `"exit` status as completion, and `:24–32` uploads/launches without enforced success or a job-identity check. A stale status file or failed upload can advance the chain using old code. `launch_gpu_jobs.sh:16–18` reports a background client PID, not verified kernel/job startup.

Impact: both Qwen runs can consume GPU time after a required base measurement failed, and the chain can proceed from a failed preceding model. A green client exit is not evidence of a trained, evaluated, durably saved model.

Fix: propagate nonzero status at every layer, explicitly fail required stages, and keep any best-effort rescue upload in an error trap that preserves the original exit status. Have the runner exit nonzero if any child fails. Make bootstrap assert exact installed versions. Require the expected job UUID, all required children successful, and artifact receipts before chaining. Atomically write status and verify the new blocking job actually started. Merely adding `set -e` inside a function or `&&` context is insufficient without testing its caller behavior.

**C3 — Critical: the new manifest does not bind predictions to an experiment or the frozen test rows.**

Evidence: `eval/androidcontrol/generate.py:53–66,78–79,101–104`; `eval/androidcontrol/score.py:115–125`. Generation writes data ID, thinking mode, pixel cap and decoding limit, but compares only `model` and `n_rows`. It overwrites the old manifest before reusing rows. Model identity is a string, so new weights at the same local path pass; exactly the same weights referenced by a different local path or Hub ID fail. Hub IDs themselves are mutable because no revision is resolved. Existing per-row model labels are not checked during generation.

Executed reproduction: an existing row under `data=old@test`, thinking 0, 65,536 pixels and 32 output tokens was reused after changing to `new@test`, thinking 1, 774,400 pixels and 256 tokens. The old manifest was replaced with the new settings, falsely describing the mixed file. Switching only the model string to an equivalent Hub alias instead raised “manifest mismatch.”

Scorer counterexamples all exited **0**, reported `complete: true`, and scored the one supplied step/episode at **100%**:

| Input | Why it should not certify a complete named test |
|---|---|
| One row, no manifest, no `model` | Expected rows are unknown, but `expected is None` means complete |
| One unexpected episode ID with a one-row count manifest | Counts do not establish membership |
| All rows say `old-model`, manifest says `new-model` | Scorer checks only that there is at most one row-model string |
| `--limit 1` manifest and a correct episode prefix | Completeness is relative to the truncated dataset, yet episode SR looks complete |

Ground truth, bboxes, terminal flags and subsplit labels are trusted from the prediction file. There is no independently frozen key/GT manifest. Replacing one expected row with another unique row of the same count passes, even if the former was difficult or had a different label. `--expected` checks a count only. `--allow_incomplete` also permits duplicate/mixed-model inputs, and its emitted `complete` field still depends only on count.

The pass-1 fixes **do** correctly reject duplicate keys, multiple distinct model strings, and missing outputs when an expected count is available; all three positive controls returned **2**. C2 prevents those exit codes from reliably stopping the pipeline.

Current local evidence is stronger than during pass 1: `results/androidcontrol/lfm3vl2b_base_nothink.jsonl` now has 18,415 unique rows, but **none has a model field and its generation manifest is absent**. Recomputing with `--expected 18415` reports `models:["?"]`, `complete:true`. This demonstrates the provenance gap on a real artifact; it does **not** demonstrate that its rows are wrong or that the observed row count is incomplete. Its frozen SHA-256 is in [current_artifact_checks.json](pass2/current_artifact_checks.json).

Fix: hash resolved model weights/revision, tokenizer/template, prompt code, dataset revision and selected key/GT manifest, preprocessing and decoding settings into one run identity. Validate every existing row before resuming; never replace its identity metadata with a new configuration. Score against the independently frozen expected rows, verify GT and model identity, and distinguish `complete_subset` from full-test completeness. No-manifest legacy files need an explicitly unverified status, not automatic certification. Retain rejected/incomplete status in machine-readable artifacts and prevent publication as final metrics.

**M1 — Major: Qwen general-eval resolution changes before versus after SFT.**

Evidence: `train/sft_vlm.py:102–108,207,210` constructs and saves a processor with `size.longest_edge=774400`. `eval/general/eval_general.py:32` loads whatever processor is stored with each model and supplies no matched resize override. Both Qwen job files request 774,400 training pixels (`qwen35_2b_l4.json:17`, `qwen35_08b_l4.json:19`). The native [2B processor config](https://huggingface.co/Qwen/Qwen3.5-2B/blob/main/preprocessor_config.json) and [0.8B processor config](https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/main/preprocessor_config.json) permit **16,777,216** pixels. The pinned processor maps the misleadingly named `shortest_edge`/`longest_edge` fields to **pixel areas**, so the training setting is valid; the general comparison is the problem. See `pass2/qwen2_vl_image_reference.py:159–169`.

The local resize reproduction uses the actual pinned Qwen function, without loading a model:

| Synthetic input, height × width | Native Qwen base general eval | Saved FT general eval |
|---|---|---|
| 1024 × 2048 | 1024 × 2048, **2,048 image tokens** | 608 × 1216, **722 image tokens** |
| 2400 × 1080 | 2400 × 1088, **2,550 image tokens** | 1280 × 576, **720 image tokens** |
| 512 × 512 | 256 image tokens | 256 image tokens |

These are geometry demonstrations, not measured MMStar score changes. Questions requiring small text/diagram detail can change difficulty. Base eval also has a much larger possible L4 memory load. This directly confounds the 0.8B preservation claim and the 2B before/after control.

Fix: pass and record an explicit, identical eval preprocessing configuration for base and FT, ideally load one frozen evaluation processor for each within-family pair. Assert pixel grids/token counts on fixed examples. If native-resolution scores are also useful, report them as separate protocols. Do not infer forgetting from runs with different image budgets.

**M2 — Major: the documented base/FT comparison changes thinking policy.**

Evidence: `vm_model_pipeline.sh:76–83` uses FT thinking 1 and base thinking 0; `docs/EVAL_PROTOCOL.md:15–18` explicitly documents this. Rendering proves these are different prompts. Qwen base is prefixed with an already closed empty think block; FT is prefixed with an open think block and must spend some of its 256 new tokens on intent and closure. LFM3 has the analogous difference. Greedy decoding alone does not make them matched comparisons.

For LFM2.5, `generate.py:86` and `eval_general.py:53` correctly omit `enable_thinking` because its native template has no such variable. Both boolean settings therefore produce the same assistant header; **`--enable_thinking 0` does not disable learned inline thought**. The 450M script's comment is partly accurate about inline FT behavior, but its manifest flag alone cannot characterize the actual policy.

Impact: the Qwen comparison can measure the usefulness of the complete proposed deployment policies, but cannot assign their difference exclusively to SFT. Different use of the output cap can also create different truncation rates. General eval uses closed-think Qwen prompts for both base/FT; that is a separate direct-answer evaluation, not a test of the agent's thinking policy.

Fix: run base and FT under matched thinking and generation budgets, recording effective template suffix and finish reason. Keep the desired base-off/FT-on deployment comparison as an explicitly named additional result. For LFM2.5, define an actual output contract/budget rather than labeling a no-op flag “no thinking.”

**M3 — Major: the general evaluator mistakes incidental letters and truncated thoughts for answers.**

Evidence: `eval/general/eval_general.py:38–41,53–63`. Executing the real `letter()` function gives:

```text
"A cat is pictured. The correct answer is C." -> A
"B is wrong. The answer is D."               -> B
"<think>Compare A and B. I need more time"    -> A
"<think>Compare A and B.</think>D"           -> D
"c"                                        -> None
```

`max_new_tokens=24` makes incomplete answers especially relevant to an FT model trained to emit inline thoughts. With no closing think tag, the function searches the unfinished reasoning. Even without thoughts, the capitalized article “A” matches. This can either create false correctness (gold A) or mark a correct final answer wrong. The saved `raw=t[:80]` discards evidence needed to reparse some answers, and no finish reason/token length is retained. A changed output style can be misreported as changed knowledge.

MMStar options are **not a demonstrated missing-options bug**: the official [MMStar dataset view](https://huggingface.co/datasets/Lin-Chen/MMStar) shows options embedded in `question`, with a single answer letter. The optional `A`–`D` field loop at `:78` is empty for that schema, but `q` already contains the choices. This was checked on the published schema/examples, not by downloading all 1,500 images. Validate the complete frozen TSV rather than assuming future schemas/answer formats match `strip()[:1]`.

Fix: retain the full decoded completion and termination metadata; require a declared complete final-answer format. Reject unfinished thought blocks and ambiguous prose rather than searching for the first incidental letter. A robust alternative is a separately specified forced-choice likelihood evaluation. Use the same contract before/after; report formatting failures separately from answer accuracy and do not silently use a judge to repair only one model's outputs.

**M4 — Major: 500 MMLU items are a coarse screen, not evidence of no forgetting.**

Evidence: `eval_general.py:84–90,97–102` samples 500 test rows with seed 0 and writes accuracy, with no CI, paired analysis or preservation criterion. At 250/500 correct, the reproduced **95% Wilson interval is 45.63%–54.37%**, roughly ±4.37 percentage points. The worst-case normal interval for a difference between two *independent* 500-item accuracy estimates is roughly **±6.20 pp**. These before/after evaluations use the same items, so the proper calculation is paired, based on discordant outcomes.

For example, 60 base-correct/FT-wrong items and 45 base-wrong/FT-correct items imply a **−3 pp** change; the paired normal 95% interval is approximately **−7.01 to +1.01 pp**. It is compatible with material forgetting and with a small gain. This is a synthetic calculation, not an estimate for any current model. More agreement can make the paired interval narrower; the number “500” alone does not determine it.

The sample is pooled across subjects. The code produces a zero-shot, micro-averaged random subset result, not a full conventional MMLU subject-macro result. Small subjects may have very few observations. A stable aggregate can conceal losses on particular skills. A single seed also gives no training-run variance estimate.

Fix: predeclare an acceptable loss, retain immutable question IDs, report paired deltas and CIs/McNemar discordances, and report subject/sample composition. Increase the sample or run full MMLU if the required non-inferiority margin is only a few points. Do not equate “not statistically significant” with “preserved.” Apply similar paired analysis to MMStar; use episode-level uncertainty for correlated AndroidControl steps and task-level uncertainty for AW.

**M5 — Major: checkpoint restore can silently restart or change the experiment.**

Evidence: `train/sft_vlm.py:55,67–76,176–196`. The restore block catches **all** exceptions and continues with `resume=None`. Executing that exact AST block against a failing fake Hub yields:

```text
hub resume failed: synthetic Hub unavailable
trainer.train(resume_from_checkpoint=None)
```

An authentication error, transient service error, incompatible destination, or damaged restore can therefore become fresh training under the old run/repo name. `run_config.json` has already been overwritten. An existing `checkpoint-*` entry prevents remote restore without checking that the local checkpoint is complete or appropriate. Model/dataset/template/optimizer compatibility is not enforced; a structurally loadable checkpoint can be combined with a different data order, row count or schedule.

The per-device-batch concern requires care: in **Transformers 5.20.2**, the saved batch size is restored only when `auto_find_batch_size` is true (`pass2/trainer_reference.py:1548–1551`). This repository does not enable that option. Do **not** apply the older claim that any saved batch size silently overrides `--bs`. The current resume arithmetic at `:1689–1692` instead skips `(global_step % updates_per_epoch) * current_gradient_accumulation_steps` batches:

| Resume at step 100 | Previously presented rows | Rows skipped with new settings |
|---|---:|---:|
| BS16/GA2 → BS8/GA4 | 3,200 | 3,200 |
| BS16/GA2 → BS8/GA2 | 3,200 | 1,600: repeats 1,600 |
| BS8/GA4 → BS16/GA4 | 3,200 | 6,400: skips 3,200 unseen |

These single-epoch calculations assume identical dataset/order/world size. The first change preserves row position, though dropout/floating-point grouping need not be bitwise identical. Changing the dataset or replay order invalidates even that conclusion. `lfm3_train_l4_resume.json:11–13` requests 1250/8/4; no saved checkpoint state was available to establish which change actually happened on its VM.

`max_steps` is the **total target**, not additional steps after resume; positive `max_steps` overrides epochs in the pinned trainer (`:2480–2513`). Qwen 2B requests about 40,000 row presentations, about 0.403 epochs if the reported 99,216-row dataset is unchanged. Qwen 0.8B requests one epoch: **1,875 optimizer steps** if exactly 48,000 agent and 12,000 replay rows survive. These are intentional different schedules, not equal update budgets. A completed-step checkpoint should be recognized explicitly: the pinned loop's next-update range and end-of-step stopping logic do not supply an application-level “already complete, export only” receipt. This matters when a VM dies after its final checkpoint but before merged export.

Fix: make fresh/resume intent explicit; fail a requested restore instead of silently starting fresh. Resolve one Hub commit for listing and download, verify checkpoint files, and compare a saved immutable manifest **before** overwriting configuration or constructing the resumed schedule. Record consumed-row/order state and reject incompatible batch/data changes or explicitly start a new experiment. Preserve the previous run config and recognize already finished training before calling `train()` again.

**M6 — Major: evaluations and some logs are vulnerable to VM loss inside long stages.**

Evidence: general evaluation accumulates results in memory through `run()` (`eval_general.py:45–65`), finishes both benchmarks (`:81,91`), and only then opens the JSONL at `:93`. If MMStar completes and MMLU crashes, **none of the completed item results is written**. If a VM disappears halfway through either stage, the work is lost. General eval has no per-item resume.

AndroidControl is better: it flushes each batch (`generate.py:104–105`). But the generic wrapper only calls `push_evals` after the whole subprocess returns (`vm_model_pipeline.sh:76–78`), so an abrupt VM loss still destroys unuploaded partial predictions. A torn final JSONL line makes the next resume crash at `generate.py:65`; there is no checked recovery of the last incomplete record. General summaries and status files are also written nonatomically. An OOM or network failure followed by C2 can leave missing stages while the pipeline looks finished.

Training is not completely unprotected: pinned Trainer checkpoint upload includes the output directory, including logs, and separately uploads `last-checkpoint` (`pass2/trainer_reference.py:4389–4452`). However, uploads are asynchronous and a save is skipped while an earlier push is unfinished (`:4393–4395`); “every 100 saves” is not a guaranteed maximum remote lag. Restore downloads only `last-checkpoint/*`, not root custom logs. A new VM can subsequently overwrite the root JSONL log with only the new session's entries, although checkpoint `trainer_state.log_history` retains its own history. Logger `elapsed_s` restarts at zero on each process. The 450M wrapper waits until all evaluations to perform its final artifact upload (`vm_450m_pipeline.sh:40–50`).

Impact: both next jobs repeat expensive measurements or lose their raw evidence, undermining the stated requirement to survive disappearing Colab VMs. Qwen 2B's `PRE_GENERAL_MODELS` also refers to the prior model's **local** merged path (`qwen35_2b_l4.json:25`); a replacement VM cannot satisfy that path, and C2 continues after its failure.

Fix: append per-item results immediately, flush bounded batches, upload immutable chunks during the stage, and resume only verified chunks under the same run identity. Atomically finalize complete manifests/summaries. Recover a torn tail only after validating the intact prefix, retaining the damaged bytes as evidence. Verify remote commits and retain per-session logs plus cumulative state. Restore prior required models by immutable durable reference, not a former VM's path.

**M7 — Major: replay is schema-compatible in source, but its amount and identity are not guaranteed.**

Evidence: the agent and replay builders declare the same `images`/`messages` feature structure (`data/build_androidcontrol.py:119–124`, current `build_general_replay.py:26–28`). `images` is a sequence of Image features; `messages` is a list of structs, **not** `Sequence(dict)` with its transpose semantics. Nullable string `reasoning_content=None` is intentional. Both original PIL image inputs and the current `{bytes,path}` inputs are supported Image representations. There is no demonstrated schema crash. `sft_vlm.py:73–76` removes metadata before casting, and no-system replay messages rendered successfully for all three templates. This is source/character evidence; actual Arrow conversion was not executed locally because `datasets`/`pyarrow` are not installed.

The mixing guarantee is weaker: `build_general_replay.py:33–44` samples `k` rows first and then discards unsuitable rows **without replacement sampling**. Small subsets and invalid/multiple-image/empty-text samples shrink the result. The production-builder reproduction requests 20 rows, rejects the five chart samples, and keeps 15; mixing those with 80 agent rows yields **15.79%**, not 20%. The real 20% expression is `12000 / (48000 + 12000)` only if both counts are reached. `sft_vlm.py:77` prints the actual row fraction, but does not enforce it. No claim is made that the current real replay already has this synthetic shortfall.

The builder keeps only the first conversation turn, drops source IDs, uses mutable data-file globs, and restricts localized narratives to the first two shards. It does not save selected source indices, exclusions, image hashes or a replay manifest. The training script then removes all metadata. Rebuilding after a dataset/shard change or reusing a directory from the old builder is not reliably comparable. Row percentage is also not loss-token percentage: long caption targets can contribute disproportionately to assistant tokens. No replay-vs-eval overlap check exists. Shared source families such as AI2D motivate checking exact item/image identity; they do **not** establish that an MMStar item leaked. No actual replay/test overlap was proved here.

The concurrent JPEG/thumbnail change reduces the old builder's risk of holding thousands of full-resolution decoded images in RAM. It does not add count enforcement or provenance, and changes replay image bytes/resolution. That change needs a new replay fingerprint rather than silent reuse of an old cache.

Fix: filter/validate first and sample to an exact budget, or record and gate on the accepted count. Persist source revision/subset/shard/index, image/text hashes, transformations and exclusion counts. Include this manifest in the training identity and deduplicate against the frozen general evaluation where possible. Log both row and supervised-token mixture proportions; label the two-shard source restriction. Add a small real Arrow encode/save/load/cast and collator preflight before GPU allocation.

**M8 — Major: reasoning-only JSON can be mistaken for a final action.**

Evidence: `generate.py:87–96` feeds the model an **open** think block for enabled Qwen/LFM3 inference, but stores only newly generated tokens. `agent_format.py:109–118` strips a thought only if a closing `</think>` is present; otherwise it attempts to parse the entire suffix. Thus an output suffix consisting only of `{"action_type":"wait"}` can pass **strict** parsing while the assistant is still inside the prefilling prompt's open thought. The reproduction records that exact prefix/suffix combination. The parser lacks the prompt state needed to reject it.

Online, `lfm_agent.py:93` explicitly falls back to parsing `reasoning + content`. The reproduction parses a contemplated `wait` object followed by “No final answer yet” into an executable action. This can execute a speculative action or promote truncated reasoning to a correct offline output. It particularly affects thinking-enabled FT Qwen relative to the closed-think base prompt.

Fix: preserve assistant-prefill state and finish reason; require a completed thought boundary when inference began inside thought, then parse only the final answer. In AW, never use reasoning text as an action fallback. If an intentional repair policy is retained, name and score it separately from final-answer validity and apply it consistently.

**M9 — Major: strict schema validation is incomplete, and NaN still escapes online error recording.**

Evidence: `agent_format.py:113,141–149,203–220`; `lfm_agent.py:119–138`. Reproduced results:

| Output | Current result |
|---|---|
| Click at `[true,5.5]` | Accepted by **strict** parser although coordinates are documented integers |
| Duplicate `action_type` keys | `json.loads` keeps the last key; strict parser accepts it |
| Click at `[NaN,20]` | Accepted by lenient parser; `action_to_str` raises `ValueError` converting NaN to int |
| Click at `[Infinity,20]` | Lenient parser clamps to `[1000,20]` |
| Status with omitted `goal_status` | Lenient parser still supplies `complete` |
| Status with `goal_status:"banana"` | Now rejected: this part of pass 1 was fixed |

NaN coordinate comparisons correctly reject it in the new **strict** path, but AW still uses the lenient path. History serialization occurs before the action-execution `try`, so the accepted NaN can discard the step/attempt record via a higher-level task exception. `strict` and lenient action success may also disagree after float acceptance followed by integer truncation. An omitted terminal status can stop the agent, although the actual AW reward remains environment-judged; it does not automatically grant benchmark success.

The new strict-versus-lenient reporting exposes a material difference on the current local base file: high-mode step SR is **31.54% lenient versus 14.46% under current strict parsing**; high parse rate is **91.37% versus 40.34%**. These are recalculations of the same observed file, not new model evaluations, and its identity limitation is described in C3. Its strict rate is still not fully canonical because of the defects above.

Fix: require `type(v) is int` and bounds for grid coordinates, reject duplicate JSON keys, reject nonfinite values before any repair, and never default malformed terminal decisions into completion. Keep parsing, canonicalization and coordinate conversion inside a recorded failure boundary. Report strict and repaired outcomes with explicit definitions, including terminal rows.

**M10 — Major: the new AW teardown fix hides failures, and cleanup still accepts an unchecked command result.**

Evidence: `eval/androidworld/android_world_local_fixes.patch:62–76,94–105`; live `android_world/android_world/suite_utils.py:288–297`; `summarize_aw.py:41–44,61,75–77`. The teardown patch now catches the exception, but writes it only to `aux_data.teardown_exception`. It leaves `is_successful` and `exception_info` unchanged. The actual `_run_task` function, run with a synthetic successful task whose teardown raises, returned:

```text
is_successful = 1.0
exception_info = None
aux_data.teardown_exception = "...RuntimeError: cannot clean"
```

The production summarizer then reports **success_rate=1.0, n_exceptions_counted_as_fail=0**. This contradicts `docs/EVAL_PROTOCOL.md:55–61`. Even a record explicitly containing `exception_info="boom"` and success 1.0 still reports success 1.0 while counting one “exception counted as fail.” The exception flag never forces reward to zero.

Cleanup is improved: visible nonempty output after both deletion attempts now raises. However, `file_utils.py:119–134` reads `ls` stdout without checking response status. A fake error-status response with empty stdout passes the real function's emptiness test. `ls -1` and `*` also exclude dotfiles. Finally, the teardown patch proceeds to another task without an enforced environment reset; its comment assumes the next initializer verifies everything the failed cleanup could leave behind. The code does not establish that global invariant.

Impact: Qwen's later AW comparison can include dirty-state carryover or lifecycle failures invisible in its headline failure count. The pass-1 vocabulary corruption **is** removed: the live `_NOUNS` list equals the nested repository's stock HEAD list, 51 items in each, as independently checked.

Fix: define lifecycle-failure policy, set a consistent structured failure record, include teardown in summary denominators, and quarantine/reset the environment after failed cleanup. Check command status before interpreting stdout, include all relevant files, and test both visible and hidden leftovers. An episode may preserve its raw task reward separately, but it must not be labeled exception-free under the stated policy.

**M11 — Major: AW summary completeness and numeric handling remain unsafe.**

Evidence: `summarize_aw.py:37–47,60–89`. The pass-1 `episode_data=NaN` crash is fixed by requiring a dict. The synthetic upstream-style failed record now exits successfully, but emits **`mean_steps: NaN`** and nonstandard JSON because `episode_length` remains NaN and serialization allows it. Infinity/out-of-range rewards and malformed records are not rejected. A pickle holding `[success, failure]` is truncated to its first element at `:40` and reports **100%**, instead of preserving both attempts under an explicit policy.

The denominator is whatever `*.pkl.gz` files happen to be readable in that directory. There is no expected task/instance/attempt manifest, completion flag, model identity, seed/config verification or duplicate/retry policy. A surviving successful prefix can appear as the run's success rate while unsaved failures are absent. Conversely, declaring every missing scheduled task a completed failure would also be wrong unless that failure policy is explicit. Unreadable/in-progress pickle files can abort the whole summary. Mean fractional reward is labeled success rate without a separate full-completion count.

Fix: validate finite numeric ranges and use `allow_nan=False`; represent unavailable values as null. Iterate all episodes and validate unique task-instance-attempt identities. Join against a frozen schedule and show completed/missing/failed coverage. Keep raw reward mean, explicit binary completion, lifecycle failure and interruption separate. Publish a full-suite result only after completion criteria hold.

**M12 — Major: mutable dependencies and missing provenance prevent reproduction or a leakage certificate.**

Evidence: `sft_vlm.py:64,103,110–113`; `generate.py:37,48–51`; `eval_general.py:32–34,69,84`; `build_general_replay.py:34–35`. Every model/dataset load uses a mutable ID or directory without an immutable revision/hash. Remote model code is trusted without recording its revision. Data loads use all files matching `data/<split>/*.parquet`; stale overlapping shards in that namespace would be concatenated. Neither training nor generation asserts processed split membership, uniqueness, raw provenance or frozen GT identity before GPU work. The source split lists are disjoint, but that alone cannot certify every later parquet upload.

Seeds, a run name, and the pinned package strings in `colab_bootstrap.py` do not capture source hashes, installed versions after a failed pip operation, selected replay indices, effective processor settings, trainable parameter names, or resumed state. `JsonlLogger` only records metrics/time/memory; `run_config.json` records arguments, not the resolved resources. The general eval summary records only model string and aggregate accuracy; per-item rows omit dataset revision/prompt/image hashes. The Qwen 2B/0.8B recipes also intentionally differ in rank, LR, replay, total row presentations and selected data; an across-size difference is not a model-size-only experiment.

Fix: produce one resolved immutable experiment manifest before GPU work, save it with checkpoints and every eval chunk, and compare it on restore/reuse. Include git/source hashes, library lock plus observed versions, model/tokenizer/processor/code revisions, dataset shard and key manifests, replay membership/transforms, templates, exact trainable names, seeds, schedule and decoding policy. Run split/duplicate/GT checks on the exact published revision. Record unknown foundation-model contamination as unknown; no audit here proves pretraining leak freedom.

**M13 — Major: privileged offline history still limits the conclusion.**

Evidence: `data/build_androidcontrol.py:194,208,230–233` and `agent_format.py:62–77`. High-mode prompts still contain previous human step instructions with ground-truth actions; current instruction is not appended early, but repeated annotations can reveal an instruction needed again. Online `lfm_agent.py:119–120` instead stores the model's own first reasoning line, truncated to 200 characters, plus its proposed action, even when execution later fails. It receives no explicit execution-failure feedback. Inline reasoning returned entirely in `content` also does not populate this intent history unless the serving layer separately extracts it.

`docs/EVAL_PROTOCOL.md:19–22` now discloses privileged teacher-forced history, which is a useful pass-1 correction. It does not change the input distribution. Calling offline accuracy an “upper bound” is an informal expectation, not a mathematical guarantee: added text can also distract a model. Episode SR is all teacher-forced steps correct on supplied screens, not a rollout success estimate.

Impact: Qwen can improve under an oracle-history offline protocol without improving recovery or self-generated histories. This is not a demonstrated same-row label append bug or cross-split leak.

Fix: make prior-action-only history the main matched offline/online protocol, or clearly name this an oracle-history benchmark and add an action-only ablation. Keep short-intent prediction as the training target if desired. Freeze history policy for all models; record execution outcomes and use a consistent feedback policy for online comparisons.

**m1 — Minor: `push_evals` silently drops large raw files and copies unrelated runs.**

Evidence: `vm_model_pipeline.sh:22–24`. The actual upload loop, exercised with fake file sizes and no large allocation, uploaded a 100-byte metrics file and another model's 499,999,999-byte file, but silently omitted the current run's **500,000,000-byte** JSONL. It filters with `<`, not `<=`, and issues no exclusion receipt. All `/content/eval/*` files are copied into each final repo, including unrelated/stale runs. The current local 6.37 MB base JSONL is below this threshold; no current size-related loss was established.

Fix: upload scoped, hashed chunks with an explicit inventory and remote verification. Treat inability to preserve a required raw artifact as a failed completion condition. Separate each run's namespace.

**m2 — Minor: retry telemetry is only partly repaired, and legacy traces get false zeroes.**

Evidence: `lfm_agent.py:94–111`; `summarize_aw.py:48–57,81–86`. New traces correctly retain returned attempts and sum their latency; the synthetic two-call step reports two calls and 3 seconds. But top-level `usage` still contains only the final call, and the summarizer reads that value, so total retry token cost is not reported. Timings are kept only for the final call; HTTP exceptions are not recorded in the attempts list. Identical greedy retries use the identical prompt, so they need not fix a deterministic format error.

A legacy trace with a valid parsed action but no new `first_attempt_*`/`attempts` fields reports **0% first-attempt validity and zero calls**, rather than “not recorded.” New numerators use only present fields but divide by all steps. Mixed old/new files therefore bias those rates.

Fix: version trace schemas, use observed-field denominators/null for older records, store every call outcome including HTTP failures and finish reasons, and aggregate usage over attempts. Keep first-attempt and eventual validity separate.

**m3 — Minor: narrower schema/metric edge cases.**

`px_to_norm` divides by width/height while `norm_to_px` multiplies by width−1/height−1 (`agent_format.py:224–231`); the endpoint discrepancy from pass 1 persists. `score_rows` can accept an already decoded bbox, but the CLI bbox pass unconditionally applies `json.loads` to a truthy bbox (`score.py:139`); a list-valued bbox raises even though the main scoring path supports it. The configured builder emits strings, so this is not an immediate Qwen launch failure. `click_bbox_hit_strict` uses the lenient action parser (`:141`): “strict” refers to geometry, not strict JSON validity. Terminal output is still only leniently scored (`:148–149`). Empty denominators become zero in several metrics, hiding “not evaluated.”

Fix: define a single endpoint convention for new data without silently changing frozen labels; normalize schema once on input; distinguish `bbox_only_with_lenient_parser` from strict syntax; score terminal validity under both policies; emit null plus counts for empty populations.

**m4 — Minor: remaining documentation overclaims.**

`docs/DATASETS_AND_SPLITS.md:57–59` still turns a scaling observation about distinct episodes into a claim about diminishing returns after one optimization epoch. The qualification at `:67` does not establish that optimum. `EVAL_PROTOCOL.md:11` still says every step appears in both modes; builder `:206–207` requires a nonempty hint, and the observed base file has 8,444 nonterminal high rows but 8,428 low rows. The dataset table's “8,435 high-level steps” bbox wording (`DATASETS_AND_SPLITS.md:18`) still conflates curated records with bbox-bearing click targets. The explicit input-text semantic difference and ±4 pp **standard error** wording have improved, but no phone latency or complete-suite result follows from a desktop proxy or a partial run.

Fix: retain exact denominators/protocol qualifiers next to numbers; make epoch sufficiency a validation question. Report the action-semantics difference—AW input text presses Enter—as a transfer constraint. Fix the stale report path at `EVAL_PROTOCOL.md:73` to the actual audit artifacts.

**Positive checks: loss masks, Qwen targets, pixels, kwargs, and schedule.**

The template check used real `agent_format.build_messages`, the repository's versioned TRL multimodal helper, and the production `_inline` transformation. Native templates were reconstructed from the publishers' code views; web rendering removes indentation. The LFM3 render source matches the previously extracted served template after indentation normalization. The Qwen native source matches the inverse of the checked-in patch after the same normalization. Applying the real patcher to that reconstructed indented native file reproduces the checked-in patch byte-for-byte. No source template was modified.

For goal “Open Settings,” intent “Tap Settings.” and a center click, these are the complete **generation/loss spans** observed with Jinja. Role headers, system/user text and image placeholders are outside the spans. EOS is correctly included; the Liquid templates also include their trailing newline.

```text
LFM3 native:
<think>Tap Settings.</think>{"action_type":"click","point_2d":[500,500]}<|im_end|>\n

LFM2.5 native + --inline_think:
<think>Tap Settings.</think>{"action_type":"click","point_2d":[500,500]}<|im_end|>\n

Qwen3.5 patched:
<think>\nTap Settings.\n</think>\n\n{"action_type":"click","point_2d":[500,500]}<|im_end|>
```

| Template | Inference default | Explicit thinking on | Explicit thinking off | Prefix of agent training render? |
|---|---|---|---|---|
| LFM3 | Opens `<think>` | Opens `<think>` | Appends `<think></think>` | Default/on yes; off no for nonempty intent |
| LFM2.5 inline | Assistant header only | Same header; flag unused | Same header; flag unused | Yes in all three cases |
| Qwen3.5 patched | Empty closed think block | Opens `<think>\n` | Empty closed think block | On yes; default/off no for nonempty intent |

Qwen's training assistant branch always renders the supplied reasoning; it does **not** need an `enable_thinking=True` training kwarg for this full-conversation dataset. The absence of that kwarg in `SFTTrainer` is therefore **not** a masking bug. Inference does need explicit true to continue the trained nonempty thought prefix; `generate.py:86` supplies it for the configured FT Qwen run. Replay without a system prompt renders successfully: Liquid/Qwen3.5 include an empty thought where their template requires one; LFM2.5 renders the answer directly. The original LFM2.5 template ignores `reasoning_content`, so the existing `--inline_think` transformation is necessary and correct for nonempty intents. Empty intents produce no inline think block on that family, a small target-format difference.

Pinned [TRL 1.16.0 vision collation](https://github.com/huggingface/trl/blob/v1.16.0/trl/trainer/sft_trainer.py#L370) requests assistant masks and masks padding/nonassistant labels (`pass2/sft_trainer_reference.py:370–415`). Pinned [Transformers processor code](https://github.com/huggingface/transformers/blob/v5.20.2/src/transformers/processing_utils.py#L2259) adjusts span offsets after expanding image placeholders (`pass2/processing_reference.py:2259–2284`). These support the intended path; the audit did not dump actual model-tokenizer masks. A saved tiny collated batch must still verify positive supervised tokens, excluded image/prompt/pad tokens, and a supervised end token before the expensive run.

For both Qwen configs, the [pinned modeling source](https://github.com/huggingface/transformers/blob/v5.20.2/src/transformers/models/qwen3_5/modeling_qwen3_5.py) and publisher configurations identify 24 language layers: 18 linear-attention and six full-attention. The regex from each **actual job JSON** matches all **186 intended LM linear modules** in the constructed name set:

| Family | Matched leaves | Count |
|---|---|---:|
| Linear attention | `in_proj_qkv`, `in_proj_z`, `in_proj_b`, `in_proj_a`, `out_proj` | 18 × 5 = 90 |
| Full attention | `q_proj`, `k_proj`, `v_proj`, `o_proj` | 6 × 4 = 24 |
| MLP | `gate_proj`, `up_proj`, `down_proj` | 24 × 3 = 72 |

No constructed vision-tower names match the `language_model` prefix. Convolutions, norms and standalone state parameters are excluded intentionally; this is not a promise to adapt every parameter of linear attention. The generic shell passes an empty `--modules_to_save` at `:56`, freezing the projector under the intended PEFT recipe. The Python default still differs: direct invocation defaults to saving/training `multi_modal_projector` (`sft_vlm.py:39,115–120`). Record actual trainable parameters in the preflight rather than relying only on this name-level proof. Do not drop the job-specific regex and assume the LFM default covers Qwen's MLP and `in_proj_*` leaves.

Qwen's factor is 16-pixel patch × merge 2 = **32**. The matched AC pixel cap gives the same **1280 × 576 / 720 image positions** as LFM3 for a 2400 × 1080 input, and keeps an already resized 1280 × 576 dataset image unchanged. This is geometry/token-count parity, not identical normalized tensors or compute. The LFM2.5 `--max_pixels 0` avoids imposing the Qwen-style size dictionary on its tiling processor; it does not mean “no image processing,” nor undo the screenshot resizing already performed by the data builder. Tile/token counts are not established as equal across those families.

Both evaluators correctly select **left padding** (`generate.py:49`, `eval_general.py:33`) and slice generated suffixes at the common padded input width. Training selects right padding, which the TRL vision collator also requests. No padding-side bug was found. The template-variable guard prevents the unsupported LFM2.5 thinking kwarg from falling through as a processing kwarg. The duplicate outer `padding=True` is redundant with `processor_kwargs`, but both specify the same value here; the pinned kwarg routing does not establish a current crash. Templates represented as a dict would require resolving the actual selected template before the substring test—current audited templates are strings.

Finally, `warmup_steps=0.03` is valid in [Transformers 5.20.2](https://github.com/huggingface/transformers/blob/v5.20.2/src/transformers/training_args.py#L2118): values below one are fractions. It means **38 warmup steps** for 1,250 updates, or **57** for 1,875. This was not misreported as a fractional-step bug. L4 memory/time remain unmeasured: no token-length census, largest-replay-batch check or GPU smoke run was performed. `max_length=None` avoids chopping image tokens, but also permits arbitrarily expensive long examples; do not treat the current batch sizes as locally certified to fit.

**Pass-1 disposition.**

| Pass-1 finding | Current assessment |
|---|---|
| Corrupted `_NOUNS` vocabulary | **Fixed in checked-in patch and live nested checkout**; 51 stock entries match exactly. No claim about every historical trace |
| Silent directory cleanup failure | **Partially fixed**; visible nonempty check added, but command status/hidden files/environment quarantine remain M10 |
| Teardown outside failure boundary | **Partially fixed with a new reporting hole**; exception goes to auxiliary data and is ignored by headline failure accounting |
| Summarizer crashes on `episode_data=NaN` | **Crash fixed**; other NaN fields and exception-success contradictions remain M11/M10 |
| Lenient parsing/invalid status | **Partly fixed**; bad explicit status rejected, strict metric added; integer/duplicate-key/nonfinite/final-answer defects remain |
| Missing rows/stale prediction resume | **Partly fixed**; duplicate/count/multiple-model rejection works, but identity and expected-key completeness do not; C3 |
| Retry attempts disappear | **Partly fixed** for new returned calls; total latency and attempts preserved, token totals/HTTP failures/legacy denominators remain |
| Privileged human history | **Disclosed, unchanged in data**; use a named oracle-history protocol, M13 |
| AW-app filter overclaim | Documentation now calls it a heuristic; no exact data-level contamination certificate was added |
| Processed splits and run provenance | **Unresolved** for immutable published revisions and hashes; M12 |
| Epoch sufficiency claim | Qualification added, but unsupported epoch inference remains in preceding text; m4 |
| AC/AW input-text semantics | **Disclosed, behavior unchanged**; training `input_text` and AW Enter-after-typing still differ |
| Low-mode/bbox coverage wording | **Still inaccurate** in the cited table/“every step” wording |
| Scroll evidence wording/path | **Improved**: 154/79 and sparse horizontal evidence now qualified; no global inversion inferred |
| Projector Python default vs shell recipe | **Still different**, but the inspected Qwen shell jobs explicitly freeze it |
| Pixel/thinking/runtime parity | AC Qwen/LFM3 geometry passes; general-eval budget mismatch is **newly identified**; thinking confound remains |
| Reward/list/NaN handling | **Unresolved in part**, M10–M11 |
| Launcher success propagation | **Unresolved and more consequential with chaining**, C2 |
| Endpoint normalization | **Unchanged**, m3 |
| AW uncertainty wording | Improved to standard error; it is still not a 95% interval or coverage proof |

**Required before launching the configured Qwen jobs:** make stage receipts/identities and error propagation reliable; fail closed on requested checkpoint restoration; freeze the dataset/replay/model/template/runtime manifest; use independent expected-row validation; persist evaluation progress durably; match general-eval preprocessing and specify thinking/answer parsing; predeclare a retention margin with paired uncertainty. Preserve the completed work already on the running models rather than relaunching it under an unverified identity. Separately fix AW lifecycle/summary handling before calling any downstream suite result comparable. Then run tiny real CPU processor/collator/schema checks and a separately authorized GPU smoke test before committing the full budgets. The local template/regex positives alone are insufficient to waive these blockers.

**NO-GO — do not launch Qwen3.5-2B or Qwen3.5-0.8B through the current configured pipelines.**
