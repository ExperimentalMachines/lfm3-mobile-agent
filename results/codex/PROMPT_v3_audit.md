ADVERSARIAL INDEPENDENT AUDIT of the LFM3-VL-2B v3 results in /Users/alpha/lfm3-android. Reproduce, do not trust.

Claims to verify by recomputing from RAW files (AndroidWorld episode pickles under results/androidworld/<run>/run_*/*.pkl.gz
are written by our own local runs; prediction jsonl + frozen GT for offline evals). Write your OWN code under
results/codex/v3_audit/ (new files only). Do not modify any existing file. Do not upload anything anywhere.

C1 AndroidWorld seed 30, 116 tasks, full successes (is_successful >= 1, exceptions = failure): v1 lfm3vl2b_ft 15,
   v2 lfm3vl2b_v2 3, v2+force_think lfm3vl2b_v2_forcethink 6, v3 lfm3vl2b_v3 13 (+1 half-credit, AW mean 13.5),
   GUI-Owl matched guiowl15_2b_matched 23. Check all 116 episodes exist per run and task instances (goal/seed) match
   across runs; report mismatched instances.
C2 Paired exact McNemar (results/androidworld/paired_*.json): v1 vs v3 v1-only 6 / v3-only 4 p=0.75; v2 vs v3 v3-only 10 /
   v2-only 0 p=0.002; v3 vs GUI-Owl GUI-Owl-only 18 / v3-only 8 p=0.076; v1 vs v2+force_think 9/0 p=0.004.
C3 Failure modes for v3: 0 answer actions, 38 complete_but_failed, open_app "Marker"/"Markers" used instead of Markor.
C4 AndroidWorld only credits success when the agent ended the episode (android_world/android_world/suite_utils.py) and
   GUI-Owl ended 24 episodes itself (13 terminate, 11 answer; 23 correct). Check eval/androidworld/summarize_aw.py's
   recent fix (git show bebf929) is correct and did not change our own models' summaries.
C5 The research report reports/Beating GUI Owl at 2B fairly.md says the matched GUI-Owl lead is answer tasks: 25 of 116
   tasks are scored on the answer text, GUI-Owl solved 10 of them, LFM3 v1 0; on the other 91 v1 15 vs GUI-Owl 13.
   Determine answer-scored tasks from android_world's task/checker code yourself.
C6 Offline v3 numbers (results/androidcontrol/lfm3vl2b-v3mix-lora_ft.metrics.json, results/v3_dev/*.metrics.json):
   AC high .723, low .902, terminal .725; Odyssey .662, AMEX .741, ScreenQA .724. Re-score from the prediction jsonl with
   the repo's scorer (eval/*/score.py or equivalent) and check against the frozen GT; general knowledge v3 vs base
   (results/general/lfm3vl2b_v3_retention_logprob.json: MMStar 55.3% +3.2pp p=0.002, MMLU 50.0% +1.1pp p=0.38).
C7 Model card text: scripts/publish_v3_hf.py --preview output must match the verified numbers; flag any misleading claim
   (e.g. comparability to GUI-Owl's published 67.9, "no AndroidWorld data in training" — check data/build_v2_mix.py and
   the v3 data pipeline for any AndroidWorld-derived source).
C8 Statistical framing: is "v3 not detectably different from v1" and "GUI-Owl lead not significant at 0.05" correctly
   stated; what minimum detectable difference does n=116 paired give here.

Write results/codex/codex_v3_audit.md: a table claim | verified / not verified / wrong | your number | evidence path,
then a short list of defects ranked by severity, then a GO / NO-GO on the published v3 card. Be concise.
