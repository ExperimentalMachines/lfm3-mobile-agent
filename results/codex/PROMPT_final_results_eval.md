You are the INDEPENDENT FINAL EVALUATOR for /Users/alpha/lfm3-android (gpt-6-astra, max effort). Trust nothing; recompute.

Scope: LFM3-VL-2B and LFM2.5-VL-450M fine-tuned as screenshot-only Android agents (+ bases, + GUI-Owl-1.5-2B reference).
Read: STATUS.md, results/SUMMARY.md, docs/EVAL_PROTOCOL.md, docs/DATASETS_AND_SPLITS.md, docs/GUI_OWL_LESSONS.md,
docs/DATA_V2_PLAN.md, the model cards (download README.md of experimentalmachines/LFM3-VL-2B-AndroidControl and
experimentalmachines/LFM2.5-VL-450M-AndroidControl with `uvx --from huggingface_hub hf download <repo> README.md --local-dir results/codex/final_cards/<name>`).

Tasks
1. AndroidControl: for each predictions file available on the Hub eval/ folders of those two repos
   (*_ft.jsonl, *_base.jsonl, *_ft_nothink_high.jsonl, with .manifest.json), download to results/codex/final_preds/ and
   re-score with YOUR independent scorer results/codex/score_independent.py (and, separately, with eval/androidcontrol/score.py
   against data/meta/androidcontrol_test_gt.jsonl). Report both side by side; explain any differences (parser strictness).
   Verify manifests: model identity, config_hash per row, completeness vs the frozen GT (18,415 rows; high-only = 9,987 incl. terminals).
2. AndroidWorld: recompute success from the raw episode files (results/androidworld/<run>/run_*/*.pkl.gz — gzip pickles written
   locally by android_world, trusted) for lfm3vl2b_base_nothink, lfm3vl2b_ft, lfm25vl450m_ft, lfm25vl450m_base (if present),
   guiowl15_2b_matched (may be partial — report n), guiowl15_2b_native_sample. Use 116 as denominator (missing/exceptions = fail).
   Give 95% CIs (Wilson) and a paired comparison base vs FT on the same task instances (McNemar). Categorize failure modes of the
   FT models from model_content sequences (e.g. wrong open_app name, wait loops, repeated clicks, premature status, no termination).
3. General knowledge retention: recompute from results/general/*_general_logprob.jsonl (paired, McNemar, bootstrap CI) and explain
   why the generation-mode numbers (results/general/*_general.jsonl) are not used for the claim.
4. Training evidence: inspect results/training/** (loss curves, run_config provenance, train_summary). Any sign of overfit/leakage?
5. Check every number in results/SUMMARY.md, STATUS.md and the two model cards against your recomputation; list mismatches.
6. Verdict: what is solidly supported, what is weak, what is not supported; and the 3 highest-value next steps for on-phone use.

Rules: do not modify existing files; write new files only under results/codex/. Final report: results/codex/codex_final_eval.md
(tables + exact commands used). Keep it factual and concise.

Notes for this pass (2026-11-17 ~04:50): the AndroidWorld runs lfm3vl2b_ft (~50/116), lfm25vl450m_ft (~65/116) and
guiowl15_2b_matched (60/116, paused) are STILL RUNNING/PARTIAL — use the newest run_* dir, report n and the 116-denominator
lower bound, and do not wait for them. lfm25vl450m_base has not started yet (skip). Also audit
eval/androidworld/failure_modes.py and its outputs results/androidworld/*.failure_modes.json (are the labels sound?).
Modal spend so far: $13.40 metered (budget target $26). Network is available for Hub downloads.
