# Training-side tunables that move AndroidWorld-style online success for small (≤4B) GUI agents

Scope note: this pass deliberately focuses on what the earlier report (`reports/Small GUI agent training methods.md`) did not cover, got wrong, or that appeared after it (mostly Feb–Nov 2026 papers). Facts carried over from that report without re-reading the primary source are marked "(carried over, not re-read)". "AW" = AndroidWorld (116 tasks), "AC" = AndroidControl, "MW" = MobileWorld GUI-only (117 tasks). All sizes are total parameters. Unless stated, backbones are Qwen-family.

## Q1. SFT variants: own-history / on-policy data, recovery data, no-op and loop handling, terminal/answer supervision, label masking, action-token weighting, negatives

### Takeaway
The best new small-model evidence for our failure modes is VeriGUI-3B: injecting about 30% synthetic "action had no effect" samples into SFT raised recovery from injected failures from 29.7% to 45.5% and cut the repeat-the-failed-action rate from 30.4% to 26.5%. It cost under 1 point of step accuracy, and plain SFT made looping slightly *worse* than the base model. The earlier report's attribution for GUI-Libra needs correcting: most of the 3B AW gain (5.2→11.3) came from **mixing in direct-action copies of the data**. Action-token loss reweighting added only 11.3→13.0. On-policy history methods (UI-S1, OpenMobile, DAgger) still have no ≤4B AW ablation.

