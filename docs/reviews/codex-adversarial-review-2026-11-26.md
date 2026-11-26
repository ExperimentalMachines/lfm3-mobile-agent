# Adversarial review

External adversarial review requested by the owner (Codex CLI, `gpt-6.1-sol`, reasoning effort medium, read-only sandbox, no network) over a redacted transcript of the working session and the repository, 2026-11-26 14:44–14:59 Asia/Manila. Reproduced as written; local paths made relative. Verification of its main claims and the actions taken: `docs/PREREG_v411.md`, log entry 15:00.

**Yes: the project is repeatedly optimising symptoms and development probes without establishing that those improvements cause better task completion.** E’s waits fell sharply, yet AndroidWorld success stayed flat and MobileWorld remained at 5/105. Round 13 addresses a plausible weakness—conditioning on the model’s own history—but its implementation credits actions with rewards earned after human intervention, removes many long-task endings through truncation, and uses an action matcher that can treat materially wrong actions as correct. Round 12 is a reasonable bounded experiment, but neither its labels nor its replay gate justify confidence that self-checking will improve completion. The strongest next investment is measurement and reward correctness, followed by one controlled recovery-training experiment. Another symptom-specific continuation would have poor expected value.

This review used source inspection and read-only, in-memory checks. I did not rerun training or live benchmarks. Literature claims below are assessed against the repository’s research notes; the external papers were not independently reopened.

## Critical findings

### C1. Round 13 credits actions with rewards obtained after a human patch

**Evidence:** [semi_online_rl.py:235](train/semi_online_rl.py:235), [semi_online_rl.py:251](train/semi_online_rl.py:251), [semi_online_rl.py:259](train/semi_online_rl.py:259).

A wrong action is saved as a training sample. The human action then replaces it in history, and the rollout continues. Returns subsequently sum rewards across that patch boundary. Episode advantage also uses the total reward of the patched rollout.

Consequently, the wrong action receives credit for progress made possible by the human intervention.

I reproduced this using the actual rollout and reward functions with deterministic mocked generations:

- Rollout A says premature `complete`, receives a gold-action patch, then matches three actions.
- Rollout B produces two invalid actions and stops.
- The premature `complete` receives reward **0.1**, discounted return **0.975**, and advantage **approximately +2**.

The loss therefore increases its probability. This is relative reinforcement against an even worse rollout; it does not prove that every premature completion is reinforced. It does prove that the stated mechanism—early stopping forfeits subsequent reward—is not enforced.

The repository’s own UI-S1 notes specify returns ending at the **naturally matching segment**, and explicitly distinguish that from returns extending through patched trajectories: [own_mistakes_methods.md:44](docs/research/notes/training-on-own-mistakes-and-overfitting/own_mistakes_methods.md:44).

**Required correction:** represent patch boundaries explicitly and prevent pre-patch actions from receiving post-patch credit. Define terminal-action treatment deliberately. For a deployment-faithful objective, premature `complete` or `answer` must terminate that sampled attempt. If training continues after intervention, treat the continuation as a separate segment.

Until corrected, E-S can establish whether this particular surrogate helps. It cannot cleanly test the proposed credit-assignment mechanism.

### C2. Uncontrolled device carryover undermines paired benchmark interpretation

**Evidence:** [results.md:113](docs/results.md:113), [sealed_analysis.py:302](analysis/sealed_analysis.py:302).

The project already documents skipped snapshot restoration and state leaking between tasks—for example, contacts created in an earlier episode remaining in later episodes.

Matching task template and seed does not establish matching initial state. Different policies leave different residue, so subsequent tasks can differ systematically between arms. Template clustering does not repair this cross-template dependence.

This does **not** establish that the published counts are numerically wrong or that the bias favours LFM3. It establishes that the experiments have an uncontrolled source of confounding precisely where differences are only a handful of successes.

**Required correction:** establish and verify a deterministic reset contract before the next comparative run. Historical results should retain their existing carryover qualification.

## Major findings

### M1. The matcher can turn wrong actions into full rewards and fictitious successful transitions

