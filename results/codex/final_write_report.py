"""Render the final report from recomputed audit artifacts."""
import datetime, json, pathlib, shlex

ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'results/codex'
read=lambda p:json.loads((OUT/p).read_text())
ac=read('final_ac/audit.json');aw=read('final_aw_statistics.json');gen=read('final_general_statistics.json')
train=read('final_training_audit.json');data=read('final_data_audit.json');snap=read('final_snapshot_manifest.json')
mirror=read('final_mirror_audit.json')
assert mirror['official_test_in_mirror_train']==1238
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(map(str,r))+' |' for r in rows])
def ci(v,scale=100):return f'{scale*v[0]:.2f}–{scale*v[1]:.2f}'
def rate(v):return '—' if v is None else f'{v:.6f}'
labels={'lfm3vl2b-ac-lora_base':'LFM3 base, no think','lfm3vl2b-ac-lora_ft':'LFM3 FT, think',
        'lfm3vl2b-ac-lora_ft_nothink_high':'LFM3 FT, no think, high only',
        'lfm25vl450m-ac-lora_base':'450M base','lfm25vl450m-ac-lora_ft':'450M FT, inline intent'}
order=list(labels)
score_rows=[];ep_rows=[];manifest_rows=[]
for name in order:
    i=read('final_ac/'+name+'.independent.json');p=read('final_ac/'+name+'.production.json')
    def pair(block,field):return ' / '.join(rate(block[m][field]) if m in block else '—' for m in ['high','low'])
    ib=i['nonterminal']['by_mode'];pb={m:p[m]['overall'] for m in ['high','low'] if m in p}
    sb={m:p[m]['overall_strict_parse'] for m in ['high','low'] if m in p}
    score_rows.append([labels[name],pair(ib,'step_sr'),pair(pb,'step_sr'),pair(sb,'step_sr'),rate(i['terminal']['overall']['step_sr'])])
    ep_rows.append([labels[name],pair(ib,'episode_sr'),pair(pb,'episode_sr'),pair(sb,'episode_sr')])
    e=next(x for x in ac['predictions'] if x['name']==name)['identity'];m=e['manifest']
    manifest_rows.append([f'`{name}.jsonl`',f"{e['rows']:,}/{e['expected']:,}",f"`{m['config_hash']}`",f"{m['enable_thinking']} / {m['max_pixels']:,}", 'pass'])
legacy=next(x for x in ac['predictions'] if x['name']=='lfm25vl450m_base')['identity']
manifest_rows.append(['`lfm25vl450m_base.jsonl`','1,632/18,415','absent','0 / 0','FAIL'])

aw_names={'lfm3vl2b_base_nothink':'LFM3 base','lfm3vl2b_ft':'LFM3 FT','lfm25vl450m_ft':'450M FT',
          'guiowl15_2b_matched':'GUI-Owl matched','_smoke_guiowl_native':'GUI-Owl native sample'}
aw_rows=[];lat_rows=[]
for key,label in aw_names.items():
    s=aw['runs'][key]['summary']
    aw_rows.append([label,f"{s['successes']}/{s['n']}",s['exceptions'],f"{s['observed_rate']*100:.2f}% [{ci(s['wilson_95_observed'])}]",
       f"{s['successes']}/116 = {s['success_rate_116']*100:.2f}% [{ci(s['wilson_95_116'])}]",s['missing']])
    lat_rows.append([label,s['n_steps'],f"{s['latency_mean']:.3f} / {s['latency_p90']:.3f}",f"{s['prompt_tokens_mean']:.1f}",f"{100*s['strict_rate']:.2f}%"])
grows=[]
for m,label in [('lfm3vl2b','LFM3'),('lfm25vl450m','450M')]:
    for kind,x in gen['logprob'][m]['results'].items():
        grows.append([label+' '+kind.upper(),x['n'],f"{x['base_correct']}/{x['n']} = {100*x['base_correct']/x['n']:.2f}%",
           f"{x['ft_correct']}/{x['n']} = {100*x['ft_correct']/x['n']:.2f}%",f"{100*x['delta']:+.2f} [{ci(x['paired_bootstrap_95ci'])}]",
           f"{x['base_only']} / {x['ft_only']}",f"{x['mcnemar_exact_p']:.6g}"])