### Cited Findings
**Failure/no-op injection (VeriGUI, Qwen2.5-VL-3B, full SFT then offline GRPO)**
- Robust SFT builds "Type B" samples by pairing the *previous* screenshot S(t-1) with a history that claims the gold action was executed, so the screen did not change. The target output diagnoses NO_CHANGE and emits a corrective action. Failure types and weights: coordinate offset 30%, wrong action type 25%, wrong target 20%, timing/wait error 15%, null click on blank region 10%. GPT-4o wrote the CoT for both paths — [VeriGUI](https://arxiv.org/abs/2604.05477)
- AC-High robustness ablation, 3B. Rows give step SR, simulated task SR, loop rate (LR, lower is better) and recovery success rate (RSR). Base: SR 31.2, Sim-TSR 0, LR 30.0, RSR 35.0. Standard SFT: SR 42.6, Sim-TSR 10.0, **LR 30.4, RSR 29.7**. Robust SFT (70:30 success:failure): SR 41.7, Sim-TSR 13.3, **LR 26.5, RSR 45.5**. Adding offline GRPO (KL 0.05, G=6, 15 epochs): SR 46.6, Sim-TSR 16.7, LR 24.3, RSR 51.1 — [VeriGUI](https://arxiv.org/abs/2604.05477)
- Ratio ablation on the same setup. 100:0 gives RSR 29.7. 90:10 gives RSR 30.3, essentially no gain. **70:30 gives RSR 45.5 at SR 41.7.** 50:50 gives RSR 45.4 but SR falls to 39.2. "Without failure samples, no verification capability develops" — [VeriGUI](https://arxiv.org/abs/2604.05477)
- Online: VeriGUI-3B reaches **AW 12.6%** and MiniWoB++ 35.6%; VeriGUI-7B reaches AW 25.1%. **No AW ablation separates robust SFT from standard SFT.** Compute was 8×A100: about 12 h SFT plus about 20 h GRPO — [VeriGUI](https://arxiv.org/abs/2604.05477)
- The authors' qualitative case: the base model repeats a failed "open app" action forever. After robust SFT it sometimes notices the unchanged screen. After GRPO with an asymmetric penalty for "overconfident success claims", it recovers after one attempt — [VeriGUI](https://arxiv.org/abs/2604.05477)

**Action-aware SFT (GUI-Libra): correction to the earlier report**
- Qwen2.5-VL-3B, full-parameter SFT, lr 1e-5, effective batch 256, 2 epochs (1 epoch on the doubled mixed set). AW success: base 3.5, SFT (reasoning) 5.2, **SFT + mixed direct-action data 11.3**, ASFT (mixed + action/grounding token reweighting) 13.0. Mixing is therefore +6.1 and reweighting +1.7 — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- The direct-action data is the same samples with the reasoning removed, keeping only the action. The reweighting loss is (CoT + α_a·action + α_g·grounding) normalized by (|c| + α_a|a| + α_g|g|). The α values were not in the retrieved passages — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- Grounding at 3B (ScreenSpot-v2): plain SFT in reasoning mode 73.4. ASFT 76.2 in reasoning mode and 81.0 in no-reason mode — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- Data filtering (about half the data kept) improved AC-High by +4.5 Pass@1 and +6.3 Pass@4 after SFT at 3B — [GUI-Libra](https://arxiv.org/abs/2602.22190)

**Answer / memory supervision for information-retrieval tasks**
- GUI-SD-v2 (Qwen3-VL-8B) splits AW into 27 information-retrieval and 89 task-completion tasks. Adding privileged *memory* guidance (the teacher marks what to retain for later) raised IR success from 12/27 to 15/27. Reasoning plus memory guidance gave 16/27 IR and 62/89 task completion. This is distillation (Q3), not plain SFT, and at 8B — [GUI-SD-v2](https://arxiv.org/abs/2609.27307)
- Ferret-UI Lite-3B gained on AW from adding synthetic QA plus navigation data (see Q4 data curve), but the QA share was not separated out — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)

**Negative gradients and false negatives**
- GUI-Libra-4B success-adaptive negative-gradient scaling (SNGS) moved AW from 39.1 to 42.6, at the RL stage — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- LiteGUI-2B (Qwen3-VL-2B, desktop OSWorld): plain GRPO after on-policy distillation *dropped* OSWorld from 11.56 to 6.56. A reward that accepts any of several annotated valid actions restored 11.84, and adding a judge-scored subtask reward gave 13.24 — [LiteGUI](https://arxiv.org/abs/2605.07505)

**On-policy / own-history SFT (carried over, not re-read)**
- UI-S1-7B semi-online RL took AW from 21.7 (SFT) to 34.0 at 7B. OpenMobile-7B error-intervention data scored 48.3, against 44.8 for expert distillation and 33.8 for self-evolution. DigiRL's 1.3B filtered behaviour cloning took AitW from 17.7% to 57.8% — [UI-S1](https://arxiv.org/abs/2509.11543), [OpenMobile](https://arxiv.org/html/2604.15093) (carried over, not re-read)

### Inferences
- VeriGUI's Type-B construction is almost exactly the earlier report's "injected no-op recovery" idea and is fully offline. It gives a ratio prior to start from: about 30% of steps, enough to produce the behaviour, while above 50% hurts step accuracy. It is the only ≤4B controlled number for loop reduction found. Its task-level metrics move in steps of about 3.3 points (6.7 / 10.0 / 13.3 / 16.7), which suggests roughly 30 evaluated trajectories, so the Sim-TSR differences are noisy. The loop and recovery rates come from a larger slice set.
- GUI-Libra's large "mixing" effect is about protecting grounding from *long* CoT (~200 tokens). Our one-sentence intent is closer to its no-reason mode, so expect much less than +6 from mixing in direct-action rows. Action-token upweighting alone (+1.7 at 3B, single AW run of unknown variance) is within noise for one 116-task pass.
- Standard SFT slightly *raising* the loop rate (30.0→30.4) is consistent with our observation that gold-history SFT does not teach the model to notice its own no-ops.

### Gaps
- No ≤4B paper ablates label masking of repeated or `wait` steps (Xiaomi-GUI-0's masking claim has no number), terminal-status supervision on its own, or an `answer`-action data share against AW success.
- No ≤4B AW number for DAgger/own-history SFT. UI-S1 and OpenMobile are 7B/8B only.
- No evidence found on fixing misspelled or nonexistent app names through training.

## Q2. Offline vs online RL at ≤4B: GRPO variants, KL, reward design, environments/rollouts, small-compute RL

### Takeaway
At ≤4B, offline step-level GRPO helps when the reward is shaped carefully (action type + dense grounding) and a small KL is kept. GUI-Libra-3B went from 13.0 to 25.2 on AW with KL 1e-3, against 21.7 at KL 0 and 20.0 at KL 0.05. Ferret-UI Lite-3B gained only +3. Online RL at 2B has been shown only with 64+ parallel emulators and multi-GPU nodes; ClawGUI-2B went from 11.1 to 17.1 on MobileWorld. The only single-GPU RL evidence is offline: UI-R1 used 136 samples (offline AC metrics only), and Liquid's own LFM3-VL-2B demo ran SFT+GRPO "a few hours on one A100", outside GUI.

### Cited Findings
**Offline GRPO with KL (GUI-Libra, Qwen2.5-VL-3B, step-wise RL on static data, AW success)**
- ASFT 13.0. RL without ASFT at KL 1e-3: 20.9. **ASFT+RL at KL 0: 21.7; KL 1e-3: 25.2; KL 1e-2: 21.7; KL 5e-2: 20.0.** Higher KL raises Pass@4 but can lower Pass@1. Without KL, the offline-to-online correlation weakened (Pearson r=0.63, Spearman 0.53, p=0.053) — [GUI-Libra](https://arxiv.org/abs/2602.22190)

**Reward design at 3B (Ferret-UI Lite, internal non-Qwen 3B, AW averaged over 5 runs)**
- SFT checkpoint about 25 → about 28 after RLVR (10K SFT steps, 1,500 RL steps, 32 samples per navigation prompt, online filtering that drops all-equal reward groups) — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- Reward ablation: action-type reward alone "leads to a substantial drop". Grounding reward alone "does not surpass the SFT baseline". Type plus grounding improves, and **dense grounding beats sparse (in-box) grounding**. Exact values are only in a figure — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- The RL gain is largest when fewer SFT steps precede it (2K vs 6K vs 10K) — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- On AC-High robustness (3B), VeriGUI found that adding verification and effect-prediction rewards to the action reward raised RSR from 44.9 to 51.1 and SR from 42.9 to 46.6 — [VeriGUI](https://arxiv.org/abs/2604.05477)

**Online RL at 2B (ClawGUI-2B, base MAI-UI-2B, MobileWorld GUI-only)**
- 64 parallel Docker emulators on 8×A6000 48GB. GiGPO, group 8, temperature 0.7, lr 1e-6, 3 epochs, batch 8. Qwen3.5-72B serves as the step-level process-reward judge. Result: **11.1 → 17.1**. Episode-level binary GRPO under the same pipeline gave 14.5, so step-level credit adds 2.6, which is about 3 of 117 tasks — [ClawGUI](https://arxiv.org/abs/2604.11784)
- MAI-UI (2B–235B): scaling parallel environments from 32 to 512 gave +5.2, and the step budget from 15 to 50 gave +4.3 — [MAI-UI](https://arxiv.org/abs/2512.22047)

**Small-compute / tiny-data RL**
- UI-R1-3B: GRPO on **136** difficulty-selected samples (ScreenSpot mobile plus AC non-click steps). AC low-level action type 79.3 → 94.3, grounding 72.3 → 82.6. Offline only, no AW. Data size helps with saturation, and selecting by difficulty beats random selection — [UI-R1](https://arxiv.org/abs/2503.21620)
- GUI-G1-3B: 17K samples. Longer reasoning chains gave *worse* grounding, box-area rewards were hacked, and difficulty-aware scaling helped. Grounding only — [GUI-G1](https://arxiv.org/abs/2505.15810)
- Liquid AI fine-tuned LFM3-VL-2B with SFT + GRPO "for a few hours on one A100" on about 3,000 images (wind-turbine defect detection). Classification accuracy rose to 67% and detection F1 from 0.003 to 0.11. This is a vendor demo, not GUI — [Liquid LFM3 blog](https://www.liquid.ai/blog/lfm3)
- LiteGUI-2B GRPO used 2 nodes of 8×A100, G=16, lr 2.5e-7, KL 0, with a 32B judge. Reward = 0.6 GUI action match + 0.3 judge-scored subtask plan + 0.1 format/length — [LiteGUI](https://arxiv.org/abs/2605.07505)

**Environment-free alternatives (abstract-level only)**
- WM-R1 replaces the Android environment with a world model during RL rollouts (2,000 curated tasks) and reports beating GRPO-only baselines. No size or AW numbers in the abstract — [WM-R1](https://arxiv.org/abs/2608.27508)
- Generalization ceiling (7B): GRPO gains shrink from +26.1 on unseen instances to +15.7 on unseen templates and +8.3 on unseen apps — [AW-Generalization](https://arxiv.org/abs/2603.07432)

### Inferences
- The KL result transfers well conceptually, since it is the same algorithm at 3B. Use KL ≈1e-3 for any offline GRPO, not 0 as many RLVR recipes do.
- For us, GUI-Libra's +12 needs caution. It started from a weak 13.0 SFT with long CoT, and the RL data was 81K curated reasoning steps.
- Single-GPU offline GRPO on LFM3-VL-2B is mechanically feasible: Liquid did it in hours on one A100. A UI-R1-style run on a few hundred to 2K hard AC/Odyssey/AMEX steps would fit within about 1 GPU-hour. Expected AW effect: 0 to +3, by analogy to Ferret (+3) and UI-S1's offline GRPO (+0.8 at 7B, carried over).
- Online RL is out of reach: the smallest documented online setup is 64 emulators.

### Gaps
- UI-R1 GPU-hours were not in the retrieved text. The paper only claims "fewer GPU hours".
- No ≤4B paper reports an AW result for LoRA-based GRPO or for RL on a single consumer/workstation GPU.
- No evidence on GRPO stability for hybrid conv/attention backbones in GUI tasks.

## Q3. Distillation from a stronger agent: trajectory distillation, thought distillation, on-policy distillation (OPD) at ≤4B

### Takeaway
The 2026 literature has moved from trajectory SFT to **on-policy distillation**. A teacher scores the *student's own* sampled outputs token by token, often with privileged information. The strongest controlled result is GUI-SD-v2 at 8B on AW (Pass@1): SFT on teacher trajectories 50.9, GRPO 52.6, privileged self-distillation 67.2, all on the same 1.4K tasks. At 2B, LiteGUI (desktop, not AW) found plain SFT *hurt* Qwen3-VL-2B, while OPD with a 32B same-family teacher helped. Token-level OPD needs a teacher that shares the student's tokenizer, which rules out GUI-Owl or Qwen teachers for LFM3 except through sequence-level data. *Self*-distillation, where the same model serves as teacher, avoids that constraint.

### Cited Findings
- **LiteGUI (Qwen3-VL-2B student, Qwen3-VL-32B teacher, desktop benchmarks).** Rows give ScreenSpot-Pro / OSWorld / Lite-Bench. Base 40.16 / 6.04 / 33.35. **+SFT 31.56 / 3.25 / 37.96** (forgetting). +SFT+GRPO 33.47 / 3.77 / 42.65. **+OPD 41.87 / 9.32 / 51.47.** OPD with the teacher conditioned on the human-verified valid action most similar to the student's own action: 42.50 / 11.56 / 55.88. Full method with multi-solution dual-level GRPO: 43.13 / 13.24 / 61.76 — [LiteGUI](https://arxiv.org/abs/2605.07505)
- LiteGUI OPD settings: GKD with on-policy fraction λ=1.0, β=1.0, reverse KL, 1×8 A100, lr 2.5e-7, 2 epochs, global batch 32, max completion 512 tokens — [LiteGUI](https://arxiv.org/abs/2605.07505)
- **GUI-SD-v2 (Qwen3-VL-8B, full parameters including vision encoder, Kimi-K3 as privileged-guidance source)**: AW Pass@1 base 40.5, SFT on Kimi-K3 trajectories 50.9, GRPO 52.6, naive OPSD 50.0, GUI-SD-v1 57.8, **GUI-SD-v2 67.2** (Pass@3 79.3). MobileWorld 17.9 → 25.6 — [GUI-SD-v2](https://arxiv.org/abs/2609.27307)
- GUI-SD-v2 data and scale: 400 tasks in stage 1 (correction guidance on erroneous steps) and 1,013 tasks in stage 2, drawn from the OpenMobile and MobileForge task pools and rolled out in Android emulators. Settings: lr 5e-6, 8 rollouts per GUI state (4 with and 4 without privilege), temperature 1.0 — [GUI-SD-v2](https://arxiv.org/abs/2609.27307)
- GUI-SD-v2 ablations: step-level guidance 67.2 against trajectory-level 51.7. Teacher quality matters: Qwen3.5-Plus 57.8, MiniMax-M3 59.5, Gemini3.8-Flash 63.7, Kimi-K3 67.2. A privilege-following stage first: 49.1 with no stage-1 training, 61.2 with privilege-conditioned SFT, 67.2 with the proposed PAPO — [GUI-SD-v2](https://arxiv.org/abs/2609.27307)
- GHD (7B/8B) uses the *next screenshot* as privileged context for a parameter-sharing teacher and distills only when the student fails and the hindsight teacher recovers the gold action. It reported +6.2 and +7.4 over SFT (carried over, not re-read) — [GHD](https://arxiv.org/abs/2608.06065)
- Multi-teacher OPD across platforms (UI-MOPD, 8B): MobileWorld 12.0 — [UI-MOPD](https://arxiv.org/abs/2607.04425). MAGA focuses OPD on structured action tokens and suppresses signal on correct actions, +2.0 mean success at 8B over the strongest baseline — [MAGA](https://arxiv.org/abs/2607.29320)
- SAPD (non-GUI: ALFWorld, WebShop) does on-policy distillation over *offline* trajectory decision contexts with no new environment interaction. It reports less forgetting than SFT and 4.7× faster steps than online OPD — [SAPD](https://arxiv.org/abs/2610.27847)
- Trajectory distillation at 3B: Ferret-UI Lite's synthetic trajectories from a multi-agent system (planner, grounder and critic, VLM-judge filtered) raised AW from 19.6 to 25.2 as they scaled from 0 to 17K (see Q4) — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)

### Inferences
- Off-the-shelf OPD (GKD/reverse KL) needs teacher log-probs over the student's vocabulary. LFM3-VL-2B has no larger LFM3-VL sibling (the family is 2B-class only, per the [Liquid LFM3 blog](https://www.liquid.ai/blog/lfm3)), so a cross-family teacher such as GUI-Owl or Qwen3-VL-8B can supply only sequence-level supervision: trajectories, DAgger labels, thoughts. **Self-distillation with privileged context** (GHD's next screenshot, GUI-SD's gold action or memory hint) is tokenizer-safe and needs no second model in memory. We already have next screenshots for AC, GUI-Odyssey and AMEX, so a GHD-style gated self-distillation is the most budget-compatible OPD variant. Its gains are measured only at 7B/8B, so transfer to 2B is uncertain, though LiteGUI shows OPD-style training helps at 2B.
- LiteGUI's "SFT hurts" result comes from Qwen3-VL-2B full-parameter SFT on desktop data. It warns that SFT on narrow data can erase base GUI skills; LFM3-VL-2B reports GUI understanding of 83.1 on Liquid's suite.
- Any teacher rollouts must come from non-AW tasks. GUI-SD-v2's MobileForge pool generates tasks on target apps, so check for AW-app overlap before copying the recipe.

### Gaps
- No ≤4B *mobile/AW* OPD result. LiteGUI-2B is desktop-only, and GUI-SD-v2 and GHD are 8B/7B.
- No published thought-only distillation ablation at ≤4B (teacher thoughts plus gold actions vs gold actions only) on AW.

## Q4. Hyperparameters specific to GUI agents: LoRA vs full FT, rank, vision tower/projector, epochs, LR, mixing, data-scale curves, forgetting

### Takeaway
There is still no AW-measured LoRA-vs-full or frozen-vs-unfrozen-vision ablation at ≤4B. Nearly every 2026 small-agent paper uses **full-parameter training with the vision encoder unfrozen**: GUI-Libra (lr 1e-5), UI-Oceanus (2–4B SFT lr 1e-5), GUI-SD-v2 and VeriGUI. The most useful new curves are (a) Ferret-UI Lite-3B, where adding diverse synthetic *online-collected* trajectories kept raising AW (19.6→25.2 at 17K), and (b) evidence that narrow SFT causes forgetting at 2B while OPD and RL do not. Epoch guidance conflicts across papers.

### Cited Findings
**Full vs LoRA, vision tower**
- GUI-Libra: full-parameter SFT on Qwen2.5-VL / Qwen3-VL 3B–8B, lr 1e-5, effective batch 256, 2 epochs — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- GUI-SD-v2: "All model parameters, including the vision encoder and vision-language connector, are optimized" — [GUI-SD-v2](https://arxiv.org/abs/2609.27307)
- UI-Oceanus at 2B–4B: continual pre-training lr 3e-5, global batch 1,024, 1 epoch; SFT lr 1e-5, batch 64, 2 epochs, constant schedule (full FT) — [UI-Oceanus](https://arxiv.org/abs/2604.02345)
- LFM2-VL's own multimodal mid-training trains LM, connector and vision encoder together with LR ratio 5:5:1. LFM2-VL's SFT mixture used "no explicit grounding supervision such as bounding boxes or point coordinates" — [LFM2 report](https://arxiv.org/abs/2511.23404)
- Liquid docs: LoRA "Start with r=16", alpha = 2r. Full SFT lr 1e-5 to 5e-5. The VLM LoRA example (LFM2.5-VL-1.6B) uses r=8, α=16, lr 5e-4, max_image_tokens=256, and target_modules ["q_proj","v_proj","fc1","fc2","linear","gate_proj","up_proj","down_proj"]. The full VLM FT example uses lr 2e-5 — [Liquid TRL docs](https://docs.liquid.ai/lfm/fine-tuning/trl)
- Robotics evidence, non-GUI: for the π₀ VLA, freezing the VLM or restricting the vision encoder to LoRA "significantly degrades performance"; LoRA r=32 with the vision encoder fully trained matched full FT — [LoRA for VLA](https://arxiv.org/abs/2607.10172)
- Small-model LoRA pitfall (Qwen2-VL-2B, LoRA, AITW): apparent 5–7 point method gains came mostly from a serialization artifact (off-screen type-event points clamped to the origin). Fixing it lifted the baseline by about 7 points. Injecting conditioning via `inputs_embeds` silently switched image tokens to 1-D positions, costing 9 points — [Decoupling What from Where](https://arxiv.org/abs/2610.07444)

**Data-scale curves**
- Ferret-UI Lite-3B SFT ablations, AW averaged over 5 runs: human-annotated only, no CoT 13.7; +short CoT 15.8; +long CoT 19.6; **+synthetic data 5K 20.3; 13K 22.4; 17K 25.2.** The synthetic data is online rollouts from a multi-agent system (curriculum task generator, planner, grounder, critic) filtered by a VLM judge, plus offline task rewriting — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- Ferret-UI Lite grounding-to-navigation data ratio: "balanced ratios" are best, and grounding data "does not degrade" navigation — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- UI-Oceanus forward-dynamics continual pre-training (predict the next screen from screen plus action; 5M transitions, 3.2B tokens). Offline exact match: Qwen3-VL-2B 47.9 → 52.7, Qwen3-VL-4B 57.3 → 60.3, with a log-linear trend and no saturation. Inverse dynamics (predict the action from two screens) did not help: 2B EM 46.4–49.5. Online gains were measured only at 8B (27.5 → 30.9) and 32B, on WeChat mini-programs, not AW. CPT mix: 70% dynamics, 20% general, 10% grounding — [UI-Oceanus](https://arxiv.org/abs/2604.02345)
- STP (state-transition pretraining, joint inverse + forward dynamics) improves AC and GUI-Odyssey and scales with transition volume (abstract only) — [STP](https://arxiv.org/abs/2607.24112)
- AC out-of-domain scaling is extremely slow (carried over, not re-read) — [AndroidControl](https://arxiv.org/abs/2406.03679)

**Epochs / under- vs over-training**
- Ferret-UI Lite: RL gains are largest after fewer SFT steps (2K vs 6K vs 10K) — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- WinDOM (Qwen3.5-2B, grounding only): an *under-saturated* SFT cold start is a better GRPO initializer than a converged one, +5.4 out-of-domain mean over base — [WinDOM](https://arxiv.org/abs/2606.25964); contradicted for math by [Rethinking Expert Trajectory Utilization](https://arxiv.org/abs/2512.11470), which recommends switching to RL in the "stable or mild overfitting" SFT regime
- General long-CoT SFT (Olmo3-7B, not GUI): under a fixed update budget, 128 epochs on 400 samples beat 1 epoch on 51,200 samples by 12–26 points with "no additional catastrophic forgetting" — [Data Repetition Beats Data Scaling](https://arxiv.org/abs/2602.11149)

**Forgetting**
- Qwen3-VL-2B SFT on GUI trajectories: ScreenSpot-Pro 40.16 → 31.56 and OSWorld 6.04 → 3.25. OPD instead raised both — [LiteGUI](https://arxiv.org/abs/2605.07505)
- On AndroidControl continual learning, SFT "triggers knowledge overwriting" while RL "demonstrates an inherent resilience" (abstract only) — [CGL](https://arxiv.org/abs/2603.02951)
- UI-Oceanus keeps 20% general multimodal data "as a regularizer to prevent catastrophic forgetting" (no ablation number) — [UI-Oceanus](https://arxiv.org/abs/2604.02345)

### Inferences
- Our setup (LoRA r64, about 0.4–0.5 epoch, vision frozen) differs from every recent small-agent recipe on two axes: adapter vs full, and vision frozen vs trained. No GUI paper isolates either axis on AW, so the lever is untested, not disproven. The VLA evidence and LFM2-VL's own 5:5:1 joint training suggest a cheap probe: LoRA on the vision encoder as well, or unfreezing the projector. A projector-only unfreeze costs little memory on a 96GB card.
- Liquid's VLM LoRA example targets `fc1`/`fc2`, which in SigLIP2 naming are vision-encoder MLP layers. This suggests Liquid's own default adapts the vision tower. Verify the actual module names in the LFM3-VL checkpoint with `named_modules()`, since LFM3-VL uses a new encoder.
- Ferret's curve says AW kept improving with *more diverse, online-collected, judge-filtered* trajectories. Our v3 mix added more *static* human data (Odyssey, AMEX, ScreenQA) and AW did not move. That fits the earlier report's conclusion that data provenance and on-policy-ness matter more than volume.
- The epoch evidence conflicts. Being under-trained (about 0.45 epoch) is not obviously harmful if RL follows, per Ferret and WinDOM. For SFT-only deployment, the repetition paper suggests more epochs on a smaller curated set is at least safe. Neither result is GUI-at-2B on AW.

### Gaps
- No ≤4B AW ablation of LoRA vs full FT, LoRA rank, vision-tower freezing, or learning rate.
- No published data-mixing-ratio sweep against AW at ≤4B beyond Ferret's grounding:navigation "balanced" statement, whose exact ratios were not in the retrieved passages.
- No AW measurement of general-ability forgetting at 2B.

## Q5. Reasoning format at ≤4B: none vs short intent vs long CoT

### Takeaway
At 3–4B, removing reasoning at *training* time consistently hurts AW, and short CoT recovers only part of the long-CoT gain. Long CoT damages grounding unless offset with direct-action mixing or RL, and latent or implicit reasoning can match explicit CoT at 4B. Our short-intent format sits at the "short CoT" point, which in Ferret-UI Lite-3B was +2.1 over none and −3.8 under long CoT.

### Cited Findings
- Ferret-UI Lite-3B (non-Qwen), AW averaged over 5 runs: no CoT 13.7, short CoT 15.8, long CoT 19.6 — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- GUI-Libra-3B AW: ASFT trained with CoT 13.0 vs **trained without CoT 5.2**. RL model trained with CoT 25.2 vs without 12.2. Removing CoT only at inference: ASFT 8.7, RL 18.3. "Training with CoT consistently yields better performance than removing CoT during training, even when inference is ultimately performed without CoT" — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- Grounding cost of long CoT (3B, ScreenSpot-v2): SFT reasoning mode, about 223 tokens, 73.4. ASFT no-reason, about 68 tokens, 81.0. RL closes the gap: GUI-Libra-3B scores 83.4 reasoning vs 83.2 no-reason — [GUI-Libra](https://arxiv.org/abs/2602.22190)
- GUI-G1-3B: longer reasoning chains lead to worse grounding, and a "fast thinking" template helped (grounding only) — [GUI-G1](https://arxiv.org/abs/2505.15810). UI-R1 concludes that "reasoning is not essential for simpler tasks, such as GUI grounding" — [UI-R1](https://arxiv.org/abs/2503.21620)
- MIRAGE-4B: latent reasoning matches explicit-CoT SFT on AW with a 3–5× smaller decoded-token budget, and improves an instruction-tuned baseline by 10.2 points — [MIRAGE](https://arxiv.org/abs/2606.04627). Action-only SFT (31.0) scored below the untuned base (42.9) (carried over, not re-read)
- VeriGUI's structured Think → Verification → Action → Expected-Effect format links each step's predicted effect to the next step's check. It is the format that produced the loop and recovery gains in Q1 — [VeriGUI](https://arxiv.org/abs/2604.05477)
- GUI-SD-v2 at 8B: a model that must write task-relevant memory into its output gained on information-retrieval tasks (12/27 → 15/27) — [GUI-SD-v2](https://arxiv.org/abs/2609.27307)

### Inferences
- The evidence favours keeping some reasoning and supports *structured* short fields over free-form long CoT. Two fields map onto our failure modes: an outcome check of whether the last action changed the screen (VeriGUI) and a memory field for information to report later (GUI-SD-v2). Both stay short enough to avoid GUI-Libra's grounding penalty.
- Long CoT added +3.8 over short at 3B in Ferret, but at a latency cost. Its grounding damage appears mainly without RL or direct-action mixing.

### Gaps
- No ≤2B reasoning-format ablation on AW. No study on a hybrid or SSM backbone, where per-token decode is cheaper and could change the cost side of long CoT.

## Q6. Evidence on non-Qwen backbones and hybrid/SSM architectures (LFM2/LFM3)

### Takeaway
Non-Qwen ≤4B GUI evidence is thin. The main source is Ferret-UI Lite (Apple internal 3B dense model with a ViTDet encoder), where CoT, synthetic data scaling and dense-grounding RL all transferred. **No published GUI-agent training study uses an LFM2/LFM3 or other conv/SSM-hybrid backbone.** One correction to our project background: per Liquid, **LFM3-VL-2B does not use a SigLIP2 tower**. It uses a new in-house 164M convolution+attention encoder, and it was post-trained with grounding and GUI-understanding capability, unlike LFM2-VL.

### Cited Findings
- LFM3 backbone: 24 layers = 13 gated short convolutions (kernel 7) + 5 sliding-window GQA (window 256) + 6 global GQA with partial RoPE. Pre-trained on 22T tokens, the last 3.5T with "a larger share of agentic traces" — [Liquid LFM3 blog](https://www.liquid.ai/blog/lfm3)
- LFM3-VL-2B: "our new in-house vision encoder which uses 3× less compute than the SigLIP2 encoder in previous LFM VL models". The 164M encoder matches Qwen3.5-2B's encoder at 55.9% average across 13 VLM benchmarks with 2.2× fewer FLOPs. Pipeline: LFM3-1.7B-Base → vision mid-training → SFT → Vision RL → multi-domain on-policy distillation (MOPD) — [Liquid LFM3 blog](https://www.liquid.ai/blog/lfm3)
- Liquid's own suite for LFM3-VL-2B vs Qwen3.5-2B: visual grounding 77.3 vs 61.2, GUI understanding 83.1 vs 67.2, Agentic 42.5 vs 15.2. These are vendor evaluations — [Liquid LFM3 blog](https://www.liquid.ai/blog/lfm3)
- Vendor agent claim (text model, macOS): LFM3-1.7B vs Qwen3.5-2B on 65 macOS tasks, 64% vs 48% success, "stuck in under 1% of attempts versus 15%" — [Liquid LFM3 blog](https://www.liquid.ai/blog/lfm3)
- LFM3-VL fine-tuning by Liquid: SFT+GRPO a few hours on one A100 (defect detection). Vision-language navigation fine-tune: 2.8M samples, 72 GPU-hours on MI325X. Manipulation VLA "fine-tuned end to end", 170 GPU-hours — [Liquid LFM3 blog](https://www.liquid.ai/blog/lfm3)
- LFM2-VL (earlier generation): SigLIP2 NaFlex encoder, PixelUnshuffle connector (4× token reduction), 128–256 tokens for untiled images and about 2,800 with tiling. SFT used no box or point supervision — [LFM2 report](https://arxiv.org/abs/2511.23404)
- Ferret-UI Lite: "internal 3B dense model", ViTDet image encoder with AnyRes tiling, AW 28.0 — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- Other non-autoregressive or non-Qwen GUI backbones found: LLaDA-UI, a 16.7B MoE block-wise diffusion LM agent — [LLaDA-UI](https://arxiv.org/abs/2609.13287). No Mamba, SSM or LFM GUI agent paper was found in searches.

### Inferences
- Because LFM3-VL-2B already reports strong grounding and GUI understanding, our remaining gap to GUI-Owl-1.5-2B is less likely to be a missing-grounding problem than it would be for LFM2-VL. That strengthens the case that the binding constraint is policy behaviour (answer, stop, recover), which the earlier report also concluded.
- Liquid's statement that GRPO on LFM3-VL-2B runs "a few hours on one A100" is the only backbone-specific evidence that our RL tooling budget is not absurd. It does not speak to GUI or AW outcomes.
- The vision-tower question should be re-asked for this specific in-house conv+attention encoder; SigLIP2-based LoRA intuitions may not apply.

### Gaps
- No LFM3-VL model card details retrieved: training-data share of GUI data, coordinate convention, recommended LoRA targets for the new encoder. Read the HF model card before any vision-tower experiment.
- No hybrid or SSM-backbone GUI ablation exists, so every effect size in this file is a Qwen or Apple-internal transfer.

## Q7. Consolidated evidence table and feasibility at our budget (~2.5 GPU-h on RTX PRO 6000 96GB, ~$11 Modal, 2 local emulators, no AW-derived training)

### Takeaway
Within budget, the best-evidenced SFT-only changes are: VeriGUI-style 30% no-change injection with an outcome-check field, a small direct-action mix, and memory/answer fields. The best-evidenced RL change is a small offline GRPO with KL 1e-3 and a dense-grounding plus action-type reward. Privileged self-distillation (GHD/GUI-SD style, same model as teacher) is the strongest new method family and is tokenizer-safe for LFM3, but it is evidenced only at 7–8B. Online RL is not feasible.

### Cited Findings
| Tunable | Setting (exact) | Model / size | Before → after | Benchmark | Transfer to 2B LFM3 | Fits budget? | Source |
|---|---|---|---|---|---|---|---|
| No-change failure injection in SFT | 30% Type-B samples (prev screen + erroneous action in history, NO_CHANGE target) | Qwen2.5-VL-3B, full SFT | Loop rate 30.4→26.5; RSR 29.7→45.5; SR 42.6→41.7 | AC-High robustness slices (offline) | Medium-high (3B, data-only) | Yes, SFT only | [VeriGUI](https://arxiv.org/abs/2604.05477) |
| Same, ratio | 90:10 / 70:30 / 50:50 | same | RSR 30.3 / 45.5 / 45.4; SR 42.1 / 41.7 / 39.2 | AC-High | same | Yes | [VeriGUI](https://arxiv.org/abs/2604.05477) |
| Offline GRPO + verification reward | KL 0.05, G=6, 15 ep; action + effect + verification rewards | Qwen2.5-VL-3B | LR 26.5→24.3, RSR 45.5→51.1; AW final 12.6 (no AW ablation) | AC-High; AW | Medium | No at their scale (~20 h on 8×A100); a mini version possibly | [VeriGUI](https://arxiv.org/abs/2604.05477) |
| Direct-action data mixing | Same steps duplicated without CoT | Qwen2.5-VL-3B, full SFT | AW 5.2→11.3 | AW | Low-medium (gain tied to long CoT) | Yes | [GUI-Libra](https://arxiv.org/abs/2602.22190) |
| Action/grounding token reweighting | ASFT loss, α_a, α_g > 1 | Qwen2.5-VL-3B | AW 11.3→13.0 | AW | Medium (small effect) | Yes | [GUI-Libra](https://arxiv.org/abs/2602.22190) |
| KL in offline GRPO | KL 0 / 1e-3 / 1e-2 / 5e-2 | Qwen2.5-VL-3B | AW 21.7 / 25.2 / 21.7 / 20.0 | AW | High (same algorithm) | Small run only | [GUI-Libra](https://arxiv.org/abs/2602.22190) |
| Negative-gradient downscaling (SNGS) | success-adaptive | Qwen3-VL-4B | AW 39.1→42.6 | AW | Medium | Small run only | [GUI-Libra](https://arxiv.org/abs/2602.22190) |
| Reasoning in training | with vs without CoT | Qwen2.5-VL-3B | ASFT 13.0 vs 5.2; RL 25.2 vs 12.2 | AW | Medium-high | n/a (keep intent) | [GUI-Libra](https://arxiv.org/abs/2602.22190) |
| Reasoning length | none / short / long CoT | Apple 3B | AW 13.7 / 15.8 / 19.6 | AW (5-run mean) | Medium-high (non-Qwen) | Long CoT costs latency | [Ferret-UI Lite](https://arxiv.org/abs/2509.26539) |
| Synthetic online-collected trajectories | +5K / 13K / 17K (judge-filtered multi-agent rollouts + task rewriting) | Apple 3B | AW 19.6→20.3→22.4→25.2 | AW (5-run mean) | Medium-high | Teacher rollouts on our emulators (non-AW tasks) | [Ferret-UI Lite](https://arxiv.org/abs/2509.26539) |
| RLVR reward | type+dense grounding vs type-only / grounding-only | Apple 3B | SFT ~25→~28; type-only drops; grounding-only ≤ SFT | AW | Medium-high | Small run only | [Ferret-UI Lite](https://arxiv.org/abs/2509.26539) |
| Tiny-data GRPO | 136 hard samples | Qwen2.5-VL-3B | AC-low type 79.3→94.3; grounding 72.3→82.6 | AC (offline) | Medium; AW unknown | Yes | [UI-R1](https://arxiv.org/abs/2503.21620) |
| Plain SFT on narrow GUI data | full SFT | Qwen3-VL-2B | ScreenSpot-Pro 40.16→31.56; OSWorld 6.04→3.25 | desktop | Medium (forgetting risk) | caution | [LiteGUI](https://arxiv.org/abs/2605.07505) |
| On-policy distillation (32B teacher) | GKD reverse KL, λ=1, lr 2.5e-7 | Qwen3-VL-2B | OSWorld 6.04→9.32 (guided 11.56) | desktop | Medium; needs same-tokenizer teacher | No LFM3 teacher | [LiteGUI](https://arxiv.org/abs/2605.07505) |
| Privileged self-distillation (memory+reasoning) | 400 + 1,013 emulator tasks; 8 rollouts per state | Qwen3-VL-8B, full incl. ViT | AW 40.5→67.2 (SFT 50.9, GRPO 52.6) | AW Pass@1 | Low-medium (8B, strong external guidance) | Partially (self-teacher), compute-limited | [GUI-SD-v2](https://arxiv.org/abs/2609.27307) |
| Online RL, step-level credit | 64 envs, 8×A6000, GiGPO G=8, lr 1e-6, PRM 72B | MAI-UI-2B | MW 11.1→17.1 (GRPO binary 14.5) | MobileWorld | High (2B) | No (needs 64 envs) | [ClawGUI](https://arxiv.org/abs/2604.11784) |
| Env parallelism / step budget | 32→512 envs; 15→50 steps | MAI-UI family | +5.2; +4.3 | AW/MW | High | No | [MAI-UI](https://arxiv.org/abs/2512.22047) |
| Forward-dynamics CPT | 5M transitions, 70/20/10 mix, lr 3e-5 | Qwen3-VL-2B / 4B | EM 47.9→52.7 / 57.3→60.3 | offline in-house | Medium; online only at 8B+ | No at full scale; a small auxiliary task maybe | [UI-Oceanus](https://arxiv.org/abs/2604.02345) |
| Under-saturated SFT before RL | early vs converged cold start | Qwen3.5-2B | +5.4 OOD-mean grounding with early init | ScreenSpot-Pro / OSWorld-G / SS-V2 | Medium | Yes | [WinDOM](https://arxiv.org/abs/2606.25964) |

### Inferences
- Budget mapping. Changes that need only SFT on existing data: VeriGUI-style injection, direct-action mix, outcome-check/memory fields, masking. Each fits in one ~1 GPU-hour run of our 1,250-step config. A UI-R1/GUI-Libra-style offline GRPO (KL 1e-3, type + dense-grounding reward, a few hundred to 2K hard steps) plausibly fits in ~1 GPU-hour on a 96GB card for a 2B model, by analogy to Liquid's "few hours on one A100" demo. Privileged self-distillation needs on-policy sampling plus a second forward pass with privileged context. It is feasible only as a small pilot within 2.5 GPU-h, and its evidence is 7–8B.
- Emulator time (2 local) fits teacher-trajectory collection on non-AW apps à la Ferret's synthetic-data curve. Online RL does not fit (minimum documented: 64 envs).
- Effects stated at 3B on AW are mostly single-pass numbers of a few points (e.g., +1.7 for reweighting, +2.6 for GiGPO on MW). At 116 tasks these are within run-to-run noise. Only Ferret-UI Lite averaged 5 runs.

### Gaps
- Exact α weights (GUI-Libra), exact Ferret grounding:navigation ratios and its reward-ablation numbers sit in figures or tables not retrieved here.
- No ≤4B study combines the cheap SFT fixes (injection + answer/memory fields + masking) with an AW evaluation. Their additivity is unknown.
