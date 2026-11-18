# Independent evaluation audit — pass 1

Repository: `~/lfm3-android`. Audit date: 2026-11-16. **Verdict: not yet fit to publish trustworthy, comparable headline benchmark numbers.** The split-routing and training design have substantial support in code, but the AndroidWorld environment patches alter benchmark semantics, exception handling is broken, and scoring/completeness policies need correction or explicit qualification.

The final artifact snapshot is **18:51:04 Asia/Manila / 10:51:04 UTC**. Repository HEAD was `914d59117c6b12ca72c41f494f730d6b58268a31`; AndroidWorld HEAD was `55ddaf5edc6f6c25673aed343907d5b9dca66f84` with local modifications. [Input hashes](input_manifest_final_pass1.json) identify the files examined. Results arriving after that snapshot are outside this report. This audit did not edit existing project files; all audit outputs are under `results/codex/`. Python checks used `-B` to avoid writing bytecode into source directories. A final hash check detected a concurrent change to `scripts/gpu_session.sh` after the snapshot; that later version is outside this audit's frozen source state. Concurrent workspace changes were left intact.

Evidence levels matter here: I independently checked local metadata, source, installed AndroidWorld changes, GGUF metadata/template, and trusted episode pickles. I exercised the production parser and summarizer with synthetic counterexamples. I checked versioned upstream TRL/Transformers source and public model sources. I did **not** run GPU training, download the private processed dataset, reproduce a phone benchmark, or recompute real AndroidControl predictions: none of those prediction files exists locally. `dataset_verification.json` explicitly says its numbers were copied from lost VM output; it is an assertion to audit, not an independently reproducible verification record.

## Findings ranked by severity

“Critical” means a blocker to benchmark validity; “major” means a material measurement, comparability, or assurance problem; “minor” means a narrower correctness, reporting, or reproducibility issue. Unverified risks are distinguished from reproduced defects.

| Rank | Severity | Finding | Main location |
|---|---|---|---|
| 1 | Critical | Failed environment cleanup is silently accepted; teardown can escape checkpointing | `android_world/android_world/utils/file_utils.py:125`; `android_world/android_world/suite_utils.py:288` |
| 2 | Critical | Monkey patch accidentally changes seeded task-data vocabulary | `android_world/android_world/task_evals/utils/user_data_generation.py:921` |
| 3 | Major | AndroidWorld summarizer crashes on upstream exception records | `eval/androidworld/summarize_aw.py:44` |
| 4 | Major | Invalid outputs are repaired into successful actions, including invalid terminal status | `train/agent_format.py:108`, `:136`, `:149` |
| 5 | Major | Offline completeness and resume identity are unchecked | `eval/androidcontrol/score.py:93`; `eval/androidcontrol/generate.py:54` |
| 6 | Major | Offline high-level history contains privileged human instructions | `data/build_androidcontrol.py:208` |
| 7 | Major | App-name filter does not establish AndroidWorld contamination freedom | `data/build_androidcontrol.py:40`, `:168` |
| 8 | Major | Processed split verification and training/run provenance cannot be independently reconstructed | `results/data/dataset_verification.json:2`; `train/sft_vlm.py:52`, `:150` |
| 9 | Major | Retry attempts disappear from parsing and latency statistics | `eval/androidworld/lfm_agent.py:91`, `:103` |
| 10 | Major | “One epoch is enough” is not supported by the cited scaling argument or this log | `docs/DATASETS_AND_SPLITS.md:56`, `:66` |
| 11 | Major | Identically named input-text actions have different AC/AW behavior | `eval/androidworld/lfm_agent.py:124`; `android_world/android_world/env/actuation.py:105` |
| 12 | Minor | Low-mode and bbox coverage are overstated | `docs/EVAL_PROTOCOL.md:11`; `docs/DATASETS_AND_SPLITS.md:18` |
| 13 | Minor | Scroll evidence is noisy and incomplete; documentation points to the wrong artifact path | `results/data/scroll_convention_check.json:3`; `docs/EVAL_PROTOCOL.md:33` |
| 14 | Minor | CLI projector-training default differs from the actual language-only shell recipe | `train/sft_vlm.py:39`; `scripts/vm_train.sh:18` |
| 15 | Minor | JPEG/PNG, token budgets, thinking modes and runtime settings complicate parity claims | `data/build_androidcontrol.py:82`; `eval/androidworld/lfm_agent.py:36` |
| 16 | Minor | Reward mean, list truncation and permissive NaN serialization need explicit handling | `eval/androidworld/summarize_aw.py:39`, `:55`, `:68` |
| 17 | Minor | Job launcher can report completion after failed jobs; legacy data-push stats path is stale | `scripts/vm_blocking_jobs.py:33`; `scripts/vm_push_data.sh:13` |
| 18 | Minor | Coordinate normalization and inversion use different endpoint conventions | `train/agent_format.py:188`, `:194` |

## 1. Data and splits

### What is actually verified

The builder selects `id2split[episode_id]` once per raw episode (`data/build_androidcontrol.py:65–66,156–160`). It does not use the mirror's train/test designation. All ordinary, low-mode, and synthetic terminal rows for that episode follow that selected split (`:198–217`). **No episode-level train/val/test overlap was found in the supplied split lists.** This is the right design for avoiding the mirror's random-split leakage.

Independent local counts, saved in [split audit](split_audit_pass1.json):