fail_rows=[]
for flag,label in [('unmapped_open_app','Unmapped `open_app` name'),('consecutive_waits_ge3','≥3 consecutive waits'),
                   ('consecutive_same_click_ge3','≥3 consecutive same clicks'),('no_termination','No status/answer termination')]:
    fail_rows.append([label]+[aw['runs'][n]['summary']['flags_among_failures'].get(flag,0) for n in ['lfm3vl2b_ft','lfm25vl450m_ft']])
fail_rows += [['Complete status but task failed',19,3],['Exception',0,3],['Any raw parsing mismatch with stored actions',0,0]]
tr_rows=[]
for m,label in [('LFM3-VL-2B','LFM3'),('LFM2.5-VL-450M','450M')]:
    t=train[m];ev=list(t['eval_losses'].values());c=t['config'];s=t['summary']
    tr_rows.append([label,f"{t['last_logged_step']:,} × {c['bs']*c['grad_accum']}",f"{s['train_rows']:,}",f"{s['epoch']:.6f}",
       f"{t['last10_loss_mean']:.6f}",f"{ev[0]:.6f} → {ev[-1]:.6f}",f"{c['lora_r']}/{c['lora_alpha']}; {c['lr']}"])

cut=datetime.datetime.fromisoformat(snap['timestamp_utc']).astimezone(datetime.timezone(datetime.timedelta(hours=8)))
parts=[f"""**Independent final evaluation — LFM Android agents**

Cutoff: **{cut:%Y-%m-%d %H:%M:%S} Asia/Manila** ({snap['timestamp_utc']}); checkout `{snap['git_head']}`. All evaluator writes are under `results/codex/`. Running episodes were not awaited. This is a recomputation of stored predictions and trusted local episode pickles, not new inference or a physical-phone test.

**Verdict:** offline action adaptation is supported; robust autonomous phone operation is not. LFM3's current closed-loop improvement is statistically inconclusive; 450M has no successful recorded AndroidWorld episode in this snapshot. Retention evidence is limited to two forced-choice benchmarks.

**AndroidControl: independent scoring and integrity.**

The frozen GT SHA-256 is `1926a44e0ffa7940b28866907d28913a5bd4af38f5b67463798cec8b6df25e84`. Its 18,415 unique rows comprise **8,444 high nonterminal + 8,428 low nonterminal + 1,543 high terminal** rows. High-only has 9,987 rows. High evaluates 1,543 episodes; low evaluates 1,542. All GT fields also match the pinned Hub dataset's non-image columns. The local split file equals [Google's official split file](https://storage.googleapis.com/gresearch/android_control/splits.json).

Rates below are **high / low**. “Independent” uses the existing, inspected, self-tested `results/codex/score_independent.py` without importing the production scorer. Both CLI scorers use frozen GT; missing independent predictions count as wrong. Episode rates exclude terminal rows and use teacher-forced history, so they are offline proxies for completion.
""",
table(['Prediction','Independent step SR','Repository lenient step SR','Repository exact-schema step SR','Terminal SR, both scorers'],score_rows),
'\n'+table(['Prediction','Independent episode SR H / L','Repository lenient episode SR H / L','Repository exact-schema episode SR H / L'],ep_rows),
"""
Differences come from parsing and app-name normalization:

* LFM3 base: leniency adds **202 high and 431 low** successes through extraction/repairs (e.g. trailing `]`, app-name aliases), plus **one high** punctuation-normalization match. The independent parser accepts harmless extra fields; repository exact-schema parsing rejects them. Thus the independent parser is not uniformly stricter than the repository's strict mode. Base parse rates H/L are independent **85.55/89.40%**, lenient **91.32/96.51%**, exact-schema **39.82/37.81%**.
* LFM3 FT differs by **one high and one low** app-name match; no-think FT by **two high** matches; 450M FT by **three high and five low** matches. The repository strips punctuation (`Weather&Radar` versus `Weather & Radar`, `Voice Recorder-URecorder`); the independent app matcher preserves it. All these outputs parse in both scorers. No geometry/text-F1 disagreement affected these totals.
* LFM3 FT has **3/18,415** malformed/unclosed outputs; 450M FT and LFM3 no-think FT parse completely. Matched no-think LFM3 still improves over base, but terminal sensitivity drops from **79.20% to 10.05%** when thinking is disabled. The main 71.48% versus 31.34% comparison changes thinking configuration.

Hub revisions were pinned: LFM3 `9df77c802f6a1b690b4738ca4a4288f6f166661b`; 450M `ae7c9a369fabac59c7257028d9f30a31a4128d80`. All matching prediction files and manifests were downloaded:
""",
table(['Hub eval filename','Rows / required','Recomputed config hash','Thinking / max_pixels','Integrity'],manifest_rows),
"""
For each passing file: no missing, extra or duplicate keys; prediction metadata matches GT; every row's model and config hash matches its manifest; the manifest hash recomputes exactly. Base identities are `LiquidAI/LFM3-VL-2B` and `LiquidAI/LFM2.5-VL-450M`; FT identities are `/content/runs/lfm3vl2b-ac-lora/merged` and `/content/runs/lfm25vl450m-ac-lora/merged`. LFM3 FT/no-think share fingerprint `266f78620fcc8043`; 450M FT has `0cc239497a006fcf`. These are consistency checks: base fingerprints contain an unpinned Hub name; local FT fingerprints hash partial weight bytes and an optional receipt. They do not cryptographically establish the complete evaluated weights or tie them to a served GGUF.

The legacy `lfm25vl450m_base.jsonl` is **invalid for benchmark reporting**: 16,783 missing rows; no row/manifest config hash or model fingerprint. The independent full-GT missing-as-failure SR is **5/8,444 = 0.000592 high; 22/8,428 = 0.002610 low; terminal 0**. The repository scorer correctly exits 2. Its separately run `--allow_incomplete` diagnostic reports **5/751 = 0.006658** and **22/748 = 0.029412** on observed rows only; those are not comparable full-test scores. No 450M `_ft_nothink_high.jsonl` exists at the pinned revision.

**AndroidWorld: frozen partial runs.**

Newest directories selected at cutoff: base `run_20261116T190932199444`; LFM3 FT `run_20261117T030335477504`; 450M FT `run_20261117T022926194002`; matched GUI-Owl `run_20261116T231457945810`. The native sample is physically under `_smoke_guiowl_native/run_20261116T225639669685`, as its saved summary says. There are no duplicate task/instance files. Exceptions, NaN rewards and missing tasks count as failures. 450M base is absent and skipped.
""",
table(['Run','Successes / recorded n','Exceptions','Observed % [95% Wilson CI]','116-denominator % [95% Wilson CI]','Unobserved of 116'],aw_rows),
"""
For unfinished runs, the 116-denominator value is the requested **current lower bound**, not a completed evaluation. Its Wilson interval is conditional on imputing missing tasks as failures; it is not an interval for the eventual full-run result. Observed-prefix intervals also do not fix nonrandom task ordering. The native 2/2 consists of two selected easy tasks, not a 100% score on the suite.

Paired LFM3 comparison requires identical **task, instance ID, seed and goal**: **47 pairs**, base 1/47, FT 3/47; both correct 1, base-only 0, FT-only 2, both wrong 44. Exact two-sided **McNemar p = 0.50** (Δ +4.26 pp). `MarkorCreateFolder` is excluded: the goal's timestamp-based folder name differs despite the same seed. There is no 450M base/FT comparison. The original base predates the answer-ends-episode change; the separate three-task answer-rule rerun has 0/3 and is not spliced into the 116-run. Harness equivalence is therefore incomplete even for seed-matched comparisons.

Recomputed telemetry (HTTP model-call time per step, including retries; prompt counts are the recorded final response's usage):
""",
table(['Run','Recorded steps','Mean / p90 seconds','Mean prompt tokens','Stored first-attempt strict validity'],lat_rows),
"""
Both FT sequences independently parse identically to their stored actions. GUI-Owl's “strict” flag is only its own tool-call parser success, not the LFM exact-schema test. “Compute-matched” means a one-image configuration, not equal total compute: matched GUI-Owl averages **2,343 prompt tokens**, versus **1,155** for LFM3 FT, with different histories/task mixes. These Mac measurements do not establish phone latency, memory, thermal behavior or BF16-to-Q4 accuracy retention.

**FT failure modes and classifier audit.** Counts below concern failed recorded episodes (**45 LFM3; 65 450M**); flags overlap. Repetition means ≥3 consecutive actions on a 25/1000 coordinate grid. “Complete but failed” describes the terminal signal and judge result, not a proven causal diagnosis.
""",
table(['Observed failure indicator','LFM3 FT','450M FT'],fail_rows),
"""
Concrete sequences: LFM3 `ClockStopWatchRunning` repeatedly opens `Stopwatch` then waits; the executor logs no matching activity. Both models use `File Manager` where the harness maps `files`. LFM3 also emits `Timer` and `Marker`; 450M adds `Expense`, `Note`, `SDKs`, `Calendar Pro`, and other unmapped names. These are interface failures, not necessarily nonexistent Android apps. LFM3 `MarkorChangeNoteContent` repeats click `[920,812]` eight times; 450M `BrowserDraw` has 17 consecutive waits. Both models sometimes complete answer-requiring Notes tasks without providing an answer; **neither FT run emits any `answer` action** in this snapshot. Valid JSON plainly does not imply successful behavior.

`eval/androidworld/failure_modes.py` is unsuitable as a causal failure taxonomy:

* **Lines 20–24, 38, 47:** GUI-Owl uses `action`/`coordinate`, while the classifier reads `action_type`/`point_2d`. Distinct GUI actions collapse to identical mostly-None keys; termination is missed. It labels all **50** nonexception GUI failures as loops, whereas only **18** meet the independent consecutive-action criterion. The other 32 labels lack that evidence.
* **Line 47:** removing waits and invalid steps before computing runs makes interrupted repetitions look consecutive: LFM3's saved repeated-action flags are **12**, versus **2** consecutive non-wait repeats; 450M **39 versus 34**. Such cycles can still be problematic, but the definitions differ.
* **Lines 40–41, 63–68:** “unknown” ignores supported default-URI names and package-name fallback; an initial unmapped name does not prove the episode remained stuck. “Loop until step limit” does not check the budget or screen progress. Status/answer labels cannot distinguish premature completion, an incorrect result or a judge/environment defect. Priority labels hide co-occurring flags.

Saved output arithmetic reproduces on the same files: base n=116, LFM3 FT n=48, GUI matched n=60. The saved 450M file is stale at **n=64**; cutoff n=65 adds `SimpleCalendarAddOneEventInTwoWeeks`. Retain flags and traces; do not treat these labels as established causes.

**General-knowledge retention.** Raw four-letter scores were re-argmaxed; every stored prediction/correctness flag agrees. Base/FT keys, gold answers and categories match exactly, without duplicate IDs. Δ intervals are paired percentile bootstraps, 100,000 resamples, seed 20261117; exact McNemar uses discordant counts and was cross-checked against SciPy. Units of Δ and its interval are percentage points.
""",
table(['Model / benchmark','n','Base','FT','Δ [95% bootstrap CI]','Base-only / FT-only','Exact McNemar p'],grows),
"""
LFM3 improves on this MMStar evaluation. The remaining comparisons detect no change, but **nonsignificance does not establish “no forgetting”**: the intervals permit MMLU losses of 1.7 pp (LFM3) and 2.3 pp (450M). No noninferiority margin was specified. MMLU is the fixed 1,000-item subset, not the full benchmark; no broad or quantized-phone retention claim follows. General-eval rows also lack per-row model/config/revision fingerprints.

Generation-mode results are excluded from the retention claim because answer formatting, truncated reasoning and parsing differ after SFT. LFM3 unparsed answers fall **280→75/1,500 MMStar** and **534→131/1,000 MMLU**, inflating apparent generation accuracy changes (**46.07→55.53%**, **28.6→45.8%**) independently of knowledge. 450M generation scores are **41.6→40.87% MMStar**, **39.4→38.3% MMLU** (MMLU unparsed **19→23**). Forced-choice scoring avoids free-form answer extraction; it remains a prompt-dependent recognition test, not a general generation-quality test.

**Training and leakage evidence.** Full `log_history.json`, resumed JSONL logs, configs, summaries and `loss_curves.png` were inspected; all four training files per model match their pinned Hub copies byte-for-byte.
""",
table(['Model','Optimizer steps × effective batch','Dataset rows','Final epoch','Mean last 10 logged train losses','Val loss at step 250 → final','LoRA r/alpha; LR'],tr_rows),
f"""
All intermediate validation losses decrease monotonically. The plot agrees with the logs; these curves show no validation-loss evidence of overfitting. The 450M train loss includes general replay while its validation loss is AC-only, so their levels are not directly comparable. LFM3 sees 40,000 row exposures (~0.403 epoch); 450M runs 60,000 exposures, consistent with 48,000 agent + 12,000 replay rows (20%). Summary wall times **4,015.68/3,431.06 seconds** cover resumed training calls, not total training or billing.

The pinned dataset `1c49e7d117bd109eebd976b04deefa708b0e2007` contains **99,216 train rows / 13,573 episodes**, **827 validation rows / 137 episodes**, and the **18,415-row test**. Reading non-image columns of every shard found **zero train/val/test episode intersections**, no duplicate row keys, no IDs outside official splits, and zero GT field mismatches. Thirty official train episodes are absent; the surviving stats cannot attribute all 30 to the AW-app filter. Independently reading the source mirror's train episode IDs reproduces the cards' **{mirror['official_test_in_mirror_train']:,} official test episodes in mirror train** claim.

No positive split-leakage evidence was found. Limits: the AW-app filter is a name heuristic; screenshot duplicates across distinct episodes and pretraining contamination were not tested. 450M replay is recorded only as `/content/data/replay`, without an archived row/image roster or source revisions proving no MMStar/MMLU overlap. Run configs record model/dataset SHAs but loading code does not pin those revisions. There is no isolated replay ablation. AC train has **13,573 positive `complete` labels and zero `answer`, `keyboard_enter` or `infeasible` labels**; that supervision gap is consistent with, but does not prove the cause of, the observed failures.

**Claim-by-claim corrections.** Numeric lines in the two documents and downloaded cards are inventoried in `final_numeric_claim_inventory.json`.
""",
table(['Source / claim','Audit finding'],[
 ['`SUMMARY.md:10`, `STATUS.md:17`: LFM3 base high 0.315; SUMMARY low episode 0.172','Current Hub predictions give **0.313359 high**, **0.173152 low episode** (0.313 / 0.173 rounded). The old local `base_nothink` metrics explain the stale numbers; low step 0.634 and high episode 0.027 still round correctly.'],
 ['`STATUS.md:17`: independent base 0.291 / 0.584','Current Hub outputs give **0.289318 / 0.582463**. The displayed figures belong to the earlier prediction set.'],
 ['`STATUS.md:19`: 450M base MMStar 41.6%, MMLU 39.4%','These are generation-mode figures. Forced-choice baseline is **38.4667% / 39.9%**, as SUMMARY and the FT comparison correctly use.'],
 ['`STATUS.md:18,20`: “no forgetting”','Too strong; use the paired intervals above and “no detected decline on these tests.”'],
 ['LFM3 card and `SUMMARY.md:11`: McNemar p=0.00','Rounding artifact, not zero: **3.02807×10⁻⁷**. All other displayed forced-choice percentages, deltas and p-values reproduce.'],
 ['STATUS training “running”, base “in pipeline”, GGUF conversion “next”; SUMMARY blank partial AW rows','Stale/incomplete at cutoff: final training and current AC base artifacts exist; local FT GGUFs and the partial AW episodes above already exist. No complete FT suite result is available.'],
 ['Both cards / STATUS: FT AC, episode, terminal numbers; LFM3 unseen app/task/category','Reproduce with the repository scorer at displayed precision, including **0.671367 / 0.696237 / 0.681316** unseen H step SR. Small independent differences are app-name normalization, not unexplained errors.'],
 ['STATUS 450M “100% valid”; both cards training recipes; quantized sizes','Reproduce: 450M AC **18,415/18,415** valid; recipe metadata agrees. LFM3 Q4 **1,099,627,104 bytes + 203,031,872-byte mmproj**; 450M total **332,128,128 bytes** supports “≈330 MB”. Sizes do not measure RAM.'],
 ['SUMMARY/STATUS base 1/116, 2.25 s, 1.1k tokens; native 2/2, 61 s, 10.7k','Reproduce with the scope restrictions above. Native 100% is only the selected two-task sample.'],
 ['450M card: “~720 image tokens” using the common resize rule','Not established for its HF processor: manifest max_pixels=0 uses the native 512×512/tiled LFM2 processor, unlike LFM3. The stored screen resize alone does not determine its image-token count.'],
 ['STATUS cost estimates, launch timestamps, review tallies; Qwen rows','Historical/operational claims are not established by these result artifacts; not certified here. User-reported $13.40 spend and $26 target are not independently metered. Qwen evaluation is outside this model scope.']]),
"""
Related protocol corrections: `EVAL_PROTOCOL.md`/`DATASETS_AND_SPLITS.md` imply 8,444 low rows (16 hints are absent; one episode has no low rows), and the blanket “FT enable_thinking=True” rule does not describe 450M's inline-intent configuration. `DATASETS_AND_SPLITS.md` still says no public answer data, contradicted by the already-corrected ScreenQA plan. “Compute-matched” should specify the matched image budget and measured total prompt cost. Historical M5/platform and license descriptions were not independently certified by re-scoring.

**What is supported and the three highest-value next steps.**

Supported: action-format adaptation and large teacher-forced AC gains; disjoint official episode splits at the audited revision; decreasing validation loss; the specific paired forced-choice results; the observed Mac-run successes/failures. Weak: a closed-loop LFM3 gain (two discordant wins), generalization from partial task prefixes, and transfer from BF16 offline scoring to Q4 online execution. Unsupported: phone readiness, a general “no forgetting” guarantee, 450M closed-loop improvement without its base run, full-suite GUI-Owl native success, or attributing gains to replay/data diversity without ablations.

1. **Repair the runtime interface first:** deterministic installed-app/alias resolution, explicit execution-error feedback, unchanged-screen/repetition recovery and calibrated completion checks. Preserve screenshot-only policy observations. The concrete `files`/`File Manager`, Clock/`Stopwatch`, `Markor`/`Marker` failures are actionable before more training.
2. **Train the missing behavior:** recovery after mistakes, answer actions, negative/ambiguous completion examples and model-generated histories. Use the proposed diverse-data round against an equal-budget AC-only control, with non-AW tasks and documented replay provenance.
3. **Freeze and validate the shipping path:** weight/GGUF hashes, actual inference config and task parameters (including timestamps); finish matched 116-task base/FT evaluations; compare BF16 and Q4 on identical screenshots; then measure physical-phone end-to-end success, p50/p95 latency, peak memory and sustained thermal behavior. Neither Mac timing nor offline SR substitutes for this.

**Exact commands and evidence.** Commands ran from `/Users/alpha/lfm3-android`. Caches were redirected below the permitted output tree; existing Hub credentials were read via their token path and never copied into the report. The initial unconfigured `uvx` attempt was denied an external cache write; attempts with an isolated HF_HOME but no token path received 401. The following card downloads succeeded (and match the pinned READMEs byte-for-byte):

```sh
HF_TOKEN_PATH=/Users/alpha/.cache/huggingface/token UV_TOOL_DIR=$PWD/results/codex/final_cache/uv-tools UV_CACHE_DIR=$PWD/results/codex/final_cache/uv HF_HOME=$PWD/results/codex/final_cache/hf PYTHONDONTWRITEBYTECODE=1 uvx --from huggingface_hub hf download experimentalmachines/LFM3-VL-2B-AndroidControl README.md --local-dir results/codex/final_cards/LFM3-VL-2B-AndroidControl
HF_TOKEN_PATH=/Users/alpha/.cache/huggingface/token UV_TOOL_DIR=$PWD/results/codex/final_cache/uv-tools UV_CACHE_DIR=$PWD/results/codex/final_cache/uv HF_HOME=$PWD/results/codex/final_cache/hf PYTHONDONTWRITEBYTECODE=1 uvx --from huggingface_hub hf download experimentalmachines/LFM2.5-VL-450M-AndroidControl README.md --local-dir results/codex/final_cards/LFM2.5-VL-450M-AndroidControl
python3 -B results/codex/final_snapshot.py
HF_TOKEN_PATH=/Users/alpha/.cache/huggingface/token HF_HOME=$PWD/results/codex/final_cache/hf python3 -B results/codex/final_fetch.py > results/codex/final_fetch.log 2>&1
python3 -B results/codex/final_score_ac.py > results/codex/final_score_ac.log 2>&1
.venv-aw/bin/python -B results/codex/final_extract_aw.py > results/codex/final_extract_aw.log 2>&1
python3 -B results/codex/final_statistics.py > results/codex/final_statistics_retry.log 2>&1
HF_TOKEN_PATH=/Users/alpha/.cache/huggingface/token HF_HOME=$PWD/results/codex/final_cache/hf UV_CACHE_DIR=$PWD/results/codex/final_cache/uv UV_PYTHON_DOWNLOADS=never PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with pyarrow --with huggingface-hub --with fsspec python -B results/codex/final_data_audit.py > results/codex/final_data_audit.log 2>&1
curl --fail --silent --show-error --max-time 30 https://storage.googleapis.com/gresearch/android_control/splits.json -o results/codex/final_official_splits.json
HF_TOKEN_PATH=/Users/alpha/.cache/huggingface/token HF_HOME=$PWD/results/codex/final_cache/hf UV_CACHE_DIR=$PWD/results/codex/final_cache/uv UV_PYTHON_DOWNLOADS=never PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with pyarrow --with huggingface-hub --with fsspec python -B results/codex/final_mirror_audit.py > results/codex/final_mirror_audit.log 2>&1
python3 -B results/codex/final_write_report.py
python3 -B results/codex/final_validate.py
```

Hub acquisition used `HfApi.model_info(..., files_metadata=True)` inventories; `final_fetch.py` downloads with `hf_hub_download(repo, path, revision=sha, local_dir=...)`. Parquet audits read only metadata/action columns via `HfFileSystem` and PyArrow. `final_extract_aw.py` records SHA-256 of each original gzip pickle and retains the raw model-content sequences without images. The initial statistics pass stopped on exception records lacking `seed`; the corrected pass uses explicit missing seed values and exact-instance pairing. No episode was discarded from success denominators for that omission.

All expanded scorer commands, exit statuses and logs are in [final_ac/commands.json](final_ac/commands.json); exact shell invocations are in [final_ac/executed_scorers.sh](final_ac/executed_scorers.sh). Primary machine-readable evidence: [AC audit](final_ac/audit.json), [AW statistics and failure traces](final_aw_statistics.json), [paired retention](final_general_statistics.json), [training audit](final_training_audit.json), [dataset audit](final_data_audit.json), [source-mirror check](final_mirror_audit.json), [input cutoff/hashes](final_snapshot_manifest.json), and [Hub download receipt](final_download_receipt.json). Snapshot copies of all original reporting documents are in `final_inputs/`; downloaded cards are in `final_cards/`. [Final verification](final_verification.json) checks input/download hashes, all 294 extracted episode files, scorer exit codes and report links; all original snapshotted source files remained unchanged.
"""]

cmds=read('final_ac/commands.json')
(OUT/'final_ac/executed_scorers.sh').write_text('#!/bin/sh\n# Documentary record: includes intentionally rejected legacy scoring.\n'+
    '\n'.join(shlex.join(x['argv'])+f"  # observed exit {x['exit_code']}" for x in cmds)+'\n')
report='\n\n'.join(parts).strip()+'\n'
(OUT/'codex_final_eval.md').write_text(report)
print('Wrote',OUT/'codex_final_eval.md',len(report.split()),'words')
