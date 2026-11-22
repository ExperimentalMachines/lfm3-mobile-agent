# Learning from own attempts at 2B on ~1 day, two Mac emulators and ~5 A100-hours (as of 2026-11-22)

Scope: methods where LFM3-VL-2B learns from its own samples or rollouts, without a paid teacher and without AndroidWorld (AW) or MobileWorld (MW) tasks. This builds on, and does not repeat, [training-on-own-mistakes-and-overfitting.md](../../training-on-own-mistakes-and-overfitting.md) (Agentic-DPO, VeriGUI, UI-S1, GHD, DeLoop, SOP proxy) and [small-gui-agent-training-methods.md](../../small-gui-agent-training-methods.md) (DigiRL, OpenMobile, contamination table). Numbers from those reports are re-cited to the original papers only where needed for comparison.

Labels: **Reported** = authors' number in their harness. **Ours** = measured in this repo. **Inference** = my reasoning, not measured.

---

## Q1. Offline methods on existing static trajectories using the model's own samples: what did each gain, at what size, with what compute and data?

### Takeaway
Offline own-sample methods give their largest reported gains when the model's *wrong* samples get a training signal (DPO/negative imitation/Q-ranking), not when only its correct samples are re-imitated. Only Agentic-DPO has a 2B result (non-mobile); the mobile evidence is 3–7B (UI-S1, Digi-Q, GUI-Owl). Our own v4.2 (self-history SFT, wrong steps patched with gold) matched v4 on seed 30 (18 vs 18), which fits this pattern.

### Cited Findings

**Effect sizes, offline or static-data methods (Reported unless "Ours")**

