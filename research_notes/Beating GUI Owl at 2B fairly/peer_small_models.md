# Peer small (≤4B) GUI / mobile agents other than GUI-Owl: recipes, AndroidWorld results, ablations, licenses (as of 2026-11-18)

Project reference points (our harness: AndroidWorld 116 tasks, pass@1, one current screenshot plus text history): LFM3-VL-2B v1 (AndroidControl SFT) 15/116 = 12.9%; Qwen3.5-2B same recipe 16/116 = 13.8%; GUI-Owl-1.5-2B 23/116 = 19.8% (its authors report 67.9 in their own harness). Abbreviations: AW = AndroidWorld, AC = AndroidControl, SR = success rate, SFT = supervised fine-tuning, RL = reinforcement learning, RFT = rejection-sampling fine-tuning.

Method note: most numbers come from targeted extraction of arXiv HTML pages, Hugging Face model cards and API metadata, and official repo code, all fetched on 2026-11-18. Rows marked "(prior notes)" reuse primary-source citations from the project's 2026-11-17 notes in `research_notes/Small GUI agent training methods/`. I did not re-fetch those today.

## Q1. Per-model comparison: base, size, training stages, I/O format, AW result with its setting, AC High/Low, ablations

### Takeaway
Every ≤4B model with a strong AW number (45-83%) is built on Qwen3-VL or Qwen3.5 (2B/4B). Each adds three things to SFT: (a) far more agent data than ours (millions of samples, or about 1M steps), (b) explicit thought supervision, and (c) online RL in emulators or real phones. Several strong small agents use a single current screenshot plus text history, which is what we use: UI-Venus-1.5-2B (inferred from code), PhoneBuddy-4B, AutoPlay-3B and GUI-Libra. So one-image input is not by itself the ceiling. The recipes closest to ours (Qwen2.5-VL-3B or an internal 3B, SFT on public offline datasets) land at 5-25% AW. Our 12.9% matches the Ferret-UI Lite no-CoT baseline (13.7) and sits between GUI-Libra-3B's plain SFT (5.2) and its action-aware SFT (13.0).

### Cited Findings

#### Comparison table (one row per model; AW settings are each paper's own unless stated; do not rank across rows)

