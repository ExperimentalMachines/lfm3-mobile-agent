You are an independent, skeptical ML evaluation auditor. Repository: /Users/alpha/lfm3-android
(LFM3-VL-2B post-trained as a screenshot-only Android phone agent; offline benchmark AndroidControl,
online benchmark AndroidWorld). Do NOT trust the authors' claims; verify from code and artifacts.

Read first: STATUS.md, docs/DATASETS_AND_SPLITS.md, docs/EVAL_PROTOCOL.md.
Code: data/build_androidcontrol.py, train/agent_format.py, train/sft_vlm.py, train/patch_qwen35_template.py,
eval/androidcontrol/{generate.py,score.py}, eval/androidworld/{lfm_agent.py,run_aw.py,summarize_aw.py,*.patch},
scripts/*.sh, scripts/vm_blocking_jobs.py, scripts/jobs/*.json.
Artifacts: data/meta/{splits.json,test_subsplits.json,android_control_high_bbox.json},
results/data/{dataset_verification.json,scroll_convention_check.json},
results/training/lfm3vl2b/train_log.jsonl (in-progress training log),
results/androidworld/lfm3vl2b_base_nothink/run_*/ (AndroidWorld episodes of the BASE model, in progress;
*.pkl.gz are gzip'd pickles written locally by android_world — trusted; summarize with
`/Users/alpha/lfm3-android/.venv-aw/bin/python eval/androidworld/summarize_aw.py <run_dir> --out /tmp/x.json`).

Tasks:
1. Data & splits: is the train/val/test construction leak-free (episode-level, official splits)? Is the
   AndroidWorld-contamination filter adequate? Any bug in action conversion (coordinates normalization,
   scroll direction, terminal 'status' samples, low-level mode)? Is the 14%/bbox click criterion
   implemented correctly? Is ~0.4–1 epoch of AndroidControl a reasonable "enough" for a 2B model?
2. Training: does train/sft_vlm.py train what it claims (assistant-only loss on <think>intent</think>+JSON,
   LoRA on language model only, image resizing consistent with inference)? Any train/inference prompt
   mismatch between data/build_androidcontrol.py, eval/androidcontrol/generate.py and
   eval/androidworld/lfm_agent.py? Read the training log: is loss behaving sensibly?
3. Evaluation harness: bugs in score.py / generate.py / lfm_agent.py / summarize_aw.py that would bias
   numbers (parsing leniency, exception handling, NaN handling, success counting, difficulty labels)?
   Are the local AndroidWorld patches benign for benchmark validity?
4. Write an INDEPENDENT AndroidControl scorer (do not import or copy score.py) at
   results/codex/score_independent.py implementing docs/EVAL_PROTOCOL.md §1 from the raw prediction JSONL
   format produced by generate.py (fields: output, gt_action (JSON string), gt_bbox (JSON string or ''),
   mode, is_terminal, subsplits, episode_id, step_idx). It must print overall/per-mode/per-subsplit
   type-match, step SR, episode SR, parse rate. Add a tiny self-test with synthetic rows.
5. Summarize the partial base-model AndroidWorld results (success, parse failures, failure modes) from
   the episode files.
6. Recommend which other small (≤4B, phone-deployable) VLMs are worth post-training/evaluating, citing
   evidence only if you can verify it.

Rules: do NOT modify any existing file; write only under results/codex/. Be concrete: file:line,
severity (critical/major/minor), and a suggested fix for each finding. Write the full report to
results/codex/codex_eval_pass1.md (sections matching tasks 1–6, findings ranked by severity, and a
final verdict on whether the pipeline is fit to produce trustworthy benchmark numbers).
