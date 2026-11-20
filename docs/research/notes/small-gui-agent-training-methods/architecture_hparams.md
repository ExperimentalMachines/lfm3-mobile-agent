# Architecture, I/O design and training hyperparameters for small (<=3B) mobile GUI agents; small-model AndroidWorld landscape (as of Nov 2026)

Context for the reader: our setup is LFM3-VL-2B, LoRA r64/alpha128, lr 2e-4, 1,250 steps x batch 32 (40k rows), 1 screenshot (~720 image tokens), text history of last 8 steps (intent + action JSON), short intent in `<think>`, JSON action, 0-1000 coords. Results: AndroidControl (AC) step SR 0.715 high / 0.948 low; AndroidWorld (AW) 15/116 (12.9%). Same harness: Qwen3.5-2B same recipe AC 0.734/0.949; GUI-Owl-1.5-2B 23/116 (19.8%) with 1 image.

Comparability warning used throughout: AW numbers below are mostly self-reported by model authors in their own harness (own prompt, own history format, often multiple history screenshots, sometimes pass@3). They are not directly comparable to our 1-screenshot harness. The clearest proof is our own measurement: GUI-Owl-1.5-2B scores 67.9 in its authors' report but 19.8% (23/116) in our 1-image harness.

## 1. Landscape: best published small agents on AndroidWorld and their recipes

### Takeaway
By late 2026 the best end-to-end <=4B agents report 50-70% on AW: GUI-Owl-1.5-2B (67.9), GUI-Owl-1.5-4B (69.8), Step-GUI-4B (63.9 pass@1), UI-Venus-1.5-2B (55.6), MIRAGE-4B (52.6) and MAI-UI-2B (49.1). The plain base Qwen3-VL-2B gets 36.4 and Qwen3-VL-4B gets 45.3. All of the leaders are built on Qwen3-VL and use multi-stage pipelines: large GUI mid-training or SFT (millions of samples, or 10B tokens), then offline and/or online RL in live emulators. All use their own harnesses, which usually include several history screenshots. The older 3B generation (Ferret-UI Lite 28.0, ScaleCUA-3B 23.7) sits near 25-30%. Our 12.9% is low next to the reported numbers, but it is in the same range as GUI-Owl-1.5-2B measured in our own harness (19.8%).

