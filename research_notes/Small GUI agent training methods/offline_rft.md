# Offline and Semi-Online Reinforcement Fine-Tuning (RFT) for Small GUI Agents on Static Data

Scope: rule-based-reward GRPO/RLVR on single-step GUI action prediction from static trajectories (offline RFT), semi-online RL that simulates multi-turn rollouts from static trajectories, and how either transfers to online benchmarks (AndroidWorld = AW, 116 tasks). Emphasis on models of 3B or smaller. Grounding benchmarks (ScreenSpot / -v2 / -Pro, OSWorld-G) are kept separate from agent benchmarks: offline step-level ones (AndroidControl = AC, GUI-Odyssey) and online ones (AW, AndroidLab, OSWorld). Unless stated otherwise, "AC-High/Low SR" means step success rate.

Project context: LFM3-VL-2B with LoRA SFT gets AC step accuracy 0.715 (high-level) / 0.948 (low-level) but only 15/116 (12.9%) on AW, versus 1/116 for the base model. Observed failures: never answers, completes too early, does not recover from errors, loops. Compute is 1x 96GB GPU for a few hours plus 2 emulators.

## Q1. Method catalogue: model sizes, data sizes, rewards, KL, rollouts, steps, GPU budget

### Takeaway
Almost every 2025 "R1-style" GUI paper starts from Qwen2.5-VL-3B or 7B. They train GRPO (InfiGUI-R1 uses RLOO) on 136 to about 100K static samples with rule rewards: format, action type, then point-in-bbox or a dense distance/Gaussian coordinate score, then text F1 or exact match. Typical settings are lr ≈1e-6, 8 rollouts per prompt (16 to 32 in some), 1 to 9 epochs, and 8 to 32 datacenter GPUs. KL settings vary: β=0.04 in older TRL/VLM-R1-style recipes, 1e-4 to 1e-3 in the 2025-26 agent papers, and 0 in grounding-only or GHD recipes.

