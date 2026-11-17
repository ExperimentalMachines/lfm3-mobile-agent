ADVERSARIAL PRE-TRAINING AUDIT of the v4 pipeline in /Users/alpha/lfm3-android (code committed at HEAD). Find bugs that
would waste tonight's GPU run or invalidate the comparison. Reproduce by running code locally (no GPU, no uploads).
Do not modify existing files; write new files only under results/codex/v4_pipeline_audit/ and the report
results/codex/codex_v4_pipeline_audit.md (ranked defects: severity, file:line, failing input, fix; then MUST-FIX list).

Scope (read docs/PREREG_v4.md and reports/Beating GUI Owl at 2B fairly.md for intent):
1. data/v4_select.py: candidate rules, AndroidWorld-app guard (is it leaky? too broad?), history-coverage check, dev split
   screen-disjointness (img_sha), determinism. Inputs: data/v4work/v3_train_meta.parquet, data/v4work/v4_candidates.json.
2. data/vm_v4_teacher.py (runs on Colab GPU later): prompt quality, JSON parsing, rejection rules, agree() logic
   (false accepts/false rejects, numbers, currency, case), ScreenQA shortening acceptance rule, row/image alignment
   (img_sha assert), incremental saving, smoke mode (--limit).
3. data/v4_build_parquet.py: every transformation and assertion; train/dev leakage; qa copies (goal rewrite, final-row
   answer, intents of prefix rows), episode rows spanning shards, ScreenQA replacement, dev_answer/dev_complete
   construction, schema/metadata preservation, README configs. A dry run on 1 shard with FAKE labels exists in
   data/v4work/smoke/out (labels data/v4work/FAKE_labels.json) — inspect it; you may re-run with --shards 1 --dry_run
   into a new --work directory under results/codex/v4_pipeline_audit/.
4. Prompt parity training vs inference: train/agent_format.py (SYSTEM_PROMPT_V4, user_text apps line, v4_app_list,
   to_v4_messages, apps_in_text), eval/androidcontrol/generate.py (--prompt_v4_pool, v4_msgs), eval/androidworld/lfm_agent.py
   (prompt_version v4, device app list from app_resolver.device_app_names) and eval/androidworld/app_resolver.py. Check
   that the exact strings the model sees at AndroidWorld time match the training format (whitespace, ordering, list
   style), and judge the train/test shift between training app lists (12-30 names from the training pool) and the
   AndroidWorld device list (30 names).
5. Fairness of the mirrored GUI-Owl input (eval/androidworld/guiowl_agent.py --installed_apps) and the sealed runner
   scripts/local_sealed_aw.sh (can outcomes leak? are arms run identically?), scripts/local_v4_to_aw.sh, scripts/v4_gate.py
   (does the gate match docs/PREREG_v4.md?), scripts/vm_model_pipeline.sh PROMPT_ARGS changes.
Be concise; prioritise defects that change results.
