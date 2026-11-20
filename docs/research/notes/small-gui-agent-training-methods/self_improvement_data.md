# Self-improvement, trajectory synthesis, DAgger-style rollouts, recovery/reflection data, and data recipes for small (<=3B) mobile GUI agents

Context: LFM3-VL-2B, screenshot-only, LoRA SFT on AndroidControl gives 15/116 on AndroidWorld (AW). Measured failures: no `answer` emission, premature `complete` (45/101 failures), no recovery after no-effect actions, identical-action loops (54 episodes hit the step budget). Notes were compiled in November 2026. Numbers were extracted from arXiv HTML full text with targeted extraction, so table values should be spot-checked before they go into a final report. AW numbers are pass@1 unless marked otherwise.

## Q1. Trajectory synthesis and self-evolution (OS-Genesis, AutoPlay/Explorer-style, GUI-Owl, UI-TARS flywheel, MAI-UI, Step-GUI, UI-Genie, ZeroGUI, OpenMobile): gains, model size, trajectory counts, verifiers

### Takeaway
Environment-grounded synthetic trajectories reliably beat human-task-driven data on AW at 3-8B. About 1K synthesized trajectories gave a 4B model +11 pts (OS-Genesis). About 20K exploration-grounded tasks took a 3B model to 34.2% (AutoPlay). 2.8K tasks / 34K steps took a 7B model from 25.5% to 51.7% (OpenMobile). The strongest small model, MAI-UI-2B at 49.1%, comes from an iterative rejection-sampling loop that uses an MLLM judge and reuses failed-trajectory prefixes. Most of the large gains come from synthesis on AW's own 20 apps, so app-level contamination is the norm, not the exception.

