# Overfitting and the offline–online gap for GUI/mobile agents trained on static datasets

Research date: 2026-11-21. Labels: **[M]** = measured result reported by the source; **[C]** = claim, interpretation or opinion by the source's authors; "Inferences" sections are mine. Sources are dated by arXiv ID / first version. Items already covered in `docs/research/beating-gui-owl-at-2b-fairly.md` and its notes are only cross-referenced, not repeated.

How the three senses of "overfitting" map onto the evidence below:

| Sense | What would show it | Where the evidence is |
|---|---|---|
| (a) Memorising training rows | train loss ≪ held-out loss; better closed-loop on train episodes than test episodes; IDD ≫ OOD on AC test splits | Q5 (diagnostics), Q1 (AC IDD/OOD gap) |
| (b) Fitting dataset conventions that don't transfer | offline gains without online gains; behaviours that mirror annotation artifacts (e.g. `wait` + copied instruction) | Q1, Q2, Q3 |
| (c) Overfitting evaluation choices | repeated selection on one seed/benchmark; checker bugs; same-org benchmark/model | Q4 |

## Q1. Does offline step accuracy (AndroidControl, GUI-Odyssey, AITW, AMEX) predict online success (AndroidWorld, MobileWorld)?

### Takeaway
Across published models and checkpoints, offline step accuracy is at best a weak-to-moderate predictor of online success: AndroidControl-High explains about half the variance in AndroidWorld (R² = 0.47) and GUI-Odyssey less (R² = 0.40), and within a fixed SFT recipe AndroidControl can stay flat while AndroidWorld more than doubles. The gap is structural (teacher-forced history, single demonstrated action per step, no recovery states), so our "Odyssey/AMEX up, AndroidWorld flat" result is the expected pattern, not an anomaly.

### Cited Findings

**Quantitative correlation analyses**