### Cited Findings
**UI-R1 (vivo/CUHK, Mar 2025)**
- Qwen2.5-VL-3B. 136 hard samples chosen for quality, difficulty and diversity: 101 click, 5 scroll, 2 input, 9 back, 19 open_app. Click data comes from the ScreenSpot mobile split; the other actions come from 1K AndroidControl episodes with click steps removed because AC's element boxes are misaligned. — [UI-R1](https://arxiv.org/abs/2503.21620)
- Reward = R_type (binary) + R_coord (1 if the predicted point is inside the GT bbox) + R_format (<think>/<answer> tags). An IoU>0.5 box reward did worse than the point-in-box reward. — [UI-R1](https://arxiv.org/abs/2503.21620)
- Hyperparameters: lr 9.98e-7 decaying to 0, 8 generations, 8 epochs, per-device batch 1 with grad-accum 2. Trained on 8x RTX 4090 in about 8 hours. — [UI-R1](https://arxiv.org/abs/2503.21620)
- UI-R1-E-3B ("efficient") was trained on 2K samples in two stages: DAST (a length-budget reward) for 4 epochs, then NOTHINK for 4 epochs. — [UI-R1](https://arxiv.org/abs/2503.21620)

**GUI-R1 (SIAT/NUS, Apr 2025)**
- Qwen2.5-VL-3B and 7B. GUI-R1-3K was filtered from about 14M samples: Qwen2.5-VL-7B sampled 10 answers per item and items with accuracy exactly 0 or 1 were dropped, leaving 1.5K low-level + 1.5K high-level samples. — [GUI-R1](https://arxiv.org/abs/2504.10458)
- Trained with EasyR1 for 9 epochs on 8x A100-80G. Reward = α·format + β·accuracy, and α=0.2/β=0.8 beat 0.5/0.5 and 0.8/0.2. Accuracy combines type match, point-in-bbox, and input-text F1>0.5. Policy update is GRPO "under KL constraints"; the coefficient is not given in the passages retrieved. — [GUI-R1](https://arxiv.org/abs/2504.10458) / [code](https://github.com/ritzz-ai/GUI-R1)
- Doubling image resolution (1.05M to 2.1M pixels) sped convergence and raised the ceiling. — [GUI-R1](https://arxiv.org/abs/2504.10458)

**InfiGUI-R1-3B (Apr 2025)**
- Qwen2.5-VL-3B in two stages. Stage 1 distills spatial reasoning via SFT from a QwQ-32B teacher (lr 2e-6, batch 32). Stage 2 is RLOO RL (lr 1e-6, batch 256, rollout batch 256, 16 rollouts per sample) on 16x H800. — [InfiGUI-R1](https://arxiv.org/abs/2504.14239)
- RL data: AndroidControl (10K trajectories + 2K reflection/error-recovery trajectories), 5K grounding, 11K MathV360K, 4K COCO. — [InfiGUI-R1](https://arxiv.org/abs/2504.14239)
- Reward: 0.1·format + 0.9·accuracy. Within accuracy, type gets weight 0.2 and exact params 0.8. A sub-goal similarity reward (weight 0.2) applies when params are wrong. The bbox IoU threshold is 0.7. — [InfiGUI-R1](https://arxiv.org/abs/2504.14239)

**GUI-G1-3B (RUC/Huawei, May 2025)**
- Qwen2.5-VL-3B trained on about 17K public grounding samples. Uses a no-think "Fast Thinking Template" and reward R_hit + α·R_IoU + β·R_box. Modifies GRPO by replacing the per-response length normalization with a constant (Dr.GRPO-style) and adding a difficulty weight derived from relative box size. — [GUI-G1](https://arxiv.org/abs/2505.15810) / [code](https://github.com/Yuqi-Zhou/GUI-G1)

**GUI-G2-7B (Gaussian rewards, Jul 2025)**
- Qwen2.5-VL-7B on about 100K grounding instances, using VLM-R1 on 8x A100 for 1 epoch. lr 1e-6, global batch 8, 8 rollouts, KL β=0.04. — [GUI-G2](https://arxiv.org/abs/2507.15846)
- Reward = ν·R_point + γ·R_coverage, with ν=γ=1:
  - R_point is a Gaussian centered on the element.
  - R_coverage is a Bhattacharyya-style overlap between the predicted and GT Gaussians.
  - The variance adapts to element size: σ = α·(width or height), with α=0.5.
  — [GUI-G2](https://arxiv.org/abs/2507.15846)

**SE-GUI (May 2025)**
- 3B and 7B. Uses about 3K filtered "seed" samples, a dense point reward, and self-evolutionary stages in which attention maps from the previous stage supervise the next. — [SE-GUI](https://arxiv.org/abs/2505.12370)

**UI-AGILE (Jul 2025)**
- 3B and 7B on 9K samples, 2 epochs, lr 1e-6, 8 generations. — [UI-AGILE](https://arxiv.org/abs/2507.22025) / [code](https://github.com/KDEGroup/UI-AGILE)
- Continuous grounding reward. When all 8 samples score 0, the image is cropped (factor 0.6) and resampled, up to 4 attempts. — [UI-AGILE](https://arxiv.org/abs/2507.22025)
- "Simple Thinking" reward: the ideal thought is 120 to 200 characters, with a minimum of 50 and a maximum of 300. — [UI-AGILE](https://arxiv.org/abs/2507.22025)

**GTA1 (Salesforce, Jul 2025)**
- A grounding model trained with GRPO, outputting coordinates directly with no thinking. The only reward is a binary click-in-bbox. — [GTA1](https://arxiv.org/abs/2507.05791)
- Training data is cleaned by dropping samples whose annotated box has max IoU < τ with every OmniParser-detected element. — [GTA1](https://arxiv.org/abs/2507.05791)

**LPO (Jun 2025)**
- GRPO with an information-entropy-based location prior and a dynamic location reward based on physical distance. Only the abstract was read. — [LPO](https://arxiv.org/abs/2506.09373)

**ReGUIDE (May 2025)**
- Web grounding. Online RL with self-generated reasoning, a spatial-equivariance critique, and test-time spatial search. Claims to beat baselines with about 0.2% of their data. Only the abstract was read. — [ReGUIDE](https://arxiv.org/abs/2505.15259)

**AgentCPM-GUI (Tsinghua/ModelBest, Jun 2025)**
- 8B (MiniCPM-V). RFT stage uses GRPO with 8 generations, lr 1e-6, KL β=0.04, 3 epochs, max completion 512 tokens. — [AgentCPM-GUI](https://arxiv.org/abs/2506.01391) / [code](https://github.com/OpenBMB/AgentCPM-GUI)
- Reward is -1 for format failure, 0 for wrong, 1 for correct, where a POINT counts as correct if it falls inside the GT bbox. Actions are compact JSON averaging 9.7 tokens, with coordinates in 0-1000. — [AgentCPM-GUI](https://arxiv.org/abs/2506.01391)

**Ferret-UI Lite (Apple, Sep 2025)**
- Apple's internal 3B dense model, not Qwen. 10K SFT steps, then 1500 RL steps of GRPO. — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- Rollouts: 32 per navigation prompt; 8 on the full image + 4 on a zoomed crop per grounding prompt. Groups with identical rewards are filtered out online. — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- Navigation reward = f_type + f_param:
  - f_type = 2 if the type matches and the action has no params; 1 if the type matches and params are needed; 0 otherwise.
  - f_param for strings is exact match.
  - f_param for taps is a dense score max(1 − 0.5·(|dx|/w + |dy|/h), 0).
  — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)

**UI-S1 (Tongyi/ZJU, Sep 2025)**
- Semi-online RL, detailed under Q4. Key settings: kl_loss_coef 1e-4, lr 1e-6, train batch 32, 5 epochs, 4 nodes x 8 GPUs, 2 historical images, γ=0.5, ω=1, patch threshold ε=1, DAPO-style variance threshold η=0.3, max response 512 tokens. — [UI-S1](https://arxiv.org/abs/2509.11543) / [code](https://github.com/X-PLUG/MobileAgent/tree/main/UI-S1)

**UI-Venus (Ant, Aug 2025)**
- Qwen2.5-VL 7B and 72B, trained purely with GRPO RFT on about 107K grounding and about 350K navigation samples. — [UI-Venus](https://arxiv.org/abs/2508.10833) / [code](https://github.com/inclusionAI/UI-Venus)
- Navigation reward has four parts: format, type, coordinate, content. — [UI-Venus](https://arxiv.org/abs/2508.10833)
- Grounding and navigation were trained as separate models because mixing the two rewards destabilized training. — [UI-Venus](https://arxiv.org/abs/2508.10833)

**GUI-Libra (Feb 2026)**
- Qwen2.5-VL-3B/7B and Qwen3-VL-4B/8B. SFT on the 81K-sample GUI-Libra set, then GRPO on a 40K subset. — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- RL settings: 300 iterations, lr 1e-6, global batch 128, rollout batch 256, n=8, temperature 1.0, max response 1500 tokens. KL 0.001 (0.005 for 7B). Reward = 0.1·format + 0.9·accuracy. — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- About 16 hours (4B) or 20 hours (8B) on 8x B200 for RL. — [GUI-Libra](https://arxiv.org/abs/2602.22190)

**SOLAR-RL (vivo, Apr 2026)**
- Semi-online. Qwen2.5-VL-7B on 15K trajectories (94K steps). N=8, lr 1e-6, γ=0.95, KL 0.001 (low_var_kl), global batch 128, 650 steps. About 60 hours on 32x L40S. — [SOLAR-RL](https://arxiv.org/abs/2604.22558)

**Gated Hindsight Distillation, GHD (Aug 2026)**
- Qwen2.5-VL-7B and Qwen3-VL-8B. Trains on a hard subset of OpenMobile trajectories: 6,968 / 5,982 of 27,360 examples, keeping those the SFT model fails in one attempt. — [GHD](https://arxiv.org/abs/2608.06065)
- G=8, lr 1e-6, no KL penalty, 200 steps, on 4x A100 or RTX PRO 6000. — [GHD](https://arxiv.org/abs/2608.06065)

### Inferences
- The most common recipe is lr 1e-6, 8 rollouts at temperature 1.0, 1 to 5 epochs over 1K to 40K samples, with zero-variance groups filtered or resampled.
- The smallest documented budgets that still improved step-level metrics are UI-R1 (8 consumer GPUs for 8 hours, 136 samples) and GHD (4 GPUs for 200 steps). Both are in the range of 1x 96GB for a few hours for a 2B model if rollouts are kept short.
- KL needs a different setting for each job. Grounding-only or binary-reward recipes often drop it. Multi-step agent recipes that care about online transfer (GUI-Libra, SOLAR-RL, UI-S1) keep a small one, about 1e-4 to 1e-3.

### Gaps
- Not recovered from the retrieved passages: UI-R1's KL coefficient; GUI-R1's rollout count and KL value; GUI-G1's KL and rollout count; UI-S1's number of rollouts per trajectory (N) and total GPU-hours (it is in a figure, not text).
- Phi-Ground (arXiv 2507.23779) was not examined. I could not verify whether its training includes an RL stage or what its findings are.
- Mobile-R1's backbone and size for the final model were not confirmed in the passages read. Its data collection used Qwen2.5-VL-3B as the executing agent.
- No paper found uses a non-Qwen, non-transformer hybrid backbone such as LFM's conv/attention design. Ferret-UI Lite (Apple's internal 3B) is the only non-Qwen small model with an AW number.

## Q2. Does offline RFT improve AndroidControl, and does it transfer to AndroidWorld? Thinking vs no-thinking at small scale

### Takeaway
Offline step-level GRPO reliably raises AC and grounding scores. AW success moves anywhere from slightly down to about +12 points, depending on the recipe:
- Plain GRPO with ground-truth history gives about 0 to +3 points on AW.
- The gain is large only with careful design: KL-regularized, CoT-retaining, filtered data, and handling of partially verifiable rewards (GUI-Libra-3B: 13.0 to 25.2).
- Methods that simulate the agent's own history (semi-online) or add privileged hindsight do better still.

On thinking: no-think is as good or better for pure grounding, but explicit (short) reasoning helps closed-loop navigation, including at 3B.

### Cited Findings
**Offline RFT gains on AC and grounding**
- UI-R1-3B (136 samples) raised AC-Low action-type accuracy from 79.3 to 94.3 and click grounding from 72.3 to 82.6 relative to Qwen2.5-VL-3B zero-shot. Grounding here uses a 14%-of-screen distance criterion on an AC subset. ScreenSpot average went 65.0 to 83.3. No online benchmark was reported. — [UI-R1](https://arxiv.org/abs/2503.21620)
- GUI-R1-3B compared with base Qwen2.5-VL-3B and with SFT on the same 3K data:

  | Benchmark | Base | SFT (same 3K) | GUI-R1 RFT |
  |---|---|---|---|
  | AC-High SR | 38.90 | 41.22 | 46.55 |
  | AC-Low SR | 59.32 | 58.79 | 64.41 |

  No AW number was reported. — [GUI-R1](https://arxiv.org/abs/2504.10458)
- InfiGUI-R1-3B reached AC-Low SR 92.1 and AC-High SR 71.1 (vs UI-TARS-2B at 89.3/68.9), ScreenSpot 87.5, ScreenSpot-Pro 35.7. No AW number. — [InfiGUI-R1](https://arxiv.org/abs/2504.14239)
- UI-AGILE-3B: AC-Low SR 74.3, AC-High SR 56.9. UI-AGILE-7B: 77.6 / 60.6. Both with only 9K samples (OS-Atlas evaluation protocol, 7,708 steps). — [UI-AGILE](https://arxiv.org/abs/2507.22025)

**Offline RFT that did not transfer**
- AgentCPM-GUI-8B is strong on AC-High (EM 69.2) but scored only 16.4 on AW in UI-S1's evaluation. — [UI-S1](https://arxiv.org/abs/2509.11543)
- In UI-S1's controlled comparison on Qwen2.5-VL-7B:

  | Variant | AC-High SR | AW |
  |---|---|---|
  | Base | 52.7 | 14.9 |
  | + Offline RL (GRPO, ground-truth history) | 59.0 | 15.7 |
  | + SFT | 56.1 | 21.7 |

  So offline RL raised AC-High SR but left AW essentially flat, and it degraded MiniWob++ (54.0 to 53.3). — [UI-S1](https://arxiv.org/abs/2509.11543)
- UI-S1 found that across models AC-High predicts AW poorly (R²=0.470). GUI-Odyssey is worse (R²=0.398). Its semi-online SOP metric reaches R²=0.934. — [UI-S1](https://arxiv.org/abs/2509.11543)

**Offline RFT that did transfer, at about 3B**
- Ferret-UI Lite-3B: step-wise RLVR on top of SFT raised AW from 25% to 28% (mean of 5 runs, 15-step cap) and OSWorld from 15% to 17.3%. — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- GUI-Libra-3B (Qwen2.5-VL-3B) on AW, 20-step cap:

  | Stage | AW |
  |---|---|
  | Base | 3.5 |
  | SFT | 5.2 |
  | Action-aware SFT (ASFT) | 13.0 |
  | ASFT + KL-regularized offline GRPO | 25.2 |

  — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- GUI-Libra-4B (Qwen3-VL-4B) went from 27.0 to 42.6 on AW, and GUI-Libra-8B from 30.4 to 42.6. GUI-Libra RL uses on-policy sampling on static step states with offline step-wise rewards and no environment interaction during training. — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- GHD's controlled comparison (Pass@1 over 3 runs):

  | Model | Method | AW | AndroidLab |
  |---|---|---|---|
  | Qwen2.5-VL-7B | SFT | 46.55 | 29.71 |
  | Qwen2.5-VL-7B | + GRPO | 47.13 | 31.93 |
  | Qwen2.5-VL-7B | + GHD | 52.73 | 43.10 |
  | Qwen3-VL-8B | SFT | 59.05 | 39.13 |
  | Qwen3-VL-8B | + GRPO | 61.35 | 37.43 |
  | Qwen3-VL-8B | + GHD | 66.47 | 54.11 |

  So plain offline GRPO on SFT moved AW by only +0.6 to +2.3 and lowered AndroidLab at 8B. — [GHD](https://arxiv.org/abs/2608.06065)
- UI-Venus-7B (GRPO-only RFT on 350K navigation samples) reports 49.1% on AW, and 72B reports 65.9%. Large-scale offline RFT with history alignment can transfer at 7B. — [UI-Venus](https://arxiv.org/abs/2508.10833)
- Reference points reported in GHD's Table 1 (secondary; not checked against the originals): Step-GUI-4B 63.9, MAI-UI-8B 70.7, UI-Venus-1.5-8B 73.7, OpenMobile-7B 51.7. Small Qwen3-VL-based models trained with much larger (often online) pipelines now reach 60%+ on AW. — [GHD](https://arxiv.org/abs/2608.06065)

**Thinking vs no-thinking**
- Grounding favors no-think:
  - UI-R1's ablation: THINK (UI-R1-3B) scored ScreenSpot-v2 85.4 / ScreenSpot-Pro 17.8, NOTHINK 86.4 / 32.1, DAST then NOTHINK (UI-R1-E-3B) 89.5 / 33.5. Their conclusion: "Reasoning is not essential for simpler tasks, such as GUI grounding." — [UI-R1](https://arxiv.org/abs/2503.21620)
  - GUI-G1 found longer reasoning chains consistently reduce ScreenSpot grounding accuracy, and accuracy tracks image tokens rather than text tokens. — [GUI-G1](https://arxiv.org/abs/2505.15810)
  - GTA1: adding a format/thinking reward to the click reward lowered ScreenSpot-Pro from 50.1 to 46.9 and OSWorld-G from 67.7 to 67.0 (7B). — [GTA1](https://arxiv.org/abs/2507.05791)
  - "Think or Not Think": No-Thinking-RL matches or beats thinking-based RFT on visual perception tasks across model sizes. Models with limited capability "struggle to generate high-quality CoT," which makes thinking-based RFT less effective. — [Think or Not](https://arxiv.org/abs/2503.16188)
- Navigation and online control favor (short) thinking:
  - GTA1: an in-domain 7B trained on AndroidControl had similar AC grounding with or without thinking, but AW success rose from 39% to 44% with thinking. — [GTA1](https://arxiv.org/abs/2507.05791)
  - GUI-Libra-3B: removing CoT from training dropped AW from 25.2 to 12.2 (ASFT: 13.0 to 5.2). Removing CoT only at inference dropped GUI-Libra from 25.2 to 18.3. — [GUI-Libra](https://arxiv.org/abs/2602.22190)
  - Ferret-UI Lite-3B SFT on AW: no CoT 13.7, short CoT 15.8, long CoT 19.6. — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
  - UI-AGILE: "No Thinking" is significantly worse on AC. "Simple Thinking" grounds better than "Normal Thinking" with comparable AC accuracy, and Normal Thinking needs 1.7x the training time. — [UI-AGILE](https://arxiv.org/abs/2507.22025)
  - UI-Venus: explicit thinking "significantly enhances" navigation, while grounding performs about the same with or without it. — [UI-Venus](https://arxiv.org/abs/2508.10833)
  - UI-R1 appendix: agents that produce reasoning beat direct-action agents by about 6% on action prediction. — [UI-R1](https://arxiv.org/abs/2503.21620)

### Inferences
- The project's numbers fit the published pattern. High AC-Low (0.948) and AC-High (0.715) with low AW (12.9%) is the same offline/online gap UI-S1 quantifies (R²=0.47). Plain GRPO on AC steps with gold history would most likely add a few AC points and about 0 to 3 AW tasks, based on the UI-S1 (+0.8), GHD (+0.6 / +2.3) and Ferret-UI Lite (+3) evidence.
- The large offline-RL AW gains (GUI-Libra +12 at 3B) came with three things together: CoT kept in training, KL ≈1e-3, and down-weighted negative gradients. They are not a free lunch from rule rewards.
- The current "short intent in <think>" design matches the best-supported setting for small models. UI-AGILE's "Simple Thinking" (120 to 200 characters) and GUI-Libra's mixed reasoning/direct-action data both point this way: keep a brief rationale for navigation and do not let it grow during RL.

### Gaps
- No paper reports AW for UI-R1-3B, GUI-R1-3B or InfiGUI-R1-3B themselves, so their offline gains cannot be directly mapped to online gains.
- Base Qwen2.5-VL-3B AW scores differ between harnesses: 3.5 (GUI-Libra), 5.0 (UI-S1), 16.8 (Ferret-UI Lite). Cross-paper AW comparisons are therefore noisy.
- No 2B-scale (or below) offline-RFT-to-AW result was found. The smallest data points are 3B.

## Q3. Does RFT on top of SFT beat more SFT? Data-efficiency claims

### Takeaway
On equal data, RFT usually beats SFT on grounding and OOD step metrics. On top of an SFT checkpoint it gives further but smaller online gains, which shrink the more SFT was done (Ferret-UI Lite). For in-distribution AC-High the benefit can be zero (AgentCPM-GUI). The well-supported data-efficiency claims (hundreds to a few thousand samples) are for grounding and step metrics, not for online task success.

### Cited Findings
**RFT vs SFT on the same data**
- GUI-R1 on GUI-R1-3K: RFT beat SFT at 3B on ScreenSpot (80.08 vs 63.55) and ScreenSpot-Pro (25.23 vs 13.80), on AC-High SR (46.55 vs 41.22) and on AC-Low SR (64.41 vs 58.79). Small-scale SFT even lowered some metrics below base (AC-Low grounding). — [GUI-R1](https://arxiv.org/abs/2504.10458)
- UI-R1: SFT on 500 samples helps in-domain grounding, but its benefit "significantly diminishes in OOD scenarios." RFT on 136 samples generalizes better. — [UI-R1](https://arxiv.org/abs/2503.21620)

**RFT stacked on SFT**
- AgentCPM-GUI-8B, SFT-only vs SFT+RFT (exact match):

  | Benchmark | SFT | SFT + RFT |
  |---|---|---|
  | AC-Low | 83.1 | 90.2 |
  | GUI-Odyssey | 66.7 | 75.0 |
  | AITZ | 61.1 | 76.4 |
  | AC-High | 69.5 | 69.2 |
  | CAGUI | 91.5 | 91.3 |

  The authors attribute the flat AC-High and CAGUI results to those sets having large, diverse training splits, where "imitation learning alone generalizes well." — [AgentCPM-GUI](https://arxiv.org/abs/2506.01391)
- Ferret-UI Lite-3B: RLVR after 2K, 6K or 10K SFT steps improves AW in every case, and "the gains are most pronounced when the number of SFT steps is smaller." Final result: SFT 25 to RL 28. — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- UI-S1-7B on AW: SFT only 21.7, semi-online RL only 30.4, SFT then semi-online RL 34.0. — [UI-S1](https://arxiv.org/abs/2509.11543)
- GUI-Libra-3B on AW: SFT 5.2 to action-aware SFT 13.0 to +RL 25.2. Better SFT accounts for about 8 points and RL for about 12. — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- GHD, 7B/8B on AW: offline GRPO adds +0.6 / +2.3 over SFT, and gated hindsight distillation adds +6.2 / +7.4 over SFT under identical data and initialization. — [GHD](https://arxiv.org/abs/2608.06065)

**Data-efficiency claims (grounding and step metrics)**
- UI-R1: 136 samples, comparable to OS-Atlas-7B SFT on 76K. — [UI-R1](https://arxiv.org/abs/2503.21620)
- GUI-R1: 3K vs 13M+, "0.02% of the data." — [GUI-R1](https://arxiv.org/abs/2504.10458)
- SE-GUI-7B: 3K samples reach ScreenSpot-Pro 47.3, above UI-TARS-72B at 38.1. — [SE-GUI](https://arxiv.org/abs/2505.12370)
- GUI-G1-3B: 17K samples, ScreenSpot 90.3 / ScreenSpot-Pro 37.1. — [GUI-G1](https://arxiv.org/abs/2505.15810)
- UI-AGILE: 9K samples. — [UI-AGILE](https://arxiv.org/abs/2507.22025)

**Data efficiency for semi-online RL (AW)**
- UI-S1 with thought-free patch at ε=1 reached AW 24.0 / 29.1 / 34.0 with 200 / 500 / 1000 training trajectories. Performance follows an exponential saturation law, and larger ε makes each sample more useful. — [UI-S1](https://arxiv.org/abs/2509.11543)
- SOLAR-RL (7B, 15K trajectories / 94K steps) reports AW 33.7. It argues this is comparable to UI-TARS-7B-SFT (33.3, trained on 145K trajectories). UI-Venus (49.1) used about 350K steps. — [SOLAR-RL](https://arxiv.org/abs/2604.22558)

**Data selection matters as much as quantity**
- UI-R1 chooses "hard" samples (base model wrong), and this beat random selection and the full dataset. — [UI-R1](https://arxiv.org/abs/2503.21620)
- GUI-R1 drops samples with accuracy 0 or 1. — [GUI-R1](https://arxiv.org/abs/2504.10458)
- SE-GUI: filtering lifts ScreenSpot-Pro from 31.3 to 40.0 with dense reward. — [SE-GUI](https://arxiv.org/abs/2505.12370)
- GHD trains only on examples its SFT model fails. — [GHD](https://arxiv.org/abs/2608.06065)

### Inferences
- With a well-trained LoRA SFT (AC-High 0.715), continuing SFT on AC is unlikely to move AW much. Running plain offline GRPO on the same AC steps is also likely to give small gains; AgentCPM-GUI saw no AC-High gain, and GHD and UI-S1 saw tiny AW gains.
- The evidence points to changing what the model is trained on (its own history, hard and failed steps, hindsight information) rather than switching from SFT to RL on unchanged data.
- Hard-example mining is cheap and consistently helpful: keep only AC steps where the current SFT checkpoint fails or is inconsistent across 8 samples. It also removes zero-variance GRPO groups.

### Gaps
- No controlled "same compute, more SFT epochs vs RFT" comparison measured on AW was found. Existing comparisons hold data constant, not compute.
- The low-data claims (136 / 3K samples) were never validated online by their authors.

## Q4. Semi-online RL: simulating multi-turn rollouts from static trajectories, history patching, AndroidWorld gains

### Takeaway
UI-S1 rolls the policy through an expert trajectory while keeping the model's own thoughts and actions in its history:
- The next state is the expert's next screenshot whenever the action matches.
- On a mismatch, a patch module substitutes the expert action (optionally with a synthetic thought) and continues, up to ε times.
- Rewards are discounted over the matched segment, and the advantage combines step-level and episode-level terms.

This gave the biggest documented static-data AW gains at 7B: +12.3 over SFT and +19.1 over the base in UI-S1's own harness. It is also positive at 3B, though from a low base (5.0 to 13.1 without SFT). Successors (SOLAR-RL, GHD) refine credit assignment or add hindsight supervision.

### Cited Findings
**UI-S1 diagnosis: mismatch between training and deployment history**
- Offline RL conditions each step on expert history, H_static = {(S*, a*)}. At deployment the agent conditions on its own outputs, H_online = {(S, a^π, T^π)}. Statically trained agents "never learn to process their own outputs or recover from errors." — [UI-S1](https://arxiv.org/abs/2509.11543)

**Rollout mechanics**
- For an expert trajectory τ*, sample N rollouts. Each keeps its own history H_t^i = {(S, a^i, T^i)}. If Matches(a_t^i, a_t*), then S_{t+1} = S*_{t+1}; otherwise the rollout ends unless patched. — [UI-S1](https://arxiv.org/abs/2509.11543)

**Patch module**
- On a mismatch, the wrong action is replaced by a_t* and the rollout continues with H_{t+1} = H_t ∪ {(S_t, a_t*, T_patch)}, up to ε patches. Three patch variants were compared:

  | Patch type | Thought used | SOP score (1K data, ε=∞) | Notes |
  |---|---|---|---|
  | Thought-free | empty | 25.7 | cheapest |
  | Off-policy | from an auxiliary model, e.g. DeepSeek-R1 | 22.6 | style mismatch hurts |
  | On-policy | policy generates it given the expert-action hint | 26.1 | best |

  The final configuration is thought-free with ε=1. — [UI-S1](https://arxiv.org/abs/2509.11543)
- ε effect at 1K samples, thought-free: SOP score 22.3 (ε=0) to 25.7 (ε=∞), +15% relative. AW goes 30.0 to 34.0 to 33.9 to 34.5 for ε=0/1/2/∞. Larger ε keeps policy entropy higher. — [UI-S1](https://arxiv.org/abs/2509.11543)

**Reward and advantage**
- Step reward: r_t = 0.1·r_format + 0.4·1[format]·r_type + 0.5·1[format·type]·r_exact_match. — [UI-S1](https://arxiv.org/abs/2509.11543)
- Discounted return R_t = Σ γ^(k−t) r_k, summed only up to the end of the naturally matching segment. Using the full patched length instead was slightly worse: AW 28.0 vs 27.9 at ε=1, and 28.9 vs 27.7 at ε=2. — [UI-S1](https://arxiv.org/abs/2509.11543)
- Advantage A = A_episode + ω·A_step, where A_step is normalized across rollouts at the same step. Dynamic sampling resamples until advantage std > η=0.3. γ=0.5 was best; γ=0 (no future reward) was worst. — [UI-S1](https://arxiv.org/abs/2509.11543)

**Results**
- Qwen2.5-VL-7B on AW (UI-S1 prompt):

  | Variant | AW |
  |---|---|
  | Base | 14.9 |
  | + SFT | 21.7 |
  | + Offline RL | 15.7 |
  | + Semi-online RL only | 30.4 |
  | SFT + semi-online (UI-S1-7B) | 34.0 |

  AITW-Gen went 50.5 to 74.3, and AC-High SR 52.7 to 68.2. UI-S1-7B also needs fewer steps per AW task than SFT. — [UI-S1](https://arxiv.org/abs/2509.11543)
- Model-size scaling without SFT cold start (AW):

  | Model | Base | UI-S1 |
  |---|---|---|
  | 3B | 5.0 | 13.1 |
  | 7B | 14.9 | 30.4 |
  | 32B | 28.3 | 38.9 |

  "As the model size increases, the relative performance improvement diminishes." — [UI-S1](https://arxiv.org/abs/2509.11543)
- In the case study, the offline-RL model "terminate[s] prematurely after planning to navigate to the next app, likely due to overfitting to local rewards." The SFT model loses information and repeats redundant actions. — [UI-S1](https://arxiv.org/abs/2509.11543)
- Ablations show both episode-level advantages and multiple historical images (2 used) help. — [UI-S1](https://arxiv.org/abs/2509.11543)

**SOP (Semi-Online Performance) metric**
- Evaluates AC-Test multi-turn with the model's own history and stops at the first mismatch. Reports PG (fraction of steps completed) and TSR (fraction of fully completed tasks). Correlates with AW at R²=0.934, vs 0.470 for AC-High. — [UI-S1](https://arxiv.org/abs/2509.11543)

**SOLAR-RL (2026 successor)**
- Reconstructs N=8 candidate rollouts per step from static data and detects the first failure point using per-step validity checks (coordinate distance, text F1, type match). It then reassigns dense step rewards so the total matches trajectory quality, concentrating credit on steps before the breakdown. — [SOLAR-RL](https://arxiv.org/abs/2604.22558)
- Per-action scoring: Gaussian on click distance; Gaussian times direction match for scroll; F1 for type; app-name similarity >0.9 for launch; exact match for system actions. — [SOLAR-RL](https://arxiv.org/abs/2604.22558)
- 7B results: AW 33.7, AC-High SR 69.27. Plain GRPO with sparse trajectory rewards "collapses" late in training on very long tasks, which SOLAR-RL avoids. The largest stability gains are on Launch, Scroll and Finished actions. — [SOLAR-RL](https://arxiv.org/abs/2604.22558)

**Related static-data alternatives**
- UI-Venus "Self-Evolving Trajectory History Alignment" rewrites the historical thoughts between epochs to match the agent's own evolving reasoning style. It also oversamples rare actions (e.g. LongPress) under several sampled history variants. — [UI-Venus](https://arxiv.org/abs/2508.10833)
- GHD: a parameter-sharing teacher sees the next screenshot and re-scores the student's on-policy samples. Token-level distillation is applied only when the student fails and the teacher recovers the demonstrated action. — [GHD](https://arxiv.org/abs/2608.06065)
- In GHD's ablation, a teacher given only the reference action does not help (−0.43 vs SFT). The next screenshot is what provides the gain (+7.42 at 8B). — [GHD](https://arxiv.org/abs/2608.06065)
- Mobile-R1 notes that applying task-level rewards directly converges poorly because success signals are sparse. It uses a curriculum: format SFT, then action-level GRPO, then multi-turn task-level GRPO in a real environment. — [Mobile-R1](https://arxiv.org/abs/2506.20332)

### Inferences
- The project's SFT almost certainly conditions on gold history (gold intents/actions). Semi-online training, or simply rolling the SFT model through AC trajectories and training on its own intent history, directly targets the "no recovery" and "loops" failures that UI-S1 attributes to the static-history mismatch.
- The thought-free patch at ε=1 is cheap and fits a "short intent" format: on a mismatch, insert the gold action with an empty (or templated) intent.
- Compute is the binding constraint. Each semi-online trajectory needs T sequential policy calls per rollout. UI-S1 got AW 24.0 from only 200 trajectories at 7B, which suggests a few hundred AC episodes x 8 rollouts could fit in a few GPU-hours for a 2B model. This is extrapolated, not reported.
- SOP (AC-Test with self-history, stop at first mismatch) is a cheap offline proxy that would let the project screen checkpoints before spending emulator time. UI-S1 reports R²=0.93 with AW.

### Gaps
- UI-S1's rollout count N per trajectory, wall-clock time and GPU-hours were not recoverable from text (there is a GPU-hours figure).
- No semi-online result below 3B was found. UI-S1-3B (13.1 AW) was trained without SFT, so the effect of SFT followed by semi-online at 3B is unknown.
- SOLAR-RL and UI-S1 were not compared head-to-head under one harness.

## Q5. Pitfalls: reward hacking on coordinates, length collapse, grounding vs planning trade-offs, offline-online decorrelation

### Takeaway
The documented failure modes are:
- Box-size reward hacking (hit reward shrinks boxes; IoU reward grows them).
- Sparse binary point rewards giving erratic or zero gradients.
- GRPO length and difficulty biases (long wrong answers, under-training on hard samples).
- Format reward saturating early and dominating.
- KL-free RL raising training reward while online success falls and entropy collapses.
- Rewards being only partially verifiable (valid alternative actions get punished).
- Offline RL learning to stop early.
- Mode collapse when RL runs on GUI-only data or without a reasoning warm-up.
- Conflicts between grounding and navigation rewards.

### Cited Findings
**Coordinate and box reward hacking**
- R_hit drives predicted boxes smaller (accuracy up, IoU down). R_IoU drives them larger (IoU up, accuracy down). Fix: combine both with a box-size regularizer R_box. R_box alone fails to optimize format. — [GUI-G1](https://arxiv.org/abs/2505.15810)

**Sparse vs dense coordinate rewards**
- On ScreenSpot-v2 (7B): sparse Point 87.4, IoU 85.8, Point+IoU 86.5, Gaussian dense 93.3. — [GUI-G2](https://arxiv.org/abs/2507.15846)
- Sparse rewards show "erratic fluctuations" in distance to target, while Gaussian rewards converge monotonically. — [GUI-G2](https://arxiv.org/abs/2507.15846)
- Fixed variance scores 87.8 vs 93.3 for adaptive σ = 0.5 x element size. — [GUI-G2](https://arxiv.org/abs/2507.15846)
- SE-GUI: dense beats sparse on ScreenSpot-Pro (filtered data 35.8 to 40.0). — [SE-GUI](https://arxiv.org/abs/2505.12370)
- Ferret-UI Lite navigation: a dense distance reward beats a sparse in-bbox reward on AW. Type-only reward drops AW below SFT; grounding-only does not beat SFT. "Small models … are sensitive to RL reward designs." — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- Counterpoint: GTA1 found a plain binary click reward best for grounding at 7B. Adding IoU or format terms lowered ScreenSpot-Pro (50.1 to 42.2 or 46.9). — [GTA1](https://arxiv.org/abs/2507.05791)

**Zero-signal groups**
- In UI-AGILE's first epoch only 61.8% of steps succeeded on the first attempt, so 19.1% to 38.2% of samples gave no learning signal. Cropping-based resampling added +12.4% on ScreenSpot-Pro, and the continuous reward +10%. — [UI-AGILE](https://arxiv.org/abs/2507.22025)
- Ferret-UI Lite and UI-S1 both filter or resample zero-variance groups (UI-S1 uses η=0.3). — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539); [UI-S1](https://arxiv.org/abs/2509.11543)

**Length bias and length collapse**
- GRPO's 1/|o| normalization favors short correct and long incorrect responses. During training, incorrect responses got longer and correct ones shorter, which hurts grounding. Fix: constant normalization (Max_Tokens) plus difficulty weighting. — [GUI-G1](https://arxiv.org/abs/2505.15810)
- GUI-R1: mean response length first falls, then rises, and no "aha moment" appears in single-image non-interactive training. — [GUI-R1](https://arxiv.org/abs/2504.10458)
- UI-R1-E adds an explicit DAST length budget before going no-think. — [UI-R1](https://arxiv.org/abs/2503.21620)

**Format reward dominance**
- Format reward converges early. Lowering its weight (α 0.8 to 0.2) improved AC-High and GUI-Odyssey. — [GUI-R1](https://arxiv.org/abs/2504.10458)
- Most later recipes use format weight 0.1 (InfiGUI-R1, UI-S1, GUI-Libra). — [InfiGUI-R1](https://arxiv.org/abs/2504.14239); [UI-S1](https://arxiv.org/abs/2509.11543); [GUI-Libra](https://arxiv.org/abs/2602.22190)

**KL and offline-online decorrelation**
- With KL=0, training reward curves match the KL runs, but offline (AC-High) and online (AW) performance degrade as reward rises, and policy entropy collapses. The authors call this "a form of reward hacking." — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- AW results by KL setting at 3B: KL 0 gives 21.7, 0.001 gives 25.2, 0.01 gives 21.7, 0.05 gives 20.0. — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- Correlation between offline and online scores across checkpoints is Pearson 0.76 overall. With KL>0 it rises to Pearson 0.89 and Spearman 0.83. — [GUI-Libra](https://arxiv.org/abs/2602.22190)

**Partial verifiability**
- A step reward that credits only the single demonstrated action treats valid alternatives as failures. Positive feedback is reliable; negative feedback is ambiguous. — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- Success-adaptive negative-gradient scaling (SNGS) raised 3B AW to 25.2, vs 19.1 / 20.0 with uniform negative scaling of 0.75 / 0.9. At 4B it gave 39.1 to 42.6. — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- SoLS applies a related idea in off-policy RL: unregularized updates on positive samples, conservative updates on negative ones. Reports at least 17% relative improvement on AW (abstract only). — [SoLS](https://arxiv.org/abs/2509.01720)

**Grounding vs planning (CoT interference)**
- SFT with long CoT hurts grounding: SFT-3B in reasoning mode grounds at 73.4, while action-aware SFT in no-reason mode reaches 81.0. Reweighting action/grounding tokens (α_a=2, α_g=4) and mixing direct-action data recover most of the gap. After RL, reasoning-mode and no-reason grounding are equal (83.4 vs 83.2 at 3B). — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- UI-AGILE likewise: grounding accuracy falls and AC accuracy rises from No to Simple to Normal thinking. — [UI-AGILE](https://arxiv.org/abs/2507.22025)

**Premature termination and myopia from step rewards**
- Offline RL "terminate[s] prematurely" (UI-S1 case study). — [UI-S1](https://arxiv.org/abs/2509.11543)
- Mobile-R1: action-level rewards "can easily lead to local optima." Its stage-3 model correctly stops on a "Followed" state that the stage-2 model kept clicking past. — [Mobile-R1](https://arxiv.org/abs/2506.20332)
- SOLAR-RL's largest stability gains are on the Finished, Launch and Scroll primitives. — [SOLAR-RL](https://arxiv.org/abs/2604.22558)

**Mode collapse and cold start**
- AgentCPM-GUI: without a thought warm-up during SFT, the model "failed to generate reasoning traces during the RFT stage." — [AgentCPM-GUI](https://arxiv.org/abs/2506.01391)
- AgentCPM-GUI: training only on GUI data caused "pronounced mode collapse" in RFT (repetitive thoughts). Mixing 50% general multimodal data into SFT fixed it. — [AgentCPM-GUI](https://arxiv.org/abs/2506.01391)
- UI-S1: an off-policy thought patch from a stronger model hurts because its reasoning style does not match the policy's. — [UI-S1](https://arxiv.org/abs/2509.11543)

**Reward conflicts and rare actions**
- Mixing grounding rewards (as single-step clicks) with navigation rewards "can lead to unstable training, ultimately degrading performance on both tasks." — [UI-Venus](https://arxiv.org/abs/2508.10833)
- Rare but pivotal actions (LongPress, CallUser) are under-learned unless oversampled. — [UI-Venus](https://arxiv.org/abs/2508.10833)
- UI-Venus rebuilds information-retrieval traces by inserting the explicit answers, which bears on "never answers" failures. — [UI-Venus](https://arxiv.org/abs/2508.10833)

**Noisy data and validity checks**
- About half of open-source UI data contains noise (UI-Venus's estimate). — [UI-Venus](https://arxiv.org/abs/2508.10833)
- GTA1 filters annotations that are misaligned with OmniParser detections. — [GTA1](https://arxiv.org/abs/2507.05791)
- UI-R1 excluded AndroidControl click steps from RL because AC element boxes are "unfiltered and misaligned." — [UI-R1](https://arxiv.org/abs/2503.21620)
- GUI-Libra found AC has action-type and coordinate mismatches and built a cleaned AndroidControl-v2. — [GUI-Libra](https://arxiv.org/abs/2602.22190)

### Inferences
**Mapping the project's failure modes to the literature**
- "Never answers": AC has no answer action, so no AC-only reward can teach it. Answer-bearing trajectories must be added (UI-Venus-style trace reconstruction), or rewarded via AW-like synthetic tasks.
- "Premature complete": UI-S1, Mobile-R1 and SOLAR-RL all report that step-only (myopic) rewards cause early stopping. A semi-online or discounted-return reward, or extra weight on terminal-action correctness, is the documented remedy.
- "Loops" and "no recovery": consistent with gold-history training. Semi-online self-history, plus error-recovery trajectories (InfiGUI-R1's 2K reflection trajectories), are the evidence-backed fixes.

**Reward advice for AC-based GRPO**
- If GRPO is run on AC clicks, use a dense or Gaussian point reward with size-adaptive σ, or a containment reward on cleaned boxes. Do not use raw AC bboxes uncritically, given that UI-R1 and GUI-Libra both flag AC box and type mismatches.
- Keep a small KL (about 1e-3), weight format at about 0.1, filter zero-variance groups, and monitor entropy and response length.

### Gaps
- No paper reports reward hacking specific to 0-1000 normalized coordinates, e.g. snapping to screen-center priors. Evidence is limited to box-size hacking and sparse-reward instability.
- No quantitative report found on loop frequency or premature-stop rates before and after RFT on AW. Evidence is case studies.
- AndroidFlux (arXiv 2610.34384, failure-recovery reward modeling) and Adaptive Milestone Reward (arXiv 2602.11524) appeared in search but were not read.

## Q6. What concrete recipe does the evidence support for a 2B model on 1x 96GB GPU for a few hours?

### Takeaway
The evidence favors a semi-online or self-history variant of GRPO on a few hundred to about 1K AndroidControl trajectories, starting from the existing SFT checkpoint, over plain offline GRPO with gold history. Use a thought-free patch at ε=1, γ≈0.5, 8 rollouts, lr ≈1e-6 (LoRA may need higher), small KL, rewards weighted format 0.1 / type 0.4 / params 0.5 with a dense click term, and hard-example mining. Screen checkpoints with SOP before AW runs. Expected AW gains at 2B are uncertain: published 3B results range from +3 to +12 points.

### Cited Findings
- UI-S1 semi-online settings: γ=0.5, ω=1, ε=1 thought-free patch, η=0.3, lr 1e-6, KL 1e-4, 2 history images, 5 epochs, 1K trajectories (AW 34.0 at 7B; 200 trajectories gave 24.0). — [UI-S1](https://arxiv.org/abs/2509.11543)
- The UI-S1 step reward (0.1 format + 0.4 type + 0.5 exact, each gated on the previous term) and GUI-Libra's 0.1 / 0.9 split both down-weight format. — [UI-S1](https://arxiv.org/abs/2509.11543); [GUI-Libra](https://arxiv.org/abs/2602.22190)
- At 3B: KL 0.001 was best (AW 25.2). CoT kept in training. SNGS for ambiguous negatives. — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- Dense click reward max(1 − 0.5·(|dx|/w + |dy|/h), 0) beats the sparse bbox reward on AW at 3B. Type-only or grounding-only rewards fail. — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- Gaussian point reward with σ = 0.5 x element size is the best-documented dense grounding reward. — [GUI-G2](https://arxiv.org/abs/2507.15846)
- Short "Simple Thinking" (120 to 200 characters) balances grounding, planning and 1.7x lower training time than normal thinking. — [UI-AGILE](https://arxiv.org/abs/2507.22025)
- Train only on samples the current SFT model fails (GHD), or on hard samples (UI-R1). — [GHD](https://arxiv.org/abs/2608.06065); [UI-R1](https://arxiv.org/abs/2503.21620)
- Compute references:
  - UI-R1-3B: 8x RTX 4090, about 8 hours. — [UI-R1](https://arxiv.org/abs/2503.21620)
  - GHD: 4 GPUs, 200 steps. — [GHD](https://arxiv.org/abs/2608.06065)
  - GUI-Libra-4B RL: 8x B200, about 16 hours for 300 iterations on 40K samples. — [GUI-Libra](https://arxiv.org/abs/2602.22190)
  - SOLAR-RL-7B: 32x L40S, about 60 hours. — [SOLAR-RL](https://arxiv.org/abs/2604.22558)
- Hindsight distillation, where the teacher sees the next screenshot and distillation is gated on student failure, adds +5.6 AW over GRPO at 7B with no extra modules at inference. — [GHD](https://arxiv.org/abs/2608.06065)

### Inferences
**Suggested order of experiments (inferred from the cited evidence, not a published recipe)**
1. Build SOP-style evaluation on AC-Test with the model's own intent history, plus a hard subset where the SFT model fails.
2. Run semi-online GRPO (thought-free patch, ε=1, γ=0.5) on about 300 to 1000 AC episodes. Use the dense click reward, a small KL (1e-4 to 1e-3), 8 rollouts, and zero-variance filtering.
3. Add answer-bearing and recovery trajectories, to address "never answers" and "no recovery".
4. If budget remains, try GHD-style hindsight distillation. It reuses the same static data and shares parameters with the policy.

**Budget estimate**
- At 2B with 8 rollouts x about 5 to 6 steps per AC episode, 500 episodes is about 20K to 25K generations per epoch. That is plausibly 1 to 3 hours on one 96GB GPU with vLLM-style batched generation and short outputs. This is an engineering estimate, not a reported figure.

**Risks specific to this project**
- All cited work uses Qwen2.5-VL or Qwen3-VL (or Apple's 3B). LFM3-VL-2B's hybrid conv/attention backbone and LoRA have no published GUI-RFT precedent.
- UI-S1's diminishing-returns-with-scale finding cuts in the project's favor: relative gains were larger at 3B. However, the absolute 3B AW after semi-online RL without SFT was only 13.1%.

### Gaps
- No published 2B-scale or LoRA-based GUI RFT with AW evaluation was found.
- No published wall-clock numbers exist for semi-online RL on a single GPU.
- Not examined: newer online and hybrid methods surfaced by search (UI-Voyager 2603.24533, UI-Mem 2602.05832, Android Coach 2604.07277, PhoneBuddy 2606.23049, "Generalization in Online RL for Mobile Agents" 2603.07432). They need emulator-in-the-loop training and fall outside the static-data scope, but some may offer cheaper online alternatives at small scale.