**Evidence:** [score.py:56](eval/androidcontrol/score.py:56), [sop.py:107](eval/androidcontrol/sop.py:107), [semi_online_rl.py:202](train/semi_online_rl.py:202).

I executed the actual matching functions. All three examples returned `(True, True)`:

| Prediction | Ground truth | Why accepting it is consequential |
|---|---|---|
| Tap `[500,600]` | Tap `[500,500]`, known box `[480,480,520,520]` | Prediction is outside the element; distance fallback still accepts it |
| Type `0917 123 4568` | Type `0917 123 4567` | Wrong phone number passes token F1 |
| Answer `10.00` | Answer `10.99` | Wrong numeric answer passes token F1 |

The distance fallback applies even when a bounding box exists. Text matching removes punctuation and accepts token F1 ≥ 0.5.

Those conventions may be tolerable as permissive one-step benchmark metrics. They are much more dangerous as **transition-validity tests and RL rewards**:

1. A materially wrong action receives reward 1.
2. Its wrong action is retained in history.
3. The next screenshot shows the human’s successful transition.

The learner can thus see the correct result of an action it did not perform correctly.

**Correction:** preserve the legacy score for comparability, but introduce a stricter transition matcher. Use known element boxes when reliable; require exact or task-aware matching for numbers, identifiers, recipients, and entered text. Audit ambiguous alternatives separately.

### M2. The 12-step cap removes the endings round 13 claims to teach

**Evidence:** [semi_online_rl.py:114](train/semi_online_rl.py:114), [semi_online_rl.py:128](train/semi_online_rl.py:128), [PREREG_v411.md:66](docs/PREREG_v411.md:66).

The builder appends a judged ending, then keeps only `steps[:12]`. Long episodes consequently lose their terminal supervision or their written corrective action.

A read-only count of the committed inputs found:

- **371/619** written next actions have endpoint `step_idx ≥ 12`.
- **94/200** held-out judged-done endpoints have endpoint `step_idx ≥ 12`.

These are endpoint-pool counts, not counts from the actual 400 selected training episodes. They nevertheless demonstrate that truncation disproportionately removes the difficult endings.

A 20-step episode becomes a 12-step prefix with no completion decision. Matching that prefix can also increment `completed_rollouts`, because “completed” means reaching the truncated length: [semi_online_rl.py:265](train/semi_online_rl.py:265).

**Correction:** report endpoint retention by source and selected episode. Use complete short episodes plus explicitly labelled suffix windows for long-task endings. A suffix window with an expert prefix is a separate training condition and should be described accordingly. Never call successful prefix matching task completion.

### M3. The false-complete metric excludes some violations of the owner’s definition

**Evidence:** [sealed_analysis.py:102](analysis/sealed_analysis.py:102), [replay_done_check.py:49](eval/androidworld/replay_done_check.py:49).

False completes exclude:

- Episodes receiving any positive partial credit.
- Answer tasks.
- Exceptions.
- Terminations other than `status complete`.

A task scoring 0.5 and ending in `complete` is unfinished under “fully met, nothing more or less,” but does not enter this false-complete count.

This is a reproducible taxonomy, but it is narrower than the failure the project says it is fixing. Comparing agents by this count alone is especially misleading when agents terminate differently. GUI-Owl’s zero does not establish that it is a universally correct completion judge.

**Correction:** retain the historical metric and add all unsuccessful completion claims, including partially completed tasks. Report incorrect answers and infeasible declarations separately, alongside step-limit failures and successes.

### M4. Round 12 reuses a judge-label population that previously failed its quality gate

**Evidence:** [rounds.md:310](docs/rounds.md:310), [r12_mix.py:231](data/r12_mix.py:231), [semi_online_rl.py:103](train/semi_online_rl.py:103).

Round 10 records that judging AndroidControl’s own completion rows scored **26/32**, below the required **28/32**, and that the labels were not used.

Round 12 nevertheless:

- Trains yes/no checks from that verdict population.
- Removes judged-unfinished completion rows and corresponding variants from replay.

Round 13 also drops those completion steps.

The review materials do not establish a new source-specific validation that overturns the failed check. Calibration on AndroidControl preference pairs is not interchangeable with calibration on AndroidControl’s original completion rows.