### Cited Findings
- **OS-Genesis (reverse task synthesis).** It explores the UI by interacting with elements, turns ⟨s_pre, a, s_post⟩ triplets into low-level instructions, then lifts those into high-level tasks that seed trajectory collection with GPT-4o. — [OS-Genesis](https://arxiv.org/html/2412.19723)
- OS-Genesis AW success (both its data and the task-driven baseline use 1K trajectories). InternVL2-4B: zero-shot 0.00, task-driven 4.02, task-driven + self-instruct 7.14, OS-Genesis 15.18. InternVL2-8B: 2.23 / 4.46 / 5.36 / 16.96. Qwen2-VL-7B: 0.89 / 6.25 / 9.82 / 17.41. — [OS-Genesis](https://arxiv.org/html/2412.19723)
- OS-Genesis uses a GPT-4o Trajectory Reward Model that grades 1-5 on completion and coherence, rather than a binary labeler that discards incomplete trajectories. The authors say TRM mainly helps high-level metrics (AC-High, AW). A binary labeler gives "slight gains in high-level tasks… at the cost of reduced performance in low-level tasks." — [OS-Genesis](https://arxiv.org/html/2412.19723)
- OS-Genesis scaling: "task performance generally improves as the number of trajectories increases, while saturation emerges at larger data scales", which the authors attribute to VLM capacity and to GPT-4o's ability to complete high-level tasks. The extracted text does not say whether AW apps were used for exploration. It does say only 20 of AndroidControl's 833 apps were seen during synthesis. — [OS-Genesis](https://arxiv.org/html/2412.19723)
- **AutoPlay (exploration-grounded task generation).** An MLLM explorer with memory explores apps, then a task generator writes environment-grounded tasks from the exploration context. It produced 20k tasks across 20 Android apps and 10k tasks across 13 Ubuntu apps. The executor uses a GPT-4o planner/reflector with a UI-TARS-1.5-7B grounder (mobile). The verifier is GPT-4o: it summarises the trajectory, reasons in CoT, then returns success/failure. Qwen2.5-VL-32B serves as the verifier for RL. — [AutoPlay](https://arxiv.org/html/2509.25047)
- AutoPlay results: AutoPlay-3B reaches **34.2% on AW**. AutoPlay-7B beats Qwen2.5-VL-7B by 20.6 pts on AW, and 72B beats its base by 12.9 pts. RL adds another 5.7 pts. **Contamination:** "we use 20 mobile apps from Rawles et al. (2024)", which are the AndroidWorld apps. — [AutoPlay](https://arxiv.org/html/2509.25047)
- **OpenMobile (2026).** Explore → build a global environment memory → synthesize compositional tasks, including question-answering tasks. The output is 2.8K instructions and 34K action steps across 20 Android apps. Qwen2.5-VL-7B goes from 25.5 to **51.7** on AW and Qwen3-VL-8B from 47.6 to **64.7**. In its ablation, OS-Genesis-style task synthesis scores 34.1, a coupled pipeline 45.3, and OpenMobile 48.3. Contamination: it runs on the AndroidWorld emulator and apps but states "we do *not* incorporate any benchmark test instructions". Removing the most similar instructions causes "only a marginal performance drop". — [OpenMobile](https://arxiv.org/html/2604.15093)
- **MAI-UI (Dec 2025).** MAI-UI-2B scores **49.1%** on AW, with SFT-only at 45.1 and RL adding 4.0. The 8B scores 70.7 and the 235B-A22B 76.7. Its self-evolving SFT pipeline has three parts. Tasks come from app manuals, expert-designed tasks and filtered open datasets. Trajectories come from human annotation on emulators plus several GUI agents. Iterative rejection sampling alternates fine-tuning with rollouts from the updated policy. — [MAI-UI](https://arxiv.org/html/2512.22047v1)
- MAI-UI's judge "assesses end-to-end success, prioritizing visual evidence from screenshots over textual claims generated by the GUI agent". For failed trajectories it "identifies the longest prefix of correct actions before the first deviation", so partial successes are reused. The extracted text gives no dataset sizes and no AW contamination statement. — [MAI-UI](https://arxiv.org/html/2512.22047v1)
- **GUI-Owl / Mobile-Agent-v3.** Queries come from a human-annotated DAG of app navigation flows with LLM instruction synthesis. GUI-Owl rolls out on those queries. A step-level critic labels each step GOOD/NEUTRAL/HARMFUL, and a two-channel trajectory critic (text and multimodal) decides by consensus. Hard tasks get query-specific guidance distilled from successful trajectories. The loop is iterative online rejection sampling, M(k+1) = Train(M(k), T(k)_filtered). GUI-Owl-7B scores 66.4 on AW and Mobile-Agent-v3 73.3. The authors report "sustained performance improvements" over iterations but no numbers were extracted. The extracted text has no contamination statement. — [Mobile-Agent-v3](https://arxiv.org/html/2508.15144)
- **UI-TARS data flywheel.** Online traces are filtered three ways. Rules remove "redundant actions that do not alter the environment". A VLM scores traces against a threshold. Humans truncate traces at the first error and keep the valid prefix. This runs "on hundreds of virtual PCs for multiple rounds". — [UI-TARS](https://arxiv.org/html/2501.12326)
- **Step-GUI (Dec 2025, 4B/8B).** Its Calibrated Step Reward System anchors LLM-generated step-level labels to trajectory-level verification, either scripts or human labels. The paper claims ">90% annotation accuracy with 10-100× lower cost". Over 6 self-evolving rounds, AW jumped from 44.83% (round 2) to 73.40% (round 3). Final AW is 80.2 for the 8B and 75.8 for the 4B, both labeled pass@3. Data volumes: ~11.2M mid-train and ~1.67M cold-start samples. The extracted text has no contamination statement. — [Step-GUI](https://arxiv.org/html/2512.15431v1)
- **UI-Genie.** A reward model (UI-Genie-RM, trained on 517k samples) guides beam-like exploration. At each step the agent proposes 10 candidates and the top 5 partial paths are kept. Outcome verification then admits successful trajectories. Three rounds produced UI-Genie-Agent-16k (16k trajectories). AndroidLab success for the 7B rose from 18.1% (round 0) to 38.7% (round 3), and "the most dramatic improvement occurs during the first round". The 3B reaches 93.8 / 72.9 on AndroidControl low/high. AW was not evaluated. — [UI-Genie](https://arxiv.org/html/2505.21496)
- **ZeroGUI.** It generates tasks with a VLM (more than 4,000 Ubuntu and 225 Android tasks) and estimates rewards with a voting VLM judge. AndroidLab SR rose 2.8 on the operation subset and 1.8 on the full set, and OSWorld rose 14% relative for UI-TARS-7B-DPO. **Contamination:** stage 2 is "test-time training… to adapt to target test tasks". False positives from the reward estimator hurt more than false negatives. — [ZeroGUI](https://arxiv.org/html/2505.23762)
- **Ferret-UI Lite (3B, Apple).** It reaches 28.0% on AW with online multi-agent synthesis (curriculum task generator, planner, grounder, critic) and a VLM-as-judge filter. RLVR lifts AW from 25% to 28%. The authors note small models "show limited performance compared to larger models" on multi-step navigation and are "sensitive to RL reward designs". — [Ferret-UI Lite](https://arxiv.org/html/2509.26539)

### Inferences
- At 2-4B, the evidence suggests 1K-3K environment-grounded, verifier-filtered trajectories should give a larger AW gain than adding more human offline data. OS-Genesis-4B gained about 11 pts with 1K trajectories. OpenMobile gained about 26 pts at 7B with 2.8K tasks. Our 15/116 (12.9%) is roughly where OS-Genesis-4B ended (15.2%), so we are at the "offline data only" ceiling.
- Synthesizing tasks from exploration of the actual emulator apps, as OpenMobile and AutoPlay do, appears to be the main driver. Both use the AW app set, so any gain we get this way has to be reported as "app-overlap, no test-instruction overlap".
- A cheap and robust verifier design combines three things: judge on screenshots, not on the agent's claims (MAI-UI); reuse the prefix of failed trajectories up to the first error (MAI-UI, UI-TARS); and keep false positives low (ZeroGUI).

### Gaps
- Explorer (web), AgentTrek (web tutorials), AndroidGen, LearnAct and Go-Browse were not fetched. They are mostly web or few-shot methods with no small-model AW numbers verified here.
- MAI-UI, GUI-Owl and Step-GUI training-set sizes and AW app overlap could not be verified from the extracted text.
- The OS-Genesis exploration environment (whether it used AW's emulator snapshot and apps) was not confirmed.
- UI-TARS-2 data-flywheel details were not fetched.
- MAI-Gym (an open GUI RL/eval platform, [arXiv 2610.20939](https://arxiv.org/html/2610.20939v1)) and Darwin Mobile Agent ([arXiv 2606.20622](https://arxiv.org/html/2606.20622v1)) surfaced in search but were not read.

## Q2. DAgger / on-policy distillation / rejection-sampling fine-tuning (filtered BC on self-rollouts): gains vs pure SFT; how many rollouts

### Takeaway
On-policy data beats off-policy SFT at every scale where it has been measured. DigiRL's 1.3B model went from 17.7% (SFT) to 57.8% with online filtered BC and 67.2% with RL on AitW Web Shopping, using about 1K online trajectories. The best 2026 recipe is DAgger-like. The learner drives the episode, an expert takes over only when a monitor detects a deviation, and the training set keeps the expert steps with the learner's error-filled history. This beat pure expert distillation (48.3 vs 44.8) and pure self-evolution (33.8).

### Cited Findings
- **DigiRL (AutoUI, 1.3B; AitW).** Test success on General / Web Shopping: SFT 14.6 / 17.7; offline filtered BC 50.7 / 45.8; online filtered BC 61.5 / 57.8; offline-to-online DigiRL 71.9 / 67.2. The text also says Web Shopping improved "57.8% to 61.4%", which conflicts with the table's 67.2, so check this. Data: about 1,500 offline trajectories, or 500 offline plus 1,000 online for offline-to-online. The Gemini autonomous evaluator has "average error rate 2.8% against human judgement". — [DigiRL](https://arxiv.org/html/2406.11896)
- **OpenMobile policy-switching rollouts (DAgger-like).** The learner starts and a monitor "detects that the learner has deviated from productive progress" and switches to the expert (Gemini-3.1-Pro-Preview). The paper retains "only expert steps for training while preserving the full interaction history, including learner errors… to expose the model to realistic error-recovery scenarios". Ablation pass@1 on AW: expert distillation 44.8, self-evolution 33.8, random switch 45.1, **error-intervention switch 48.3**, with the Avg.ER column at 0.42 / 0.10 / 0.64 / 1.56. — [OpenMobile](https://arxiv.org/html/2604.15093)
- **On-Policy Self-Distillation for GUI agents (Sept 2026, Qwen3-VL-8B).** The model under privileged context (corrective or planning/memory hints from a strong LLM, Kimi-K3) acts as a self-teacher for the same model under normal context. Training combines GRPO-style group advantages with token-level reverse-KL distillation. AW results: SFT 50.9, GRPO 52.6, OPSD **67.2** (+26.7 over base). It used 400 tasks in stage 1 and 1,013 tasks in stage 2, with 8 rollouts per state (4 privileged, 4 not). The extracted text has no contamination statement. — [OPSD for GUI agents](https://arxiv.org/html/2609.27307v1)
- **TurnOPD (2026; text agents, not GUI).** On-policy distillation brings small students close to their teachers. ALFWorld with Qwen3-1.7B: zero-shot 0.00, vanilla OPD 83.0, TurnOPD 86.3, teacher 90.75. WebShop 1.7B: 25.8 → 82.8 (teacher 84.5). Multi-hop search with Qwen3.5-2B: 36.1 → 47.2-47.8 (teacher 59.0). Runs used 32 H20 GPUs and took about 1.2-4.5 h per 100 optimizer steps. Failed rollouts show "repeated invalid actions, loops over the same subgoal". — [TurnOPD](https://arxiv.org/html/2607.05804v1)
- **Iterative rejection sampling in production systems.** MAI-UI alternates fine-tuning and rollout, filters with an MLLM judge, and reuses the longest correct prefix of failed runs. MAI-UI-2B reaches 45.1 with SFT and 49.1 after RL. — [MAI-UI](https://arxiv.org/html/2512.22047v1). GUI-Owl uses iterative online rejection sampling — [Mobile-Agent-v3](https://arxiv.org/html/2508.15144). UI-Genie's 7B reaches 38.7 on AndroidLab after 3 rounds, with the biggest jump in round 1 — [UI-Genie](https://arxiv.org/html/2505.21496)
- Scaling the online environment matters. MAI-UI reports +5.2 pts from scaling parallel environments from 32 to 512, and +4.3 from raising the step budget from 15 to 50. — [MAI-UI](https://arxiv.org/html/2512.22047v1)
- UI-TARS argues that SFT on corrected steps ignores negatives. Its DPO on (erroneous, corrected) step pairs "significantly improves the performance on OSWorld". — [UI-TARS](https://arxiv.org/html/2501.12326)

### Inferences
- With 2 emulators, a DAgger-like loop is feasible. Roll out LFM3-2B. Detect deviations with the cheap triggers already measured (no visual change after an action, repeated identical action, or `complete` while the judge says the task is not done). Then have a large VLM teacher, run locally or through an API, propose the corrective action. Train on the corrective step with the learner's own erroneous history in context.
- DigiRL and OPSD suggest about 1K online trajectories, or about 1.4K tasks, is enough for large gains at 1-8B. UI-Genie and Step-GUI suggest round 1 gives the most.
- Self-evolution alone (self-rollouts filtered for success) is the weakest variant in OpenMobile (33.8 vs 48.3). For a 2B model starting at about 13%, few successful self-rollouts will exist, so expert intervention is likely required.
- My own throughput guess, not from a source: 2 emulators at roughly 1-3 min per episode gives about 40-120 episodes per hour, so 1K rollouts is about 1-2 days of emulator time.

### Gaps
- No paper found isolates filtered BC vs DAgger vs RL at 2B on AndroidWorld specifically. DigiRL is AitW at 1.3B. OpenMobile and OPSD are 7-8B.
- The exact meaning of OpenMobile's "Avg.ER" column was not confirmed from the extraction.
- The source of OPSD's training tasks, and whether they overlap AW, was not confirmed.

## Q3. Error recovery and reflection data (injected mistakes plus corrections, "back" recovery, history-aware training): evidence it reduces loops and no-op repeats

### Takeaway
Synthetic recovery data can be made offline from AndroidControl with no emulator, and it helps. GUI-Reflection built about 33K samples from AndroidControl in two ways: goal modification so a step becomes a mistake followed by Back and a retry, and insertion of ineffective actions (no-op scroll or tap) followed by reflection. On its own benchmark this raised SFT success from 14.6% to 23.6%, and to 34.7% with online reflection tuning. GUI-Reflection-8B scores 34.5% on AW. Xiaomi-GUI-0 identifies imitating repeated steps as a direct cause of loops. Its fix is to drop repeated steps from the labels while keeping them in the history.

### Cited Findings
- **GUI-Reflection (InternVL2.5-8B), offline error data from AndroidControl.**
  - Approach 1: an MLLM modifies the goal so that action a_t becomes a natural mistake. Step t+1's thought recognises the mistake and outputs Back or a correction. If it is Back, step t+2 summarises the error and retries. 17,557 samples.
  - Approach 2: an "ineffective incorrect action" is inserted, such as scrolling when already at the bottom or tapping a non-interactive element. The next step's thought reflects on it and then takes the original correct action. 15,394 samples.
  - Online: find the first wrong step, label a pre-error correction and a post-error recovery (Back, then retry).
  - — [GUI-Reflection](https://arxiv.org/html/2506.08012)
- GUI-Reflection ablation on the authors' own Android environment (215 task templates, 11 apps; the figures are for its level-2 tasks): filtered BC without reflection data 14.58%, with reflection data 23.61%, plus online reflection tuning 34.72%. On AW (Table 3), GUI-Reflection-8B scores **34.5** against UI-TARS-7B at 33.0. — [GUI-Reflection](https://arxiv.org/html/2506.08012)
- **Xiaomi-GUI-0 (Qwen3-VL-30B-A3B; 78.9% AW).** "using repeated steps directly as labels teaches the model a negative pattern, namely to keep repeating when stuck… manifests online as repetition loops." The fix: "detach these steps from the training labels while preserving them in the trajectory history". The corrective step that breaks the stall (Back, switching entry point, re-planning) stays as a label. — [Xiaomi-GUI-0](https://arxiv.org/html/2606.31410v2)
- Xiaomi-GUI-0's error-driven flywheel uses interactive annotation that "localizes and corrects the first key error in failed trajectories". A teacher model also scores and takes over: it "detects off-path student behavior at scale and demonstrates recovery". There are about 5,000 samples covering 14 types of abnormal state. No ablation numbers were extracted. — [Xiaomi-GUI-0](https://arxiv.org/html/2606.31410v2)
- **Ferret-UI Lite** perturbs clean trajectories "with error-prone frames (e.g., replacing terminate with an erroneous swipe) to simulate stuck navigation states and generate correction sequences". — [Ferret-UI Lite](https://arxiv.org/html/2509.26539)
- **UI-TARS reflective tuning.** Annotators label the corrected action at the first error (an error-correction pair). They also label the *next* step given that the error already happened (a post-reflection pair), for example reopening a page that was closed by mistake. — [UI-TARS](https://arxiv.org/html/2501.12326)
- **OpenMobile** keeps learner errors in the history before the expert's corrective step to "expose the model to realistic error-recovery scenarios". The error-intervention switch (48.3) beat pure expert distillation (44.8). — [OpenMobile](https://arxiv.org/html/2604.15093)
- **Loop prevalence and inference-time fixes.**
  - AndroidReality reports agents that "retr[y] the same incorrect coordinate-level actions repeatedly, in extreme cases up to dozens of identical clicks before the step budget is exhausted". Its test-time diagnoser triggers alternative-action recovery after 3 identical taps. — [AndroidReality](https://arxiv.org/html/2608.07775v1)
  - VLAA-GUI (desktop; frontier backbones) uses a tiered loop breaker. Tier 1: the same action on the same target with no visible change forces a different interaction mode. Tier 2: the same screen state seen 3 times forces a change of strategy. Removing the loop breaker drops WindowsAgentArena from 60.4% to 52.6% at 50 steps, and OSWorld (Gemini 3 Flash, 50 steps) from 63.1% to 58.9%. "weaker models are more prone to repetitive behavior." — [VLAA-GUI](https://arxiv.org/html/2604.21375v3)
- UI-TARS's rule-based filter removes traces with "redundant actions that do not alter the environment" before training. — [UI-TARS](https://arxiv.org/html/2501.12326)

### Inferences
- Concrete offline fixes for our loop and no-effect failures that need no emulator:
  1. Scan AndroidControl, GUI-Odyssey and AMEX for consecutive identical actions or actions with no screen change, and mask them as labels while keeping them in history (Xiaomi-GUI-0).
  2. Generate GUI-Reflection-style insertions: put a no-op action into the history and make the label the original correct action, about 15K samples. Also generate "wrong tap → Back → retry" sequences, about 17K samples. AndroidControl provides consecutive screenshots, so the "Back returns to the previous screen" assumption (I_{t+2} = I_t) can be used as GUI-Reflection does.
- A deterministic loop breaker at inference time is cheap insurance, but it is not a training fix. The evidence for it is from desktop/frontier agents (VLAA-GUI) and test-time recovery (AndroidReality), not 2B training.

### Gaps
- No source reports a direct metric such as "repeated-action rate before and after" from recovery-data training at small scale. Xiaomi-GUI-0 gives the mechanism but no extracted ablation numbers. GUI-Reflection gives success-rate deltas only.
- The size of BacktrackAgent and GUI-ReWalk effects was not checked.

## Q4. Answer and termination supervision: learning when to stop and when to answer (AW information-retrieval tasks); calibrated completion and verifier models

### Takeaway
AW has 27 information-retrieval tasks out of 116, so an agent that never answers gives up about 23% of the benchmark. Successful pipelines synthesize QA-style tasks from the environment. OpenMobile generates question-answering tasks, and Ferret-UI Lite rewrites trajectory goals into questions. Termination calibration is taught with explicit negatives (early truncation, redundant continuation) and with screenshot-based judges that ignore the agent's own success claims. False completion is the dominant failure even for frontier agents.

### Cited Findings
- AW's 116 tasks split into information retrieval (27) and task completion (89). An 8B OPSD model reached 59.3% (16/27) on IR versus 69.7% (62/89) on task completion. — [OPSD for GUI agents](https://arxiv.org/html/2609.27307v1)
- OpenMobile generates both "Action tasks" and "Question-answering tasks". QA tasks "Require performing a series of actions and answering a question related to the environment's content (e.g., 'how many tasks need to be completed this Wednesday? Answer… with a single number')". It uses Qwen3-VL's action and answer format. — [OpenMobile](https://arxiv.org/html/2604.15093)
- Ferret-UI Lite builds synthetic QA by "rewriting goals into natural language questions" on existing episodes. It also replaces `terminate` with an erroneous swipe to create stuck-state corrections. — [Ferret-UI Lite](https://arxiv.org/html/2509.26539)
- GUI-Reflection's pretraining mix includes ScreenQA (62,401 samples), alongside grounding and captioning sets. — [GUI-Reflection](https://arxiv.org/html/2506.08012)
- UI-Genie trains its reward model on trajectory negatives built by "Early truncation (… incomplete executions)", "Cross-task substitution" and "Redundant continuation — appending unnecessary steps beyond task completion to model failure in recognizing terminal states". — [UI-Genie](https://arxiv.org/html/2505.21496)
- MAI-UI's judge prioritizes "visual evidence from screenshots over textual claims generated by the GUI agent". MAI-UI also synthesizes `ask_user` turns: tasks deliberately omit information, and an LLM user agent answers when asked. — [MAI-UI](https://arxiv.org/html/2512.22047v1)
- Step-GUI's step-level data includes "progress tracking", "state summary", "effect prediction", "self-reflection" and "state verification" categories. — [Step-GUI](https://arxiv.org/html/2512.15431v1)
- Premature completion is pervasive. In VLAA-GUI (desktop), "most failed tasks still end with an incorrect completion claim": the false-DONE share of failures stays above 86% even with their Completeness-Aware Planner. That planner derives K UI-observable success criteria and requires a separate MLLM judge to accept DONE. Removing it drops WindowsAgentArena from 60.4% to 51.3%. On OSWorld with Gemini 3 Flash at 50 steps, removing it *raised* success (66.0 vs 63.1), so the effect varies by model and budget. — [VLAA-GUI](https://arxiv.org/html/2604.21375v3)
- ZeroGUI found reward false positives (judging a task done when it is not) hurt more than false negatives. — [ZeroGUI](https://arxiv.org/html/2505.23762)
- DigiRL's Gemini-based evaluator had a 2.8% error rate against humans on AitW. — [DigiRL](https://arxiv.org/html/2406.11896)

### Inferences
- The `answer` failure is mostly a format and coverage gap, not a capability gap. Two data sources would close it:
  - Rewrite AndroidControl/GUI-Odyssey goals into "find X and answer" questions whose answer is visible on the final screenshot (Ferret-UI Lite style), plus ScreenQA (already in v2).
  - Generate QA tasks on our emulators from exploration (OpenMobile style).
  Each episode must end with `answer(...)` and then `complete`, using the exact format AW's harness parses.
- For premature `complete` (45/101), two data fixes apply:
  1. Add hard negatives as SFT counter-examples. Take truncated success trajectories whose label at the truncation point is the next real action, not `complete`, which is UI-Genie's early-truncation idea turned into SFT.
  2. In DAgger rollouts, treat "model said complete but the judge or the task check says not done" as an intervention trigger and label the teacher's continuation.

  A short "progress/state verification" thought before `complete` (Step-GUI categories) is a plausible further lever.
- A screenshot-only success judge for our own synthetic tasks should be tuned for precision over recall (ZeroGUI).

### Gaps
- No paper found isolates the AW gain from adding answer/QA supervision at small scale.
- No found work trains an explicit calibrated "stop-probability" head for GUI agents. GUI-Critic-R1 (pre-operative critic) was not fetched.

## Q5. Reasoning/thought distillation from a large VLM teacher for small agents: help or hurt?

### Takeaway
The evidence is mixed but leans positive for closed-loop OOD success at 3B, provided thoughts are distilled into the model rather than prompted. Ferret-UI Lite-3B improved on AW from 13.7% (no CoT) to 15.8% (short CoT) and 19.6% (long CoT). UI-TARS found thought-free (System-1) output slightly better in-domain at a single sample but thoughts better out of domain (AW). Thinking tends to hurt pure grounding.

### Cited Findings
- **Ferret-UI Lite (3B).** Teacher thoughts were generated by GPT-4o with set-of-marks, conditioned on the ground-truth action and history, in three types: plan, action think and reflect. Short CoT improved AW from 13.7% to 15.8%, and long CoT reached 19.6%. The paper's stated deltas (+2.1, then +4.1) do not sum exactly to the extracted endpoints, so verify against the table. — [Ferret-UI Lite](https://arxiv.org/html/2509.26539)
- **UI-TARS.** "at N=1, system-2 reasoning performs slightly worse than system-1 reasoning across all three in-domain benchmarks". The advantage flips at N=16/64. "system-2 reasoning significantly outperforms system-1 in the OOD setting (AndroidWorld)." — [UI-TARS](https://arxiv.org/html/2501.12326)
- **Aguvis (7B).** Removing the GPT-4o-generated inner monologue drops AndroidControl-Low from 80.5 to 69.1, AC-High from 61.5 to 60.3, and ScreenSpot from 84.4 to 79.3. — [Aguvis](https://arxiv.org/html/2412.04454)
- **CoT empirical study (prompted frontier models).** Claude 3.7 Sonnet thinking improved AW by 6.3 pts on average (M3A-SoM 55.2 → 64.7). Gemini 2.0 Flash Thinking dropped 2.7 pts on average. On ScreenSpot, thinking cut Gemini grounding from 50.2% to 21.5% (normalized bbox). "reasoning and non-reasoning VLMs fail on different sets of tasks." — [Does CoT help mobile GUI agents?](https://arxiv.org/html/2503.16788v1)
- GUI-Owl reports AW gains from adding offline hint-guided rejection sampling, distillation from a multi-agent framework, and general reasoning SFT data, with each step "steadily" improving results. — [Mobile-Agent-v3](https://arxiv.org/html/2508.15144)
- The OPSD paper distills "reasoning and memory privileges" (what to plan, what to remember) into the policy and reaches 67.2 on AW at 8B. — [OPSD for GUI agents](https://arxiv.org/html/2609.27307v1)

### Inferences
- For a 2B model whose failures are termination and loops (state tracking), not grounding, a short structured thought is the likely sweet spot. It would cover what changed after the last action, what progress has been made, and whether the goal is visibly satisfied. Long free-form CoT is less suited. The thoughts should be teacher-generated, conditioned on the ground-truth action (Aguvis/Ferret-UI Lite recipe), and kept short to limit latency.
- Ablate thought vs no-thought at matched data, since UI-TARS shows the in-domain sign can be negative at N=1.

### Gaps
- No direct 2B AW ablation of thoughts was found. Latency or token-cost tradeoffs at 2B were not quantified in the sources read.

## Q6. Grounding pretraining (OS-Atlas, UGround, Aria-UI, ScreenSpot-style data) before agent SFT: how much does it help agent success at 2-3B?

### Takeaway
The gains are modest when the base VLM already has GUI perception. OS-Atlas grounding pretraining added +0.5 (4B) to +2.7 (7B) step-SR on AndroidControl-Low and +4.9 (4B) on GUI-Odyssey. In a controlled mid-training study on AW (Qwen2-VL-7B), GUI-perception data gave +5.0 pts versus +6.3 for multimodal math or chart QA. A 300K mixed reasoning mid-training set gave +12.2.

### Cited Findings
- **OS-Atlas** (13M+ elements, 2.3M screenshots), same agent SFT data, AndroidControl-Low step SR: InternVL2-4B 80.10 vs OS-Atlas-4B 80.64; Qwen2-VL-7B 82.56 vs OS-Atlas-7B 85.22. GUI-Odyssey SR: InternVL2-4B 51.45 vs OS-Atlas-4B 56.39; Qwen2-VL-7B 60.23 vs OS-Atlas-7B 61.98. — [OS-Atlas](https://arxiv.org/html/2410.23218)
- **GUIMid (Qwen2-VL-7B; mid-training, then the same GUI post-training).** AW SR: GUI post-training only 9.0; GUI perception 14.0; non-GUI perception 14.0; chart/doc QA 15.3; multimodal math 15.3; CodeI/O 14.9; MathInstruct 14.4; web Screenshot2Code 9.9. The GUIMid 300K mixture reaches **21.2** (+12.2). "GUI perception data… has a comparatively limited impact on final performance." — [Breaking the Data Barrier](https://arxiv.org/html/2504.10127)
- Aguvis's two-stage design trains grounding first, then planning with inner monologue. The extracted ablation covered removing Stage 2: AC-High 61.5 → 58.0, AC-Low 80.5 → 75.6. — [Aguvis](https://arxiv.org/html/2412.04454)
- Small successful agents still train heavily on grounding. Ferret-UI Lite-3B mixes GroundUI, OS-Atlas, UGround, Aria-UI, Aguvis, WaveUI, ShowUI and Jedi data and scores 91.6 on ScreenSpot-V2 and 28.0 on AW. — [Ferret-UI Lite](https://arxiv.org/html/2509.26539). Step-GUI's mid-training includes 2.7M grounding samples — [Step-GUI](https://arxiv.org/html/2512.15431v1)

### Inferences
- Our measured failures (no answer, premature complete, loops) are policy and state-tracking failures, not grounding failures. A separate grounding stage is unlikely to be the best use of limited GPU hours unless LFM3-VL-2B's ScreenSpot accuracy is low. That is cheap to measure first. A modest grounding and reasoning component mixed into SFT is a safer bet than a dedicated stage.

### Gaps
- The Aguvis "w/o Stage 1 (grounding)" row was not extracted. No 2B-specific grounding-pretraining → AW ablation was found. UGround and Aria-UI agent-level ablations were not fetched.

## Q7. Data-scale curves (AndroidControl/AitW scaling; diminishing returns)

### Takeaway
More offline AndroidControl-style data scales poorly out of domain. The AndroidControl authors extrapolate 1M episodes to reach 95% in-domain high-level step accuracy, but **60M** for out-of-domain. Synthetic, environment-grounded data shows early saturation as well (OS-Genesis), and self-improvement gains are front-loaded in the first round (UI-Genie).

### Cited Findings
- AndroidControl (PaLM-2S LoRA): "we extrapolate that it would take 500K and 1M episodes to reach 95% step-accuracy for low and high-level instructions". OOD step accuracy "is estimated to reach 95% at 10M and 60M episodes for low-level and high-level instructions". Reaching 95% episode completion on 5-step high-level OOD tasks would need about 150M episodes. "fine-tuning on more data alone may be insufficient for achieving robust out-of-domain performance." — [AndroidControl data scale](https://arxiv.org/html/2406.03679)
- In AndroidControl, the in-domain vs OOD gap grows with data. At 10K episodes it is 7.7-8.7 pp for high-level and 2.0-3.2 pp for low-level instructions. The best fine-tuned model reaches 71.5% (HL) and 86.6% (LL) step accuracy in-domain. — [AndroidControl data scale](https://arxiv.org/html/2406.03679)
- OS-Genesis: performance rises with trajectory count but "saturation emerges at larger data scales". — [OS-Genesis](https://arxiv.org/html/2412.19723)
- UI-Genie: the biggest jump comes in self-improvement round 1, then gains are smaller (AndroidLab 7B: 18.1 → 38.7 over 3 rounds). — [UI-Genie](https://arxiv.org/html/2505.21496)
- Step-GUI: a non-monotone, step-like curve over 6 rounds (AW 44.83% at round 2 → 73.40% at round 3). — [Step-GUI](https://arxiv.org/html/2512.15431v1)
- OpenMobile shows AW rising with the number of synthesized instructions (Fig. 3). Only 2.8K tasks and 34K steps were needed for +26 pts at 7B. — [OpenMobile](https://arxiv.org/html/2604.15093)

### Inferences
- Adding more AndroidControl, AMEX or GUI-Odyssey data (our v2 mix of about 79K episodes) should improve in-domain step accuracy but is unlikely, alone, to move AW much. The AndroidControl curve says OOD high-level scales one to two orders of magnitude slower. A few thousand on-policy or environment-grounded trajectories is the higher-yield addition.

### Gaps
- No published scaling curve for a <=3B model on AW specifically was found.

## Objective synthesis: what data, how much, and how to generate it cheaply for LFM3-VL-2B (2 emulators, few GPU-hours)

### Takeaway
The evidence points to a three-part recipe:
1. Offline, emulator-free fixes on the existing v2 mix: mask repeated or no-op steps as labels (Xiaomi-GUI-0), add about 30K GUI-Reflection-style injected-error and recovery samples, add QA goal-rewrites ending in `answer`, and add truncated-trajectory negatives for `complete`.
2. 1-3K emulator rollouts collected DAgger-style. The learner drives, and a large-VLM teacher intervenes on detected deviations: no screen change, repeated actions, or an unverified `complete`. Train on the teacher steps with the learner's error history (OpenMobile, Xiaomi-GUI-0).
3. A screenshot-only judge tuned for precision, used to filter and reuse failed-trajectory prefixes (MAI-UI).

### Cited Findings
- Error-intervention DAgger-style data beat pure expert distillation and pure self-evolution — [OpenMobile](https://arxiv.org/html/2604.15093). Repeated-step label masking targets loops — [Xiaomi-GUI-0](https://arxiv.org/html/2606.31410v2). Injected-error data raised SFT success from 14.6% to 23.6% on GUI-Reflection's environment — [GUI-Reflection](https://arxiv.org/html/2506.08012). About 1K online trajectories sufficed for large gains at 1.3B — [DigiRL](https://arxiv.org/html/2406.11896). 1K synthesized trajectories gave +11 pts at 4B — [OS-Genesis](https://arxiv.org/html/2412.19723). The judge should rely on visual evidence and reuse prefixes — [MAI-UI](https://arxiv.org/html/2512.22047v1).
- **Contamination summary:**
  - AutoPlay synthesizes tasks on the 20 AW apps — [AutoPlay](https://arxiv.org/html/2509.25047).
  - OpenMobile uses the AW emulator and apps but no test instructions, and runs a similarity-removal check — [OpenMobile](https://arxiv.org/html/2604.15093).
  - ZeroGUI's stage 2 trains on the target test tasks — [ZeroGUI](https://arxiv.org/html/2505.23762).
  - GUI-Reflection uses its own 11-app environment; overlap with AW was not stated — [GUI-Reflection](https://arxiv.org/html/2506.08012).
  - MAI-UI, GUI-Owl, Step-GUI and OPSD: no contamination statement in the extracted text.
  - Step-GUI headline AW numbers are pass@3, not pass@1 — [Step-GUI](https://arxiv.org/html/2512.15431v1).

### Inferences
- For our project, synthesizing tasks on the AW emulator apps is the cheapest high-yield path. Results must then be reported as "app-overlap, no test-instruction/template overlap". Generated instructions should be deduplicated against AW's 116 task templates by embedding similarity, with an ablation that removes the nearest neighbours (OpenMobile's protocol). Never use AW task classes or their success checkers as the training reward if results are to be claimed as clean held-out AW numbers.
- Expected ceiling reference points for 2-4B: OS-Genesis-4B at 15.2% (1K synthetic trajectories), Ferret-UI Lite-3B at 28.0%, AutoPlay-3B at 34.2% (20K tasks on AW apps), and MAI-UI-2B at 49.1% (industrial pipeline plus online RL).

### Gaps
- No single source isolates the AW contribution of each of our four failure fixes at 2B. Expected gains for LFM3-VL-2B specifically are extrapolations from 3-8B results.
