# Input design, output format, inference and harness choices that move AndroidWorld (AW) success for small screenshot-only agents

Scope note: the notes cover what the earlier report (`/Users/alpha/lfm3-android/reports/Small GUI agent training methods.md`) did not, plus three corrections to it (marked **CORRECTION**). Numbers the earlier report already cites (SecAgent N=0→1 history 36.2→72.8, OpenPhone 15.2→4.3, Phi-Ground text-first +1.7 to +2.4, MAI-UI 720p≈1080p, VLAA-GUI loop breaker) are repeated only where they are needed for a table. "[cross-harness]" marks any number compared across evaluation setups. "Own harness" means the authors' own evaluation code. SR means success rate.

## Q1. History design: how many past screenshots, what text history, and outcome annotations

### Takeaway
Going from 1 to 2 screenshots in context brings the largest single gain measured anywhere, and returns flatten by about 4–8 images. Keeping the agent's own past reasoning text matters about as much as the extra image. Explicit outcome or state tracking helps most when visual history is short. GUI-Owl-1.5's official AW harness keeps the **last 5 screenshots plus its own past responses**, while our "matched" GUI-Owl run gave it **1 screenshot**. That one setting is a large, plausibly dominant, part of the 67.9 → 19.8 gap.

### Cited Findings

| Setting (model, benchmark) | Before → after | Source |
|---|---|---|
| Retained screenshots 1 → 2 (Qwen3.7-Plus, frontier API; GMA mobile benchmark, 300 tasks; prior thoughts kept) | SR 43.33 → 49.33; avg 57.20 → 63.78 | [GMA](https://arxiv.org/abs/2608.27477) |
| Screenshots 2 → 4 → 8 → 16 (same setup) | SR 49.33 → 51.00 → 52.00 → 52.00 (avg 65.53 → 67.10 → 65.52) | [GMA](https://arxiv.org/abs/2608.27477) |
| Drop previous thoughts at 2 images (same setup) | SR 49.33 → 41.67; compositional avg 69.78 → 57.13 | [GMA](https://arxiv.org/abs/2608.27477) |
| Replace evicted older screenshots with text captions (2 images) | SR 49.33 → 51.33; "realistic" tier avg 11.00 → 34.60 | [GMA](https://arxiv.org/abs/2608.27477) |
| Explicit structured state tracking (TSR-style task requirements, sub-goal progress, execution state), 1 image | SR 43.33 → 53.67; gain shrinks as images grow (avg nearly flat at 8 images: 67.10 → 66.95) | [GMA](https://arxiv.org/abs/2608.27477) |
| Structured vs free-form state, Qwen3.7-Plus | none 49.33 / free-form 50.33 / structured 54.33 SR; GPT-5.6 prefers free-form (65.67) over structured (64.00) | [GMA](https://arxiv.org/abs/2608.27477) |
| Task-State Representation wrapper (training-free; instruction summary + progress tracker + pre/post-action visual comparison) | "up to 12 absolute points" on complex cross-app and memory tasks across 4 mobile benchmarks | [TSR](https://arxiv.org/abs/2607.00502) |
| Historical screenshots vs summary-only memory (desktop, OSWorld-Verified) | ≈ +13 points SR from activating historical screenshots; MobileWorld zero-shot, CausalCache 36.8 vs Recent-4 30.2 | [CausalCache](https://arxiv.org/abs/2608.22577) |
| 5 history screenshots with redundant patches removed (Qwen2.5-VL-7B; OSWorld, WebTailBench, AgentNetBench) | −46% tokens, +3% SR vs no-drop baseline; "performance continues to improve as more past observations are incorporated when redundancy is removed" | [ReVision](https://arxiv.org/abs/2605.11212) |
| Step-level reflection summary used as history (M3A vs M3A-Simple, GPT-4 Turbo, AW a11y tree) | 19.8 → 30.6 (also adds guidelines, so not history alone) | [AndroidWorld](https://arxiv.org/abs/2405.14573) |
| Error summary passed when switching to the cloud model (MAI-UI-2B local + 32B cloud, AW) | +6.9 SR vs no error summary | [MAI-UI](https://arxiv.org/abs/2512.22047) |
| Training thoughts that carry observation, memory, reflection and progress ("unified CoT synthesis"; GUI-Owl-1.5-8B-Thinking, AW) | 65.0 → 71.6 | [Mobile-Agent-v3.5](https://arxiv.org/abs/2602.16855) |

- GUI-Owl-1.5's official AW agent defaults to `last_image=5`. It runs a multi-turn chat that keeps the model's own previous replies. Turns older than the image window lose their screenshot and become `Previous actions:\nStep{j}: <Action sentence>`. The goal and history text come **before** the image in the user turn — [gui_owl.py @ c4cd0a8](https://github.com/X-PLUG/MobileAgent/blob/c4cd0a8f9ddedad24dd8a3daf3a56ca69343849f/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py).
- UI-TARS limits input to "the last N observations", while "the full history of previous actions and thoughts is retained as short-term memory" — [UI-TARS](https://arxiv.org/abs/2501.12326). (The passage read here does not state the value of N.)
- Our GUI-Owl comparison ran the "matched" configuration: "K=1 image at <= max_pixels (compute-matched to our ~1k-token prompt)". "Native" is "K=5 images at full resolution (their deployment; ~2.5k image tokens each)" — [guiowl_agent.py](../../../../eval/androidworld/guiowl_agent.py). The matched run averaged 2,261 prompt tokens and 7.9 s/step on 116 episodes. The 2-episode native smoke run averaged 10,707 prompt tokens and 61.1 s/step (2/2 easy tasks solved) — [matched summary](../../../../results/androidworld/guiowl15_2b_matched.summary.json), [native sample](../../../../results/androidworld/guiowl15_2b_native_sample.summary.json).
- A 4B world-model study found that "for overconfident mobile agents with low action entropy, posterior self-reflection provides limited gains". World models were "more effective as prior perception or training supervision than as universal post-hoc verifiers" — [How Mobile World Model Guides GUI Agents](https://arxiv.org/abs/2605.10347).

### Inferences
- GMA's 1→2 image gain (+6 SR) and its thought-removal loss (−7.7 SR) were measured on a frontier API model, not at 2B. Their direction agrees with SecAgent-3B (offline) and OpenPhone-3B from the earlier report. Read together, the 2B evidence and the frontier evidence point the same way: the first extra screenshot plus the agent's own reasoning history are the two cheapest history wins, and past ~4–8 images gains plateau.
- State tracking and outcome notes help most when visual history is short. That is our current regime: 1 image, a text history of (intent, action JSON) pairs, and no outcomes. This supports the earlier plan to *train* outcome notes into the history. The earlier finding that a runtime-only "[no visible change]" note does not help is consistent with GMA's model-specific result: a harness mechanism helps a model only if that model knows how to use it.
- For the GUI-Owl fairness question, the 5→1 image cut removes exactly the input that GUI-Owl's RL-trained policy expects, so the matched run likely understates GUI-Owl by more than any other single setting (see Q6).

### Gaps
- No paper found that ablates the number of history screenshots *on AW* at ≤4B with matched training. GMA uses a frontier model on a different benchmark, and SecAgent is offline.
- No measured comparison of history formats ("intents only" vs "actions only" vs "intent+action" vs "summary") at ≤4B on AW was found.

## Q2. Resolution, visual token budget and prompt order

### Takeaway
Mobile screenshots are much less resolution-hungry than desktop or pro screens. Grounding gains from more crops or tokens are ~0 on ScreenSpot-v2-Mobile and large only on ScreenSpot-Pro. 720p is reported to match 1080p, and 540p degrades. Training-free token pruning keeps 94–99% of accuracy at 30–70% fewer tokens. Our ~0.77M-pixel image sits just above the degrading 540p-equivalent (~0.65M). The evidence favours a current image near 720p-equivalent (~1.15M) plus cheaper, lower-resolution history images, rather than ever-higher resolution for one image. Text-before-image is a small, consistent training-time win, and GUI-Owl's own harness already uses it.

### Cited Findings

| Setting | Before → after | Source |
|---|---|---|
| max_crops 6 → 15 (Phi-Ground, image-first input; grounding) | SSv2-Mobile 85.1 → 85.4; SS-Pro 14.6 → 27.7 | [Phi-Ground](https://arxiv.org/abs/2507.23779) |
| max_crops 6 → 15 (text-first) | SSv2-Mobile 87.5 → 87.1; SS-Pro 18.7 → 30.6 | [Phi-Ground](https://arxiv.org/abs/2507.23779) |
| Text before image vs image before text (trained each way) | SSv2-Mobile +2.4 (6 crops), +1.7 (15 crops); SS-Pro +4.1 / +2.9 | [Phi-Ground](https://arxiv.org/abs/2507.23779) |
| Input resolution during online RL (MAI-UI, Qwen3-VL base, relative coordinates) | 720p "comparable to 1080p" with ~50.1% speed-up per step; 540p "substantially degrades" | [MAI-UI](https://arxiv.org/abs/2512.22047) |
| Temporal-adaptive resolution plus structure-aware pruning (training-free, Qwen2-VL-2B, GUI navigation) | 3.4× fewer FLOPs, 3.3× faster vision encoding, >94% of original performance retained | [GUIPruner](https://arxiv.org/abs/2602.23235) |
| Adaptive quadtree token merging (GUI-Owl-1.5-32B-Instruct) | −29.52% visual tokens, +13.22% speed, 99.06% of full-token performance | [AQuaUI](https://arxiv.org/abs/2605.19260) |
| Caching ViT embeddings of history screenshots across steps | "substantially reducing FLOPs while preserving model performance" | [Where and How to Prune](https://arxiv.org/abs/2603.26041) |
| Zoom-in, a second-pass crop (GUI-Owl-1.5-2B-Instruct, ScreenSpot-Pro) | 57.8 → 70.4 | [Mobile-Agent-v3.5](https://arxiv.org/abs/2602.16855) |
| Zoom-in (MAI-UI-2B, OSWorld-G) | 52.0 → 55.9 | [MAI-UI](https://arxiv.org/abs/2512.22047) |

- ClawGUI-Eval reproduced 46/48 published grounding numbers within 2 points. The two failures were Qwen3-VL-2B on SS-Pro (official 48.5, reproduced 43.90) and UI-TARS-1.5-7B (49.6 vs 42.06). The authors attribute them to "undisclosed prompt or resolution choices" — [ClawGUI](https://arxiv.org/abs/2604.11784).
- Even GUI-Owl-1.5's official mobile code is ambiguous about resizing. A GitHub issue reports `smart_resize(factor=28, max_pixels=10035200)` for image encoding and `factor=16` for coordinate rescaling, and asks whether Qwen3-VL needs factor 32 — [MobileAgent issue #285](https://github.com/x-plug/mobileagent/issues/285).

### Inferences
- Our budget of ~774K pixels (~590×1310) falls between MAI-UI's two settings, assuming "540p/720p" names the short side of a 1080×2400 portrait screen. 540p is then ≈540×1200 = 0.65M pixels ("substantially degrades") and 720p ≈720×1600 = 1.15M pixels ("comparable to 1080p"). We sit just above the degrading setting. MAI-UI gives no exact pixel counts, so this placement is approximate. ScreenSpot-v2-Mobile suggests that resolution beyond a moderate level buys little on phones, but our budget may be below that level. The earlier plan's ~1.1–1.15M-pixel budget (≈720p) for the current image, with history images at lower resolution plus ViT caching (GUIPruner-style decaying resolution), is the evidence-backed split.
- The text-first gain is a *training-time* effect: Phi-Ground trained each order separately. Flipping the order at inference on a model trained image-first should not be expected to help, and could hurt.

### Gaps
- No ≤4B resolution ablation with AW success numbers was found. MAI-UI reports qualitative ("comparable", "substantially degrades") rather than numeric AW deltas.
- No measurement was found of how much the vision projector (mmproj) precision or llama.cpp's image preprocessing shift accuracy.

## Q3. Action space and coordinate format: 0–1000 vs pixels, point vs bbox, open_app, answer design

### Takeaway
Output-format choices are second-order once a model is trained on them. Point and bbox formats differ by ≤1.3 points of click accuracy, and relative ×1000 coordinates are the convention of choice: GUI-Owl-1.5 uses a 1000×1000 grid, and Qwen3-VL uses relative coordinates. What matters more is (a) harness-side resolution of names and timing, such as app names and waiting for launches, and (b) answer handling, which is coupled to AW's rule that an episode only scores if the agent ends it.

### Cited Findings

| Choice | Measured effect | Source |
|---|---|---|
| Point vs XYXY vs XYWH vs center+WH output (Phi-Ground, trained per format) | SSv2 click acc 85.5 / 84.7 / 84.2 / 85.0; SS-Pro 30.6 / 30.0 / 29.4 / 30.4 | [Phi-Ground](https://arxiv.org/abs/2507.23779) |
| 1000 learned coordinate tokens instead of text digits | "can lead to model collapse and poor performance" | [Phi-Ground](https://arxiv.org/abs/2507.23779) |
| Digit label smoothing and per-digit loss re-weighting | gains only at small data and batch sizes; "no significant impact" at batch 2048 and million-scale data | [Phi-Ground](https://arxiv.org/abs/2507.23779) |
| Relative coordinates ×1000 | chosen because "their value range is fixed and relatively dense" | [Phi-Ground](https://arxiv.org/abs/2507.23779) |
| Relative coordinates enabling lower resolution | MAI-UI attributes its 720p≈1080p result to "the relative coordinate mechanism of Qwen3-VL" | [MAI-UI](https://arxiv.org/abs/2512.22047) |
| Coordinate normalization conventions as an evaluation confound | listed among choices that "shift reported accuracy by several points across implementations" | [ClawGUI](https://arxiv.org/abs/2604.11784) |

- GUI-Owl-1.5's AW action space is `key, click, long_press, swipe, type, system_button(Back/Home/Menu/Enter), open (app by name), wait, answer, terminate(success|failure)`. The prompt states "The screen's resolution is 1000x1000". **Answer handling:** after an `answer` action, the harness forces the next action to `terminate success` and stores the text in `env.interaction_cache` — [gui_owl.py](https://github.com/X-PLUG/MobileAgent/blob/c4cd0a8f9ddedad24dd8a3daf3a56ca69343849f/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py). Our port instead ends the episode on `answer` immediately — [guiowl_agent.py](../../../../eval/androidworld/guiowl_agent.py).
- MobileGym-Bench uses a "structured AnswerSheet protocol that avoids free-text matching failures" — [MobileGym](https://arxiv.org/abs/2605.26114). AW checks some information-retrieval tasks by exact parse, for example `int(agent_response) == expected_count` for "Express your answer as a single integer" — [AndroidWorld](https://arxiv.org/abs/2405.14573).
- App launching: Coati's earlier full trial (72.4%) lost 10 of its 32 failures to "step exhaustion after launches seen as blank screens". "A same-target stopping rule, waiting for a launched app to render and setting a slider to its extreme recovered 9 of them without losing any of 10 solved tasks" — [Coati](https://arxiv.org/abs/2611.02644). That is a frontier backbone (Gemini 3.8 Flash) with an accessibility-tree harness.
- AW's own `launch_app` resolves names through a mapping. Names not in `_DEFAULT_URIS` or `_PATTERN_TO_ACTIVITY` that do not look like package names fail. Our failure-mode script flags these as `unmapped_open_app` — [failure_modes.py](../../../../eval/androidworld/failure_modes.py).
- Compact action vocabularies are motivated by on-device latency. AgentCPM-GUI introduces "a compact action space that reduces output length and supports low-latency execution on mobile devices", but the abstract gives no ablation number — [AgentCPM-GUI](https://arxiv.org/abs/2506.01391).

### Inferences
- Our 0–1000 `point_2d` format matches GUI-Owl's convention, so coordinate format is not a fairness confound and not a likely source of gains.
- The design levers are: (i) an `answer` that ends the episode, or answer-then-terminate as in GUI-Owl's harness, with numeric answers emitted bare; (ii) `open_app` names restricted to the device's installed-app vocabulary, as the earlier report proposed; (iii) a fixed post-launch wait in the harness, reported separately as a harness change.

### Gaps
- No paper found that compares `open_app`-by-name against navigating the app drawer on AW success.
- No ablation found of absolute pixels vs 0–1000 vs 0–1 on AW *success* (only grounding accuracy).
- No published measurement found of parse-failure rates by output format at ≤4B.

## Q4. Inference-time methods usable on a phone (≤4B): retries, verification, loop detection, test-time scaling, step budget

### Takeaway
Measured per-step best-of-n with a separate verifier gives about +5 AW points at 7B. Most of the offline gain also comes from self-ranking candidates by the actor's own logits, with no second model. Gains plateau at n≈5–8. External reflectors and device–cloud fallback give much larger gains, +7 to +17 points, but need an 8B+ second model or the cloud. Verification of completion claims cuts false "complete" by about a third without raising SR. No ≤4B on-device AW measurement of any of these exists.

### Cited Findings

| Method (actor size, benchmark) | Cost | Before → after | Source |
|---|---|---|---|
| PRM verifier, n=3 candidates per step (UI-TARS-1.5-7B actor, 7B PRM, AW) | 3 policy samples + 3 PRM calls per step | 32.8 → 37.9 | [GUI-Shepherd](https://arxiv.org/abs/2509.23738) |
| Actor self-verification by its own logits, n=3 (same actor, AC-High offline) | 3 samples, no extra model | TM 77.4 → 80.8, EM 62.3 → 64.8 (PRM: 81.1 / 65.2) | [GUI-Shepherd](https://arxiv.org/abs/2509.23738) |
| Number of candidates n = 3/5/8/16 with PRM (AC-High offline) | linear in n | EM 65.2 / 65.8 / 65.9 / 65.9 (plateau at 8) | [GUI-Shepherd](https://arxiv.org/abs/2509.23738) |
| Process reward *agent* vs standard PRM (Qwen-VL series, AW) | tool-using verifier | +5.0 over standard PRMs; Qwen3-VL reaches 54.74 | [GUI-PRA](https://arxiv.org/abs/2509.23263) |
| External 8B reflector on paired screenshots (MobileWorld, 117 tasks) | +1 8B call per step | GUI-Owl-1.5-8B +17.09 → 46.15; MAI-UI-8B +14.53 → 35.90 | [Q-Reflector](https://arxiv.org/abs/2608.05587) |
| Device–cloud collaboration (MAI-UI-2B local, 32B cloud on monitor-detected deviation, AW) | cloud calls −42.7% vs cloud-only | +33.4% relative over 2B alone; >40% of tasks fully on-device | [MAI-UI](https://arxiv.org/abs/2512.22047) |
| Host-evidence completion audit, VerifyLoop (Gemini 3.8 Flash, AW, a11y harness) | 1 audit per claimed completion | false-completion 8.0% → 5.4%; SR 89.7 (C1, 1 trial) vs 86.5 (C2, 3-trial mean; 89.7 on its first trial) | [Coati](https://arxiv.org/abs/2611.02644) |
| Prefill-centric NPU inference with fixed-context management (on-device, vs autoregressive T3A+) | — | latency −85.0%, SR up to +24.6% | [DroidPrefill](https://arxiv.org/abs/2611.20772) |
| Verifier-as-policy (scores discretized candidate actions with prefill only; 8B) | 4.3 s/step | AW 59.5% (a11y tree) | [V-Droid](https://arxiv.org/abs/2503.15937) |
| Training-free skill library with reflect-revise-reuse | — | max +6.0 on AW (+16.2 MobileWorld) | [EvoSkill-GUI](https://arxiv.org/abs/2609.17653) |
| World model as prior, Code2World-8B (Gemini-2.5-Flash actor, AW) | +1 8B call per step | +9.5% | [Code2World](https://arxiv.org/abs/2602.09856) |
| Experience reuse with speculative KV (on-device, AW workloads) | — | 1.63–2.36× step-latency speed-up "while maintaining task success rates" | [PastForward](https://arxiv.org/abs/2609.32166) |
| Step budget 15 → 50 (Ferret-UI Lite 3B, OSWorld) | more steps | 17.3 → 19.8 | [Ferret-UI Lite](https://arxiv.org/abs/2509.26539) |
| Step budget 15 → 50 (UI-TARS-72B-DPO, OSWorld) | more steps | 22.7 → 24.6 | [UI-TARS](https://arxiv.org/abs/2501.12326) |
| Latent instead of explicit reasoning (MIRAGE, 4B, AW) | 3–5× fewer decoded tokens | matches explicit-CoT SFT; +10.2 over a comparable instruct baseline | [MIRAGE](https://arxiv.org/abs/2606.04627) |
| Parallel rollouts, pass@4 vs pass@1 (MolmoWeb-8B, web) | 4 full episodes + selector | WebVoyager 78.2 → 94.7; Online-Mind2Web 35.3 → 60.5 | [MolmoWeb](https://arxiv.org/abs/2604.08516) |

- In MAI-UI's RL training, a repetition penalty was part of the recipe: standard GRPO gave +1.8 on AW, and "our enhanced GRPO with data curriculum, repetition penalty, and experience replay" gave +6.0 (8B) — [MAI-UI](https://arxiv.org/abs/2512.22047). This is a training-time loop control, not an inference-time one.
- Coati's step-budget finding: under AW's official budget, the open-source agents' "failures here are step-limit cut-offs rather than wrong decisions", because their released configs "plan up to roughly 120 steps" against "about ten steps for a simple task" — [Coati](https://arxiv.org/abs/2611.02644).

### Inferences
- The only option that is both cheap and phone-feasible is **self-ranking n=3–5 sampled actions by the actor's own log-probability**. It is a llama.cpp feature, needs no second model, and its offline AC-High gain was ~85% of the external PRM's gain at 7B. A 2B actor with an imprecise 2B judge will probably get less. Treat it as a harness change and report it apart from model gains.
- Pass@k and multi-episode retries are not comparable to single-attempt AW numbers (see MobileForge's Pass@3 in Q6). They should never enter a headline comparison.
- A completion audit targets our largest failure class, 45 false "complete" in 101 failures. Coati cut false completions by a third without raising SR. Because AW scores 0 on budget exhaustion (Q6 correction), converting a false complete into "keep going" helps only if later steps reach the goal.

### Gaps
- No published measurement found of retry-on-parse-failure effects on AW. (Our own v2 run: 30.4% empty-intent steps; forcing intents parsed 34/34 but did not fix the policy, per the git log.)
- No ≤4B, fully on-device best-of-n or reflection result on AW was found. All verifier results use a 7B+ actor or verifier, or a cloud model.
- No paper isolates an inference-time loop breaker on AW. VLAA-GUI (desktop) is the closest, and it is in the earlier report.

## Q5. Quantization effects (4-bit GGUF / AWQ / GPTQ vs bf16) on VLM agents

### Takeaway
**No published measurement of 4-bit quantization on a GUI agent's AW (or AndroidControl) success was found.** The closest evidence comes from general VLMs, tool-calling LLM agents and robot VLAs. It says 4-bit weight quantization usually leaves headline scores within noise (−1.6 points on VQA at 2B/7B; no significant change on τ²-bench). It can, however, multiply an agent's existing failure mode (up to 2.5×) and damage confidence signals and format-following, which are exactly what loops, parse failures and false completes depend on.

### Cited Findings

| Setting | Effect | Source |
|---|---|---|
| Qwen2-VL 2B/7B, 4-bit vs full precision, VQA under image degradations (5,700 predictions) | accuracy −1.6 points; internal error-detection AUROC 0.95 → 0.80; verbalized-confidence parse rate 99% → 64% | [Bigger or Cheaper?](https://arxiv.org/abs/2607.24440) |
| Tool-calling agents, 16/8/4-bit weights (τ²-bench, 2 families, dense and MoE, 456 episodes per cell) | no score change survives correction (equivalence bound ±7.5); failure volume up to 2.5× (+17.6 points per task); hidden by the 10-error budget; a 2-error budget exposes a 17-point gap | [Flat Score, Amplified Failures](https://arxiv.org/abs/2607.27275) |
| VLAs (4 models, >180K LIBERO episodes), RTN / AWQ / GPTQ vs VLA-specific PTQ at 4 bits | plain RTN matches calibrated methods; "configurations with no significant LIBERO loss lose 1.5–4.3 points under paired LIBERO-plus perturbations"; 4-bit not faster at batch 1 on H100 | [LoopQ](https://arxiv.org/abs/2611.05093) |
| <3B VLMs on Jetson, component-wise quantization | dense backbones degrade under INT4 noise while MoE mitigates it; INT4 LLM "causes slower token generation due to dequantization overhead" | [Rethinking Small VLM Quantization](https://arxiv.org/abs/2607.08029) |
| 1–2B VLMs, weight-only low-bit | existing methods collapse at 2-bit; staged ViT/LLM-sensitive distillation needed below 4 bits | [SPEED-Q](https://arxiv.org/abs/2511.08914) |

### Inferences
- For a fair GUI-Owl comparison, both models must be served at the same precision, or each at its best. If GUI-Owl ran as a Q4 GGUF while its reported 67.9 is bf16 under vLLM, that is a third confound beside images and resolution. The precision used in our matched run is not recorded in the summary JSON read here.
- Cheap to run on the Mac: a paired pass of LFM3 at Q8_0 vs Q4_K_M that logs parse-failure rate, same-action loop counts and false-complete rate, not just SR, because Flat Score shows the damage shows up in failure volume first.

### Gaps
- No GUI-agent quantization study (ScreenSpot, AndroidControl or AW) at any bit width was found in the paper index or web search. Vendor model cards for quantized GUI models were not checked.
- No evidence was found on whether keeping the vision projector at F16 while quantizing the LLM to Q4_K_M changes grounding error.

## Q6. Harness effects and run-to-run variance on AW: how much do they move the same model, and is our GUI-Owl comparison fair?

### Takeaway
A *faithful* third-party run in the model's own harness reproduces published AW numbers within ~0.5–2.6 points at 8–32B. A *different* harness moves the same model by 7–31 points. Prompting scaffold alone moved GPT-4 Turbo by 10.8 points, and seeds alone move a model 3–7 points. Our matched GUI-Owl run (19.8 vs 67.9 reported, −48.1) used AW's official step budget, just as GUI-Owl's own harness does, so the budget is **not** the confound. Instead it cut GUI-Owl to 1 screenshot at reduced resolution, possibly quantized, against its 5-screenshot full-resolution deployment. The current comparison is therefore compute-matched, not a fair test of GUI-Owl as released.

### Cited Findings

**Same model, different harness or setting (AW unless noted):**

| Model | Harness A → harness B | SR | Source |
|---|---|---|---|
| GUI-Owl-1.5-32B | own paper/leaderboard → faithful third-party re-run (3 seeds: 7, 30, 1234) | 69.8 → 69.3 ± 0.5 | [Beyond the GUI Paradigm](https://arxiv.org/abs/2606.19388) |
| MAI-UI-8B | own → third-party re-run | 70.7 → 68.1 ± 0.6 | [Beyond the GUI Paradigm](https://arxiv.org/abs/2606.19388) |
| Qwen3-VL-32B | own → third-party re-run | 57.3 → 57.8 ± 4.9 | [Beyond the GUI Paradigm](https://arxiv.org/abs/2606.19388) |
| UI-TARS-1.5-7B | reported → Ferret-UI Lite harness (same seed, 5-run mean) [cross-harness] | 33.0 → 26.4 | [Ferret-UI Lite](https://arxiv.org/abs/2509.26539) |
| UI-TARS-1.5-72B | reported → Ferret-UI Lite harness [cross-harness] | 46.6 → 37.7 | [Ferret-UI Lite](https://arxiv.org/abs/2509.26539) |
| Artemis / FinalRun / Midscene (Gemini 3.8 Flash backbone) | own evaluations (~90%) → official step budget, GUI-only, ADB-won tasks not credited | ~90 → 77.6 / 59.9 / 59.1 | [Coati](https://arxiv.org/abs/2611.02644) |
| GPT-4 Turbo | M3A-Simple → M3A (guidelines + reflection), a11y tree | 19.8 → 30.6 | [AndroidWorld](https://arxiv.org/abs/2405.14573) |
| GPT-4 Turbo | M3A a11y tree → M3A SoM (screen + a11y) | 30.6 → 25.4 | [AndroidWorld](https://arxiv.org/abs/2405.14573) |
| Gemini 1.5 Pro | M3A a11y tree → M3A SoM | 19.4 → 22.8 | [AndroidWorld](https://arxiv.org/abs/2405.14573) |
| GUI-Owl-1.5-2B-Instruct | own paper → our harness, "matched" (K=1 image, ≤max_pixels) [cross-harness] | 67.9 → 19.8 (23/116) | [Mobile-Agent-v3.5](https://arxiv.org/abs/2602.16855); [our summary](../../../../results/androidworld/guiowl15_2b_matched.summary.json) |
| Public AW leaderboard, top 7 self-reported entries | single trial, not independently verified | 97.4–100 | [Coati, Table 8](https://arxiv.org/abs/2611.02644) |

**Run-to-run variance (same harness):**

| Setting | Spread | Source |
|---|---|---|
| M3A + GPT-4 Turbo, a11y tree, 3 task seeds | 27.6 / 26.3 / 33.2 (mean 29.0; range 6.9) | [AndroidWorld](https://arxiv.org/abs/2405.14573) |
| Same agent with a fixed seed, 20 trials per task on 5 tasks | "performance varies even with a fixed seed, suggesting model non-determinism"; varying the seed varies results significantly more | [AndroidWorld](https://arxiv.org/abs/2405.14573) |
| Coati, 3 trials, 116 tasks | 89.7 / 87.1 / 82.8 (SD 3.5); 95/116 tasks solved in all 3 trials | [Coati](https://arxiv.org/abs/2611.02644) |
| GUI-Owl-1.5-32B / MAI-UI-8B / Qwen3-VL-32B, 3 seeds | SD 0.5 / 0.6 / 4.9 | [Beyond the GUI Paradigm](https://arxiv.org/abs/2606.19388) |
| Ferret-UI Lite and its baselines | reported as 5-run means "because AndroidWorld generates tasks dynamically with randomness" | [Ferret-UI Lite](https://arxiv.org/abs/2509.26539) |
| Metric choice: MobileForge reports AW **Pass@3** (ForgeOwl-8B 77.6; Qwen3-VL-8B adapted 67.2) | not comparable to single-attempt SR | [MobileForge](https://arxiv.org/abs/2606.19930) |

**What GUI-Owl-1.5's own AW harness does** ([gui_owl.py](https://github.com/X-PLUG/MobileAgent/blob/c4cd0a8f9ddedad24dd8a3daf3a56ca69343849f/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py), [suite_utils.py](https://github.com/X-PLUG/MobileAgent/blob/c4cd0a8f9ddedad24dd8a3daf3a56ca69343849f/Mobile-Agent-v3.5/android_world_v3.5/android_world/suite_utils.py), [run_ma35.py](https://github.com/X-PLUG/MobileAgent/blob/c4cd0a8f9ddedad24dd8a3daf3a56ca69343849f/Mobile-Agent-v3.5/android_world_v3.5/run_ma35.py)):
- Step budget: unchanged from stock AW, `int(10 * task_complexity)`; task seed 30 by default; one combination per template.
- History: last 5 screenshots plus its own previous replies; older steps as text "StepN: <Action>".
- Coordinates: 1000×1000 grid. Images are resized by its `update_image_size_` helper, sent as PNG, temperature set by its vLLM wrapper.
- Answer → forced terminate on the next step; app opening by name through AW's `open_app`.
- A Chrome first-run initialization helper exists in the agent (`initialize_chrome`). Whether it is called during AW runs was not traced.
- Success needs the agent to signal done (below).

**AW scoring rule (verified in code):** stock AndroidWorld sets `agent_successful = task_successful if interaction_results.done else 0.0` ([local copy, suite_utils.py:261](https://github.com/google-research/android_world/blob/55ddaf5edc6f6c25673aed343907d5b9dca66f84/android_world/suite_utils.py)). `episode_runner.run_episode` returns `done=False` when the step budget runs out without a terminal action ([episode_runner.py:96-104](https://github.com/google-research/android_world/blob/55ddaf5edc6f6c25673aed343907d5b9dca66f84/android_world/episode_runner.py)). GUI-Owl's fork keeps the same line ([suite_utils.py fork](https://github.com/X-PLUG/MobileAgent/blob/c4cd0a8f9ddedad24dd8a3daf3a56ca69343849f/Mobile-Agent-v3.5/android_world_v3.5/android_world/suite_utils.py)).

**Corrections to the earlier report:**
- **CORRECTION 1:** The earlier report says that "success is checked on the final device state, so running out the budget after reaching the goal costs nothing". Under stock AW scoring, an episode that hits the budget without `status`/`terminate`/`answer` scores **0** even when the final state is correct (code above). False completes and never completing both lose. Correct termination is a necessary skill, not a free option.
- **CORRECTION 2:** The earlier report says GUI-Owl "never ended an episode itself". `summarize_aw.py` sets `ended_with_status` only when the last parsed `action_type == "status"`, which GUI-Owl's schema (`action: terminate`) never produces. Its `frac_episodes_self_terminated = 0.0` is therefore a schema artifact ([summarize_aw.py:67](../../../../eval/androidworld/summarize_aw.py)). Our GUI-Owl port returns `done=True` on `terminate` and `answer` ([guiowl_agent.py:118-122](../../../../eval/androidworld/guiowl_agent.py)). The schema-aware failure-mode file shows **23 success, 92 step_budget_exhausted, 1 answer_but_failed, 0 complete_but_failed**, with answers in 11 episodes ([guiowl failure modes](../../../../results/androidworld/guiowl15_2b_matched.failure_modes.json)). GUI-Owl did terminate 24 episodes and was correct in 23. Its edge is *calibrated termination*: almost no false completes against LFM3's 45.
- **CORRECTION 3:** The ~48-point "harness loss" for GUI-Owl-1.5-2B is better read as a **configuration** loss. The step budget matches GUI-Owl's official harness. Faithful third-party re-runs of its 32B sibling land within 0.5 points. The settings we changed are 5→1 images, full→≤max_pixels resolution, a different `answer` flow and possibly precision.

### Inferences
- **Size of pure harness effects:** expect ±0.5–2.6 points from faithful re-runs, 5–10 points from a re-implemented harness (Ferret's UI-TARS re-runs, M3A scaffold, SoM vs a11y), and 12–31 points from budget or access changes (Coati). Seed-to-seed spread is 1–7 points even within a harness. At 116 tasks, a ±1-task difference between two models is noise. (The earlier report's McNemar analysis still applies.)
- **Fair GUI-Owl comparison:** a fair headline needs three conditions: (a) GUI-Owl "native", meaning K=5 full-resolution images, its own prompt, answer-then-terminate and bf16 (or the same quantization for both); (b) LFM3 in its best configuration; (c) the same 116 instances, budget `10×complexity`, the same seeds, and ideally 3 seeds each. The compute-matched run remains a valid *second* comparison ("at equal prompt tokens"), but it should be labelled as such. Native GUI-Owl costs ~10.7K prompt tokens and ~61 s/step on our Mac (2-episode sample), so a full native pass is ~8× slower than matched. One option is a stratified native subset, for example all 27 information-retrieval tasks plus a random 30, run once and compared pairwise.
- **Our own harness tweaks** (post-launch wait, completion audit, loop breaker, self-ranking) should go in a separate "harness" column, never folded into model gains, following Coati's and the AW authors' practice.

### Gaps
- No paper isolates the effect of the number of history images on *GUI-Owl's own* AW score, so the share of the −48.1 points due to 5→1 images, as opposed to resolution or precision, cannot be split without our own native run.
- The precision and serving stack of our matched GUI-Owl run, and the exact `max_pixels`, are not recorded in the files read here.
- No public multi-seed variance numbers were found for any ≤4B model on AW. Ferret-UI Lite reports only 5-run means without SD.