| Supplied split | Unique episodes | Duplicate IDs | Intersection with other splits |
|---|---:|---:|---:|
| train | 13,603 | 0 | 0 |
| validation | 137 | 0 | 0 |
| test | 1,543 | 0 | 0 |

The four test subsplits contain IDD 721, app_unseen 631, task_unseen 803, category_unseen 700 episodes. All IDs belong to test; their union covers test. They overlap, so their counts must not be added as disjoint test populations. The curated file has 8,435 unique `(episode, step)` keys across all 1,543 test episodes. **Only 5,074 entries have a nonempty max bbox: 5,065 clicks and 9 long presses.** All those entries' supplied GT points fall inside their supplied max bboxes; this does not independently establish their alignment with the unavailable screenshot mirror.

The [official AndroidControl README](https://github.com/google-research/google-research/blob/master/android_control/README.md) confirms episode IDs, actions between consecutive screenshots, repeated step instructions, and the official GCS distribution location. The official GCS split object could not be retrieved in this audit. Consequently, I verified internal disjointness and routing, **not byte-for-byte equivalence to the original GCS split file or end-to-end leak freedom of the published parquet shards**.

### Major — processed-data assurance is weaker than “zero overlap verified” implies

`results/data/dataset_verification.json:2` is a manually reconstructed aggregate. Its reported 99,216 train / 827 val / 18,415 test rows, zero duplicates, and zero processed-row overlap cannot be recomputed from the local files. Its 30 missing train episodes include filtering/malformed-data effects, while `:77` gives only a partial AW-filter count of 15. Do not equate all 30 with confirmed AW-app exclusions. The builder also lacks fail-fast assertions for disjoint ID sets, duplicate episode rows across raw shards, and curated action/coordinate agreement (`data/build_androidcontrol.py:66,74–77,280`). None of these observations proves that leakage occurred.

**Suggested fix:** retain the frozen processed dataset revision, raw shard list/hashes, episode-to-split manifest, exact exclusion reasons, and executable verification output. Assert uniqueness of `(episode_id, step_idx, mode)`, correct official membership, expected coverage, and coordinate/action agreement on bbox joins. Compare the split-file hash with the official distribution. Repeat these checks on the exact revision used by training/evaluation, including all uploaded shard tags.

### Major — high-level prompts contain privileged instruction history

`data/build_androidcontrol.py:194,208,230–233` stores previous **human** instructions with previous GT actions. `train/agent_format.py:62–76` places those instructions into the next prompt. This is not a same-step append-order error: history is copied before appending the current action. It is nevertheless richer information than a goal plus ordinary action history. Official annotations can repeat the same instruction across several actions.

I found **1,466 / 8,435 (17.38%)** curated rows whose normalized current instruction occurs among the last eight historical instructions. Example: `android_control_images/6405/step_15.png` repeats the instruction to expose the share option. This is evidence from the curated metadata, not a recomputation from the private processed dataset. Online, `lfm_agent.py:113–114` has only the model's own first reasoning line, truncated to 200 characters; the no-think base model generally supplies no such intent. Thus offline “high” is an **oracle-history offline task**, not a faithful simulation of its online context. Episode SR also remains a teacher-forced proxy, with no recovery or state drift.

**Suggested fix:** use prior actions only for the principal high-level comparison, consistently in training and inference; retain human-intent history as a separately named oracle-context ablation. Alternatively disclose this privilege prominently and compare only against systems given identical history. Preserve short-intent prediction as an assistant training target if desired.

### Major — contamination filter is a heuristic, not a clean-benchmark certificate

The builder accepts AndroidControl as its source and has no code path explicitly adding AW rollout datasets. That is positive evidence about this SFT input. However, `AW_APP_PATTERNS` plus the goal/`open_app` check (`data/build_androidcontrol.py:40–45,168–170`) cannot establish app exclusion or absence of task contamination:

- It misses demonstrated aliases: `Tasks app`, `org.tasks`, `com.arduia.expense`, and spaced `Open Tracks`; the upstream action mapping recognizes several such variants (`android_world/android_world/env/adb_utils.py:148–162`). The audit reproduces these misses.
- An episode can navigate into an app by clicking rather than `open_app`, with no app name in its goal. Step instructions, package metadata and screen identity are not checked.
- Generic apps are intentionally retained. That is disclosed transfer learning, not automatically contamination. Conversely, excluding an app name would not prove that a foundation checkpoint had never seen AW or AndroidControl test material.

**Suggested fix:** define whether the claim is “no AW rollout data added” or “AW-app-disjoint SFT.” For the latter, use canonical package IDs and an alias registry derived from the suite, inspect the full episode's app transitions, and retain exclusion manifests. Audit foundation-model data disclosures separately; report unknown pretraining contamination as unknown. There is **no demonstrated leaked AW training episode** in the supplied evidence.

### Action conversion: mostly coherent, with bounded caveats

`convert_action` preserves the eight official action families and normalizes click/long-press coordinates using the **original** screen dimensions before resizing (`data/build_androidcontrol.py:86–98,174–193`). Aspect-preserving resizing therefore does not require scaling the normalized points again. Bboxes use the same coordinate system. Unknown actions reject the whole episode, rather than leaving a partially converted trajectory (`:182–210`).

Synthetic terminal labels use screenshot index `len(actions)` only when an extra final screenshot exists (`:211–219`), which matches the official action-between-screens layout. The terminal intent is an assistant target, not a high-mode user hint. There is no obvious terminal off-by-one error. The success assumption remains unverified, and all terminal labels are positive `complete`; there are no infeasible/negative stop examples. **Suggested improvement:** audit final-state validity and add separate evaluation of premature stopping, infeasibility and information-retrieval answers. High positive-terminal accuracy alone does not establish reliable stopping.

**Minor — low-mode coverage and bbox wording.** Low rows are emitted only for nonempty hints (`:206–207`). The aggregate artifact reports 8,428 low rows versus 8,444 high ordinary steps, not two complete copies. The claimed total 18,415 is consistent with `8,444 + 8,428 + 1,543`; two full copies would total 18,431. Likewise, 8,435 curated records do not mean 8,435 bbox-bearing clicks. **Fix:** publish exact per-mode manifests and the bbox-bearing denominator, and either retain blank-hint low rows with an explicit policy or identify this as a restricted low-level subset.

**Minor — scroll verification overclaim.** No inversion is performed (`:92–93`), and AW's `scroll down` physically moves toward the top, revealing content below (`android_world/android_world/env/actuation.py:138–165`). The phase-correlation artifact has 154 vertical agreements and 79 disagreements among 233 informative examples, with 810 additional unclear vertical cases. Horizontal evidence is only 4 agreements / 6 disagreements, with 158 unclear. This supports a majority vertical convention, not a clean empirical proof for all directions; I found no evidence requiring a global inversion. The older row-mean check is still noisier. **Fix:** retain the check script and representative manually inspected transition pairs, verify all four directions, and correct the artifact path in `docs/EVAL_PROTOCOL.md:33` to `results/data/scroll_convention_check.json`.

**Minor — endpoint mismatch.** `px_to_norm` divides by width/height; `norm_to_px` multiplies by width−1/height−1 (`train/agent_format.py:187–194`). This introduces a small endpoint offset in addition to normal quantization, not a 14% error. **Fix:** define one convention, test edge/center round trips, and change both sides together if changing it. Do not silently renormalize an already frozen benchmark.

### The 14% / bbox criterion

`eval/androidcontrol/score.py:47–60` implements the written rule correctly for valid canonical actions: require identical action type, then accept **bbox hit OR** Euclidean distance at most 0.14 in independently normalized x/y coordinates. In the 0–1000 grid the radius is 140, not 140√2. Inclusive bbox boundaries are correct. The bbox-only statistic (`:121–132`) includes failed parses and wrong action types in its denominator, as it should. Missing bboxes fall back to distance. The parser repairs described in section 3 corrupt the inputs to this otherwise correct geometry.

The rule is deliberately forgiving: on a 1080×2400 display, an axis-aligned 14% allowance is roughly 151 horizontal or 336 vertical pixels. Token-F1 ≥0.5 and bidirectional app-name containment are also forgiving. These are protocol choices, not implementation bugs. Report strict bbox and exact argument metrics alongside the primary score; do not present this custom scorer as automatically identical to every published AndroidControl evaluation.

### Major — 0.4–1 epoch is a reasonable pilot, not demonstrated sufficiency

The active L4 job requests 1,250 optimizer steps × effective batch 32 = about 40,000 rows, **0.403 epochs** of the reported 99,216-row mixture (`scripts/jobs/lfm3_train_l4.json:11–16`). Rows include terminal targets and low-mode copies, so this is not 40,000 independent trajectories. A full pass is a defensible initial format/behavior-adaptation budget for an already pretrained 2B VLM; it is not evidence that navigation has saturated.

`docs/DATASETS_AND_SPLITS.md:56–68` incorrectly turns a scaling result about **additional distinct training episodes** into a claim about diminishing returns after **one optimization epoch**. The [AndroidControl paper, sections 4.4–4.5](https://papers.neurips.cc/paper_files/paper/2024/file/a79f3ef3b445fd4659f44648f7ea8ffd-Paper-Datasets_and_Benchmarks_Track.pdf) studies dataset size and extrapolated accuracy, not an epoch optimum for LFM3. **Fix:** compare fixed checkpoints around 0.1/0.25/0.4/0.7/1.0 epochs on held-out validation episodes, separating action quality, grounding, terminal behavior and loss. Extend training only if validation improves; keep the frozen test out of this selection. No answer data and no on-policy recovery data are genuine limits that more repeats alone will not resolve.

## 2. Training implementation, prompt parity, and loss

### The intended loss and LoRA path are supported by source

The builder puts JSON in assistant `content` and the instruction in `reasoning_content` (`data/build_androidcontrol.py:231–233`). `train/sft_vlm.py:121–124` enables assistant-only loss and disables truncation. This is not merely an ignored configuration flag in the pinned libraries: [TRL 1.16.0's vision collator](https://github.com/huggingface/trl/blob/v1.16.0/trl/trainer/sft_trainer.py#L385) prepares image-first messages, requests `return_assistant_tokens_mask`, and masks non-assistant labels to −100 at lines 412–415. Its multimodal helper preserves `reasoning_content`.

The [public LFM3 template](https://huggingface.co/LiquidAI/LFM3-VL-2B/blob/main/chat_template.jinja) contains generation markers encompassing reasoning, JSON and the assistant end token. I also extracted the **actual local GGUF template**, and rendered it and the checked-in Qwen template with TRL's versioned preparation helper. Both produced an assistant span containing `<think>intent</think>`, JSON and `<|im_end|>`, excluding the user goal. With thinking enabled, the inference prompt was an exact character prefix of the corresponding training sequence. [Checks](template_render_checks.json), [reproducer](check_template_rendering.py), [versioned dependency excerpts](dependency_evidence.txt).

`train/patch_qwen35_template.py:10–27` places the assistant body and end token inside generation markers, while keeping the role header outside. Its single-occurrence assertions guard against an unexpected input template. No confirmed Qwen masking defect was found. These are character/source checks, **not a tokenizer-mask dump or a live GPU forward/backward verification of the active VM**. Saving one actual masked batch and trainable-parameter listing would close that remaining assurance gap.

The target regex is restricted to `language_model` modules (`train/sft_vlm.py:38,90–93`), so it does not directly place LoRA in the vision tower. Crucially, the active wrapper passes an empty `--modules_to_save` list (`scripts/vm_train.sh:18`), overriding the Python default that would otherwise fully train the multimodal projector. Thus the listed L4 recipe is consistent with language-only adaptation.

**Minor — default discrepancy.** Running the Python script with defaults would also train `multi_modal_projector` (`train/sft_vlm.py:39,87–92`). **Fix:** make projector training an explicit opt-in and save every trainable parameter name/count. For other architectures, inspect regex coverage rather than assuming this LFM-oriented module list adapts every intended layer.

### Major — input-text semantics differ across benchmarks

The official AndroidControl [action definition](https://github.com/google-research/google-research/blob/master/android_control/README.md#action-space) says `input_text` does **not** press Enter. AW's executor does (`android_world/android_world/env/actuation.py:104–105`), and `lfm_agent.py:124–131` uses that executor directly. The shared system prompt only says it types into the focused field (`train/agent_format.py:27`). This is a verified transition mismatch even though `docs/DATASETS_AND_SPLITS.md:76–77` acknowledges AW's behavior. A text-entry training example can therefore teach a different resulting screen than the online action produces.

**Suggested fix:** preserve the official AW executor for comparable AW results, document the semantic difference, and train/test transfer cases using that executor. Add explicit enter/submit behavior to suitable new data or a declared adapter; do not secretly change AW actuation to make the SFT data fit. This issue can hurt transfer without constituting a bug in offline string matching.

### Major — checkpoint and run identity are not locked

Model/processor/dataset loads omit immutable revisions (`train/sft_vlm.py:61,72,82`; `eval/androidcontrol/generate.py:37,47`). Training writes `run_config.json` **before** deciding to resume, resumes any local `checkpoint-*`, and catches a failed hub restore before continuing with fresh training (`train/sft_vlm.py:52,149–168`). No compatibility check ties the restored checkpoint to dataset shard hashes, model revision, template, module targets, or optimizer schedule. The same output/hub defaults could mix experiments on a later rerun. I did not find evidence that the active L4 run has already done so.

**Suggested fix:** create an immutable experiment manifest before training; compare it on resume, reject incompatible runs, and fail a requested resume if checkpoint retrieval fails. Record whether the run started fresh, actual library versions, adapter parameter names, checkpoint step, dataset revision and source hashes. Preserve the prior configuration instead of overwriting it. Use a different run identity for Qwen and for different training schedules.

### Image and inference parity

The shared resize returns **576×1280** for 1080×2400, or 737,280 pixels / 720 merged 32×32 image positions. Builder and AW call this helper; HF training and offline generation use the same min/max pixel settings (`train/agent_format.py:155–184`; `train/sft_vlm.py:72–75`; `eval/androidcontrol/generate.py:47–50`; `eval/androidworld/lfm_agent.py:88`). The [native image processor](https://huggingface.co/LiquidAI/LFM3-VL-2B/blob/main/image_processing_lfm3_vl.py) and [configuration](https://huggingface.co/LiquidAI/LFM3-VL-2B/blob/main/processor_config.json) support the factor-32 dynamic resize. Local mmproj metadata confirms patch size 16, merge 2 and a compatible pixel range. No gross resize or coordinate-scale mismatch was found.

**Minor — “same” is too strong beyond this.** Stored training/offline screenshots are JPEG quality 92, whereas AW sends PNG of the resized live frame (`data/build_androidcontrol.py:82`; `lfm_agent.py:27–30`). HF and llama.cpp pixel/tensor parity was not measured. Offline has 256 output tokens; AW defaults to 512. Base is no-think while FT is intended to think, so a future improvement combines training and decoding policy changes. The local GGUF contains a 1.1 repeat-penalty metadata default while offline explicitly sets 1.0; AW does not send that parameter. The server's effective override was not obtainable, so an actual penalty mismatch is **unconfirmed**.

**Fix:** record effective runtime settings, template hash, input dimensions and image-token counts; compare a fixed screenshot through HF and the shipping runtime. Publish base/FT with matched decoding as an ablation, and keep separately named deployment-policy results. Re-run a fixed held-out subset after GGUF conversion. Desktop-server latency is not phone latency.

### Loss behavior in the available log

The log grew during the audit. The final [preserved log](train_log_snapshot_pass1.jsonl) has four records, corresponding to `results/training/lfm3vl2b/train_log.jsonl:1–4` at the cutoff:

| Optimizer step | Epoch | Loss | Gradient norm | Token accuracy | LR |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.000323 | 2.1750 | 7.1344 | 71.87% | 0 |
| 10 | 0.003225 | 1.8146 | 2.5914 | 74.29% | 0.00004737 |
| 20 | 0.006451 | 0.6029 | 1.0471 | 86.66% | 0.00010000 |
| 30 | 0.009676 | 0.5071 | 0.6734 | 88.70% | 0.00015263 |

This is a plausible early format-learning curve: finite losses, decreasing gradient norms, increasing token accuracy, and approximately stable 10.28 GB peak allocation after the initial record. It has seen about 960 row presentations, **under 1% of one epoch**, not 0.4 epochs. There is no validation-loss record, completed summary, or downstream quality measurement. Token accuracy on reasoning/JSON is not action success.

`warmup_steps=0.03` is **not a bug in the pinned Transformers version**. [Transformers 5.20.2](https://github.com/huggingface/transformers/blob/v5.20.2/src/transformers/training_args.py#L2118) interprets values below 1 as a fraction, yielding 38 warmup steps for 1,250 updates. The observed LRs agree with that schedule. A larger initial unclipped gradient norm also does not establish instability; `max_grad_norm=1.0` is configured.

## 3. Evaluation harness and AndroidWorld patches

### Critical — silent cleanup failure and unrecorded teardown failure

`eval/androidworld/android_world_local_fixes.patch:75–95`, applied at `android_world/android_world/utils/file_utils.py:125–134`, tries normal and root deletion and then returns normally even if **both** fail. A mock of the real function confirms that behavior. Tasks can then inherit files from prior episodes. That can change initialization or reward in either direction; no successful deletion/postcondition is required.

There is a second boundary problem: upstream `_run_task` catches initialization/agent/judge exceptions, but calls `task.tear_down` outside that protected block (`android_world/android_world/suite_utils.py:244–259,288`). Checkpointing occurs only after `_run_task` returns (`:394–403`). The supplied run actually crashed here on camera cleanup (`logs/aw_run_base.log:4867–4885`), and later resumed the same run directory (`:4991–5006`). Therefore “exceptions count as failures” is not implemented for every lifecycle phase, and the first camera attempt was not durably retained in the current episode files. Suppressing deletion failures is not a valid replacement for fixing this lifecycle boundary.

**Suggested fix:** protect and log the entire lifecycle, persist attempt identity and failure before continuing, and enforce a verified clean environment before the next task. If cleanup cannot be verified, mark the attempt/environment failed and reinitialize rather than carrying state forward. Freeze patches and restart a new comparable benchmark run. Preserve interrupted attempts instead of making them disappear on resume.

### Critical — monkey patch corrupts generated task data

Both `android_world_monkey_fix.patch:45–57` and the cumulative `android_world_local_fixes.patch:58–70` accidentally change `_NOUNS`, inserting strings `--pct-syskeys` and `0` after `monkey`. The live checkout contains this at `android_world/android_world/task_evals/utils/user_data_generation.py:921`. `generate_random_file_name` uses this list (`:134–138`). The list length changes from 51 to 53, altering seeded random choices even when neither bogus word is selected. An isolated comparison of the first choice for seeds 0–99 changes **74/100** choices; this is a deterministic vocabulary demonstration, not an estimate of the percentage of affected benchmark tasks.

**Suggested fix:** remove the vocabulary hunk, retain only actual monkey-command changes, regenerate task parameters from the unmodified vocabulary, and rerun affected comparisons with a locked patch set. Current seeded task generation is not identical to stock commit `55ddaf5`.

The command-only monkey changes, configurable adb port, and avoiding killing a shared adb server do not directly inspect model output or modify rewards. Those are defensible operational adaptations if documented and applied consistently. They do **not** make the vocabulary and best-effort-cleanup changes benign. The two monkey-containing patch files overlap and should not be treated as independent patches to stack blindly.

### Major — summarizer does not handle the exceptions it promises to count

Upstream `_create_failed_result` writes `episode_data=np.nan`, `episode_length=np.nan`, and `is_successful=np.nan` (`android_world/android_world/suite_utils.py:544–557`). `summarize_aw.py:42–43` repairs only success; `ed = ep.get("episode_data") or {}` leaves truthy NaN unchanged. Line 45 then raises `AttributeError: 'float' object has no attribute 'get'`. This was reproduced using a synthetic trusted pickle. A separate conflicting record with `exception_info` and success 1.0 is counted as successful while also incrementing `n_exceptions_counted_as_fail`; the exception flag never forces the reward to zero.

**Suggested fix:** require `episode_data` to be a mapping; normalize all numeric fields with finite checks; explicitly set success to zero when an exception is present; preserve missing data as null; serialize with `allow_nan=False`. Handle unreadable/in-progress files distinctly from completed failures. Include all scheduled task instances in a final completion manifest. [Reproducers and outputs](audit_checks_results.json).

### Major — parser leniency materially changes measured validity

`train/agent_format.py:108–151`, shared by offline scoring and AW, scans for a decodable object, tolerates trailing content, accepts aliases, clips coordinates, and coerces an absent/invalid `goal_status` to `complete`.

Reproduced examples:

| Raw output defect | Production outcome |
|---|---|
| `{"action_type":"status"}` | Complete terminal success |
| `{"action_type":"status","goal_status":"banana"}` | Complete terminal success |
| Click at `[-1000,500]`, GT at `[0,500]` | Clipped into a successful click |
| Click with `Infinity`, GT at the right edge | Clipped into a successful click |
| Valid action followed by an extra brace or another action | First object accepted |
| Click containing `NaN` | Counts as parsed; then online coordinate conversion raises |

The NaN conversion is outside the online execution `try` (`lfm_agent.py:121–132`). `_query` also permits parsing a JSON object from reasoning when content is invalid (`:93`), potentially executing a contemplated action rather than a final answer. Leniency can be a legitimate deployment adapter, but it is not a strict parse rate for the documented one-action format. The rate of repaired outputs can differ strongly between base and trained models.

**Suggested fix:** freeze a canonical schema and reject nonfinite/out-of-bounds/wrong-type arguments and invalid terminal statuses. If keeping repair behavior, separately report strict validity, repaired validity and repaired-action SR for every model under the identical predeclared policy. Never silently promote malformed status to completion. Put conversion/validation inside the recorded failure boundary.

### Major — missing rows and stale resumes can bias offline numbers

`score.py:93–101` treats all **present** rows of an episode as the entire episode. A one-step correct prefix scores episode SR 1.0 even if later steps are absent. `generate.py:45–46` can cut an episode with `--limit`, and generation failures leave an appended partial file. `generate.py:54–59` resumes solely by `(episode_id, step_idx, mode)`; it does not check the model, dataset revision, thinking flag, pixel budget, prompt, generation settings or row content. Reusing a name can silently mix experiments. Duplicates and unexpected test IDs are also not rejected by the scorer.

**Suggested fix:** validate against a frozen expected-row manifest; report missing and duplicate keys and refuse a headline complete-test score until coverage is established. Score missing outputs as failures under an explicitly declared failure policy. Bind resume files to an immutable run identity and handle interrupted trailing lines explicitly. The independent scorer supports `--expected-rows` for this purpose.

### Major — retry cost and initial parse failures are discarded

Each retry overwrites `resp`, and only the last response's latency, tokens, timings and parsed action are saved (`lfm_agent.py:90–106`). `summarize_aw.py:45–51,73–76` therefore measures **last-attempt** latency and **after-retry** parse failures. It cannot tell how many first attempts failed or recover their compute cost. Identical greedy retries receive no corrective prompt, so they may simply repeat the same error.

**Suggested fix:** serialize a list of attempts with raw response, finish reason, parse error, elapsed time and usage; aggregate total model time/tokens per agent step and distinguish first-attempt from final validity. Keep action execution failures as a separate metric. This also prevents misleading comparisons to systems using different retry policies.

### Minor harness/reporting issues

- **Mean reward is not necessarily a full-task completion count.** `summarize_aw.py:55,68` averages raw success values. Some upstream composite tasks return 0.5 for completing one of two parts (`android_world/android_world/task_evals/composite/system.py:49,87`; `composite/markor_sms.py:68`). Upstream also averages rewards, while its console uses a `>0.5` success threshold. **Fix:** preserve the official reward mean, report binary completion with an explicit criterion separately, and avoid ambiguous “N successes” from fractional rewards. All frozen observed rewards here are exactly zero, so the distinction does not change this snapshot.
- **Lists are truncated.** `summarize_aw.py:39` keeps only the first episode in a pickle list. Current incremental files each contain one item, so this did not alter the observed result. **Fix:** iterate every item and deduplicate by task/instance/attempt policy. Reject invalid or out-of-range success values instead of blindly applying `float`.
- **Difficulty labels are correct in this checkout.** The metadata path at `summarize_aw.py:26` resolves correctly. It contains 116 tasks with 61 easy / 36 medium / 19 hard labels. The partial-run labels below match it. No invented difficulty bug was found. If the file is missing, fail or prominently report unknown coverage rather than quietly proceeding as if stratification were available.
- **Job success propagation is weak.** `scripts/vm_blocking_jobs.py:29–36` prints completion and exits successfully even if a child failed; `launch_gpu_jobs.sh:9` suppresses bootstrap failure, and `colab_bootstrap.py:20–21` prints a failed pip code without enforcing it. **Fix:** propagate nonzero codes and verify actual pinned versions before jobs. `scripts/vm_push_data.sh:13` also expects `stats.json`, while the builder writes `stats-<tag>.json` (`data/build_androidcontrol.py:298–301`); align the legacy script with the actual artifact layout. These are pipeline reliability defects, not evidence that a completed score was already fabricated.

## 4. Independent AndroidControl scorer

Delivered [score_independent.py](score_independent.py), a standard-library implementation that neither imports nor copies `eval/androidcontrol/score.py` or `train/agent_format.py`. The separate audit reproducer imports production code solely to demonstrate defects; the independent scorer does not depend on it.

It reads the requested raw JSONL fields, computes type match, step SR, episode SR and parse rate overall, by mode, and by each overlapping subsplit, with raw counts. It keeps terminal rows separate and includes bbox-only accuracy. Overall episode aggregation uses `(mode, episode_id)` pairs so high and low trajectories are not accidentally merged. Empty denominators produce null.

The protocol leaves normalization and JSON-envelope tolerance underspecified. The scorer explicitly documents its choices: closed think prefix and one optional code fence are permitted; the remaining output must be exactly one JSON object; canonical field names, integral finite grid coordinates and explicit terminal status are required. No clipping, alias repair, default completion, duplicate JSON keys, trailing junk or NaN/Infinity is accepted. Text normalization uses Unicode word tokens and casefolding; F1 uses multiset overlap. App containment is case-insensitive and nonempty. These are disclosed independent-parser choices, so disagreement with production repair behavior is expected and must not be disguised as numerical equivalence.

Without an external reference manifest, episode SR is explicitly labeled **observed_rows_only**, because predictions cannot prove that their own episode tails are present. With `--expected-rows`, missing predictions are inserted as failures; extra keys, duplicate keys and conflicting GT metadata are errors. The reference should be exported from the frozen dataset, not reconstructed from predictions.

```sh
python3 -B results/codex/score_independent.py --self-test
python3 -B results/codex/score_independent.py predictions.jsonl \
  --expected-rows frozen_test_rows.jsonl --out results/codex/offline_metrics.json
```

The embedded synthetic test passed geometry boundaries, bbox override, exact/F1 text, action-type mismatch, app containment, status mismatch, malformed outputs, overlapping subsplits, high/low grouping, terminal separation, duplicate rejection and missing-row denominators. A separate CLI JSONL integration check passed; see [synthetic input](scorer_synthetic.jsonl) and [metrics](scorer_synthetic_metrics.json). These are synthetic test results only. **No real offline benchmark score is reported because no raw offline predictions were available.**

## 5. Partial base-model AndroidWorld results

Frozen run: `results/androidworld/lfm3vl2b_base_nothink/run_20261116T175808535091/`. Twelve locally written gzip pickles were hashed and independently read; every file contained one episode. The agent name is `lfm3vl2b_base_nothink_q4km`. The final observed finish timestamp is 18:45:09; capture occurred at 18:51:04. This is an alphabetical, nonrandom prefix of the task suite, **not a 116-task estimate** and not a fine-tuned-model result.

| Task | Difficulty | Steps | Final parse failures | Execution failures | Outcome |
|---|---|---:|---:|---:|---|
| AudioRecorderRecordAudio | easy | 12 | 0 | 0 | failure, no termination |
| AudioRecorderRecordAudioWithFileName | easy | 20 | 10 | 0 | failure, no termination |
| BrowserDraw | easy | 20 | 0 | 6 | failure, no termination |
| BrowserMaze | easy | 20 | 0 | 7 | failure, no termination |
| BrowserMultiply | hard | 22 | 0 | 7 | failure, no termination |
| CameraTakePhoto | easy | 10 | 1 | 0 | failure, no termination |
| CameraTakeVideo | medium | 10 | 0 | 0 | failure, no termination |
| ClockStopWatchPausedVerify | easy | 10 | 0 | 0 | failure, no termination |
| ClockStopWatchRunning | easy | 10 | 0 | 0 | failure, status infeasible |
| ClockTimerEntry | easy | 10 | 0 | 0 | failure, no termination |
| ContactsAddContact | easy | 12 | 0 | 0 | failure, no termination |
| ContactsNewContactDraft | easy | 12 | 0 | 0 | failure, no termination |

**Observed totals:** 0/12 successes; 168 steps; 11/168 = **6.55% after-retry parse failures**; 20 execution failures; 1/12 = **8.33% self-termination**, specifically infeasible; no answer actions. Difficulty counts are easy 10, medium 1, hard 1, all zero success. The remaining **104 tasks were not observed in this snapshot** and are neither scored as completed failures nor silently called a completed-suite denominator. There are no episode-level exception records among these 12, but the run log contains the earlier uncheckpointed teardown exception discussed above.

Production summary and independent extraction agree on these observed counts. [Independent results](aw_independent_final_pass1.json), [production summary](aw_summary_original_final_pass1.json), [independent extractor](summarize_aw_independent.py). The stricter independent format parser rejects **21/168 = 12.50%** of saved outputs, compared with production's 11, demonstrating a real strict-versus-repaired validity difference. This is a post-hoc syntax audit; it does not change the actions already executed or the online success outcome.

The mean saved model latency is **2.760 s**, median **2.742 s**, with **1,094.49** mean saved prompt tokens. These describe the last HTTP attempt only, on the local serving setup. Episode runtimes total 1,180.04 s and include other work; neither statistic is a validated phone-speed measurement.

### Observed failure modes, with evidence and fixes

1. **Schema failures:** ten unparseable AudioRecorderWithFileName outputs request `open_app` with a point/notes but no app name; one camera output has malformed JSON. Several additional malformed outputs with extra braces are accepted by repair. Evidence: saved `episode_data.model_content` and `parsed_action`, summarized per file in the independent JSON. **Fix:** use a declared schema-constrained output path or instruction tuning; keep strict and repaired validity separate. Parser implementation severity is major, as above.
2. **App-resolution loops:** all 20 recorded execution failures are `open_app("file manager")` in the three Browser tasks. It falls through to an invalid adb monkey package invocation. `lfm_agent.py:132–133` records the exception but does not put an execution-failure explanation into subsequent model history; history already says the action happened (`:114`). **Minor agent-design issue; fix:** use a fixed declared app alias policy or teach valid names/UI navigation, and return execution feedback consistently to all agents. Do not add aliases selectively after seeing which model failed. Count execution failures separately from JSON failures.
3. **Onboarding/navigation and repeated gestures:** AudioRecorder alternates app launch/home actions, and its last saved pre-action frame is still the setup screen. CameraTakePhoto repeatedly long-presses near the shutter. BrowserDraw's last saved frame is a Chrome/launcher transition rather than the requested drawing. I inspected the extracted [audio frame](aw_AudioRecorderRecordAudio_step12.jpg), [browser frame](aw_BrowserDraw_step20.jpg), and [camera frame](aw_CameraTakePhoto_step10.jpg). These are stored pre-action thumbnails, not new observations of the live emulator or proof of the post-action state. **Fix:** validate initial app setup and transition stabilization consistently, then test recovery and repetition handling without changing reward rules.
4. **Failure to finish:** eleven episodes consume their budget without signaling completion; the remaining one declares infeasible. Upstream stores task success only when `interaction_results.done` is true (`suite_utils.py:261`). Thus zero stored success does **not** prove no useful UI operation occurred; successful state without completion would also be zero. **Fix:** separately log raw task-state reward, agent termination and final reward, and evaluate termination training before attributing all zeroes to grounding.

The episodes do not justify attributing AudioRecorderWithFileName failure to an upstream task bug: these traces already fail to launch/use it reliably. Nor do they support conclusions about the fine-tuned checkpoint. Patch/state issues prevent treating this pilot as a clean published baseline even though its observed zero-success count is straightforward to reproduce.

## 6. Other small VLMs worth evaluating

The following recommendations distinguish verified available artifacts/runtime paths from vendor-reported scores. I did not reproduce other authors' benchmark results or measure these models on this user's phone. Quantized weights fitting in storage do not establish acceptable RAM, prefill, thermal behavior or sustained agent latency.

| Priority/use | Candidate, below the 4B cap | Verified evidence and qualification |
|---|---|---|
| First alternative SFT backbone | **Qwen3-VL-2B-Instruct** | Official image/text checkpoint and an [official Qwen GGUF distribution](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF) provide a concrete llama.cpp deployment path. Good controlled counterpart to the Qwen3-VL-derived GUI specialists. Check its native prompt and coordinate convention before sharing a recipe. |
| Next SFT candidate | **Qwen3.5-2B** | The [official model card](https://huggingface.co/Qwen/Qwen3.5-2B) verifies a vision encoder plus 2B-language-backbone hybrid and explicitly positions the small model for task-specific tuning. The [llama.cpp project](https://github.com/ggml-org/llama.cpp/blob/master/README.md) demonstrates Qwen3.5-family GGUF support, but I did not verify a publisher-owned 2B GGUF artifact or this exact model on a phone. Validate conversion/runtime parity before committing a full training budget. |
| Evaluate stock before more SFT | **GUI-Owl-1.5-2B-Instruct** | The [publisher model card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct) identifies the Qwen3-VL foundation and publishes 2B weights; it reports 67.9 AndroidWorld. That is a verified **author-reported claim**, not independently verified performance here. Use its native agent interface first, then a documented common adapter. Its prior GUI/environment training makes it a specialist baseline, not evidence of contamination-free transfer. |
| Evaluate stock before more SFT | **MAI-UI-2B** | [Publisher weights](https://huggingface.co/Tongyi-MAI/MAI-UI-2B/tree/main) and [config](https://huggingface.co/Tongyi-MAI/MAI-UI-2B/blob/main/config.json) verify an available Qwen3-VL-based 2B GUI checkpoint. Its exact quantized derivative and phone behavior remain to be validated; shared architecture supplies a plausible conversion path, not a finished phone qualification. Audit its training provenance before making clean-AW comparisons. |
| Smaller deployment control | **LFM2.5-VL-1.6B** | The [publisher's GGUF distribution](https://huggingface.co/LiquidAI/LFM2.5-VL-1.6B-GGUF) supplies a concrete compact deployment baseline. Include the matching vision projector and buffers in memory accounting. This tests whether LFM3's extra capacity translates to this agent task; no superiority claim is needed. |
| Lower-priority architecture/efficiency control | **SmolVLM2-2.2B-Instruct** | The [publisher card](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct) provides the image-capable checkpoint and tuning guidance; [llama.cpp's multimodal documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md) explicitly lists its GGUF. It is a useful portable control, not an established AndroidWorld winner. |

For the two GUI specialists, Qwen3-VL compatibility and the official Qwen runtime path are deployment **inferences**, not tests of their exact converted artifacts. They still require a model-specific action adapter and output/template checks. Avoid assuming a model labeled “4B” necessarily has ≤4B total parameters including vision; similarly, “E2B” or “A3B” may describe effective/active rather than resident parameters. I have not included those borderline models as confirmed fits.

A budget-conscious order is: first repair the harness, then run stock GUI-Owl/MAI and a Qwen3-VL-2B baseline, then compare matched SFT runs for LFM3 and the chosen Qwen model. Hold data revision, information available in history, image budget, parser, retries and evaluation seeds constant; report native-interface specialist results separately if the adapter changes their behavior. Select on validation, then run the frozen test and a complete AW suite. Use multiple seeds for a final comparison and episode/task-level uncertainty intervals. The documented roughly ±4 percentage points at N=116 is approximately a **one-standard-error worst-case value**, not a 95% interval, and does not apply to this nonrandom 12-task prefix.

## Final verdict

**Suitable for development experiments; not yet suitable for trustworthy headline benchmark claims.** The supplied ID lists are disjoint; episode routing, basic action conversion, the documented click geometry and intended assistant-loss template are mostly sound. The partial base-model outcome is reproducible as **0/12 at the stated cutoff**, and the available training loss is behaving plausibly early in training.

Before publishing numbers: restore benchmark-preserving patches and enforce clean resets; checkpoint lifecycle failures; fix NaN/exception summarization; freeze parser policy and complete-row/task denominators; eliminate or explicitly label privileged offline history; lock data/model/template/runtime identities; and evaluate the final checkpoint plus its quantized artifact under matched, complete runs. More training cannot substitute for those measurement fixes. The requested independent scorer and reproducers are delivered, but the missing raw offline predictions and processed dataset prevent a stronger end-to-end certification in this pass.