**Concrete failure:** a valid completion incorrectly labelled unfinished becomes a negative done-check example, while its positive action supervision is removed.

**Correction:** quarantine these verdicts until their particular population passes a fresh audit. Otherwise document explicitly that a previously failed label source is being used experimentally.

### M5. Label creation and verification share substantial blind spots

**Evidence:** [rounds.md:75](docs/rounds.md:75), [next_action_review.json:2](results/r12_dev/next_action_review.json:2), [claude_next_action.py:39](analysis/done_audit/claude_next_action.py:39).

The judge is Claude. The coding assistant performing “by-eye” calibration is also Claude. The next-action writer is explicitly told that the task is unfinished and receives the judge’s explanation.

This creates correlated verification and anchoring. The absence of `DONE` responses is weak evidence because the writer was primed against that conclusion.

The 39/40 review establishes apparent plausibility under that review process. It does not establish successful execution or independent correctness. One weak action was counted correct because it was a plausible first step; another repeated a historically ineffective tap.

Round 12 also assumes certain pre-end actions imply an unfinished task: [r12_mix.py:221](data/r12_mix.py:221). A demonstrator’s last tap, app opening, or typing action can be redundant. Action type alone cannot establish that it was necessary.

**Correction:** separate “visibly unfinished,” “visibly finished,” and “cannot determine.” Use independent or executable checks on a stratified sample. Do not force ambiguous screenshots into binary truth labels.

### M6. SOP is useful, but its current validation cannot establish the proposed general gate

**Evidence:** [PREREG_v411.md:32](docs/PREREG_v411.md:32), [sop.py:95](eval/androidcontrol/sop.py:95).

There are four problems.

**First, it measures survival along an expert screenshot sequence.** It keeps model-generated histories only while the matcher accepts the actions. It does not observe states caused by a genuinely wrong transition, backtracking, or recovery. Describing this as training or evaluating on “states the policy itself visits” overstates what static replay supplies.

**Second, premature-status rate is censored by earlier errors.** A model failing immediately on a tap gets no opportunity to emit premature `status` later. Lower premature-status incidence can therefore accompany worse navigation.

Report both episode incidence and the hazard conditional on reaching each nonterminal step, stratified by depth.

**Third, seven related models with one noisy AndroidWorld run each are a weak calibration set.** A correlation can be driven by one poor model or a shared training lineage. Training directly against this matcher then changes the relationship being validated.

For the registered AndroidWorld values, an exact permutation calculation with untied SOP ranks gives approximately **p = 0.0476** at the `ρ ≥ 0.70` threshold. The threshold is barely significant under that favourable null calculation; it is not strong predictive validation.

**Fourth, the reference outcomes are inconsistent.** Round 13 uses E/D false-complete counts **23/26**, while the rerun-adjusted table reports **24/27**: [PREREG_v411.md:35](docs/PREREG_v411.md:35), [PREREG_v46.md:234](docs/PREREG_v46.md:234).

**Correction:** treat SOP as a provisional regression measure. Freeze one adjudicated reference table, report uncertainty and leave-one-model-out sensitivity, and require prospective online validation.

### M7. The statistical rules confuse screening thresholds, detectable effects, and evidence of failure

**Evidence:** [rounds.md:23](docs/rounds.md:23), [rounds.md:133](docs/rounds.md:133), [PREREG_v411.md:79](docs/PREREG_v411.md:79).

Nine discordant outcomes between two runs do **not** mean nine net successes are the minimum detectable improvement. The replicate had nine flips but only a one-success net difference. Statistical power depends on discordance, dependence, effect size, and the chosen test.

That replicate also changed run conditions: the initial pass had nine exceptions and lacked a cold boot; the replicate had two exceptions. It mixes infrastructure effects with behavioural variability.

Conversely, E-S’s threshold of 22 versus E’s 19 is a reasonable advancement heuristic, but three extra successes in 116 tasks are not persuasive evidence of improvement.

Repeated development rounds and changing probes create adaptive selection even when each round is preregistered. Multiple hard offline gates also create false rejection opportunities; they do not automatically make the overall process rigorous.

**Correction:** distinguish:

