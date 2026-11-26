# analysis/done_audit/

The label audits and probes of rounds 8–12 ("is the agent done?"). Run by hand; outputs are in `results/v46_dev/`,
`v47_dev/`, `v48_dev/` and `r1*_dev/`. Names in the scripts' docstrings are the labels used then
(D = `-Dev-FullMix`, E = `-Counterfactual`, v4.7 = `MobileAgent-SFT-Counterfactual-WaitFix`; see [docs/naming.md](../../docs/naming.md)).

| Script | What |
|---|---|
| `aw_compare_runs.py`, `aw_false_complete_dump.py`, `aw_waits.py`, `aw_done_check_summary.py` | AndroidWorld run comparisons: false completes (and a dump for review), wait behaviour, what the round-12 done check did |
| `extract_terminal.py`, `judge_terminal.py`, `mjb_build.py` | Round 8: the training `status` rows, a vision-judge pass over them, MobileJudgeBench as a held-out "is it done?" set |
| `build_history_probes.py`, `probes_to_disk.py`, `probe_llama.py` | History-reliance probes (round 8) and running them through a model |
| `bedrock_judge.py`, `claude_judge.py`, `claude_label_rows.py`, `claude_next_action.py` | The completion judges (Qwen3-VL-235B on Bedrock, Claude), bulk labelling, and the written next actions for unfinished final screens (rounds 10–12) |
| `contradicts_sheets.py`, `stopdpo_pair_sheets.py`, `waitfix_sheets.py`, `waitfix_sheets_round3.py` | Contact sheets for review by eye (judge verdicts, stop-DPO pairs, the WaitFix rows) |
| `goal_parts.py`, `wait_audit.py`, `wait_detail.py` | Multi-part goals in the data (round 9 / 10 design check) and the audit of the training split's `wait` steps (round 9) |
| `manual_terminal_review.json`, `contradicts_review.json`, `validation_2026-11-25.json`, `validation_waitfix_2026-11-25.json` | By-eye labels and judge validations (data) |
