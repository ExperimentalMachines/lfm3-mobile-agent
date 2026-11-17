**Fourth v2 SFT verification — 2026-11-17 — narrow B1/B2 follow-up**

**Final decision: GO for training both LFM3-VL-2B and Qwen3.5-2B on `experimentalmachines/AndroidAgent-SFT-v2` @ `42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a`, using the v1 recipe: 1,250 steps × effective batch 32 = 40,000 row presentations.** The two blocking conversion defects from [verification 3](codex_data_v2_verify3.md) pass this bounded re-verification. No new B1/B2 blocker was observed. The previous judgment that residual source-label noise is non-blocking is unchanged.

Dataset: [immutable DATA revision](https://huggingface.co/datasets/experimentalmachines/AndroidAgent-SFT-v2/tree/42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a). Inspected the B1/B2 patch in `cb1ffec` and the current builder at local HEAD `4c3c5a7337ee7da4cb256322cafdfa50710fc7aa`. Builder SHA-256: `d96819262789c6296fa7fe3e8079178568ef8b81f71ab4429b93f8984fc0f946`. At this HEAD, `HEAD~1` already contains the builder fix; `git show cb1ffec -- data/build_v2_mix.py` exposes the relevant change.

| Blocker | Status | Evidence |
|---|---|---|
| **B1 — false keyboard-submit merges delete non-submit actions and retain their dependent observations** | **PASS within the stated scope** | Actual source-loop fixtures cut hide-keyboard, toolbar-above-keyboard and suggestion taps; genuine bottom-right Search/Enter taps merge. All three named source episodes cut at the offending tap. Exact action/intent/history reconstruction matches all **2,195 Odyssey + 1,341 AMEX** downloaded rows, including **625 rows after submit merges**. Visually spot-checked **20 immediately following rows**, with **0 observed false merges**. |
| **B2 — control/selection drags emitted as generic scrolls** | **PASS within the stated scope** | All three named gesture paths fail the stricter geometry rule; actual loops cut before or at those steps. The complete published dev split contains no offending clock row or dependent suffix. Reviewed **20 published scroll rows**, ten per new source, prioritizing short/off-centre paths: **0 visible control/selection drags**. All **433** downloaded new-source scroll targets match their raw source paths and current acceptance rules. |

**Download and verification scope.** Used exactly **two train shards, `00002` and `00013`**, and **all three dev shards**, plus pinned stats. All five parquet files match their pinned Hub LFS SHA-256 values; the stats Git blob also matches. Total: **1,139,820,926 bytes**. Reused `results/codex/data_v2_cache`, including raw-source annotations; fetched missing annotation JSONs only. No other train shard was read for this audit. Evidence is isolated in `data_v2_cache/verify4_42f7f76364/`. [Download manifest](data_v2_cache/verify4_42f7f76364/download_manifest.json), [pinned inventory](data_v2_cache/verify4_42f7f76364/inventory.json).

| Population | Independently checked | Pinned full count |
|---|---:|---:|
| train / AndroidControl | 7,026 | 55,936 |
| train / GUI-Odyssey | 1,195 | 9,979 |
| train / AMEX | 873 | 7,072 |
| train / ScreenQA | 779 | 5,995 |
| dev_odyssey | 1,000 | 1,000 |
| dev_amex | 468 | 468 |
| dev_screenqa | 500 | 500 |
| **Total** | **11,841** | **80,950** |

**B1 fixtures and named cases.** Executed the actual current `odyssey()` and `amex()` function bodies, preserving their branches and histories. Only image materialization was stubbed; temporary source files and screenshot-name membership exercised the real loops. Traced their actual `continue`/`break` branches, rather than relying solely on a separately implemented classifier. All **17 loop fixtures** passed, plus the quota/cap fixture.

For `TEXT → tap → result tap`, hide-keyboard at `[500,950]`, toolbar at `[686,499]` and suggestion at `[249,453]` retain only TEXT and cut at the tap. Genuine bottom-right Search and Enter at `[920,930]` retain TEXT plus the result, with one `input_text` history action. Negative dismissal wording overrides a bottom-right coordinate. A second submit-like tap cuts; an ordinary app tap remains. AMEX soft-key taps and explicit `PRESS_ENTER` merge correctly, and a second submit-like tap cuts. [Actual-loop fixtures](data_v2_cache/verify4_42f7f76364/actual_loop_fixtures.json).

| Previously reported episode/step | Current actual-loop result | Published evidence in this bounded download |
|---|---|---|
| WPS `5994133452263654`, toolbar tap **27**, formerly dependent row **31** | Cuts at **27**; last retained step **26**. No image-picker suffix is constructed. | Episode absent from the two sampled train shards. |
| `4912446279173881`, suggestion tap **4**, formerly dependent row **5** | Cuts at **4**; last retained step **3**. | Episode absent from the two sampled train shards. |
| `6951686067814574`, minimize-keyboard tap **4**, formerly dependent row **5** | Cuts at **4**; last retained step **3**. | Episode absent from the two sampled train shards. |
| `4394352513523177/22`, clock-hand drag | Cuts earlier, at rejected scroll **21**; last retained step **20**. The step-22 path independently fails geometry. | Episode absent from the two sampled train shards. |
| `0173202679441530/21`, dev clock-hand drag | Cuts earlier, at rejected scroll **20**; last retained step **19**. The step-21 path independently fails geometry. | **Entire published dev checked:** this episode contributes only step **7**; no step 21 or later suffix. |
| `4143524179769456/4`, text-selection-handle drag | Cuts at **4**; last retained step **3**. | Episode absent from the two sampled train shards. |

The exact candidate cutoffs above are established by actual-loop execution on the original annotations. Full-train absence of the named suffixes is supported by those cutoffs and the matching rebuilt stats/logs; **it is not an independent scan of all sixteen published train shards**. Absence from two sampled shards alone would not prove it. [Source replay and named-case evidence](data_v2_cache/verify4_42f7f76364/source_replay.json).

**Published spot checks.** Reconstructed complete histories from raw annotations for every downloaded Odyssey/AMEX row: **0 action, intent or history mismatches; 0 rows beyond a current cutoff**. This includes **517 Odyssey + 108 AMEX** rows following submit merges. Selected **20 immediately following rows**, ten per source with distinct episodes and deterministic seed `20261117`, and viewed their published screenshots. The ten Odyssey cases use bottom-right taps; the ten AMEX cases use explicit Enter. Their visible query/results states and retained histories support the merges. One Odyssey source instruction is stale (`9972379785892686/10`, TikTok-arrow wording); its bottom-right coordinate, raw search intention and subsequent `triller` results support submission. It does not demonstrate a deleted non-submit action.

For B2, reviewed **20 distinct published rows/images**, ten Odyssey and ten AMEX, ranked toward the remaining short/off-centre paths. Visible operations were list/page/gallery scrolling, launcher swipes and a scrollable calendar month grid; none dragged a clock hand, slider or text-selection handle. Also exercised real-loop fixtures rejecting drag wording, scrolling immediately after Odyssey long-press, short drags and diagonal drags, while retaining ordinary page swipes. These observations support the fix; the heuristic is not a universal proof of executor equivalence.

All **40 row IDs, images and individual judgments** are in the [visual ledger](data_v2_cache/verify4_42f7f76364/visual_review.md); [selection and raw contexts](data_v2_cache/verify4_42f7f76364/target_samples.json). Viewed all eleven contact sheets at original resolution. These are source-operation checks, not on-device replay or a new general source-label audit.

**Requested regression checks.**

| Check | Result |
|---|---|
| Pinned stats / every-row assertions | **PASS.** Downloaded stats equal `results/data_v2/stats.json` byte for byte. All four source-stage final log objects match; merge counts match; no build log contains a traceback. Action counters total **80,950**, exactly **78,982 train + 1,968 dev**. The builder's `verify()` is unchanged and runs before publication. Independently reran that actual function on all **11,841 downloaded rows**, in addition to the independent image/schema/history checks: no failures. Full-population counters remain builder-side evidence. |
| Train/dev image overlap | **PASS.** Pinned full-build assertion: **0**. Independently recomputed every downloaded JPEG and decoded RGB-pixel hash: **0 train/dev overlaps** by either measure, **0 source-qualified episode overlaps**, and every stored `img_sha` matches the bytes. |
| Caps / quotas | **PASS.** Full stats report maximum **3** train rows per Odyssey/AMEX episode. Observed maxima are Odyssey **3**, AMEX **3**, ScreenQA **2**; dev Odyssey **1**, AMEX **4**, ScreenQA **2**. The actual adversarial quota fixture returns **3 unique rows** from one episode across quota passes. All source totals remain below their ceilings; AMEX has **999 input_text**, **12 standalone Enter**, and AC **5,998 terminal** train rows. |
| Other scoped invariants | **PASS.** All downloaded images decode, are portrait and have expected resize dimensions; strict target JSON equals `gt_action`; no exact image+messages duplicate; no new-source terminal target; AMEX intents remain blank. `verify`, sampling, merge, row/materialization, AC and ScreenQA function bodies are unchanged by the B1/B2 patch; AC and ScreenQA stage stats equal verification 3. |
| Both jobs / actual loading | **PASS.** `scripts/jobs/lfm3_v2mix_g4.json` and `scripts/jobs/qwen35_2b_v2mix_g4.json` both use `TRAIN_DATA=experimentalmachines/AndroidAgent-SFT-v2@train#42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a` and the same `DEV_REV`. Recording stubs executing the real training/evaluation loader bodies confirm the pin reaches both Hub listing and `load_dataset`. Pipeline dev counting and generation propagate it. |

[Independent checks](data_v2_cache/verify4_42f7f76364/checks.json), [actual sampled builder assertions/caps](data_v2_cache/verify4_42f7f76364/sample_builder_assertions.json), [pinned stats/log/job/loader evidence](data_v2_cache/verify4_42f7f76364/build_evidence.json). The previously noted `_provenance()` HEAD-reporting caveat remains diagnostic only; the actual load path is pinned.

Both jobs retain **1,250 steps, batch 8 × accumulation 4, learning rate `2e-4`, LoRA rank 64 / alpha 128, `MAX_PIXELS=774400`, and thinking-enabled training**. No builder, dataset, trainer or job was edited, and no training/device run was launched. **LFM3-VL-2B: GO. Qwen3.5-2B: GO.** This decision applies to this immutable revision and the requested v1-budget experiment.