- Operational advancement thresholds.
- Evidence of improvement.
- Evidence ruling out a worthwhile improvement.

A failed gate is not automatically evidence that the underlying idea is ineffective.

### M8. The sequencing problem was already diagnosed, then repeated

**Evidence:** [small-gui-agent-training-methods.md:88](docs/research/small-gui-agent-training-methods.md:88), [own_mistakes_methods.md:439](docs/research/notes/training-on-own-mistakes-and-overfitting/own_mistakes_methods.md:439), conversation lines 11575–11618.

Earlier research already recommended:

- Calibrating SOP before further selection.
- Learning from model-generated histories.
- Considering self-history SFT before porting a full RL stack.

The latest conversation presents essentially these conclusions as a newly discovered limitation after several additional rounds.

The causal explanation is also too confident:

- “Every round trains on human histories” contradicts the earlier own-history and counterfactual interventions.
- Calling the failure “causal confusion” names a hypothesis; the experiments do not isolate it.
- “Every final screen” being labelled done does not mean the model observes an explicit final-screen flag. Endpoint-distribution shortcuts are plausible, not proven.

Round 13 then launched full training while the proposed yardstick validation was still running. The preregistration permits fallback testing, so this is not necessarily a protocol violation. It does undermine the stated sequence, “fix the yardstick first.”

**Correction:** maintain an experiment ledger containing the hypothesis, distinguishing observation, and result that would change the next decision. Stop recycling the same diagnosis without testing the missing causal link.

### M9. These held-out seeds are no longer fresh confirmation for later models

**Evidence:** [PREREG_v46.md:246](docs/PREREG_v46.md:246), [PREREG_v46.md:262](docs/PREREG_v46.md:262), [PREREG_v411.md:80](docs/PREREG_v411.md:80).

The repository acknowledges that the seeds were opened and v4’s failures inspected before later model development. Sealing a new model’s outcomes until its run finishes does not restore independence from those earlier diagnoses.

Likewise, AndroidControl **test** episodes repeatedly used as gates are now a development resource.

The round-11/12 endpoint probes are not episode-disjoint holdouts: uniform replay does not exclude their source episodes, and E already trained on preceding trajectory rows. This is not proof of direct terminal-label leakage, but “never trained” needs to mean **the endpoint supervision**, not an unseen episode: [r11_mix.py:171](data/r11_mix.py:171), [r12_mix.py:260](data/r12_mix.py:260).

I found no direct benchmark-row ingestion in the reviewed training builders. That narrower conclusion does not certify all historical dataset provenance.

**Correction:** label these as reused evaluation instances. Reserve untouched episode groups for prospective proxy validation and fresh seeds for the final frozen candidate, while acknowledging shared task templates.

### M10. The done-check system can change failure labels without improving completion

**Evidence:** [lfm_agent.py:208](eval/androidworld/lfm_agent.py:208), [lfm_agent.py:227](eval/androidworld/lfm_agent.py:227), [lfm_agent.py:309](eval/androidworld/lfm_agent.py:309).

The implementation follows the registered fail-open and three-block rules. Those rules themselves limit what it can accomplish:

- Unparseable checks accept completion.
- After three blocks, completion is accepted unchecked.
- A rejected completion forces another action without establishing that a useful continuation exists.
- The replacement grammar excludes `status` but permits `answer`, which immediately ends the episode and bypasses this completion check.

Thus a blocked `complete` can become an incorrect answer or a step-limit failure. False-complete count falls while task completion does not improve.

The unit test checks request routing and replacement execution against a stub. It does not establish that the real server honours the intended reasoning continuation and grammar combination, or that replacements improve outcomes.

**Correction:** measure recovered successes, destroyed successes, replacement actions, answer substitutions, and additional steps. Treat reduced false-complete count as a secondary result.

## Minor findings

### N1. Replay retention differs from the table’s explicit “yes” criterion

[replay_done_check.py:118](eval/androidworld/replay_done_check.py:118) counts every non-`no` answer as a retained success. The preregistration table requires answers **yes** on at least 76 successes.

For example, 75 yes answers and 19 unparseable answers pass implementation retention but fail the table’s explicit-yes criterion.

