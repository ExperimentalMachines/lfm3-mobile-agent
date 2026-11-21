# Training recipes of small (≤4B) screenshot GUI agents vs our LFM3-VL-2B recipe (as of 2026-11-21)

Scope and conventions:
- **Our recipe:** LFM3-VL-2B, LoRA r64 on the language model only (vision frozen), SFT only. About 92k step rows: AndroidControl (AC) 69k, GUI-Odyssey 10k, AMEX 7k, ScreenQA 6k. 1,250 steps × 32 rows = 40k rows seen (0.43 epoch). Input is 1 screenshot plus an 8-step text history of (intent, action). Output is a short intent plus one JSON action.
- **Our results:** AndroidWorld (AW) 18/116 on a dev seed. In the same 1-screenshot harness, GUI-Owl-1.5-2B scores 23/116 and MAI-UI-2B 32/116. On MobileWorld (MW) GUI-only we score 6/105, GUI-Owl-1.5-2B 22/105 and MAI-UI-2B 11/105.
- **Labels:**
  - "Own harness" means the number the authors report.
  - "Reproduced" means a third party, or our harness, ran it.
  - "(prior notes)" means the fact is carried over from `docs/research/notes/beating-gui-owl-at-2b-fairly/*.md` or `small-gui-agent-training-methods/*.md` and was not re-fetched today.
  - "Inference" means my reasoning, not a source statement.
- **Avoiding duplication:** the earlier notes already cover ablation gains per ingredient, CoT effects, licenses, harness sensitivity and the contamination taxonomy. This file adds recipe sizes (data volume, epochs, full fine-tuning vs LoRA, inputs), current MW numbers, MW-app overlap, and the LFM-family check.
- Every arXiv paper was read from its arXiv HTML or the Firecrawl research index on 2026-11-21. Dates given are submission dates.

---

## Q1. Per-model recipes: base, data size, data sources, online data, stages, epochs, full fine-tuning vs LoRA, inputs, scores

### Takeaway
Every ≤4B agent above ~40% AW starts from a Qwen-VL base and trains on far more data than we do:
- 10^5–10^6 step samples over 1–3 epochs, or 10–50B tokens of mid-training.
- Nearly all use full-parameter training.
- Almost all add environment-collected data: online RL, self-evolving rollouts, or teacher rollouts in simulators.

Our recipe is the smallest exposure in the table (40k rows, <1 epoch), and the only one that is SFT-only, offline-only and LoRA-only, with no grounding, CoT or answer supervision. The closest published analogues are the plain-SFT, public-data arms of other papers: GUI-Libra-3B SFT, AppVLM-base, Ferret-UI Lite no-CoT and UI-S1 SFT. They land at 5–22% AW, the same band as ours.

### Cited Findings

#### Master table (numbers are each paper's own harness unless marked; do not rank across rows)

