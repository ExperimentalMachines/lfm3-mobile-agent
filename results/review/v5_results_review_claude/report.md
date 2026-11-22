Verdict: GO AFTER FIXES

Independent Claude reviewer (a fresh agent; it had only the prompt `results/agy/PROMPT_v5_results_review.md`). It
stands in for agy, whose quota was exhausted on 2026-11-23 (resets ≈ 2026-11-28). The reviewer could not write files,
so this report was saved from its reply. Reviewed at `903c660`.

All four gate decisions are correct and reproduce: P fails offline, P2 and S pass offline, P2 and S fail online, and
round 5 is negative. No gate parameter changed after an outcome. What needs fixing is wording: some claims about *why*
P2 behaved as it did say more than the data shows, and some disclosures are missing or imprecise.

## Findings

| ID | Sev | file:line | What is wrong | Evidence | Exact fix |
|---|---|---|---|---|---|
| F1 | P1 | research report `:473` | Both facts given as evidence are false. P2's 0.785 is not the "best-ever" terminal `complete` (P 0.885, v1 0.792), and 28 is not the "worst" false-`complete` count (S has 37) | `results/v5_dev/lfm3_v43dpo_offline_gate.json:4`; `docs/results.md:337`; S = 37. On the 107 tasks neither P2 nor E crashed: 26 vs 25 | Replace the cell: offline 0.738 → 0.785, but online stopping did not change measurably; the offline gate measured stopping on final steps only |
| F2 | P2 | `docs/results.md:180-182`; `docs/models.md:25`; dpo2 card `:27,75`; PREREG `:307-309`; research report `:471,476-481` | "Stops more often, not more accurately", "ends with a false `complete` more often" and the mechanism given are noise-level. E's 9 crashes inflate the raw gap | Paired, neither crashed: ends with `complete` P2 vs E +10/−7 (p 0.63), vs replicate +13/−6 (p 0.17); false `complete` +9/−8 (p 1.0) and +13/−7 (p 0.26). Final DPO margin 0.047 (P 0.43). The runs were on an emulator, not "a live phone" | Reword as "stopping not measurably changed; why is not determined"; label the mechanism inference; PREREG correction appended, not edited |
| F3 | P2 | `scripts/publish/vm_publish_public.py:60`; `results/v5_dev/publish_public.log` | No record that the public model repos received the result cards; the last logged README upload (21:38) predates the online results | Publish log times vs commit times | Upload the three cards and log it, or verify the Hub READMEs |
| F4 | P3 | `analysis/aw_false_complete.py:1-3,17-23` | Claims the taxonomy definition but counts answer tasks and partial credit and skips unparseable last steps. Same counts for round 5; differs for v1–v4.1 (45 vs 27, 36 vs 20, 39 vs 21, 28 vs 24, 28 vs 26) | Taxonomy file `results/androidworld/failure_taxonomy_20261122.json` | Implement the taxonomy's rules or fix the docstring |
| F5 | P3 | PREREG `:294-296`; `docs/results.md` | "Nothing re-run" after the reboot is wrong: the in-flight task was restarted from scratch (P2 RecipeDeleteMultipleRecipesWithNoise, S CameraTakeVideo, one of S's 4 losses to E). results.md does not mention the reboot or void passes | `logs/aw_run_lfm3vl2b_v43dpo2.log:45574,46815`; `logs/aw_run_lfm3vl2b_v43sft.log:2415,2735` | Append a correction; one sentence in results.md |
| F6 | P3 | `docs/results.md:169-176` | No exceptions column; E (the reference) was not cold-booted | `logs/local_v41_dev_aw.log`. Neither crashed: replicate 0 (+4/−4), P2 +2 (p 0.75), S +5 (p 0.27) | Add the column and a note |
| F7 | P3 | research report `:472,490` (also `:19,:380`) | The 20–28 band is still called "Held" / "tight" although S has 37 | S = 37 | "Partly … S left it upwards (37)" and qualify the other mentions |
| F8 | P3 | research report `:474` | "Through more stopping, not better stopping" states a cause the log calls undetermined | PREREG "not determined"; some S wins finished far faster than E | Say "not determined" |
| F9 | P3 | research report `:455-458` | "As executed" omits that the pre-registration changed the plan's gates before training: floor max(R,10) → max(R,6), early-`status` and median-token checks dropped, pair-mix rule (≥20% wait/copy) not adopted (P: 5%) | Report `:408-410` vs PREREG `:220-229`; `results/v5_dev/v43dpo_pairs_stats.json` | Add the list |
| F10 | P3 | PREREG headings | Several heading times do not match commits or the launcher log (mostly declared earlier than labelled). The 17:35 entry was committed at 18:34, after the pair statistics were printed (settings in code since 16:18). S's offline-gate pass has no entry | `git log -- docs/PREREG_v41.md`; pipeline log `:2916` | Append one correction entry with hashes and times |
| F11 | P3 | sft card `:69`; research report `:465` | v4.2's 0.340 validation loss is not reproducible from repo files | No v4.2 `log_history.json` under `results/` | Commit v4.2's log and cite it, or drop the number |
| F12 | P3 | `scripts/publish/local_quantize_publish.sh:17-19,37-38` | `publish-only` checks the GGUF's hash but not the projector's (today's projector matches) | Script lines | Move the projector check so it runs in both modes |

## Answers (summary)

1. **Numbers:** everything reproduces except F11. Seed 30: E 18 / 9 exc / 25 FC; replicate 19 / 2 / 22 (+5/−4, R = 9);
   P2 21 / 3 / 28 (+7/−4, p 0.55); S 24 / 1 / 37 (+10/−4, p 0.18). Ends with `complete` (right, precision, at step
   limit): E 38 (13, 0.34, 53); replicate 37 (15, 0.41, 59); P2 44 (16, 0.36, 51); S 56 (19, 0.34, 37). Offline gates
   and pair counts reproduce.
2. **Gates:** applied exactly as declared; no change after an outcome. P2 declared at 19:54:13 before its training
   started (19:56:57); the S cut declared at 20:08:12 before S's restart (≈ 23 training steps logged, no eval).
3. **Definitions:** `>= 1` and `> 0` give identical counts (values are 0, 1 or NaN). False-`complete` code ≠ taxonomy (F4).
4. **Claims:** no improvement claimed; gate outcomes stated correctly. The cause claims (F1, F2, F7, F8) overreach.
5. **Disclosure:** void passes and the reboot are in the PREREG, not in results.md; the in-flight task restart (F5)
   and E's missing cold boot (F6) were not disclosed.
6. **Publishing:** published GGUF SHA-256 = manifests = evaluated files (P2 `b6b90de4…3128`, S `f17b3482…49e0`,
   projector `c5c5b58d…`). Projector not checked in `publish-only` (F12). Hub cards not verifiable offline (F3).