Fail-open retention matches deployment behaviour; explicit-yes retention measures verifier competence. Report both and resolve the specification discrepancy.

### N2. SOP output and resume integrity are incomplete

[sop.py:123](eval/androidcontrol/sop.py:123) reports PG and TSR but omits the registered aggregate `(PG + TSR)/2`. It also omits the promised human-wait failure breakdown.

At [sop.py:144](eval/androidcontrol/sop.py:144), resume identifies rows only by episode ID. Reusing an output path after changing model or options can silently combine incompatible results. Duplicate rows are not rejected.

Replay has a similar resume weakness: [replay_done_check.py:102](eval/androidworld/replay_done_check.py:102).

Record and enforce model, data, prompt, configuration, and case-set hashes.

### N3. Restarted round-13 jobs can reuse stale exports

[sm_r13.sh:37](scripts/training/sm_r13.sh:37) skips merging whenever `merged/config.json` exists. It does not verify that the export corresponds to the current adapter. A stale or interrupted export can consequently be evaluated.

Training checkpoints overwrite a single adapter directory before writing the state file: [semi_online_rl.py:380](train/semi_online_rl.py:380). Saving model, optimiser, and progress separately is not transactional; random-generator state is also not restored.

These are conditional restart bugs, not evidence that the current uninterrupted run is corrupted. Use immutable checkpoint directories and adapter hashes for exports and evaluations.

### N4. The E analysis makes an incorrect review-coverage claim

[sealed_analysis.py:297](analysis/sealed_analysis.py:297) emits “Every success is also reviewed.” However, [PREREG_v46.md:297](docs/PREREG_v46.md:297) explicitly says E’s success review was not performed.

The arithmetic handling of E’s rerun false-complete counts appears correct: replacements update the original arm’s stored count at [sealed_analysis.py:194](analysis/sealed_analysis.py:194), and E’s rule compares the intended arms. I found no demonstrated E-arm tally bug.

Correct the coverage statement and distinguish checker success from reviewed satisfaction of the owner’s goal.

## Is the current strategy the right bet?

**Round 12:** worth completing as a bounded verifier-and-data experiment. It is a weak primary bet because it adds no independent observation, inherits judge errors, and may merely redirect termination. Its decisive result is additional completed tasks after blocking.

**Round 13:** the stronger direction, but the present implementation is an experimental adaptation, not a faithful UI-S1 reproduction. Beyond patch-boundary returns, it differs in patch thoughts, input images, optimisation, regularisation, and training exposure. The notes describe thought-free patches, two history images, KL regularisation, filtering, and five epochs; the implementation uses expert intents at patches, one image, an unclipped mean-token policy-gradient loss, and 400 episodes.

The loss sign is correct. Generations precede a single optimiser update, so lack of PPO clipping is **not inherently a correctness bug**. But a positive-advantage smoke update only checks gradient direction. It does not validate advantages, transition semantics, or useful learning.

**LoRA at 2B:** not established as the binding limit. Similar results from another 2B backbone under a similar recipe cannot isolate adapter capacity. Nor do near-ceiling permissive grounding scores prove perception is solved. There is insufficient evidence to spend the next day sweeping rank or full fine-tuning.

**Single-screenshot input:** a plausible structural limitation for verifying changes and remembering earlier facts. It is not universally insufficient: some goals are fully visible on the current screen. Test an equal-budget before/after input or compact evidence memory on transition-dependent cases before redesigning everything.

**Evaluation noise:** large enough to hide modest gains and reverse rankings. E’s reported difference from v4, −0.6 points with CI approximately [−5.4,+4.2], permits a useful gain or loss. That uncertainty does not rescue a strategy whose intermediate metrics repeatedly improve without demonstrated task gains. It demands better experiments.

## Ranked recommendations

### 1. Repair transition matching and patch-boundary credit before interpreting E-S

**Change:** add strict transition matching, explicit terminal handling, natural-segment returns, and endpoint-retention statistics.

**Why:** C1, M1, and M2 directly affect what the algorithm rewards.

**Cost:** roughly half to one engineering day; CPU checks plus a small GPU smoke.