| Model (release) | Base / params | Training stages (data, size) | Input format | Output format | AW SR (setting) | AC-High / AC-Low | Headline ablation | Src |
|---|---|---|---|---|---|---|---|---|
| **MAI-UI-2B** (paper 26 Dec 2025; weights 29 Dec 2025) | Qwen3-VL-2B | SFT (perception/grounding, then navigation; tasks from app manuals, expert tasks, open datasets; self-evolving rejection-sampled trajectories); grounding RL; online RL (tailored GRPO, up to 512 concurrent envs on 10 ECS servers, 35+ self-hosted apps). Data sizes not given for 2B | Current + 2 previous screenshots (`history_n=3` default); previous `<thinking>`+`<tool_call>` re-fed as text; 720p ≈ 1080p, 540p degrades | `<thinking>` (short plan + one-sentence summary) then `<tool_call>` JSON. Actions: click, long_press, type, swipe, open, drag, system_button, wait, terminate, answer, ask_user, mcp_call. Coords 0-999. No-thinking prompt variant exists | **49.1** (RL); **45.1** SFT-only. Own harness, screenshot-only; step budget and trials not stated. Leaderboard: 49.1, trials blank | 67.3 / not given by MAI-UI (MIRAGE's table: low EM 74.17) | RL +4.0 at 2B. At 8B: vanilla GRPO +1.8 vs their GRPO +6.0; RL env step budget 15→50 = 66.4→70.7; envs 32→512 = 65.5→70.7 | [paper](https://arxiv.org/html/2512.22047), [code](https://raw.githubusercontent.com/Tongyi-MAI/MAI-UI/main/MAI-UI/src/mai_naivigation_agent.py), [prompt](https://raw.githubusercontent.com/Tongyi-MAI/MAI-UI/main/MAI-UI/src/prompt.py) |
| **UI-Venus-1.5-2B** (Ant Group, 9 Feb 2026) | Qwen3-VL-2B | Mid-training 10B tokens / 30+ datasets (semantic perception 20.8%, GUI-VQA 22.1%, grounding 24.8%, hybrid navigation-reasoning); task-specific offline RL (GRPO); online RL with full-trajectory rollouts on a device cloud ("thousands of heterogeneous devices"), easy/medium/hard step buckets; TIES merge of specialists | Paper prompts: current screenshot + `<previous_actions>` text. The repo's mobile policy sends **one** image plus "previous actions and reasoning" as `Step i: ...` lines (inferred to match AW eval) | `<think>`, `<action>`, `<conclusion>`. Actions: Click, Drag, Scroll, Type, Launch, Wait, Finished, CallUser, LongPress, PressBack/Home/Enter/Recent. Coords [0,1000] normalized (code prompt: 0-999) | **55.6** (final, merged). Online-RL checkpoint **59.8**. Own harness, screenshot-only, "no zoom-in or agent-framework strategies"; steps and runs not stated | not reported | 2B AW by stage: mid-training 39.0 → offline RL 45.3 → online RL 59.8 → merge 55.6 (merge −4.2 at 2B, +1.0 at 8B) | [paper](https://arxiv.org/html/2602.09082), [processor code](https://github.com/inclusionAI/UI-Venus/blob/UI-Venus-2/Venus_framework/Venus_framework_mobile/processor/uivenus_processor.py) |
| **Step-GUI-4B / GELab-Zero-4B-preview** (StepFun; weights 28 Nov 2025; report 17 Dec 2025) | Qwen3-VL-4B-Instruct | Mid-training ≈11.2M samples (1.9M general MM, 2.7M grounding, 2.0M knowledge, 170K action alignment, 4.0M trajectory, 420K env-specific). Cold-start SFT ≈1.67M (284K general, 122K grounding, 864K knowledge, 404K trajectory). 6 self-evolving rounds with a "Calibrated Step Reward System"; GRPO | Current screenshot + instruction + "historical interaction logs" (number of images not stated) | CoT + actions (click, swipe, long_press, input_text, hotkey, awake, …); point coords | **63.9 pass@1**, **75.8 pass@3** (headline). Live emulator, "purely through visual understanding" | not reported | No ablation table in the report | [paper](https://arxiv.org/html/2512.15431), [card](https://huggingface.co/stepfun-ai/GELab-Zero-4B-preview), [repo](https://github.com/stepfun-ai/gelab-zero) |
| **PhoneBuddy-4B** (Jun 2026) | Qwen3.5-4B | Full-param SFT on **950,758 action steps** from real apps + PhoneWorld mock apps (1,115 steps, batch 512, packed 8,192 tokens, LR 1e-5→1e-6). Then only **50 online RL steps**: real-app RL (reward from Gemini-3.1-Pro rubrics judged by Qwen3.5-122B) or 50/50 real + mock RL (rule verifiers) | **Current screenshot only** + text: instruction, serialized history of prior **thought-action pairs**, and an "intermediate-state" field carried from the previous step | Optional reasoning block + updated intermediate state + one tagged tool call. Actions: click, double click, long press, type, scroll, drag, back/home/menu/enter, open app, close app, wait (+ ask user / output info / finish). Coords [0,1000] | SFT **60.3** → real RL **77.2** → real+mock RL **83.2**. Own harness; 30-step budget in training, **50** at eval | not reported | Real RL +16.9; adding mock RL +6.0 more | [paper](https://arxiv.org/html/2606.23049) |
| **UI-Voyager-4B** (25 Mar 2026) | Qwen3-VL-4B-Instruct | No human SFT. 4 rounds of RFT on **>7,000 tasks generated from AW templates** (seed generator perturbs parameters; rule verifier). Then GRSD: the shortest successful rollout's actions at "fork points" are distilled into failed rollouts | History window of h (action, observation) pairs (h not stated in extracted text) | Reasoning + `click`, `long_press`, `swipe`, `open_app`, `input_text`, `keyboard_enter`, `navigate_back/home`, `wait`, `status`, `answer` | **81.0** pass@1, mean over **64 seeds**, up to 30 steps. **Trained on AW templates (unseen-instance regime)** | not reported | Base 45.3 → RFT 37%→73% (round 3: 73.2) → GRPO/PPO ≈76 → GRSD 81.0 | [paper](https://arxiv.org/html/2603.24533), [card](https://huggingface.co/MarsXL/UI-Voyager) |
| **Holo2-4B** (H Company, 10 Nov 2025) | Qwen3-VL-4B-Thinking | "Multi-stage" pipeline on proprietary + open + synthetic + human-annotated data (no sizes) | not stated | not stated (thinking base) | **64.6**, measured in H's **Surfer 2 agent harness**. Same harness: Qwen3-VL-4B-Thinking 45.7, Holo1.5-3B 27.5 | not reported | none | [card](https://huggingface.co/Hcompany/Holo2-4B) |
| **Holo3.1-0.8B / 4B** (29 May–2 Jun 2026) | Qwen3.5-0.8B / 4B | Not described | not stated | Structured JSON or native function calling | Blog: "the smaller 4B and 9B variants improve from 58% to 72%" on AW. The likely reading is Qwen3.5 base (Qwen3.5-4B card: 58.6) → Holo3.1 ≈72 (**inference**). No 0.8B number | not reported | none | [HF blog](https://huggingface.co/blog/Hcompany/holo31), [card](https://huggingface.co/Hcompany/Holo-3.1-4B) |
| **MIRAGE-4B** (6 Jun 2026) | Qwen3-VL-4B-Instruct | SFT: explicit-thought warm-up, then latent CoT (9 latent slots, APLR 3 refinement passes) + Q-Former world-model loss aligning latents with next-frame features. Supervised only | not stated in passages read | Latent reasoning (≈31 decoded tokens/task vs 103 for base) | **52.6** (base 42.9 in the same harness); 116 tasks; RL none | High EM 64.43 / Low EM 77.59 | Action-only SFT **31.0** (below base) vs explicit-CoT SFT **52.6**; 3 latent slots 32.8 | [paper](https://arxiv.org/abs/2606.04627) |
| **GUI-Libra-3B / 4B** (Feb 2026) | Qwen2.5-VL-3B / Qwen3-VL-4B | SFT on **GUI-Libra-81K**: AC, GUI-Odyssey, AMEX, AitZ, AitW, GUIAct, MM-Mind2Web, re-annotated with GPT-4.1 reasoning (≈210 thought tokens/step) and filtered; "action-aware SFT" (ASFT). GRPO on 40K steps, KL 0.001, success-adaptive negative-gradient scaling (SNGS); offline step rewards, no environment | Current screenshot + serialized previous actions | `<think>` + action with `point_2d`. 13 actions incl. Answer, Terminate, OpenAPP, NavigateBack/Home, Wait, LongPress. Coords absolute (Qwen2.5-VL) or [0,1000] (Qwen3-VL) | 3B **25.2** (base 3.5); 4B **42.6** (base Qwen3-VL-4B **27.0** in this harness). Official Docker env, **20-step cap, 115 tasks** (#82 excluded), screenshot-only, no reflection modules | AC-v2 (re-labelled) High 57.3 / 62.3; Low 85.9 / 86.4 | 3B: SFT 5.2 → +mixed data 11.3 → ASFT 13.0 → RL 25.2; no CoT in training 12.2; CoT dropped at inference 18.3 | [paper](https://arxiv.org/html/2602.22190) |
| **AutoPlay-3B** (Sep 2025) | Qwen2.5-VL-3B | ~20k tasks generated by exploring the **20 AW apps** → ≈8k GPT-4o-verified successful trajectories for SFT; GRPO on the 8k solvable tasks (Qwen2.5-VL-32B verifier, 120 updates, 32 H100) | **Current image + history of past actions** + instruction | Low-level actions (action space in its App. F) | SFT **34.2** → RL **39.9** pass@1 (mean of 5 trials); pass@5 52.2 → 53.4. **Same apps as AW**; no test instructions | not reported | 7B task-generator ablation: no exploration 28.8, iterative exploration 21.6, no guidelines 26.7, AutoPlay 38.2 | [paper](https://arxiv.org/html/2509.25047) |
| **ADMIRE-3B** (12 Feb 2026) | Qwen2.5-VL-3B-Instruct | Online GRPO inside AW sandbox AVDs, adaptive milestone reward (GPT-4o milestones) | not extracted | not extracted | 18.1 (base) → outcome reward 26.7 / process reward 27.5 / ADMIRE **31.0**. **Trained in-domain on AW** | — | Static human milestones 28.4 vs adaptive 31.0 | [paper](https://arxiv.org/abs/2602.11524) |
| **Ferret-UI Lite-3B** (Apple, 30 Sep 2025) | Internal 3B dense LM + VitDet encoder, AnyRes tiling | SFT 10K steps: grounding mix (OS-Atlas, UGround, Aria-UI, Aguvis, ShowUI, Jedi, WaveUI, GroundUI) + navigation (Aguvis planning, OpenCUA, **17K synthetic trajectories** from a multi-agent generator/critic) + short/long CoT. RLVR (GRPO) 1.5K steps, reward = action type + dense grounding | Screenshot + text history of past actions; zoom-in crop tool at inference | Short CoT (plan) or long CoT (think + reflection); function-call actions (tap, swipe, textentry, open_app, navigate_back/home, long_press, terminate, …); centre point | **28.0** (mean of 5 runs, own harness). Same table: Qwen2.5-VL-3B 16.8, UI-TARS-1.5-7B 26.4 (re-run) | **68.9 / 86.6** | AW: human data, no CoT 13.7 → short CoT 15.8 → long CoT 19.6 → +syn 5K 20.3 → 13K 22.4 → 17K 25.2 → RLVR 28.0 | [paper](https://arxiv.org/html/2509.26539) |
| **ScaleCUA-3B** (Sep 2025) | Qwen2.5-VL-3B | ScaleCUA-Data (6 OSes): 17.1M grounding, 471.4K understanding, cross-platform trajectories (agents + humans); grounding / direct-action / reasoned-action modes | History + low-level text instructions; 1080p default | Optional `<think>`; Python-like calls; raw (absolute) coords | **23.7** (quoted by Ferret-UI Lite/MAI-UI). Extraction gives 23.7 at "15 steps" vs **9.6** at AW's predefined step limits (direction looks odd, see Gaps) | extraction unreliable (see Gaps) | Training resolution 1080p → AW 23.3 vs 2K → 13.4; reasoned > direct by +1.4 to +8.2 | [paper](https://arxiv.org/html/2509.15221) |
| **UI-TARS-2B-SFT** (ByteDance, 21 Jan 2025) | Qwen2-VL-2B | ~50B tokens: perception, grounding, action traces (open mobile 145k traces + own 14.9k), reflective online traces. DPO only for 7B/72B | Last **5** screenshots + full thought/action history | Thought (System-2) + action (Click, Drag, Scroll, Type, Wait, Finished, CallUser, LongPress, PressBack/Home/Enter); relative coords | **no 2B AW number**. 7B-SFT 33.0, 72B-SFT 46.6 | SR **68.9 / 89.3** (GUI-Odyssey 83.4) | System-2 slightly worse than System-1 at N=1 in-domain; better at N=16/64 and OOD (AW) | [paper](https://arxiv.org/html/2501.12326) |
| **Qwen3-VL-2B / 4B** (Oct 2025; report Nov 2025) | native | GUI perception (element description, dense captioning, dense grounding) + multi-step trajectories from a "self-evolving trajectory-production framework" + CoT rationales, inside the general post-training | — | [0,1000] normalized coords | 2B **36.4**, 4B-Instruct **45.3** (vendor-reported, quoted by MAI-UI, Step-GUI, UI-Voyager). 4B in other harnesses: 42.9 (MIRAGE), 27.0 (GUI-Libra), 45.7 Thinking (Holo2/Surfer 2) | 4B: MIRAGE re-run High EM 54.58 / Low EM 68.48 | — | [report](https://arxiv.org/html/2511.21631), [UI-Voyager T2](https://arxiv.org/html/2603.24533) |
| **Qwen3.5-0.8B / 2B / 4B** (27-28 Feb 2026) | native, hybrid Gated-DeltaNet LM | general RL "across million-agent environments" | — | — | 4B card: **AndroidWorld 58.6** (Qwen3.5-9B 57.8). 2B and 0.8B cards list no AW | — | — | [4B card](https://huggingface.co/Qwen/Qwen3.5-4B), [2B card](https://huggingface.co/Qwen/Qwen3.5-2B) |
| **OS-Atlas-4B** (Oct 2024) (prior notes) | InternVL2-4B | Grounding pre-training (13M+ elements, 2.3M screenshots) then agent SFT | — | — | no AW | 67.5 / 80.6 | Grounding pre-training: AC-Low +0.5 at 4B (80.10→80.64); GUI-Odyssey +4.9 | [OS-Atlas](https://arxiv.org/html/2410.23218), [Ferret T2](https://arxiv.org/html/2509.26539) |
| **OS-Genesis-4B** (Dec 2024) (prior notes) | InternVL2-4B | 1K reverse-synthesized trajectories (GPT-4o) | — | — | **15.18** (zero-shot 0.00, task-driven 4.02, +self-instruct 7.14) | — | Synthesis vs task-driven: +11.2 | [OS-Genesis](https://arxiv.org/html/2412.19723) |
| **ShowUI-2B** (Nov 2024) | Qwen2-VL-2B | 256K grounding/navigation samples (prior notes) | — | — | **7.8** in MIRAGE's harness (own paper: no AW) | MIRAGE re-run High EM 59.82 / Low EM 74.83 | — | [MIRAGE T1-2](https://arxiv.org/abs/2606.04627) |
| **InfiGUIAgent-2B** (Jan 2025) | Qwen2-VL-2B | two-stage SFT | screenshot | — | **9.0** (AW leaderboard, screenshot) | — | — | [leaderboard](https://docs.google.com/spreadsheets/d/1cchzP9dlTZ3WXQTfYNhh3avxoLipqHN75v1Tb86uhHo/edit?gid=0#gid=0) |
| **InfiGUI-R1-3B** (Apr 2025) (prior notes) | Qwen2.5-VL-3B | SFT distilling spatial reasoning from QwQ-32B, then RLOO on 10K AC + 2K reflection trajectories + 5K grounding + general | — | reasoning | no AW | SR 71.1 / 92.1 | — | [InfiGUI-R1](https://arxiv.org/abs/2504.14239) |
| **SecAgent-3B** (Mar 2026) (prior notes) | Qwen2.5-VL-3B | LoRA SFT + full-param RFT; Chinese-app data | N previous screenshots + semantic text summary | thought + action | no AW (offline CMGUI) | AC-High step acc. 69.5 | N=0 → N=1 task acc. 36.2 → 72.8 | [SecAgent](https://arxiv.org/abs/2603.08533) |
| **OpenPhone-3B** (Oct 2025) (prior notes) | Qwen2.5-VL-3B | SFT → GRPO on synthetic GUI data; device-cloud routing | text history summary | reasoning | no AW; **AndroidLab 15.2** | — | No history 4.3; no reasoning 8.7 | [OpenPhone](https://arxiv.org/abs/2510.22009) |
| **Smol2Operator** (HF, Sep 2025) | SmolVLM2-2.2B (also nanoVLM-460M) | Phase 1: grounding SFT on aguvis-stage-1; Phase 2: agentic SFT on aguvis-stage-2 (unified action space) | — | Normalized [0,1] coords | no AW | — | ScreenSpot-v2: base 0.47 → phase 1 41.27 → phase 2 61.71. Normalized vs pixel coords at 1152 px: 33.72 vs 4.32 (400K samples). 460M model ≈58% | [blog](https://raw.githubusercontent.com/huggingface/blog/main/smol2operator.md) |

#### Per-model notes with extra detail
- **MAI-UI (Alibaba Tongyi).**
  - The input "includes the task instruction, historical screenshots, and the model's past outputs, including thoughts and actions" (§2.4.1) — [MAI-UI](https://arxiv.org/html/2512.22047).
  - The official agent code defaults to `history_n: 3`, i.e. the current screenshot plus up to 2 previous ones (`max_history = min(len(history_images), history_n - 1)`), with `SCALE_FACTOR = 999` and temperature 0.0 — [mai_naivigation_agent.py](https://raw.githubusercontent.com/Tongyi-MAI/MAI-UI/main/MAI-UI/src/mai_naivigation_agent.py).
  - The system prompt hard-codes the AndroidWorld app list for the `open` action, e.g. "Simple Calendar Pro", "Pro Expense", "Broccoli APP", "OSMand" — [prompt.py](https://raw.githubusercontent.com/Tongyi-MAI/MAI-UI/main/MAI-UI/src/prompt.py).
  - Device-cloud collaboration (MAI-UI-2B on device, 32B in the cloud) gives a 33.4% relative gain over on-device only and cuts cloud API calls by over 40%. Adding an error summary at handoff gives +6.9 — [MAI-UI](https://arxiv.org/html/2512.22047); [HF card](https://huggingface.co/Tongyi-MAI/MAI-UI-2B).
  - Follow-up work: Qwen-UI-Agent (2026-07-30) and MAI-Gym-9B (Oct 2026). Neither has a ≤4B release — [MAI-UI repo README](https://raw.githubusercontent.com/Tongyi-MAI/MAI-UI/main/README.md); [MAI-Gym-9B card](https://huggingface.co/Tongyi-MAI/MAI-Gym-9B).
- **UI-Venus-1.5 (Ant Group).**
  - Stage ablation (Table 7):
    - AW for 2B / 8B / 30B-A3B after mid-training: 39.0 / 57.0 / 67.1. After offline RL: 45.3 / 63.5 / 68.0. After online RL: 59.8 / 72.7 / 75.5. After merge: 55.6 / 73.7 / 77.6.
    - ScreenSpot-Pro for 2B: 52.3 → 59.0 → (n/a) → 57.7.
    - Source: [UI-Venus-1.5](https://arxiv.org/html/2602.09082).
  - The repo prompt for 1.x mobile has the section "###先前的动作和推理过程" ("previous actions and reasoning process") filled with `Step i: <action_description>`. The output format is `<think>…</think><action>…</action><conclusion>总结当前操作</conclusion>` ("summarize the current operation"). The policy builds messages with a single `image_url` (current screenshot) — [processor](https://github.com/inclusionAI/UI-Venus/blob/UI-Venus-2/Venus_framework/Venus_framework_mobile/processor/uivenus_processor.py); [policy](https://github.com/inclusionAI/UI-Venus/blob/UI-Venus-2/Venus_framework/Venus_framework_mobile/policy/ui_venus_policy.py).
  - This framework is the real-device deployment code. That the AW evaluation used the same one-image format is my **inference**; the paper's appendix prompts likewise "review current screenshot and previous actions" — [UI-Venus-1.5](https://arxiv.org/html/2602.09082).
- **Step-GUI.** The GELab-Zero README restates the AW result as "75.86% success rate", which is the pass@3 figure. The paper justifies pass@3 by "environment instability" — [gelab-zero README](https://github.com/stepfun-ai/gelab-zero); [Step-GUI](https://arxiv.org/html/2512.15431).
- **PhoneBuddy.**
  - "Each inference step is framed as a multimodal action prediction problem with the current screenshot and a structured textual context … a serialized history of prior thought-action pairs, and an intermediate-state field carried over from the previous step" — [PhoneBuddy](https://arxiv.org/html/2606.23049).
  - Cross-app tasks did not improve with RL (22.0 / 20.0 / 18.0); the authors cite weak "long-horizon state tracking, information handoff" — [PhoneBuddy](https://arxiv.org/html/2606.23049).
  - The PhoneWorld mock apps are "reconstructed from real GUI traces". The paper does not say whether AW apps are among them (Gap).
- **MIRAGE.**
  - "Action-only SFT performs worse than the base model, indicating that removing thought supervision without replacing it by internal computation can harm interactive decision making" — [MIRAGE](https://arxiv.org/abs/2606.04627).
  - Its Appendix B "Training data" cites the AndroidWorld paper. Whether AW-environment trajectories were used for training is unverified (Gap).
- **GUI-Libra (3B ablation, Table 9).**
  - AW by variant: base 3.5; SFT 5.2; SFT + mixed data 11.3; ASFT 13.0; RL without ASFT 17.4 (KL 0) / 20.9 (KL 0.001); GUI-Libra 21.7 (KL 0) / **25.2 (KL 0.001)** / 21.7 (KL 0.01) / 20.0 (KL 0.05).
  - Without CoT: ASFT 5.2 and GUI-Libra 12.2 when CoT is removed from training; ASFT 8.7 and GUI-Libra 18.3 when CoT is skipped only at inference.
  - 4B: SNGS 39.1 → 42.6.
  - Source: [GUI-Libra](https://arxiv.org/html/2602.22190).
- **Ferret-UI Lite.**
  - Grounding-data ablation (ScreenSpot-Pro / -V2): base 50.15/90.49; without OS-Atlas 43.35/89.62; without Aria-UI 46.93/89.94; without Jedi 47.63/88.36.
  - "dense grounding rewards outperforming sparse grounding rewards" for navigation RL.
  - Source: [Ferret-UI Lite](https://arxiv.org/html/2509.26539).
- **Holo1.5-3B** (11 Sep 2025, Qwen2.5-VL-3B): "large-scale supervised fine-tuning, followed by online reinforcement learning (GRPO)", natively up to 3840×2160 px. AW 27.5 in H's Surfer 2 harness — [Holo1.5-3B card](https://huggingface.co/Hcompany/Holo1.5-3B); [Holo2-4B card](https://huggingface.co/Hcompany/Holo2-4B).
- **No ≤4B variant exists** for UI-TARS-1.5 (open weights 7B only), UI-TARS-2 (≈230B MoE, AW 73.3), UI-S1 (7B), MobileRL (7B/9B), ZeroGUI (7B), Aguvis (7B/72B), OpenCUA (7B/32B/72B, desktop) or AgentCPM-GUI (8B) — [HF API listings](https://huggingface.co/api/models?search=UI-TARS); [UI-Voyager Table 2](https://arxiv.org/html/2603.24533); [OpenCUA](https://huggingface.co/xlangai/OpenCUA-7B); [AgentCPM-GUI](https://github.com/OpenBMB/AgentCPM-GUI).
- **AgentCPM-GUI-8B** (outside the size limit) is designed for on-device use. Compact JSON actions average 9.7 tokens, with 0-1000 coordinates, an optional `thought` field and STATUS flags. AC-High EM 69.17, AC-Low EM 90.20 — [AgentCPM-GUI README](https://github.com/OpenBMB/AgentCPM-GUI). UI-S1's re-evaluation gave it only 16.4 on AW (prior notes) — [UI-S1](https://arxiv.org/abs/2509.11543).
- **Grounding-only small models (no agent AW):**
  - InfiGUI-G1-3B (AEPO RL on Qwen2.5-VL-3B, Aug 2025) — [card](https://huggingface.co/InfiX-ai/InfiGUI-G1-3B).
  - GUI-Actor-2B/3B (Microsoft, Jun 2025) — [HF](https://huggingface.co/microsoft/GUI-Actor-3B-Qwen2.5-VL).
  - Phi-Ground (Jul 2025) — [HF](https://huggingface.co/microsoft/Phi-Ground).
  - GoClick (230M encoder-decoder grounder, Apr 2026) — [arXiv 2604.23941](https://arxiv.org/abs/2604.23941).
  - BlueLM-2.5-3B (vivo, Jul 2025) reports ScreenSpot / -V2 / -Pro grounding against Qwen2.5-VL-3B but no online agent benchmark — [BlueLM-2.5-3B](https://arxiv.org/html/2507.05934v1). vivo's agent model BlueLM-GUI is 35B-A3B — [summary](https://academy.dair.ai/papers/bluelm-gui-technical-report-a-real-device-centric-flywheel-for-self-improving-mo-2609.12394).
- **Sub-2B / on-device:**
  - Holo3.1-0.8B and PhoneBuddy-0.8B (a "small Real+Mock RL checkpoint", Jun 2026) exist, but neither card reports AW — [Holo3.1](https://huggingface.co/Hcompany/Holo-3.1-0.8B); [PhoneBuddy-0.8B](https://huggingface.co/PhoneBuddyAI/PhoneBuddy-0.8B).
  - StepX-Edge (0.9B UI VLM, Jul 2026) targets UI understanding and grounding, not navigation. It reports 0.84 s TTFT on Snapdragon 8 Gen5 — [arXiv 2607.22708](https://arxiv.org/abs/2607.22708).
  - An LFM2-VL-1.6B fine-tune on AndroidControl episodes exists (Tonic "L-Operator", Aug 2025) with no reported benchmark — [HF](https://huggingface.co/Tonic/l-android-control).
  - Liquid's own cookbook has "LFM2.5 Mobile Actions", a text function-calling model, not a screenshot agent — [Liquid cookbook](https://github.com/Liquid4All/cookbook/blob/main/README.md).
  - Google's Gemini "screen automation" on Pixel 10 / Galaxy S26 is a Gemini-app (cloud) feature with no published benchmark. Gemini Nano's public APIs are text/vision utilities — [Google blog](https://blog.google/products-and-platforms/platforms/android/gemini-intelligence/); [Pixel help](https://support.google.com/pixelphone/answer/16940971?hl=en).
  - I found no Apple or Samsung small agent with an AW number other than Ferret-UI Lite.

### Inferences
- The closest published analogues to our v1 (AC-style public offline data, short or no reasoning, SFT only) score 5-14% on AW: GUI-Libra-3B SFT 5.2, ASFT 13.0; Ferret-UI Lite no-CoT 13.7; OS-Genesis-4B task-driven 4.0. Our 12.9% is normal for that recipe class, not an outlier.
- GUI-Libra trained on almost exactly our v2/v3 sources (AC + GUI-Odyssey + AMEX + AitZ + AitW + GUIAct). Its SFT-only AW of 5.2 → 11.3 → 13.0 is the published counterpart of "offline accuracy rose but AW did not". The large AW gains came only after long teacher CoT, KL-regularized RL and negative-gradient down-weighting were added.
- Single-image input is compatible with 55-60% at 2-4B (UI-Venus-1.5-2B inferred; PhoneBuddy-4B SFT-only). Both carry a model-written textual state forward each step: UI-Venus's `<conclusion>` and PhoneBuddy's "intermediate-state" plus prior thoughts. Our history is intent + action JSON. Of the cheap changes, adding carried-over summary/state text is best supported by peers.

### Gaps
- Exact AW step budgets, number of runs and seeds for MAI-UI-2B, UI-Venus-1.5-2B and Step-GUI-4B are not stated in the passages read.
- UI-Voyager's history window h and MIRAGE's history format were not extracted.
- ScaleCUA's AC numbers came back garbled (for 3B, AC-Low "grounding 91.4 / SR 93.7" and AC-High "81.4 / 83.9" do not fit the expected column order). Its AW "15 steps 23.7 vs predefined 9.6" direction looks counterintuitive. Both need checking against Table 5/9 of [ScaleCUA](https://arxiv.org/html/2509.15221).
- Holo2-4B, Holo3.1 and Qwen3.5-4B AW harness details (history images, step cap) are not published on the cards.
- Rows marked "(prior notes)" were not re-fetched today.

## Q2. What evaluation setting sits behind each AW number, and how harness-sensitive are small models?

### Takeaway
AW numbers for the same small model move by 2-6x across harnesses. Step budget, prompt format, resolution, quantization, pass@k and AW-specific training all matter more than many recipe differences. The only official-leaderboard entries ≤4B are MAI-UI-2B (49.1, self-reported, trials blank) and InfiGUIAgent-2B (9.0). Several headline numbers (UI-Voyager 81.0, ADMIRE 31.0, MobileRL) come from RL on AW templates or apps. Step-GUI's headline is pass@3.

### Cited Findings
- The AW leaderboard was archived in Nov 2026: "With multiple submissions reaching 100%, AndroidWorld is now considered saturated … Scores are self-reported and unverified." Its ≤4B "Model" entries are MAI-UI-2B 49.1 (Screenshot) and InfiGUIAgent-2B (Qwen2-VL-2B) 9.0 (Screenshot, 1 trial) — [AW leaderboard](https://docs.google.com/spreadsheets/d/1cchzP9dlTZ3WXQTfYNhh3avxoLipqHN75v1Tb86uhHo/edit?gid=0#gid=0).
- **Same model, different harness:**
  - **Qwen3-VL-4B:** 45.3 vendor-reported ([Step-GUI](https://arxiv.org/html/2512.15431); [UI-Voyager](https://arxiv.org/html/2603.24533)); 42.9 in MIRAGE ([MIRAGE](https://arxiv.org/abs/2606.04627)); **27.0** in GUI-Libra's 20-step See-Act-V harness ([GUI-Libra](https://arxiv.org/html/2602.22190)); 45.7 for the Thinking variant in H's Surfer 2 harness ([Holo2-4B card](https://huggingface.co/Hcompany/Holo2-4B)); 14.8% on the Easy split and 7.3% on Medium+Hard on a phone NPU (llama.cpp Q4_0, 512×512 input) ([DroidPrefill, arXiv 2611.20772](https://arxiv.org/html/2611.20772)).
  - **MAI-UI-2B:** 49.1 own ([MAI-UI](https://arxiv.org/html/2512.22047)); 46.5 in MIRAGE's harness ([MIRAGE](https://arxiv.org/abs/2606.04627)); **8.2% Easy / 0.0% Medium+Hard** on device with Q4_0 and 512×512 screenshots ([DroidPrefill](https://arxiv.org/html/2611.20772)). In the same on-device table GUI-Owl-1.5-4B gets 16.3 / 3.6.
  - **Qwen2.5-VL-3B:** 3.5 (GUI-Libra), 16.8 (Ferret-UI Lite, re-run), 18.1 (ADMIRE) — [GUI-Libra](https://arxiv.org/html/2602.22190); [Ferret-UI Lite](https://arxiv.org/html/2509.26539); [ADMIRE](https://arxiv.org/abs/2602.11524). UI-S1 reported 5.0 (prior notes) — [UI-S1](https://arxiv.org/abs/2509.11543).
  - **UI-TARS-1.5-7B:** 26.4 (Ferret re-run), 30.0 (MAI-UI table), 32.8 (ADMIRE table), 33.0 (Ferret "reported") — [Ferret-UI Lite](https://arxiv.org/html/2509.26539); [ADMIRE](https://arxiv.org/abs/2602.11524); [UI-Voyager Table 2](https://arxiv.org/html/2603.24533).
- **Settings disclosed per paper:**
  - GUI-Libra: official Docker, 20 steps, 115 tasks — [GUI-Libra](https://arxiv.org/html/2602.22190).
  - UI-Voyager: ≤30 steps, mean over 64 seeds — [UI-Voyager](https://arxiv.org/html/2603.24533).
  - PhoneBuddy: 50-step eval budget — [PhoneBuddy](https://arxiv.org/html/2606.23049).
  - Ferret-UI Lite: mean of 5 runs — [Ferret-UI Lite](https://arxiv.org/html/2509.26539).
  - AutoPlay: mean over 5 trials — [AutoPlay](https://arxiv.org/html/2509.25047).
  - Step-GUI: pass@3 headline, pass@1 also reported — [Step-GUI](https://arxiv.org/html/2512.15431).
  - MAI-UI: history_n=3 in code, temperature 0 — [code](https://raw.githubusercontent.com/Tongyi-MAI/MAI-UI/main/MAI-UI/src/mai_naivigation_agent.py).
  - UI-TARS: last 5 screenshots — [UI-TARS](https://arxiv.org/html/2501.12326).
- **Step budget and resolution effects:**
  - MAI-UI's RL environment step budget 15/30/50 gives 66.4/68.5/70.7 at 8B — [MAI-UI Table 9](https://arxiv.org/html/2512.22047).
  - ScaleCUA: 1080p training gives AW 23.3 vs 2K 13.4 — [ScaleCUA](https://arxiv.org/html/2509.15221).
  - DroidPrefill: on-device inference at full or near-full resolution takes >80 s to encode, so it uses 512×512. At 224×512 coordinates are often malformed, and at 448×1024 latency rises "without reliably recovering correct grounding" — [DroidPrefill](https://arxiv.org/html/2611.20772).
- **AW-specific training (contamination regimes):**
  - UI-Voyager trains on >7,000 AW-template tasks — [UI-Voyager](https://arxiv.org/html/2603.24533).
  - ADMIRE trains with RL inside the AW sandbox — [ADMIRE](https://arxiv.org/abs/2602.11524).
  - AutoPlay generates tasks on the 20 AW apps — [AutoPlay](https://arxiv.org/html/2509.25047).
  - MAI-UI's prompt enumerates AW apps — [prompt.py](https://raw.githubusercontent.com/Tongyi-MAI/MAI-UI/main/MAI-UI/src/prompt.py).

### Inferences
- The only clean comparisons for the project are same-harness runs: our 1-image harness on GUI-Owl-1.5-2B, MAI-UI-2B, UI-Venus-1.5-2B, GELab-Zero-4B and Holo3.1-0.8B/4B. The weights are public, so running them is feasible. Published numbers should be treated as upper bounds tied to each author's prompt and history format.
- MAI-UI-2B collapses on device (8.2 Easy) and GUI-Owl drops in our harness (67.9 → 19.8). Together these suggest small agents are brittle to prompt-format and resolution shifts. A model trained in our own harness format has a structural advantage in our evaluation. That is legitimate if disclosed, but the "fair" comparison should also give peers their native prompt.

### Gaps
- No ≤4B paper ablates the number of history screenshots on AW itself. The nearest are SecAgent (offline) and OpenPhone (AndroidLab) — [SecAgent](https://arxiv.org/abs/2603.08533); [OpenPhone](https://arxiv.org/abs/2510.22009).
- DroidPrefill reports Easy versus Medium+Hard splits, not the full 116-task SR, so it cannot be directly set against full-suite numbers.

## Q3. Which ingredient do the authors' own ablations credit most, and how much was each worth?

### Takeaway
In descending order of measured AW effect at ≤4B:
1. Online RL / environment interaction, worth +4 to +17 points (+28 with AW-template RFT).
2. Explicit thought supervision, +6 to +21 points; action-only SFT can fall below the untuned base.
3. Environment-grounded synthetic trajectories, +5 to +11.
4. Offline step-level RL with KL control, +6 to +12.

Grounding pre-training and model merging are small or negative for agent success at 2-4B. No ≤4B paper credits multi-image history on AW directly.

### Cited Findings
- **Online RL / RFT in environments:**
  - UI-Venus-1.5-2B: offline RL → online RL **+14.5** (45.3 → 59.8), the largest stage gain at 2B — [UI-Venus-1.5](https://arxiv.org/html/2602.09082).
  - PhoneBuddy-4B: SFT → real-app RL **+16.9** (60.3 → 77.2) in 50 RL steps; adding mock-app RL +6.0 (83.2) — [PhoneBuddy](https://arxiv.org/html/2606.23049).
  - UI-Voyager-4B: RFT rounds 37% → 73% (round 3: 73.2); GRSD adds +5 over GRPO/PPO (76 → 81) — [UI-Voyager](https://arxiv.org/html/2603.24533).
  - MAI-UI-2B: SFT → RL +4.0 (45.1 → 49.1). At 8B, the RL "extras" are worth +4.2 over vanilla GRPO (66.5 vs 70.7) — [MAI-UI](https://arxiv.org/html/2512.22047).
  - ADMIRE-3B: outcome-reward GRPO +8.6; milestone reward +12.9 — [ADMIRE](https://arxiv.org/abs/2602.11524).
  - AutoPlay-3B: RL +5.7 (34.2 → 39.9) — [AutoPlay](https://arxiv.org/html/2509.25047).
  - Ferret-UI Lite-3B: RLVR "from 25% to 28%" — [Ferret-UI Lite](https://arxiv.org/html/2509.26539).
- **Reasoning / thought supervision:**
  - MIRAGE-4B: action-only SFT 31.0 vs explicit-CoT SFT 52.6 (**+21.6**; base 42.9) — [MIRAGE](https://arxiv.org/abs/2606.04627).
  - GUI-Libra-3B: removing CoT from training 25.2 → 12.2 (**−13.0**); removing it only at inference → 18.3 — [GUI-Libra](https://arxiv.org/html/2602.22190).
  - Ferret-UI Lite-3B: no CoT 13.7 → short CoT 15.8 → long CoT 19.6 (**+5.9**) — [Ferret-UI Lite](https://arxiv.org/html/2509.26539).
  - ScaleCUA: reasoned over direct action +1.4 to +8.2 — [ScaleCUA](https://arxiv.org/html/2509.15221).
  - UI-TARS: System-2 is slightly worse at N=1 in-domain but better OOD — [UI-TARS](https://arxiv.org/html/2501.12326).
- **Synthetic / online trajectory data:**
  - Ferret-UI Lite: +17K synthetic trajectories 19.6 → 25.2 (**+5.6**; 5K +0.7, 13K +2.8) — [Ferret-UI Lite](https://arxiv.org/html/2509.26539).
  - OS-Genesis-4B: 1K synthesized vs 1K task-driven trajectories, 15.18 vs 4.02 (**+11.2**) (prior notes) — [OS-Genesis](https://arxiv.org/html/2412.19723).
  - AutoPlay (7B ablation, 5k tasks): exploration-grounded tasks 38.2 vs no exploration 28.8 (**+9.4**) — [AutoPlay](https://arxiv.org/html/2509.25047).
  - PhoneBuddy's ≈951K-step SFT alone reaches 60.3 at 4B — [PhoneBuddy](https://arxiv.org/html/2606.23049).
- **Offline RL / RL-style SFT on static data:**
  - UI-Venus-1.5-2B: mid-training → offline RL +6.3 (39.0 → 45.3) — [UI-Venus-1.5](https://arxiv.org/html/2602.09082).
  - GUI-Libra-3B: ASFT 13.0 → offline GRPO with KL 0.001 = 25.2 (**+12.2**). KL 0 gives 21.7, KL 0.05 gives 20.0. Plain SFT on the same 81K data gives only 5.2 — [GUI-Libra](https://arxiv.org/html/2602.22190).
- **Data mixing on the same offline sources:** GUI-Libra-3B SFT 5.2 → "SFT + Mixed Data" 11.3 — [GUI-Libra](https://arxiv.org/html/2602.22190).
- **Grounding pre-training:** OS-Atlas at 4B gives +0.5 AC-Low and +4.9 GUI-Odyssey (prior notes) — [OS-Atlas](https://arxiv.org/html/2410.23218). Smol2Operator shows that a base with no grounding (SmolVLM2-2.2B, ScreenSpot-v2 0.47) needs a grounding phase first (→ 41.27, then 61.71 after the agentic phase) — [Smol2Operator](https://raw.githubusercontent.com/huggingface/blog/main/smol2operator.md).
- **Model merging** hurt at 2B (−4.2 AW) but helped at 8B (+1.0) and 30B-A3B (+2.1) — [UI-Venus-1.5](https://arxiv.org/html/2602.09082).
- **History (non-AW evidence):**
  - SecAgent-3B offline task accuracy: N=0 36.2 → N=1 72.8; N=1 without semantic context 56.4 (prior notes) — [SecAgent](https://arxiv.org/abs/2603.08533).
  - OpenPhone-3B on AndroidLab: no history 15.2 → 4.3 (prior notes) — [OpenPhone](https://arxiv.org/abs/2510.22009).
- **Resolution / coordinates:**
  - ScaleCUA AW 1080p 23.3 vs 2K 13.4. On ScreenSpot-Pro, raw coords 42.3 beat normalized 37.9 on a Qwen2.5-VL base, whose native convention is absolute — [ScaleCUA](https://arxiv.org/html/2509.15221).
  - Smol2Operator: normalized coords 33.72 vs pixel coords 4.32 on SmolVLM2 — [Smol2Operator](https://raw.githubusercontent.com/huggingface/blog/main/smol2operator.md).
  - MAI-UI: 720p ≈ 1080p, 540p "substantially degrades" — [MAI-UI](https://arxiv.org/html/2512.22047).

### Inferences
- For a fixed 2B model in our harness, the evidence ranks the next levers as follows.
  1. Replace intent-only thoughts with teacher-written structured CoT plus a carried-over progress/state summary. GUI-Libra, MIRAGE and Ferret all show +6 to +13 from thought supervision. The GUI-Libra-81K set is directly reusable; see Q4.
  2. Add environment-grounded trajectories collected on emulator apps, with an AW-test-instruction filter: +5 to +11.
  3. Apply KL-regularized offline RL on step data, which runs on Colab with no emulator: up to +12 at 3B in GUI-Libra.
  4. Run online RL only if the 2-emulator setup can afford it. PhoneBuddy got +17 from just 50 RL steps, but from a 60% SFT start with large-scale rollouts per step.
- The data-mixing results (GUI-Libra 5.2 → 11.3; our v2/v3 flat on AW) point the same way. Adding more offline datasets of the same kind does not substitute for reasoning supervision or interactive data.
- The UI-Venus 2B merge loss is a caution against averaging LoRA adapters or specialist checkpoints at 2B without an AW check.

### Gaps
- No ≤2B paper isolates each ingredient on AW in one controlled table. The 2B evidence is UI-Venus (stage-wise) and MAI-UI (RL only); the rest is 3-4B.
- PhoneBuddy's per-RL-step rollout count and compute were not in the passages read.
- No paper reports AW for LFM-family or other non-Qwen sub-2B agents.

## Q4. Which peers release weights and training data under permissive licenses (data sources, distillation teachers)?

### Takeaway
Weights for nearly all strong small peers are Apache-2.0 or MIT: MAI-UI-2B/8B, UI-Venus-1.5-2B/8B, GELab-Zero-4B, Holo2-4B/8B, Holo3.1-0.8B/4B, GUI-Libra-3B/4B, UI-Voyager-4B, UI-TARS-2B-SFT, ScaleCUA-3B, Qwen3-VL/Qwen3.5. Training data is mostly **not** released by the top industrial recipes (MAI-UI, UI-Venus, Step-GUI, Holo, Ferret-UI Lite). The most useful permissive data for us is GUI-Libra-81K (Apache-2.0, GPT-4.1 reasoning over AC/GUI-Odyssey/AMEX/AitZ/AitW/GUIAct). Others are OS-Atlas data, Aguvis stage-1/2, UI-Genie-Agent-16k, OS-Genesis mobile data, GUI-Net-1M and InfiGUIAgent-Data.

### Cited Findings
- **Weights (HF license tags fetched 2026-11-18):**
  - Apache-2.0:
    - MAI-UI-2B and -8B; also MAI-Gym-9B — [HF API](https://huggingface.co/api/models?author=Tongyi-MAI).
    - UI-Venus-1.5-2B/8B/30B-A3B — [HF API](https://huggingface.co/api/models?search=UI-Venus-1.5).
    - GELab-Zero-4B-preview — [HF](https://huggingface.co/stepfun-ai/GELab-Zero-4B-preview).
    - Holo2-4B and Holo2-8B; Holo3.1-0.8B/4B/9B/35B-A3B — [HF API](https://huggingface.co/api/models?author=Hcompany).
    - GUI-Libra-3B/4B/8B — [HF](https://huggingface.co/GUI-Libra/GUI-Libra-4B).
    - UI-TARS-2B-SFT and UI-TARS-1.5-7B — [HF API](https://huggingface.co/api/models?search=UI-TARS).
    - ScaleCUA-3B/7B/32B — [HF](https://huggingface.co/OpenGVLab/ScaleCUA-3B).
    - OS-Atlas-Base/Pro-4B — [HF](https://huggingface.co/OS-Copilot/OS-Atlas-Pro-4B).
    - InfiGUI-R1-3B and InfiGUI-G1-3B — [HF API](https://huggingface.co/api/models?author=InfiX-ai).
    - AgentCPM-GUI — [HF](https://huggingface.co/openbmb/AgentCPM-GUI).
    - Qwen3-VL-2B/4B and Qwen3.5-2B/4B — [Qwen3-VL-2B](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct); [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B).
    - MobileRL-9B — [HF](https://huggingface.co/xuyifan/MobileRL-9B). ZeroGUI-7B — [HF](https://huggingface.co/OpenGVLab/ZeroGUI-AndroidLab-7B).
  - MIT:
    - UI-Voyager-4B — [HF](https://huggingface.co/MarsXL/UI-Voyager).
    - ShowUI-2B — [HF](https://huggingface.co/showlab/ShowUI-2B).
    - GUI-Actor-2B/3B and Phi-Ground — [HF API](https://huggingface.co/api/models?search=GUI-Actor).
    - GUI-Owl-1.5 (reference) — [HF](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct).
    - OpenCUA-7B — [HF](https://huggingface.co/xlangai/OpenCUA-7B).
  - Restrictive:
    - Holo1.5-3B: "Qwen Research License" — [card](https://huggingface.co/Hcompany/Holo1.5-3B).
    - Holo2-30B-A3B: CC-BY-NC-4.0 ("research-only") — [Holo2-4B card](https://huggingface.co/Hcompany/Holo2-4B).
    - Holotron-3-Nano: NVIDIA Open Model License — [card](https://huggingface.co/Hcompany/Holotron-3-Nano).
  - No license tag: PhoneBuddy-4B / 4B-RealApp / 0.8B weights are public on HF; the 0.8B card says it was "initially published as private for validation" — [PhoneBuddy-0.8B](https://huggingface.co/PhoneBuddyAI/PhoneBuddy-0.8B).
  - Not released: no Ferret-UI Lite weights were found on HF; the paper offers "methods and lessons learned" — [Ferret-UI Lite](https://arxiv.org/html/2509.26539).
- **Training and eval data (HF dataset tags):**
  - Apache-2.0:
    - GUI-Libra-81K-SFT and GUI-Libra-81K-RL — [HF](https://huggingface.co/datasets/GUI-Libra/GUI-Libra-81K-SFT).
    - OS-Atlas-data — [HF](https://huggingface.co/datasets/OS-Copilot/OS-Atlas-data).
    - xlangai aguvis-stage1/stage2 — [HF](https://huggingface.co/datasets/xlangai/aguvis-stage2). The smolagents unified-action-space versions carry no tag — [HF](https://huggingface.co/datasets/smolagents/aguvis-stage-2).
    - InfiGUIAgent-Data — [HF](https://huggingface.co/datasets/InfiX-ai/InfiGUIAgent-Data).
    - GUI-Net-1M (TongUI, web tutorials) — [HF](https://huggingface.co/datasets/Bofeee5675/GUI-Net-1M).
    - GUIAct — [HF](https://huggingface.co/datasets/yiye2023/GUIAct).
    - AndroidDaily tasks (StepFun benchmark) — [HF](https://huggingface.co/datasets/stepfun-ai/AndroidDaily).
  - MIT:
    - UI-Genie-Agent-16k and UI-Genie-RM-517k — [HF](https://huggingface.co/datasets/HanXiao1999/UI-Genie-Agent-16k).
    - OS-Genesis mobile data — [HF](https://huggingface.co/datasets/OS-Copilot/OS-Genesis-mobile-data).
    - AgentNet (desktop) — [HF](https://huggingface.co/datasets/xlangai/AgentNet).
  - CC-BY-4.0: GUI-Odyssey — [HF](https://huggingface.co/datasets/OpenGVLab/GUI-Odyssey); AMEX — [HF](https://huggingface.co/datasets/Yuxiang007/AMEX).
  - CC-BY-NC-4.0: CAGUI (eval only) — [HF](https://huggingface.co/datasets/openbmb/CAGUI).
  - ScaleCUA-Data is public but has no HF license tag; the repo is Apache-2.0 — [HF](https://huggingface.co/datasets/OpenGVLab/ScaleCUA-Data); [repo](https://github.com/OpenGVLab/ScaleCUA).
  - PhoneWorld APKs are tagged "other" — [HF](https://huggingface.co/datasets/EthanLeoLYX/PhoneWorld-APKs).
- **Not released or not mentioned:**
  - MAI-UI training data: the paper does not mention a release — [MAI-UI](https://arxiv.org/html/2512.22047).
  - UI-Venus-1.5 data: "not explicitly stated as released" — [UI-Venus-1.5](https://arxiv.org/html/2602.09082). UI-Venus 1.0 released AW validation trajectories — [UI-Venus README](https://github.com/inclusionAI/UI-Venus).
  - Step-GUI: only the AndroidDaily tasks — [gelab-zero](https://github.com/stepfun-ai/gelab-zero).
  - Holo: "high-quality proprietary data" — [Holo2-4B](https://huggingface.co/Hcompany/Holo2-4B).
  - AutoPlay data: none found on HF.

### Inferences
- **Best permissive distillation teachers for a screenshot-only Android student:**
  - MAI-UI-8B (70.7 self-reported, Apache-2.0; its output format already re-feeds thinking).
  - UI-Venus-1.5-8B (73.7, Apache-2.0; uses one image plus `<conclusion>` summaries, closest to our input format).
  - Holo2-8B (60.4 in Surfer 2, Apache-2.0).
  - GUI-Owl-1.5-8B (MIT).

  Of these, UI-Venus-1.5's single-image format makes its rollouts in our harness least format-mismatched (**inference**).
- Avoid teachers trained on AW templates (UI-Voyager, MobileRL) if we want a clean claim. Their AW-specific behaviour would leak into our student.
- GUI-Libra-81K can replace our intent-only `<think>` with ~210-token GPT-4.1 reasoning on the same AC/GUI-Odyssey/AMEX sources at zero labeling cost. Its action schema and absolute/[0,1000] coordinates need conversion to our JSON and 0-1000 format.

### Gaps
- License terms for PhoneBuddy weights and ScaleCUA-Data are not stated in HF metadata.
- I did not check whether teacher-generated data from Apache/MIT models carries extra conditions inherited from teacher training data (e.g. Qwen base licenses are Apache-2.0, so likely none).