### Cited Findings
**Model-by-model (AW success rate, self-reported unless noted)**
- **GUI-Owl-1.5-2B-Instruct: 67.9 AW** (OSWorld-Verified 43.5, MobileWorld 31.3). **GUI-Owl-1.5-4B-Instruct: 69.8 AW**. 8B-Instruct: 69.0. 8B-Thinking: 71.6. 32B-Instruct: 69.8. — [Mobile-Agent-v3.5 / GUI-Owl-1.5 report, Table 1](https://arxiv.org/abs/2602.16855); 67.9 also on the [HF model card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct)
  - Recipe: built on Qwen3-VL. "Hybrid Data Flywheel" (simulated plus cloud-sandbox environments), unified CoT/thought synthesis, multi-platform environment RL (MRPO). Instruct/thinking variants exist, but the report evaluates only Instruct at 2B/4B. — [arXiv 2602.16855](https://arxiv.org/abs/2602.16855)
  - The HF card's vLLM serving example sets `IMAGE_LIMIT_ARGS='image=5'` (up to 5 images per prompt) and pixel bounds `longest_edge 3072000 / shortest_edge 65536`. This implies the official harness feeds multiple screenshots. — [HF card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct)
- **UI-Venus-1.5-2B: 55.6 AW** (8B 73.7; 30B-A3B 77.6). AndroidLab 36.2 (44.2 human-verified). — [UI-Venus-1.5 report, Table 2-3](https://arxiv.org/abs/2602.09082)
  - Recipe: Qwen3-VL backbone. Four stages: (1) Mid-Training on 10B tokens across 30+ GUI datasets; (2) task-specific Offline-RL (GRPO); (3) Online-RL with full-trajectory rollouts; (4) model merge of grounding, web and mobile specialists. — [arXiv 2602.09082](https://arxiv.org/abs/2602.09082)
  - Stage ablation for 2B, AW: Mid-Training 39.0 → Offline-RL 45.3 → **Online-RL 59.8 (+14.5)** → Model Merge 55.6 (−4.2). For 8B the merge helped (+1.0); for 2B it hurt. — [UI-Venus-1.5, Table 7](https://arxiv.org/abs/2602.09082)
- **MAI-UI-2B: 49.1 AW** (SFT-only 45.1; online RL +4.0). AC-High 67.3, GUI-Odyssey 72.6, ScreenSpot-Pro 57.4. 8B: 70.7. 32B: 73.3. 235B-A22B: 76.7. — [MAI-UI report, Tables 6, 7, 9](https://arxiv.org/abs/2512.22047)
  - Recipe: Qwen3-VL backbone. Four stages: (i) SFT on perception and grounding; (ii) SFT on mobile navigation plus a little grounding; (iii) RL for grounding; (iv) online RL for mobile navigation. The 2B model is also trained as a trajectory monitor for device-cloud handoff. — [arXiv 2512.22047](https://arxiv.org/abs/2512.22047)
  - Harness (per a third-party code reading of the official repo): default `history_n = 3`, i.e. the current screenshot plus 2 previous ones. Previous model replies (thinking + tool call) are re-fed as assistant text. Coordinates are on a 0-999 scale (`SCALE_FACTOR=999`). Output is `<thinking>…</thinking><tool_call>{"name":"mobile_use",…}</tool_call>`, with a NO_THINKING variant. — [cnblogs MAI-UI code reading (secondary)](https://www.cnblogs.com/rossiXYZ/p/19963833)
- **Step-GUI-4B (GELab-Zero-4B): 63.9 AW pass@1, 75.8 pass@3.** Its baseline Qwen3-VL-4B-Instruct gets 45.3. Step-GUI-8B: 67.7 pass@1, 80.2 pass@3. Headline numbers are pass@3, a non-standard metric the authors justify by emulator instability. — [Step-GUI report, Table 4](https://arxiv.org/abs/2512.15431)
  - Recipe: mid-training mixture of ~1.9M general text/multimodal samples, 2M knowledge, 2.7M grounding, 170K action-alignment, 4M trajectories and 420K environment-specific samples. Then cold-start knowledge injection and a self-evolving pipeline with a "Calibrated Step Reward System". — [arXiv 2512.15431](https://arxiv.org/abs/2512.15431)
- **MIRAGE-4B: 52.6 AW** (Qwen3-VL-4B-Instruct base at 42.9 in their harness). MIRAGE-8B: 57.8 (base 47.6). It uses latent instead of explicit reasoning (see Q5). — [MIRAGE, Tables 2-3](https://arxiv.org/abs/2606.04627)
- **Ferret-UI Lite-3B (Apple): 28.0 AW** (mean of 5 runs). AC LL 86.6 / HL 68.9. ScreenSpot-V2 91.6, ScreenSpot-Pro 53.3. In the same harness: Qwen2.5-VL-3B zero-shot 16.8, UI-TARS-1.5-7B 26.4, UI-TARS-1.5-72B 37.7. ScaleCUA-3B is reported at 23.7. — [Ferret-UI Lite, Tables 2-3](https://arxiv.org/abs/2509.26539)
  - Recipe: internal 3B dense model with a VitDet encoder and AnyRes tiling. SFT for 10K steps, then RLVR (GRPO) for 1.5K steps. 17K synthetic trajectories plus long-CoT traces. Zoom-in visual tool use at inference. — [arXiv 2509.26539](https://arxiv.org/abs/2509.26539)
- **Base general VLMs on AW** (as reported by the Qwen3-VL team and quoted by others): Qwen3-VL-2B 36.4; Qwen3-VL-4B-Instruct 45.3; Qwen3-VL-8B 47.6; Qwen3-VL-30B-A3B 54.3. — [MAI-UI Table 6](https://arxiv.org/abs/2512.22047); [UI-Venus-1.5 Table 2](https://arxiv.org/abs/2602.09082); [Step-GUI Table 4](https://arxiv.org/abs/2512.15431)
- **Qwen3.5-2B** (released Mar 2026): the HF model card reports no AW score. Its only GUI number is ScreenSpot-Pro, listed as "--/54.5" (thinking/non-thinking). The model defaults to non-thinking mode. Its LM is a hybrid layout, "6 × (3 × (Gated DeltaNet → FFN) → 1 × (Gated Attention → FFN))". — [HF Qwen3.5-2B card](https://huggingface.co/Qwen/Qwen3.5-2B)

**7B-9B references**
- UI-Venus-7B: 49.1. GUI-Owl-7B: 66.4. UI-TARS-7B: 33.0. UI-TARS-1.5-7B: 30.0. Holo2-8B: 60.4. MobileRL-9B: 80.2. — [MAI-UI Table 6](https://arxiv.org/abs/2512.22047); [UI-Venus-1.5 Table 2](https://arxiv.org/abs/2602.09082); [Step-GUI Table 4](https://arxiv.org/abs/2512.15431)
- Late-2026 larger open agents: OpenMobile-2 reports AW 79.9 — [arXiv 2610.14157](https://arxiv.org/abs/2610.14157). MAI-Gym-9B reports 78.4 on MobileWorld (no AW in its abstract) — [arXiv 2610.20939](https://arxiv.org/abs/2610.20939)

**Grounding-only or offline-only small models (no AW found)**
- UI-TARS-2B: ScreenSpot-V2 84.7, ScreenSpot-Pro 18.9. UI-R1-3B: 89.2/33.5. InfiGUI-R1-3B: SS-Pro 35.7. Jedi-3B: 88.8/37.1. GUI-G1-3B: SS-Pro 38.1. — [Ferret-UI Lite Table 1](https://arxiv.org/abs/2509.26539)
- OS-Atlas-4B: AC LL 80.6 / HL 67.5. — [Ferret-UI Lite Table 2](https://arxiv.org/abs/2509.26539)
- AgentCPM-GUI-8B: AC-High 69.2. — [MAI-UI Table 7](https://arxiv.org/abs/2512.22047)
- SecAgent-3B (Qwen2.5-VL-3B): AC-High step accuracy 69.5. In the same table: UI-R1-3B 45.4, GUI-R1-3B 46.6, Qwen2.5-VL-3B 60.1, Qwen3-VL-4B 47.5. — [SecAgent Table 3](https://arxiv.org/abs/2603.08533)
- OpenPhone-3B (Qwen2.5-VL-3B): AndroidLab 15.2 on-device only (not AW). — [OpenPhone Table 1](https://arxiv.org/abs/2510.22009)
- ShowUI-2B is a grounding/navigation model trained on 256K samples. Its paper reports AITW/Mind2Web/MiniWob, not AW. — [ShowUI](https://arxiv.org/abs/2411.17465)

**Harness disagreements across papers**
- UI-TARS-1.5-7B is listed as 30.0 by MAI-UI and 26.4 (re-evaluated) by Ferret-UI Lite. Ferret-UI Lite lists "UI-TARS-1.5 (7B, reported) 33.0", while MAI-UI attributes 33.0 to UI-TARS-7B. — [MAI-UI Table 6](https://arxiv.org/abs/2512.22047) vs [Ferret-UI Lite Table 3a](https://arxiv.org/abs/2509.26539)
- Qwen3-VL-4B base: 45.3 per Step-GUI, 42.9 in MIRAGE's harness. — [Step-GUI](https://arxiv.org/abs/2512.15431); [MIRAGE](https://arxiv.org/abs/2606.04627)

### Inferences
- **Our harness costs GUI-Owl-1.5-2B about 48 points** (67.9 reported vs 19.8 measured). The likely causes are fewer history screenshots (1 vs up to 5), a different prompt or history format (they re-feed thoughts/conclusions), resolution, and max-step settings. Under our harness, LFM3-2B (12.9%) trails GUI-Owl-1.5-2B by ~7 points, not ~55.
- **AC step accuracy predicts AW poorly at this scale.** Our AC-High 0.715 is already above MAI-UI-2B (67.3) and Ferret-UI Lite (68.9), yet their AW is 49.1 and 28.0. What separates the leaders on AW is online-RL robustness (UI-Venus-2B +14.5; MAI-UI-2B +4.0) and diverse synthetic or online trajectories, not offline step accuracy.
- Every strong <=4B agent starts from Qwen3-VL-2B/4B, which already scores 36-45 on AW before any GUI training. A different base (LFM3-VL) likely starts lower on agentic priors, so mid-training or grounding data may matter more for us than for Qwen-based recipes.

### Gaps
- I did not fetch the official AndroidWorld leaderboard sheet ([google-research/android_world](https://github.com/google-research/android_world)). Leaderboard entries for <=3B models (e.g. whether UI-TARS-2B, ShowUI-2B, Holo1.5-3B or InfiGUI-3B were submitted) are unverified.
- No published AW number was found for UI-TARS-2B, ShowUI-2B, OS-Atlas-4B, InfiGUI-2B/3B, Holo1.5-3B, AgentCPM-GUI, Phi-Ground or Qwen3.5-2B/4B.
- Exact harness details (number of history images, max steps, resolution) for GUI-Owl-1.5 and UI-Venus-1.5 AW evaluations were not confirmed from their code. The GUI-Owl `image=5` limit is a serving cap, not a confirmed eval setting.

## 2. History design: past screenshots vs text-only history; action vs thought history

### Takeaway
At small scale, the biggest jump comes from adding one previous screenshot, together with a semantic text summary of earlier steps. More screenshots give diminishing returns at large token cost. Raw action history (coordinates/JSON) is the weakest text form. Natural-language summaries or re-fed thoughts beat it. Leading harnesses keep 2-4 previous screenshots plus prior reasoning as text (MAI-UI default: 2 previous + current). Our design is 0 previous screenshots plus 8 steps of intent + action JSON. That is closest to the variant SecAgent shows to be clearly worse than one previous screenshot plus a semantic summary.

### Cited Findings
- **SecAgent-3B ablation** (Qwen2.5-VL-3B, offline CMGUI benchmark; N = number of previous screenshot+action pairs):

  | Setting | Step acc. | Task acc. | Input tokens |
  |---|---|---|---|
  | N=0 | 85.3 | 36.2 | 1,537 |
  | N=1 | 94.8 | 72.8 | 2,239 |
  | N=2 | 95.1 | 73.8 | — |
  | N=5 | 95.5 | 74.1 | 3,642 (TTFT doubles, TPS −12.9%) |
  | N=1 w/o semantic context | 90.6 | 56.4 | — |
  | N=1 w/o thought | 94.0 | 68.9 | — |

  — [SecAgent, Table 4](https://arxiv.org/abs/2603.08533)
- SecAgent's argument: raw parameterized actions (e.g. click coordinates) "without their associated screenshots cannot convey meaningful historical progression." Its semantic context is "a concise natural language summary that records key operations (clicked labels, typed inputs, searched outcomes)", updated at each step. — [SecAgent](https://arxiv.org/abs/2603.08533)
- **OpenPhone-3B** (AndroidLab online): removing history drops success from 15.2% to 4.3%. Its history is a text summary that compresses each step's state. — [OpenPhone, Table 2](https://arxiv.org/abs/2510.22009)
- **MAI-UI harness**: `history_n=3` (current + 2 previous screenshots), with previous model responses re-fed as assistant text. — [cnblogs code reading (secondary)](https://www.cnblogs.com/rossiXYZ/p/19963833). MAI-UI formalizes the policy as a_t = π(I, o_t, h_t), where h_t contains past actions and observations. — [MAI-UI](https://arxiv.org/abs/2512.22047)
- **GUI-Owl-1.5**: removing "unified CoT synthesis" drops AW from 71.6 to 65.0 at 8B-Thinking. That synthesis equips each trajectory step with "observation, memory, reflection, and progress tracking", i.e. thought/memory history rather than raw actions. — [GUI-Owl-1.5, Table 10](https://arxiv.org/abs/2602.16855)
- **CausalCache**: on OSWorld-Verified, activating historical screenshots improves success by about 13 points over summary-only memory. On MobileWorld (zero-shot), Recent-4 screenshots gets 30.2%; smarter selection of which past screenshots to show gets 36.8%, with the gain concentrated in cross-app memory tasks (+11.2) and none on single-app tasks. — [CausalCache abstract](https://arxiv.org/abs/2608.22577)
- **ECHOES**: recursively compressed text history, trained with a multi-image privileged teacher via on-policy distillation, "achieves competitive performance" without keeping history screenshots at deployment. — [ECHOES abstract](https://arxiv.org/abs/2610.22408)
- **HiconAgent-3B**: dropping history observations while keeping history actions as "anchors" gives up to 2.47x speedup and 60% fewer FLOPs, with results comparable on AndroidControl/AITW. — [HiconAgent abstract](https://arxiv.org/abs/2512.01763)
- **PAL-UI-3B**: dual-level summaries plus a tool to retrieve specific past screenshots on demand outperforms truncate-or-summarize baselines in mobile navigation. — [PAL-UI abstract](https://arxiv.org/abs/2510.00413)
- **Re-encoding cost**: when the same screenshot is re-fed across steps, its ViT embeddings can be cached and reused, cutting FLOPs without hurting accuracy. — [Where and How to Prune](https://arxiv.org/abs/2603.26041)

### Inferences
- The cheapest likely AW gain is adding one previous screenshot (N=1). In SecAgent it nearly doubled task accuracy, for ~45% more input tokens. ViT caching makes the extra image nearly free on the encoder side; the cost is in LM prefill.
- Our "intent + action JSON" history sits between raw actions and a semantic summary. Upgrading it to an outcome-aware summary (what was typed or found, which screen was reached), as SecAgent and OpenPhone do, is the evidence-backed text-side change.
- AW has many cross-app and memory tasks (e.g. reading a value in one app and entering it in another). CausalCache's split suggests text-only history hurts most on exactly those tasks.

### Gaps
- No paper found ablates the number of history screenshots directly on AndroidWorld at <=3B. SecAgent is offline Chinese apps; OpenPhone is AndroidLab; CausalCache is OSWorld/MobileWorld.
- I found no direct comparison of an 8-step vs a 3-step text history at small scale.

## 3. Action space and coordinate format

### Takeaway
The field has converged on point (not box) outputs in a fixed normalized range: 0-1000 or 0-999 relative coordinates, which is also Qwen3-VL's native convention. Our 0-1000 points are aligned with this. Evidence favours plain-text digits with a standard next-token loss over special coordinate tokens or loss tricks. The common small-agent action spaces include `answer`, `terminate`/`status`, `system_button`, `wait`, `long_press`, `drag` and `swipe`. MAI-UI adds `ask_user`/`mcp_call`, and SecAgent converts grounding boxes to center points so grounding data shares the navigation action format.

### Cited Findings
- **Phi-Ground ablations**:
  - It chose relative coordinates scaled by 1000 "because their value range is fixed and relatively dense".
  - Special-token coordinates (1000 bins per axis) led to "model collapse and poor performance".
  - Label smoothing and digit-place loss reweighting helped only with small data or batch sizes and gave no gain at batch 2048 with millions of samples.
  - Point output gave the best click accuracy (ScreenSpot-V2 85.5) vs XYXY 84.7, XYWH 84.2, MidWH 85.0. Boxes only help if IoU is needed.
  - Putting the text instruction before the image improved ScreenSpot-V2-mobile by 1.7-2.4 points and SS-Pro by 2.9-4.1 points, because causal attention makes image tokens instruction-aware.

  — [Phi-Ground, §2, §5.1, Tables 2-3](https://arxiv.org/abs/2507.23779)
- MAI-UI uses relative coordinates (0-999 in code). It notes that "leveraging the relative coordinate mechanism of Qwen3-VL" is what allowed lowering the input to 720p without loss. — [MAI-UI §3.5](https://arxiv.org/abs/2512.22047); [code reading](https://www.cnblogs.com/rossiXYZ/p/19963833)
- MAI-UI action space: click(x,y), long_press, type, swipe (direction + optional coords), drag, system_button (back/home/menu/enter), wait, terminate (success/fail), answer, ask_user, mcp_call. There is no explicit `open_app` in its Table 1. — [MAI-UI Table 1](https://arxiv.org/abs/2512.22047)
- UI-Venus-1.5 extends the UI-Venus-1.0 mobile action space with Hover, DoubleClick and Hotkey for web. — [UI-Venus-1.5](https://arxiv.org/abs/2602.09082)
- SecAgent converts grounding bounding boxes to center-point click targets during SFT. The aim is to "unify the action space, facilitating better knowledge transfer" between grounding and navigation data. — [SecAgent §4.3](https://arxiv.org/abs/2603.08533)
- The AndroidWorld-style JSON action prompt (as used by Aguvis's AW planner) includes `{"action_type":"status","goal_status":"complete"|"infeasible"}` and `{"action_type":"answer","text":...}`. — [Aguvis Appendix, Table 13](https://arxiv.org/abs/2412.04454)
- Grounding RL rewards: MAI-UI uses point-in-box and reports that dense rewards perform similarly. Ferret-UI Lite found dense grounding rewards beat sparse ones for navigation RL, and that an action-type-only reward hurts. — [MAI-UI §2.2.2](https://arxiv.org/abs/2512.22047); [Ferret-UI Lite Fig. 7b](https://arxiv.org/abs/2509.26539)

### Inferences
- No change to the coordinate format is indicated. If our prompt places the image before the instruction, moving the goal and history text ahead of the image is a cheap change that Phi-Ground measured as a gain. This is worth checking against how LFM3-VL's chat template orders modalities.
- An explicit `answer` action and a `status`/`terminate` with infeasible are standard and needed for AW's information-retrieval tasks. Converting grounding boxes to center points keeps grounding data in the agent action format.

### Gaps
- I did not verify in this pass whether AndroidWorld's reference action space includes `open_app`, or any measured AW effect of having `open_app` vs navigating via the launcher.
- No small-model AW ablation of 0-1000 vs absolute-pixel coordinates was found; the evidence is grounding-only (Phi-Ground) or anecdotal (MAI-UI).

## 4. Image resolution / visual-token budget vs accuracy

### Takeaway
For phone screens, accuracy is flat above roughly the "720p" level but drops at "540p". MAI-UI found 720p equal to 1080p (with ~50% faster RL steps), while 540p "substantially degrades" performance. Phi-Ground finds visual tokens are a bottleneck only for high-resolution, small-target benchmarks, with diminishing returns above ~2,000 tokens, and little effect on ScreenSpot-V2-type mobile grounding. Our ~720 tokens is likely between MAI-UI's degraded 540p and adequate 720p regimes (inference below).

### Cited Findings
- MAI-UI: "720p resolution achieves performance comparable to 1080p while providing a ~50.1% speedup per step. Conversely, 540p resolution… substantially degrades model performance due to insufficient detail for fine-grained UI element perception." — [MAI-UI §3.5](https://arxiv.org/abs/2512.22047)
- Phi-Ground (fixed training budget, 6 models): "when the number of image tokens is low, it may become a bottleneck… When the number of image tokens exceeds 2000, their impact gradually diminishes". On ScreenSpot-V2, "neither the model size nor the number of image tokens significantly affects performance". — [Phi-Ground §5.5](https://arxiv.org/abs/2507.23779)
- Ferret-UI Lite and MAI-UI both use inference-time zoom-in (crop around a first prediction and re-predict) to get high-resolution detail at small scale. MAI-UI-2B ScreenSpot-Pro rises from 57.4 to 62.8 with zoom-in. — [MAI-UI Table 2](https://arxiv.org/abs/2512.22047); [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- Ferret-UI Lite: synthetic high-resolution grounding data helps mainly on ScreenSpot-Pro, only modestly on ScreenSpot-V2. — [Ferret-UI Lite Fig. 6c](https://arxiv.org/abs/2509.26539)
- ShowUI-2B: UI-guided visual token selection removes 33% of redundant visual tokens during training, with a 1.4x speedup. — [ShowUI](https://arxiv.org/abs/2411.17465)
- Token pruning study: keep a balance of foreground/background tokens and spatial uniformity when pruning for GUI navigation. — [Where and How to Prune](https://arxiv.org/abs/2603.26041)

### Inferences
- **Token arithmetic (assumptions flagged):** assume an AW emulator screen of 1080x2400 and Qwen3-VL's 32x32 px per visual token (patch 16, 2x2 merge). Then 1080p ≈ 2,500 tokens, "720p" (720x1600) ≈ 1,125 tokens and "540p" (540x1200) ≈ 630 tokens. Our ~720 tokens is closer to the degraded 540p point than to the safe 720p point. Raising to ~1,000-1,200 tokens is a plausible grounding gain, especially for small icons and keyboard keys.
- Mobile grounding (ScreenSpot-V2-like) saturates early, so resolution likely matters less than history and RL for AW. A 720 → ~1,100-token test is cheap and should be checked against per-step click accuracy on our AC/AW failure cases.

### Gaps
- No direct AW-success-vs-tokens curve for a <=3B model was found. The MAI-UI resolution ablation does not state the model size (it appears in the 8B RL analysis) or give the 540p number.
- The pixel-to-token mapping for LFM3-VL's NaFlex encoder was not verified, so the comparison to Qwen3-VL token counts is approximate.

## 5. Thinking: explicit reasoning vs direct action for small models

### Takeaway
For small agents, training with reasoning or thought supervision consistently beats action-only SFT, often by large margins. At 4B on AW, action-only SFT (31.0) underperformed the untuned base (42.9), while explicit-CoT SFT reached 52.6. However, requiring reasoning from a weak model can hurt, and general CoT can degrade pure grounding. Latent reasoning (MIRAGE) matches explicit CoT with 3-5x fewer decoded tokens. Our short "intent in `<think>`" sits between Aguvis-style inner monologue and no-CoT. The evidence suggests richer structured thoughts (observation / progress / rationale / expected outcome) would help.

### Cited Findings
- **MIRAGE (Qwen3-VL-4B, AW SR):**

  | Variant | AW SR |
  |---|---|
  | Base model | 42.9 |
  | Action-only SFT | 31.0 |
  | Explicit CoT SFT | 52.6 |
  | Latent CoT, serial | 50.9 |
  | MIRAGE-4B (latent + world model) | 52.6 |

  Average decoded tokens fall from 103 to 31 at 4B. The latent-slot budget matters: 3 slots gives 32.8 vs 52.6 with 9. — [MIRAGE, Tables 2-4](https://arxiv.org/abs/2606.04627)
- **Ferret-UI Lite-3B (AW SFT ablation):** baseline without CoT 13.7 → +short CoT 15.8 → +long CoT 19.6 → +17K synthetic trajectories 25.2 → +RL 28.0. — [Ferret-UI Lite, Table 4](https://arxiv.org/abs/2509.26539)
- **OpenPhone-3B (AndroidLab):** "w/o Reasoning" (direct actions) drops from 15.2 to 8.7. However, prompting GPT-5-nano to reason dropped it from 18.1 to 2.9, while Gemini-2.5-Flash rose from 22.5 to 36.2. The authors conclude reasoning helps only above a capability threshold. — [OpenPhone, Tables 1-2](https://arxiv.org/abs/2510.22009)
- **SecAgent-3B (offline):** removing thought gives task accuracy 72.8 → 68.9 and step accuracy 94.8 → 94.0. — [SecAgent Table 4](https://arxiv.org/abs/2603.08533)
- **Aguvis-7B:** removing inner monologue drops AC-Low from 80.5 to 69.1 and ScreenSpot from 84.4 to 79.3. The authors attribute part of the gain to "low-level instructions of inner monologue act as atomic instruction and grounding action pairs". Enforced planning "resolves approximately 20% of grounding errors". — [Aguvis §4.2, Table 6, App. E](https://arxiv.org/abs/2412.04454)
- **GUI-Owl-1.5:**
  - 8B-Thinking vs 8B-Instruct on AW: 71.6 vs 69.0. At 32B: 69.8 vs 69.8.
  - Thinking hurts some grounding: OSWorld-G 55.0 (8B-Thinking) vs 65.8 (8B-Instruct).
  - At 2B/4B only Instruct variants are reported.

  — [GUI-Owl-1.5 Tables 1, 4](https://arxiv.org/abs/2602.16855)
- **MAI-UI:** "Prior studies find that general chain-of-thought reasoning can often degrade grounding performance". It instead uses "instruction-as-reasoning" (restating the target from appearance, function, location or intent) for grounding, and `<thinking>` for navigation. — [MAI-UI §3.6](https://arxiv.org/abs/2512.22047)

### Inferences
- Keep thoughts at train and inference time. Our current thought is a short intent, roughly Aguvis's low-level-instruction monologue, which already helps grounding. The evidence (Ferret-UI Lite long > short CoT; GUI-Owl-1.5 observation/memory/reflection/progress synthesis; SecAgent semantic context) points to adding progress tracking and screen observation fields. Synthesizing these with a teacher is the main cost.
- Latency: thoughts of ~100 tokens per step at 2B are cheap compared with prefill of 700-2,000 image tokens. If latency becomes binding, MIRAGE-style latent reasoning is the published route that keeps accuracy.
- MIRAGE's "action-only SFT < base" result is a warning: if a training mix includes many action-only rows (e.g. converted AC data without thoughts), it could pull AW down even while AC step accuracy rises.

### Gaps
- No ablation at <=2B on AW compares short-intent vs long structured CoT directly. Ferret-UI Lite (3B) is the closest.
- No small-model evidence was found on Qwen3.5-style hybrid-attention models' thinking vs non-thinking behaviour for GUI.

## 6. Hyperparameters: LoRA vs full FT, modules to tune, LR, batch, epochs, data scale, forgetting

### Takeaway
Little GUI-specific evidence exists on LoRA vs full fine-tuning at 2-3B. The top small agents (MAI-UI, UI-Venus, GUI-Owl, Step-GUI) do large-scale full-model training; their reports do not ablate LoRA. SecAgent-3B used LoRA for SFT and full-parameter tuning for RL and matched 7-8B models offline. General LoRA evidence:
- LoRA matches full fine-tuning on small-to-medium SFT sets only if applied to all layers including MLPs.
- The best LoRA learning rate is about 10x the full-fine-tuning rate.
- LoRA tolerates large batches worse than full fine-tuning.

On data scale, AndroidControl's LoRA study shows in-domain accuracy grows log-linearly with episodes, but the in-domain vs out-of-domain gap widens as data and LoRA rank grow. Our 40k rows (~1.3 epochs at 1,250 x 32) is tiny next to the multi-million-sample mid-training of the leaders.

### Cited Findings
- **SecAgent-3B:** "We adopt LoRA tuning for the SFT stage, and full-parameter tuning for the RFT stage" (Qwen2.5-VL-3B). It reaches AC-High 69.5 step accuracy, above AgentCPM-GUI-8B in its table. — [SecAgent §5.1, Table 3](https://arxiv.org/abs/2603.08533)
- **Thinking Machines, "LoRA Without Regret":**
  - LoRA equals full fine-tuning on small/medium SFT datasets and underperforms once the data exceeds adapter capacity.
  - Attention-only LoRA "significantly underperforms" MLP-only. Apply LoRA to all layers.
  - Optimal LoRA LR ≈ 10x (fitted 9.8x) the full-fine-tuning LR, and changes less than 2x between rank 4 and 512.
  - "LoRA is less tolerant of large batches than full fine-tuning", independent of rank.
  - In RL, LoRA matches full fine-tuning even at rank 1.

  — [Thinking Machines blog](https://thinkingmachines.ai/blog/lora/)
- **AndroidControl (PaLM-2S, LoRA):**
  - In-domain step accuracy grows log-linearly with episodes: high-level 30.3 (5 episodes) → 52.5 (1k) → 62.0 (10k) → 65.6 (all 13.6k) at r=4; 71.5 at r=64.
  - Extrapolated: 95% in-domain step accuracy needs ~500K (low-level) / 1M (high-level) episodes; out-of-domain needs ~10M / 60M.
  - The in-domain vs out-of-domain gap widens with data and rank: high-level gap −6.8 (r4, all) vs −12.3 (r64, all).
  - Episode accuracy collapses with length: 21.3% at 5 steps vs 7.6% at 6 steps, despite 64-71% step accuracy.

  — [AndroidControl, Tables 4-5, Fig. 5, App. E.4](https://arxiv.org/abs/2406.03679)
- **Ferret-UI Lite:** SFT 10K steps then RL 1.5K steps. RLVR improved AW at every SFT length tested (2K, 6K, 10K), "most pronounced when the number of SFT steps is smaller". A balanced grounding:navigation data ratio gave the best overall results, and grounding data did not degrade navigation. — [Ferret-UI Lite §4, Fig. 6b, 7a](https://arxiv.org/abs/2509.26539)
- **OpenPhone-3B GRPO:** larger batches (150-160) stabilized GRPO; small batches (24-32) gave oscillating rewards and lower success. SFT-free GRPO learned more slowly. — [OpenPhone §3.3](https://arxiv.org/abs/2510.22009)
- **Phi-Ground grounding SFT:** batch sizes up to 8K with tens of millions of samples, and 40M-sample training mixtures. — [Phi-Ground §5.5](https://arxiv.org/abs/2507.23779)
- **Vision tower (adjacent evidence, not GUI):** in a π0 VLA LoRA study, performance saturated at r=32. "Freezing the VLM or restricting the vision encoder to LoRA significantly degrades performance"; full vision-encoder fine-tuning plus LoRA r=32 matched full fine-tuning. — [arXiv 2607.10172](https://arxiv.org/abs/2607.10172). Contrast: on general multimodal benchmarks, existing visual fine-tuning methods "fail to consistently outperform the frozen baseline". — [CoVFT](https://arxiv.org/abs/2603.21077)
- **Forgetting / general capability:**
  - Step-GUI's mid-training mixes ~1.9M general text/multimodal and 2M knowledge samples to "retain and consolidate broad knowledge" alongside agent data. — [Step-GUI §2.1.1](https://arxiv.org/abs/2512.15431)
  - UI-Venus-1.5's model merge traded ~1.4 points of ScreenSpot-Pro for unification, and cost the 2B model 4.2 AW points. — [UI-Venus-1.5 Table 7](https://arxiv.org/abs/2602.09082)

### Inferences
- **Our LR 2e-4 with r64/alpha128 is in the normal LoRA range**: about 10x a typical 1-2e-5 full-fine-tuning LR. Batch 32 is small, which suits LoRA's large-batch sensitivity. More important are (a) adapter coverage of all linear layers, including MLP and LFM's conv-block projections, and (b) whether the projector and vision tower are trainable. The VLA evidence suggests vision plasticity matters for new visual domains, but GUI-specific confirmation is missing.
- **40k rows is likely the binding constraint, not LoRA vs full.** By AndroidControl's log-linear trend, AC-style data alone keeps lifting in-domain AC while out-of-domain/online gains lag. The ~3-point AC-High gap between LFM3 (0.715) and Qwen3.5-2B (0.734) under the same recipe suggests the base model, not the adapter, is limiting.
- RL is the step most consistently tied to AW gains at 2-3B (+3 to +14.5). Per Thinking Machines, LoRA (even low rank) is sufficient for the RL stage, so it can follow without switching to full fine-tuning.

### Gaps
- No GUI-agent paper found compares LoRA vs full fine-tuning, or frozen vs tuned vision tower, at <=3B on AW.
- No small-agent paper found reports epochs/LR/batch sweeps for navigation SFT (most report only steps).
- Catastrophic forgetting of general VLM skills after GUI SFT at 2B is not quantified in the sources I read.

## 7. Multi-stage curricula (grounding → planning → agent; mid-training; RL)

### Takeaway
Every leading small agent uses at least 3 stages:
1. A broad GUI knowledge/grounding stage (mid-training at millions of samples or 10B tokens).
2. Agentic SFT on trajectories with thoughts.
3. RL — offline step-level GRPO and/or online multi-turn RL in emulators. Online RL gives the largest AW jumps at 2B.

Aguvis shows that staging grounding before planning beats both joint training and skipping a stage. Skipping the planning/reasoning stage hurts most.

### Cited Findings
- **Aguvis-7B stage ablation** (AC-High / AC-Low / ScreenSpot): full Stage1→2: 61.5 / 80.5 / 84.4; joint Stage1+2: 59.2 / 80.9 / 85.0; w/o Stage 2: 58.0 / 75.6 / 81.8; w/o Stage 1: 58.8 / 79.8 / 77.4. Joint training biases toward grounding because grounding data is more abundant, so planning-heavy data should come later. — [Aguvis Tables 6, 14](https://arxiv.org/abs/2412.04454)
- **MAI-UI (2B-235B):** SFT perception/grounding → SFT navigation + some grounding → grounding RL → online navigation RL. 2B: 45.1 → 49.1 AW from online RL. Enhanced GRPO (curriculum, repetition penalty, experience replay) gave +6.0 vs +1.8 for vanilla GRPO at 8B. A longer environment-step budget helped (15 → 50 steps: +1.7 → +6.0). Scaling parallel envs 32 → 512 took 8B from 65.5 to 70.7. — [MAI-UI §3.1, §3.5](https://arxiv.org/abs/2512.22047)
- **UI-Venus-1.5:** Mid-Training (10B tokens, 30+ datasets) → Offline-RL → Online-RL → Merge. 2B AW: 39.0 → 45.3 → 59.8 → 55.6. Mid-training is motivated by "sparse reward signals" in RL when the base lacks GUI structure. — [UI-Venus-1.5 §2.1, Table 7](https://arxiv.org/abs/2602.09082)
- **Step-GUI:** mid-train (~11M mixed samples incl. 4M trajectories) → cold-start knowledge injection → self-evolving data loop with calibrated step rewards. Step-GUI-4B reaches 63.9 AW pass@1. — [Step-GUI §2](https://arxiv.org/abs/2512.15431)
- **GUI-Owl-1.5:** data flywheel (virtual and sandbox environments) → unified thought synthesis → multi-platform RL (MRPO). Removing virtual-environment trajectories drops in-house Mobile-Eval from 86.7 to 50.0. — [GUI-Owl-1.5 Table 11](https://arxiv.org/abs/2602.16855)
- **Ferret-UI Lite-3B:** single SFT stage over a balanced grounding+navigation mix (real + 17K synthetic trajectories with long CoT), then RLVR with action-type plus dense-grounding rewards. AW: 25 → 28 from RL. — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539)
- **SecAgent-3B:** SFT (grounding converted to navigation format + navigation) → RFT with GRPO (format reward 0.5 + action reward 1). On out-of-domain apps, SFT+RFT beat SFT alone, e.g. Baidu Maps task accuracy 41.7 → 62.5 when those apps were held out. — [SecAgent §4.3, Table 5](https://arxiv.org/abs/2603.08533)
- **OpenPhone-3B:** SFT then GRPO. w/o GRPO 7.2, w/o SFT 8.7, full 15.2 (AndroidLab). — [OpenPhone Table 2](https://arxiv.org/abs/2510.22009)
- **MIRAGE:** two-stage — explicit-thought warmup (1 epoch), then latent-CoT stage with LR reset. — [MIRAGE §3.4](https://arxiv.org/abs/2606.04627)

### Inferences
- Our pipeline is a single SFT stage of 40k rows. Against the published evidence, the two missing pieces most tied to AW are:
  1. A GUI grounding/perception stage (or mixed-in grounding data converted to point actions), which Aguvis and Ferret-UI Lite show helps.
  2. Some form of RL, at minimum offline step-level GRPO on AC-style data with point-in-box + action-type rewards, which is cheap and gave +3 to +6 points at 2-3B. Online AW-like RL gave up to +14.5 but needs parallel emulators.
- Model merging of specialist checkpoints hurt the 2B model in UI-Venus-1.5. Avoid it at our scale unless measured.

### Gaps
- No published curriculum at <=2B on a non-Qwen base (e.g. LFM) was found, so transfer of these stage gains to LFM3-VL is unverified.
- No public AW ablation of offline-only GRPO (no emulator) for a 2B model was found. UI-Venus's Offline-RL stage (+6.3 at 2B) is the closest, but it follows a 10B-token mid-training stage.