| Study | Offline metric | Online metric | Reported association |
|---|---|---|---|
| UI-S1 (Tongyi/ZJU, Sep 2025) | AC-High step SR | AndroidWorld | **R² = 0.470** |
| UI-S1 | GUI-Odyssey step SR | AndroidWorld | **R² = 0.398** |
| UI-S1 | SOP (semi-online, model's own history kept) | AndroidWorld | **R² = 0.934** |
| GUI-Libra (UIUC/Microsoft, Feb 2026) | AC-v2 offline score, all RL checkpoints, 3B+7B | AndroidWorld | Pearson **r = 0.76** overall |
| GUI-Libra, KL > 0 checkpoints only | same | same | Pearson 0.89 (p < 1e-4), Spearman 0.83 (p = 2e-4) |
| GUI-Libra, KL = 0 checkpoints only | same | same | Pearson 0.63 (p = 0.015), Spearman 0.53 (p = 0.053, n.s.) |

- [M] UI-S1 fits offline vs online scores across a set of models (Figure 2/10): AC-High R² = 0.470, GUI-Odyssey R² = 0.398, its semi-online SOP R² = 0.934; SOP keeps the model's own outputs in the history and patches divergences from the expert trajectory — [UI-S1, arXiv 2509.11543](https://arxiv.org/abs/2509.11543). [C] Authors: SOP "fills a critical gap between fast but unrealistic offline evaluation and accurate but expensive online testing." Note SOP is the authors' own metric, and the number of models in the regression is not given in the passages read.
- [M] In the same paper, offline-strong models can be online-weak: AgentCPM-GUI-8B scores 16.4 on AW (vs UI-TARS-7B 33.0); [C] the authors say offline-RL models like AgentCPM-GUI "excel at single-turn tasks but struggle with multi-turn execution." Their own Qwen2.5-VL-7B: base 14.9 → SFT 21.7 → offline RL 15.7 → semi-online RL 30.4 → UI-S1 34.0 AW — [UI-S1, arXiv 2509.11543](https://arxiv.org/abs/2509.11543).
- [M] GUI-Libra plots offline vs online scores of all intermediate RL checkpoints (3B and 7B): overall Pearson r = 0.76; with KL regularisation 0.89 / Spearman 0.83; without KL 0.63 / Spearman 0.53 (p = 0.053). Training rewards overlap across KL settings while no-KL evaluation degrades, which they call reward hacking with entropy collapse — [GUI-Libra, arXiv 2602.22190](https://arxiv.org/abs/2602.22190). (The KL result was partly noted in `training_tunables.md`.)
- [M] **Within one SFT recipe, AC-High is flat while AW moves (Qwen2.5-VL-3B, GUI-Libra Table 9):** AC-v2 High Pass@1 SFT 45.7 → SFT+mixed 45.5 → ASFT 44.5, while AW 5.2 → 11.3 → 13.0. Removing CoT from training costs AC-High ~4 points (44.5 → 40.2) but AW 13.0 → 5.2; [C] "the declines are substantially larger than those observed on offline benchmarks" — [GUI-Libra, arXiv 2602.22190](https://arxiv.org/abs/2602.22190).
- [C] GUI-Libra's theorem bounds online failure as 1 − J(π) ≤ H · C(π) · (1 − M_off(π) − η̄_π): offline matching M_off fails to predict online success when the occupancy mismatch C(π) is large (compounding errors push the agent to states absent from the dataset) or when off-demonstration valid actions η̄ vary ("partial verifiability") — [GUI-Libra, arXiv 2602.22190](https://arxiv.org/abs/2602.22190).

**Mechanism evidence: teacher-forced history overstates closed-loop ability**
- [M] Non-GUI but closest analogue to our 0.728 teacher-forced AC number: on customer-support workflows, SFT raised gold-history all-turn success from 28.5% to 47.7% (mean of Qwen3-4B/14B, Gemma3-4B/12B), but closed-loop tool-workflow completion stayed at 0/77 for both Gemma models and reached only 3/77 and 8/77 (max 10.4%) for Qwen3; a holistic judge found 0/77 successes for every model — [When Better Turns Do Not Make Better Agents, arXiv 2609.21187 (Sep 2026)](https://arxiv.org/abs/2609.21187). [C] "gold-history evaluation restores the correct state before each decision."
- [M] AndroidControl's own "weakest link" arithmetic: assuming i.i.d. step success, completing a 5-step task 95% of the time needs ~99% step accuracy — [AndroidControl, arXiv 2406.03679 (Jun 2024)](https://arxiv.org/abs/2406.03679).
- [M] AndroidControl's IDD–OOD gap **grows** with more fine-tuning data (PaLM-2S LoRA, high-level instructions): LT-1k IDD 53.2 vs OOD 48.1–49.3 (−3.9 to −5.1 pp); LT-all r64 IDD 70.8 vs OOD 57.4–59.6 (−11.2 to −13.4 pp). [C] Extrapolations: 95% OOD step accuracy needs ~10M (low-level) / 60M (high-level) episodes; 95% episode completion on 5-step HL tasks ~150M; "fine-tuning may not scale well out of domain" — [AndroidControl, arXiv 2406.03679](https://arxiv.org/abs/2406.03679).
- [M] Same-benchmark static vs end-to-end gap: Step-GUI-8B scores 89.91% on AndroidDaily static actions vs 52.50% on its 235 end-to-end tasks (different task sets, so only indicative) — [Step-GUI, arXiv 2512.15431 (Dec 2025)](https://arxiv.org/abs/2512.15431).
- [M] AppVLM reports the highest AndroidControl offline accuracy among its baselines, yet only "matches GPT-4o" on AndroidWorld, and needed extra training iterations on AW-collected data to get there — [AppVLM, arXiv 2502.06395 (Feb 2025)](https://arxiv.org/abs/2502.06395).
- [M] Offline scores also swing with the metric itself: on the AC Hard subset, switching from point-matching to bounding-box matching alone raised SR by +6.9 to +11.5 pp across five models, and correcting tasks added +3.1 to +6.2 pp — [AndroidControl-Curated, arXiv 2510.18488 (Oct 2025)](https://arxiv.org/abs/2510.18488).
- [M] Offline can be made more faithful: a multi-path offline benchmark reports 94.72% agreement with human evaluators — [MobiBench, arXiv 2512.12634 (Dec 2025)](https://arxiv.org/abs/2512.12634). Recovery ability "only partially correlates with clean-start success" on AW checkpoints — [AndroidFlux, arXiv 2610.34384 (Oct 2026)](https://arxiv.org/abs/2610.34384).
- [M] Our own controlled case (from the main research doc): v3 raised GUI-Odyssey .269 → .662 and AMEX .306 → .741 with no AW change (paired 2 vs 2 discordant tasks, p = 1.0) — [beating-gui-owl-at-2b-fairly.md](../../beating-gui-owl-at-2b-fairly.md).

### Inferences
- Applying AndroidControl's i.i.d. arithmetic to our 0.728 teacher-forced step accuracy predicts ≈20% success at 5 steps, ≈4% at 10, ≈1% at AW's mean ~14.3 steps, and ≈0% at MobileWorld's mean 27.8 steps (step means from [MobileWorld, arXiv 2512.19432](https://arxiv.org/abs/2512.19432)). We observe 15.5% on AW, so step errors are neither i.i.d. nor all fatal (alternative paths, easy tasks). The offline number is therefore not a calibrated predictor in *either* direction, which is consistent with the R² ≈ 0.4–0.5 above.
- The pattern "offline up, online flat" is exactly sense (b): the extra GUI-Odyssey/AMEX rows taught the model to match those datasets' labels under gold history, which is what offline metrics reward, without changing what happens once its own history diverges.
- The cheapest better proxy available to us is a UI-S1-style SOP run on the AC test split (model's own history, patched on mismatch). If SOP tracks our AW deltas across v1–v4 while AC step accuracy does not, that confirms sense (b) for our checkpoints.

### Gaps
- No paper reports a rank correlation between AMEX offline accuracy and AW/MobileWorld; GUI-Odyssey has only UI-S1's R² = 0.398.
- No published correlation for MobileWorld vs any offline benchmark.
- UI-S1's regression population (which models, how many) was not visible in the passages read; GUI-Libra's correlation is within one RL recipe, not across independent SFT models.
- No ≤4B, LoRA-SFT-only correlation study exists; all quantitative analyses are 3B–8B with RL in the mix.

## Q2. Known annotation artifacts and label noise in AndroidControl, GUI-Odyssey, AMEX and AITW

### Takeaway
AndroidControl's `wait`-with-recycled-instruction pattern is independently documented, and the dataset contains almost no recovery behaviour because annotators were told to avoid unnecessary actions. Estimated label-error rates are about 20% for AndroidControl (GUI-Libra) and about 28% failed episodes in sampled AITW (AitZ). Cleaning or filtering to about half the data improves offline scores by a few points; no study shows the effect on AndroidWorld in isolation.

### Cited Findings

**AndroidControl**
- [M] Collection protocol: annotators type a short low-level instruction *before* each action, "as if they were instructing someone"; they "are instructed to avoid performing actions that are unnecessary or unrelated to the task"; typos and grammar errors were deliberately left in. The action set includes `wait` ("Wait until the next observation is received") — [AndroidControl, arXiv 2406.03679](https://arxiv.org/abs/2406.03679).
- [M] **Recycled instructions on `wait`:** a 2026 grounding audit removes "within-episode duplicate step instructions, which arise when annotators recycle the previous step's instruction for a wait action", because "the recycled instruction no longer describes the visible target" (their de-duplicated subset: n = 26,832) — [Lexical Coupling in GUI Element Grounding, arXiv 2608.21794 (Aug 2026; EMNLP 2026 Findings)](https://arxiv.org/abs/2608.21794). This independently matches our measurement (4,151 `wait` rows, 94% copying the previous instruction).
- [M] **Recovery behaviour is almost absent:** typing-correction events occur only 82 times in 63 of 15,283 episodes (0.4% of episodes); the authors conclude that "behavioural friction surfaces are systematically sparse" because of the avoid-unnecessary-actions rule — [arXiv 2608.21794](https://arxiv.org/abs/2608.21794).
- [M] Corpus size used there: 83,848 actions across 8 action classes; official split 13,603 / 137 / 1,543 episodes — [arXiv 2608.21794](https://arxiv.org/abs/2608.21794).
- [M] `wait` and termination are confusable even for the dataset authors' model (PaLM-2S LoRA, one of the appendix confusion matrices): `wait` is predicted correctly 76.0% of the time, true `terminate` is predicted as `wait` 12.4% of the time; [C] "task completion … in many cases it is wrongly recognized as a pause", and terminate/navigate_back/wait are hardest from high-level instructions because they are "generally not explicit in a user instruction" — [AndroidControl, arXiv 2406.03679](https://arxiv.org/abs/2406.03679).
- [M] GUI-Libra estimates "about 20% errors in action types and/or coordinates" in AndroidControl; their cleaned AC-v2 evaluation set keeps 398 of 500 sampled steps (−20.4%) after a Qwen3-VL-32B consistency check — [GUI-Libra, arXiv 2602.22190](https://arxiv.org/abs/2602.22190).
- [M/C] AndroidControl-Curated (industry preprint, BMW ArcherMind) reports three deficiency classes: Unclear Task 24.13%, Multiple Valid Actions 8.12%, Wrong Ground Truth 37.63%, stated to "collectively affect over 70% of the AndroidControl samples". The denominator appears to be the subset their pipeline flagged (steps all expert models failed), so these are **not** dataset-wide rates — [AndroidControl-Curated, arXiv 2510.18488](https://arxiv.org/abs/2510.18488). [C] "training on larger datasets sometimes reduced model performance — the benchmark was actively teaching incorrect behaviors" (asserted, not shown in the passages read).
- [M] Released AndroidControl-Curated flags, counted by a third party: of 8,377 Curated rows, 527 task rewrites, 1,272 candidate-disagreement reviews, 86 action-text typo fixes — [arXiv 2608.21794](https://arxiv.org/abs/2608.21794).

**AITW**
- [M] AITW has "numerous mismatch cases between the observed screenshots and the instructions"; for "check the settings for the spotify app", 13 of 15 episodes never open Spotify. AITW instructions are heavily templated (webshopping), and googleapps has >2,000 episodes per instruction. AitZ manually verified 7,180 sampled episodes and kept 5,147 as successful (≈28% rejected), then one episode per instruction (2,504) — [Android in the Zoo, arXiv 2403.02713 (Mar 2024)](https://arxiv.org/abs/2403.02713).

**GUI-Odyssey, AMEX and the mixed corpora**
- [M] GUI-Libra's SFT filter (drop steps whose action Qwen3-VL-8B re-predicts in <30% of 10 samples; drop clicks whose coordinate falls outside a Qwen3-VL-32B box for the described target) keeps "approximately half" of AC + GUI-Odyssey + AMEX + AitZ + AitW + web data. On a 3B model, filtering improved AC-High by +4.5 Pass@1 and +6.3 Pass@4 — [GUI-Libra, arXiv 2602.22190](https://arxiv.org/abs/2602.22190).
- [M] Thought content per step before re-annotation: AndroidControl ≈11 tokens (its low-level instructions), AMEX 0 — [GUI-Libra Table 2, arXiv 2602.22190](https://arxiv.org/abs/2602.22190).

### Inferences
- The `wait` artifact is a textbook instance of sense (b). In training, "history ends with instruction X, current target is X again" almost always maps to `wait`. In closed loop, a model that repeats its previous intent (73% for us) recreates that history pattern, and `wait` follows (21% of steps under non-wait intents). The model is executing a learned dataset rule on states its own errors created.
- Because AndroidControl contains almost no corrections (0.4% of episodes), SFT on it cannot teach "notice no-progress and change course"; that has to come from added data (recovery rows, own-history states) or the harness.
- A targeted cleaning step is cheap and well motivated. Either drop the recycled-instruction `wait` rows, or rewrite their intent to a wait-specific one ("wait for the page to load"), so intent text no longer predicts `wait` by copying. Published evidence for the *online* effect of such cleaning is missing (see Gaps).

### Gaps
- No published per-dataset noise rate for GUI-Odyssey or AMEX alone; GUI-Libra reports only the pooled retention (~half).
- No study isolates the AndroidWorld effect of removing or relabelling AndroidControl `wait` rows; Xiaomi-GUI-0's masking claim has no number (noted in `training_tunables.md`).
- AndroidControl-Curated's denominators are ambiguous and the paper is an unreviewed industry preprint.
- No source reports the fraction of AndroidControl `wait` rows with recycled instructions; our 94% figure is our own measurement.

## Q3. Exposure bias, compounding error, history copying and looping: measured rates and mitigations

### Takeaway
Looping and repetition are common across GUI agents, including strong ones. In GraceBench, half of *successful* runs still contain a loop or deviation, and once a trajectory loops, 39–75% of its steps are loop steps. Two mechanisms are well supported. First, small models copy surface forms from their own context. Second, agents fail to link past actions to their outcomes. The best-evidenced fixes act on the context, not on instructions: abstract or relabel the failed or repeated action, ban exact repeats at decode time, and at training time add the agent's own off-trajectory states.

### Cited Findings

**Measured loop / deviation rates**
- [M] GraceBench (169 tasks, 10 mobile apps, 3,718 trajectories, 15-action budget, temperature 0): 51.24% of successful trajectories contain a deviation or loop. Loop burden rate (loop steps / decision steps, over looping trajectories; `WAIT` counted because "repeated waiting can consume the interaction budget") ranges 0.39–0.75. Selected rows (detailed / concise instructions): GUI-Owl-1.5-8B deviation rate 0.33 / 0.38, LBR 0.56 / 0.50, SR 0.17 / 0.24; UI-TARS-1.5-7B deviation 0.51 / 0.51, LBR 0.51 / 0.46 — [GraceBench, arXiv 2610.19900 (Oct 2026)](https://arxiv.org/abs/2610.19900).
- [M] Standard SFT left loop rate unchanged (30.0 → 30.4%) on AC-based robustness slices at 3B — VeriGUI, already in `training_tunables.md` ([arXiv 2604.05477](https://arxiv.org/abs/2604.05477)).
- [M] Our v2 had same-action loops in 30 AW episodes vs 5 for v1 (main research doc).

**Mechanism: copying from context**
- [M] For 6 instruction-tuned models (135M–1.7B, 4 families; text tool-calling and MBPP repair, not GUI), putting a failed call in the transcript makes repeating it *more* likely: −1.03 nats per action token; normalised repeat probability 0.06 → 0.54; greedy exact repeats 0% → 19%. 83% of the effect comes from the call's surface form, not from the failure message — [Feedback That Backfires, arXiv 2608.23651 (Aug 2026)](https://arxiv.org/abs/2608.23651).
- [M] Harness ranking by share of rollouts ending in a loop: abstract description + decoder ban 4%, abstract only 8%, verbatim + ban 12%, "do not repeat" instruction 17%, standard harness 29%, clean restart 67% (worst). [C] "the context after a failure must differ from the context before it, and the difference must not be the failed action" — [arXiv 2608.23651](https://arxiv.org/abs/2608.23651). Caveat: single author, CPU-only, small text models. Task success did not follow the same ordering.
- [M] Follow-up in games (Sokoban, Connect Four, Othello; 8 models, 135M–1.7B): corrective gain −1.38 nats/token. Along the OLMo-2-1B post-training ladder, the inversion is present in the base model and "largely removed at the DPO stage" — [Feedback That Backfires in Games, arXiv 2610.30205 (Oct 2026)](https://arxiv.org/abs/2610.30205).
- [M] Language agents keep much of history's benefit even when past actions are shuffled. Explicitly labelling each observation as the outcome of the preceding action "improves task success and reduces next-action repetition" with no new information — [When History Fails to Become Experience, arXiv 2610.02769 (Oct 2026)](https://arxiv.org/abs/2610.02769).
- [M] Computer-use agents show "inertia": they repeat fruitless actions "despite recognizing that these actions are ineffective". Temporarily resetting the context (R³) gives 17–55% lower measured inertia — [Absorbed in Inertia, arXiv 2609.37176 (Sep 2026)](https://arxiv.org/abs/2609.37176).
- [M] AitZ qualitative analysis: CogAgent "does not take historical information into account … leading to repetitive and ineffective actions". For AUTO-UI, adding a textual "previous action result" raised STOP action-matching from 60.12 to 79.17 — [AitZ, arXiv 2403.02713](https://arxiv.org/abs/2403.02713).

**Mechanism: exposure bias / off-trajectory states**
- [C] Behaviour cloning leaves "policy-induced off-trajectory states" unsupervised. [M] Mixing in successful continuations from states the plain policy reached raised three base models from the low-30% range to >50% on OSWorld-Verified — [SGCD, arXiv 2606.18890 (Jun 2026)](https://arxiv.org/abs/2606.18890).
- [M/C] Agent-tuned LLMs do well held-in but fail held-out, are "frequently stuck in the same mistake", and [C] "just memorize existing observation-action relations". Training on self-refinement trajectories improves held-out generalisation — [AgentRefine, arXiv 2501.01702 (Jan 2025)](https://arxiv.org/abs/2501.01702).
- [M] Own-history training on static trajectories (UI-S1 semi-online RL; OpenMobile error intervention) is covered in the main doc and `training_tunables.md` (AW 21.7 → 34.0 at 7B).

**Mitigations**
- [M] Inference: a mandatory Loop Breaker (switch interaction mode after repeated failures, force a strategy change on screen-state recurrence) "nearly halves wasted steps for loop-prone models" (desktop, frontier backbones) — [VLAA-GUI, arXiv 2604.21375](https://arxiv.org/abs/2604.21375).
- [M] Training (non-GUI): DPO with a looping action as negative and the next non-looping action from the same rollout as positive cut Qwen3-8B tasks containing loops from 57.3% to 6.1% on CodeGym (with history compression); Qwen3-32B success 37.7% → 44.8%. No rewards, gold answers or judges needed — [DeLoop, arXiv 2610.19376 (Oct 2026)](https://arxiv.org/abs/2610.19376).
- [M] Training (GUI): 30% synthetic no-change rows cut loop rate 30.4 → 26.5% at 3B, offline only — VeriGUI, in `training_tunables.md`.

### Inferences
- Our closed-loop signature (73% repeat of the previous intent, then `wait`) fits the surface-copying mechanism: the previous intent string sits verbatim in the history, and AndroidControl taught that a repeated instruction predicts `wait`. Two cheap, untested-on-GUI harness changes follow from the evidence. (1) Show a de-duplicated or abstracted history: replace a repeated intent with "(same as previous; screen unchanged)". (2) Ban exact re-emission of the previous intent+action pair at decode time. Both must be reported as harness variables, not model gains, and mirrored for any comparison model.
- "Do not repeat" prompt instructions are the remedy *least* supported by evidence (no effect in 2608.23651).
- DeLoop's recipe (own rollouts → loop/non-loop DPO pairs) needs no checker and could reuse our existing AW/MobileWorld failure trajectories, but only on non-AW apps under our contamination rule.

### Gaps
- No measured loop rate for a ≤4B LoRA-SFT GUI agent on AW apart from our own runs; GraceBench's smallest models are 7–8B.
- The surface-copying studies use ≤1.7B text models; no study checks whether the effect holds for VLM GUI agents with intent text in history.
- No GUI paper ablates de-duplicating repeated intents in history.

## Q4. Benchmark overfitting and contamination: AndroidWorld, MobileWorld, dev-set selection, seeds and statistics

### Takeaway
AndroidWorld's checker layer has at least one documented false-success bug. Its outcomes often cannot be verified from retained artifacts. A third of its templates do not vary with seed. MobileWorld is maintained by the same Tongyi lab whose follow-up to MAI-UI now reports 82.1% on it. Selection on a single dev seed is a known inflation source. The statistical recipe (sealed seeds, paired template-clustered tests, about 350 paired episodes for an 8-task margin) is already worked out in the earlier notes.

### Cited Findings

**AndroidWorld checker and evidence problems**
- [M] An outcome-evidence audit (41 AW tasks × GPT-5.4 and Claude Opus 4.7) found native success 61.0% but evidence-supported bounds of [15.9%, 65.9%], because 50% of records were "Unknown": released successes depend on app database, media, filesystem or content-provider state the run bundle does not keep. It found 2 benchmark conflicts — [Can Agent Benchmarks Support Their Scores?, arXiv 2605.10448 (May 2026)](https://arxiv.org/abs/2605.10448).
- [M] Concrete AW false success: in the recipe-deletion task ("delete recipes whose directions contain Parmesan"), the agent searched, opened Eggplant Parmesan and deleted nothing, yet was scored successful, because "the released target construction leaves the evaluator with an empty target set" ([recipe.py L133–180](https://github.com/google-research/android_world/blob/main/android_world/task_evals/single/recipe.py#L133-L180)) — [arXiv 2605.10448](https://arxiv.org/abs/2605.10448).
- [M] 38 of 116 AW templates produce identical instances regardless of seed, and RL gains shrink from unseen instances (+26.1) to unseen templates (+15.7) to unseen apps (+8.3) — [AW-Generalization, arXiv 2603.07432](https://arxiv.org/abs/2603.07432) (from earlier notes, not re-read).
- [C] MobileWorld's authors call AW saturated ("recent agents achieving over 90% success rates indicate its saturation") — [MobileWorld, arXiv 2512.19432 (Dec 2025)](https://arxiv.org/abs/2512.19432).

**MobileWorld provenance**
- [M] MobileWorld (Tongyi-MAI) reported 20.9% as the best end-to-end model in Dec 2025 — [arXiv 2512.19432](https://arxiv.org/abs/2512.19432). Its README (update dated 2026-07-30) reports that "Qwen-UI-Agent", "the follow-up to MAI-UI", scores 82.1% on MobileWorld. The leaderboard accepts community-submitted trajectory bundles — [MobileWorld GitHub](https://github.com/tongyi-mai/mobileworld).
- [M] MAI-UI's online-RL environment includes Mattermost, Mastodon and Mall4Uni, which are also MobileWorld apps (earlier notes, `fair_evaluation.md`).
- [M] GUI-Owl-1.5's MobileWorld scores are self-reported; MobileWorld's own harness gave GUI-Owl-7B 7.7 on GUI-only tasks (earlier notes).

**Agent-benchmark validity in general**
- [M] Agentic benchmark setup or reward flaws can under- or over-estimate performance "by up to 100% in relative terms" (e.g. TAU-bench counting empty responses as successful) — [ABC, arXiv 2507.02825 (Jul 2025)](https://arxiv.org/abs/2507.02825).
- [M] Automated red-teaming found reward-hacking exploits reaching near-perfect scores "without solving a single task" on most of 10 agent benchmarks (software engineering, web, desktop, terminal), with 219 distinct flaws. The abstract does not say whether AW was included — [BenchJack, arXiv 2605.12673 (May 2026)](https://arxiv.org/abs/2605.12673).
- [M] Of 150 audited FAIL verdicts from five web, enterprise and desktop CUA benchmarks, 15.3% were wrong (10.7% evaluator false negatives, 4.7% broken tasks) — [How Benchmarks Mis-Score Computer-Use Agents, arXiv 2607.28367 (Jul 2026)](https://arxiv.org/abs/2607.28367).
- [C] Held-out sets should differ from training as much as the intended generality. Only 1 of 8 domain-general agent benchmarks surveyed had an appropriate holdout, and without one developers "may (intentionally or unintentionally) take shortcuts that work only for the specific tasks represented" — [AI Agents That Matter, arXiv 2407.01502 (Jul 2024)](https://arxiv.org/abs/2407.01502).

**Variance and statistical practice** (already in `beating-gui-owl-at-2b-fairly.md`; summarised, not re-derived)
- Seed-to-seed spread 2–7 points; one 116-task run detects only a ~14-task gap at 80% power; best-of-5 selection on seed 30 inflates by ~3–5 tasks; pooled-seed McNemar inflates false positives (0.07–0.14) while a template-level sign-flip permutation test holds 0.04–0.06; an 8-task non-inferiority claim needs ~350 paired episodes over ≥3 sealed seeds — [beating-gui-owl-at-2b-fairly.md](../../beating-gui-owl-at-2b-fairly.md); [Statistical Precipice, arXiv 2605.08261](https://arxiv.org/abs/2605.08261).
- [M] Faithful third-party reruns of GUI-Owl-1.5-32B land at 69.3 ± 0.5 over seeds {7, 30, 1234} — [Beyond the GUI Paradigm, arXiv 2606.19388](https://arxiv.org/abs/2606.19388) (earlier notes).

### Inferences
- Wilson 95% intervals on our headline numbers (computed here): AW 18/116 = 15.5% → **[10.0%, 23.2%]**; MobileWorld 6/105 = 5.7% → **[2.6%, 11.9%]**. At these widths, differences of 2–4 tasks between our versions are not interpretable from one run.
- For (c), seed 30 should be treated as a training-adjacent dev set (≥6 LFM3 configurations scored on it). Reportable claims need sealed seeds, and results on the 78 seed-varying templates should be reported separately.
- The recipe false-success bug shows that AW success labels can be wrong in the *agent's favour*. Per-episode spot checks of claimed successes (especially recipe and other "delete matching items" tasks) belong in any parity claim. Because the bug is in the benchmark, it affects all arms equally on the same seed.
- MobileWorld is a useful held-out benchmark for *us* (no exposure), but scores of Tongyi-family models on it should be read as possibly in-environment.

### Gaps
- No public list of AW checker bugs beyond the recipe case; the 2605.10448 audit covered only 41 tasks.
- No independent audit of MobileWorld checkers or of whether Qwen-UI-Agent trained on MobileWorld apps (the README entry gives no training disclosure).
- No published run-to-run variance for MobileWorld.

## Q5. Practical diagnostics for overfitting in SFT of VLM agents

### Takeaway
At 0.43 epochs, classic memorisation (sense a) is unlikely; published SFT studies place loss overfitting and capability erosion beyond ~2 epochs. Validation loss is a sound selection signal *within* one recipe but cannot see closed-loop behaviour. The informative diagnostics are therefore the AC test sub-split gap, seen-vs-unseen training rows, SOP-style own-history replay, and behaviour probes for dataset conventions.

### Cited Findings

**Loss curves and epochs**
- [M] Controlled SFT sweep (Qwen3/Llama, 0.6B–235B, LoRA and full FT, four customer datasets; not agents): within a fixed (model, dataset, recipe) cell, validation loss ranks judged quality (standardised Spearman −0.38 to −0.88), but "does not transfer across model families". "Past about two epochs the validation loss overfits, the judged task score does not improve, and general instruction-following degrades" (e.g. Qwen3-8B full FT IFEval 0.73 at 2 epochs → 0.34 at 8). Fresh examples beat repeated passes; the 1.7B model overfits *more* than 8B; LoRA erodes like full FT. Optimal LoRA LR is ~1e-3, about 33× the full-FT optimum; rank plateaus around 64 — [Post-Training Science for SFT, arXiv 2609.01244 (Sep 2026)](https://arxiv.org/abs/2609.01244).
- [M] Verbatim memorisation during fine-tuning "increases dramatically in the first few epochs, often significantly before either validation perplexity or evaluation performance is optimised". An n-gram memorisation score reliably precedes it and works as an early-stopping signal — [Early Detection and Reduction of Memorisation, arXiv 2510.11372 (Oct 2025)](https://arxiv.org/abs/2510.11372).
- [M] Counter-evidence that memorisation is not always harmful: in long-CoT SFT, Olmo3-7B trained 128 epochs on 400 samples beat 1 epoch on 51,200 samples by 12–26 pp on AIME/GPQA; gains plateau when training token accuracy reaches full memorisation — [Data Repetition Beats Data Scaling, arXiv 2602.11149 (Feb 2026)](https://arxiv.org/abs/2602.11149).
- [M] Typical GUI SFT uses ~2 epochs (GUI-Libra, UI-Oceanus), and no ≤4B paper ablates epochs on AW (earlier notes, `training_tunables.md`).

**Signals that more data/epochs help offline but not closed-loop**
- [M] More AndroidControl data widens the IDD–OOD gap (−3.9 to −5.1 pp at 1k episodes → −11.2 to −13.4 pp at full data, HL, r64) — [AndroidControl, arXiv 2406.03679](https://arxiv.org/abs/2406.03679).
- [M] In visual navigation (V-IRL) and a card game, "SFT … tends to memorize training data and struggles to generalize out-of-distribution", while outcome-reward RL generalises; SFT is still needed to stabilise output format — [SFT Memorizes, RL Generalizes, arXiv 2501.17161 (Jan 2025)](https://arxiv.org/abs/2501.17161).
- [M] Adding 0 → 36K mock-app steps raised in-domain success 14.2 → 73.3 while AW stayed ~46% (PhoneWorld, earlier notes; [arXiv 2605.29486](https://arxiv.org/abs/2605.29486)).
- [M] Smaller, cleaner data can beat larger noisy data: GUI-Libra keeps ~half its corpus and gains +4.5 AC-High Pass@1 — [arXiv 2602.22190](https://arxiv.org/abs/2602.22190).
- [M] Step-wise cross-entropy that pushes every step toward the reference "repairs errors but also breaks 8–13% of initially correct answers", and "overall accuracy metrics hide these losses" (latent-memory prefixes on a frozen 8B) — [ScopeMem, arXiv 2610.26503 (Oct 2026)](https://arxiv.org/abs/2610.26503).
- [M] Semi-online evaluation (SOP) is the best-correlated cheap proxy for AW found (R² 0.934) — [UI-S1, arXiv 2509.11543](https://arxiv.org/abs/2509.11543).

### Inferences
Concrete diagnostics for our run (0.43 epoch over 92k rows; AC val loss 0.306; AC test 0.728), ordered by cost:

| Diagnostic | Tests | Reading |
|---|---|---|
| Train loss vs AC-val loss at the same step (log both) | (a) | A gap ≲ noise at 0.43 epoch means no row-level memorisation. We currently have only the eval number. |
| Loss on *seen* vs *never-seen* training rows | (a) | At 0.43 epoch, if sampling was without replacement, ~57% of training rows were never seen, a free in-distribution holdout. A seen/unseen gap measures memorisation directly. Needs sampler logs. |
| AC test step accuracy by sub-split (IDD vs app/task/category-unseen) | (a)/(b) | AndroidControl's own LoRA models drop 11–13 pp IDD→OOD at full data. A much smaller drop for us argues against (a). |
| SOP-style replay on AC test (own history, patch on mismatch) | (b) | If SOP falls far below 0.728 and tracks AW across v1–v4, the offline number is inflated by teacher forcing. |
| Convention probes: P(`wait` \| previous intent duplicated in history), P(repeat intent \| screen unchanged), `complete` vs `answer` on question goals | (b) | Directly measures whether AndroidControl rules (recycled-instruction `wait`, always-`complete`) fire on non-AndroidControl states. |
| Closed-loop on AC/Odyssey *train* episodes' apps vs test apps | (a) vs (b) | Better closed-loop success on train-app tasks indicates memorisation; equal failure on both indicates convention or exposure problems. |
| Sealed AW seeds + MobileWorld, template-clustered paired tests | (c) | Separates real changes from dev-seed selection. |

- On current evidence, sense (b) is best supported: offline-only gains, the documented `wait` artifact reproduced in closed-loop behaviour, and near-zero recovery data. Sense (c) is a live risk for any seed-30 comparison. Sense (a) is unlikely at 0.43 epoch but untested.
- Training more epochs on the same static mix is the lever with the weakest support for closed-loop gains. Published curves suggest it will raise offline numbers and widen the in/out-of-domain gap.

### Gaps
- No GUI-agent paper reports train-vs-val loss curves alongside AW success across epochs, so the loss-to-closed-loop link for VLM agents is unmeasured.
- No ≤4B study of epochs, LoRA rank or LR against AW or MobileWorld success.
- The SFT epoch study (2609.01244) uses text-only customer tasks with low label noise, so its "~2 epochs" threshold may not transfer to noisy GUI data with ~20% label errors.
