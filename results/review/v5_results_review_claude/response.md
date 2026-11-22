# Response to the independent round-5 results review

All 12 findings checked; all accepted. No gate decision changes.

| ID | Action |
|---|---|
| F1 | Research report row rewritten: 0.738 → 0.785 offline, online stopping not measurably changed (26 vs 25 on tasks neither crashed); the offline gate measured final steps only |
| F2 | P2 wording fixed in `results.md`, `models.md`, the dpo2 card and the research report ("stopping not measurably changed; why not determined"; mechanism labelled inference; DPO margin 0.047 noted). PREREG correction appended (01:55 entry). Re-checked S the same way: its higher stop rate **is** significant (+25/−11 vs E, p 0.03), so the S wording stays, with the paired p added |
| F3 | The three model-repo READMEs were uploaded at 01:37 (after the results, before this review) and are re-uploaded with the fixes; uploads now logged in `logs/publish_v43_cards.log` |
| F4 | `analysis/aw_false_complete.py` rewritten to the taxonomy's rules; it now matches `failure_taxonomy_20261122.json` for all nine dev runs (v1 27, v2 20, v3 21, v4 25, v4+guards 28, v4.1 24, v4.1+guards 26, v4.2 25, v4.2+guards 25) and gives unchanged round-5 counts (22, 28, 37) |
| F5 | PREREG correction; one sentence in `results.md` |
| F6 | Exceptions column and run-conditions note in `results.md`; `aw_paired_flips.py` prints the crash-excluded view (replicate 0, P2 +2 p 0.75, S +5 p 0.27) |
| F7 | All four band mentions qualified ("nine runs before round 5; v4.3-sft later made 37") |
| F8 | "Not determined" wording |
| F9 | Table of plan-vs-registered gate changes added to "Round 5 as executed". Note: under the plan's max(R, 10) the floor would have been 10, not 9; no candidate reached either |
| F10 | PREREG correction entry lists the commit hashes and times; S's offline-gate pass (21:56, before its 22:12 pass) recorded |
| F11 | v4.2's `training_logs/log_history.json` (from its public repo) committed under `results/v42_dev/training_logs/` and cited (eval loss 0.3404 at step 1,250) |
| F12 | Projector hash check moved before the mode switch, so it runs in every mode |