| Model (paper date) | Base | SFT / training data volume | Data sources | Online / env data | Stages | Epochs / steps; full fine-tuning vs LoRA | Inputs (history) | AW | MW GUI-only | AC-High / AC-Low |
|---|---|---|---|---|---|---|---|---|---|---|
| **Ours** | LFM3-VL-2B | 92k steps; 40k seen | AC, GUI-Odyssey, AMEX, ScreenQA | none | SFT | 1,250 × 32 = **0.43 epoch**; **LoRA r64, LM only, vision frozen** | 1 shot + 8-step (intent, action) text | 18/116 (ours) | 6/105 (ours) | v1: 71.5 / 94.8 (prior notes) |
| **GUI-Owl-1.5-2B** ([2602.16855](https://arxiv.org/html/2602.16855v1), 15 Feb 2026) | Qwen3-VL (2B) | **Not disclosed** | Human DAG tasks, real-device rollouts with checkpoint repair, human demos, "vibe-coded" virtual envs, CoT synthesis by teacher VLMs (prior notes) | Yes: cloud phones and virtual envs; MRPO online RL | Pre-train → SFT → RL | Not disclosed; full post-train (prior notes) | Official AW code: up to 5 screenshots; MW repo: `history_n=1` (prior notes) | **67.9** own; **23/116** ours | **32.2** leaderboard (3 runs; paper 31.3); **22/105** ours | not reported |
| **MAI-UI-2B** ([2512.22047](https://arxiv.org/html/2512.22047), 26 Dec 2025) | Qwen3-VL-2B | **No counts given** for grounding, navigation or self-evolving data ([MAI-UI](https://arxiv.org/html/2512.22047)) | Open datasets, app-manual tasks, expert tasks, self-evolving rejection-sampled trajectories (prior notes) | Yes: online RL, 32→512 parallel envs on 10 ECS servers, "over 35 applications" incl. **Mattermost, Mastodon, Mall4Uni**; group size 16 ([MAI-UI](https://arxiv.org/html/2512.22047)) | SFT → grounding RL → online RL | Epochs, LR and full/LoRA not stated ([MAI-UI](https://arxiv.org/html/2512.22047)) | Current + 2 previous screenshots in code (`history_n=3`) (prior notes) | **49.1** own (SFT 45.1); **32/116** ours | not on official leaderboard; **11.1** reproduced by ClawGUI ([2604.11784](https://arxiv.org/html/2604.11784)); **11/105** ours | 67.3 / — |
| **UI-Venus-1.5-2B** ([2602.09082](https://arxiv.org/html/2602.09082), 9 Feb 2026) | Qwen3-VL-2B | Mid-training **10B tokens** over 30+ datasets ([UI-Venus-1.5](https://arxiv.org/html/2602.09082)) | Open GUI datasets + device-cloud rollouts | Yes: online RL on a Device-as-a-Service cloud, "thousands of heterogeneous devices"; tasks from an LLM-built "static task library" for "a predefined set of applications" plus MLLM-generated tasks; easy/medium/hard step buckets ([UI-Venus-1.5](https://arxiv.org/html/2602.09082)) | Mid-train → offline RL → online RL → TIES merge | Not stated | 1 screenshot + previous actions text (prior notes) | **55.6** own (stages 39.0 → 45.3 → **59.8** → 55.6) | not on leaderboard (30B-A3B: 17.1). VenusBench-Mobile: 2B **8.7** vs MAI-UI-2B 6.7 ([UI-Venus-1.5 T4](https://arxiv.org/html/2602.09082)) | — |
| **UI-Venus-1.0-7B** ([2508.10833](https://arxiv.org/html/2508.10833), Aug 2025) | Qwen2.5-VL-7B | Navigation: **350k** cleaned samples from GUI-Odyssey 114k, AITZ 14k, AC 84k, AitW 371k, AMEX 39k, self-annotated Chinese apps 20k, grounding 107k, VQA 42k. Separate grounding set: 627k → 107k ([UI-Venus](https://arxiv.org/html/2508.10833)) | Same open sets as ours plus AitW/AITZ, own annotation, grounding, VQA; information-retrieval traces rebuilt with an inserted `CallUser` answer step | "Iteratively trace generation" on a "virtual cloud environment … dozens of available mobiles" ([UI-Venus](https://arxiv.org/html/2508.10833)) | **GRPO RFT only (no SFT)** | **10 epochs** at 7B (1 at 72B), lr 4e-7, global batch 256; `freeze_vit=True` for navigation ([UI-Venus](https://arxiv.org/html/2508.10833)) | Current screenshot + text (thought, action) history | 49.1 (72B 65.9) | 8.5 (72B 16.4) leaderboard | 76.1 / 92.4 (step SR) |
| **UI-TARS-2B-SFT** (2501.12326, Jan 2025) (prior notes) | Qwen2-VL-2B | **~50B tokens** (perception, grounding, action traces, reflective online traces) | Open mobile traces (145k) + own 14.9k | reflective online traces | Continued pre-training + SFT | full | Last **5** screenshots + full thought/action history | no 2B AW number | — | 68.9 / 89.3 |
| **UI-TARS-1.5 / UI-TARS-2** | Open weights only at 7B (1.5); UI-TARS-2 ≈230B MoE, AW 73.3 (prior notes) | — | — | — | — | — | — | not ≤4B | Doubao-1.5-UI-TARS 26.3 leaderboard | — |
| **AgentCPM-GUI-8B** ([2506.01391](https://arxiv.org/html/2506.01391), 2 Jun 2025), >4B reference | MiniCPM-V 8B | Grounding pre-training **12M** samples; SFT **55k trajectories / 470k steps** ([AgentCPM-GUI](https://arxiv.org/html/2506.01391)) | Self-collected Chinese apps + AC, AITZ, GUI-Odyssey, AMEX, AitW, GUICourse, OS-Atlas, UGround | none (offline RFT/GRPO) | Grounding pre-training → SFT → GRPO RFT | **3 epochs**, lr 1e-5, ZeRO-2 **full** fine-tuning ([AgentCPM-GUI](https://arxiv.org/html/2506.01391)) | query + screenshot; compact JSON, 9.7 output tokens on average | not reported by authors; **16.4** reproduced by UI-S1 ([2509.11543](https://arxiv.org/html/2509.11543)) | — | 69.2 / 90.2 (EM) |
| **UI-S1-7B** ([2509.11543](https://arxiv.org/html/2509.11543), Sep 2025), >4B reference | Qwen2.5-VL-7B | SFT on **AC-Train + AMEX** (size not stated) | AC, AMEX (offline only) | Semi-online: rollouts *through static trajectories* with the model's own history, patching expert actions | SFT → semi-online RL | RL: 5 epochs, lr 1e-6, batch 32, 4×8 GPUs; full/LoRA not stated ([UI-S1 T9](https://arxiv.org/html/2509.11543)) | **2 historical images** + text history | SFT **21.7** → +semi-online RL **34.0** (base 14.9 in their prompt) | — | AC-High SR 59.5 (their metric) |
| **GUI-Libra-3B / 4B** ([2602.22190](https://arxiv.org/html/2602.22190), Feb 2026) | Qwen2.5-VL-3B / Qwen3-VL-4B | **19k traj / 170k steps → filtered 9k traj / 81k steps** ([GUI-Libra](https://arxiv.org/html/2602.22190)) | AC, GUI-Odyssey, AMEX, AitZ, AitW, GUIAct, MM-Mind2Web, with GPT-4.1 reasoning | none (offline GRPO on 40k steps, 300 iterations) | SFT (action-aware) → offline RL | **1 epoch on the mixed set / 2 epochs on 81K**, effective batch 256, lr 1e-5, **full** fine-tuning ([GUI-Libra](https://arxiv.org/html/2602.22190)) | 1 screenshot + previous actions text | 3B **25.2** (plain SFT 5.2); 4B **42.6** (base 27.0 in their harness) | — | AC-v2 57.3 / 85.9 (3B) (prior notes) |
| **Ferret-UI Lite-3B** ([2509.26539](https://arxiv.org/html/2509.26539), 30 Sep 2025) | Internal Apple 3B + ViTDet | **10K SFT steps** (batch not given); mixture incl. Aguvis-Planning mobile 259.6K, OpenCUA 420.8K, synthetic mobile 70K / desktop 75K; online synthetic navigation up to **17K trajectories** ([Ferret-UI Lite](https://arxiv.org/html/2509.26539)) | Aguvis, OpenCUA, grounding sets, synthetic | Yes: multi-agent system "interacts directly with GUI platforms to generate synthetic rollouts"; environment not named ([Ferret-UI Lite](https://arxiv.org/html/2509.26539)) | SFT → RLVR (GRPO, 1,500 steps, 32 samples/prompt) | 10K SFT steps; full/LoRA not stated | Screenshot + past-action history; zoom crop | **28.0** (mean of 5 runs; SFT 25) | — | 68.9 / 86.6 |
| **InfiGUI-R1-3B** ([2504.14239](https://arxiv.org/html/2504.14239), Apr 2025) | Qwen2.5-VL-3B | RL data: AC **10k traj + 2k reflection traj**, grounding 5k, MathV360K 11k, COCO 4k ([InfiGUI-R1](https://arxiv.org/html/2504.14239)) | AC + teacher reasoning (QwQ-32B / Qwen2.5-VL-32B) | none | Reasoning distillation SFT → RLOO | batch 256, lr 1e-6, 16 rollouts; full/LoRA not stated | screenshot + history | not reported | — | 71.1 / 92.1 |
| **InfiGUI-G1-3B** (Aug 2025) | Qwen2.5-VL-3B | Grounding-only RL (AEPO) (prior notes) | — | — | — | — | — | no agent AW | — | — |
| **OpenPhone-3B** ([2510.22009](https://arxiv.org/html/2510.22009), Oct 2025) | Qwen2.5-VL-3B | "Synthetic GUI data"; size not stated in passages read ([OpenPhone](https://arxiv.org/html/2510.22009)) | Gemini-2.5-Pro CoT, then Qwen3-32B synthesizes instances | not clear | SFT → GRPO | not stated | **SoM-annotated** screenshot + text history summary | no AW; **AndroidLab 15.2** (LLM-judged variant of AndroidLab) | — | — |
| **UI-Genie-Agent-3B** ([2505.21496](https://arxiv.org/html/2505.21496), May 2025) | Qwen2.5-VL-3B | Initial SFT: AC 88k steps / 15,283 traj; AMEX 34k / 2,946; AndroidLab 6k / 726. Then **+16k synthetic trajectories** over 3 self-improvement rounds; reward-model data 517k ([UI-Genie](https://arxiv.org/html/2505.21496)) | Open + self-generated, reward-model filtered | Yes: "dynamic Android environment (incl. AndroidLab apps)" | SFT → 3 rounds of RM-filtered self-improvement | 3B: **full** fine-tuning, **vision frozen**, lr 1e-5, batch 160; 1 epoch per new round. 72B: **rsLoRA r64 α256** + PiSSA ([UI-Genie](https://arxiv.org/html/2505.21496)) | **5 most recent screenshots** + language action summary | not reported; AndroidLab **28.8** | — | 72.9 / 93.8 |
| **MobileRL-7B/9B** ([2509.18119](https://arxiv.org/html/2509.18119), Sep 2025), >4B reference | Qwen2.5-VL-7B / GLM-4.1V-9B | Reasoning-free SFT **97.9k steps** (AC-Low 21.3k, AC-High 14.3k, human annotation 62.2k); reasoning SFT 23.6k steps ([MobileRL](https://arxiv.org/html/2509.18119)) | AC + human annotation | Yes: AdaGRPO on **2,000 AW tasks + 1,103 AndroidLab tasks**, 256 parallel AVDs, 100 steps, n=16 | SFT → reasoning SFT → online RL | SFT **2 epochs**, lr 1e-5→1e-6, batch 256, FSDP (full) | screenshot + compressed XML | 7B: SFT 50.2 → 56.8 → **72.0**; 9B **80.2** | — | — |
| **ClawGUI-2B** ([2604.11784](https://arxiv.org/html/2604.11784), 13 Apr 2026) | MAI-UI-2B | RL only; task count not stated | — | Yes: **64 parallel MobileWorld Docker emulators**, GiGPO, group size 8, Qwen3.5-72B process-reward judge ([ClawGUI](https://arxiv.org/html/2604.11784)) | Online RL on top of MAI-UI-2B | **3 epochs**, lr 1e-6, batch 8; full/LoRA not stated | Policy history not stated | — | **17.1** own (GRPO 14.5; base 11.1) | — |
| **MobileWeave-4B** ([2611.23860](https://arxiv.org/html/2611.23860), 18 Nov 2026) | Qwen3-VL-4B | **2,198 synthesized tasks → 1,332 teacher trajectories / ~15.4k steps**, plus recovery set 104 traj / 1,008 steps ([MobileWeave](https://arxiv.org/html/2611.23860)) | Teacher Qwen3.8-27B in the MobileGym browser simulator (+ GPT-6.1 Sol for loop recovery) | Yes: teacher rollouts in the simulator; recovery labels at **the policy's own stalls** | SFT → recovery SFT | SFT **3 epochs**, batch 32, lr 1e-5, **full**; recovery 200 updates, lr 2e-6, vision and projector frozen | **1 screenshot** + text (Observation, Action) for up to 30 steps | **52.9 ± 2.0** (base 44.0) | **22.8 ± 1.1** own (base 9.1) | — |
| **AppVLM-3B** ([2502.06395](https://arxiv.org/html/2502.06395), Feb 2025) | PaliGemma-3B-896 | AC SFT, then rejection-sampled RFT rounds on AW-environment rollouts | AC + **AW environment** | Yes: AW tasks with varied parameters | SFT → iterative RFT → final SFT | **3 epochs** every round, batch 64, lr 3e-6, **full ("without using any adapters")** ([AppVLM](https://arxiv.org/html/2502.06395)) | SoM-annotated screenshot + last 5 actions text | AC-only SFT **11.4** → **37.8** (82-task subset with QA/verification/drawing removed; 3 seeds) | — | AC IDD 73.9 (relaxed accuracy) |
| **PhoneBuddy-4B** (2606.23049, Jun 2026) (prior notes) | Qwen3.5-4B | **950,758 steps**; 1,115 optimizer steps × batch 512, packed 8,192 tokens | Real apps + PhoneWorld mock apps | Yes: 50 online RL steps | SFT → RL | full, lr 1e-5→1e-6 | 1 screenshot + thought/action history + intermediate state | SFT 60.3 → 83.2 | — | — |
| **Step-GUI-4B / GELab-Zero-4B** (2512.15431, Dec 2025) (prior notes) | Qwen3-VL-4B | Mid-training ≈11.2M samples; cold-start SFT ≈1.67M | mixed + 6 self-evolving rounds | Yes | Mid-train → SFT → GRPO | — | screenshot + logs | 63.9 pass@1 | **16.1** leaderboard | — |
| **UI-Voyager-4B** (2603.24533, Mar 2026) (prior notes) | Qwen3-VL-4B | 4 RFT rounds on **>7,000 AW-template tasks** | AW templates | Yes (AW) | RFT → GRSD | — | h-step history | 81.0 (64 seeds) | — | — |

Supporting details:
- **MW official numbers for ≤4B models** (leaderboard JSON, fetched 2026-11-21; 117 GUI-only tasks; max 50 steps) — [MobileWorld leaderboard](https://tongyi-mai.github.io/MobileWorld/leaderboard.json):
  - Only two ≤4B rows exist: GUI-Owl-1.5-2B-Instruct 32.2 (3 runs; `num_images_in_history` null) and GELab-Zero-4B 16.1 (1 run).
  - No MAI-UI-2B, UI-Venus-1.5-2B or ClawGUI-2B row.
  - Reference rows: MAI-UI-8B 27.5, GUI-Owl-7B 7.7, UI-Venus-7B 8.5, Qwen3-VL-8B 9.4.
- **Reproduced MW numbers:**
  - ClawGUI-Eval reports MAI-UI-2B **11.1** and MAI-UI-8B **19.7**, against 27.5 on the official leaderboard — [ClawGUI T1](https://arxiv.org/html/2604.11784).
  - Our 11/105 (10.5%) for MAI-UI-2B is close to ClawGUI's 11.1.
  - Our 22/105 (21.0%) for GUI-Owl-1.5-2B is about 11 points under its leaderboard 32.2. The leaderboard uses 117 tasks and our subset 105, so this is an approximate comparison.
- **AW harness effect on the two reference models** (own harness vs our harness):
  - GUI-Owl-1.5-2B: 67.9 → 19.8%.
  - MAI-UI-2B: 49.1 → 27.6%.
  - In our harness MAI-UI-2B beats GUI-Owl-1.5-2B on AW (32 vs 23), the reverse of their MW ordering (11 vs 22).
- **Output format:** GUI-Owl-1.5-2B-Instruct's official AW prompt asks for "Action: a short imperative" plus one `<tool_call>` and requests no thinking (prior notes, [gui_owl.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py)). That is structurally the same as our "short intent + JSON action".
- **What SFT-only on public offline data yields:**

  | Model | Data | AW |
  |---|---|---|
  | GUI-Libra-3B, plain SFT | 81K | **5.2** ([GUI-Libra](https://arxiv.org/html/2602.22190)) |
  | AppVLM-base 3B | AC only, harder 82-task subset | **11.4** ([AppVLM](https://arxiv.org/html/2502.06395)) |
  | Ferret-UI Lite, no-CoT | human data | **13.7** (prior notes) |
  | UI-S1-7B, SFT | AC + AMEX | **21.7** ([UI-S1](https://arxiv.org/html/2509.11543)) |
  | MobileRL-7B, reasoning-free SFT | AC + 62.2k human-annotated steps of unstated origin; XML input | **50.2** ([MobileRL](https://arxiv.org/html/2509.18119)) |

- **Base-model starting points:**
  - Qwen3-VL-4B is already at 44.0 AW in MobileWeave's harness and 27.0 in GUI-Libra's — [MobileWeave](https://arxiv.org/html/2611.23860); [GUI-Libra](https://arxiv.org/html/2602.22190).
  - Qwen3-VL-2B is 36.4 (vendor, prior notes).
  - Untuned LFM3-VL-2B scored 1/116 in our harness (prior doc `small-gui-agent-training-methods.md`).
  - On grounding, LFM3-VL-2B reports ScreenSpot-Pro 55.5 and ScreenSpot-v2 mobile 92.2 — [LFM3-VL-2B card](https://huggingface.co/LiquidAI/LFM3-VL-2B). GUI-Owl-1.5-2B reports ScreenSpot-Pro 57.8 and ScreenSpot-v2 89.7 (prior notes).
- **LoRA among peers:**
  - Only UI-Genie's 72B uses LoRA (rsLoRA r64) — [UI-Genie](https://arxiv.org/html/2505.21496).
  - The AndroidControl authors' best model, "LT-all-r64", was PaLM-2S with LoRA adapters (AC IDD 70.8, as quoted by [AppVLM](https://arxiv.org/html/2502.06395)).
  - CoAdapt-GUI updates "a LoRA adapter on a frozen vision-language model" for test-time adaptation — [2608.11588](https://arxiv.org/abs/2608.11588).
  - Every ≤4B agent with an AW number that states its method uses full fine-tuning: GUI-Libra, UI-Genie-3B, AppVLM, MobileWeave and PhoneBuddy.
- **Frozen vision is common, not unusual:**
  - UI-Venus navigation (`freeze_vit=True`) — [UI-Venus](https://arxiv.org/html/2508.10833).
  - UI-Genie-3B — [UI-Genie](https://arxiv.org/html/2505.21496).
  - MobileWeave's recovery stage — [MobileWeave](https://arxiv.org/html/2611.23860).

### Inferences
- **Where ours is unusually small.** Rows seen: 40k. In tokens (inference), that is about 40k × ~1.1–1.3k tokens, roughly 45–50M, using the ~720 image tokens per row from the prior doc plus text. That is ~200× less than UI-Venus-1.5's 10B-token mid-training and ~1,000× less than UI-TARS-2B's ~50B. Only MobileWeave (~46k step-samples over 3 epochs) is comparable in samples seen. It started from a base already at 44 AW, used teacher-written online trajectories, and added recovery labels at the policy's own stalls.
- **Where ours is offline-only.** Of the ≤4B agents above 40 AW, only GUI-Libra-4B (offline SFT + offline GRPO) and MIRAGE-4B (SFT, prior notes) used no environment interaction. Both start from Qwen3-VL-4B, which is already at 27–45 AW.
- **Where ours is narrow:**
  - We use 4 mobile-only datasets.
  - We have no grounding data. UI-Venus used 107k grounding samples and AgentCPM-GUI 12M.
  - We have no teacher CoT (GUI-Libra, InfiGUI-R1, GUI-Owl).
  - We have no answer-insertion. UI-Venus rebuilt information-retrieval traces with `CallUser`; ours has zero answer labels (prior doc).
  - We have no self-generated or online-collected data.
- **Where ours is normal:** frozen vision, a single screenshot with text history (UI-Venus-1.5, GUI-Libra, MobileWeave and PhoneBuddy all use one image), and a short non-CoT output (GUI-Owl-1.5-Instruct).

### Gaps
- MAI-UI and GUI-Owl-1.5 disclose no data counts, epochs, learning rates or full-vs-LoRA. Their 2B recipes cannot be sized.
- UI-Venus-1.5-2B: offline-RL data size, online-RL task count and steps, and epochs are not stated.
- UI-S1's 3B scaling result (Table 6) was not retrievable from the passages, and its SFT data size is not stated.
- The Ferret-UI Lite SFT batch size, and so its samples seen, is not given.
- OpenPhone's training-data size and its exact apps were not in the passages retrieved.
- PhoneBuddy's epoch count cannot be computed from "1,115 steps × batch 512 packed sequences" without the mean tokens per step.

---

## Q2. Who trains on AndroidWorld-like environments or MobileWorld apps, and who discloses contamination controls?

### Takeaway
Four kinds of AW exposure appear among small agents:
- **Training on AW templates or the AW environment** is explicit for MobileRL, UI-Voyager and AppVLM (and ADMIRE/AutoPlay per prior notes).
- **MobileWorld exposure:**
  - ClawGUI-2B ran its RL inside MobileWorld's own Docker environment and reports MW GUI-only. Its task source and test separation are undisclosed.
  - MAI-UI's RL environment contains MobileWorld's self-hosted apps (Mattermost, Mastodon, Mall4Uni), from the same lab.
- **Undisclosed real-device/cloud environments:** GUI-Owl-1.5, UI-Venus-1.0/1.5 and Ferret-UI Lite use cloud or real-device environments with unnamed apps and no benchmark decontamination statement.
- **Explicit test-overlap controls** appear in only a minority: MobileRL (exact-instance removal), MobileWeave (embedding dedup against MobileGym test), and AndroidLab training splits (manual non-overlap).

### Cited Findings

| Model | AW exposure | MW app exposure | Disclosed control |
|---|---|---|---|
| MobileRL | **2,000 AW tasks** generated "by replacing predefined substitutable components" and varying initial states; AW rule rewards | — | Removes tasks "whose specific content and initial states coincide with those in the test set"; AndroidLab 1,103 tasks "manually verified … non-overlap with the test set" ([MobileRL](https://arxiv.org/html/2509.18119)) |
| AppVLM-3B | RFT on AW-environment rollouts with varied task parameters; the authors call this "essential … to adapt to tasks in AndroidWorld" | — | None; evaluates on an 82-task subset over 3 seeds ([AppVLM](https://arxiv.org/html/2502.06395)) |
| UI-Voyager-4B | >7,000 AW-template tasks (prior notes) | — | None (prior notes) |
| ClawGUI-2B | — | **RL in 64 MobileWorld Docker emulators** ("launches dozens of Docker-based Android emulators in parallel via MobileWorld"); "the environment initializes the device state and loads a new task" | **None**; training-task source and count not stated; evaluated on MW GUI-only ([ClawGUI](https://arxiv.org/html/2604.11784)) |
| MAI-UI | Prompt hard-codes AW app names (prior notes) | RL apps include **Mattermost, Mastodon, Mall4Uni** among "over 35 applications" | "No statement about decontamination" in the paper ([MAI-UI](https://arxiv.org/html/2512.22047)) |
| MAI-Gym-9B (>4B) | — | Synthesized **1,000 training tasks inside MobileWorld**, yet calls MW a benchmark "whose tasks never appear in training" (prior notes; [2610.20939](https://arxiv.org/abs/2610.20939)) | Task-level only |
| GUI-Owl-1.5 | AW used as a development metric in v1; no app exclusion stated (prior notes) | Cloud phones and virtual envs; apps unnamed | None (prior notes) |
| UI-Venus-1.5 | Online-RL tasks from "a predefined set of applications" (unnamed) | unnamed | Dedups new tasks only against its own pool (semantic threshold ψ < ε), not against benchmarks ([UI-Venus-1.5](https://arxiv.org/html/2602.09082)) |
| UI-Venus-1.0 | Cloud env with "dozens of available mobiles", Chinese and English apps | unnamed | None found ([UI-Venus](https://arxiv.org/html/2508.10833)) |
| Ferret-UI Lite | Synthetic online rollouts; platforms unnamed | — | None found ([Ferret-UI Lite](https://arxiv.org/html/2509.26539)) |
| UI-Genie | Trajectory generation in an env "including AndroidLab apps"; SFT includes AndroidLab's 726-trajectory train set; evaluated on AndroidLab | — | None found ([UI-Genie](https://arxiv.org/html/2505.21496)) |
| OpenPhone | Evaluated on AndroidLab + 4 added apps (Chrome, TikTok, Reddit, **Gmail**) | — | None in passages read ([OpenPhone](https://arxiv.org/html/2510.22009)) |
| MobileWeave | Trains only in the MobileGym simulator (apps incl. Calendar, Clock, SMS, Settings, Notes) | same | BGE-M3 embedding dedup against MobileGym test. States that AW, AndroidLab and MW "run on different apps and UIs" ([MobileWeave](https://arxiv.org/html/2611.23860)) |
| GUI-Libra, AgentCPM-GUI, UI-S1, InfiGUI-R1 | Offline public datasets only; no environment training | — | No statement, but no environment exposure ([GUI-Libra](https://arxiv.org/html/2602.22190); [AgentCPM-GUI](https://arxiv.org/html/2506.01391); [UI-S1](https://arxiv.org/html/2509.11543)) |

- The MobileWorld leaderboard itself flags tasks or prior trajectories used as memory. KnowAct-GUIClaw notes "GUI memory induced from prior MobileWorld trajectories" — [leaderboard](https://tongyi-mai.github.io/MobileWorld/leaderboard.json).
- MW's self-hosted apps are Mattermost, Mastodon and Mall4Uni. Its Fossify calendar/gallery/messages apps are forks of the Simple apps AW uses (prior notes, inference there).

### Inferences
- For a "clean" comparison on MW, ClawGUI-2B (+6.0 over MAI-UI-2B) and MAI-UI (same lab, same apps) are the least clean small baselines. GUI-Owl-1.5-2B's 32.2 is self-submitted from undisclosed environments.
- Our offline-public-data recipe sits in the same exposure class as GUI-Libra, AgentCPM-GUI and UI-S1: no environment interaction at all. That class has no app-level contamination channel beyond whatever the public datasets contain.

### Gaps
- Not verified: whether AMEX or GUI-Odyssey episodes include Gmail, Google Calendar or other apps that overlap MW's email/calendar tasks. That needs a package-name scan of our own training rows.
- ClawGUI's training task list is not public in the passages read. Whether it reused MW test tasks cannot be ruled out.
- MAI-UI's full list of the 35+ RL apps was not found.

---

## Q3. How much SFT data and how many epochs do small agents use? Is 0.43 epoch of 92k rows unusual?

### Takeaway
Yes. No ≤4B agent recipe found trains its main SFT stage for under 1 epoch. The norm is 1–3 epochs of full fine-tuning on 80k–1M step samples, about 2–35× more samples seen than our 40k. Two facts complicate a simple "train longer" reading:
- GUI-Libra's 2 epochs over 81K at batch 256 amount to only about 630 optimizer updates, fewer than our 1,250 (inference).
- MobileWeave shows ~46k samples can move AW by +9 when the data is teacher-online and failure-targeted.

The gap is samples seen, data kind and full-vs-LoRA capacity, not update count.

### Cited Findings

| Recipe | Base size | SFT unique samples | Epochs | Samples seen (inference = unique × epochs) | Full / LoRA | Source |
|---|---|---|---|---|---|---|
| **Ours** | 2B | 92k | **0.43** | **40k** | LoRA r64 | — |
| MobileWeave-4B | 4B | ~15.4k (+1k recovery) | 3 (+200 updates) | ~46k (+3.2k) | full | [MobileWeave](https://arxiv.org/html/2611.23860) |
| GUI-Libra-3B/4B | 3–4B | 81k (mixed set larger) | 2 (1 on mixed) | ~162k | full | [GUI-Libra](https://arxiv.org/html/2602.22190) |
| UI-Genie-Agent-3B | 3B | ~128k initial + 16k traj synthetic | 1 per new round (initial not stated) | ≥128k | full, vision frozen | [UI-Genie](https://arxiv.org/html/2505.21496) |
| MobileRL-7B | 7B | 97.9k + 23.6k | 2 | ~243k | full (FSDP) | [MobileRL](https://arxiv.org/html/2509.18119) |
| AppVLM-3B | 3B | AC (~88k steps per UI-Genie's count) | 3 per round | ~264k on AC alone | full, "without … adapters" | [AppVLM](https://arxiv.org/html/2502.06395); [UI-Genie T1](https://arxiv.org/html/2505.21496) |
| Smol2Operator | 2.2B | 400k (phase 1) | 2 per phase | ~800k (phase 1) | not stated | [HF blog](https://huggingface.co/blog/smol2operator) |
| UI-Venus-7B (RFT, not SFT) | 7B | 350k | 10 | 3.5M (×rollouts) | LM tuned, vision frozen | [UI-Venus](https://arxiv.org/html/2508.10833) |
| AgentCPM-GUI-8B | 8B | 470k (+12M grounding pre-training) | 3 | ~1.4M | full | [AgentCPM-GUI](https://arxiv.org/html/2506.01391) |
| PhoneBuddy-4B | 4B | 950,758 steps | 1,115 steps × batch 512 packed | ~0.57M packed sequences | full | (prior notes) |
| UI-Oceanus 2B/4B | 2–4B | CPT 3.2B tokens; SFT n/a | CPT 1, SFT 2 | — | full | (prior notes) |
| Ferret-UI Lite-3B | 3B | mixture >1M samples | 10K steps (batch not given) | — | not stated | [Ferret-UI Lite](https://arxiv.org/html/2509.26539) |
| L-Operator (LFM2-VL-1.6B) | 1.6B | "Android control episodes" (unspecified) | **1** | — | **LoRA r16 α32** | [HF card](https://huggingface.co/Tonic/l-android-control) |

- RL/RFT stages run more epochs than SFT: UI-S1 5 ([UI-S1](https://arxiv.org/html/2509.11543)), ClawGUI 3 ([ClawGUI](https://arxiv.org/html/2604.11784)), UI-Venus 10 ([UI-Venus](https://arxiv.org/html/2508.10833)).
- Under-training before RL can be deliberate:
  - Ferret-UI Lite: RL gains are largest after fewer SFT steps (2K vs 6K vs 10K).
  - WinDOM (Qwen3.5-2B): an under-saturated cold start was the better GRPO initializer.
  - Contradicted for math by "Rethinking Expert Trajectory Utilization".
  - (prior notes; [WinDOM 2606.25964](https://arxiv.org/abs/2606.25964))
- Data repetition can beat breadth in general SFT: 128 epochs on 400 samples beat 1 epoch on 51,200 at a fixed update budget (Olmo3-7B, not GUI) (prior notes).

### Inferences
- **0.43 epoch is unusual for an SFT-only, final-deployment model.** The sub-epoch evidence (Ferret, WinDOM) only applies when RL follows, which our recipe does not.
- **AC gets about 0.43 × 69k ≈ 30k rows seen**, roughly one-third of AC's ~88k training steps per UI-Genie's count. Some AC episodes are likely never seen. This matters less for AC test accuracy (near ceiling at 0.948 Low) than for AW coverage (inference).
- **Update count is not the gap.** GUI-Libra's ~630 updates at batch 256 versus our 1,250 at batch 32 suggests the bigger differences are 4× more samples seen per run, full-parameter updates (lr 1e-5), and teacher-reasoning targets.
- **The best cheap peer is MobileWeave-4B:** ~46k samples, about the same as ours, and +8.9 AW / +13.7 MW. Its data was online teacher rollouts plus stall-recovery labels on the policy's own failures. That supports changing the data kind over just adding epochs of the same 4 offline datasets. Caveat: a 4B Qwen3-VL base already at 44.0 AW.

### Gaps
- No ≤4B paper sweeps SFT epochs against AW success at fixed data. The closest are Ferret-UI Lite's 2K/6K/10K-step cold-start study (reported for RL gain, not SFT-only AW) and GUI-Libra's 1-vs-2-epoch note.
- No ≤4B AW ablation of LoRA vs full fine-tuning was found (the prior notes reach the same conclusion).
- Exact unique-step counts after filtering are missing for Ferret-UI Lite, UI-S1 and OpenPhone.

---

## Q4. Anything published on LiquidAI LFM2 / LFM2.5 / LFM3-VL as GUI agents?

### Takeaway
No peer-reviewed or arXiv paper trains or evaluates an LFM-family VLM as a GUI agent on AndroidWorld, MobileWorld or AndroidControl. Evidence is limited to the following, so our LFM3-VL-2B AW/MW numbers appear to be the only public agent-benchmark numbers for an LFM VLM.
- **Liquid's own model cards and blogs** report grounding and GUI-understanding scores, plus one tool-use "Agentic" category.
- **One community AndroidControl fine-tune** of LFM2-VL-1.6B (LoRA r16, 1 epoch) reports only a self-reported action accuracy.
- **Liquid tutorials** cover text tool-calling and browser-control agents, not screenshot mobile agents.

### Cited Findings
- **LFM3-VL-2B model card** (fetched 2026-11-21) — [HF card](https://huggingface.co/LiquidAI/LFM3-VL-2B):
  - ScreenSpot-Pro 55.5 (49.3 without thinking). Comparisons: Qwen3.5-2B 38.1, Qwen3.5-4B 50.6.
  - ScreenSpot-v2: desktop 94.6, mobile 92.2, web 89.9.
  - "GUI understanding" category 83.1 (Qwen3.5-2B 67.2).
  - "Agentic" (MM-ToolSandbox) 42.5 (Qwen3.5-2B 15.2).
  - No AndroidWorld number.
  - Pipeline: LFM3-1.7B-Base (22T tokens, last 3.5T with "a larger share of agentic traces and tool calls") → vision mid-training → SFT including grounding and agentic traces → vision RL → multi-domain on-policy distillation.
  - Fine-tuning links point to TRL SFT/GRPO notebooks. No LoRA targets or rank are given.
- **LFM2.5-VL-3B** (HF blog, 12 Aug 2026) — [HF blog](https://huggingface.co/blog/LiquidAI/lfm2-5-vl-3b):
  - ScreenSpot-v2 mobile 81.2 / desktop 78.7 / web 82.2, against LFM2-VL-3B's 7.6 / 6.0 / 2.5. LFM2 had essentially no GUI grounding.
  - No agent benchmark.
  - Liquid's announcement says it "suits screen and UI agents" — [Liquid AI on X](https://x.com/liquidai/status/2087539876929441983).
- **LFM2 tech report** ([2511.23404](https://arxiv.org/abs/2511.23404), 28 Nov 2025): LFM2-VL's SFT used "no explicit grounding supervision such as bounding boxes or point coordinates" (prior notes).
- **Community fine-tune "L-Operator"** — [HF card](https://huggingface.co/Tonic/l-android-control):
  - Base LFM2-VL-1.6B; LoRA r16 / α32; 1 epoch on "Android control episodes".
  - Max 256 image tokens with image splitting; JSON action output.
  - Self-reported "Action Accuracy on Android Control Episodes" 0.980. Metric and split are undefined; there is no AW number.
  - The prior notes date it Aug 2025.
- **Liquid tutorials:** a Kotlin "tool-calling agent on Android" with LFM2.5-1.2B-Instruct ([Liquid docs](https://docs.liquid.ai/examples/android/tool-calling-agent)), and "Fine-tuning LFM2-350M for browser control with GRPO and OpenEnv" in the cookbook index ([Liquid4All cookbook](https://github.com/Liquid4All/cookbook)). Neither is a screenshot mobile GUI agent.
- **Vendor claims for LFM3** (prior notes, [Liquid LFM3 blog](https://www.liquid.ai/blog/lfm3)):
  - LFM3-1.7B (text) vs Qwen3.5-2B on 65 macOS tasks: 64% vs 48%.
  - LFM3-VL fine-tuning demos: SFT+GRPO on one A100; a 2.8M-sample navigation fine-tune.
- **Searches with no GUI-agent hit:** arXiv (Firecrawl research index, from 2025-06) and the web, for LFM2-VL / LFM2.5-VL / LFM3-VL with AndroidWorld, ScreenSpot or computer use. The only non-Liquid paper using LFM2-VL was a clinical screenshot-classification study — [JMIR 2026, doi:10.2196/90581](https://doi.org/10.2196/90581).

### Inferences
- LFM3-VL-2B's grounding (ScreenSpot-Pro 55.5) is about equal to GUI-Owl-1.5-2B's (57.8, prior notes), while its untuned AW is ~1/116. The 2B-class gap to GUI-Owl is therefore in policy and agent post-training, not perception. That matches the Q1 finding that every strong peer adds agent-trajectory volume and environment data on top of a base the vendor already agent-tuned. Qwen3-VL-2B is at 36.4 AW out of the box.
- Liquid's LoRA guidance (r16, sometimes adapting vision MLPs; prior notes) and the L-Operator recipe (r16, 1 epoch) are both smaller than ours. No LFM-specific evidence exists on whether LoRA capacity binds for agent behaviour.

### Gaps
- No LFM3-VL tech report with GUI-data shares or coordinate conventions was found; the card cites a blog only.
- L-Operator's dataset size, metric definition and creation date are not on the card.
- There is no third-party ScreenSpot reproduction for LFM3-VL-2B.