**Success criterion:** adversarial fixtures reject wrong identifiers and wrong elements; terminal actions have defined stopping behaviour; pre-patch returns contain no post-patch reward; logged completed tasks require genuine endpoints.

Keep the existing E-S run as a labelled exploratory arm. A corrected run is a new experiment.

### 2. Establish deterministic initial state and contemporaneous paired evaluation

**Change:** verify reset postconditions; run E and the candidate under the same pinned protocol with balanced emulator assignment and order.

**Why:** C2 makes small historical differences difficult to interpret.

**Cost:** about one engineering day, followed by emulator time using the two available devices.

**Success criterion:** reset assertions pass, contamination from preceding tasks is absent in sentinel checks, and both arms have comparable infrastructure reliability.

Do not add cloud machines until this protocol works locally.

### 3. Fix the outcome taxonomy and measure recovery yield

**Change:** report full success, unsuccessful completion claims including partial credit, wrong answers, infeasible declarations, and budget exhaustion. For checks, report successful recovery after each block and harm to otherwise successful episodes.

**Why:** M3 and M10 expose straightforward ways to improve a failure count without helping the user.

**Cost:** a few hours of analysis and harness logging.

**Success criterion:** a candidate’s claimed benefit survives the full outcome accounting, with additional successes rather than only redistributed failures.

### 4. Make SOP a prospective regression tool with proper integrity checks

**Change:** freeze episode IDs and hashes, add strict/permissive scores, depth-conditioned stop hazards, aggregate SOP, wait failures, and paired uncertainty. Keep a separate untouched episode group.

**Why:** M6 and N2 prevent treating one noisy correlation as permanent validation.

**Cost:** half a day plus inference; no emulator required for the proxy.

**Success criterion:** model rankings are not driven by one outlier or loose matching, and subsequent candidate improvements predict online direction. A failed retrospective correlation should leave SOP provisional, not trigger threshold shopping.

### 5. Run one matched self-history SFT control against corrected RL

**Change:** save first-divergence examples from clean training trajectories, using the same episode budget and input format as RL. Train with the existing SFT stack. Reserve endpoint exposure deliberately.

**Why:** this distinguishes the value of model-generated histories from the value of the new RL objective. The repository already proposed this cheaper control.

**Cost:** one bounded continuation on the L4 or A10G, plus rollout generation. Use the same reviewed data in both arms.

**Success criterion:** corrected RL improves strict SOP or online completion beyond the matched SFT control. Otherwise choose the simpler training procedure.

### 6. Re-audit ambiguous endings with independent evidence

**Change:** quarantine failed AndroidControl verdicts; audit a stratified sample of done, unfinished, wait, and written-action cases without showing the original verdict first. Allow “unknown.”

**Why:** M4 and M5 show that current agreement figures overstate independence.

**Cost:** several hours; a small portion of the remaining roughly $62 API budget if needed. Do not relabel everything.

**Success criterion:** source-specific error rates meet fixed bars, ambiguous cases are excluded, and a sample of written actions demonstrably advances the intended task where execution is feasible.

### 7. Test outcome observability before increasing model or adapter size

**Change:** on clean non-benchmark trajectories, compare current-only input with an equal-total-pixel-budget before/after pair or an explicit evidence memory. Target wrong transitions and goals requiring earlier facts.

**Why:** the current history records intentions and actions more reliably than outcomes.

**Cost:** half a day to build a diagnostic; one small training run only if the diagnostic shows headroom.

**Success criterion:** improved discrimination of successful versus failed transitions on held-out cases, followed by improved recovery—not merely better explanation text.

### 8. Freeze one candidate and reserve confirmation for the final decision

**Change:** reconcile reference counts, document all attempted variants and amendments, distinguish screening from inference, and reserve fresh evaluation instances for one frozen candidate. Report reused seeds as reused.

**Why:** preregistration per round does not remove cumulative selection or earlier benchmark exposure.

**Cost:** several hours of bookkeeping; final emulator time dominates.

**Success criterion:** the final report states the effect and uncertainty, exposes failure tradeoffs, and makes no superiority or generalisation claim that the evaluation cannot support.