ADVERSARIAL AUDIT of the BUILT v4 training data and the RL pilot in /Users/alpha/lfm3-android. v4 training is
ALREADY RUNNING on it (dataset alpharomercoma/AndroidAgent-SFT-v4 @ 570febb36b3ee2ed6b11c72653a1abee62744f5d; an exact
local copy is data/v4work/build/out/). Your job: decide whether anything is bad enough to STOP training, and list
everything else. Do not modify existing files; write new files only under results/codex/v4_data_audit/ and the report
results/codex/codex_v4_data_audit.md (first line: STOP or CONTINUE, then ranked findings with evidence paths).
Prior audits: results/codex/codex_v4_pipeline_audit.md (fixes since: data/v4_answer_check.py, data/vm_v4_teacher2.py,
guard v2 + dev changes in data/v4_build_parquet.py) — check that each P1 is actually closed in the built artifact.

1. LABEL QUALITY (most important): sample >= 60 navigate-then-answer final rows (episode_id ending "#qa", gt answer)
   stratified by kind (question vs compound) and answer type (number, price, date/time, name, phrase). Extract each
   screenshot (images column) to PNG under results/codex/v4_data_audit/samples/ and LOOK at it (use your image viewing
   tool). For each: is the answer actually visible and correct for the goal's question? is the question answerable from
   the screen and not leaking the answer? does the goal make sense with the navigation history in the prompt? Report
   the error rate with a 95% CI. Do the same for 30 shortened ScreenQA answers (data/v4work/screenqa_rows.json gives the
   originals) and 20 dev_answer rows.
2. Leakage/contamination: dev_answer/dev_complete screens vs train (img_sha), AndroidWorld app/task exposure in the QA
   copies (guard v2), any AndroidWorld template phrasing in goals.
3. Prompt/format: v4 system prompt + "Installed apps" line on every train/dev row, one stable app list per episode,
   answer JSON validity, reasoning strings, duplication weights (final answer rows duplicated x4 question / x2 compound).
4. RL pilot: train/rl_reward.py (run its fixtures; try to break it), train/grpo_vlm.py (TRL 1.16 GRPO usage for LFM3-VL:
   prompt/image columns, enable_thinking, LoRA over merged v4 so the KL reference is v4, beta, lr 1e-5, bs/ga/gens),
   data/v4_rl_pool.py and the pushed pool alpharomercoma/AndroidAgent-RL-v4 @ 586c241b8b454a89f1803cf523d18d514cd34b08,
   scripts/vm_rl_go.sh (budgeting, evals). Flag anything that would make the RL result invalid or wasted.
Be concise and evidence-based.