| Method (arXiv) | What the model learns from | Model | Benchmark: before → after | Data / compute | Teacher? |
|---|---|---|---|---|---|
| **Agentic-DPO** ([2607.10601](https://arxiv.org/abs/2607.10601)) | Own one-step mistakes at expert states (rejected) vs expert action (chosen); DPO + 0.5 × SFT anchor | **Qwen3.5-2B** | Mind2Web step SR 35.4 → 52.3; τ-bench 18.0 → 35.2 (above online GRPO 32.1) | K = 2–4 samples/state; ~1.6× SFT cost per step | None |
| **UI-S1 semi-online RL** ([2509.11543](https://arxiv.org/abs/2509.11543)) | Own history rolled over gold screens; patched on mismatch | Qwen2.5-VL-3B / 7B | AW 5.0 → 13.1 (3B, no SFT); 21.7 → 34.0 (7B after SFT); 200 trajectories already gave 24.0 at 7B | 4 × 8 GPUs, 5 epochs | None |
| **Digi-Q** ([2502.15760](https://arxiv.org/abs/2502.15760)) | Offline TD-learned Q-function on frozen VLM features; policy imitates best-of-16 own samples ranked by Q, only if advantage > 0 | Paper text names LLaVA-1.5-7B and also "the 3B VLM" for the Q-function (inconsistent in extraction) | AitW General test: **71.2** vs offline DigiRL 59.0, filtered BC 54.5, SFT (AutoUI) 22.9. Web Shopping: 58.0 vs 47.6 / 43.8 / 25.0 | 1,008 (General) / 1,296 (Web Shopping) offline trajectories; 0.14–0.64 × 10¹⁸ FLOPs | None (dataset has outcome labels) |
| **GUI-Owl iterative online rejection sampling** ([2508.15144](https://arxiv.org/abs/2508.15144)) | Own rollouts filtered by critic, retrained each round | 7B | AW 35 → 39 → 48 → 51 over 3 rounds (+16) | Cloud environments; critic = step + trajectory consensus | In-house critic |
| **UI-Voyager RFT + GRSD** ([2603.24533](https://arxiv.org/abs/2603.24533)) | Rejection fine-tuning on own successes (3 rounds), then self-distillation of the successful action into failed contexts at SSIM-matched fork points | Qwen3-VL-4B | AW Pass@1 37 → **73.2** (3 RFT rounds) → **81.0** (GRSD); GRPO and PPO plateau at 76 | >7,000 tasks from **AW templates** (contaminated by our rule); adb rule verifier | None |
| **STEVE KTO** ([2503.12532](https://arxiv.org/abs/2503.12532)) | Step-verified good vs bad steps of own trajectories | Qwen2-VL-7B | WinAgentArena 7.1 (SFT) → 14.2 (KTO); ScreenSpot −1.7 (SFT) vs +0.3 (KTO) | 4,820 trajectories; GPT-4o step verifier | Paid verifier |
| **SEAgent adversarial imitation of failures** ([2508.04700](https://arxiv.org/abs/2508.04700)) | Pushes probability away from own failed actions (L_AI), added to GRPO on successes | UI-TARS-7B-DPO | VSCode: BC 23.2 → BC + L_AI 30.4; GRPO 34.8 → GRPO + L_AI 37.7 | Weight γ = 0.2 best; γ 0.5 → 26.1, γ 0.8 → 23.1 | Open judge (see Q3) |
| **GHD** ([2608.06065](https://arxiv.org/abs/2608.06065)) | Same model, shown the next gold screen, distils into its failed steps during GRPO | 7B / 8B | AW 46.55 → 52.73; 59.05 → 66.47 (plain GRPO +0.6 / +2.3) | GRPO stack; code not released | None |
| **v4.2 self-history SFT** (ours) | Own predicted (intent, action) history on training episodes; wrong steps replaced by gold | LFM3-VL-2B | AW seed 30: v4 18 → v4.2 **18**; v4.1 12 | One 1,250-step LoRA SFT | None |
| **v4-RL static GRPO** (ours) | 4 samples/state, LoRA r16, 200 steps | LFM3-VL-2B | AndroidControl step acc 0.728 → **0.667**; 66% zero-variance groups, 60% terminal states | 0.95 A100-h | None |

- Digi-Q's best-of-N extraction: "N = 16 action token sequences are sampled from the behavior-cloned policy, ranked according to the Q-values … and the policy is trained to imitate the highest Q-value action as long as this best action attains a positive advantage" — [Digi-Q](https://arxiv.org/abs/2502.15760).
- Digi-Q's Q-function is trained "using offline temporal-difference (TD) learning on top of frozen, intermediate-layer representations of a VLM that has gone through an initial phase of representation fine-tuning" — [Digi-Q](https://arxiv.org/abs/2502.15760).
- UI-Voyager's fork points use "SSIM matching with a similarity threshold θ, preceded by mean-hash pre-filtering (hash similarity below 0.80)" — [UI-Voyager](https://arxiv.org/abs/2603.24533).
- SEAgent's L_AI is `−log π_θ(a|s,I) / π_ref(a_F|s,I)` over failed actions a_F, combined as L_GRPO + γ L_AI — [SEAgent](https://arxiv.org/abs/2508.04700).
- Agentic-DPO failure cases (from our earlier report): 0% accuracy without SFT warm-up at 2B/4B; −14 to −18 points without the SFT anchor; 2B overfits after its best refresh round — [Agentic-DPO](https://arxiv.org/abs/2607.10601).
- UI-TARS-2 flywheel: rollouts with V(s) = 1 go to the next SFT set, V(s) = 0 go to the continual-pre-training set — [UI-TARS-2](https://arxiv.org/abs/2509.02544).

### Inferences
- **The common factor in the big offline gains is a contrast at the same state.** Agentic-DPO (own wrong vs gold), Digi-Q (own best vs own rest), GRSD (own success vs own failure at a fork point), SEAgent L_AI and KTO all compare two actions at one state. Plain re-imitation of own correct steps (v4.2, filtered BC) adds less: Digi-Q beats filtered BC by 16.7 points on the same 1k trajectories.
- **v4.2's null result is consistent with this.** It removed the copy-history mismatch but gave the model no signal about its own wrong outputs (they were patched out). Agentic-DPO is the closest drop-in fix and reuses the v4.2 replay states.
- **Digi-Q is attractive in principle but not in one day.** It needs a representation-fine-tuning stage, a TD-trained value head and outcome-labelled offline trajectories. Our static datasets have no failures, so the Q-function would see no negative outcomes (inference).
- **UI-Voyager's 37 → 73 shows iterative RFT can be very strong at 4B, but only in-distribution.** Its 7,000 tasks are AW templates; under our rule it is an upper bound for "train on the test environment", not a transfer estimate.

### Gaps
- No offline own-sample method reports AW or MW at ≤2B. Agentic-DPO's 2B result is on Mind2Web/τ-bench.
- Digi-Q's exact policy and Q-function backbone sizes were inconsistent in the extracted text (LLaVA-1.5-7B vs "3B VLM"); not resolved.
- No paper ablates KTO vs DPO on mobile at ≤4B.
- ARPO and DigiRL "offline parts": Digi-Q reports offline DigiRL (59.0 General test); DigiRL's own offline-only table was not re-extracted here.

---

## Q2. Online learning from rollouts in real apps with self-generated tasks and self/open-VLM verification: effect sizes at 2–8B, trajectories needed, transfer to unseen apps

### Takeaway
Online self-generated-task methods report large in-domain gains (WebRL +38 at 8B, SEAgent +23 at 7B, UI-Voyager +44 at 4B), but each needed hundreds to thousands of tasks, many parallel environments and either a paid model or a strong open judge. When the evaluation apps or tasks were *not* trained on, gains shrank to +0.5 to +8 points. With two emulators, we can reach DigiRL/OS-Genesis scale (~1–2k episodes), not WebRL/ARPO scale.

### Cited Findings

**Effect sizes (Reported)**

| Method (arXiv) | Task source | Verifier | Model | Result | Scale |
|---|---|---|---|---|---|
| **ZeroGUI** ([2505.23762](https://arxiv.org/abs/2505.23762)) | VLM-generated tasks (GPT-4o) | Qwen2.5-VL-32B judge, voting | UI-TARS-7B-DPO | AndroidLab 45.7 → **46.4** (generated tasks only) → 47.5 (+ test-time training on test tasks). OSWorld 17.7 → 18.2 → 20.2. Aguvis-7B OSWorld 3.0 → 4.1 → 4.9 | 225 Android tasks (175 used); group size 64; 16k sequences per step |
| **ARPO** ([2505.16282](https://arxiv.org/abs/2505.16282)) | 128 OSWorld tasks with ≥1 success in 16 rollouts | OSWorld checkers | UI-TARS-1.5-7B | OSWorld 23.5 → 29.9; in-domain 43.8 → 68.8 (GRPO) → **81.25** (ARPO); out-of-domain 55.2 → **52.08 (GRPO)** → 56.3 (ARPO) | 8 rollouts/task; 256 parallel envs; 1.2 h/epoch with 256 envs vs >6 h with 8 |
| **SEAgent** ([2508.04700](https://arxiv.org/abs/2508.04700)) | Curriculum from Qwen2.5-72B + guidebook | Fine-tuned Qwen2.5-VL-7B "World State Model" | UI-TARS-7B-DPO | OSWorld 5 apps 11.3 → **34.5** (specialist-to-generalist); e.g., Writer 4.35 → 31.8 | ~100–300 successes per app per phase, 4 phases; 3.5K successes distilled; 8 × A100-80GB |
| **WebRL** ([2411.02337](https://arxiv.org/abs/2411.02337)) | New tasks evolved from own failures, kept if critic score in 0.05–0.75 | Trained ORM (80.8% test accuracy) | Llama-3.1-8B / GLM-4-9B | WebArena-Lite 4.8 → **42.4** / 6.1 → **43.0** | 8 phases × 500 tasks; GPT-4o filters infeasible tasks |
| **NNetNav** ([2410.02907](https://arxiv.org/abs/2410.02907)) | Exploration first, instructions written in hindsight | Open Llama-3.1-70B labeler + ORM pruning | Llama-3.1-8B | WebArena 1.0 → 16.3; WebVoyager 4.4 → 35.2; vs instruction-first synthetic data: MiniWoB++ 0.48 vs 0.28, WebArena 7.2 vs 4.2 | >10,000 demos (~100k transitions), 20 sites; 4 × H100 |
| **Learn-by-Interact** ([2501.10893](https://arxiv.org/abs/2501.10893)) | Backward construction: instructions rewritten from sub-trajectories | LLM committee (Claude-3.5, Gemini-1.5) | Codegemma-7B / Codestral-22B | OSWorld 0.0 → 6.5 / 2.2 → 11.7; WebArena (22B) 4.7 → 24.2 | 1,125 raw OSWorld trajectories → 11,782 filtered examples |
| **Explorer** ([2502.11357](https://arxiv.org/abs/2502.11357)) | Exploration-driven web tasks | GPT-4o | Phi-3.5V-4B / Qwen2-VL-7B | Mind2Web-Live 2.4 → 18.1 / 14.5 → 19.3; MiniWoB++ 35.9 → 46.7 (4B) | $0.28 per successful trajectory (GPT-4o); total count garbled in extraction |
| **OS-Genesis** ([2412.19723](https://arxiv.org/abs/2412.19723)) | Reverse task synthesis from exploration | GPT-4o reward model | InternVL2-4B | AW 15.18 vs 4.02 for task-driven data | 1K trajectories |
| **AutoPlay** ([2509.25047](https://arxiv.org/abs/2509.25047)) | Exploration-grounded tasks on the **20 AW apps** | GPT-4o / Qwen2.5-VL-32B | Qwen2.5-VL-3B | AW 34.2; RL +5.7; 7B ablation 38.2 (explored) vs 28.8 (no exploration) | ~20k tasks; 32 H100 for RL |
| **UI-Genie** ([2505.21496](https://arxiv.org/abs/2505.21496)) | Reward-model-guided beam exploration | UI-Genie-RM (517k samples) | Qwen2.5-VL-3B | AndroidLab 28.8 after 3 rounds | 16k trajectories |
| **ClawGUI** ([2604.11784](https://arxiv.org/abs/2604.11784)) | MW containers | MW checkers | MAI-UI-2B | MW GUI 11.1 → 17.1 | 64 MW containers, 8 × A6000 (in-environment; forbidden for us) |
| **MAI-UI** ([2512.22047](https://arxiv.org/abs/2512.22047)) | Online RL, 35+ apps | Rules + MLLM judge | 2B / 8B | 2B +4.0 AW; 8B vanilla GRPO +1.8 vs +6.0 with curriculum, replay, repetition penalty | 32–512 envs; fewer envs "exhibit early saturation" |
| **UI-TARS-2** ([2509.02544](https://arxiv.org/abs/2509.02544)) | Data flywheel (SFT ← verified, CT ← rest) | ORM F1 83.8, "relatively high false positive rate" | ~230B MoE | AW 73.3 | Thousands of VMs |

**Transfer to apps not trained on (Reported)**

| Evidence | In-domain gain | Unseen-app / OOD gain |
|---|---|---|
| AndroidWorld-Generalization, GRPO ([2603.07432](https://arxiv.org/abs/2603.07432)) | +26.1 unseen instances | +15.7 unseen templates; **+8.3 unseen apps** |
| ARPO, UI-TARS-1.5-7B ([2505.16282](https://arxiv.org/abs/2505.16282)) | +37.4 (43.8 → 81.25) | **+1.1** (55.2 → 56.3); plain GRPO **−3.1** |
| ZeroGUI generated tasks only ([2505.23762](https://arxiv.org/abs/2505.23762)) | — | **+0.5** OSWorld, **+0.7** AndroidLab (UI-TARS-7B-DPO) |
| PhoneWorld app coverage ([2605.29486](https://arxiv.org/html/2605.29486)) | — | 5 → 34 training apps: AW 61.2 → 71.6 at 9B |

### Inferences
- **Scale gap.** Every online method with a double-digit gain used ≥500 tasks per phase or ≥64 parallel environments. Our two emulators give ~1.5–2.4k episodes per day (Q5). That is DigiRL / OS-Genesis / UI-S1-200-trajectory scale, enough for one filtered-SFT or DPO round, not for iterative GRPO.
- **Expect small transfer.** Our target apps (AW, MW) are, by rule, not the apps we can train on. The best reported unseen-app transfer is +8.3 (GRPO, many tasks); ZeroGUI's generated-task-only gain is under 1 point. A realistic expectation for one day on non-AW/MW apps is 0 to +3 AW tasks out of 116, i.e., inside seed noise (inference).
- **What does transfer is behaviour, not app knowledge.** Loop avoidance, stopping, answering and recovery are app-independent. Own-attempt data should therefore be mined for those behaviours (repeated intents, `wait` under non-wait intents, false `complete`), not for app coverage.
- **Hindsight relabelling with an open model works at 8B on web.** NNetNav used only open weights (70B labeler) and beat instruction-first synthesis (7.2 vs 4.2 WebArena in the controlled run). This is the strongest teacher-free evidence for "label what the rollout actually did".

### Gaps
- No method in this list reports a ≤2B *mobile* model trained only on self-generated tasks in non-benchmark apps and evaluated on AW or MW.
- ZeroGUI's offline-RFT vs online-RFT vs RL comparison (its Table 4) was again not extracted; only Tables 1–3 were.
- Explorer's exact successful-trajectory count was garbled in the extraction ("9,494K" of "175K"); check the paper before quoting a count.
- I did not find GSAR's numbers (EMNLP 2026, goal-state-anchor rewards with self-evolving synthesis); the PDF timed out.

---

## Q3. Reward without a paid teacher or benchmark checkers: which signal is reliable enough at our scale?

### Takeaway
Programmatic adb state checks are the only signal with reported training results clearly better than judges (AW GRPO: rule 36.8 vs best judge 30.2 vs Qwen judge 26.4 at 7B). Open VLM judges reach ~80–86% accuracy but are false-positive heavy, and at our ~15% success base rate that makes a large share of "verified successes" wrong. Use adb checks for rewards; use open models only for hindsight *labels* that an adb state diff can confirm.

### Cited Findings

**Training with rule vs judge rewards (Reported)**

| Setup | Rule / checker | Judge rewards | Source |
|---|---|---|---|
| GRPO on AW, UI-TARS-7B-SFT, full 116 tasks, best checkpoint | **36.8** | GPT-5-mini 30.2; GPT-5.2 27.9; **Qwen 26.4** | [MobileJudgeBench 2608.11434](https://arxiv.org/abs/2608.11434) |
| Same, easy set | 54.6 | 45.4 / 42.6 / 39.9 | [MobileJudgeBench](https://arxiv.org/abs/2608.11434) |
| SEAgent VSCode, SFT on judge-filtered successes | — | Qwen2.5-VL-72B judge: **10.1** (below the 13.0 base); fine-tuned 7B World State Model: 23.2 | [SEAgent](https://arxiv.org/abs/2508.04700) |
| ZeroGUI judge design (OSWorld) | — | SR 23.9 (last screen) → 25.6 (all screens) → 27.2 (all screens + voting); 24.0 if agent's response included | [ZeroGUI](https://arxiv.org/abs/2505.23762) |

**Judge accuracy (Reported)**

| Judge | Data | Accuracy / precision | Source |
|---|---|---|---|
| Qwen backend, simple baseline prompt | 931 human-labelled mobile trajectories, 68 apps | Accuracy 85.7%; precision 80.2%; errors 71 FP vs 7 FN | [MobileJudgeBench](https://arxiv.org/abs/2608.11434) |
| GPT-5.2 / Gemini | same | 90.8 / 90.9% accuracy; GPT precision 93.7% (FN-dominated) | [MobileJudgeBench](https://arxiv.org/abs/2608.11434) |
| Qwen2.5-VL-32B, ZeroGUI best design | OSWorld | Precision 61.5, recall 51.1 (worst design: 47.5 / 40.4) | [ZeroGUI](https://arxiv.org/abs/2505.23762) |
| Raw Qwen2.5-VL-72B / 7B | AgentRewardBench | Precision 26.2 / 25.4% | [SEAgent](https://arxiv.org/abs/2508.04700) |
| Fine-tuned Qwen2.5-VL-7B (World State Model) | AgentRewardBench / OSWorld-Full | 71.6 / 73.9% precision (GPT-4o 72.1 / 74.6) | [SEAgent](https://arxiv.org/abs/2508.04700) |
| WebRL ORM | WebArena-Lite | 80.8% (test), 79.4% (rollouts) | [WebRL](https://arxiv.org/abs/2411.02337) |
| UI-TARS-2 ORM | 300 in-house traces | F1 83.8, "relatively high false positive rate" | [UI-TARS-2](https://arxiv.org/abs/2509.02544) |
| GRADE (visual trajectory vs external guidelines) | 350 tasks, 94 commercial apps | 87.37% human agreement | [AndroidDaily 2605.27761](https://arxiv.org/abs/2605.27761) (via [paper list](https://github.com/OSU-NLP-Group/GUI-Agents-Paper-List)) |

**Judge failure modes (Reported)**
- Qwen-based judges are false-positive dominated: "constraint violation", "partial completion", "surface UI match". GPT-based judges fail by "last-frame anchoring" and "invisible state change" — [MobileJudgeBench](https://arxiv.org/abs/2608.11434).
- ZeroGUI: false positives "distort policy improvement" more than false negatives; judges are "misled by agent responses" — [ZeroGUI](https://arxiv.org/abs/2505.23762).

**Programmatic checks in practice (Reported)**
- UI-Voyager's verifier "check[s] application states using the Android Debug Bridge (adb command)" — [UI-Voyager](https://arxiv.org/abs/2603.24533).
- MobileWorld verifies through "backend DB, adb local-storage inspection and app callbacks" — [MobileWorld](https://arxiv.org/abs/2512.19432).

**Hindsight relabelling and self-consistency (Reported)**
- NNetNav relabels every 4 steps up to 40, prunes with an ORM, and re-annotates each state's action to match the new instruction; all components are zero-shot open LLMs (Llama-3.1-70B) — [NNetNav](https://arxiv.org/abs/2410.02907).
- Learn-by-Interact filters relabelled data by removing consecutive duplicate (action, observation) pairs and by unanimous committee vote — [Learn-by-Interact](https://arxiv.org/abs/2501.10893).
- GUI-RCPO turns agreement between sampled grounding regions into a self-supervised test-time reward — [GUI-RCPO 2508.05615](https://arxiv.org/abs/2508.05615). It applies to single-step grounding, not multi-step success.

### Inferences
- **Base-rate math for a judge at our success rate.** Suppose the judge has 90% recall and a 10% false-positive rate, and ~15% of our rollouts truly succeed. Then kept = 0.135 true + 0.085 false, so **~39% of "successes" are wrong**. At a 5% FP rate it is still ~24%. MobileJudgeBench's 80.2% precision was measured at its own (higher) base rate, so ours would be worse. A filtered-SFT set with a third wrong demonstrations is likely to teach false `complete`, our existing failure.
- **adb checks are cheap for the generic apps we may use** (engineering, not from a paper): `settings get system screen_brightness`, `settings get global airplane_mode_on`, `cmd wifi status`, `content query --uri content://com.android.contacts/...`, `dumpsys alarm`, `ls /sdcard/...`, `getprop`, and app SQLite on a rooted image. Each gives an exact reward for templated tasks.
- **State-diff hindsight relabelling.** Snapshot adb-readable state before and after an exploratory rollout. Any change (brightness 120 → 10, a new contact, a new alarm, a file renamed) becomes a templated instruction that is verified by construction. This is NNetNav-style relabelling with the labeler replaced by a diff. Loops produce no diff and drop out automatically.
- **Self-consistency is not a success signal for multi-step tasks.** It can only rank candidate actions at a state (as GUI-RCPO does for grounding).
- **If an open judge is used at all** (e.g., Qwen3-VL-8B on Colab, already used as a teacher), use it only where adb cannot see state (answer tasks, Chrome pages), with ZeroGUI's precision design: all screenshots, no agent text, unanimous k = 3.

### Gaps
- MobileJudgeBench's extraction says "Qwen" without the exact model size; I could not confirm which Qwen VL size gave 85.7%.
- No study reports judge precision for an open ≤8B VLM on mobile trajectories at a ~15% base rate.
- No published GUI paper uses adb state diffs as the hindsight labeler; this is my proposal.

---

## Q4. Known failure modes and the fixes that worked

### Takeaway
Our v4-RL failure (66% zero-variance groups, 60% terminal states, AC 0.728 → 0.667) is the documented GRPO failure for small agents. The fixes with numbers are: filter tasks/states to 0 < pass@k < 1, inject a cached success into all-fail groups, keep a KL term, keep an SFT anchor, and keep negative weight small. All of them are easier to get in a DPO/KTO-style pairwise loss than in GRPO.

### Cited Findings

| Failure mode | Evidence (Reported unless "Ours") | Fix that worked |
|---|---|---|
| **Zero-variance groups** | Ours: 66% of groups; "when every output … receive[s] the same reward … the resulting advantage … is zero" ([DAPO 2503.14476](https://arxiv.org/abs/2503.14476), as summarised in [ARPO](https://arxiv.org/abs/2505.16282)) | ARPO replay: inject a cached per-task success when all rollouts fail → in-domain 68.8 (GRPO) → 81.25; mean reward 0.65 → 0.75 ([ARPO](https://arxiv.org/abs/2505.16282)). DAPO dynamic sampling drops uniform-reward groups |
| **Too-easy / too-hard tasks** | 60% terminal states in our v4-RL (ours) | ARPO keeps only tasks with ≥1 success in 16 rollouts ([ARPO](https://arxiv.org/abs/2505.16282)); WebRL keeps generated tasks with critic score 0.05–0.75 ([WebRL](https://arxiv.org/abs/2411.02337)) |
| **Out-of-domain drop / forgetting** | ARPO: plain GRPO OOD 55.2 → 52.08; LiteGUI-2B: GRPO after on-policy distillation dropped OSWorld 11.56 → 6.56 ([LiteGUI 2605.07505](https://arxiv.org/abs/2605.07505)); WebRL lists "catastrophic forgetting" and "policy distribution drift" | KL to reference (GUI-Libra-3B: AW 25.2 at KL 1e-3 vs 21.7 at KL 0, [2602.22190](https://arxiv.org/abs/2602.22190)); WebRL KL + replay of past successes filtered by perplexity 1/0.95–1/0.5 ([WebRL](https://arxiv.org/abs/2411.02337)); ARPO replay recovered OOD to 56.3 |
| **Collapse without anchor** | Agentic-DPO: 0% without SFT warm-up at 2B/4B; −14 to −18 without the SFT term ([2607.10601](https://arxiv.org/abs/2607.10601)) | DPO + 0.5 × SFT loss on chosen; ≤1–2 refresh rounds |
| **Too much negative signal** | SEAgent γ = 0.5 → 26.1, γ = 0.8 → 23.1 vs 37.7 at γ = 0.2 ([SEAgent](https://arxiv.org/abs/2508.04700)); VeriGUI 50% failure rows lowered step SR 42.6 → 39.2 ([2604.05477](https://arxiv.org/abs/2604.05477)) | Small negative weight (γ ≈ 0.1–0.2); ≤30% failure rows |
| **Reward hacking / judge false positives** | Qwen judges 71 FP vs 7 FN ([MobileJudgeBench](https://arxiv.org/abs/2608.11434)); ORM "relatively high false positive rate" ([UI-TARS-2](https://arxiv.org/abs/2509.02544)) | Rule rewards (36.8 vs 26.4); judges: all screens + voting, no agent text ([ZeroGUI](https://arxiv.org/abs/2505.23762)); UI-TARS-2 found no substantial hacking on manual inspection |
| **Few environments saturate early** | MAI-UI: fewer environments "exhibit early saturation"; vanilla GRPO +1.8 vs +6.0 with curriculum, replay and repetition penalties at 8B ([MAI-UI](https://arxiv.org/abs/2512.22047)) | More envs (not available to us), curriculum, replay |
| **Loops not fixed by reward on gold action** | DeLoop: gold-action GRPO left loops at 52.7% (baseline 57.3%); own-rollout loop training cut loops to 6.1% with success 25.1 → 25.9 at 8B ([DeLoop 2610.19376](https://arxiv.org/abs/2610.19376)) | Train directly on own looping states |
| **Shortened / dropped reasoning** | Action-only SFT at 4B scored 31.0 vs 42.9 base ([MIRAGE 2606.04627](https://arxiv.org/abs/2606.04627)); UI-TARS-2 uses format rewards and length penalties ([UI-TARS-2](https://arxiv.org/abs/2509.02544)) | Keep the short `<think>` in chosen targets; no length reward |

### Inferences
- **Zero variance is structural in our static GRPO.** With binary reward and K samples, P(zero variance) = p^K + (1−p)^K. At K = 4 that is ≥ 0.5 whenever p ≤ 0.16 or p ≥ 0.84. Our states are bimodal (terminal screens near p = 1, hard states near p = 0), which explains 66%.
- **Step-level DPO with gold as "chosen" is the no-zero-variance version of GRPO** on static data: every state with one wrong own sample yields a pair. It also carries ARPO's "inject a success" idea by construction.
- **For own-rollout data, filter by pass@4 ∈ (0, 1) before any training**, as ARPO and our earlier report recommend. Tasks the model always solves teach nothing; tasks it never solves give no positive.
- **Keep negatives ≤ ~30% of pairs or loss weight**, and always mix the original SFT data (or the SFT anchor) to avoid the AC drop we saw in v4-RL.

### Gaps
- No ≤2B GUI paper reports the zero-variance fraction or a dynamic-sampling ablation.
- No GUI paper measures "shortened thought" collapse under DPO specifically.

---

## Q5. Throughput math: trajectories per day on two emulators, training steps per ~5 A100-hours, best use

### Takeaway
Two emulators give roughly **1,700 AW-length episodes per 20 hours**, or ~2,400 short (≤15-step) self-made episodes. With k = 4 samples per task that is ~400–600 tasks per day, and at a ~15% success rate ~250–400 verified successes (~2.5–4k steps). Five A100-hours buy about one full v4-sized SFT run plus one ~500-step DPO run, or two ~1,000-step SFT rounds. The binding resource is A100 time, not rollouts, so spend emulator time on own-attempt data and A100 time on one or two pairwise/filtered runs.

### Cited Findings (Ours)

| Quantity | Value | Source |
|---|---|---|
| v4 seed-30 run: steps / episodes | 1,706 steps / 116 episodes (mean 14.7, median 10) | [dev_seed30_summary.json](../../../../results/androidworld/dev_seed30_summary.json) |
| v4 step latency (Q4_K_M, llama.cpp) | median 2.96 s (p10 1.74, p90 4.63); prompt 1,303 tokens, output 22 tokens (medians) | same |
| v4.2 seed-30 wall time, 116 tasks, one emulator (two runs in parallel on the Mac) | 03:06 → 05:53 = **2 h 47 min** (~86 s/episode) | `logs/aw_run_lfm3vl2b_v42.log` (untracked) |
| v4 SFT, 1,250 × 32 rows, Colab A100 | ~2.7 h (~4.1 rows/s) | [training-on-own-mistakes report §6](../../training-on-own-mistakes-and-overfitting.md) |
| v4-RL GRPO, 200 steps | 0.95 h | same |
| Agentic-DPO cost per step | ~1.6× SFT (Reported) | [Agentic-DPO](https://arxiv.org/abs/2607.10601) |
| MW emulator stability | dies after ~64 snapshot loads (Reported) | [MW issue #48](https://github.com/Tongyi-MAI/MobileWorld/issues/48) |

### Inferences

**Rollouts (inference from the numbers above)**

| Item | Estimate |
|---|---|
| Per-episode overhead (reset, setup, teardown) | 86 s − 14.7 × ~3.1 s ≈ **~40 s** |
| AW-length episodes, 2 emulators | ~42/h each → **~84/h → ~1,700 per 20 h** |
| Self-made tasks with a 15-step cap (mean ~10 steps) | ~30 s steps + ~30–40 s reset ≈ 65 s → ~55/h each → **~2,200–2,400 per 20 h** |
| Tasks covered at k = 4 samples each | ~400–600 per day |
| Verified successes at 10–20% success | ~170–480 episodes ≈ **2–5k positive steps** (vs 92k SFT rows) |
| Fork-point / loop-state negatives | Every failed episode with a loop gives several (repeat-intent, `wait`) states → thousands of rejected samples |
| Offline K = 4 sampling on static states (no emulator) | ~1.5–3 s/sample on the Mac → ~1,200–2,400 samples/h per server; **~6k states × 4 in ~5–10 h**. On the A100 with batched HF generation it should take well under an hour (not measured) |

**A100 budget (~5 h)**

| Use | Steps | A100-h |
|---|---|---|
| Full v4-sized SFT round (1,250 × 32) | 1,250 | ~2.7 |
| Short RFT/SFT round mixing own successes into original data | ~600–800 | ~1.3–1.7 |
| Step-DPO (Agentic-DPO recipe), batch 32 pairs | ~500 | ~1.7 (= 500 steps × ~7.8 s per SFT step × 1.6) |
| Static GRPO (for comparison) | 200 | 0.95 (already failed) |
| Offline evals (AC test, SOP proxy, probes) + GGUF export | — | ~0.5 |

- **Best split (inference): ~1.7 h DPO + ~1.5 h RFT round + ~0.5 h evals + ~1 h slack** for Colab restarts. That leaves no room for a GRPO stack or a judge model beyond a short Qwen3-VL-8B session.
- **The Mac cannot do emulator rollouts and offline sampling at full speed at once** (both use the same CPU/GPU). Do offline sampling for DPO on the A100 or before the rollout window.
- **Synchronous online GRPO does not fit.** Groups of 8 on even 200 tasks = 1,600 episodes = a full day of emulators per update batch.

### Gaps
- LFM3-VL support and speed in vLLM / batched HF generation on the A100 were not measured.
- Real reset time for self-made tasks (snapshot load vs app-data clear) is unknown until measured; ~30–40 s is an estimate from the AW overhead.
- Emulator stability over thousands of snapshot loads on the Mac AVD is unknown (MW's ~64-load limit was on its Docker image).

---

## Q6. Which apps can host own-attempt rollouts without breaking the contamination rule?

### Takeaway
Use generic system apps (Settings, Clock, Contacts, Files, Chrome) with task text deduplicated against the 116 AW templates and the 105 MW tasks, plus a handful of offline F-Droid apps outside both benchmarks. Avoid Fossify Calendar/Gallery/File Manager (MW's Calendar is Fossify, and Fossify forks the Simple Mobile Tools line that AW's "Simple" apps come from).

### Cited Findings
- MW's apps include "Calendar (Fossify), Camera, Chrome, Clock, Contacts, Files, Gallery, Messages and Settings", plus self-hosted Mattermost, Mastodon and Mall4Uni — [MobileWorld](https://arxiv.org/abs/2512.19432) (as recorded in our [RL infrastructure notes](../small-gui-agent-training-methods/rl_infrastructure.md)).
- MW's English GUI-only app mix includes Settings 7, Chrome 7, Files 16, Contacts 5, Clock 3 tasks (own count) — [training-on-own-mistakes report §4](../../training-on-own-mistakes-and-overfitting.md).
- AndroidLab apps with no AW counterpart: Bluecoins, Cantook, Maps.me, PiMusic, Zoom; AndroidLab test tasks stay evaluation-only — [small-gui-agent-training-methods.md](../../small-gui-agent-training-methods.md); [AndroidLab 2410.24024](https://arxiv.org/abs/2410.24024).
- Fossify apps share package names across Google Play and F-Droid, and the suite includes Calendar, Gallery and File Manager — [fossify.org](https://www.fossify.org/).
- Fossify Notes "operates offline without internet permission" — [F-Droid: Fossify Notes](https://f-droid.org/en/packages/org.fossify.notes/).
- Other offline F-Droid candidates with checkable local state: [Loop Habit Tracker](https://f-droid.org/en/packages/org.isoron.uhabits/), [Table Habit](https://f-droid.org/en/packages/io.github.friesi23.mhabit/), [Organic Maps](https://f-droid.org/en/packages/app.organicmaps/); top-downloaded note/time-tracker apps include Quillpad, Simple Time Tracker and Track & Graph — [F-Droid top downloads](https://grote.gitlab.io/fdroid-metrics-distilled/).

### Inferences

| Pool | Tier | Reward source | Notes |
|---|---|---|---|
| Settings (brightness, airplane mode, Wi-Fi, display size, dark mode, ringtone volume) | Allowed generic; overlaps AW/MW task *types* | `settings get`, `cmd wifi`, `dumpsys` | Dedup task text (n-gram + embedding) against AW templates and MW tasks; report as "generic-app overlap" |
| Clock (alarms, timers, world clock) | Allowed generic | `dumpsys alarm`, app prefs on rooted image | Same dedup |
| Contacts (add / edit / star / delete) | Allowed generic | `content query` on the contacts provider | Same dedup |
| Files (create folder, rename, move) | Allowed generic | `ls` / `stat` on `/sdcard` | Same dedup |
| Chrome (open URL, search, bookmarks) | Allowed generic | Hard without network-state checks; answer tasks need a judge | Lowest priority |
| F-Droid offline apps not in AW/MW: Loop Habit Tracker, Table Habit, Simple Time Tracker, Track & Graph, Quillpad | Clean | App SQLite on a rooted image; exported files | Best "unseen app" pool; 3–5 apps is enough for one day |
| Organic Maps | Clean app, but same task family as AW's OsmAnd | Bookmarks DB / KML export | Use with care; large offline map download |
| Fossify Notes / other Fossify apps | Clean by name, but same UI lineage as AW "Simple" apps and MW's Fossify Calendar | App DB | Avoid, or disclose as UI-lineage overlap |
| AndroidLab non-AW apps (Bluecoins, Cantook, Maps.me, PiMusic, Zoom) | Clean for AW/MW; AndroidLab test tasks stay eval-only | AndroidLab-style UI-tree sub-goals or app DB | Needs AndroidLab's AVD image |
| AW's bundled MiniWoB++ suite | Permitted by the earlier project rule table, but it ships inside AW; **confirm with the owner** | Built-in rule rewards | Zero engineering; UI-S1 SFT *lowered* MiniWob++ 54.0 → 46.7, so it is a weak proxy for app tasks ([UI-S1](https://arxiv.org/abs/2509.11543)) |
| Mastodon / Mattermost (own servers) | Separate, disclosed claim only | DB queries | Not for the main claim |

### Gaps
- I did not verify which F-Droid apps run cleanly on our exact AVD image/API level, or whether their databases are readable without root.
- Whether AW's MiniWoB++ suite counts as an "AndroidWorld task" under the current rule is a project decision, not a research question.

---

## Q7. Ranked recommendation for ~1 day, two Mac emulators and ~5 A100-hours

### Takeaway
1. **Step-DPO on own wrong samples at self-history states** (Agentic-DPO recipe, loop- and stop-targeted pairs): strongest small-model evidence, no emulator, ~2 A100-h.
2. **One round of verified own-rollout data on clean apps** (adb-checked self-made tasks, k = 4, pass@4 ∈ (0, 1)), used as filtered SFT plus fork-point/loop pairs: ~1.5 A100-h, all emulator time.
3. **Only if budget remains:** open-VLM hindsight labels for answer tasks. Skip online GRPO, full UI-S1 RL, Digi-Q, ZeroGUI, SEAgent, WebRL-style curricula.

### Cited Findings
- Agentic-DPO at 2B: 35.4 → 52.3 Mind2Web step SR; beats online GRPO on τ-bench (35.2 vs 32.1) — [Agentic-DPO](https://arxiv.org/abs/2607.10601).
- Contrast-at-the-same-state methods beat plain re-imitation: Digi-Q 71.2 vs filtered BC 54.5 on the same ~1k trajectories — [Digi-Q](https://arxiv.org/abs/2502.15760); GRSD 81.0 vs RFT 73.2 and GRPO/PPO 76 — [UI-Voyager](https://arxiv.org/abs/2603.24533).
- Own-rollout loop training cut loops 57.3% → 6.1% (success +0.8) at 8B — [DeLoop](https://arxiv.org/abs/2610.19376).
- Rule rewards beat judges in training (36.8 vs 26.4 with a Qwen judge) — [MobileJudgeBench](https://arxiv.org/abs/2608.11434).
- Self-history SFT alone (v4.2) did not move seed 30 (18 vs 18) — ours, [PREREG_v41.md](../../../PREREG_v41.md) context.
- Online self-generated-task gains transfer weakly: +0.5–0.7 (ZeroGUI), +1.1 OOD (ARPO), +8.3 unseen apps (GRPO, many tasks) — [ZeroGUI](https://arxiv.org/abs/2505.23762), [ARPO](https://arxiv.org/abs/2505.16282), [AndroidWorld-Generalization](https://arxiv.org/abs/2603.07432).

### Inferences

**Ranked plan**

| Rank | Method | Data source | Reward | A100-h | Mac / emulators | Expected effect (inference) | Main risk |
|---|---|---|---|---|---|---|---|
| **1** | **Step-DPO, Agentic-DPO recipe**: chosen = gold step; rejected = own sample that differs (K = 4, T ≈ 0.8). Over-sample states where the rejected is `wait` under a non-wait gold, a copied intent, or an early `complete`. λ = 0.5 SFT anchor, small β, 1 refresh at most | v4.2 self-history states on AC / GUI-Odyssey / AMEX train episodes (states already exist) | Gold action match (no judge) | ~0.3 sampling + ~1.7 training | none | Fewer copied intents and `wait`s; 0 to +3 AW tasks on seed 30; AC within ~2 pts | 2B overfit after best round; AC regressions if anchor dropped |
| **2** | **One own-rollout round on clean apps**: 50–100 templated tasks (Settings, Clock, Contacts, Files + 3–5 offline F-Droid apps), k = 4 each at T ≈ 0.7; keep tasks with pass@4 ∈ (0, 1). Train on (a) verified successes, shortest first; (b) the correct prefix of failures up to the first loop; (c) fork-point pairs (success vs failure at an SSIM-matched screen) and own loop steps as rejected | ~1,500–2,000 episodes in ~20 h on two emulators | **adb state checks**; state-diff hindsight relabels for exploratory runs | ~1.5 (mixed into original SFT data at ≤ ~20% share, or added as DPO pairs) | both emulators, full day | Large gains on the trained apps; 0 to +3 AW / MW from behaviour transfer | Engineering time for tasks and checks (~½ day); emulator instability |
| **3** | Open-VLM hindsight labels (Qwen3-VL-8B on Colab) for answer tasks and Chrome | Rank-2 rollouts | Judge with all screens, no agent text, unanimous k = 3 | ~0.5 | — | Small; adds answer supervision | FP-heavy judges at a ~15% base rate (~25–40% wrong "successes") |
| Skip | Online GRPO / ARPO / ZeroGUI | — | — | ≥ 5 | ≥ 64 envs in published runs | Saturates with few envs (MAI-UI) | Zero-variance, as in v4-RL |
| Skip | Full UI-S1 semi-online RL, GHD | — | — | ≥ 10 | — | +6 to +12 at 7B | verl port, 32 GPUs in the paper |
| Skip | Digi-Q | — | — | several | — | +16.7 over filtered BC at AitW | Needs outcome-labelled failures and a TD value head |
| Skip | SEAgent / WebRL-style curricula | — | — | ≥ 8 | 8 × A100 | +23 to +38 in-domain | Open 72B curriculum model; many phases |

**One-day schedule (inference)**

| Window | A100 | Mac + 2 emulators |
|---|---|---|
| 0–4 h | Batched K = 4 sampling on v4.2 states; build DPO pairs | Write 50–100 task templates + adb checks; smoke-test 10 tasks; measure reset time |
| 4–8 h | Step-DPO run (~500 steps) + AC/SOP/probe evals | Rollouts start (k = 4, T ≈ 0.7) |
| 8–20 h | idle (save units) | Rollouts continue (~1,500–2,000 episodes) |
| 20–23 h | RFT/DPO round on own-rollout data mixed with original SFT | Seed-30 dev runs of DPO model (run 1) vs v4.2, paired |
| 23–24 h | GGUF export | Seed-30 run of round-2 model |

**Decision rules (inference)**
- Promote a model only if the loop monitors (intent-repeat rate, `wait` under non-wait intents, cap-hit tasks) fall **and** AC step accuracy stays within ~2 points of v4.
- Report seed-30 results as development numbers; the seed-varying template subset separately; sealed seeds stay sealed until a version is frozen.
- Label rank-2 data in the model card by tier: "generic system apps (task text deduplicated against AW/MW)" and "clean F-Droid apps".

### Gaps
- No published 2B mobile result for any of the three ranked methods; all expected effects above are extrapolations.
- The one-day plan assumes LFM3-VL batched generation works on the A100 in TRL/HF; if not, offline sampling moves to the Mac and competes with rollouts.
- How many of the ~2k rollouts will contain usable fork points is unknown; UI-Voyager does not report fork-point yield.
