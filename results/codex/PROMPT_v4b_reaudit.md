TARGETED ADVERSARIAL RE-AUDIT in /Users/alpha/lfm3-android. Your previous report results/codex/codex_v4_data_audit.md said STOP
for dataset alpharomercoma/AndroidAgent-SFT-v4@570febb. The data was rebuilt as @337553984ee970a767dceb21adc6343f3d613602
(exact local copy: data/v4work/build/out/; builder data/v4_build_parquet.py, checker data/v4_answer_check.py) and v4 is
being retrained on it now; the RL pool is alpharomercoma/AndroidAgent-RL-v4@9ba36d90abe9bdbaa0c578879336472ab054cc2c
(train/rl_reward.py, train/grpo_vlm.py, scripts/vm_rl_go.sh, scripts/strict_dev_metrics.py). For EACH of your previous
findings 1-9, state closed / partially closed / open with evidence from the rebuilt artifact. Re-sample 40 QA final rows
(new random seed, stratified as before) and LOOK at the screenshots: answer error rate, goal-leak rate, navigation
mismatch rate with Wilson CIs. Re-run your app-inventory census, AW-app exposure scan and real-pool reward attacks.
Do not modify existing files; write results/codex/codex_v4b_reaudit.md (first line STOP or CONTINUE) and evidence under
results/codex/v4b_reaudit/. Be concise.
