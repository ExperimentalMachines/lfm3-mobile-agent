# Online (on-policy, in-environment) RL for Android/mobile GUI agents — what works at <=2-4B, and what is feasible for LFM3-VL-2B

Scope note: primary sources are arXiv technical reports (2024-11/2026). Numbers are AndroidWorld (AW, 116 tasks) success rate (SR, %) unless stated. "SFT->RL" deltas are the paper's own ablations. Our reference point: LFM3-VL-2B LoRA-SFT = 15/116 (12.9%), GUI-Owl-1.5-2B = 23/116 (19.8%) under our 1-screenshot harness.

## 1. Algorithms, rewards, and AW gains over the SFT start (DigiRL, DistRL, UI-TARS-2, MobileRL, ZeroGUI, GUI-Owl/MRPO, AgentCPM-GUI, UI-Venus, ARPO, 2025-2026 successors)

### Takeaway
The field converged on GRPO-family critic-free RL (DAPO-style clip-higher, no or tiny KL, dynamic/curriculum task filtering, replay of successful trajectories) with binary task-success rewards from rule-based verifiers (AW/AndroidLab-style state checks) plus MLLM judges for unverifiable tasks; PPO with a pretrained value model (UI-TARS-2) and step-level credit schemes (GiGPO, PRMs, milestones, fork-point self-distillation) are the main alternatives. Online RL on top of a good SFT model typically adds +4 to +15 AW points; plain GRPO with no extras adds much less (+1.8 in MAI-UI's ablation).

### Cited Findings
**First generation (AitW, pre-AndroidWorld)**
- DigiRL: 1.3B VLM, two stages (offline RL init, then offline-to-online RL), advantage-weighted RL with stochasticity-aware advantage estimators, automatic curriculum, VLM-based evaluator for reward. On AitW: 17.7% (SFT on static demos) -> 67.2%. The prior best autonomous RL baseline, filtered behavior cloning, reached 57.8%. — [DigiRL, arXiv 2406.11896](https://arxiv.org/abs/2406.11896)
- DistRL: centralized training with decentralized (multi-machine, asynchronous) data collection and a custom off-policy algorithm that prioritizes collected data. Reports 3x training efficiency, 2.4x faster data collection than synchronous multi-machine methods, and +20% relative success on general Android tasks (AitW). — [DistRL, arXiv 2410.14803](https://arxiv.org/abs/2410.14803)

**Large-lab online RL with AW numbers**
- UI-TARS-2 (~230B MoE per MAI-UI's table): multi-turn **PPO** (it reports PPO beating GRPO "by a clear margin"), with:
  - Decoupled GAE, Length-Adaptive GAE (alpha=0.05), value-model pretraining, and clip-higher.
  - Rewards: rule verifiers where possible, LLM-as-judge for browsing, and UI-TARS-2 itself as a generative ORM (last 5 screenshots plus text history) for non-verifiable tasks.
  - "Format rewards and length penalties to discourage premature termination or infinite continuation."
  - Final AW = 73.3. — [UI-TARS-2, arXiv 2509.02544](https://arxiv.org/abs/2509.02544)
- MobileRL (AdaGRPO): GRPO plus three additions:
  - Difficulty-adaptive positive replay (AdaPR).
  - Failure curriculum filtering (FCF).
  - Shortest-path reward adjustment (SPA), which rewards shorter successful trajectories.

  Hyperparameters: verl, group n=16, max 50 turns, KL 0.001, lr 1e-6. Stage-wise AW gains:

  | Backbone | Reasoning-free SFT | Reasoning SFT | AdaGRPO |
  |---|---|---|---|
  | Qwen2.5-VL-7B | 27.6 -> 50.2 | 56.8 | 72.0 (+15.2) |
  | GLM-4.1V-9B | 7.7 -> 48.1 | 66.2 | 80.2 (+14.0) |

  Ablation (7B): full 71.1; w/o AdaPR 63.6; w/o SPA 69.1; w/o FCF 64.8; no RL 56.8. — [MobileRL, arXiv 2509.18119](https://arxiv.org/abs/2509.18119)
- MAI-UI (Qwen3-VL-based, 2B/8B/32B/235B):
  - Algorithm: GRPO with group size 16, DAPO clip-higher (0.2/0.3), token-level loss, no KL. Additions: a pass@K-stratified 4-level difficulty curriculum, a success-trajectory replay buffer, and an action-level **repetition penalty** covering single repeated actions and 3-5-action cycles.
  - Reward: binary task completion from rule verifiers (root AVD access) or MLLM-as-judge; the hybrid verifier has 83% agreement with humans.
  - SFT -> RL on AW: 2B 45.1 -> 49.1 (+4.0); 8B 64.7 -> 70.7 (+6.0); 32B 69.8 -> 73.3 (+3.5).
  - Standard GRPO alone gave only +1.8 on 8B. — [MAI-UI, arXiv 2512.22047](https://arxiv.org/abs/2512.22047)
- GUI-Owl / Mobile-Agent-v3: introduces TRPO (Trajectory-aware Relative Policy Optimization) for online RL with fully asynchronous training. The abstract reports TRPO's result on OSWorld (34.9). GUI-Owl-7B reaches 66.4 on AW, and the Mobile-Agent-v3 framework reaches 73.3. — [Mobile-Agent-v3, arXiv 2508.15144](https://arxiv.org/abs/2508.15144)
- GUI-Owl-1.5 / Mobile-Agent-v3.5 (2B/4B/8B/32B/235B, Qwen3-VL). Its RL algorithm is MRPO (Multi-platform Reinforcement Policy Optimization):
  - A single device-conditioned policy across platforms.
  - An "online rollout buffer" that oversamples and selects diverse groups to avoid GRPO groups collapsing to identical outcomes, while staying on-policy.
  - Token-ID transport to avoid tokenizer mismatch between rollout and training.
  - Alternating per-platform training to reduce gradient interference.
  - "Unstable-set" task selection from multi-round rollouts.

  Table 1 lists GUI-Owl-1.5-2B-Instruct at 67.9 on AW and 31.3 on MobileWorld; 4B-Instruct 69.8; 8B-Instruct 69.0; 8B-Thinking 71.6. The 2B/4B values were extracted by a fetch tool from the HTML table, so re-verify. — [Mobile-Agent-v3.5, arXiv 2602.16855](https://arxiv.org/abs/2602.16855); [HTML Table 1](https://arxiv.org/html/2602.16855v1)
- UI-Venus-1.5 (2B/8B/30B-A3B, Qwen3-VL): pipeline is Mid-Training -> Offline-RL (GRPO with format + action-type + coordinate/content step rewards) -> Online-RL (full-trajectory rollouts on a "Device-as-a-Service" layer) -> model merge. AW per stage:

  | Model | Mid-train | Offline-RL | Online-RL | Merge |
  |---|---|---|---|---|
  | 2B | 39.0 | 45.3 | 59.8 (+14.5) | 55.6 (-4.2) |
  | 8B | 57.0 | 63.5 | 72.7 (+9.2) | 73.7 |
  | 30B-A3B | 67.1 | 68.0 | 75.5 (+7.5) | 77.6 |

  Also: offline step-level RL raised step accuracy but trace-level success "peaks and then declines". — [UI-Venus-1.5, arXiv 2602.09082](https://arxiv.org/abs/2602.09082)
- ZeroGUI: GPT-4o generates tasks from current screens; a Qwen2.5-VL-32B judge votes 4 times (unanimous); two-stage online GRPO (G=64, DAPO dynamic sampling, k2-KL instead of k3) runs first on generated tasks and then test-time training on the test tasks.
  - UI-TARS-7B-DPO on AndroidLab: 45.7 -> 47.5 (+1.8); operation subset +2.8.
  - OSWorld: 17.7 -> 20.2.
  - Aguvis-7B OSWorld: 3.0 -> 4.9.
  - Ablation on the OSWorld Daily domain: offline RFT 22.4, online RFT 24.5, online RL 27.2. — [ZeroGUI, arXiv 2505.23762](https://arxiv.org/abs/2505.23762)
- AgentCPM-GUI (8B): grounding pretraining -> SFT -> reinforcement fine-tuning with GRPO, reported on offline benchmarks (AndroidControl/CAGUI, 91.3% exact match on CAGUI), so it is not online RL. — [AgentCPM-GUI, arXiv 2506.01391](https://arxiv.org/abs/2506.01391)
- ARPO: GRPO plus a replay buffer of successful experience plus task selection by baseline success, on OSWorld (desktop, UI-TARS-1.5-7B). — [ARPO, arXiv 2505.16282](https://arxiv.org/abs/2505.16282)

**2025-2026 successors (credit assignment, sample efficiency)**
- AndroidWorld-Generalization (open-source system): GRPO with containerized async rollouts, UI-TARS-7B-SFT base, curriculum easy -> medium -> all, rule-based reward. AW 23.0 -> 49.1 (+26.1); without curriculum 45.1. PPO with token-level GAE shows the same trends. — [arXiv 2603.07432](https://arxiv.org/abs/2603.07432)
- SoLS (off-policy actor-critic): direct updates on positive-advantage samples and clipped/conservative updates on negative ones, plus Successful Transition Replay. Llama-3-8B (text-only UI-tree input; LoRA used at least for the SFT stage) on an 80-task AW subset: SFT 22.1; PPO 28.3; A2C-STR 32.1; DigiRL-STR 38.8; SoLS-STR 51.3. — [SoLS, arXiv 2509.01720](https://arxiv.org/abs/2509.01720)
- UI-Voyager (Qwen3-VL-4B):
  - Stage 1 is multi-round rejection fine-tuning (RFT).
  - Stage 2 is Group Relative Self-Distillation (GRSD). It finds "fork points" where a failed and a successful rollout share a screen (SSIM), then trains SFT-style on the failed context with the successful action. It replaces GRPO/PPO.
  - RFT round 3 = 73.2 pass@1; final 81.0.
  - GRPO/PPO started directly from base Qwen3-VL-4B needed ~175 steps to match one RFT round (64.0%). — [UI-Voyager, arXiv 2603.24533](https://arxiv.org/abs/2603.24533)
- ClawGUI-RL (open-source, verl + verl-agent): GiGPO (anchor-state step-level grouping) plus a process reward model (Qwen3.5-72B judge on previous/current screenshot plus history), with R = R_outcome + R_step. From MAI-UI-2B on MobileWorld GUI-only: 11.1 -> 17.1 (GiGPO+PRM) vs 14.5 (binary GRPO). — [ClawGUI, arXiv 2604.11784](https://arxiv.org/abs/2604.11784)
- ADMIRE (adaptive milestone reward, GRPO). Milestones are distilled from successful explorations; the reward is asymmetric: only milestone steps are rewarded in successful trajectories, while failed ones get a progress (k/K) scaffold.
  - Qwen2.5-VL-3B on AW: 18.1 base -> 26.7 (outcome reward), 27.5 (process reward), 31.0 (ADMIRE).
  - 7B: 32.8 -> 39.7 / 36.2 / 44.0. — [ADMIRE, arXiv 2602.11524](https://arxiv.org/abs/2602.11524)
- GUI-Shepherd PRM: +7.7 AW points via multi-turn online PPO vs ORM-based competitors. — [arXiv 2509.23738](https://arxiv.org/abs/2509.23738)
- Android Coach (Single-State-Multiple-Actions with a learned critic + PRM): +8.3 AW and +7.5 AndroidLab over UI-TARS-1.5-7B; 1.4x training efficiency vs PPO/GRPO at matched success. — [arXiv 2604.07277](https://arxiv.org/abs/2604.07277)
- UI-S1 "semi-online RL": simulates online rollouts on offline trajectories, with a Patch Module to recover divergence and discounted future returns; +12.0 AW over base at 7B. — [UI-S1, arXiv 2509.11543](https://arxiv.org/abs/2509.11543)
- DART-GUI-7B (decoupled async RL, OSWorld): 42.13%, +14.61 absolute over base. — [arXiv 2509.23866](https://arxiv.org/abs/2509.23866)
- PhoneBuddy: AW 60.3 (SFT) -> 77.2 (real-app RL) -> 83.2 (mixed real + mock-app RL). — [arXiv 2606.23049](https://arxiv.org/abs/2606.23049)
- Other self-reported AW results, not independently verified:
  - BlueLM-GUI (35B-A3B, RL on hundreds of real phones): 84.9 AW. — [arXiv 2609.12394](https://arxiv.org/abs/2609.12394)
  - OpenMobile-2: 79.9 AW and 50.4 MobileWorld. — [arXiv 2610.14157](https://arxiv.org/abs/2610.14157)
  - MAI-Gym-9B: 78.4 MobileWorld. — [arXiv 2610.20939](https://arxiv.org/abs/2610.20939)

### Inferences
- The consistent recipe at every scale is SFT (ideally with reasoning traces) followed by curriculum-filtered, replay-augmented GRPO with binary verifiable rewards. The "extras" (curriculum, replay, repetition/length shaping) account for most of the gain: MAI-UI got +1.8 from vanilla GRPO vs +6.0 with them, and MobileRL lost 7.5-14.3 points when components were ablated.
- Step-level credit methods (GiGPO, ADMIRE, PRM, GRSD) add roughly 2-5 points over outcome-only GRPO at 2-7B. GRSD and RFT are notable because their losses are plain SFT losses, so they reuse an existing LoRA-SFT stack.

### Gaps
- TRPO internals (how trajectory reward is spread over steps) were not verified from the GUI-Owl paper text. MRPO's environment count, GPU count, and RL-over-SFT delta at 2B are not given in the parts read.
- UI-TARS-2 does not report an AW SFT -> RL ablation in the passages retrieved.
- DigiRL/DistRL compute numbers were not retrieved, and neither reports AndroidWorld.
- ARPO's exact OSWorld numbers were not retrieved.

## 2. Results at 1-4B scale: how much does online RL add over SFT?

### Takeaway
There is direct evidence of online-RL gains at ~2-4B:
- MAI-UI-2B +4.0 (45.1 -> 49.1) and UI-Venus-1.5-2B +14.5 (45.3 -> 59.8, before merging).
- ADMIRE Qwen2.5-VL-3B +8.6 to +12.9 (from 18.1).
- ClawGUI-2B +6.0 on MobileWorld.
- MobileGym Qwen3-VL-4B +12.8 (on its own benchmark).
- Ferret-UI Lite 3B +3 from step-level (non-environment) RLVR.

Gains are largest when the starting policy is weak-to-moderate and train/test share task templates. They are smallest on the hardest tasks.

### Cited Findings
| Model (size) | RL type | Start -> after RL | Source |
|---|---|---|---|
| MAI-UI-2B (Qwen3-VL-2B) | Online GRPO + curriculum/replay/repetition penalty | AW 45.1 -> 49.1 | [2512.22047](https://arxiv.org/abs/2512.22047) |
| UI-Venus-1.5-2B | Online full-trajectory RL | AW 45.3 -> 59.8 (55.6 after merge) | [2602.09082](https://arxiv.org/abs/2602.09082) |
| ADMIRE w/ Qwen2.5-VL-3B (warm-up SFT) | Online GRPO, AW sandbox | AW 18.1 -> 26.7 (outcome) / 31.0 (milestone); MobileMiniWoB++ 52.1 -> 57.6 | [2602.11524](https://arxiv.org/abs/2602.11524) |
| ClawGUI-2B (from MAI-UI-2B) | Online GiGPO + PRM | MobileWorld GUI-only 11.1 -> 17.1 (GRPO: 14.5) | [2604.11784](https://arxiv.org/abs/2604.11784) |
| Qwen3-VL-4B-Instruct | Online GRPO in MobileGym (browser-sim apps), 10 steps | MobileGym-Bench 9.4 -> 22.2; real-device signal subset 32.2 -> 72.9 (95.1% of sim gain retained) | [2605.26114](https://arxiv.org/abs/2605.26114) |
| UI-Voyager (Qwen3-VL-4B) | Iterated RFT (online rejection sampling) then GRSD | Qwen3-VL-4B reported 45.3 -> RFT r3 73.2 -> 81.0 | [2603.24533](https://arxiv.org/abs/2603.24533) |
| Ferret-UI Lite (3B, Apple internal) | Step-level RLVR (GRPO, 32 samples/step, offline logged states), 1500 RL steps | AW 25 -> 28 (5-run mean); OSWorld 15 -> 17.3 | [2509.26539](https://arxiv.org/abs/2509.26539) |
| GUI-Owl-1.5-2B-Instruct | SFT + MRPO (RL delta not reported) | AW 67.9 (paper's own harness) | [2602.16855](https://arxiv.org/html/2602.16855v1) |

- Additional reference points at 2-4B:
  - Qwen3-VL-2B 36.4, ScaleCUA-3B 23.7, Ferret-UI Lite-3B 28.0. — [MAI-UI Table 6](https://arxiv.org/abs/2512.22047)
  - Step-GUI-4B 63.9, Qwen3-VL-4B 45.3. — [UI-Voyager Table 2](https://arxiv.org/abs/2603.24533)
  - GELab-Zero-4B 63.9. — [Mobile-Agent-v3.5 Table 1](https://arxiv.org/html/2602.16855v1)
- Ferret-UI Lite reward ablation (3B):
  - Action-type-only reward "leads to a substantial drop".
  - Grounding-only reward "does not surpass the SFT baseline".
  - Type + dense distance-based grounding reward works best.
  - RLVR gains are largest when preceded by fewer SFT steps. — [2509.26539](https://arxiv.org/abs/2509.26539)
- MobileGym 4B gain by difficulty: L1 +21.3, L2 +25.4, L3 +11.1, L4 +0.9. "Training is most effective where the base model already exhibits moderate capability." — [2605.26114](https://arxiv.org/abs/2605.26114)
- Offline/rule-based RL at 3B with no online environment:
  - UI-R1-3B (GRPO on 136 tasks): +12.7 on AndroidControl over Qwen2.5-VL-3B. — [2503.21620](https://arxiv.org/abs/2503.21620)
  - Magma-R1-3B: 2.4k curated samples, ~60 H20 GPU-hours, near Qwen3-VL-235B on AndroidControl-Curated. — [2510.18488](https://arxiv.org/abs/2510.18488)
  - OpenPhone: Qwen2.5-VL-3B SFT -> GRPO on synthetic data, evaluated on AndroidLab (numbers not retrieved). — [2510.22009](https://arxiv.org/abs/2510.22009)

### Inferences
- At 2B, the gain from a well-engineered online-RL stage on a strong SFT model is +4 (MAI-UI) to +14.5 (UI-Venus) AW points.
- Our SFT start (12.9%) is weaker than every reported 2-4B RL start except ADMIRE's 3B base (18.1). ADMIRE got +8.6 from outcome-only GRPO with 32 emulators, so a similar or larger relative gain is plausible, but only if the 2B policy samples some successes per task group.
- With grounding-quality issues, a dense coordinate reward (Ferret-UI Lite) or step-level supervision is more likely to help a 2B model than sparse episode reward alone.
- Expected gains on held-out templates/apps are much smaller (see question 4).

### Gaps
- No paper reports online RL on LFM-family or hybrid conv/attention VLMs. All small-model results are Qwen2.5-VL/Qwen3-VL-based or an Apple internal 3B.
- GUI-Owl-1.5-2B's RL delta is not reported.
- MAI-UI-2B's RL compute (environment count/steps for the 2B run specifically) was not found.

## 3. Rollout scale, environment-hours, GPU-hours; minimum viable setup

### Takeaway
Published online-RL runs span roughly 3 orders of magnitude:
- Industrial: 256-512 concurrent emulators (MobileRL, MAI-UI) to >10,000 (Qwen-UI-Agent).
- Academic: 16-96 environments on 2-8 GPUs.

The smallest documented successes:
- AndroidWorld-Generalization: 16 emulators + 2 H100.
- ADMIRE: 32 emulators + 8 A800.
- ClawGUI: 64 environments + 8 A6000.
- MobileGym: 96 browser-sim instances + 3 RTX Pro 6000, only 10 GRPO steps (~960 trajectories).

Environment throughput, not GPU, is the bottleneck. Fewer environments can saturate early.

### Cited Findings
- **MobileRL:** 4 CPU machines with 1 TB RAM each, dedicated to rollouts. Each AVD needs >5 GB RAM and >30 GB disk. The system "can only stably sustain up to 256 parallel rollouts, with each step taking more than 10 minutes"; "training 100 steps already takes more than 25 hours" (elsewhere ">40 hours" for a 100-step budget). Train batch 256, n=16. — [2509.18119](https://arxiv.org/abs/2509.18119)
- **MAI-UI:**
  - Infrastructure: 10 Alibaba ECS servers support up to 512 concurrent containerized AVDs; async strict on-policy verl; Megatron TP+PP+CP for trajectories "up to millions of tokens".
  - Scaling environments 32 -> 512 improved 8B from 65.5 to 70.7 (SFT was 64.7); "fewer environments exhibit early saturation".
  - Step budget per trajectory 15/30/50 gave +1.7/+3.8/+6.0.
  - 720p matches 1080p with ~50% faster steps; 540p hurts. — [2512.22047](https://arxiv.org/abs/2512.22047)
- **AndroidWorld-Generalization:** 16 parallel Docker emulators, two H100-80GB, 8 rollouts per task capped at 20 steps, 500 policy iterations per experiment.
  - Parallel 16 environments reduced collection time 6.83x vs sequential.
  - Synchronous rollout is 57.8% slower than asynchronous at 16 environments.
  - "Rollout collection dominates training." — [2603.07432](https://arxiv.org/abs/2603.07432)
- **ADMIRE:** 32 remote emulators, 8x A800. Per iteration: 4 tasks x 8 trajectories, max 20 steps, prompt <=6500 tokens, response <=512, lr 1e-6, no KL. — [2602.11524](https://arxiv.org/abs/2602.11524)
- **ClawGUI-2B:** 64 parallel virtual environments, 8x A6000 48GB, GiGPO group 8, batch 8, 3 epochs, lr 1e-6, temperature 0.7, spare-container rotation for unhealthy emulators. — [2604.11784](https://arxiv.org/abs/2604.11784)
- **MobileGym:**
  - Sim-to-Real run: Qwen3-VL-4B, 3 GPUs, 96 parallel instances, group k=8, batch 12, 10 steps, lr 1e-6, KL 0.01, clip 0.2/0.28.
  - Instances are browser-hosted, ~400 MB each with ~3 s cold start. By contrast, an AW Docker emulator takes ~4.5 GB host RAM, a 20.2 GB image, and a ~78 s median boot without KVM.
  - A VLM judge would cost ~$1 (Qwen3.6-Plus) to $8.5 (GPT-5.4) per 96-trajectory GRPO step; code judging costs $0. — [2605.26114](https://arxiv.org/abs/2605.26114)
- **SoLS:** 15K episodes (~200K transitions), 8 concurrent emulator processes. Each update uses 100 on-policy transitions plus 50 from the success replay. — [2509.01720](https://arxiv.org/abs/2509.01720)
- **ZeroGUI:** GRPO G=64; each rollout step collects 16k sequences before one update; 175 generated Android training tasks. — [2505.23762](https://arxiv.org/abs/2505.23762)
- **Ferret-UI Lite:** 10K SFT steps + 1500 RL steps, 32 samples per navigation prompt. — [2509.26539](https://arxiv.org/abs/2509.26539)
- **Interaction-reducing methods:**
  - Restarting rollouts from intermediate checkpoints on expert trajectories cut environment interaction by 56-61% vs vanilla GRPO while improving performance (MobileGym, CUA-Gym-Hub). — [arXiv 2610.39251](https://arxiv.org/abs/2610.39251)
  - Android Coach: a critic lets it score multiple actions per emulator state, giving 1.4x efficiency. — [2604.07277](https://arxiv.org/abs/2604.07277)
  - World-model rollouts with no emulator (WM-R1, 2000 tasks; numbers not retrieved). — [2608.27508](https://arxiv.org/abs/2608.27508)
- **Industrial upper bound:** Qwen-UI-Agent uses >10,000 concurrent environments and >100-turn trajectories. — [arXiv 2607.28227](https://arxiv.org/abs/2607.28227)

### Inferences
- **Throughput estimate (assumptions, not measured):** 2.7 s/step model latency plus ~1-3 s environment overhead gives ~4-6 s/step. Averaging ~15-20 steps per episode, including failures that run to the cap, plus AW task setup gives ~50-80 episodes/hour across 2 emulators.
- **Comparison to published runs:**
  - The entire MobileGym 4B run (~960 trajectories) is ~12-20 emulator-hours for us.
  - One ADMIRE iteration (32 trajectories) is ~25-40 minutes.
  - A 500-iteration AndroidWorld-Generalization-scale run is out of reach.
  - MAI-UI's 32-environment saturation result suggests our 2 emulators would favor low-variance, sample-efficient methods (RFT/replay, step-level self-distillation, critic- or checkpoint-based rollout reuse) over large-group GRPO.
- **Minimum viable "true online" setup implied by the literature:**
  - ~16 emulators and ~1-2 large GPUs co-located, so the policy is served and trained in the same loop (AndroidWorld-Generalization).
  - Group size 8, <=20 steps per episode, curriculum from easy templates.
- Our compute is split: emulators on the Mac, training on ephemeral Colab, a small Modal budget. That favors batched, iterated "collect -> filter/score -> LoRA update -> redeploy" cycles, effectively online RFT or slightly off-policy GRPO, over strict on-policy async RL.

### Gaps
- No paper reports end-to-end wall-clock or GPU-hours for a 2B online-RL run. MAI-UI does not break down 2B compute.
- No published Mac/ARM-host emulator RL setup was found.
- The per-step environment latency of AW on Apple Silicon is unknown here; we should measure it.

## 4. AndroidWorld contamination: training on AW task generators vs held-out pools

### Takeaway
Many headline AW numbers come from RL directly on AW task templates with new random seeds: MobileRL (2,000 tasks), UI-Voyager (>7,000 tasks), ADMIRE (in-domain AW sandbox), and SoLS (RL environment = evaluation benchmark). ZeroGUI even does test-time training on test tasks. This is the "Unseen Instance" regime. When templates or apps are held out, RL gains shrink sharply: AndroidWorld-Generalization measured +26.1 on unseen instances vs +15.7 on unseen templates and +8.3 on unseen apps. Clean non-AW task pools now exist (AndroidLab train tasks, MobileMiniWoB++, MobileGym train templates, OpenMobile-2's 2K verifiable tasks, MAI-Gym's 2,000 tasks and mocked apps, VLM-generated tasks), but their transfer to AW is less documented.

### Cited Findings
- **MobileRL:** "AndroidWorld further provides randomized initialization parameters ... we remove all tasks whose specific content and initial states coincide with those in the test set ... we curate 2,000 tasks" for RL, plus 1,103 AndroidLab tasks. The best 9B model was RL-trained "purely on the AndroidWorld environment". — [2509.18119](https://arxiv.org/abs/2509.18119)
- **UI-Voyager:** "we follow MobileRL and employ training sets from AndroidWorld, consisting over 7000 tasks"; evaluated on the same 116 AW tasks (64 random seeds). — [2603.24533](https://arxiv.org/abs/2603.24533)
- **AndroidWorld-Generalization:**
  - 38 of 116 templates "consistently produce identical task instances regardless of seed" and must be excluded from training. The remaining 78 templates x 16 seeds give 1,149 deduplicated training instances; test uses seeds 30/7/1234.
  - Unseen Template split: 57 train / 18 test templates. Unseen App split: 12 train / 5 test apps (Audio Recorder, Clock, OsmAnd, Tasks, Broccoli).
  - GRPO gains: Unseen Instance +21.8 to +26.1, Template +15.7, App +8.3. PPO gives +17.1 / +15.7 / +8.3.
  - Per-app few-shot test-time RL adds +10.4 on unseen apps. — [2603.07432](https://arxiv.org/abs/2603.07432)
- **SoLS:** "We use AndroidWorld as our RL environment and evaluation benchmark throughout our experiments" (80-task subset). — [2509.01720](https://arxiv.org/abs/2509.01720)
- **ZeroGUI:** stage 2 is "test-time training" on target test tasks with VLM rewards and no ground truth. Generated tasks are conditioned on exemplar test tasks. — [2505.23762](https://arxiv.org/abs/2505.23762)
- **ADMIRE:** trains on AW (each worker is "an AVD running the AndroidWorld sandbox") and calls MobileMiniWoB++ "out-of-domain". The 3B model's OOD gain (+5.5) is far below its AW gain (+12.9). — [2602.11524](https://arxiv.org/abs/2602.11524)
- **MAI-UI:** RL environment is a containerized AVD "inspired by an experimental feature in AndroidWorld" with 35+ self-hosted apps (Mattermost, Mastodon, Mall4Uni, ...). The paper does not state whether AW templates are in the RL task pool. — [2512.22047](https://arxiv.org/abs/2512.22047)
- **Non-AW task pools with verifiers:**
  - AndroidLab: 138 test tasks over 9 apps; MobileRL used 1,103 training tasks with a GLM-4.1V-9B reward model at 86% accuracy. — [2509.18119](https://arxiv.org/abs/2509.18119)
  - MobileMiniWoB++: 92 tasks in one app. — [2602.11524](https://arxiv.org/abs/2602.11524)
  - MobileGym-Bench: 160 train / 256 test parameterized templates over 28 browser-simulated apps, deterministic JSON-state judges, AnswerSheet protocol for query tasks. — [2605.26114](https://arxiv.org/abs/2605.26114)
  - OpenMobile-2: "over 2K executable tasks with automatic rewards", 35 simulated commercial apps, released. — [2610.14157](https://arxiv.org/abs/2610.14157)
  - MAI-Gym: 2,000 verified tasks and mocked apps, released. — [2610.20939](https://arxiv.org/abs/2610.20939)
  - MobileWorld: 116 GUI-only + 45 user-interaction + 40 MCP tasks (eval). — [2512.22047](https://arxiv.org/abs/2512.22047)
  - AndroidFlux: failure-recovery checkpoints built on AW, plus an offline RL dataset. — [2610.34384](https://arxiv.org/abs/2610.34384)

### Inferences
- If we RL on AW templates (even with new seeds), our AW number becomes an "Unseen Instance" score and is not comparable to GUI-Owl-1.5-2B or MAI-UI-2B as a generalization measure. We should report it as such. Better: train on the AW Unseen-App/Unseen-Template train split and report the held-out split separately.
- Also exclude the 38 seed-invariant templates from any AW-derived training pool.
- The cleanest pools for us:
  - AndroidLab training tasks: Android, verifiable, different apps.
  - MobileGym's 160 train templates: cheap, so many parallel instances fit on the Mac, but browser-simulated, so AW transfer is unproven.
  - VLM-generated tasks on non-AW apps in our own emulator.
- ZeroGUI's lesson applies to all of these: use exemplars plus multiple candidates per prompt, and include infeasible tasks.

### Gaps
- No paper directly measures how MobileGym, OpenMobile-2, or MAI-Gym training transfers to the 116 AW tasks for a 2B model.
- MAI-UI's and UI-Venus-1.5's RL task overlap with AW templates is undisclosed.

## 5. Known pitfalls: reward hacking, collapse, sparse rewards, long horizons, partial credit, and links to our failure modes

### Takeaway
Documented failure modes:
- Training collapse without replay or length shaping (MobileRL).
- Early saturation with few environments and too-short step budgets (MAI-UI).
- False-positive judge rewards making agents overconfident (ZeroGUI, UI-TARS-2).
- Step-level offline rewards decoupling from trajectory success (UI-Venus).
- Mis-specified partial rewards hurting small models (Ferret-UI Lite).
- No gains on the hardest tasks.

Several papers ship concrete fixes that map onto our four failure modes (never answers, premature complete, no recovery after no-ops, loops).

### Cited Findings
- **Collapse/stability:**
  - MobileRL: "FCF only (w/o AdaPR & SPA) ... collapses after about 30 steps"; SPA gains appear after ~60 steps "because the lack of step-wise control leads to overly long trajectories". — [2509.18119](https://arxiv.org/abs/2509.18119)
  - ZeroGUI: k2-KL gives "higher and more stable training accuracy" than GRPO's k3-KL. — [2505.23762](https://arxiv.org/abs/2505.23762)
  - UI-TARS-2: value estimates were "negatively correlated with the obtained rewards" until value pretraining. Entropy *rises* during GUI RL, unlike reasoning RL. — [2509.02544](https://arxiv.org/abs/2509.02544)
- **Judge noise and reward hacking:**
  - ZeroGUI: false positives are "more detrimental" than false negatives. Including the agent's own response in the judge prompt raises recall but lowers precision and final success ("misled by the response"). Unanimous voting over 4 samples helps. Noisy positives reduce infeasibility detection ("overconfident"). — [2505.23762](https://arxiv.org/abs/2505.23762)
  - UI-TARS-2's ORM had F1 83.8 with a "relatively high false positive rate", yet RL still worked; manual inspection found no substantial reward hacking. — [2509.02544](https://arxiv.org/abs/2509.02544)
  - MobileGym found a 10.2% VLM-judge misjudgment rate on real-device trajectories. — [2605.26114](https://arxiv.org/abs/2605.26114)
  - ADMIRE notes process rewards are "prone to bias and reward hacking". — [2602.11524](https://arxiv.org/abs/2602.11524)
- **Partial credit:**
  - MobileGym reward = fraction of goal checks passed, multiplied by penalty factors:
    - x0.8 if the goal is reached with side effects.
    - **x0.8 for "false complete"** (declares COMPLETE without full success).
    - x0.5 for aborting after success.
    - x0.5 for "overdue" (keeps acting until truncation after reaching the goal).

    Submitting a wrong AnswerSheet earns no extra credit. — [2605.26114](https://arxiv.org/abs/2605.26114)
  - ADMIRE: adding dense base reward to *successful* trajectories hurt; removing the progress scaffold from *failed* ones hurt most. — [2602.11524](https://arxiv.org/abs/2602.11524)
- **Step vs trace mismatch:**
  - UI-Venus-1.5: offline step-reward RL raises step accuracy while trace success "peak[s] and then decline[s]". — [2602.09082](https://arxiv.org/abs/2602.09082)
  - MobileRL: RL slightly lowered offline AndroidControl-High SR (7B 72.8 -> 71.3; 9B 77.5 -> 73.9). — [2509.18119](https://arxiv.org/abs/2509.18119)
- **Loops / repeated actions:**
  - MAI-UI penalizes "recurring action sequences (from single repeated actions to cyclic patterns of 3-5 actions)" but not the same action type with different parameters. — [2512.22047](https://arxiv.org/abs/2512.22047)
  - MobileGym's harness terminates early when the same action repeats >=10 times. — [2605.26114](https://arxiv.org/abs/2605.26114)
  - VeriGUI (action-effect verification + GRPO with asymmetric verification rewards) "significantly reduces failure loops". — [2604.05477](https://arxiv.org/abs/2604.05477)
- **Premature termination:**
  - UI-TARS-2 uses "format rewards and length penalties to discourage premature termination or infinite continuation". — [2509.02544](https://arxiv.org/abs/2509.02544)
  - MobileGym's false-complete penalty (above). — [2605.26114](https://arxiv.org/abs/2605.26114)
- **Answer emission:**
  - AndroidWorld-Generalization added "answer" to UI-TARS's action space. Information-retrieval tasks started at 0% SR and improved with RL, but "information retrieval at the hard level remains unsolved". — [2603.07432](https://arxiv.org/abs/2603.07432)
  - MobileGym's AnswerSheet adds a 15-step budget for query tasks and uses structured fields to avoid free-text matching failures. — [2605.26114](https://arxiv.org/abs/2605.26114)
- **Recovery:**
  - MAI-UI case studies: after RL the agent dismisses unseen permission dialogs and recovers from navigating to the wrong app. — [2512.22047](https://arxiv.org/abs/2512.22047)
  - UI-Venus-1.5 credits online RL with "error recovery". — [2602.09082](https://arxiv.org/abs/2602.09082)
  - AndroidFlux: recovery "only partially correlates with clean-start success"; its released offline RL dataset improves recovery. — [2610.34384](https://arxiv.org/abs/2610.34384)
  - UI-Voyager's fork-point distillation teaches the correct action at the exact state where failed rollouts diverge. — [2603.24533](https://arxiv.org/abs/2603.24533)
- **Hard tasks and weak starts:**
  - MobileGym L4 +0.9 vs L2 +25.4. — [2605.26114](https://arxiv.org/abs/2605.26114)
  - RL directly from a base 4B model was "highly inefficient" (~175 steps to match one RFT round). — [2603.24533](https://arxiv.org/abs/2603.24533)
  - Without reasoning-free SFT, MobileRL's final AW was consistently lower. — [2509.18119](https://arxiv.org/abs/2509.18119)

### Inferences
- Concrete shaping for our failure modes, combining verified designs:
  - Binary verifier success, with a MobileGym-style **false-complete multiplier**.
  - **Answer-correctness gating** for query tasks (no success unless the `answer` content matches).
  - A MAI-UI-style **repetition penalty** on identical consecutive actions and short cycles.
  - An early-stop at N repeats to save emulator time.
  - An SPA-style mild preference for shorter successful trajectories, used cautiously since it can encourage premature completion if success detection is noisy.
- Do not show the agent's own final message to any VLM judge (ZeroGUI).
- Because a 2B policy that "never emits answer" will never sample a rewarded answer, RL alone will not fix this. Seed it via SFT/RFT on answer-bearing trajectories first (MobileRL and UI-Voyager both find warm-starting essential).

### Gaps
- No paper isolates the effect of a repetition penalty at 2B, or measures no-op detection specifically (screen-unchanged after action) as a reward feature.
- No source quantifies reward hacking rates for AW's rule-based verifiers, which are generally considered reliable.

## 6. Feasibility with our compute (Colab RTX PRO 6000 96GB for a few GPU-hours, Mac with 2 AW emulators at ~2.7 s/step, Modal ~$13)

### Takeaway
Strict on-policy async GRPO at published scale (16-512 environments, tens to hundreds of iterations) is not feasible. Feasible, evidence-backed options, in priority order:
1. **Iterated online rejection fine-tuning (RFT / filtered BC) with verifier rewards**, run as batch rounds on held-out-split AW templates or AndroidLab tasks.
2. **Fork-point self-distillation (GRSD) on the same group rollouts.**
3. **Emulator-free "semi-online" / offline step-level RL on AndroidControl trajectories** (UI-S1, GHD, Ferret-UI-style dense rewards), run entirely on Colab.
4. Optionally, a **short GRPO run (~10 steps x ~96 trajectories, MobileGym-scale)** with repetition / false-complete shaping, if we accept ~12-20 emulator-hours per run.

### Cited Findings
- **RFT is close to online RL and cheap:**
  - ZeroGUI ablation: offline RFT 22.4 < online RFT 24.5 < online RL 27.2 (OSWorld Daily). — [2505.23762](https://arxiv.org/abs/2505.23762)
  - UI-Voyager: four RFT rounds on Qwen3-VL-4B rose steadily to 73.2 pass@1, and RFT was the necessary warm start before any RL-style stage. — [2603.24533](https://arxiv.org/abs/2603.24533)
  - DigiRL's filtered-BC baseline reached 57.8 vs 67.2 for full DigiRL at 1.3B on AitW. — [2406.11896](https://arxiv.org/abs/2406.11896)
- **GRSD uses only an SFT loss** on (failed context, successful action) pairs at SSIM-matched fork points, replacing GRPO/PPO. — [2603.24533](https://arxiv.org/abs/2603.24533)
- **Smallest GRPO run with a measured gain:** MobileGym, 10 GRPO steps x 96 trajectories (group 8, batch 12) on 3 RTX Pro 6000 gave a 4B model +12.8. — [2605.26114](https://arxiv.org/abs/2605.26114)
- **Emulator-free alternatives:**
  - UI-S1 semi-online RL on offline trajectories: +12.0 AW at 7B. — [2509.11543](https://arxiv.org/abs/2509.11543)
  - SOLAR-RL: semi-online with first-failure-point dense rewards. — [2604.22558](https://arxiv.org/abs/2604.22558)
  - Gated Hindsight Distillation: next-screenshot privileged teacher; beats GRPO on AW and AndroidLab across two VLMs. — [2608.06065](https://arxiv.org/abs/2608.06065)
  - Ferret-UI Lite: step-level RLVR on logged states, 25 -> 28 AW at 3B. — [2509.26539](https://arxiv.org/abs/2509.26539)
  - VEM: value environment model with no environment, on AitW. — [2502.18906](https://arxiv.org/abs/2502.18906)
- **Rollout-saving tricks:**
  - Intermediate-checkpoint restarts: -56-61% interactions. — [2610.39251](https://arxiv.org/abs/2610.39251)
  - Successful-trajectory replay (MobileRL AdaPR, MAI-UI, ARPO, SoLS STR). — [2509.18119](https://arxiv.org/abs/2509.18119); [2512.22047](https://arxiv.org/abs/2512.22047); [2509.01720](https://arxiv.org/abs/2509.01720)
  - Curriculum from easy templates: +4 points over no curriculum in AndroidWorld-Generalization (49.1 vs 45.1). — [2603.07432](https://arxiv.org/abs/2603.07432)
  - Lower screenshot resolution (720p) for ~50% faster steps. — [2512.22047](https://arxiv.org/abs/2512.22047)
- **Open infrastructure that could be reused:**
  - AndroidWorld-Generalization's open RL system with containerized AW and train/test splits. — [github](https://github.com/zihuanjiang/AndroidWorld-Generalization)
  - ClawGUI-RL (verl + verl-agent, GiGPO + PRM, emulator or real device). — [github](https://github.com/zju-real/ClawGUI)
  - MobileRL. — [github](https://github.com/THUDM/MobileRL)
  - MobileGym (browser-hosted). — [mobilegym.github.io](https://mobilegym.github.io)

### Inferences
- **Concrete plan sketch (inference):**
  1. **Task pool.** Build a held-out-safe pool, e.g. AW Unseen-App train split (12 apps / 62 templates / 905 instances) minus the 38 seed-invariant templates, plus AndroidLab train tasks if emulator support allows.
  2. **Rollouts.** Run 4-8 rollouts per task with the current LoRA policy on 2 emulators at temperature ~0.7-1.0 with a 20-30 step cap. That is ~50-80 episodes/h, i.e. ~10-20 tasks/h at group 4-8.
  3. **Training.** Keep successes plus GRSD fork-point pairs, then run one LoRA SFT round on Colab (minutes to <1 GPU-hour for a few thousand steps).
  4. **Iterate** 3-4 rounds.

  This mirrors UI-Voyager's RFT + GRSD loop at ~1/100th the scale.
- **Shaping.** Add the repetition penalty and false-complete / answer-gating filters at the data-selection stage: drop "successful" trajectories that contain loops, or that ended with `complete` on query tasks without an answer.
- **Starting point.** At 12.9% AW, many task groups will have zero successes. Curriculum filtering (keep tasks with 0 < pass@k < 1, as in FCF / DAPO dynamic sampling) and easy-template-first ordering matter more for us than algorithm choice.
- **Modal budget.** The ~$13 is best spent on a short burst of policy serving or a VLM judge only for tasks without rule verifiers. MobileGym's estimate of ~$1-8.5 per 96-trajectory step for API judging implies rule-verifiable tasks should dominate.
- **Expected magnitude (speculative).** Published 2-4B online-RL gains are +4 to +14.5 AW points from much stronger starts with 32-512 environments. With 2 emulators and RFT-style updates, a few points on held-out templates is a more realistic target; larger gains would likely be "Unseen Instance" gains.

### Gaps
- No published experiment uses only 2 emulators or a Mac host. Our throughput numbers are estimates and need measurement (AW reset/setup time per task on Apple Silicon is unknown).
- There is no direct evidence on how much RFT-only (vs GRPO) adds at 2B on AW held-out templates.
- No evidence was found on LoRA-only online RL for GUI agents. SoLS used LoRA for SFT; whether its RL stage also used LoRA was not confirmed from the passages read.
